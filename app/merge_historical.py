#!/usr/bin/env python3
"""
Merge Raw ERA5 NetCDF Files to Yearly Historical Files

This script consolidates raw NetCDF files downloaded by era5_flow into yearly
historical NetCDF files for fast time-series queries.

Run after downloading data with skip_historical_merge=True to create the
yearly historical files without the FUSE filesystem issues.

Usage:
    python app/merge_historical.py --variable temp_max --year 2015
    python app/merge_historical.py --variable wind_u_max --year 2020
    python app/merge_historical.py --variable temp_max --all-years
"""
import argparse
import logging
from pathlib import Path
from datetime import date, datetime
import xarray as xr
import numpy as np
from typing import List, Optional
import shutil
import os

from app.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Variable name mapping (output_name -> original_variable)
VARIABLE_REVERSE_MAPPING = {
    "temp_max": ("2m_temperature", "daily_maximum"),
    "temp_min": ("2m_temperature", "daily_minimum"),
    "temp": ("2m_temperature", "daily_mean"),
    "wind_u": ("10m_u_component_of_wind", "daily_mean"),
    "wind_u_max": ("10m_u_component_of_wind", "daily_maximum"),
    "wind_u_min": ("10m_u_component_of_wind", "daily_minimum"),
    "wind_v": ("10m_v_component_of_wind", "daily_mean"),
    "wind_v_max": ("10m_v_component_of_wind", "daily_maximum"),
    "wind_v_min": ("10m_v_component_of_wind", "daily_minimum"),
}


def find_raw_files_for_variable(variable: str, year: Optional[int] = None) -> List[Path]:
    """
    Find all raw NetCDF files for a given variable and optionally a specific year.

    Args:
        variable: Output variable name (e.g., 'temp_max', 'wind_u_max')
        year: Optional year to filter by

    Returns:
        List of Path objects to raw NetCDF files
    """
    raw_dir = settings.DATA_DIR / "raw" / "era5_land_daily"

    if not raw_dir.exists():
        logger.error(f"Raw directory not found: {raw_dir}")
        return []

    if variable not in VARIABLE_REVERSE_MAPPING:
        logger.error(f"Unknown variable: {variable}")
        logger.info(f"Available variables: {list(VARIABLE_REVERSE_MAPPING.keys())}")
        return []

    original_var, statistic = VARIABLE_REVERSE_MAPPING[variable]

    # Build pattern to match files
    # Example: 2mtemperature_daily_maximum_20150101_20150131.nc
    var_pattern = original_var.replace("_", "").replace("m", "m")  # "2mtemperature" or "10mucomponentofwind"
    stat_pattern = statistic.replace("_", "")  # "dailymaximum"

    pattern = f"{var_pattern}_{statistic}_*.nc"

    all_files = sorted(raw_dir.glob(pattern))

    if year:
        # Filter files that contain dates from the specified year
        filtered_files = []
        for f in all_files:
            # Extract date range from filename
            # Example: 2mtemperature_daily_maximum_20150101_20150131.nc
            parts = f.stem.split('_')
            if len(parts) >= 4:
                start_date_str = parts[-2]  # "20150101"
                end_date_str = parts[-1]    # "20150131"

                try:
                    start_date = datetime.strptime(start_date_str, "%Y%m%d").date()
                    end_date = datetime.strptime(end_date_str, "%Y%m%d").date()

                    # Include if any part of the date range overlaps with target year
                    if start_date.year <= year <= end_date.year:
                        filtered_files.append(f)
                except ValueError:
                    continue

        return filtered_files

    return all_files


