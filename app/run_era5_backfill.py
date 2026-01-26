"""
ERA5 Full Backfill Script
Checks ALL dates from 2015-01-01 to 7 days ago and fills any gaps.
Processes both Temperature (max/min/mean) and Wind Speed.
Run this ONCE before setting up operational daily updates.
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
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
    logger.info("ERA5 FULL BACKFILL - ONE-TIME OPERATION")
    logger.info("=" * 80)

    # Check current state
    temp_max_dir = Path(settings.DATA_DIR) / "temp_max"
    wind_dir = Path(settings.DATA_DIR) / "wind_speed"

    temp_files = list(temp_max_dir.glob("temp_max_*.tif")) if temp_max_dir.exists() else []
    wind_files = list(wind_dir.glob("wind_speed_*.tif")) if wind_dir.exists() else []

    logger.info(f"Current temp_max files: {len(temp_files)}")
    logger.info(f"Current wind_speed files: {len(wind_files)}")

    # ERA5 has 7-day lag
    start_date = date(2015, 1, 1)
    end_date = date.today() - timedelta(days=7)

    logger.info("")
    logger.info("Backfill Configuration:")
    logger.info(f"  Start: {start_date}")
    logger.info(f"  End: {end_date} (7-day lag)")
    logger.info(f"  Total days to check: {(end_date - start_date).days + 1}")
    logger.info("")
    logger.info("Strategy:")
    logger.info("  - Skip existing files (fast)")
    logger.info("  - Download only missing dates")
    logger.info("  - Process in batches of 31 days (CDS API limit)")
    logger.info("  - Update GeoTIFF mosaics")
    logger.info("  - Update historical NetCDF")
    logger.info("  - Convert Kelvin → Celsius")
    logger.info("  - Clip to Brazil shapefile")
    logger.info("=" * 80)
    logger.info("")

    # Temperature (max, min, mean)
    logger.info("PROCESSING TEMPERATURE DATA...")
    logger.info("-" * 80)

    era5_land_daily_flow(
        batch_days=31,
        start_date=start_date,
        end_date=end_date,
        variables_config=[
            {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
            {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
            {'variable': '2m_temperature', 'statistic': 'daily_mean'},
        ],
        skip_historical_merge=False
    )

    logger.info("✓ Temperature backfill complete")
    logger.info("")

    # Wind speed
    logger.info("PROCESSING WIND DATA...")
    logger.info("-" * 80)

    era5_land_daily_flow(
        batch_days=31,
        start_date=start_date,
        end_date=end_date,
        variables_config=[
            {'variable': '10m_u_component_of_wind', 'statistic': 'daily_maximum'},
            {'variable': '10m_v_component_of_wind', 'statistic': 'daily_maximum'},
        ],
        skip_historical_merge=False
    )

    logger.info("✓ Wind backfill complete")
    logger.info("")

    # Final count
    final_temp_files = list(temp_max_dir.glob("temp_max_*.tif")) if temp_max_dir.exists() else []
    final_wind_files = list(wind_dir.glob("wind_speed_*.tif")) if wind_dir.exists() else []

    logger.info("=" * 80)
    logger.info("BACKFILL COMPLETE")
    logger.info(f"Total temp_max files: {len(final_temp_files)}")
    logger.info(f"Total wind_speed files: {len(final_wind_files)}")

    expected_days = (end_date - start_date).days + 1
    logger.info(f"Expected files (if complete): ~{expected_days}")
    logger.info("=" * 80)
