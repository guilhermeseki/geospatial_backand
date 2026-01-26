"""
GLM Daily Update Flow Runner
Processes recent GLM lightning data with automatic historical NetCDF updates.
Only processes dates from April 15, 2025 onwards (GOES-19 operational date).
"""
from datetime import date, timedelta
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("GLM DAILY UPDATE")
    logger.info("=" * 80)

    # GOES-19 became operational on April 15, 2025
    operational_date = date(2025, 4, 15)
    start_date = operational_date
    # GLM has 1-2 day lag
    end_date = date.today() - timedelta(days=2)

    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info("Checks: From GOES-19 operational (April 15, 2025) to yesterday")
    logger.info("Updates: GeoTIFF mosaics + historical NetCDF")
    logger.info("Clips: Brazil shapefile polygon")
    logger.info("Data lag: 1-2 days")
    logger.info("=" * 80)

    result = glm_fed_flow(
        start_date=start_date,
        end_date=end_date
    )

    if result:
        logger.info(f"✓ Processed {len(result)} new GLM files")
    else:
        logger.info("✓ No new GLM files needed (all up to date)")

    logger.info("=" * 80)
