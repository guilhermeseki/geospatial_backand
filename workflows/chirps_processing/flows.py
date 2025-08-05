from datetime import date, timedelta
from prefect import flow, get_run_logger
from pathlib import Path
from .tasks import (
    check_data_availability,
    download_chirps_data,
    process_chirps_data,
    validate_output
)
from .schemas import DataSource
from config.settings import get_settings

@flow(name="process-chirps-daily",
      description="Daily download and processing of CHIRPS precipitation data",
      retries=2,
      retry_delay_seconds=300)
def chirps_daily_flow(
    days_back: int = 1,
    source: DataSource = "CHIRPS_FINAL"
):
    """
    Main workflow for daily CHIRPS data processing.
    
    Args:
        days_back: How many days back to process (default: 1 for yesterday's data)
        source: Data source (CHIRPS_FINAL, CHIRPS, or MERGE)
    """
    logger = get_run_logger()
    settings = get_settings()
    
    try:
        # 1. Determine processing date (yesterday by default)
        process_date = date.today() - timedelta(days=days_back)
        logger.info(f"Starting CHIRPS processing for {process_date}")
        
        # 2. Check data availability
        is_available = check_data_availability(process_date, source)
        
        if not is_available:
            logger.warning(f"No data available for {process_date} from {source}")
            return None
        
        # 3. Download data
        raw_path = download_chirps_data(process_date, source)
        
        # 4. Process data
        processed_path = process_chirps_data(
            raw_path, 
            process_date, 
            source,
            bbox=settings.latam_bbox  # Defined in your settings
        )
        
        # 5. Validate output
        if validate_output(processed_path):
            logger.success(f"Successfully processed {source} data for {process_date}")
            return processed_path
            
        raise ValueError(f"Output validation failed for {processed_path}")
        
    except Exception as e:
        logger.error(f"Flow failed: {str(e)}")
        raise