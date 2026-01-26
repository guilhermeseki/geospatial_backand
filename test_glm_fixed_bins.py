"""
Test the new GLM FED flow with fixed 30-minute bins
"""
from datetime import date
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Test with a recent date that should have data
test_date = date(2025, 7, 30)  # We know this date exists

logger.info("=" * 80)
logger.info("TESTING GLM FED WITH FIXED 30-MINUTE BINS")
logger.info("=" * 80)
logger.info(f"Test date: {test_date}")
logger.info("Expected: Fixed bins at 00:00, 00:30, 01:00, ..., 23:30 UTC")
logger.info("=" * 80)

result = glm_fed_flow(
    start_date=test_date,
    end_date=test_date
)

if result:
    logger.info(f"\n✓ Test SUCCESS: Processed {len(result)} files")
    logger.info("Check the log above to verify:")
    logger.info("  - 'Resampling to fixed 30-minute bins'")
    logger.info("  - 'Created XX fixed 30-minute bins'")
    logger.info("  - Bins should be ~48 per day (00:00 to 23:30)")
else:
    logger.error(f"\n✗ Test FAILED")

logger.info("=" * 80)
