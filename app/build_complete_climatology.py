#!/usr/bin/env python3
"""
Build complete climatology files (1991-2020) and reorganize data structure:
1. Build 2015-2020 yearly NetCDF files from existing GeoTIFFs
2. Consolidate 1991-2020 into /mnt/workwork/climatology_data/
3. Delete 1991-2013 GeoTIFFs and yearly NetCDFs (keep only 2014+ in geoserver_data)
"""
import sys
from pathlib import Path
import xarray as xr
import rioxarray
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config.settings import get_settings


def build_yearly_netcdf(variable: str, year: int, output_dir: Path, geotiff_dir: Path):
    """Build yearly NetCDF from GeoTIFFs."""
    pattern = f"{variable}_{year}*.tif"
    geotiff_files = sorted(geotiff_dir.glob(pattern))

    if not geotiff_files:
        return None

    print(f"    Loading {len(geotiff_files)} GeoTIFF files...")

    datasets = []
    dates = []

    for geotiff_file in geotiff_files:
        date_str = geotiff_file.stem.split('_')[-1]
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            dates.append(date)
            da = rioxarray.open_rasterio(geotiff_file, chunks='auto')
            da = da.squeeze(drop=True)
            datasets.append(da)
        except Exception as e:
            print(f"      ⚠️  Skipping {geotiff_file.name}: {e}")
            continue

    if not datasets:
        return None

    combined = xr.concat(datasets, dim='time')
    combined = combined.assign_coords(time=dates)
    combined = combined.sortby('time')

    ds = xr.Dataset({variable: combined})
    ds[variable].attrs['long_name'] = f"Daily {variable.replace('_', ' ').title()}"
    ds[variable].attrs['units'] = '°C'
    ds[variable].attrs['source'] = 'ERA5-Land'

    if 'x' in ds.coords:
        ds = ds.rename({'x': 'longitude', 'y': 'latitude'})

    ds = ds.chunk({'time': 1, 'latitude': 100, 'longitude': 100})

    output_file = output_dir / f"{variable}_{year}.nc"
    encoding = {
        variable: {
            'zlib': True,
            'complevel': 5,
            'chunksizes': (1, min(100, ds.dims['latitude']), min(100, ds.dims['longitude']))
        }
    }

    ds.to_netcdf(output_file, encoding=encoding)

    for d in datasets:
        d.close()
    ds.close()

    return output_file


