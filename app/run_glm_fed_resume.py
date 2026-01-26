#!/usr/bin/env python3
"""
Resume GLM FED processing from 2025-04-15 to 2025-11-21
With improved error handling - continues even if historical NetCDF append fails
"""
from datetime import date
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

# Setup logging
log_file = 'logs/glm_fed_backfill_resume.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),  # Append mode to resume
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Resume GLM FED backfill"""

    # Target range: April 15, 2025 to November 21, 2025
    start_date = date(2025, 4, 15)
    end_date = date(2025, 11, 21)

    logger.info("")
    logger.info("=" * 80)
    logger.info("GLM FED BACKFILL PROCESSING - RESUME")
    logger.info("=" * 80)
    logger.info(f"Target range: {start_date} to {end_date}")
    logger.info(f"Total days in range: {(end_date - start_date).days + 1}")
    logger.info("")
    logger.info("Improvements in this run:")
    logger.info("  - Historical NetCDF append failures are logged but won't stop processing")
    logger.info("  - GeoTIFF creation is the priority (critical for GeoServer)")
    logger.info("  - Progress counter shows N/M dates remaining")
    logger.info("=" * 80)
    logger.info("")

    # Run the flow
    try:
        result = glm_fed_flow(start_date=start_date, end_date=end_date)

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"✓ Processing complete!")
        logger.info(f"  Successfully processed: {len(result)} dates")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.info("\n⚠ Processing interrupted by user")
        logger.info("You can resume by running this script again - it will skip completed dates")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Processing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("\nYou can resume by running this script again - it will skip completed dates")
        sys.exit(1)

if __name__ == "__main__":
    main()
