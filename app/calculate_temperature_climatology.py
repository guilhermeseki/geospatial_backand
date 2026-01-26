"""
Calculate monthly temperature climatology (1991-2020) from daily ERA5-Land data.

This script:
1. Loads daily temp_max and temp_min data for 1991-2020 (30 years)
2. Calculates monthly averages for each month across all years
3. Creates 12 monthly climatology GeoTIFFs (January through December)
4. Creates a consolidated NetCDF file for fast queries

Output structure:
  /mnt/workwork/geoserver_data/temp_max_climatology/
    ├── temp_max_clim_month01.tif  (January climatology)
    ├── temp_max_clim_month02.tif  (February climatology)
    ├── ...
    └── temp_max_climatology_monthly.nc

  /mnt/workwork/geoserver_data/temp_min_climatology/
    ├── temp_min_clim_month01.tif
    ├── ...
    └── temp_min_climatology_monthly.nc
"""
import sys
from pathlib import Path
import xarray as xr
import numpy as np
from datetime import datetime
import rioxarray

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config.settings import get_settings


def calculate_monthly_climatology(
    variable: str,
    start_year: int = 1991,
    end_year: int = 2020,
    output_dir_suffix: str = "_climatology"
):
    """
    Calculate monthly climatology for a temperature variable.

    Args:
        variable: "temp_max" or "temp_min"
        start_year: Start year for climatology period (default: 1991)
        end_year: End year for climatology period (default: 2020)
        output_dir_suffix: Suffix for output directory (default: "_climatology")
    """
    settings = get_settings()

    print("=" * 80)
    print(f"CALCULATING MONTHLY CLIMATOLOGY FOR {variable.upper()}")
    print("=" * 80)
    print(f"Reference period: {start_year}-{end_year} ({end_year - start_year + 1} years)")
    print(f"Source: ERA5-Land daily data")
    print("=" * 80)

    # Input directory (yearly NetCDF files)
    input_dir = Path(settings.DATA_DIR) / f"{variable}_hist"

    # Output directory
    output_dir = Path(settings.DATA_DIR) / f"{variable}{output_dir_suffix}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nInput directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    # Check which years are available
    available_years = []
    for year in range(start_year, end_year + 1):
        year_file = input_dir / f"{variable}_{year}.nc"
        if year_file.exists():
            available_years.append(year)
        else:
            print(f"  WARNING: Missing data for {year}")

    if not available_years:
        raise FileNotFoundError(f"No data found in {input_dir} for years {start_year}-{end_year}")

    print(f"\nFound data for {len(available_years)} years: {min(available_years)}-{max(available_years)}")

    # Load all years
    print("\nLoading data...")
    datasets = []
    for year in available_years:
        year_file = input_dir / f"{variable}_{year}.nc"
        print(f"  Loading {year}...")
        ds = xr.open_dataset(year_file, chunks='auto')
        datasets.append(ds)

    # Concatenate all years along time dimension
    print("\nCombining all years...")
    combined = xr.concat(datasets, dim='time')

    # Get the data variable
    if variable not in combined.data_vars:
        raise ValueError(f"Variable '{variable}' not found in dataset. Available: {list(combined.data_vars)}")

    da = combined[variable]

    print(f"  Combined data shape: {da.shape}")
    print(f"  Time range: {da.time.values[0]} to {da.time.values[-1]}")

    # Determine coordinate names (could be x/y or lon/lat)
    if 'x' in da.coords:
        lon_coord, lat_coord = 'x', 'y'
    elif 'lon' in da.coords:
        lon_coord, lat_coord = 'lon', 'lat'
    else:
        lon_coord, lat_coord = 'longitude', 'latitude'

    print(f"  Spatial extent: {da[lon_coord].min().values:.2f} to {da[lon_coord].max().values:.2f} (lon)")
    print(f"                  {da[lat_coord].min().values:.2f} to {da[lat_coord].max().values:.2f} (lat)")

    # Calculate monthly climatology
    print("\nCalculating monthly climatology (this may take a few minutes)...")

    # Group by month and calculate mean
    monthly_clim = da.groupby('time.month').mean(dim='time')

    print("  Computing statistics...")
    monthly_clim = monthly_clim.compute()

    print(f"  ✓ Climatology calculated for {len(monthly_clim.month)} months")

    # Save as individual GeoTIFFs
    print("\nSaving monthly GeoTIFF files...")
    geotiff_paths = []

    for month_num in range(1, 13):
        month_data = monthly_clim.sel(month=month_num)

        # Ensure CRS is set
        if not month_data.rio.crs:
            month_data = month_data.rio.write_crs("EPSG:4326")

        # Generate output filename
        output_file = output_dir / f"{variable}_clim_month{month_num:02d}.tif"

        # Save as GeoTIFF
        month_data.rio.to_raster(output_file, compress='DEFLATE', tiled=True)
        geotiff_paths.append(output_file)

        # Calculate statistics for reporting
        mean_val = float(month_data.mean().values)
        min_val = float(month_data.min().values)
        max_val = float(month_data.max().values)

        month_name = datetime(2000, month_num, 1).strftime("%B")
        print(f"  ✓ Month {month_num:02d} ({month_name:>9}): {output_file.name}")
        print(f"      Mean: {mean_val:.2f}°C, Range: {min_val:.2f} to {max_val:.2f}°C")

    # Create consolidated NetCDF
    print("\nCreating consolidated NetCDF file...")
    netcdf_file = output_dir / f"{variable}_climatology_monthly.nc"

    # Create dataset with proper metadata
    ds_clim = xr.Dataset({
        variable: monthly_clim
    })

    # Add attributes
    ds_clim[variable].attrs['long_name'] = f"Monthly Climatology of {variable.replace('_', ' ').title()}"
    ds_clim[variable].attrs['source'] = 'ERA5-Land daily data'
    ds_clim[variable].attrs['reference_period'] = f'{start_year}-{end_year}'
    ds_clim[variable].attrs['units'] = '°C'
    ds_clim[variable].attrs['calculation'] = f'Mean of daily values for each month across {len(available_years)} years'

    # Add global attributes
    ds_clim.attrs['title'] = f'{variable} Monthly Climatology'
    ds_clim.attrs['reference_period'] = f'{start_year}-{end_year}'
    ds_clim.attrs['created'] = datetime.now().isoformat()
    ds_clim.attrs['years_used'] = f'{min(available_years)}-{max(available_years)}'
    ds_clim.attrs['n_years'] = len(available_years)

    # Determine spatial dimension names
    spatial_dims = [d for d in ds_clim.dims if d != 'month']
    lat_dim = [d for d in spatial_dims if 'lat' in d][0]
    lon_dim = [d for d in spatial_dims if 'lon' in d or 'x' in d][0]

    # Chunk for efficient access
    chunk_dict = {'month': 1, lat_dim: 100, lon_dim: 100}
    ds_clim = ds_clim.chunk(chunk_dict)

    # Save to NetCDF with compression
    encoding = {
        variable: {
            'zlib': True,
            'complevel': 5,
            'chunksizes': (1, min(100, ds_clim.dims[lat_dim]), min(100, ds_clim.dims[lon_dim]))
        }
    }

    ds_clim.to_netcdf(netcdf_file, encoding=encoding)

    file_size_mb = netcdf_file.stat().st_size / 1024 / 1024
    print(f"  ✓ NetCDF created: {netcdf_file}")
    print(f"    File size: {file_size_mb:.2f} MB")

    # Close datasets
    for ds in datasets:
        ds.close()
    combined.close()

    print("\n" + "=" * 80)
    print("✓ CLIMATOLOGY CALCULATION COMPLETE")
    print("=" * 80)
    print(f"Created {len(geotiff_paths)} monthly GeoTIFF files")
    print(f"Created consolidated NetCDF: {netcdf_file}")
    print(f"Reference period: {start_year}-{end_year} ({len(available_years)} years)")
    print("=" * 80)

    return {
        'variable': variable,
        'output_dir': output_dir,
        'geotiff_paths': geotiff_paths,
        'netcdf_file': netcdf_file,
        'reference_period': f'{start_year}-{end_year}',
        'n_years': len(available_years)
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Calculate monthly temperature climatology from daily ERA5-Land data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate temp_max climatology for 1991-2020 (default)
  python app/calculate_temperature_climatology.py --variable temp_max

  # Calculate temp_min climatology
  python app/calculate_temperature_climatology.py --variable temp_min

  # Calculate both temp_max and temp_min
  python app/calculate_temperature_climatology.py --all

  # Use different reference period
  python app/calculate_temperature_climatology.py --variable temp_max --start-year 2000 --end-year 2020
        """
    )

    parser.add_argument(
        "--variable",
        type=str,
        choices=["temp_max", "temp_min"],
        help="Temperature variable to process"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Calculate climatology for both temp_max and temp_min"
    )

    parser.add_argument(
        "--start-year",
        type=int,
        default=1991,
        help="Start year for climatology period (default: 1991)"
    )

    parser.add_argument(
        "--end-year",
        type=int,
        default=2020,
        help="End year for climatology period (default: 2020)"
    )

    args = parser.parse_args()

    # Determine which variables to process
    if args.all:
        variables = ["temp_max", "temp_min"]
    elif args.variable:
        variables = [args.variable]
    else:
        parser.error("Must specify either --variable or --all")

    print(f"Processing {len(variables)} variable(s): {', '.join(variables)}")
    print(f"Reference period: {args.start_year}-{args.end_year}")
    print()

    results = []
    for variable in variables:
        try:
            result = calculate_monthly_climatology(
                variable=variable,
                start_year=args.start_year,
                end_year=args.end_year
            )
            results.append(result)
            print()
        except Exception as e:
            print(f"\n✗ ERROR processing {variable}: {e}")
            raise

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for result in results:
        print(f"\n{result['variable'].upper()}:")
        print(f"  Output directory: {result['output_dir']}")
        print(f"  NetCDF file: {result['netcdf_file']}")
        print(f"  Reference period: {result['reference_period']} ({result['n_years']} years)")
        print(f"  Monthly GeoTIFFs: {len(result['geotiff_paths'])}")
    print("=" * 80)


if __name__ == "__main__":
    main()
