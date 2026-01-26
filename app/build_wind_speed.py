#!/usr/bin/env python3
"""
Calculate wind speed from u and v components.
Wind speed = sqrt(u² + v²)

This script processes daily GeoTIFF files to create wind speed mosaics.
"""
from pathlib import Path
from datetime import date, timedelta
import numpy as np
import rasterio
from rasterio.crs import CRS
from app.config.settings import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_wind_speed_for_date(day_date: date, settings) -> bool:
    """
    Calculate wind speed from u and v components for a specific date.

    Returns True if successful, False otherwise.
    """
    data_dir = Path(settings.DATA_DIR)

    # Input files
    u_file = data_dir / "wind_u_max" / f"wind_u_max_{day_date.strftime('%Y%m%d')}.tif"
    v_file = data_dir / "wind_v_max" / f"wind_v_max_{day_date.strftime('%Y%m%d')}.tif"

    # Output file
    output_dir = data_dir / "wind_speed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"wind_speed_{day_date.strftime('%Y%m%d')}.tif"

    # Skip if already exists
    if output_file.exists():
        logger.debug(f"Wind speed already exists for {day_date}, skipping")
        return True

    # Check if both input files exist
    if not u_file.exists() or not v_file.exists():
        logger.warning(f"Missing input files for {day_date}")
        return False

    try:
        # Read u component
        with rasterio.open(u_file) as u_src:
            u_data = u_src.read(1).astype(np.float32)
            profile = u_src.profile.copy()

        # Read v component
        with rasterio.open(v_file) as v_src:
            v_data = v_src.read(1).astype(np.float32)

        # Calculate wind speed: sqrt(u² + v²)
        wind_speed = np.sqrt(u_data**2 + v_data**2)

        # Convert from m/s to km/h (multiply by 3.6)
        wind_speed = wind_speed * 3.6

        # Handle nodata values
        nodata = profile.get('nodata', -9999.0)
        if nodata is not None:
            mask = (u_data == nodata) | (v_data == nodata)
            wind_speed[mask] = nodata

        # Update profile for output
        profile.update(
            dtype=rasterio.float32,
            driver='COG',
            compress='LZW',
            nodata=nodata
        )

        # Write wind speed to file
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(wind_speed.astype(rasterio.float32), 1)

        logger.info(f"✓ Created wind speed for {day_date}: {output_file.name}")
        return True

    except Exception as e:
        logger.error(f"✗ Failed to process {day_date}: {e}")
        if output_file.exists():
            output_file.unlink()  # Clean up partial file
        return False


def build_wind_speed_mosaics(start_date: date = None, end_date: date = None):
    """
    Build wind speed GeoTIFF files from u and v components.

    Args:
        start_date: Start date (default: first date with u/v files)
        end_date: End date (default: last date with u/v files)
    """
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)

    # Get all available dates from u component files
    u_dir = data_dir / "wind_u_max"
    u_files = sorted(u_dir.glob("wind_u_max_*.tif"))

    if not u_files:
        logger.error("No wind u component files found")
        return

    # Extract dates from filenames
    available_dates = []
    for u_file in u_files:
        try:
            date_str = u_file.stem.split('_')[-1]
            file_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
            available_dates.append(file_date)
        except (ValueError, IndexError):
            logger.warning(f"Could not parse date from {u_file.name}")
            continue

    if not available_dates:
        logger.error("No valid dates found in wind files")
        return

    # Set date range
    if start_date is None:
        start_date = min(available_dates)
    if end_date is None:
        end_date = max(available_dates)

    logger.info("=" * 80)
    logger.info("WIND SPEED CALCULATION")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Available dates: {len(available_dates)}")
    logger.info(f"Formula: wind_speed = sqrt(u² + v²)")
    logger.info("=" * 80)

    # Process each date
    success_count = 0
    skip_count = 0
    fail_count = 0

    for file_date in available_dates:
        if file_date < start_date or file_date > end_date:
            continue

        result = calculate_wind_speed_for_date(file_date, settings)
        if result:
            success_count += 1
        else:
            fail_count += 1

    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Successfully processed: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info(f"Output directory: {data_dir / 'wind_speed'}")
    logger.info("=" * 80)


if __name__ == "__main__":
    import sys

    # Optional: Pass date range as command line arguments
    # python app/build_wind_speed.py [start_date] [end_date]
    # Dates in YYYY-MM-DD format

    start = None
    end = None

    if len(sys.argv) > 1:
        try:
            start = date.fromisoformat(sys.argv[1])
        except ValueError:
            print(f"Invalid start date: {sys.argv[1]}")
            sys.exit(1)

    if len(sys.argv) > 2:
        try:
            end = date.fromisoformat(sys.argv[2])
        except ValueError:
            print(f"Invalid end date: {sys.argv[2]}")
            sys.exit(1)

    build_wind_speed_mosaics(start, end)