def build_climatology(variable: str):
    """Build complete climatology NetCDF (1991-2020)."""
    settings = get_settings()

    print(f"\n{'='*80}")
    print(f"{variable.upper()}: Building complete climatology 1991-2020")
    print(f"{'='*80}\n")

    geotiff_dir = Path(settings.DATA_DIR) / variable
    yearly_netcdf_dir = Path(settings.DATA_DIR) / f"{variable}_hist"
    climatology_dir = Path("/mnt/workwork/climatology_data/temp/daily")
    climatology_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Build missing years (2015-2020)
    print("Step 1: Building missing yearly NetCDF files (2015-2020)")
    print("-" * 80)

    for year in range(2015, 2021):
        yearly_file = yearly_netcdf_dir / f"{variable}_{year}.nc"
        if yearly_file.exists():
            print(f"  ✓ {year}: Already exists")
        else:
            print(f"  Building {year}...")
            result = build_yearly_netcdf(variable, year, yearly_netcdf_dir, geotiff_dir)
            if result:
                file_size_mb = result.stat().st_size / 1024 / 1024
                print(f"  ✓ {year}: Created ({file_size_mb:.1f} MB)")
            else:
                print(f"  ✗ {year}: No data found")

    # Step 2: Consolidate 1991-2020
    print(f"\nStep 2: Consolidating 1991-2020 into single file")
    print("-" * 80)

    yearly_files = []
    for year in range(1991, 2021):
        yearly_file = yearly_netcdf_dir / f"{variable}_{year}.nc"
        if yearly_file.exists():
            yearly_files.append(yearly_file)
            print(f"  ✓ {year}")
        else:
            print(f"  ⚠️  {year}: Missing")

    print(f"\n  Loading {len(yearly_files)} yearly files...")
    datasets = [xr.open_dataset(f, chunks='auto') for f in yearly_files]

    print(f"  Concatenating...")
    combined = xr.concat(datasets, dim='time')
    combined = combined.sortby('time')

    combined.attrs['title'] = f'{variable} Daily Data - WMO Climatology 1991-2020'
    combined.attrs['period'] = '1991-2020'
    combined.attrs['source'] = 'ERA5-Land'
    combined.attrs['region'] = 'Brazil'
    combined.attrs['created'] = datetime.now().isoformat()

    combined = combined.chunk({'time': 365, 'latitude': 100, 'longitude': 100})

    output_file = climatology_dir / f"{variable}_1991-2020.nc"
    encoding = {
        variable: {
            'zlib': True,
            'complevel': 5,
            'chunksizes': (365, min(100, combined.dims['latitude']), min(100, combined.dims['longitude']))
        }
    }

    print(f"  Writing to {output_file}...")
    combined.to_netcdf(output_file, encoding=encoding)

    for ds in datasets:
        ds.close()
    combined.close()

    file_size_gb = output_file.stat().st_size / 1024 / 1024 / 1024
    print(f"  ✓ Created ({file_size_gb:.2f} GB)")

    # Step 3: Delete 1991-2013 GeoTIFFs
    print(f"\nStep 3: Deleting GeoTIFF files (1991-2013)")
    print("-" * 80)

    geotiff_count = 0
    freed_mb = 0

    for year in range(1991, 2014):
        pattern = f"{variable}_{year}*.tif"
        for geotiff_file in geotiff_dir.glob(pattern):
            file_size = geotiff_file.stat().st_size / 1024 / 1024
            geotiff_file.unlink()
            geotiff_count += 1
            freed_mb += file_size

    freed_gb = freed_mb / 1024
    print(f"  ✓ Deleted {geotiff_count} files ({freed_gb:.2f} GB freed)")

    # Step 4: Delete 1991-2013 yearly NetCDFs
    print(f"\nStep 4: Deleting yearly NetCDF files (1991-2013) from geoserver_data")
    print("-" * 80)

    netcdf_freed_mb = 0
    for year in range(1991, 2014):
        yearly_file = yearly_netcdf_dir / f"{variable}_{year}.nc"
        if yearly_file.exists():
            file_size = yearly_file.stat().st_size / 1024 / 1024
            yearly_file.unlink()
            netcdf_freed_mb += file_size

    netcdf_freed_gb = netcdf_freed_mb / 1024
    print(f"  ✓ Deleted 1991-2013 yearly NetCDFs ({netcdf_freed_gb:.2f} GB freed)")

    total_freed_gb = freed_gb + netcdf_freed_gb
    print(f"\n  Total freed: {total_freed_gb:.2f} GB")

    return output_file


def main():
    print("="*80)
    print("BUILD COMPLETE CLIMATOLOGY: 1991-2020")
    print("="*80)
    print()
    print("This will:")
    print("  1. Build 2015-2020 yearly NetCDF files from GeoTIFFs")
    print("  2. Consolidate 1991-2020 into climatology_data directory")
    print("  3. Delete 1991-2013 GeoTIFFs (~25 GB)")
    print("  4. Delete 1991-2013 yearly NetCDFs from geoserver_data")
    print("  5. Keep only 2014+ data in geoserver_data for operational access")
    print()

    variables = ['temp_max', 'temp_min']

    for variable in variables:
        try:
            build_climatology(variable)
        except Exception as e:
            print(f"\n✗ Error processing {variable}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print()
    print("Climatology files: /mnt/workwork/climatology_data/temp/daily/")
    print("  - temp_max_1991-2020.nc")
    print("  - temp_min_1991-2020.nc")
    print()
    print("Operational data: /mnt/workwork/geoserver_data/")
    print("  - temp_max/ (2014-2025 GeoTIFFs)")
    print("  - temp_min/ (2014-2025 GeoTIFFs)")
    print("  - temp_max_hist/ (2014-2025 yearly NetCDFs)")
    print("  - temp_min_hist/ (2014-2025 yearly NetCDFs)")
    print("="*80)


if __name__ == "__main__":
    main()
