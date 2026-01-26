"""
Process GLM FED data for full year 2025
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
logger.info("PROCESSING GLM FED FOR 2025")
logger.info("=" * 80)

# Process full year 2025 - it will skip existing dates automatically
result = glm_fed_flow(
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 31)
)

logger.info(f"\n✓ Completed 2025: {len(result)} files processed")
logger.info("=" * 80)
