#!/usr/bin/env python3
"""
Simple test script to download a single day of GLM FED data from NASA Earthdata.
This is a simplified version for testing the download process.
"""
import os
import sys
from pathlib import Path
from datetime import date, timedelta
import logging

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.glm_fed_flow import (
    check_earthdata_credentials,
    download_glm_fed_daily,
    get_satellite_for_date
)
from prefect import task

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Test downloading a single day of GLM FED data"""

    # Test date: 3 days ago to allow for data availability lag
    test_date = date.today() - timedelta(days=3)

    logger.info("=" * 80)
    logger.info("GLM FED SIMPLE DOWNLOAD TEST")
    logger.info("=" * 80)
    logger.info(f"Test date: {test_date}")
    logger.info(f"Satellite: GOES-{get_satellite_for_date(test_date).replace('G', '')}")
    logger.info("")

    # Check credentials
    logger.info("Checking NASA Earthdata credentials...")
    try:
        from app.config.settings import get_settings
        settings = get_settings()

        if settings.EARTHDATA_USERNAME and settings.EARTHDATA_PASSWORD:
            username = settings.EARTHDATA_USERNAME
            password = settings.EARTHDATA_PASSWORD
            logger.info(f"✓ Found credentials in .env file")
            logger.info(f"  Username: {username}")
        else:
            logger.error("✗ Credentials not found in settings")
            logger.error("  Make sure EARTHDATA_USERNAME and EARTHDATA_PASSWORD are in .env file")
            sys.exit(1)

    except Exception as e:
        logger.error(f"✗ Failed to load credentials: {e}")
        sys.exit(1)

    logger.info("")
    logger.info("DOWNLOAD DETAILS:")
    logger.info(f"- Source: NASA GHRC DAAC")
    logger.info(f"- Expected download size: ~3 GB (1440+ minute files)")
    logger.info(f"- Processing: 30-minute fixed bins")
    logger.info(f"- Output: Daily aggregate NetCDF")
    logger.info("")
    logger.info("Starting download...")
    logger.info("=" * 80)
    logger.info("")

    try:
        # Download and process
        # Note: We can't use @task decorator outside of flow context,
        # so we'll call the task function directly
        from app.workflows.data_processing.glm_fed_flow import download_glm_fed_daily

        result = download_glm_fed_daily.fn(
            target_date=test_date,
            username=username,
            password=password,
            rolling_step_minutes=10
        )

        if result:
            logger.info("")
            logger.info("=" * 80)
            logger.info("✓ DOWNLOAD AND PROCESSING COMPLETE!")
            logger.info("=" * 80)
            logger.info(f"  Output file: {result}")
            logger.info(f"  File size: {result.stat().st_size / 1024 / 1024:.2f} MB")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Process to GeoTIFF: process_glm_fed_to_geotiff()")
            logger.info("  2. Add to historical NetCDF: append_to_yearly_historical_fed()")
            logger.info("  3. Or run full flow: python app/run_glm_fed_test.py")
            logger.info("=" * 80)
        else:
            logger.warning("⚠ Download returned None - check logs above for errors")
            logger.warning("  Common issues:")
            logger.warning("  - Data not available for this date yet")
            logger.warning("  - Authentication failed")
            logger.warning("  - Network error")

    except KeyboardInterrupt:
        logger.info("\n⚠ Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Download failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
