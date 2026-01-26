#!/usr/bin/env python3
"""
Clip temp_mean NetCDF files (2023, 2025) to Brazil extent to match 2015-2021 grid.
This is much faster than regenerating from ERA5 source data.
"""
import xarray as xr
from pathlib import Path
import shutil
from datetime import datetime

# Brazil extent from 2015-2021 files
BRAZIL_LAT_MIN = -35.0
BRAZIL_LAT_MAX = 6.5
BRAZIL_LON_MIN = -75.0
BRAZIL_LON_MAX = -33.5

DATA_DIR = Path("/mnt/workwork/geoserver_data")
HIST_DIR = DATA_DIR / "temp_mean_hist"

def clip_netcdf_to_brazil_extent(input_file: Path, output_file: Path):
    """Clip a NetCDF file to Brazil extent."""
    print(f"Processing: {input_file.name}")

    # Open the file
    ds = xr.open_dataset(input_file)

    print(f"  Original shape: {ds.temp_mean.shape}")
    print(f"  Original lat range: [{ds.latitude.min().values:.1f}, {ds.latitude.max().values:.1f}]")
    print(f"  Original lon range: [{ds.longitude.min().values:.1f}, {ds.longitude.max().values:.1f}]")

    # Clip to Brazil extent
    # Note: latitude might be decreasing (25 to -53), so use proper selection
    ds_clipped = ds.sel(
        latitude=slice(BRAZIL_LAT_MAX, BRAZIL_LAT_MIN),
        longitude=slice(BRAZIL_LON_MIN, BRAZIL_LON_MAX)
    )

    print(f"  Clipped shape: {ds_clipped.temp_mean.shape}")
    print(f"  Clipped lat range: [{ds_clipped.latitude.min().values:.1f}, {ds_clipped.latitude.max().values:.1f}]")
    print(f"  Clipped lon range: [{ds_clipped.longitude.min().values:.1f}, {ds_clipped.longitude.max().values:.1f}]")

    # Update metadata
    ds_clipped.attrs['title'] = ds_clipped.attrs.get('title', '') + ' (Brazil extent)'
    ds_clipped.attrs['spatial_extent'] = f'Brazil: [{BRAZIL_LON_MIN}, {BRAZIL_LAT_MIN}] to [{BRAZIL_LON_MAX}, {BRAZIL_LAT_MAX}]'
    ds_clipped.attrs['clipped_on'] = datetime.now().isoformat()

    # Encoding for efficient storage
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

    # Write to temp file first, then move (for FUSE filesystems)
    import tempfile
    temp_dir = Path(tempfile.mkdtemp(prefix="clip_temp_"))
    temp_file = temp_dir / output_file.name

    print(f"  Writing to: {output_file.name}")
    ds_clipped.to_netcdf(temp_file, mode='w', encoding=encoding, engine='netcdf4')

    # Move to final location
    shutil.copy2(temp_file, output_file)
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Clean up
    ds.close()
    ds_clipped.close()

    # Get file size
    size_mb = output_file.stat().st_size / 1024 / 1024
    print(f"  ✓ Complete: {output_file.name} ({size_mb:.1f} MB)")
    print()


if __name__ == "__main__":
    print("=" * 80)
    print("CLIPPING temp_mean NetCDF FILES TO BRAZIL EXTENT")
    print("=" * 80)
    print(f"Target extent: Lat[{BRAZIL_LAT_MIN}, {BRAZIL_LAT_MAX}], Lon[{BRAZIL_LON_MIN}, {BRAZIL_LON_MAX}]")
    print(f"This will create consistent 416×416 grid across all years (2015-2025)")
    print("=" * 80)
    print()

    # Files to clip
    years_to_clip = [2023, 2025]

    for year in years_to_clip:
        input_file = HIST_DIR / f"temp_mean_{year}.nc"

        if not input_file.exists():
            print(f"⚠️  {year}: File not found ({input_file.name}), skipping")
            continue

        # Backup original file
        backup_file = HIST_DIR / f"temp_mean_{year}_latam_backup.nc"
        if not backup_file.exists():
            print(f"Creating backup: {backup_file.name}")
            shutil.copy2(input_file, backup_file)
            print(f"  ✓ Backup created")
            print()

        # Clip to Brazil extent
        output_file = input_file  # Overwrite original
        clip_netcdf_to_brazil_extent(input_file, output_file)

    print("=" * 80)
    print("CLIPPING COMPLETE")
    print("=" * 80)
    print()
    print("Verifying grid consistency...")
    print()

    # Verify all files now have consistent grid
    all_files = sorted(HIST_DIR.glob("temp_mean_*.nc"))

    # Exclude backups
    all_files = [f for f in all_files if "backup" not in f.name]

    print(f"Checking {len(all_files)} temp_mean NetCDF files:")
    print()

    for nc_file in all_files:
        ds = xr.open_dataset(nc_file)
        lat_shape = ds.latitude.shape[0]
        lon_shape = ds.longitude.shape[0]
        lat_range = f"[{ds.latitude.min().values:.1f}, {ds.latitude.max().values:.1f}]"
        lon_range = f"[{ds.longitude.min().values:.1f}, {ds.longitude.max().values:.1f}]"

        print(f"  {nc_file.name:25s} {lat_shape:3d}×{lon_shape:3d}  Lat{lat_range}  Lon{lon_range}")
        ds.close()

    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Restart FastAPI app to reload datasets")
    print("2. Test temp_mean area_triggers endpoint")
    print("=" * 80)
