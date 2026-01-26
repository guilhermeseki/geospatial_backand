"""
MERGE Daily Update Flow Runner
Processes recent MERGE precipitation data with automatic historical NetCDF updates.
Checks last 30 days for missing files.
"""
from app.workflows.data_processing.precipitation_flow import merge_daily_flow
from app.workflows.data_processing.schemas import DataSource
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("MERGE DAILY UPDATE")
    logger.info("=" * 80)
    logger.info("Checks: Last 30 days for missing files")
    logger.info("Updates: GeoTIFF mosaics + historical NetCDF")
    logger.info("Clips: Brazil shapefile polygon")
    logger.info("=" * 80)

    result = merge_daily_flow(source=DataSource.MERGE)

    if result:
        logger.info(f"✓ Processed {len(result)} new MERGE files")
    else:
        logger.info("✓ No new MERGE files needed (all up to date)")

    logger.info("=" * 80)
