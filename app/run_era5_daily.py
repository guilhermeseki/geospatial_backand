"""
ERA5 Daily Update Flow Runner
Processes recent ERA5 temperature and wind data with automatic historical NetCDF updates.
"""
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from datetime import date, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("ERA5 DAILY UPDATE - TEMPERATURE & WIND")
    logger.info("=" * 80)

    # ERA5 has 7-day lag, so only check recent data
    end_date = date.today() - timedelta(days=7)
    start_date = end_date - timedelta(days=30)

    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info("Checks: Last 30 days (with 7-day lag for ERA5 availability)")
    logger.info("Updates: GeoTIFF mosaics + historical NetCDF")
    logger.info("Clips: Brazil shapefile polygon")
    logger.info("Converts: Kelvin → Celsius")
    logger.info("=" * 80)

    # Temperature (max, min, mean)
    logger.info("")
    logger.info("Processing TEMPERATURE data (max, min, mean)...")
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
        skip_historical_merge=False  # IMPORTANT: Update historical NetCDF
    )

    logger.info("✓ Temperature processing complete")

    # Wind speed
    logger.info("")
    logger.info("Processing WIND data (u and v components)...")
    logger.info("-" * 80)

    era5_land_daily_flow(
        batch_days=31,
        start_date=start_date,
        end_date=end_date,
        variables_config=[
            {'variable': '10m_u_component_of_wind', 'statistic': 'daily_maximum'},
            {'variable': '10m_v_component_of_wind', 'statistic': 'daily_maximum'},
        ],
        skip_historical_merge=False  # IMPORTANT: Update historical NetCDF
    )

    logger.info("✓ Wind processing complete")
    logger.info("=" * 80)
