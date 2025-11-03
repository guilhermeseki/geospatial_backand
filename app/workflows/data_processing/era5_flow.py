"""
ERA5 Land Daily Flow - With Historical NetCDF Management
"""
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import cdsapi
import xarray as xr
import pandas as pd
from prefect import flow, task, get_run_logger
from .schemas import DataSource
from app.config.settings import get_settings


# Mapping from ERA5 variable and statistic to directory names
VARIABLE_MAPPING = {
    "2m_temperature": {
        "daily_maximum": "temp_max",
        "daily_minimum": "temp_min",
        "daily_mean": "temp"
    },
    "total_precipitation": {
        "daily_sum": "precipitation"
    },
    "10m_u_component_of_wind": {
        "daily_mean": "wind_u",
        "daily_maximum": "wind_u_max",
        "daily_minimum": "wind_u_min"
    },
    "10m_v_component_of_wind": {
        "daily_mean": "wind_v",
        "daily_maximum": "wind_v_max",
        "daily_minimum": "wind_v_min"
    },
}


def get_output_directory(variable: str, daily_statistic: str, settings) -> Path:
    """Get the appropriate output directory for a variable and statistic combination."""
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
        elif "wind" in variable:
            # Handle wind variables
            base = "wind_speed" if "speed" in variable else "wind_u" if "u_component" in variable else "wind_v"
            if "maximum" in daily_statistic:
                dir_name = f"{base}_max"
            elif "minimum" in daily_statistic:
                dir_name = f"{base}_min"
            else:
                dir_name = base
        else:
            dir_name = f"{variable}_{daily_statistic}".replace("_", "-")
    
    output_dir = Path(settings.DATA_DIR) / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@task
def check_missing_dates(
    start_date: date,
    end_date: date,
    variable: str,
    daily_statistic: str
) -> Dict[str, List[date]]:
    """
    Check which dates are missing from GeoTIFF and historical NetCDF separately.
    
    Returns:
        Dictionary with 'geotiff' and 'historical' keys containing lists of missing dates
    """
    logger = get_run_logger()
    settings = get_settings()
    
    # Generate list of requested dates
    requested_dates = []
    current = start_date
    while current <= end_date:
        requested_dates.append(current)
        current += timedelta(days=1)
    
    logger.info(f"Checking for {len(requested_dates)} dates: {start_date} to {end_date}")
    
    # Get directories
    dir_name = get_output_directory(variable, daily_statistic, settings).name
    geotiff_dir = Path(settings.DATA_DIR) / dir_name
    hist_dir = Path(settings.DATA_DIR) / f"{dir_name}_hist"
    hist_file = hist_dir / "historical.nc"
    
    # Check GeoTIFF files
    existing_geotiff_dates = set()
    if geotiff_dir.exists():
        for tif_file in geotiff_dir.glob(f"{dir_name}_*.tif"):
            try:
                date_str = tif_file.stem.split('_')[-1]
                file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
                existing_geotiff_dates.add(file_date)
            except Exception as e:
                logger.warning(f"Could not parse date from {tif_file.name}: {e}")
    
    logger.info(f"Found {len(existing_geotiff_dates)} existing GeoTIFF files")
    
    # Check historical NetCDF
    existing_hist_dates = set()
    if hist_file.exists():
        try:
            ds = xr.open_dataset(hist_file, chunks='auto')
            var_short_name = dir_name
            if var_short_name in ds.data_vars:
                existing_hist_dates = set(pd.to_datetime(ds[var_short_name].time.values).date)
                logger.info(f"Found {len(existing_hist_dates)} dates in historical NetCDF")
            ds.close()
        except Exception as e:
            logger.warning(f"Could not read historical file: {e}")
    else:
        logger.info("Historical NetCDF does not exist yet")
    
    # Calculate missing dates separately
    requested_dates_set = set(requested_dates)
    missing_geotiff = sorted(list(requested_dates_set - existing_geotiff_dates))
    missing_historical = sorted(list(requested_dates_set - existing_hist_dates))
    
    # Dates to download = union (missing from either source)
    missing_download = sorted(list(set(missing_geotiff) | set(missing_historical)))
    
    logger.info(f"Missing from GeoTIFF: {len(missing_geotiff)} dates")
    logger.info(f"Missing from historical: {len(missing_historical)} dates")
    logger.info(f"Need to download: {len(missing_download)} dates")
    
    if missing_download:
        logger.info(f"  Download range: {min(missing_download)} to {max(missing_download)}")
    
    return {
        'geotiff': missing_geotiff,
        'historical': missing_historical,
        'download': missing_download
    }


