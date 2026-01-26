#!/usr/bin/env python3
"""
Daily Precipitation Data Update Script
Checks for new CHIRPS and MERGE data and updates automatically.

CHIRPS: Checks ONLY previous month (monthly release, 5-7 day lag)
MERGE: Checks ONLY last 30 days (daily release, 1-2 day lag)

Run daily via systemd timer or cron: 0 2 * * *
"""
from app.workflows.data_processing.precipitation_flow import (
    chirps_daily_flow,
    merge_daily_flow
)
from datetime import date
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def update_precipitation():
    """Update both CHIRPS and MERGE precipitation data."""

    today = date.today()

    logger.info("="*80)
    logger.info("PRECIPITATION DATA DAILY UPDATE")
    logger.info("="*80)
    logger.info(f"Date: {today}")
    logger.info("="*80)

    # ========================================
    # MERGE - Checks last 30 days
    # ========================================
    logger.info("\n--- MERGE (Daily data, 1-2 day lag) ---")
    logger.info("Checking last 30 days for missing data...")

    try:
        merge_results = merge_daily_flow()

        if merge_results:
            logger.info(f"✓ MERGE: Updated {len(merge_results)} new files")
        else:
            logger.info("✓ MERGE: Already up to date (no new data)")

    except Exception as e:
        logger.error(f"✗ MERGE failed: {e}")
        import traceback
        traceback.print_exc()

    # ========================================
    # CHIRPS - Checks previous month only
    # ========================================
    logger.info("\n--- CHIRPS (Monthly data, 5-7 day lag) ---")
    logger.info("Checking previous month for missing data...")

    try:
        chirps_results = chirps_daily_flow()

        if chirps_results:
            logger.info(f"✓ CHIRPS: Updated {len(chirps_results)} new files")
        else:
            logger.info("✓ CHIRPS: Already up to date (no new data)")

    except Exception as e:
        logger.error(f"✗ CHIRPS failed: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\n" + "="*80)
    logger.info("PRECIPITATION UPDATE COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    update_precipitation()