def merge_raw_files_to_yearly(
    variable: str,
    year: int,
    dry_run: bool = False
) -> Optional[Path]:
    """
    Merge raw NetCDF files for a variable and year into a yearly historical file.

    Args:
        variable: Output variable name (e.g., 'temp_max', 'wind_u_max')
        year: Year to process
        dry_run: If True, only show what would be done

    Returns:
        Path to created yearly file, or None if failed
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Merging {variable} for year {year}")

    # Find raw files
    raw_files = find_raw_files_for_variable(variable, year)

    if not raw_files:
        logger.warning(f"No raw files found for {variable} year {year}")
        return None

    logger.info(f"Found {len(raw_files)} raw files to process")

    if dry_run:
        for f in raw_files:
            logger.info(f"  Would process: {f.name}")
        return None

    # Load all datasets for this year
    datasets = []
    for raw_file in raw_files:
        try:
            ds = xr.open_dataset(raw_file)

            # Filter to only include dates from target year
            year_mask = ds.time.dt.year == year
            if year_mask.sum() > 0:
                ds_year = ds.sel(time=year_mask)
                datasets.append(ds_year)
                logger.info(f"  Loaded {len(ds_year.time)} dates from {raw_file.name}")
            else:
                ds.close()
        except Exception as e:
            logger.error(f"  Failed to load {raw_file.name}: {e}")
            continue

    if not datasets:
        logger.error(f"No valid datasets loaded for {variable} year {year}")
        return None

    # Concatenate all datasets along time dimension
    logger.info(f"Concatenating {len(datasets)} datasets...")
    try:
        combined_ds = xr.concat(datasets, dim='time')

        # Remove duplicates and sort by time
        combined_ds = combined_ds.drop_duplicates(dim='time')
        combined_ds = combined_ds.sortby('time')

        logger.info(f"Combined dataset has {len(combined_ds.time)} unique dates")

        # Prepare output directory and file
        hist_dir = settings.DATA_DIR / f"{variable}_hist"
        hist_dir.mkdir(parents=True, exist_ok=True)

        year_file = hist_dir / f"{year}.nc"
        temp_file = hist_dir / f".{year}.nc.tmp"

        # Check if file already exists
        if year_file.exists():
            logger.warning(f"Output file already exists: {year_file}")
            response = input("Overwrite? (y/n): ")
            if response.lower() != 'y':
                logger.info("Skipping...")
                return None

        # Define chunking for efficient queries
        encoding = {
            variable: {
                'dtype': 'float32',
                'zlib': True,
                'complevel': 4,
                'chunksizes': (1, 20, 20)  # time=1, lat=20, lon=20
            }
        }

        # Write to temp file first
        logger.info(f"Writing to temporary file: {temp_file}")
        combined_ds.to_netcdf(str(temp_file), mode='w', encoding=encoding, engine='netcdf4')
        os.sync()

        logger.info(f"Moving to final location: {year_file}")
        shutil.move(str(temp_file), str(year_file))
        os.sync()

        logger.info(f"✓ Successfully created {year_file}")
        logger.info(f"  Contains {len(combined_ds.time)} dates from {combined_ds.time.values[0]} to {combined_ds.time.values[-1]}")

        # Check for nulls
        null_count = int(combined_ds[variable].isnull().sum().values)
        total_count = int(np.prod(combined_ds[variable].shape))
        null_pct = 100 * null_count / total_count if total_count > 0 else 0
        logger.info(f"  Null values: {null_count:,} / {total_count:,} ({null_pct:.1f}%)")

        # Clean up
        for ds in datasets:
            ds.close()
        combined_ds.close()

        return year_file

    except Exception as e:
        logger.error(f"Failed to merge datasets: {e}")
        import traceback
        traceback.print_exc()

        # Clean up
        for ds in datasets:
            try:
                ds.close()
            except:
                pass

        if temp_file.exists():
            temp_file.unlink()

        return None


def main():
    parser = argparse.ArgumentParser(
        description='Merge raw ERA5 NetCDF files to yearly historical files'
    )
    parser.add_argument(
        '--variable',
        required=True,
        choices=list(VARIABLE_REVERSE_MAPPING.keys()),
        help='Variable to process (e.g., temp_max, wind_u_max)'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Specific year to process (e.g., 2015)'
    )
    parser.add_argument(
        '--all-years',
        action='store_true',
        help='Process all years found in raw files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2015,
        help='Start year when using --all-years (default: 2015)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        help='End year when using --all-years (default: current year)'
    )

    args = parser.parse_args()

    if not args.year and not args.all_years:
        parser.error("Must specify either --year or --all-years")

    if args.year and args.all_years:
        parser.error("Cannot specify both --year and --all-years")

    logger.info("="*80)
    logger.info("ERA5 HISTORICAL MERGE SCRIPT")
    logger.info("="*80)
    logger.info(f"Variable: {args.variable}")

    if args.all_years:
        end_year = args.end_year or date.today().year
        years = range(args.start_year, end_year + 1)
        logger.info(f"Processing years: {args.start_year} to {end_year}")
    else:
        years = [args.year]
        logger.info(f"Processing year: {args.year}")

    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")

    logger.info("="*80)
    print()

    success_count = 0
    fail_count = 0

    for year in years:
        try:
            result = merge_raw_files_to_yearly(
                variable=args.variable,
                year=year,
                dry_run=args.dry_run
            )

            if result:
                success_count += 1
            else:
                fail_count += 1

        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Failed to process year {year}: {e}")
            fail_count += 1
            continue

    print()
    logger.info("="*80)
    logger.info("MERGE SUMMARY")
    logger.info("="*80)
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("="*80)


if __name__ == "__main__":
    main()