@task(retries=2, retry_delay_seconds=600, timeout_seconds=14400)  # 4 hours (increased from 2 hours)
def download_era5_land_daily_batch(
    start_date: date,
    end_date: date,
    variable: str,
    daily_statistic: str,
    area: List[float],
    convert_bbox: bool = False
) -> Path:
    """Download ERA5 Land Daily Statistics (pre-aggregated daily data)."""
    logger = get_run_logger()
    settings = get_settings()
    
    # Area should already be in CDS format [N, W, S, E]
    cds_area = list(area)
    
    # Validate bbox: North must be > South
    north, west, south, east = cds_area[0], cds_area[1], cds_area[2], cds_area[3]
    
    if north <= south:
        raise ValueError(f"Invalid bbox: North ({north}) must be > South ({south})")
    
    if west >= east:
        raise ValueError(f"Invalid bbox: West ({west}) must be < East ({east})")
    
    logger.info(f"Using CDS bbox [N, W, S, E]: {cds_area}")
    logger.info(f"  North: {north}, South: {south} (span: {north - south}°)")
    logger.info(f"  West: {west}, East: {east} (span: {east - west}°)")
    
    # Validate dates - ERA5-Land has ~5-7 day lag
    from datetime import date as dt
    today = dt.today()
    max_available_date = today - timedelta(days=7)
    
    if end_date > max_available_date:
        logger.warning(f"End date {end_date} may not be available yet (max: ~{max_available_date})")
        logger.warning(f"ERA5-Land typically has 5-7 day lag. Request may fail!")
    
    if start_date > end_date:
        raise ValueError(f"Start date ({start_date}) must be <= end date ({end_date})")
    
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
    
    # Build CDS request
    request = {
        "variable": [variable],
        "year": years,
        "month": months,
        "day": days,
        "daily_statistic": daily_statistic,
        "time_zone": "utc+00:00",
        "frequency": "6_hourly",
        "area": cds_area
    }
    
    logger.info(f"Downloading ERA5 Land Daily: {start_date} to {end_date}")
    logger.info(f"Variable: {variable}, Statistic: {daily_statistic}")
    logger.info("=" * 80)
    logger.info("CDS API REQUEST:")
    logger.info("=" * 80)
    
    import json
    logger.info(json.dumps(request, indent=2, default=str))
    
    logger.info("=" * 80)
    logger.info("REQUEST DETAILS:")
    logger.info(f"  Dataset: derived-era5-land-daily-statistics")
    logger.info(f"  Variable: {request['variable']}")
    logger.info(f"  Daily statistic: {request['daily_statistic']}")
    logger.info(f"  Time zone: {request['time_zone']}")
    logger.info(f"  Frequency: {request['frequency']}")
    logger.info(f"  Years: {request['year']}")
    logger.info(f"  Months: {request['month']}")
    logger.info(f"  Days: {request['day']}")
    logger.info(f"  Area [N,W,S,E]: {request['area']}")
    logger.info(f"  Area interpretation:")
    logger.info(f"    North: {request['area'][0]}°")
    logger.info(f"    West: {request['area'][1]}°")
    logger.info(f"    South: {request['area'][2]}°")
    logger.info(f"    East: {request['area'][3]}°")
    logger.info("=" * 80)
    
    try:
        client = cdsapi.Client()
        logger.info("Submitting request to CDS...")
        result = client.retrieve("derived-era5-land-daily-statistics", request)
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
    bbox: tuple,
    dates_to_process: Optional[List[date]] = None
) -> List[Path]:
    """
    Convert ERA5 Land Daily NetCDF to daily GeoTIFFs.
    Only processes dates specified in dates_to_process (if provided).
    """
    logger = get_run_logger()
    settings = get_settings()
    
    output_dir = get_output_directory(variable, daily_statistic, settings)
    logger.info(f"Saving {variable} ({daily_statistic}) to: {output_dir}")
    
    if dates_to_process:
        logger.info(f"Processing only {len(dates_to_process)} specific dates")
    
    processed_paths = []
    
    try:
        ds = xr.open_dataset(netcdf_path)
        logger.info(f"NetCDF variables: {list(ds.data_vars)}")
        
        # Find the variable
        var_name = None
        if variable in ds.data_vars:
            var_name = variable
        else:
            possible_names = [
                variable,
                variable.replace("_", ""),
                "t2m", "2t", "temperature_2m",
                *[v for v in ds.data_vars if any(part in v for part in variable.split("_"))]
            ]
            for name in possible_names:
                if name in ds.data_vars:
                    var_name = name
                    break
        
        if not var_name:
            raise ValueError(f"Variable '{variable}' not found. Available: {list(ds.data_vars)}")
        
        da = ds[var_name]
        
        # Convert bbox format if needed
        if isinstance(bbox, list):
            bbox = (bbox[1], bbox[2], bbox[3], bbox[0])  # [W, S, E, N]
        
        # Find time dimension
        time_dim = None
        for possible_time_dim in ['time', 'valid_time', 'datetime']:
            if possible_time_dim in da.dims:
                time_dim = possible_time_dim
                break
        
        if time_dim:
            time_values = da[time_dim].values
        else:
            time_values = [date.today()]
        
        # Process each day
        for time_val in time_values:
            if time_dim and time_dim in da.dims:
                daily_data = da.sel({time_dim: time_val})
            else:
                daily_data = da
            
            # Convert time to date
            if isinstance(time_val, (pd.Timestamp, date)):
                day_date = pd.Timestamp(time_val).date()
            else:
                try:
                    day_date = pd.Timestamp(time_val).date()
                except:
                    day_date = date.today()
            
            # Skip if not in dates_to_process (if specified)
            if dates_to_process and day_date not in dates_to_process:
                logger.debug(f"Skipping {day_date} (already exists)")
                continue
            
            # Rename coordinates
            coord_mapping = {}
            for coord in daily_data.dims:
                coord_lower = coord.lower()
                if coord_lower in ['longitude', 'lon', 'long']:
                    coord_mapping[coord] = 'x'
                elif coord_lower in ['latitude', 'lat']:
                    coord_mapping[coord] = 'y'
            
            if coord_mapping:
                daily_data = daily_data.rename(coord_mapping)
            
            # Convert temperature from Kelvin to Celsius
            if "temperature" in variable.lower() or "t2m" in var_name.lower():
                daily_data = daily_data - 273.15
            
            daily_data = daily_data.rio.write_crs("EPSG:4326")
            
            try:
                daily_data = daily_data.rio.clip_box(*bbox)
            except Exception as e:
                logger.warning(f"Could not clip to bbox: {e}")
            
            output_path = output_dir / f"{output_dir.name}_{day_date.strftime('%Y%m%d')}.tif"
            
            daily_data.rio.to_raster(output_path, driver="COG", compress="LZW")
            processed_paths.append(output_path)
            logger.info(f"✓ Processed: {day_date} -> {output_path.name}")
        
        logger.info(f"✓ Successfully processed {len(processed_paths)} days")
        return processed_paths
        
    except Exception as e:
        logger.error(f"✗ Failed to process: {e}")
        raise


