#!/usr/bin/env python3
"""
Test GLM FED flow with a short date range (3 days)
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Test GLM FED flow with 3 days"""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test GLM FED flow with 3 days')
    parser.add_argument('--rolling-step-minutes', type=int, default=10,
                        help='Rolling window step size in minutes (default: 10). '
                             'With 30-minute windows: step=1 gives 1440 windows/day, '
                             'step=10 gives 144 windows/day')
    args = parser.parse_args()

    # Test with 3 recent days (allowing 3-day lag for data availability)
    end_date = date.today() - timedelta(days=3)
    start_date = end_date - timedelta(days=2)  # 3 days total

    logger.info("=" * 80)
    logger.info("GLM FED TEST RUN - 3 DAYS")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Total days: {(end_date - start_date).days + 1}")
    logger.info(f"Rolling window step: Every {args.rolling_step_minutes} minutes")
    logger.info(f"Expected windows per day: {1440 // args.rolling_step_minutes}")
    logger.info("")
    logger.info("ESTIMATES FOR TEST:")
    logger.info(f"- Download: ~9 GB (3 GB per day × 3 days)")
    logger.info(f"- Processing time: ~15-30 minutes (with {args.rolling_step_minutes}-minute steps)")
    logger.info(f"- Final storage: ~4.5 MB (GeoTIFFs + NetCDF)")
    logger.info("")
    logger.info("REQUIREMENTS:")
    logger.info("- NASA Earthdata credentials in ~/.netrc")
    logger.info("=" * 80)
    logger.info("")

    try:
        result = glm_fed_flow(
            start_date=start_date,
            end_date=end_date,
            rolling_step_minutes=args.rolling_step_minutes
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ TEST RUN COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"  Processed {len(result)} file(s)")
        logger.info(f"  Date range: {start_date} to {end_date}")
        logger.info("")

        if len(result) > 0:
            logger.info("✓ Test successful! You can now run the full backfill:")
            logger.info("  python app/run_glm_fed_backfill.py")
        else:
            logger.warning("⚠ No files processed - check logs above")

        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.info("\n⚠ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
