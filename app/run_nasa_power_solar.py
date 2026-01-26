"""
Run NASA POWER Solar Radiation Flow - Download and Process GHI Data

This script downloads NASA POWER solar radiation data (Global Horizontal Irradiance)
via their free REST API and processes it into:
1. Daily GeoTIFF files for GeoServer time-enabled mosaics
2. Yearly historical NetCDF files for fast API queries

Data Source: NASA POWER (Prediction Of Worldwide Energy Resources)
- Parameter: ALLSKY_SFC_SW_DWN (All Sky Surface Shortwave Downward Irradiance = GHI)
- Spatial Resolution: 0.5° (~55km)
- Temporal Resolution: Daily totals (already computed!)
- Coverage: Global (all of Brazil and Latin America)
- Period: 1981-present (near real-time, ~3-7 day lag)
- Units: kWh/m²/day (no conversion needed!)
- API: Free REST API, no authentication required
- Accuracy: <1% bias for monthly GHI (validated in Brazil)

Usage:
    # Process recent year
    python app/run_nasa_power_solar.py --year 2024

    # Process specific date range
    python app/run_nasa_power_solar.py --start-date 2024-01-01 --end-date 2024-12-31

    # Process last 30 days
    python app/run_nasa_power_solar.py --days 30
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import argparse
import logging

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.workflows.data_processing.nasa_power_flow import nasa_power_solar_flow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/nasa_power_solar.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Download and process NASA POWER solar radiation data (GHI)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD). Default: First day of current year'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD). Default: 7 days ago (near real-time lag)'
    )

    parser.add_argument(
        '--year',
        type=int,
        help='Process entire year (e.g., 2024). Overrides start-date and end-date'
    )

    parser.add_argument(
        '--days',
        type=int,
        help='Process last N days (e.g., 30). Overrides other date options'
    )

    parser.add_argument(
        '--batch-days',
        type=int,
        default=365,
        help='Number of days to download per batch (default: 365 - one year at a time)'
    )

    args = parser.parse_args()

    # Determine date range
    today = date.today()
    nasa_power_lag_days = 7  # NASA POWER has ~3-7 day lag

    if args.days:
        # Last N days
        end_date = today - timedelta(days=nasa_power_lag_days)
        start_date = end_date - timedelta(days=args.days)
        logger.info(f"Processing last {args.days} days")
    elif args.year:
        # Entire year
        start_date = date(args.year, 1, 1)
        end_date = date(args.year, 12, 31)
        logger.info(f"Processing entire year: {args.year}")
    else:
        # Custom range or default
        if args.start_date:
            start_date = date.fromisoformat(args.start_date)
        else:
            # Default: start of current year
            start_date = date(today.year, 1, 1)

        if args.end_date:
            end_date = date.fromisoformat(args.end_date)
        else:
            # Default: 7 days ago (NASA POWER lag)
            end_date = today - timedelta(days=nasa_power_lag_days)

    logger.info("=" * 80)
    logger.info("NASA POWER Solar Radiation Flow")
    logger.info("=" * 80)
    logger.info(f"Start date: {start_date}")
    logger.info(f"End date: {end_date}")
    logger.info(f"Days to process: {(end_date - start_date).days + 1}")
    logger.info(f"Batch days: {args.batch_days}")
    logger.info("")
    logger.info("Data Source: NASA POWER")
    logger.info("  Parameter: ALLSKY_SFC_SW_DWN (GHI)")
    logger.info("  Resolution: 0.5° (~55km)")
    logger.info("  Coverage: Global (all of Brazil and Latin America)")
    logger.info("  Units: kWh/m²/day (already computed, no conversion needed!)")
    logger.info("  Period: 1981-present (~3-7 day lag)")
    logger.info("  Accuracy: <1% bias for monthly GHI (validated in Brazil)")
    logger.info("  API: Free REST API, no authentication required")
    logger.info("=" * 80)
    logger.info("")

    # Run the NASA POWER flow
    try:
        result = nasa_power_solar_flow(
            start_date=start_date,
            end_date=end_date,
            batch_days=args.batch_days
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("NASA POWER Solar Radiation Flow Completed")
        logger.info("=" * 80)
        logger.info(f"✓ Processed solar radiation data")
        logger.info(f"✓ Created daily GeoTIFF files")
        logger.info(f"✓ Created/updated yearly historical NetCDF files")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Restart FastAPI app to load solar data:")
        logger.info("   systemctl restart fastapi  # or your restart method")
        logger.info("")
        logger.info("2. Test API endpoints:")
        logger.info("   curl 'http://localhost:8000/solar/info'")
        logger.info("   curl 'http://localhost:8000/solar/history?lat=-15.8&lon=-47.9&start_date=2024-01-01&end_date=2024-01-31'")
        logger.info("")
        logger.info("3. Configure GeoServer mosaic for solar radiation layer (optional):")
        logger.info("   - Create ImageMosaic store pointing to DATA_DIR/solar_radiation/")
        logger.info("   - Configure time dimension from filenames")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("NASA POWER Solar Radiation Flow Failed")
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
