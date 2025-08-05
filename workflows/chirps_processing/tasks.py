# workflows/chirps_processing/tasks.py
from datetime import date
from pathlib import Path
from typing import Tuple
import requests
import fsspec
import rioxarray
import xarray as xr
from prefect import task, get_run_logger
from .schemas import DataSource

@task(retries=3, retry_delay_seconds=60)
def check_data_availability(date: date, source: DataSource) -> bool:
    """Check if data exists on the CHIRPS server"""
    logger = get_run_logger()
    url = f"https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/{date.year}/chirps-v3.0.{date.strftime('%Y.%m.%d')}.tif"
    
    try:
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            logger.info(f"Data available for {date} at {url}")
            return True
        logger.warning(f"No data available for {date} (HTTP {response.status_code})")
        return False
    except Exception as e:
        logger.error(f"Availability check failed: {str(e)}")
        raise

@task(retries=3, retry_delay_seconds=300)
def download_chirps_data(date: date, source: DataSource) -> Path:
    """Download the raw data file"""
    logger = get_run_logger()
    url = f"https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/{date.year}/chirps-v3.0.{date.strftime('%Y.%m.%d')}.tif"
    output_path = Path(f"/data/chirps/raw/chirps_{date.strftime('%Y%m%d')}.tif")
    
    try:
        logger.info(f"Downloading from {url}")
        with fsspec.open(url) as remote_file:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as local_file:
                local_file.write(remote_file.read())
        return output_path
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise

@task
def process_chirps_data(
    input_path: Path, 
    date: date, 
    source: DataSource,
    bbox: Tuple[float, float, float, float]
) -> Path:
    """Convert raw data to analysis-ready NetCDF"""
    logger = get_run_logger()
    output_path = Path(f"/data/chirps/processed/chirps_{date.strftime('%Y%m%d')}.nc")
    
    try:
        # Load and process data
        ds = rioxarray.open_rasterio(input_path)
        ds = ds.rio.clip_box(*bbox)
        ds = ds.rename({'x': 'longitude', 'y': 'latitude'})
        ds['precip'] = ds['precip'].where(ds['precip'] >= 0, 0)
        
        # Save as NetCDF
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ds.to_netcdf(output_path)
        return output_path
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise

@task
def validate_output(output_path: Path) -> bool:
    """Verify the processed file meets requirements"""
    logger = get_run_logger()
    try:
        ds = xr.open_dataset(output_path)
        required_vars = {'precip', 'longitude', 'latitude'}
        if not required_vars.issubset(set(ds.variables)):
            raise ValueError("Missing required variables")
        return True
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise