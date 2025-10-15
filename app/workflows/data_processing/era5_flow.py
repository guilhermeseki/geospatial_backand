"""
ERA5 Land Daily Flow - Uses pre-aggregated daily statistics from CDS
Better resolution (9km) and no hourly processing needed!
"""
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import cdsapi
import xarray as xr
from prefect import flow, task, get_run_logger
from .schemas import DataSource
from config.settings import get_settings


# Mapping from ERA5 variable and statistic to directory names
VARIABLE_MAPPING = {
    "2m_temperature": {
        "daily_maximum": "temp_max",
        "daily_minimum": "temp_min", 
        "daily_mean": "temp"
    },
    "total_precipitation": {
        "daily_sum": "precipitation"
    }
}


def get_output_directory(variable: str, daily_statistic: str, settings) -> Path:
    """
    Get the appropriate output directory for a variable and statistic combination.
    
    Args:
        variable: ERA5 variable name (e.g., '2m_temperature')
        daily_statistic: Statistic type (e.g., 'daily_maximum')
        settings: Application settings
    
    Returns:
        Path to the output directory
    """
    # Check mapping first
    if variable in VARIABLE_MAPPING and daily_statistic in VARIABLE_MAPPING[variable]:
        dir_name = VARIABLE_MAPPING[variable][daily_statistic]
    else:
        # Fallback inference
        if "temperature" in variable:
            if "maximum" in daily_statistic:
                dir_name = "temp_max"
            elif "minimum" in daily_statistic:
                dir_name = "temp_min"
            else:
                dir_name = "temp"
        elif "precipitation" in variable:
            dir_name = "precipitation"
        else:
            # Default fallback
            dir_name = f"{variable}_{daily_statistic}".replace("_", "-")
    
    output_dir = Path(settings.DATA_DIR) / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@task(retries=2, retry_delay_seconds=600, timeout_seconds=7200)
