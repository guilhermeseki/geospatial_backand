#!/usr/bin/env python3
"""Process final 6 missing GLM FED dates (2025-04-01 to 2025-04-06)"""
from datetime import date
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/glm_final_6.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    start_date = date(2025, 4, 1)
    end_date = date(2025, 4, 6)

    logger.info("="*80)
    logger.info(f"GLM FED - FINAL 6 DATES ({start_date} to {end_date})")
    logger.info("="*80)

    try:
        result = glm_fed_flow(start_date=start_date, end_date=end_date)
        logger.info("="*80)
        logger.info(f"✓ COMPLETED ALL {len(result)} DATES!")
        logger.info("✓ GLM FED DATASET IS NOW COMPLETE!")
        logger.info("="*80)
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
