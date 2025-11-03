#!/usr/bin/env python3
"""
Run GLM FED data processing flow
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/glm_fed_processing.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run GLM FED processing flow"""

    # Default: process yesterday's data
    # GLM data available from 2018-01-01 (GOES-16 operational)
    yesterday = date.today() - timedelta(days=1)

    # For backfill, specify custom date range:
    # start_date = date(2020, 1, 1)
    # end_date = date(2020, 1, 31)

    logger.info("=" * 80)
    logger.info("GLM FED DATA PROCESSING")
    logger.info("=" * 80)
    logger.info("This will download and process GOES GLM Flash Extent Density data")
    logger.info("")
    logger.info("REQUIREMENTS:")
    logger.info("1. NASA Earthdata account (https://urs.earthdata.nasa.gov/)")
    logger.info("2. Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD environment variables")
    logger.info("   OR create ~/.netrc with:")
    logger.info("   machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD")
    logger.info("")
    logger.info("DATA DETAILS:")
    logger.info("- Source: NASA GHRC DAAC")
    logger.info("- Dataset: GLM Gridded Flash Extent Density")
    logger.info("- Satellite: GOES-16 (GOES-East)")
    logger.info("- Resolution: 8km × 8km")
    logger.info("- Temporal: Daily aggregation (1440 minute files → 1 daily file)")
    logger.info("- Available from: 2018-01-01 to present (with 2-3 day lag)")
    logger.info("=" * 80)
    logger.info("")

    # Run the flow
    try:
        # Process yesterday (default)
        result = glm_fed_flow(start_date=yesterday, end_date=yesterday)

        # For backfill of specific date range, uncomment:
        # result = glm_fed_flow(start_date=start_date, end_date=end_date)

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"✓ Processing complete!")
        logger.info(f"  Processed {len(result)} file(s)")
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
        logger.info("\n⚠ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Processing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
