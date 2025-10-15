from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from prefect import flow, get_run_logger
from pathlib import Path
from .tasks import (
    check_data_availability,
    download_data,
    process_data,
    validate_output,
    refresh_mosaic_shapefile
)
from .schemas import DataSource
from config.settings import get_settings
import cdsapi



"""
Alerting: Integrate Prefect notifications (e.g., Slack, email) for persistent failures:
from prefect.blocks.notifications import SlackWebhook

@flow(..., on_failure=[SlackWebhook.notify])
def merge_daily_flow(...):
    ...
"""
@flow(
    name="process-chirps-daily",
    description="Daily check and download of CHIRPS precipitation data for all missing days in the previous year until the last month",
    retries=2,
    retry_delay_seconds=300,
)
def chirps_daily_flow(source: DataSource = DataSource.CHIRPS):
    logger = get_run_logger()
    settings = get_settings()
    processed_paths = []
    raw_dir = Path(settings.DATA_DIR) / "raw"
    mosaic_dir = Path(settings.DATA_DIR) / source.value
    # Setup mosaic store
    #setup_mosaic.submit(mosaic_dir, source).result()
    # Define date range
    today = date.today()
    last_month_end = today.replace(day=1) - timedelta(days=1)
    start_date = last_month_end - relativedelta(years=10) + timedelta(days=1)
    current_date = start_date

    while current_date <= last_month_end:
        output_path = mosaic_dir / f"{source.value}_{current_date.strftime('%Y%m%d')}.tif"
        if output_path.exists():
            logger.info(f"File already exists locally: {output_path}, skipping download and processing")
        else:
            is_available = check_data_availability.submit(current_date, source).result()
            if is_available:
                raw_path = download_data.submit(current_date, source).result()
                processed_path = process_data.submit(
                    raw_path, current_date, source, bbox=settings.latam_bbox_raster
                ).result()
                if validate_output.submit(processed_path).result():
                    processed_paths.append(processed_path)
            else:
                logger.warning(f"Data not available for {current_date}, skipping")
        current_date += timedelta(days=1)

    refresh_mosaic_shapefile.submit(source).result()

    return processed_paths if processed_paths else None

@flow(
    name="process-merge-daily",
    description="Daily check and download of MERGE precipitation data for all missing days in the previous year until the last month",
    retries=2,
    retry_delay_seconds=300,
)
def merge_daily_flow(source: DataSource = DataSource.MERGE):
    logger = get_run_logger()
    settings = get_settings()
    processed_paths = []
    raw_dir = Path(settings.DATA_DIR) / "raw"
    mosaic_dir = Path(settings.DATA_DIR) / source.value
    # Setup mosaic store
    #setup_mosaic.submit(mosaic_dir, source).result()
    # Define date range
    # Start: first day of previous month
    today = date.today()

    start_date = (today.replace(day=1) - relativedelta(months=1)) 

    # End: yesterday
    end_date = today - timedelta(days=1)


    current_date = start_date
    while current_date <= end_date:
        output_path = mosaic_dir / f"{source.value}_{current_date.strftime('%Y%m%d')}.tif"
        if output_path.exists():
            logger.info(f"File already exists locally: {output_path}, skipping download and processing")
        else:
            #is_available = check_data_availability.submit(current_date, source).result()
            is_available = True
            if is_available:
                raw_path = download_data.submit(current_date, source).result()
                processed_path = process_data.submit(
                    raw_path, current_date, source, bbox=settings.latam_bbox_raster
                ).result()
                if validate_output.submit(processed_path).result():
                    processed_paths.append(processed_path)
            else:
                logger.warning(f"Data not available for {current_date}, skipping")

        current_date += timedelta(days=1)
    # Reindex mosaic
    #recalculate_time.submit(mosaic_dir, source).result()
    refresh_mosaic_shapefile.submit(source).result()

    return processed_paths if processed_paths else None

