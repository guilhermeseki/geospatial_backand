"""
Run CAMS Solar Radiation Flow - Download and Process GHI Data for Brazil

This script downloads CAMS gridded solar radiation data (Global Horizontal Irradiance)
from the Atmosphere Data Store and processes it into:
1. Daily GeoTIFF files for GeoServer time-enabled mosaics
2. Yearly historical NetCDF files for fast API queries

Data Source: CAMS gridded solar radiation
- Spatial Resolution: 0.1° (~11km)
- Temporal Resolution: 15-minute → aggregated to daily totals
- Coverage: Brazil (Eastern South America)
- Accuracy: 17.3% RMS, 4% bias (validated in Brazil)
- Period: 2005-present (updates yearly with ~6 month lag)

Usage:
    # Process entire last year
    python app/run_cams_solar.py

    # Process specific date range
    python app/run_cams_solar.py --start-date 2023-01-01 --end-date 2023-12-31

    # Process specific year
    python app/run_cams_solar.py --year 2023
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import argparse
import logging

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.workflows.data_processing.cams_solar_flow import cams_solar_flow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/cams_solar.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Download and process CAMS solar radiation data (GHI)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD). Default: First day of last year'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD). Default: Last day of last year'
    )

    parser.add_argument(
        '--year',
        type=int,
        help='Process entire year (e.g., 2023). Overrides start-date and end-date'
    )

    parser.add_argument(
        '--batch-months',
        type=int,
        default=1,
        help='Number of months to download per batch (default: 1)'
    )

    args = parser.parse_args()

    # Determine date range
    if args.year:
        start_date = date(args.year, 1, 1)
        end_date = date(args.year, 12, 31)
        logger.info(f"Processing entire year: {args.year}")
    else:
        if args.start_date:
            start_date = date.fromisoformat(args.start_date)
        else:
            # Default: first day of last year
            today = date.today()
            start_date = date(today.year - 1, 1, 1)

        if args.end_date:
            end_date = date.fromisoformat(args.end_date)
        else:
            # Default: last day of last year
            today = date.today()
            end_date = date(today.year - 1, 12, 31)

    logger.info("=" * 80)
    logger.info("CAMS Solar Radiation Flow")
    logger.info("=" * 80)
    logger.info(f"Start date: {start_date}")
    logger.info(f"End date: {end_date}")
    logger.info(f"Days to process: {(end_date - start_date).days + 1}")
    logger.info(f"Batch months: {args.batch_months}")
    logger.info("")
    logger.info("Data Source: CAMS gridded solar radiation")
    logger.info("  Variable: GHI (Global Horizontal Irradiance)")
    logger.info("  Resolution: 0.1° (~11km)")
    logger.info("  Accuracy: 17.3% RMS, 4% bias (validated in Brazil)")
    logger.info("  Coverage: Brazil (Eastern South America)")
    logger.info("=" * 80)
    logger.info("")

    # Run the flow
    try:
        result = cams_solar_flow(
            start_date=start_date,
            end_date=end_date,
            batch_months=args.batch_months
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("CAMS Solar Radiation Flow Completed")
        logger.info("=" * 80)
        logger.info(f"✓ Processed {len(result)} daily GeoTIFF files")
        logger.info(f"✓ Created/updated yearly historical NetCDF files")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Restart FastAPI app to load GHI data: systemctl restart fastapi")
        logger.info("2. Configure GeoServer mosaic for GHI layer (if needed)")
        logger.info("3. Test API endpoints: /solar/history?lat=-15.8&lon=-47.9")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("CAMS Solar Radiation Flow Failed")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    main()
