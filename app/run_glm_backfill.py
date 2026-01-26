"""
GLM Full Backfill Script
Checks ALL dates from April 15, 2025 (GOES-19 operational) to yesterday and fills any gaps.
Run this ONCE before setting up operational daily updates.
"""
from datetime import date, timedelta
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow
from pathlib import Path
from app.config.settings import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("GLM FULL BACKFILL - ONE-TIME OPERATION")
    logger.info("=" * 80)

    # Check current state
    mosaic_dir = Path(settings.DATA_DIR) / "glm_fed"
    existing_files = list(mosaic_dir.glob("glm_fed_*.tif")) if mosaic_dir.exists() else []
    logger.info(f"Current files: {len(existing_files)}")

    if existing_files:
        dates = sorted([f.stem.split('_')[2] for f in existing_files])
        logger.info(f"Current range: {dates[0]} → {dates[-1]}")

    # GOES-19 became operational on April 15, 2025
    operational_date = date(2025, 4, 15)
    start_date = operational_date
    # GLM has 1-2 day lag
    end_date = date.today() - timedelta(days=2)

    logger.info("")
    logger.info("Backfill Configuration:")
    logger.info(f"  Start: {start_date} (GOES-19 operational)")
    logger.info(f"  End: {end_date} (2-day lag)")
    logger.info(f"  Total days to check: {(end_date - start_date).days + 1}")
    logger.info("")
    logger.info("Strategy:")
    logger.info("  - Skip existing files (fast)")
    logger.info("  - Download only missing dates")
    logger.info("  - Download 1440 minute files per day from NASA Earthdata")
    logger.info("  - Aggregate to daily Flash Extent Density (FED)")
    logger.info("  - Update GeoTIFF mosaics")
    logger.info("  - Update historical NetCDF")
    logger.info("  - Clip to Brazil shapefile")
    logger.info("=" * 80)
    logger.info("")

    result = glm_fed_flow(
        start_date=start_date,
        end_date=end_date
    )

    logger.info("")
    logger.info("=" * 80)
    if result:
        logger.info(f"✓ BACKFILL COMPLETE: Processed {len(result)} missing files")
    else:
        logger.info("✓ BACKFILL COMPLETE: All files already up to date")

    # Final count
    final_files = list(mosaic_dir.glob("glm_fed_*.tif")) if mosaic_dir.exists() else []
    logger.info(f"Total files after backfill: {len(final_files)}")

    expected_days = (end_date - start_date).days + 1
    logger.info(f"Expected files (if complete): ~{expected_days}")
    logger.info("=" * 80)
