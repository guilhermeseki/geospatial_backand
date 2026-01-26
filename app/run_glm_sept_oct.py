#!/usr/bin/env python3
"""Process GLM FED for Sept-Oct dates (2025-09-13 to 2025-10-31)"""
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
        logging.FileHandler('logs/glm_sept_oct.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    start_date = date(2025, 9, 13)
    end_date = date(2025, 10, 31)

    logger.info("="*80)
    logger.info(f"GLM FED - SEPT-OCT PROCESSING ({start_date} to {end_date})")
    logger.info("="*80)

    try:
        result = glm_fed_flow(start_date=start_date, end_date=end_date)
        logger.info(f"✓ Completed {len(result)} dates")
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
