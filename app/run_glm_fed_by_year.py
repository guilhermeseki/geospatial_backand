#!/usr/bin/env python3
"""
Download GLM FED data by year
More manageable than full backfill
"""
from datetime import date, timedelta
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/glm_fed_year_{date.today().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def download_year(year: int):
    """Download GLM FED data for a specific year"""

    start_date = date(year, 1, 1)

    # For current year, stop 3 days ago (data lag)
    if year == date.today().year:
        end_date = date.today() - timedelta(days=3)
    else:
        end_date = date(year, 12, 31)

    total_days = (end_date - start_date).days + 1

    logger.info("=" * 80)
    logger.info(f"GLM FED DATA DOWNLOAD - YEAR {year}")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Total days: {total_days}")
    logger.info(f"Estimated download: ~{total_days * 3}GB")
    logger.info(f"Estimated time: {total_days * 7 / 60:.1f} hours")
    logger.info("=" * 80)
    logger.info("")

    try:
        result = glm_fed_flow(start_date=start_date, end_date=end_date)

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"✓ Year {year} complete!")
        logger.info(f"  Processed {len(result)} file(s)")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"✗ Year {year} failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Download GLM FED data year by year"""

    # Years to download
    start_year = 2020
    end_year = 2025  # Current year

    logger.info("=" * 80)
    logger.info("GLM FED YEAR-BY-YEAR DOWNLOAD")
    logger.info("=" * 80)
    logger.info(f"Years: {start_year} to {end_year}")
    logger.info("")
    logger.info("This script downloads one year at a time.")
    logger.info("You can stop and resume at any time.")
    logger.info("=" * 80)
    logger.info("")

    # Process each year
    success_count = 0
    failed_years = []

    for year in range(start_year, end_year + 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Starting year {year}...")
        logger.info(f"{'=' * 80}\n")

        if download_year(year):
            success_count += 1
        else:
            failed_years.append(year)

        logger.info(f"\n✓ Completed {success_count} year(s) so far\n")

    # Final summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Successfully processed: {success_count} year(s)")

    if failed_years:
        logger.info(f"Failed years: {failed_years}")
    else:
        logger.info("All years processed successfully!")

    logger.info("=" * 80)
    logger.info("")
    logger.info("NEXT STEPS:")
    logger.info("1. Setup GeoServer layer: python geoserver/setup_glm_fed_layer.py")
    logger.info("2. Enable time dimension: python geoserver/enable_time_glm_fed.py")
    logger.info("3. Restart FastAPI server")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
