#!/usr/bin/env python3
"""
Backfill GLM FED data from 2020 to present
Downloads and processes GOES GLM Flash Extent Density data
"""
from datetime import date, timedelta
import logging
import sys
from pathlib import Path
import argparse

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
        logging.FileHandler(f'logs/glm_fed_backfill_{date.today().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run GLM FED backfill - GOES-19 period (2025 onwards)"""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Backfill GLM FED data for GOES-19')
    parser.add_argument('--rolling-step-minutes', type=int, default=10,
                        help='Rolling window step size in minutes (default: 10)')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Skip confirmation prompt')
    args = parser.parse_args()

    # Date range: 2025-04-15 to 3 days ago (GOES-19 L3 data available from Apr 15)
    start_date = date(2025, 4, 15)  # GOES-19 L3 data starts Apr 15, 2025
    end_date = date.today() - timedelta(days=3)  # 3-day lag for GLM data

    total_days = (end_date - start_date).days + 1

    logger.info("=" * 80)
    logger.info("GLM FED DATA BACKFILL - GOES-19 PERIOD")
    logger.info("=" * 80)
    logger.info(f"Satellite: GOES-19 (GOES-East)")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Total days: {total_days}")
    logger.info(f"Rolling window step: Every {args.rolling_step_minutes} minutes")
    logger.info(f"Windows per day: {1440 // args.rolling_step_minutes}")
    logger.info("")
    logger.info("REQUIREMENTS:")
    logger.info("1. NASA Earthdata account (https://urs.earthdata.nasa.gov/)")
    logger.info("2. Credentials configured in ~/.netrc ✓")
    logger.info("")
    logger.info("DOWNLOAD ESTIMATES:")
    logger.info(f"- Days to process: {total_days}")
    logger.info(f"- Files per day: ~1,469 (29 min prev day + 1440 min target day)")
    logger.info(f"- Download per day: ~3 GB")
    logger.info(f"- Total download: ~{total_days * 3} GB (~{total_days * 3 / 1024:.1f} TB)")
    logger.info(f"- Processing time: ~30-35 min/day")
    logger.info(f"- Total time: ~{total_days * 32 / 60:.1f} hours (~{total_days * 32 / 60 / 24:.1f} days)")
    logger.info("")
    logger.info("AGGREGATION:")
    logger.info("- 30-minute rolling windows crossing midnight boundaries")
    logger.info(f"- Window calculation every {args.rolling_step_minutes} minutes")
    logger.info("- Stores MAXIMUM 30-min window per day + timestamp")
    logger.info(f"- Final storage: ~{total_days * 0.76 * 2 / 1024:.2f} GB (99.95% space savings)")
    logger.info("")
    logger.info("NOTE: This is a long-running process. Consider running in screen/tmux.")
    logger.info("=" * 80)
    logger.info("")

    # Confirm before starting
    if not args.yes:
        response = input("Do you want to proceed with the backfill? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Backfill cancelled by user")
            return

    logger.info("")
    logger.info("Starting backfill...")
    logger.info("")

    # Run the flow
    try:
        result = glm_fed_flow(
            start_date=start_date,
            end_date=end_date,
            rolling_step_minutes=args.rolling_step_minutes
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ BACKFILL COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"  Processed {len(result)} file(s)")
        logger.info(f"  Date range: {start_date} to {end_date}")
        logger.info("=" * 80)
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("1. Setup GeoServer layer:")
        logger.info("   python geoserver/setup_glm_fed_layer.py")
        logger.info("")
        logger.info("2. Enable time dimension:")
        logger.info("   python geoserver/enable_time_glm_fed.py")
        logger.info("")
        logger.info("3. Restart FastAPI to load historical data:")
        logger.info("   python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload")
        logger.info("")
        logger.info("4. Test API endpoints:")
        logger.info("   python /tmp/test_lightning_api.py")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.info("\n⚠ Backfill interrupted by user")
        logger.info("Partial data has been saved. You can resume by running this script again.")
        logger.info("The flow will skip already processed dates.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Backfill failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
