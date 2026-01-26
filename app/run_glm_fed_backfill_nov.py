#!/usr/bin/env python3
"""
Run GLM FED backfill from 2025-06-03 to latest available
"""
from datetime import date, timedelta
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

# Setup logging
log_file = f'logs/glm_fed_backfill_{date.today().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run GLM FED backfill"""

    # Backfill from 2025-06-03 to latest available
    # GLM has 2-3 day lag, so latest is ~3 days ago
    start_date = date(2025, 6, 3)
    end_date = date.today() - timedelta(days=3)

    logger.info("=" * 80)
    logger.info("GLM FED BACKFILL PROCESSING")
    logger.info("=" * 80)
    logger.info(f"Start date: {start_date}")
    logger.info(f"End date: {end_date}")
    logger.info(f"Total days: {(end_date - start_date).days + 1}")
    logger.info("=" * 80)
    logger.info("")

    # Run the flow
    try:
        result = glm_fed_flow(start_date=start_date, end_date=end_date)

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"✓ Processing complete!")
        logger.info(f"  Processed {len(result)} days")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.info("\n⚠ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Processing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
