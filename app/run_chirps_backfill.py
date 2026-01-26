"""
CHIRPS Full Backfill Script
Checks ALL dates from 2015-01-01 to yesterday and fills any gaps.
Run this ONCE before setting up operational daily updates.
"""
from app.workflows.data_processing.precipitation_flow import chirps_daily_flow
from app.workflows.data_processing.schemas import DataSource
from datetime import date, timedelta
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
    logger.info("CHIRPS FULL BACKFILL - ONE-TIME OPERATION")
    logger.info("=" * 80)

    # Check current state
    mosaic_dir = Path(settings.DATA_DIR) / "chirps"
    existing_files = list(mosaic_dir.glob("chirps_*.tif"))
    logger.info(f"Current files: {len(existing_files)}")

    if existing_files:
        dates = sorted([f.stem.split('_')[1] for f in existing_files])
        logger.info(f"Current range: {dates[0]} → {dates[-1]}")

    # Full backfill range
    start_date = date(2015, 1, 1)
    end_date = date.today() - timedelta(days=1)

    logger.info("")
    logger.info("Backfill Configuration:")
    logger.info(f"  Start: {start_date}")
    logger.info(f"  End: {end_date}")
    logger.info(f"  Total days to check: {(end_date - start_date).days + 1}")
    logger.info("")
    logger.info("Strategy:")
    logger.info("  - Skip existing files (fast)")
    logger.info("  - Download only missing dates")
    logger.info("  - Update GeoTIFF mosaics")
    logger.info("  - Update historical NetCDF")
    logger.info("  - Clip to Brazil shapefile")
    logger.info("=" * 80)
    logger.info("")

    result = chirps_daily_flow(
        source=DataSource.CHIRPS,
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
    final_files = list(mosaic_dir.glob("chirps_*.tif"))
    logger.info(f"Total files after backfill: {len(final_files)}")

    expected_days = (end_date - start_date).days + 1
    logger.info(f"Expected files (if complete): ~{expected_days}")
    logger.info("=" * 80)
