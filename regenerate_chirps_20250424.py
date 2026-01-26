"""
Regenerate single CHIRPS file for 2025-04-24
"""
import sys
import logging
from datetime import datetime
from app.workflows.data_processing.tasks import (
    download_chirps_daily,
    process_chirps_daily_to_geotiff,
    append_to_historical_netcdf
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def regenerate_single_date():
    """Regenerate CHIRPS file for 2025-04-24"""
    target_date = datetime(2025, 4, 24)

    logger.info(f"Regenerating CHIRPS for {target_date.date()}")

    try:
        # Step 1: Download raw data
        logger.info("Step 1: Downloading raw CHIRPS data...")
        raw_path = download_chirps_daily(target_date)
        logger.info(f"Downloaded to: {raw_path}")

        # Step 2: Process to GeoTIFF
        logger.info("Step 2: Processing to GeoTIFF...")
        geotiff_path = process_chirps_daily_to_geotiff(raw_path, target_date)
        logger.info(f"Created GeoTIFF: {geotiff_path}")

        # Step 3: Append to historical NetCDF
        logger.info("Step 3: Appending to historical NetCDF...")
        append_to_historical_netcdf(
            raw_path=raw_path,
            dates_to_append=[target_date],
            source='chirps',
            variable_name='precip'
        )
        logger.info("Successfully appended to historical.nc")

        logger.info(f"✓ Successfully regenerated chirps_20250424.tif")
        return True

    except Exception as e:
        logger.error(f"Failed to regenerate: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = regenerate_single_date()
    sys.exit(0 if success else 1)
