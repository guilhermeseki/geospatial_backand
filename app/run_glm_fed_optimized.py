"""
Optimized GLM FED data processing:
1. Skip dates before GOES-19 operational (April 15, 2025)
2. Only download truly missing dates (no GeoTIFF exists)
"""
from datetime import date
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("OPTIMIZED GLM FED PROCESSING FOR 2025")
logger.info("=" * 80)
logger.info("Skipping dates before GOES-19 operational date (April 15, 2025)")
logger.info("Only downloading truly missing dates")
logger.info("=" * 80)

# GOES-19 became operational on April 15, 2025
# No point querying before this date
result = glm_fed_flow(
    start_date=date(2025, 4, 15),  # Start from GOES-19 operational date
    end_date=date(2025, 12, 31)
)

logger.info(f"\n✓ Completed: {len(result)} new files processed")
logger.info("=" * 80)