def download_era5_land_daily_batch(
    start_date: date,
    end_date: date,
    variable: str,
    daily_statistic: str,
    area: List[float],
    convert_bbox: bool = True
) -> Path:
    """
    Download ERA5 Land Daily Statistics (pre-aggregated daily data).
    Resolution: 9km (0.1°) - much better than ERA5 single levels!
    
    Args:
        start_date: First date to download
        end_date: Last date to download
        variable: ERA5 variable name (e.g., '2m_temperature')
        daily_statistic: Statistic to download ('daily_maximum', 'daily_minimum', 'daily_mean', 'daily_sum')
        area: Bounding box - will be converted to CDS format [N, W, S, E]
        convert_bbox: If True, convert from raster format (W, S, E, N) to CDS format (N, W, S, E)
    
    Returns:
        Path to downloaded NetCDF file
    """
    logger = get_run_logger()
    settings = get_settings()
    
    # Convert bbox from raster format (W, S, E, N) to CDS format [N, W, S, E]
    if convert_bbox and isinstance(area, (list, tuple)) and len(area) == 4:
        # Input: (min_lon, min_lat, max_lon, max_lat) = (W, S, E, N)
        # Output: [max_lat, min_lon, min_lat, max_lon] = [N, W, S, E]
        cds_area = [area[3], area[0], area[1], area[2]]  # [N, W, S, E]
        logger.info(f"Converted bbox from {area} to CDS format: {cds_area}")
    else:
        cds_area = area
    
    # Generate date list
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # Extract components
    years = sorted(list(set([d.strftime("%Y") for d in dates])))
    months = sorted(list(set([d.strftime("%m") for d in dates])))
    days = sorted(list(set([d.strftime("%d") for d in dates])))
    
    # Prepare output path
    raw_dir = Path(settings.DATA_DIR) / "raw" / "era5_land_daily"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    var_short = variable.replace("_", "")
    output_path = raw_dir / f"{var_short}_{daily_statistic}_{start_str}_{end_str}.nc"
    
    if output_path.exists():
        logger.info(f"Batch already downloaded: {output_path}")
        return output_path
    
    # Build CDS request for ERA5 Land Daily Statistics
    # Area format: [North, West, South, East]
    request = {
        "variable": [variable],  # Must be a list
        "year": years,
        "month": months,
        "day": days,
        "daily_statistic": daily_statistic,
        "time_zone": "utc+00:00",
        "frequency": "1_hourly",  # Input frequency for the statistic calculation
        "area": cds_area  # [N, W, S, E]
    }
    
    logger.info(f"Downloading ERA5 Land Daily: {start_date} to {end_date}")
    logger.info(f"Variable: {variable}, Statistic: {daily_statistic}")
    logger.info("=" * 80)
    
    # Debug: Check CDS API configuration
    import os
    logger.info("Checking CDS API configuration...")
    cdsapi_rc = os.path.expanduser("~/.cdsapirc")
    logger.info(f"Looking for config at: {cdsapi_rc}")
    logger.info(f"Config file exists: {os.path.exists(cdsapi_rc)}")
    
    if 'CDSAPI_URL' in os.environ:
        logger.info(f"CDSAPI_URL env var: {os.environ['CDSAPI_URL']}")
    if 'CDSAPI_KEY' in os.environ:
        logger.info(f"CDSAPI_KEY env var: {'*' * 20} (hidden)")
    
    import json
    logger.info("CDS API Request:")
    logger.info(json.dumps(request, indent=2))
    logger.info("=" * 80)
    
    try:
        # Initialize client and log URL being used
        import os
        logger.info("Initializing CDS API client...")
        
        # Force reload credentials from file
        cdsapi_rc = os.path.expanduser("~/.cdsapirc")
        if os.path.exists(cdsapi_rc):
            logger.info(f"✓ Config file found: {cdsapi_rc}")
            
            # Read and parse the config manually
            with open(cdsapi_rc, 'r') as f:
                config_lines = f.readlines()
                for line in config_lines:
                    if line.strip().startswith('url:'):
                        url = line.split('url:')[1].strip()
                        os.environ['CDSAPI_URL'] = url
                        logger.info(f"✓ Set CDSAPI_URL to: {url}")
                    elif line.strip().startswith('key:'):
                        key = line.split('key:')[1].strip()
                        os.environ['CDSAPI_KEY'] = key
                        logger.info(f"✓ Set CDSAPI_KEY (length: {len(key)} chars)")
        else:
            logger.warning(f"✗ Config file not found: {cdsapi_rc}")
        
        client = cdsapi.Client()
        logger.info(f"✓ CDS Client initialized")
        logger.info(f"✓ Using URL: {client.url}")
        
        logger.info("Submitting request to CDS...")
        result = client.retrieve("derived-era5-land-daily-statistics", request)
        
        logger.info("Downloading result...")
        result.download(str(output_path))
        logger.info(f"✓ ERA5 Land Daily downloaded: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"✗ Download failed: {e}")
        if output_path.exists():
            output_path.unlink()
        raise


@task
def process_era5_land_daily_to_geotiff(
    netcdf_path: Path,
    variable: str,
    daily_statistic: str,
    bbox: tuple
) -> List[Path]:
    """
    Convert ERA5 Land Daily NetCDF to daily GeoTIFFs.
    Data is already daily - just need to split by day and convert format.
    
    Args:
        netcdf_path: Path to downloaded batch NetCDF
        variable: Variable name to extract (e.g., '2m_temperature')
        daily_statistic: Statistic type (e.g., 'daily_maximum')
        bbox: (minx, miny, maxx, maxy) or [N, W, S, E]
    
    Returns:
        List of paths to processed daily GeoTIFFs
    """
    logger = get_run_logger()
    settings = get_settings()
    
    # Get the appropriate output directory
    output_dir = get_output_directory(variable, daily_statistic, settings)
    logger.info(f"Saving {variable} ({daily_statistic}) to: {output_dir}")
    
    processed_paths = []
    
    try:
        # Open the NetCDF file
        ds = xr.open_dataset(netcdf_path)
        logger.info(f"NetCDF variables: {list(ds.data_vars)}")
        logger.info(f"NetCDF dimensions: {list(ds.dims)}")
        logger.info(f"NetCDF coordinates: {list(ds.coords)}")
        
        # Find the variable in the dataset
        # ERA5 Land uses different naming conventions
        var_name = None
        if variable in ds.data_vars:
            var_name = variable
        else:
            # Try common variations
            possible_names = [
                variable,
                variable.replace("_", ""),
                f"{variable}_{daily_statistic.replace('daily_', '')}",
                # Temperature variations
                "t2m", "2t", "temperature_2m",
                # Check all variables that contain key parts
                *[v for v in ds.data_vars if any(part in v for part in variable.split("_"))]
            ]
            
            for name in possible_names:
                if name in ds.data_vars:
                    var_name = name
                    logger.info(f"Found variable as: {var_name}")
                    break
        
        if not var_name:
            raise ValueError(
                f"Variable '{variable}' not found in dataset. "
                f"Available variables: {list(ds.data_vars)}"
            )
        
        da = ds[var_name]
        
        # Convert bbox format if needed: (minx, miny, maxx, maxy) or [N, W, S, E]
        if isinstance(bbox, list):
            # Assume [N, W, S, E] format, convert to (minx, miny, maxx, maxy)
            bbox = (bbox[1], bbox[2], bbox[3], bbox[0])  # [W, S, E, N]
        
        # Process each day
        if 'time' not in da.dims:
            logger.warning("No time dimension found - processing as single day")
            time_values = [da.coords.get('time', date.today())]
        else:
            time_values = da.time.values
        
        # Check for different time dimension names
        time_dim = None
        for possible_time_dim in ['time', 'valid_time', 'datetime']:
            if possible_time_dim in da.dims:
                time_dim = possible_time_dim
                logger.info(f"Using time dimension: {time_dim}")
                break
        
        if time_dim:
            time_values = da[time_dim].values
        else:
            logger.warning(f"No recognized time dimension found in {da.dims}")
            time_values = [date.today()]
        
        for time_val in time_values:
            # Get data for this specific day
            if time_dim and time_dim in da.dims:
                daily_data = da.sel({time_dim: time_val})
            else:
                daily_data = da
            
            # Convert numpy datetime to Python date
            import pandas as pd
            if isinstance(time_val, (pd.Timestamp, date)):
                day_date = pd.Timestamp(time_val).date()
            else:
                try:
                    day_date = pd.Timestamp(time_val).date()
                except:
                    day_date = date.today()
                    logger.warning(f"Could not parse date, using today: {day_date}")
            
            # Rename coordinates if needed (ERA5 Land uses various conventions)
            coord_mapping = {}
            for coord in daily_data.dims:
                coord_lower = coord.lower()
                if coord_lower in ['longitude', 'lon', 'long']:
                    coord_mapping[coord] = 'x'
                elif coord_lower in ['latitude', 'lat']:
                    coord_mapping[coord] = 'y'
            
            if coord_mapping:
                daily_data = daily_data.rename(coord_mapping)
            
            # Set CRS
            daily_data = daily_data.rio.write_crs("EPSG:4326")
            
            # Clip to bbox
            try:
                daily_data = daily_data.rio.clip_box(*bbox)
            except Exception as e:
                logger.warning(f"Could not clip to bbox: {e}. Using full extent.")
            
            # Generate output filename
            output_path = output_dir / f"{output_dir.name}_{day_date.strftime('%Y%m%d')}.tif"
            
            # Save as Cloud Optimized GeoTIFF
            # Note: COG driver handles tiling and overviews automatically
            daily_data.rio.to_raster(
                output_path,
                driver="COG",
                compress="LZW"
            )

            processed_paths.append(output_path)
            logger.info(f"✓ Processed: {day_date} -> {output_path.name}")
        
        logger.info(f"✓ Successfully processed {len(processed_paths)} days")
        return processed_paths
        
    except Exception as e:
        logger.error(f"✗ Failed to process ERA5 Land Daily batch: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@flow(
    name="process-era5-land-daily",
    description="Download and process ERA5 Land Daily Statistics (9km resolution)",
    retries=1,
    retry_delay_seconds=600
)
def era5_land_daily_flow(
    batch_days: int = 31,
    variables_config: Optional[List[Dict[str, str]]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    ERA5 Land Daily processing flow - downloads pre-aggregated daily data.
    No hourly processing needed! Better resolution (9km vs 31km).
    
    Args:
        batch_days: Number of days to download per batch (default: 31 for monthly)
        variables_config: List of dicts with 'variable' and 'statistic' keys
                         Example: [
                             {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
                             {'variable': '2m_temperature', 'statistic': 'daily_minimum'}
                         ]
        start_date: Start date (default: first day of last month)
        end_date: End date (default: 3 days ago, accounting for ERA5 lag)
    """
    logger = get_run_logger()
    settings = get_settings()
    
    # Default variable configuration
    if variables_config is None:
        variables_config = [
            {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
            {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
        ]
    
    # Define date range
    if start_date is None or end_date is None:
        today = date.today()
        if end_date is None:
            end_date = today - timedelta(days=3)  # ERA5 Land has ~3 day lag
        if start_date is None:
            # First day of last month
            start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    logger.info(f"Processing ERA5 Land Daily from {start_date} to {end_date}")
    logger.info(f"Variables config: {variables_config}")
    
    all_processed = []
    
    # Process each variable+statistic combination
    for var_config in variables_config:
        variable = var_config['variable']
        statistic = var_config['statistic']
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {variable} - {statistic}")
        logger.info(f"{'='*80}")
        
        # Download in batches
        current_start = start_date
        while current_start <= end_date:
            current_end = min(current_start + timedelta(days=batch_days - 1), end_date)
            
            try:
                # Download batch - use CDS format bbox
                batch_path = download_era5_land_daily_batch(
                    start_date=current_start,
                    end_date=current_end,
                    variable=variable,
                    daily_statistic=statistic,
                    area=settings.latam_bbox_cds  # Use CDS format: [N, W, S, E]
                )
                
                # Process to GeoTIFFs - use raster format bbox
                processed = process_era5_land_daily_to_geotiff(
                    netcdf_path=batch_path,
                    variable=variable,
                    daily_statistic=statistic,
                    bbox=settings.latam_bbox_raster  # Use raster format: (W, S, E, N)
                )
                
                all_processed.extend(processed)
                logger.info(f"✓ Completed batch: {current_start} to {current_end}")
                
            except Exception as e:
                logger.error(f"✗ Failed batch {current_start} to {current_end}: {e}")
            
            current_start = current_end + timedelta(days=1)
    
    # Refresh GeoServer mosaics
    if all_processed:
        from .tasks import refresh_mosaic_shapefile
        from collections import defaultdict
        
        # Group files by directory
        files_by_dir = defaultdict(list)
        for path in all_processed:
            files_by_dir[path.parent].append(path)
        
        logger.info(f"\n{'='*80}")
        logger.info("Refreshing GeoServer mosaics")
        logger.info(f"{'='*80}")
        
        for dir_path, files in files_by_dir.items():
            logger.info(f"Refreshing {dir_path.name}: {len(files)} files")
            try:
                # Use ERA5 data source for all ERA5 Land data
                refresh_mosaic_shapefile(DataSource.ERA5)
            except Exception as e:
                logger.error(f"Failed to refresh mosaic for {dir_name}: {e}")
        
        logger.info(f"\n✓ Successfully processed {len(all_processed)} total files")
    
    return all_processed