@task(retries=3, retry_delay_seconds=30)  # Add retries for HDF/NetCDF errors
def append_to_yearly_historical(
    source_netcdf: Path,
    variable: str,
    daily_statistic: str,
    bbox: tuple,
    dates_to_append: Optional[List[date]] = None
) -> List[Path]:
    """
    Append processed daily data to YEARLY historical NetCDF files.
    Creates separate files for each year: {source}_2024.nc, {source}_2025.nc, etc.

    This is more manageable than one huge historical.nc file and allows:
    - Easy updates (only modify current year)
    - Better performance (load only years needed)
    - Consistent with precipitation data architecture

    FUSE FILESYSTEM FIX: Writes to /tmp first, then copies to final location.
    """
    logger = get_run_logger()
    settings = get_settings()
    import tempfile
    import shutil
    from collections import defaultdict

    dir_name = get_output_directory(variable, daily_statistic, settings).name
    hist_dir = Path(settings.DATA_DIR) / f"{dir_name}_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"📦 Appending data from {source_netcdf.name} to yearly historical files")

    if dates_to_append:
        logger.info(f"  Processing {len(dates_to_append)} specific dates")
    else:
        logger.info(f"  Processing all dates in source file")
    
    updated_files = []

    try:
        # Open source NetCDF
        ds = xr.open_dataset(source_netcdf)
        logger.info(f"  Source variables: {list(ds.data_vars)}")

        # Find the variable
        var_name = None
        if variable in ds.data_vars:
            var_name = variable
        else:
            possible_names = [
                variable, variable.replace("_", ""),
                "t2m", "2t", "temperature_2m",
                *[v for v in ds.data_vars if any(part in v for part in variable.split("_"))]
            ]
            for name in possible_names:
                if name in ds.data_vars:
                    var_name = name
                    break

        if not var_name:
            raise ValueError(f"Variable '{variable}' not found. Available: {list(ds.data_vars)}")

        da = ds[var_name]

        # Find and standardize time dimension
        time_dim = next((d for d in ['time', 'valid_time', 'datetime'] if d in da.dims), None)
        if not time_dim:
            raise ValueError(f"No time dimension found in {da.dims}")
        if time_dim != 'time':
            da = da.rename({time_dim: 'time'})

        # Standardize spatial dimensions
        coord_mapping = {}
        for coord in da.dims:
            coord_lower = coord.lower()
            if coord_lower in ['longitude', 'lon', 'long']:
                coord_mapping[coord] = 'longitude'
            elif coord_lower in ['latitude', 'lat']:
                coord_mapping[coord] = 'latitude'
        if coord_mapping:
            da = da.rename(coord_mapping)

        # Convert temperature from Kelvin to Celsius
        if "temperature" in variable.lower() or "t2m" in var_name.lower():
            da = da - 273.15
            logger.info("  Converted temperature to Celsius")

        # Clip to bbox
        if isinstance(bbox, list):
            bbox = (bbox[1], bbox[2], bbox[3], bbox[0])
        try:
            west, south, east, north = bbox
            da = da.sel(longitude=slice(west, east), latitude=slice(north, south))
            logger.info(f"  Clipped to bbox: {bbox}")
        except Exception as e:
            logger.warning(f"  Could not clip to bbox: {e}")

        # Standardize variable name and attributes
        var_short_name = dir_name
        da.name = var_short_name
        da.attrs.update({
            'long_name': f'{variable} {daily_statistic}',
            'units': 'degrees_celsius' if 'temp' in var_short_name else 'unknown',
            'source': 'ERA5-Land',
            'statistic': daily_statistic
        })

        # Get and filter dates
        all_dates = set(pd.to_datetime(da.time.values).date)
        if dates_to_append:
            all_dates = all_dates & set(dates_to_append)
            # Filter to only dates we want to append - compare dates directly
            dates_to_keep = set(all_dates)
            time_mask = [pd.Timestamp(t).date() in dates_to_keep for t in da.time.values]
            da = da.isel(time=time_mask)

        logger.info(f"  Processing {len(all_dates)} dates")

        # Group dates by year
        dates_by_year = defaultdict(list)
        for d in all_dates:
            dates_by_year[d.year].append(d)

        logger.info(f"  Dates span {len(dates_by_year)} year(s): {sorted(dates_by_year.keys())}")

        # Process each year
        for year, year_dates in sorted(dates_by_year.items()):
            logger.info(f"\n  📅 Processing year {year} ({len(year_dates)} dates)")

            year_file = hist_dir / f"{dir_name}_{year}.nc"

            # FUSE FIX: Create temp directory for this year
            temp_dir = Path(tempfile.mkdtemp(prefix=f"era5_{year}_"))
            temp_file = temp_dir / f"{dir_name}_{year}.nc"

            try:
                # Extract data for this year - compare dates directly
                year_dates_set = set(year_dates)
                year_time_mask = [pd.Timestamp(t).date() in year_dates_set for t in da.time.values]
                year_da = da.isel(time=year_time_mask)

                # Check if yearly file already exists
                if year_file.exists():
                    logger.info(f"    Year file exists, checking for duplicates...")
                    # FUSE FIX: Copy to temp for safe processing
                    shutil.copy2(year_file, temp_file)
                    existing = xr.open_dataset(temp_file, chunks='auto')
                    existing_da = existing[var_short_name]

                    existing_dates = set(pd.to_datetime(existing_da.time.values).date)
                    new_dates = set(year_dates) - existing_dates

                    if not new_dates:
                        logger.info(f"    All {len(year_dates)} dates already exist, skipping")
                        existing.close()
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        continue

                    logger.info(f"    Adding {len(new_dates)} new dates")
                    new_dates_set = set(new_dates)
                    new_dates_mask = [pd.Timestamp(t).date() in new_dates_set for t in year_da.time.values]
                    year_da_filtered = year_da.isel(time=new_dates_mask)
                    combined = xr.concat([existing_da, year_da_filtered], dim='time').sortby('time')
                    existing.close()
                else:
                    logger.info(f"    Creating new year file with {len(year_dates)} dates")
                    combined = year_da

                # Compute time range before writing (while data is still in memory)
                time_count = len(combined.time)
                if time_count > 0:
                    time_min = pd.Timestamp(combined.time.min().values).date()
                    time_max = pd.Timestamp(combined.time.max().values).date()

                # Convert to Dataset with encoding
                year_ds = combined.to_dataset()
                year_ds.attrs['year'] = year

                encoding = {
                    var_short_name: {
                        'chunksizes': (1, 20, 20),
                        'zlib': True,
                        'complevel': 5,
                        'dtype': 'float32'
                    },
                    'time': {
                        'units': 'days since 1970-01-01',
                        'calendar': 'proleptic_gregorian',
                        'dtype': 'float64'
                    }
                }

                # FUSE FIX: Write to temp, then copy
                logger.info(f"    Writing to temp file...")
                try:
                    year_ds.to_netcdf(str(temp_file), mode='w', encoding=encoding, engine='netcdf4')
                    # Ensure data is written to disk
                    import os
                    os.sync()
                    logger.info(f"    ✓ Temp file written successfully")
                except Exception as write_error:
                    logger.error(f"    ✗ Failed to write NetCDF: {write_error}")
                    if temp_file.exists():
                        temp_file.unlink()
                    raise

                logger.info(f"    Copying to: {year_file}")
                shutil.copy2(temp_file, year_file)
                os.sync()

                # Cleanup temp
                shutil.rmtree(temp_dir, ignore_errors=True)

                updated_files.append(year_file)
                logger.info(f"    ✓ Updated {year_file.name}")
                if time_count > 0:
                    logger.info(f"      Time range: {time_min} to {time_max}")
                    logger.info(f"      Total days: {time_count}")

            except Exception as e:
                logger.error(f"    ✗ Failed to process year {year}: {e}")
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                raise

        ds.close()

        logger.info(f"\n✓ Updated {len(updated_files)} yearly file(s)")
        return updated_files

    except Exception as e:
        logger.error(f"✗ Failed to append to yearly historical: {e}")
        raise


