#!/usr/bin/env python3
"""Process GLM FED for April missing dates (2025-04-01 to 2025-04-14)"""
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
        logging.FileHandler('logs/glm_april.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    start_date = date(2025, 4, 1)
    end_date = date(2025, 4, 14)

    logger.info("="*80)
    logger.info(f"GLM FED - APRIL PROCESSING ({start_date} to {end_date})")
    logger.info("="*80)

    try:
        result = glm_fed_flow(start_date=start_date, end_date=end_date)
        logger.info(f"✓ Completed {len(result)} dates")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
