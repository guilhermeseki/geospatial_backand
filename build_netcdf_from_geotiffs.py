#!/usr/bin/env python3
"""
Build yearly NetCDF files from existing GeoTIFF files.
This is useful when GeoTIFFs exist but NetCDF historical files are missing.

Usage:
    python build_netcdf_from_geotiffs.py --source temp_mean --years 2022 2024
    python build_netcdf_from_geotiffs.py --source temp_min --years 2022
"""
import argparse
import xarray as xr
import rasterio
import numpy as np
from pathlib import Path
from datetime import datetime, date
import tempfile
import shutil

def geotiffs_to_netcdf(geotiff_dir: Path, output_file: Path, year: int, var_name: str):
    """
    Combine all GeoTIFF files for a given year into a single NetCDF file.

    Args:
        geotiff_dir: Directory containing GeoTIFF files
        output_file: Output NetCDF file path
        year: Year to process
        var_name: Variable name (e.g., 'temp_mean', 'temp_min', 'temp_max', 'glm_fed')
    """
    # Map source names to NetCDF variable names
    # GLM uses 'fed_30min_max' internally but 'glm_fed' as source name
    netcdf_var_name = 'fed_30min_max' if var_name == 'glm_fed' else var_name
    print(f"\n{'='*80}")
    print(f"Building NetCDF for {var_name} - Year {year}")
    print(f"{'='*80}")

    # Find all GeoTIFF files for this year
    pattern = f"{var_name}_{year}*.tif"
    geotiff_files = sorted(geotiff_dir.glob(pattern))

    if not geotiff_files:
        print(f"⚠️  No GeoTIFF files found matching pattern: {pattern}")
        return False

    print(f"Found {len(geotiff_files)} GeoTIFF files")

    # Extract dates and load data
    data_arrays = []
    dates = []
    shapes = {}

    print("Loading GeoTIFF files...")

    # First pass: determine most common shape
    for tif_file in geotiff_files:
        with rasterio.open(tif_file) as src:
            shape = src.shape
            shapes[shape] = shapes.get(shape, 0) + 1

    target_shape = max(shapes.items(), key=lambda x: x[1])[0]
    print(f"Target shape: {target_shape} ({shapes[target_shape]}/{len(geotiff_files)} files)")
    if len(shapes) > 1:
        print(f"⚠️  Warning: {len(geotiff_files) - shapes[target_shape]} files have different shapes and will be skipped")

    # Second pass: load files with matching shape
    for i, tif_file in enumerate(geotiff_files, 1):
        # Extract date from filename: temp_mean_20220101.tif -> 2022-01-01
        date_str = tif_file.stem.split('_')[-1]  # "20220101"
        try:
            file_date = datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            print(f"  ⚠️  Skipping {tif_file.name}: cannot parse date")
            continue

        # Read GeoTIFF
        with rasterio.open(tif_file) as src:
            data = src.read(1)  # Read first band

            # Skip files with mismatched shape
            if data.shape != target_shape:
                print(f"  ⚠️  Skipping {tif_file.name}: shape {data.shape} != {target_shape}")
                continue

            transform = src.transform
            crs = src.crs

            # Get coordinates
            height, width = data.shape
            lon = np.array([transform[2] + (i + 0.5) * transform[0] for i in range(width)])
            lat = np.array([transform[5] + (j + 0.5) * transform[4] for j in range(height)])

            # Create DataArray (explicitly NO band dimension)
            da = xr.DataArray(
                data,
                coords={
                    'latitude': lat,
                    'longitude': lon
                },
                dims=['latitude', 'longitude']
            )

            # Remove any 'band' coordinate if it exists
            if 'band' in da.coords:
                da = da.drop_vars('band')

            data_arrays.append(da)
            dates.append(file_date)

        if i % 50 == 0:
            print(f"  Loaded {i}/{len(geotiff_files)} files...")

    print(f"✓ Loaded {len(data_arrays)} files (skipped {len(geotiff_files) - len(data_arrays)})")

    # Combine into single Dataset with time dimension
    print("Combining into NetCDF...")

    # Stack all data arrays along time dimension
    combined_data = np.stack([da.values for da in data_arrays], axis=0)

    # Create time coordinate
    time_coord = [np.datetime64(d) for d in dates]

    # Set variable attributes based on source type
    if var_name == 'glm_fed':
        var_attrs = {
            'long_name': 'GLM Flash Extent Density',
            'units': 'flashes per day',
            'source': 'GOES-16/17 GLM (reconstructed from GeoTIFF)',
            'created_at': datetime.now().isoformat()
        }
    elif var_name == 'wind_speed':
        var_attrs = {
            'long_name': 'wind speed at 10m',
            'units': 'meters per second',
            'source': 'ERA5-Land (reconstructed from GeoTIFF)',
            'created_at': datetime.now().isoformat()
        }
    else:  # temperature variables
        var_attrs = {
            'long_name': f'{var_name.replace("_", " ")} temperature',
            'units': 'degrees_celsius',
            'source': 'ERA5-Land (reconstructed from GeoTIFF)',
            'created_at': datetime.now().isoformat()
        }

    # Create Dataset (use netcdf_var_name for the actual variable name in file)
    ds = xr.Dataset(
        {
            netcdf_var_name: xr.DataArray(
                combined_data,
                coords={
                    'time': time_coord,
                    'latitude': data_arrays[0].latitude,
                    'longitude': data_arrays[0].longitude
                },
                dims=['time', 'latitude', 'longitude'],
                attrs=var_attrs
            )
        }
    )

    # Add global attributes
    ds.attrs.update({
        'title': f'{var_name} {year}',
        'source': 'ERA5-Land daily statistics',
        'created_from': 'GeoTIFF files',
        'created_at': datetime.now().isoformat(),
        'year': year,
        'days': len(dates)
    })

    # Encoding for efficient storage
    encoding = {
        netcdf_var_name: {
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

    # Write to temporary file first (FUSE filesystem fix)
    temp_dir = Path(tempfile.mkdtemp(prefix="netcdf_build_"))
    temp_file = temp_dir / output_file.name

    print(f"Writing to: {output_file.name}")
    ds.to_netcdf(temp_file, mode='w', encoding=encoding, engine='netcdf4')

    # Move to final location
    output_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(temp_file, output_file)
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Verify
    size_mb = output_file.stat().st_size / 1024 / 1024
    print(f"✓ Complete: {output_file.name} ({size_mb:.1f} MB)")
    print(f"  Days: {len(dates)}")
    print(f"  Shape: {combined_data.shape}")
    print(f"  Date range: {dates[0]} to {dates[-1]}")

    ds.close()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Build yearly NetCDF files from GeoTIFF files'
    )
    parser.add_argument(
        '--source',
        required=True,
        choices=['temp_mean', 'temp_min', 'temp_max', 'wind_speed', 'glm_fed'],
        help='Data source name'
    )
    parser.add_argument(
        '--years',
        nargs='+',
        type=int,
        required=True,
        help='Years to process (e.g., 2022 2024)'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='/mnt/workwork/geoserver_data',
        help='Base data directory'
    )

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    source = args.source

    print("=" * 80)
    print("BUILDING NETCDF FROM GEOTIFF FILES")
    print("=" * 80)
    print(f"Source: {source}")
    print(f"Years: {', '.join(map(str, args.years))}")
    print(f"Data directory: {data_dir}")
    print("=" * 80)

    geotiff_dir = data_dir / source
    hist_dir = data_dir / f"{source}_hist"

    if not geotiff_dir.exists():
        print(f"✗ GeoTIFF directory does not exist: {geotiff_dir}")
        exit(1)

    success_count = 0
    for year in args.years:
        output_file = hist_dir / f"{source}_{year}.nc"

        if output_file.exists():
            print(f"\n⚠️  {output_file.name} already exists")
            response = input(f"Overwrite? (y/n): ")
            if response.lower() != 'y':
                print(f"  Skipping {year}")
                continue

        success = geotiffs_to_netcdf(geotiff_dir, output_file, year, source)
        if success:
            success_count += 1

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Successfully created {success_count}/{len(args.years)} NetCDF files")
    print("\nNext steps:")
    print("  1. Verify files exist:")
    for year in args.years:
        print(f"     ls -lh {hist_dir}/{source}_{year}.nc")
    print("  2. Restart FastAPI to load new NetCDF files:")
    print("     kill <fastapi_pid>")
    print("     python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4")
    print("=" * 80)
