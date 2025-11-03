#!/usr/bin/env python3
"""
Backfill GLM FED data from 2020 to present
Downloads and processes GOES GLM Flash Extent Density data
"""
from datetime import date, timedelta
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workflows.data_processing.glm_fed_flow import glm_fed_flow

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/glm_fed_backfill_{date.today().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run GLM FED backfill from 2020 to present"""

    # Date range: 2020-01-01 to 3 days ago (account for data lag)
    start_date = date(2020, 1, 1)
    end_date = date.today() - timedelta(days=3)  # 3-day lag for GLM data

    total_days = (end_date - start_date).days + 1

    logger.info("=" * 80)
    logger.info("GLM FED DATA BACKFILL")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Total days: {total_days}")
    logger.info("")
    logger.info("REQUIREMENTS:")
    logger.info("1. NASA Earthdata account (https://urs.earthdata.nasa.gov/)")
    logger.info("2. Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD environment variables")
    logger.info("   OR create ~/.netrc with:")
    logger.info("   machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD")
    logger.info("")
    logger.info("ESTIMATED TIME:")
    logger.info(f"- {total_days} days to process")
    logger.info("- ~1440 files per day (~2-4GB download per day)")
    logger.info(f"- Total download: ~{total_days * 3}GB")
    logger.info("- Processing time: ~5-10 minutes per day")
    logger.info(f"- Total estimated time: {total_days * 7 / 60:.1f} hours")
    logger.info("")
    logger.info("NOTE: This is a long-running process. Consider running in screen/tmux.")
    logger.info("=" * 80)
    logger.info("")

    # Confirm before starting
    response = input("Do you want to proceed with the backfill? (yes/no): ")
    if response.lower() != 'yes':
        logger.info("Backfill cancelled by user")
        return

    logger.info("")
    logger.info("Starting backfill...")
    logger.info("")

    # Run the flow
    try:
        result = glm_fed_flow(start_date=start_date, end_date=end_date)

        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ BACKFILL COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"  Processed {len(result)} file(s)")
        logger.info(f"  Date range: {start_date} to {end_date}")
        logger.info("=" * 80)
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("1. Setup GeoServer layer:")
        logger.info("   python geoserver/setup_glm_fed_layer.py")
        logger.info("")
        logger.info("2. Enable time dimension:")
        logger.info("   python geoserver/enable_time_glm_fed.py")
        logger.info("")
        logger.info("3. Restart FastAPI to load historical data:")
        logger.info("   python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload")
        logger.info("")
        logger.info("4. Test API endpoints:")
        logger.info("   python /tmp/test_lightning_api.py")
        logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.info("\n⚠ Backfill interrupted by user")
        logger.info("Partial data has been saved. You can resume by running this script again.")
        logger.info("The flow will skip already processed dates.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Backfill failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
