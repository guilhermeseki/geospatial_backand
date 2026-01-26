#!/usr/bin/env python3
"""
Build yearly NetCDF files from GeoTIFF mosaics for 1991-2014.

This reads all the daily GeoTIFF files and creates consolidated yearly NetCDF files
for fast xarray queries.
"""
import sys
from pathlib import Path
import xarray as xr
import rioxarray
from datetime import datetime
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config.settings import get_settings


def build_yearly_netcdf_from_geotiffs(variable: str, year: int):
    """
    Build a yearly NetCDF file from daily GeoTIFF files.

    Args:
        variable: "temp_max" or "temp_min"
        year: Year to process
    """
    settings = get_settings()

    # Paths
    geotiff_dir = Path(settings.DATA_DIR) / variable
    output_dir = Path(settings.DATA_DIR) / f"{variable}_hist"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{variable}_{year}.nc"

    # Find all GeoTIFF files for this year
    pattern = f"{variable}_{year}*.tif"
    geotiff_files = sorted(geotiff_dir.glob(pattern))

    if not geotiff_files:
        print(f"  ⚠️  No GeoTIFF files found for {year}")
        return None

    print(f"  Found {len(geotiff_files)} GeoTIFF files")

    # Load all files
    datasets = []
    dates = []

    for geotiff_file in geotiff_files:
        # Extract date from filename: temp_max_YYYYMMDD.tif
        date_str = geotiff_file.stem.split('_')[-1]
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            dates.append(date)

            # Load GeoTIFF
            da = rioxarray.open_rasterio(geotiff_file, chunks='auto')
            da = da.squeeze(drop=True)  # Remove band dimension
            datasets.append(da)
        except Exception as e:
            print(f"    ⚠️  Skipping {geotiff_file.name}: {e}")
            continue

    if not datasets:
        print(f"  ✗ No valid data for {year}")
        return None

    print(f"  Loaded {len(datasets)} valid files")

    # Concatenate along time dimension
    combined = xr.concat(datasets, dim='time')
    combined = combined.assign_coords(time=dates)
    combined = combined.sortby('time')

    # Create dataset
    ds = xr.Dataset({
        variable: combined
    })

    # Add metadata
    ds[variable].attrs['long_name'] = f"Daily {variable.replace('_', ' ').title()}"
    ds[variable].attrs['units'] = '°C'
    ds[variable].attrs['source'] = 'ERA5-Land'

    ds.attrs['title'] = f'{variable} Daily Data'
    ds.attrs['year'] = year
    ds.attrs['created'] = datetime.now().isoformat()

    # Rename spatial coordinates if needed
    if 'x' in ds.coords:
        ds = ds.rename({'x': 'longitude', 'y': 'latitude'})

    # Chunk for efficient access
    ds = ds.chunk({'time': 1, 'latitude': 100, 'longitude': 100})

    # Save with compression
    encoding = {
        variable: {
            'zlib': True,
            'complevel': 5,
            'chunksizes': (1, min(100, ds.dims['latitude']), min(100, ds.dims['longitude']))
        }
    }

    print(f"  Writing to {output_file.name}...")
    ds.to_netcdf(output_file, encoding=encoding)

    file_size_mb = output_file.stat().st_size / 1024 / 1024
    print(f"  ✓ Created {output_file.name} ({file_size_mb:.1f} MB)")

    # Close datasets
    for d in datasets:
        d.close()
    ds.close()

    return output_file


def main():
    print("="*80)
    print("BUILD YEARLY NETCDF FILES FROM GEOTIFFS: 1991-2014")
    print("="*80)
    print()

    variables = ['temp_max', 'temp_min']
    years = range(1991, 2015)  # 1991-2014

    total_files = 0

    for variable in variables:
        print(f"\n{'='*80}")
        print(f"Processing: {variable.upper()}")
        print(f"{'='*80}\n")

        for year in years:
            print(f"Year {year}:")
            try:
                output_file = build_yearly_netcdf_from_geotiffs(variable, year)
                if output_file:
                    total_files += 1
            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue
            print()

    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Created {total_files} yearly NetCDF files")
    print()
    print("Next step: Calculate 1991-2020 climatology")
    print("  python app/calculate_temperature_climatology.py --all --start-year 1991 --end-year 2020")
    print("="*80)


if __name__ == "__main__":
    main()