@task
def cleanup_raw_files(netcdf_path: Path):
    """Delete raw NetCDF file after processing."""
    logger = get_run_logger()
    try:
        if netcdf_path.exists():
            netcdf_path.unlink()
            logger.info(f"✓ Cleaned up: {netcdf_path.name}")
    except Exception as e:
        logger.warning(f"Could not delete {netcdf_path}: {e}")


@flow(
    name="process-era5-land-daily",
    description="Download and process ERA5 Land Daily with historical archiving",
    retries=1,
    retry_delay_seconds=600
)
def era5_land_daily_flow(
    batch_days: int = 31,
    variables_config: Optional[List[Dict[str, str]]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip_historical_merge: bool = False  # NEW: Skip problematic yearly merge
):
    """ERA5 Land Daily processing with historical NetCDF management."""
    logger = get_run_logger()
    settings = get_settings()
    
    if variables_config is None:
        variables_config = [
            {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
            {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
        ]
    
    if start_date is None or end_date is None:
        today = date.today()
        if end_date is None:
            end_date = today - timedelta(days=7)  # ERA5 Land has ~5-7 day lag
        if start_date is None:
            start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    logger.info(f"Processing from {start_date} to {end_date}")
    all_processed = []
    
    for var_config in variables_config:
        variable = var_config['variable']
        statistic = var_config['statistic']
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing: {variable} - {statistic}")
        logger.info(f"{'='*80}")
        
        # Initialize variables
        missing_download = []
        missing_geotiff = []
        missing_historical = []
        
        # Check which dates are missing
        try:
            missing_info = check_missing_dates(
                start_date=start_date,
                end_date=end_date,
                variable=variable,
                daily_statistic=statistic
            )
            missing_download = missing_info.get('download', [])
            missing_geotiff = missing_info.get('geotiff', [])
            missing_historical = missing_info.get('historical', [])
        except Exception as e:
            logger.error(f"Failed to check missing dates: {e}")
            continue
        
        if not missing_download or len(missing_download) == 0:
            logger.info(f"✓ All data already exists for {variable} - {statistic}")
            continue
        
        # Group missing dates into contiguous batches
        date_batches = []
        if len(missing_download) > 0:
            current_batch_start = missing_download[0]
            current_batch_end = missing_download[0]
            
            for i in range(1, len(missing_download)):
                if missing_download[i] == current_batch_end + timedelta(days=1):
                    current_batch_end = missing_download[i]
                else:
                    date_batches.append((current_batch_start, current_batch_end))
                    current_batch_start = missing_download[i]
                    current_batch_end = missing_download[i]
            
            date_batches.append((current_batch_start, current_batch_end))
        
        if not date_batches:
            logger.info(f"✓ No batches to process for {variable} - {statistic}")
            continue
        
        logger.info(f"Organized into {len(date_batches)} download batch(es)")
        
        # Process each batch of missing dates
        for batch_start, batch_end in date_batches:
            current_start = batch_start
            while current_start <= batch_end:
                current_end = min(current_start + timedelta(days=batch_days - 1), batch_end)
                
                # Get the specific dates in this chunk
                chunk_dates = []
                d = current_start
                while d <= current_end:
                    chunk_dates.append(d)
                    d += timedelta(days=1)
                
                # Which dates need GeoTIFF processing?
                geotiff_dates_in_chunk = [d for d in chunk_dates if d in missing_geotiff]
                
                # Which dates need historical appending?
                hist_dates_in_chunk = [d for d in chunk_dates if d in missing_historical]
                
                try:
                    logger.info(f"\nDownloading batch: {current_start} to {current_end}")
                    logger.info(f"  Will process {len(geotiff_dates_in_chunk)} GeoTIFFs")
                    logger.info(f"  Will append {len(hist_dates_in_chunk)} to historical")
                    
                    # Download batch
                    batch_path = download_era5_land_daily_batch(
                        start_date=current_start,
                        end_date=current_end,
                        variable=variable,
                        daily_statistic=statistic,
                        area=settings.latam_bbox_cds
                    )
                    
                    # Process to GeoTIFFs (only missing dates)
                    if geotiff_dates_in_chunk:
                        processed = process_era5_land_daily_to_geotiff(
                            netcdf_path=batch_path,
                            variable=variable,
                            daily_statistic=statistic,
                            bbox=settings.latam_bbox_raster,
                            dates_to_process=geotiff_dates_in_chunk
                        )
                        all_processed.extend(processed)
                    else:
                        logger.info("  Skipping GeoTIFF processing (all exist)")
                    
                    # Append to yearly historical NetCDF (only missing dates)
                    if not skip_historical_merge:
                        if hist_dates_in_chunk:
                            yearly_files = append_to_yearly_historical(
                                source_netcdf=batch_path,
                                variable=variable,
                                daily_statistic=statistic,
                                bbox=settings.latam_bbox_raster,
                                dates_to_append=hist_dates_in_chunk
                            )
                            logger.info(f"✓ Updated {len(yearly_files)} yearly historical file(s)")
                        else:
                            logger.info("  Skipping historical append (all exist)")
                    else:
                        logger.info("  Skipping historical merge (will merge later)")

                    # Clean up raw file (skip if we're keeping for later merge)
                    if not skip_historical_merge:
                        cleanup_raw_files(batch_path)
                    else:
                        logger.info(f"  Keeping raw file for later merge: {batch_path.name}")
                    
                    logger.info(f"✓ Completed batch: {current_start} to {current_end}")
                    
                except Exception as e:
                    logger.error(f"✗ Failed batch {current_start} to {current_end}: {e}")
                
                current_start = current_end + timedelta(days=1)
    
    # Refresh GeoServer mosaics
    if all_processed:
        from .tasks import refresh_mosaic_shapefile
        from collections import defaultdict
        
        files_by_dir = defaultdict(list)
        for path in all_processed:
            files_by_dir[path.parent].append(path)
        
        logger.info(f"\n{'='*80}")
        logger.info("Refreshing GeoServer mosaics")
        
        for dir_path, files in files_by_dir.items():
            logger.info(f"Refreshing {dir_path.name}: {len(files)} files")
            try:
                refresh_mosaic_shapefile(DataSource.ERA5)
            except Exception as e:
                logger.error(f"Failed to refresh mosaic: {e}")
        
        logger.info(f"\n✓ Successfully processed {len(all_processed)} total files")
    
    return all_processed