"""
Run ERA5 Solar Radiation Flow - Download and Process Surface Solar Radiation Downwards (GHI)

This script downloads ERA5-Land solar radiation data from the Climate Data Store (CDS)
and processes it into:
1. Daily GeoTIFF files for GeoServer time-enabled mosaics
2. Yearly historical NetCDF files for fast API queries

Data Source: ERA5-Land Surface Solar Radiation Downwards
- Variable: surface_solar_radiation_downwards (SSRD)
- Physical meaning: Equivalent to GHI (Global Horizontal Irradiance)
- Spatial Resolution: 0.1° (~11km)
- Temporal Resolution: Hourly → aggregated to daily totals
- Coverage: Global (all of Brazil and Latin America)
- Period: 1950-present (~7 day lag)
- Units: kWh/m²/day (converted from J/m²)

Usage:
    # Process recent year
    python app/run_era5_solar.py --year 2024

    # Process specific date range
    python app/run_era5_solar.py --start-date 2024-01-01 --end-date 2024-12-31

    # Process last 30 days
    python app/run_era5_solar.py --days 30
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import argparse
import logging

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.workflows.data_processing.era5_flow import era5_land_daily_flow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/era5_solar.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Download and process ERA5-Land solar radiation data (Surface Solar Radiation Downwards)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD). Default: 30 days ago'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD). Default: 7 days ago (ERA5 lag)'
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
        '--batch-months',
        type=int,
        default=1,
        help='Number of months to download per batch (default: 1)'
    )

    args = parser.parse_args()

    # Determine date range
    today = date.today()
    era5_lag_days = 7  # ERA5-Land has ~7 day lag

    if args.days:
        # Last N days
        end_date = today - timedelta(days=era5_lag_days)
        start_date = end_date - timedelta(days=args.days)
        logger.info(f"Processing last {args.days} days")
    elif args.year:
        # Entire year
        start_date = date(args.year, 1, 1)
        end_date = date(args.year, 12, 31)
        logger.info(f"Processing entire year: {args.year}")
    else:
        # Custom range or default (last 30 days)
        if args.start_date:
            start_date = date.fromisoformat(args.start_date)
        else:
            # Default: 30 days ago
            end_date = today - timedelta(days=era5_lag_days)
            start_date = end_date - timedelta(days=30)

        if args.end_date:
            end_date = date.fromisoformat(args.end_date)
        else:
            # Default: 7 days ago (ERA5 lag)
            end_date = today - timedelta(days=era5_lag_days)

    logger.info("=" * 80)
    logger.info("ERA5-Land Solar Radiation Flow")
    logger.info("=" * 80)
    logger.info(f"Start date: {start_date}")
    logger.info(f"End date: {end_date}")
    logger.info(f"Days to process: {(end_date - start_date).days + 1}")
    logger.info(f"Batch months: {args.batch_months}")
    logger.info("")
    logger.info("Data Source: ERA5-Land")
    logger.info("  Variable: surface_solar_radiation_downwards (SSRD)")
    logger.info("  Physical meaning: Global Horizontal Irradiance (GHI)")
    logger.info("  Resolution: 0.1° (~11km)")
    logger.info("  Coverage: Global (all of Brazil and Latin America)")
    logger.info("  Units: kWh/m²/day (converted from J/m²)")
    logger.info("  Statistic: daily_sum (sum of hourly accumulated values)")
    logger.info("=" * 80)
    logger.info("")

    # Run the ERA5 flow with solar radiation parameters
    try:
        result = era5_land_daily_flow(
            variables_config=[
                {
                    'variable': 'surface_solar_radiation_downwards',
                    'statistic': 'daily_sum'  # Sum hourly values to get daily total (kWh/m²/day)
                }
            ],
            start_date=start_date,
            end_date=end_date,
            batch_days=args.batch_months * 30  # Convert months to approximate days
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("ERA5-Land Solar Radiation Flow Completed")
        logger.info("=" * 80)
        logger.info(f"✓ Processed solar radiation data")
        logger.info(f"✓ Created daily GeoTIFF files")
        logger.info(f"✓ Created/updated yearly historical NetCDF files")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Restart FastAPI app to load solar data: systemctl restart fastapi")
        logger.info("2. Configure GeoServer mosaic for solar radiation layer (if needed)")
        logger.info("3. Test API endpoints:")
        logger.info("   GET /solar/history?lat=-15.8&lon=-47.9&start_date=2024-01-01&end_date=2024-01-31")
        logger.info("   GET /solar/info")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERA5-Land Solar Radiation Flow Failed")
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
