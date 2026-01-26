"""
Run ERA5 Hourly Solar Radiation Flow - Complete Pipeline

Downloads ERA5 hourly solar radiation and processes it into:
1. Daily GeoTIFF files for GeoServer
2. Yearly historical NetCDF files for API

Usage:
    python app/run_solar.py --year 2024
    python app/run_solar.py --start-date 2024-01-01 --end-date 2024-12-31
    python app/run_solar.py --days 30
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import argparse
import logging

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.workflows.data_processing.era5_solar_flow import era5_hourly_solar_flow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/solar_radiation.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Download and process ERA5 hourly solar radiation data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--year', type=int, help='Process entire year')
    parser.add_argument('--days', type=int, help='Process last N days')
    parser.add_argument('--batch-days', type=int, default=31, help='Days per batch (default: 31)')

    args = parser.parse_args()

    # Determine date range
    today = date.today()
    era5_lag = 7

    if args.days:
        end_date = today - timedelta(days=era5_lag)
        start_date = end_date - timedelta(days=args.days)
    elif args.year:
        start_date = date(args.year, 1, 1)
        end_date = date(args.year, 12, 31)
    else:
        start_date = date.fromisoformat(args.start_date) if args.start_date else date(today.year, 1, 1)
        end_date = date.fromisoformat(args.end_date) if args.end_date else today - timedelta(days=era5_lag)

    logger.info("=" * 80)
    logger.info("ERA5 Hourly Solar Radiation Flow")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Days: {(end_date - start_date).days + 1}")
    logger.info(f"Batch size: {args.batch_days} days")
    logger.info("")
    logger.info("Data Source: ERA5 reanalysis (hourly)")
    logger.info("  Variable: surface_solar_radiation_downwards")
    logger.info("  Process: Download hourly → Aggregate to daily → Convert to kWh/m²/day")
    logger.info("  Output: GeoTIFFs + Yearly historical NetCDF")
    logger.info("  Coverage: Latin America (Brazil focus)")
    logger.info("=" * 80)
    logger.info("")

    try:
        result = era5_hourly_solar_flow(
            start_date=start_date,
            end_date=end_date,
            batch_days=args.batch_days
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ ERA5 Hourly Solar Radiation Flow Completed")
        logger.info("=" * 80)
        logger.info(f"Processed solar radiation data: {start_date} to {end_date}")
        logger.info("✓ Created daily GeoTIFF files")
        logger.info("✓ Created/updated yearly historical NetCDF files")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Restart FastAPI to load solar data:")
        logger.info("   systemctl restart fastapi")
        logger.info("")
        logger.info("2. Test API endpoints:")
        logger.info("   curl 'http://localhost:8000/solar/info'")
        logger.info("   curl 'http://localhost:8000/solar/history?lat=-15.8&lon=-47.9&start_date=2024-01-01&end_date=2024-01-31'")
        logger.info("")
        logger.info("3. Configure GeoServer mosaic (optional):")
        logger.info("   - Create ImageMosaic store: DATA_DIR/solar_radiation/")
        logger.info("   - Configure time dimension from filenames")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("✗ ERA5 Hourly Solar Radiation Flow Failed")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)
    main()
