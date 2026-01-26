"""
Process MODIS NDVI data for 2025 ONLY (quick priority run)
"""
from datetime import date
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("PROCESSING MODIS NDVI FOR 2025 ONLY")
logger.info("=" * 80)

# Process 2025 (current year - highest priority)
result = ndvi_data_flow(
    batch_days=16,
    sources=['modis'],
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 31)
)

logger.info(f"\n✓ Completed 2025: {len(result)} files processed")
logger.info("=" * 80)
