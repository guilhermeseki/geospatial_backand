#!/usr/bin/env python3
"""
Rebuild all historical wind data with correct ERA5 wind GUST data.

This script:
1. Removes all existing wind_speed GeoTIFFs (they were built from incorrect data)
2. Downloads ERA5 wind gust data year by year (2015-2024)
3. Creates daily maximum wind gust GeoTIFFs for insurance risk assessment

FINAL CORRECT APPROACH:
- Dataset: derived-era5-single-levels-daily-statistics
- Variable: 10m_wind_gust_since_previous_post_processing (MAXIMUM gust, not instantaneous!)
- Statistic: daily_maximum (pre-computed from 24 hourly maxima)
- Output: Daily max wind gust in km/h
"""
import sys
from pathlib import Path
from datetime import date
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.workflows.data_processing.era5_wind_gust_daily_stats_flow import era5_wind_gust_daily_stats_flow

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/rebuild_wind_gust_final.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Rebuild all wind gust historical data."""

    logger.info("="*80)
    logger.info("REBUILDING WIND GUST HISTORICAL DATA - FINAL CORRECT VERSION")
    logger.info("="*80)
    logger.info("Dataset: derived-era5-single-levels-daily-statistics")
    logger.info("Variable: 10m_wind_gust_since_previous_post_processing")
    logger.info("  (MAXIMUM gust over each hour, not instantaneous snapshot!)")
    logger.info("Statistic: Daily maximum (pre-computed from 24 hourly maxima)")
    logger.info("Years: 2015-2024")
    logger.info("="*80)
    logger.info("")

    # Process year by year to avoid large downloads
    years = list(range(2015, 2025))  # 2015-2024

    total_files = 0
    failed_years = []

    for year in years:
        logger.info(f"\n{'='*80}")
        logger.info(f"PROCESSING YEAR {year}")
        logger.info(f"{'='*80}")

        try:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

            # Run the flow for this year
            result = era5_wind_gust_daily_stats_flow(
                start_date=start_date,
                end_date=end_date,
                skip_existing=True  # Skip already downloaded files
            )

            if result:
                total_files += len(result)
                logger.info(f"✓ Year {year}: Created {len(result)} files")
            else:
                logger.info(f"✓ Year {year}: All files already exist")

        except Exception as e:
            logger.error(f"✗ Year {year} FAILED: {e}")
            failed_years.append(year)
            # Continue with next year instead of stopping
            continue

    logger.info(f"\n{'='*80}")
    logger.info("REBUILD COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Total files created: {total_files}")

    if failed_years:
        logger.warning(f"Failed years: {failed_years}")
        logger.warning("You may need to retry these years manually")
        return 1
    else:
        logger.info("✓ All years processed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Verify a few dates with test_era5_wind_gust_daily_stats.py")
        logger.info("2. Build historical NetCDF (if needed)")
        logger.info("3. Update GeoServer to use new wind_speed layer")
        logger.info("4. Restart the API to load new data")
        return 0

if __name__ == "__main__":
    sys.exit(main())
