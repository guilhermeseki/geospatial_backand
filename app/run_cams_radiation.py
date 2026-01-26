"""
Run CAMS Global Radiation Flow - Satellite-Based Solar Radiation

Downloads CAMS global radiation data from the Atmosphere Data Store (ADS)
and processes it into GeoTIFF files and historical NetCDF.

Data Source: CAMS global radiation (satellite observations)
- Dataset: cams-global-radiation
- Resolution: 0.05° (~5.5 km)
- Period: 2004-present (~2-3 days lag)
- Accuracy: Better than ERA5 for solar applications

Usage:
    # Process last 30 days
    python app/run_cams_radiation.py --days 30

    # Process specific year
    python app/run_cams_radiation.py --year 2024

    # Process date range
    python app/run_cams_radiation.py --start-date 2024-01-01 --end-date 2024-12-31
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import argparse
import logging

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.workflows.data_processing.cams_radiation_flow import cams_radiation_flow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/cams_radiation.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Download and process CAMS global radiation data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--year',
        type=int,
        help='Process entire year (e.g., 2024). Overrides start/end dates'
    )

    parser.add_argument(
        '--days',
        type=int,
        help='Process last N days (e.g., 30). Overrides other date options'
    )

    parser.add_argument(
        '--batch-days',
        type=int,
        default=30,
        help='Number of days to download per batch (default: 30)'
    )

    args = parser.parse_args()

    # Determine date range
    if args.days:
        end_date = date.today() - timedelta(days=3)  # 3-day lag
        start_date = end_date - timedelta(days=args.days - 1)
        logger.info(f"Processing last {args.days} days")
    elif args.year:
        start_date = date(args.year, 1, 1)
        end_date = date(args.year, 12, 31)
        logger.info(f"Processing entire year: {args.year}")
    else:
        if args.start_date:
            start_date = date.fromisoformat(args.start_date)
        else:
            # Default: last 30 days
            end_date = date.today() - timedelta(days=3)
            start_date = end_date - timedelta(days=29)

        if args.end_date:
            end_date = date.fromisoformat(args.end_date)
        else:
            if not args.start_date:
                end_date = date.today() - timedelta(days=3)

    logger.info("=" * 80)
    logger.info("CAMS Global Radiation Flow")
    logger.info("=" * 80)
    logger.info(f"Start date: {start_date}")
    logger.info(f"End date: {end_date}")
    logger.info(f"Days to process: {(end_date - start_date).days + 1}")
    logger.info(f"Batch size: {args.batch_days} days")
    logger.info("")
    logger.info("Data Source: CAMS global radiation (satellite-based)")
    logger.info("  Variable: GHI (Global Horizontal Irradiance)")
    logger.info("  Resolution: 0.05° (~5.5 km)")
    logger.info("  Period: 2004-present (~2-3 days lag)")
    logger.info("  Accuracy: Superior to ERA5 for solar applications")
    logger.info("=" * 80)
    logger.info("")

    # Run the flow
    try:
        result = cams_radiation_flow(
            start_date=start_date,
            end_date=end_date,
            batch_days=args.batch_days
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("CAMS Global Radiation Flow Completed")
        logger.info("=" * 80)
        logger.info(f"✓ Status: {result['status']}")
        logger.info(f"✓ Files created: {result['files_created']}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Update climate_data.py to load CAMS GHI data")
        logger.info("2. Add CAMS GHI to solar router endpoints")
        logger.info("3. Configure GeoServer ImageMosaic for cams_ghi layer")
        logger.info("4. Restart FastAPI: sudo systemctl restart fastapi")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("CAMS Global Radiation Flow Failed")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)
    main()
