#!/usr/bin/env python3
"""
Operational MERGE data update script with comprehensive logging and error handling.
Designed to run daily via systemd timer or cron.
"""
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from app.workflows.data_processing.precipitation_flow import merge_daily_flow
from app.config.settings import get_settings

# Setup logging
settings = get_settings()
log_dir = Path("/opt/geospatial_backend/logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"merge_operational_{datetime.now().strftime('%Y%m')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_recent_data_completeness(days_back=7):
    """
    Verify that recent data exists for the last N days.
    Returns list of missing dates.
    """
    from datetime import date

    merge_dir = Path(settings.DATA_DIR) / "merge"
    missing_dates = []

    today = date.today()
    # Check last N days (accounting for 1-2 day lag)
    for i in range(2, days_back + 2):
        check_date = today - timedelta(days=i)
        expected_file = merge_dir / f"merge_{check_date.strftime('%Y%m%d')}.tif"

        if not expected_file.exists():
            missing_dates.append(check_date)
            logger.warning(f"Missing MERGE data for {check_date}")

    return missing_dates

def main():
    """Main execution with error handling and reporting"""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("MERGE OPERATIONAL UPDATE STARTED")
    logger.info(f"Run time: {start_time}")
    logger.info("=" * 80)

    try:
        # Pre-check: Verify recent data completeness
        logger.info("Pre-check: Verifying recent data completeness...")
        missing_dates = check_recent_data_completeness(days_back=7)

        if missing_dates:
            logger.warning(f"Found {len(missing_dates)} missing dates in last 7 days: {missing_dates}")
        else:
            logger.info("✓ All recent dates present (last 7 days)")

        # Run the daily flow (checks last 30 days)
        logger.info("Starting MERGE daily flow (checks last 30 days)...")
        result = merge_daily_flow()

        if result:
            logger.info(f"✓ Successfully processed {len(result)} new files")
            for path in result:
                logger.info(f"  - {path}")
        else:
            logger.info("✓ No new files to process (all up to date)")

        # Post-check: Verify recent data completeness again
        logger.info("Post-check: Verifying data completeness after update...")
        missing_dates_after = check_recent_data_completeness(days_back=7)

        if missing_dates_after:
            logger.error(f"⚠️  STILL MISSING {len(missing_dates_after)} dates after update: {missing_dates_after}")
            logger.error("This may indicate data source issues or download failures")
            # Don't exit with error - data might not be available yet
        else:
            logger.info("✓ All recent dates confirmed present")

        elapsed = datetime.now() - start_time
        logger.info("=" * 80)
        logger.info(f"MERGE OPERATIONAL UPDATE COMPLETED SUCCESSFULLY")
        logger.info(f"Total time: {elapsed}")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        elapsed = datetime.now() - start_time
        logger.error("=" * 80)
        logger.error(f"MERGE OPERATIONAL UPDATE FAILED")
        logger.error(f"Error: {str(e)}", exc_info=True)
        logger.error(f"Failed after: {elapsed}")
        logger.error("=" * 80)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
