"""
CHIRPS Daily Update Flow Runner
Processes recent CHIRPS precipitation data with automatic historical NetCDF updates.
Checks last 30 days for missing files.
"""
from app.workflows.data_processing.precipitation_flow import chirps_daily_flow
from app.workflows.data_processing.schemas import DataSource
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("CHIRPS DAILY UPDATE")
    logger.info("=" * 80)
    logger.info("Checks: Last 30 days for missing files")
    logger.info("Updates: GeoTIFF mosaics + historical NetCDF")
    logger.info("Clips: Brazil shapefile polygon")
    logger.info("=" * 80)

    from datetime import date, timedelta

    # Define date range
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)

    result = chirps_daily_flow(
        source=DataSource.CHIRPS,
        start_date=start_date,
        end_date=end_date
    )

    if result:
        logger.info(f"✓ Processed {len(result)} new CHIRPS files")
    else:
        logger.info("✓ No new CHIRPS files needed (all up to date)")

    logger.info("=" * 80)
