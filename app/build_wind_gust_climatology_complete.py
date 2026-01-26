#!/usr/bin/env python3
"""
Build complete wind gust climatology (1991-2020):
1. Download and process daily max wind gust from ERA5 (1991-2020)
2. Create yearly NetCDF files
3. Consolidate into single climatology file
4. Clean up old data
"""
import sys
from pathlib import Path
from datetime import date, datetime
import xarray as xr
import rioxarray

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config.settings import get_settings
from app.workflows.data_processing.wind_gust_daily_flow import wind_gust_daily_era5_flow


def build_yearly_netcdf(year: int, geotiff_dir: Path, output_dir: Path):
    """Build yearly NetCDF from GeoTIFFs."""
    variable = "wind_speed"
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
            dt = datetime.strptime(date_str, '%Y%m%d')
            dates.append(dt)
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

    ds = xr.Dataset({'wind_gust': combined})
    ds['wind_gust'].attrs['long_name'] = 'Daily Maximum Wind Gust'
    ds['wind_gust'].attrs['units'] = 'km/h'
    ds['wind_gust'].attrs['source'] = 'ERA5'

    if 'x' in ds.coords:
        ds = ds.rename({'x': 'longitude', 'y': 'latitude'})

    ds = ds.chunk({'time': 1, 'latitude': 100, 'longitude': 100})

    output_file = output_dir / f"wind_gust_{year}.nc"
    encoding = {
        'wind_gust': {
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


def consolidate_climatology():
    """Consolidate yearly NetCDFs into single climatology file."""
    settings = get_settings()

    print(f"\n{'='*80}")
    print("CONSOLIDATING WIND GUST CLIMATOLOGY 1991-2020")
    print(f"{'='*80}\n")

    geotiff_dir = Path(settings.DATA_DIR) / "wind_speed"
    yearly_netcdf_dir = Path(settings.DATA_DIR) / "wind_gust_hist"
    yearly_netcdf_dir.mkdir(parents=True, exist_ok=True)

    climatology_dir = Path("/mnt/workwork/climatology_data/wind_gust/daily")
    climatology_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Build yearly NetCDFs if needed
    print("Step 1: Building yearly NetCDF files (1991-2020)")
    print("-" * 80)

    for year in range(1991, 2021):
        yearly_file = yearly_netcdf_dir / f"wind_gust_{year}.nc"
        if yearly_file.exists():
            print(f"  ✓ {year}: Already exists")
        else:
            print(f"  Building {year}...")
            result = build_yearly_netcdf(year, geotiff_dir, yearly_netcdf_dir)
            if result:
                file_size_mb = result.stat().st_size / 1024 / 1024
                print(f"  ✓ {year}: Created ({file_size_mb:.1f} MB)")
            else:
                print(f"  ⚠️  {year}: No data found")

    # Step 2: Consolidate all years
    print(f"\nStep 2: Consolidating 1991-2020 into single file")
    print("-" * 80)

    yearly_files = []
    for year in range(1991, 2021):
        yearly_file = yearly_netcdf_dir / f"wind_gust_{year}.nc"
        if yearly_file.exists():
            yearly_files.append(yearly_file)
            print(f"  ✓ {year}")
        else:
            print(f"  ⚠️  {year}: Missing")

    if not yearly_files:
        print("\n  ✗ No yearly files found!")
        return None

    print(f"\n  Loading {len(yearly_files)} yearly files...")
    datasets = [xr.open_dataset(f, chunks='auto') for f in yearly_files]

    print(f"  Concatenating...")
    combined = xr.concat(datasets, dim='time')
    combined = combined.sortby('time')

    combined.attrs['title'] = 'Wind Gust Daily Data - WMO Climatology 1991-2020'
    combined.attrs['period'] = '1991-2020'
    combined.attrs['source'] = 'ERA5'
    combined.attrs['region'] = 'Brazil'
    combined.attrs['created'] = datetime.now().isoformat()
    combined.attrs['description'] = 'Daily maximum 10m wind gust for Brazil - WMO climatology reference period'

    combined = combined.chunk({'time': 365, 'latitude': 100, 'longitude': 100})

    output_file = climatology_dir / "wind_gust_1991-2020.nc"
    encoding = {
        'wind_gust': {
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
        pattern = f"wind_speed_{year}*.tif"
        for geotiff_file in geotiff_dir.glob(pattern):
            file_size = geotiff_file.stat().st_size / 1024 / 1024
            geotiff_file.unlink()
            geotiff_count += 1
            freed_mb += file_size

    freed_gb = freed_mb / 1024
    print(f"  ✓ Deleted {geotiff_count} files ({freed_gb:.2f} GB freed)")

    # Step 4: Delete 1991-2013 yearly NetCDFs
    print(f"\nStep 4: Deleting yearly NetCDF files (1991-2013)")
    print("-" * 80)

    netcdf_freed_mb = 0
    for year in range(1991, 2014):
        yearly_file = yearly_netcdf_dir / f"wind_gust_{year}.nc"
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
    settings = get_settings()

    print("="*80)
    print("BUILD WIND GUST CLIMATOLOGY: 1991-2020")
    print("="*80)
    print()
    print("Data source: ERA5 sis-agrometeorological-indicators")
    print("Variable: 10m_wind_gust (daily maximum)")
    print("Period: 1991-2020 (WMO climatology reference period)")
    print()
    print("This will:")
    print("  1. Download daily max wind gust from ERA5 (1991-2020)")
    print("  2. Create daily GeoTIFF files")
    print("  3. Create yearly NetCDF files")
    print("  4. Consolidate into wind_gust_1991-2020.nc")
    print("  5. Delete 1991-2013 GeoTIFFs and yearly NetCDFs")
    print("  6. Keep only 2014+ in geoserver_data for operational access")
    print()

    # Download and process data year by year
    for year in range(1991, 2021):
        print(f"\n{'='*80}")
        print(f"Downloading and processing: {year}")
        print(f"{'='*80}\n")

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        try:
            wind_gust_daily_era5_flow(
                start_date=start_date,
                end_date=end_date,
                skip_existing=True
            )
            print(f"✓ Year {year} completed")
        except Exception as e:
            print(f"✗ Year {year} failed: {e}")
            import traceback
            traceback.print_exc()
            # Continue with next year
            continue

    # Consolidate into climatology
    consolidate_climatology()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print()
    print("Climatology file: /mnt/workwork/climatology_data/wind_gust/daily/")
    print("  - wind_gust_1991-2020.nc")
    print()
    print("Operational data: /mnt/workwork/geoserver_data/")
    print("  - wind_speed/ (2014-2025 GeoTIFFs)")
    print("  - wind_gust_hist/ (2014-2025 yearly NetCDFs)")
    print("="*80)


if __name__ == "__main__":
    main()
