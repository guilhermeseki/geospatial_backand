#!/usr/bin/env python3
"""
Re-clip temp_mean 2023 and 2025 files to EXACTLY match 2015-2021 coordinates.
Uses coordinate values instead of ranges to ensure perfect alignment.
"""
import xarray as xr
from pathlib import Path
import shutil
from datetime import datetime

DATA_DIR = Path("/mnt/workwork/geoserver_data")
HIST_DIR = DATA_DIR / "temp_mean_hist"

# Get reference coordinates from 2015 file
ref_ds = xr.open_dataset(HIST_DIR / "temp_mean_2015.nc")
REF_LAT = ref_ds.latitude.values
REF_LON = ref_ds.longitude.values
ref_ds.close()

print("Reference coordinates from temp_mean_2015.nc:")
print(f"  Latitude: {len(REF_LAT)} points, [{REF_LAT.min():.1f}, {REF_LAT.max():.1f}]")
print(f"  Longitude: {len(REF_LON)} points, [{REF_LON.min():.1f}, {REF_LON.max():.1f}]")
print()

def reclip_to_exact_coords(input_file: Path, output_file: Path):
    """Re-clip using exact coordinate matching."""
    print(f"Processing: {input_file.name}")

    # Restore from backup if it exists
    backup_file = input_file.parent / f"{input_file.stem}_latam_backup.nc"
    if backup_file.exists():
        print(f"  Restoring from backup: {backup_file.name}")
        ds = xr.open_dataset(backup_file)
    else:
        ds = xr.open_dataset(input_file)

    print(f"  Original shape: {ds.temp_mean.shape}")
    print(f"  Original lat: [{ds.latitude.min().values:.1f}, {ds.latitude.max().values:.1f}] ({len(ds.latitude)} points)")
    print(f"  Original lon: [{ds.longitude.min().values:.1f}, {ds.longitude.max().values:.1f}] ({len(ds.longitude)} points)")

    # Select using exact coordinate values
    ds_matched = ds.sel(latitude=REF_LAT, longitude=REF_LON, method='nearest')

    # Force exact coordinate values (in case of minor floating point differences)
    ds_matched = ds_matched.assign_coords({
        'latitude': REF_LAT,
        'longitude': REF_LON
    })

    print(f"  Matched shape: {ds_matched.temp_mean.shape}")
    print(f"  Matched lat: [{ds_matched.latitude.min().values:.1f}, {ds_matched.latitude.max().values:.1f}] ({len(ds_matched.latitude)} points)")
    print(f"  Matched lon: [{ds_matched.longitude.min().values:.1f}, {ds_matched.longitude.max().values:.1f}] ({len(ds_matched.longitude)} points)")

    # Update metadata
    ds_matched.attrs['title'] = ds_matched.attrs.get('title', '').replace(' (Brazil extent)', '') + ' (Brazil extent - exact match)'
    ds_matched.attrs['spatial_extent'] = f'Brazil: Lat[{REF_LAT.min():.1f}, {REF_LAT.max():.1f}], Lon[{REF_LON.min():.1f}, {REF_LON.max():.1f}]'
    ds_matched.attrs['reclipped_on'] = datetime.now().isoformat()

    # Encoding
    encoding = {
        'temp_mean': {
            'chunksizes': (1, 20, 20),
            'zlib': True,
            'complevel': 5,
            'dtype': 'float32',
            '_FillValue': -9999.0
        },
        'time': {
            'units': 'days since 1970-01-01',
            'calendar': 'proleptic_gregorian',
            'dtype': 'float64'
        },
        'latitude': {
            'dtype': 'float32'
        },
        'longitude': {
            'dtype': 'float32'
        }
    }

    # Write to temp file first
    import tempfile
    temp_dir = Path(tempfile.mkdtemp(prefix="reclip_temp_"))
    temp_file = temp_dir / output_file.name

    print(f"  Writing to: {output_file.name}")
    ds_matched.to_netcdf(temp_file, mode='w', encoding=encoding, engine='netcdf4')

    # Move to final location
    shutil.copy2(temp_file, output_file)
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Clean up
    ds.close()
    ds_matched.close()

    size_mb = output_file.stat().st_size / 1024 / 1024
    print(f"  ✓ Complete: {output_file.name} ({size_mb:.1f} MB)")
    print()


if __name__ == "__main__":
    print("=" * 80)
    print("RE-CLIPPING temp_mean FILES TO EXACT COORDINATE MATCH")
    print("=" * 80)
    print()

    years_to_reclip = [2023, 2025]

    for year in years_to_reclip:
        input_file = HIST_DIR / f"temp_mean_{year}.nc"

        if not input_file.exists():
            print(f"⚠️  {year}: File not found, skipping")
            continue

        reclip_to_exact_coords(input_file, input_file)

    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print()

    # Verify all files now have identical coordinates
    all_files = sorted(HIST_DIR.glob("temp_mean_*.nc"))
    all_files = [f for f in all_files if "backup" not in f.name]

    print(f"Checking {len(all_files)} files:")
    print()

    all_match = True
    for nc_file in all_files:
        ds = xr.open_dataset(nc_file)
        lat_shape = ds.latitude.shape[0]
        lon_shape = ds.longitude.shape[0]

        lat_match = (ds.latitude.values == REF_LAT).all()
        lon_match = (ds.longitude.values == REF_LON).all()

        status = "✓" if (lat_match and lon_match) else "✗"
        print(f"  {status} {nc_file.name:25s} {lat_shape:3d}×{lon_shape:3d}  LatMatch:{lat_match}  LonMatch:{lon_match}")

        if not (lat_match and lon_match):
            all_match = False

        ds.close()

    print()
    print("=" * 80)
    if all_match:
        print("✓✓✓ ALL FILES HAVE IDENTICAL COORDINATES!")
    else:
        print("⚠️  Some files still have mismatched coordinates")
    print("=" * 80)
    print()
    print("Next: Restart FastAPI to reload datasets")
