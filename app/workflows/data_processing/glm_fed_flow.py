"""
GLM (Geostationary Lightning Mapper) Flash Extent Density (FED) Flow
Downloads and processes GOES-16/18/19 GLM Gridded FED data from NASA GHRC DAAC

Data: 1440 minute files per day → aggregated to daily GeoTIFF + NetCDF
Source: https://ghrc.nsstc.nasa.gov/home/about-ghrc/ghrc-science-disciplines/lightning
Resolution: 8km × 8km
"""
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import xarray as xr
import pandas as pd
import rasterio
from prefect import flow, task, get_run_logger
from app.config.settings import get_settings
import requests
from requests.auth import HTTPBasicAuth
import tempfile
import shutil

settings = get_settings()


@task
def check_earthdata_credentials() -> tuple:
    """
    Check for NASA Earthdata credentials.
    
    Returns:
        (username, password) tuple or raises error if not found
    """
    logger = get_run_logger()
    
    # Check environment variables
    import os
    username = os.getenv('EARTHDATA_USERNAME')
    password = os.getenv('EARTHDATA_PASSWORD')
    
    if username and password:
        logger.info("✓ Found Earthdata credentials in environment variables")
        return (username, password)
    
    # Check .netrc file
    netrc_file = Path.home() / '.netrc'
    if netrc_file.exists():
        logger.info("✓ Found .netrc file for Earthdata authentication")
        # Parse .netrc for urs.earthdata.nasa.gov
        try:
            import netrc
            netrc_obj = netrc.netrc(str(netrc_file))
            auth = netrc_obj.authenticators('urs.earthdata.nasa.gov')
            if auth:
                username, account, password = auth
                logger.info(f"✓ Retrieved credentials for user: {username}")
                return (username, password)
        except Exception as e:
            logger.warning(f"  Could not parse .netrc: {e}")
            # Fallback to manual parsing
            with open(netrc_file, 'r') as f:
                lines = f.readlines()
                in_earthdata_block = False
                username = None
                password = None

                for line in lines:
                    line = line.strip()
                    if 'urs.earthdata.nasa.gov' in line:
                        in_earthdata_block = True
                    elif in_earthdata_block:
                        if line.startswith('login'):
                            username = line.split()[1]
                        elif line.startswith('password'):
                            password = line.split()[1]
                        elif line.startswith('machine'):
                            break  # End of our block

                        if username and password:
                            logger.info(f"✓ Retrieved credentials for user: {username}")
                            return (username, password)
    
    logger.error("✗ NASA Earthdata credentials not found!")
    logger.error("  Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD environment variables")
    logger.error("  Or create ~/.netrc with:")
    logger.error("    machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD")
    raise ValueError("NASA Earthdata credentials required")


@task
def check_missing_dates_fed(
    start_date: date,
    end_date: date
) -> Dict[str, List[date]]:
    """
    Check which dates are missing from GeoTIFF and historical NetCDF.
    """
    logger = get_run_logger()
    
    # Generate list of requested dates
    requested_dates = []
    current = start_date
    while current <= end_date:
        requested_dates.append(current)
        current += timedelta(days=1)
    
    logger.info(f"Checking for {len(requested_dates)} dates: {start_date} to {end_date}")
    
    # Get directories
    geotiff_dir = Path(settings.DATA_DIR) / "glm_fed"
    hist_dir = Path(settings.DATA_DIR) / "glm_fed_hist"
    
    # Check GeoTIFF files
    existing_geotiff_dates = set()
    if geotiff_dir.exists():
        for tif_file in geotiff_dir.glob("glm_fed_*.tif"):
            try:
                date_str = tif_file.stem.split('_')[-1]
                file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
                existing_geotiff_dates.add(file_date)
            except Exception as e:
                logger.warning(f"Could not parse date from {tif_file.name}: {e}")
    
    logger.info(f"Found {len(existing_geotiff_dates)} existing GeoTIFF files")
    
    # Check historical NetCDF
    existing_hist_dates = set()
    if hist_dir.exists():
        for nc_file in hist_dir.glob("glm_fed_*.nc"):
            try:
                ds = xr.open_dataset(nc_file, chunks='auto')
                if 'flash_extent_density' in ds.data_vars:
                    existing_hist_dates.update(set(pd.to_datetime(ds['flash_extent_density'].time.values).date))
                ds.close()
            except Exception as e:
                logger.warning(f"Could not read {nc_file.name}: {e}")
    
    logger.info(f"Found {len(existing_hist_dates)} dates in historical NetCDF")
    
    # Calculate missing dates
    requested_dates_set = set(requested_dates)
    missing_geotiff = sorted(list(requested_dates_set - existing_geotiff_dates))
    missing_historical = sorted(list(requested_dates_set - existing_hist_dates))
    missing_download = sorted(list(set(missing_geotiff) | set(missing_historical)))
    
    logger.info(f"Missing from GeoTIFF: {len(missing_geotiff)} dates")
    logger.info(f"Missing from historical: {len(missing_historical)} dates")
    logger.info(f"Need to download: {len(missing_download)} dates")
    
    return {
        'geotiff': missing_geotiff,
        'historical': missing_historical,
        'download': missing_download
    }


def get_satellite_for_date(target_date: date) -> str:
    """
    Determine which GOES satellite to use based on date.

    GOES-16 (GOES-East): Jan 2018 - Dec 2024
    GOES-18 (GOES-West): Jan 2023 - present
    GOES-19 (GOES-East): Jan 2025 - present (replaced GOES-16)

    Strategy: Use GOES-19 for 2025+, GOES-16 for earlier dates
    """
    if target_date.year >= 2025:
        return "G19"  # GOES-19 for 2025 onwards
    else:
        return "G16"  # GOES-16 for historical data


@task(retries=3, retry_delay_seconds=300, timeout_seconds=7200)
def download_glm_fed_daily(
    target_date: date,
    username: str,
    password: str
) -> Optional[Path]:
    """
    Download GLM FED minute files for target day + 29 minutes from previous day.

    Calculates 30-minute rolling windows that cross midnight boundaries.
    Windows belong to the day when they END.

    For target_date D:
    - Need: D-1 23:31 to D 23:59 (29 + 1440 = 1469 minutes)
    - Calculate rolling 30-min windows
    - Extract windows ending on day D (00:00 to 23:59)
    - Save max window per grid cell
    """
    logger = get_run_logger()

    raw_dir = Path(settings.DATA_DIR) / "raw" / "glm_fed"
    raw_dir.mkdir(parents=True, exist_ok=True)

    output_file = raw_dir / f"glm_fed_daily_{target_date.strftime('%Y%m%d')}.nc"

    if output_file.exists():
        logger.info(f"✓ Daily aggregate already exists: {output_file.name}")
        return output_file

    logger.info(f"=" * 80)
    logger.info(f"DOWNLOADING GLM FED DATA FOR {target_date}")
    logger.info(f"=" * 80)

    # Determine satellite
    satellite = get_satellite_for_date(target_date)
    logger.info(f"Using satellite: GOES-{satellite.replace('G', '')}")

    # Calculate date range: need 29 minutes from previous day
    prev_date = target_date - timedelta(days=1)

    # CMR API endpoint
    cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json"

    # Build date range: need prev_day 23:31 to target_day 23:59
    # Download files for both days, then filter to specific time range
    logger.info(f"Need data from {prev_date} 23:31 to {target_date} 23:59")

    # Download previous day's files (will filter to 23:31-23:59 later)
    start_datetime_prev = f"{prev_date}T23:31:00Z"
    end_datetime_prev = f"{prev_date}T23:59:59Z"

    # Download target day's files (all of them)
    start_datetime_target = f"{target_date}T00:00:00Z"
    end_datetime_target = f"{target_date}T23:59:59Z"

    all_granules = []

    # Query for previous day (last 29 minutes)
    logger.info(f"Searching CMR for granules from previous day...")
    params_prev = {
        "short_name": "glmgoesL3",
        "provider": "GHRC_DAAC",
        "temporal": f"{start_datetime_prev},{end_datetime_prev}",
        "page_size": 100  # Get ~60 (29 min × 2 satellites), filter later
    }

    try:
        response = requests.get(cmr_url, params=params_prev, timeout=60)
        response.raise_for_status()
        prev_granules_all = response.json()['feed']['entry']
        # Filter for specific satellite by checking filename
        prev_granules = [g for g in prev_granules_all if f"_{satellite}_" in g['title']]
        logger.info(f"✓ Found {len(prev_granules)} {satellite} granule(s) from previous day")
        all_granules.extend(prev_granules)
    except Exception as e:
        logger.warning(f"⚠ Could not get previous day data: {e}")
        logger.warning(f"  Will proceed with target day only (windows may be incomplete)")

    # Query for target day (all minutes) - use pagination to get all results
    logger.info(f"Searching CMR for granules from target day...")
    params_target = {
        "short_name": "glmgoesL3",
        "provider": "GHRC_DAAC",
        "temporal": f"{start_datetime_target},{end_datetime_target}",
        "page_size": 1000  # CMR limit is 1000 per page
    }

    try:
        target_granules_all = []
        page_num = 1

        while True:
            params_page = params_target.copy()
            params_page['page_num'] = page_num

            response = requests.get(cmr_url, params=params_page, timeout=60)
            response.raise_for_status()

            page_granules = response.json()['feed']['entry']
            if not page_granules:
                break

            target_granules_all.extend(page_granules)

            # Check CMR-Hits header to see total available
            total_hits = int(response.headers.get('CMR-Hits', 0))

            logger.info(f"  Page {page_num}: {len(page_granules)} granules (total so far: {len(target_granules_all)}/{total_hits})")

            if len(page_granules) < params_target['page_size']:
                break  # Last page

            page_num += 1

        # Filter for specific satellite by checking filename
        target_granules = [g for g in target_granules_all if f"_{satellite}_" in g['title']]
        logger.info(f"✓ Found {len(target_granules)} {satellite} granule(s) from target day (out of {len(target_granules_all)} total)")
        all_granules.extend(target_granules)

        if len(target_granules) == 0:
            logger.warning(f"⚠ No {satellite} data available for {target_date}")
            logger.warning(f"  GLM FED data may not be available for this date")
            return None

        # Download granules to temporary directory
        temp_dir = raw_dir / f"temp_{target_date.strftime('%Y%m%d')}"
        temp_dir.mkdir(exist_ok=True)

        logger.info(f"Downloading {len(all_granules)} files (includes 29 min from previous day)...")

        # Set up authentication session
        session = requests.Session()
        session.auth = HTTPBasicAuth(username, password)

        downloaded_files = []

        for i, granule in enumerate(all_granules):
            # Get download URL
            links = granule.get('links', [])
            download_url = None

            for link in links:
                if link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/data#':
                    download_url = link.get('href')
                    break

            if not download_url:
                logger.warning(f"  No download URL for granule {i+1}")
                continue

            # Extract filename
            filename = download_url.split('/')[-1]
            local_file = temp_dir / filename

            # Download file
            if not local_file.exists():
                try:
                    file_response = session.get(download_url, timeout=120, stream=True)
                    file_response.raise_for_status()

                    with open(local_file, 'wb') as f:
                        for chunk in file_response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    downloaded_files.append(local_file)

                    if (i + 1) % 100 == 0:
                        logger.info(f"  Downloaded {i+1}/{len(all_granules)} files")

                except Exception as e:
                    logger.warning(f"  Failed to download {filename}: {e}")
                    continue
            else:
                downloaded_files.append(local_file)

        logger.info(f"✓ Downloaded {len(downloaded_files)} files")

        if len(downloaded_files) == 0:
            logger.error("✗ No files successfully downloaded")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        # Calculate 30-minute rolling windows across midnight boundaries
        logger.info(f"Calculating 30-minute rolling windows for {len(downloaded_files)} files...")
        logger.info(f"  Windows will cross midnight boundary from {prev_date} to {target_date}")

        # Sort files by filename to ensure chronological order
        sorted_files = sorted(downloaded_files, key=lambda f: f.name)

        # Load all minute data into a time series
        minute_data_list = []
        timestamps = []
        files_loaded = 0

        for nc_file in sorted_files:
            try:
                ds = xr.open_dataset(nc_file)

                # The variable name might be 'flash_extent_density' or 'FED'
                var_name = None
                if 'flash_extent_density' in ds.data_vars:
                    var_name = 'flash_extent_density'
                elif 'FED' in ds.data_vars:
                    var_name = 'FED'
                else:
                    # Try to find it
                    possible_names = [v for v in ds.data_vars if 'fed' in v.lower() or 'flash' in v.lower()]
                    if possible_names:
                        var_name = possible_names[0]

                if var_name is None:
                    logger.warning(f"  Could not find FED variable in {nc_file.name}")
                    ds.close()
                    continue

                fed_data = ds[var_name]
                minute_data_list.append(fed_data)

                # Extract timestamp from filename
                # Filename format: GLM_Gridded_FED_G16_YYYYMMDD_HHMMSS.nc
                try:
                    parts = nc_file.stem.split('_')
                    date_str = parts[-2]  # YYYYMMDD
                    time_str = parts[-1]  # HHMMSS

                    year = int(date_str[0:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                    hour = int(time_str[0:2])
                    minute = int(time_str[2:4])
                    second = int(time_str[4:6])

                    timestamp = pd.Timestamp(year=year, month=month, day=day,
                                            hour=hour, minute=minute, second=second)
                    timestamps.append(timestamp)
                except Exception as e:
                    logger.warning(f"  Could not parse timestamp from {nc_file.name}: {e}")
                    ds.close()
                    continue

                files_loaded += 1
                ds.close()

                if files_loaded % 100 == 0:
                    logger.info(f"  Loaded {files_loaded}/{len(downloaded_files)} files")

            except Exception as e:
                logger.warning(f"  Failed to load {nc_file.name}: {e}")
                continue

        if len(minute_data_list) == 0:
            logger.error("✗ Failed to load any files")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        logger.info(f"✓ Loaded {files_loaded} minute files")

        # Combine into time series dataset
        logger.info(f"Creating time series dataset with {files_loaded} time steps...")
        time_series = xr.concat(minute_data_list, dim='time')
        time_series['time'] = timestamps

        # Verify timestamps span the correct range
        time_min = pd.Timestamp(timestamps).min()
        time_max = pd.Timestamp(timestamps).max()
        logger.info(f"  Time range: {time_min} to {time_max}")

        # Calculate 30-minute rolling sum
        logger.info(f"Calculating 30-minute rolling windows...")
        window_size = 30  # 30 minutes

        # Rolling sum along time dimension
        # At index i, this gives the sum of minutes [i-29, i-28, ..., i-1, i]
        # So the value at time T represents the window ENDING at time T
        rolling_30min = time_series.rolling(time=window_size, min_periods=window_size).sum()

        # Filter to only keep windows that END on the target date
        logger.info(f"Filtering to windows ending on {target_date}...")
        target_start = pd.Timestamp(target_date)  # 00:00:00
        target_end = target_start + pd.Timedelta(days=1)  # 00:00:00 next day

        # Select only windows ending between target_start and target_end
        rolling_target_day = rolling_30min.sel(
            time=slice(target_start, target_end - pd.Timedelta(seconds=1))
        )

        num_windows = len(rolling_target_day.time)
        logger.info(f"  Kept {num_windows} windows ending on {target_date}")

        # Find maximum 30-min window for each grid cell (among windows ending on target date)
        logger.info(f"Finding maximum 30-minute window per grid cell...")
        max_30min_fed = rolling_target_day.max(dim='time')

        # Find the time index of maximum for each grid cell
        max_time_idx = rolling_target_day.argmax(dim='time')

        # Convert time index to actual timestamp
        target_timestamps = rolling_target_day.time.values
        max_timestamp = xr.DataArray(
            [target_timestamps[int(idx)] if int(idx) < len(target_timestamps) else target_timestamps[0]
             for idx in max_time_idx.values.flat],
            dims=max_time_idx.dims,
            coords=max_time_idx.coords
        ).reshape(max_time_idx.shape)

        logger.info(f"✓ Calculated maximum 30-minute windows for {target_date}")

        # Create output dataset
        output_ds = xr.Dataset({
            'flash_extent_density_30min_max': max_30min_fed,
            'max_30min_timestamp': max_timestamp
        })

        # Add metadata
        output_ds.attrs['title'] = f"GLM Flash Extent Density - Maximum 30-Minute Window"
        output_ds.attrs['date'] = target_date.strftime('%Y-%m-%d')
        output_ds.attrs['source'] = f"GOES-{satellite.replace('G', '')} GLM"
        output_ds.attrs['processing'] = f"Maximum 30-minute rolling window from {files_loaded} minute files"
        output_ds.attrs['window_size'] = "30 minutes"
        output_ds.attrs['window_assignment'] = "Windows belong to the day when they END"
        output_ds.attrs['midnight_crossing'] = f"Windows cross midnight from {prev_date} 23:31 to {target_date} 23:59"
        output_ds.attrs['description'] = f"Maximum flash extent density in any 30-minute window ending on {target_date}"
        output_ds.attrs['provider'] = "NASA GHRC DAAC"
        output_ds.attrs['doi'] = "10.5067/GLM/GRIDDED/DATA101"

        # Add time coordinate for the date (not the specific 30-min window)
        output_ds = output_ds.expand_dims(time=[pd.Timestamp(target_date)])

        # Save to NetCDF
        output_ds.to_netcdf(
            output_file,
            engine='netcdf4',
            encoding={
                'flash_extent_density': {
                    'zlib': True,
                    'complevel': 5,
                    'dtype': 'float32'
                }
            }
        )

        output_ds.close()

        # Cleanup temporary directory
        logger.info(f"Cleaning up temporary files...")
        shutil.rmtree(temp_dir, ignore_errors=True)

        logger.info(f"✓ Created daily aggregate: {output_file.name}")
        logger.info(f"=" * 80)

        return output_file

    except requests.exceptions.RequestException as e:
        logger.error(f"✗ CMR API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"✗ Download failed: {e}")
        logger.exception(e)
        return None


@task
def process_glm_fed_to_geotiff(
    daily_netcdf: Path,
    target_date: date
) -> Optional[Path]:
    """Convert GLM FED daily NetCDF to GeoTIFF for GeoServer."""
    logger = get_run_logger()
    settings_obj = get_settings()

    output_dir = Path(settings_obj.DATA_DIR) / "glm_fed"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"glm_fed_{target_date.strftime('%Y%m%d')}.tif"

    if output_file.exists():
        logger.info(f"✓ GeoTIFF already exists: {output_file.name}")
        return output_file

    try:
        ds = xr.open_dataset(daily_netcdf)

        # Check for variable (30-min max)
        if 'flash_extent_density_30min_max' not in ds.data_vars:
            logger.error(f"Variable 'flash_extent_density_30min_max' not found in {daily_netcdf}")
            ds.close()
            return None

        fed_data = ds['flash_extent_density_30min_max']

        # Remove time dimension if present (since it's a single day)
        if 'time' in fed_data.dims:
            fed_data = fed_data.squeeze('time', drop=True)

        # Ensure CRS is set
        if not fed_data.rio.crs:
            fed_data = fed_data.rio.write_crs("EPSG:4326")

        # Clip to Latin America bbox
        bbox = settings_obj.latam_bbox_raster  # (W, S, E, N)
        fed_clipped = fed_data.rio.clip_box(*bbox)

        # Write to Cloud Optimized GeoTIFF
        fed_clipped.rio.to_raster(
            output_file,
            driver="COG",
            compress="LZW",
            dtype="float32",
            tiled=True,
            blockxsize=256,
            blockysize=256
        )

        ds.close()

        logger.info(f"✓ Created GeoTIFF: {output_file.name}")
        return output_file

    except Exception as e:
        logger.error(f"✗ Failed to process GeoTIFF: {e}")
        logger.exception(e)
        return None


@task
def append_to_yearly_historical_fed(
    daily_netcdf: Path,
    target_date: date
) -> Optional[Path]:
    """Append GLM FED data to yearly historical NetCDF."""
    logger = get_run_logger()
    settings_obj = get_settings()

    year = target_date.year
    hist_dir = Path(settings_obj.DATA_DIR) / "glm_fed_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    year_file = hist_dir / f"glm_fed_{year}.nc"

    try:
        # Load the daily NetCDF
        daily_ds = xr.open_dataset(daily_netcdf)

        if 'flash_extent_density_30min_max' not in daily_ds.data_vars:
            logger.error(f"Variable 'flash_extent_density_30min_max' not found in {daily_netcdf}")
            daily_ds.close()
            return None

        # Ensure time dimension exists
        if 'time' not in daily_ds.dims:
            daily_ds = daily_ds.expand_dims(time=[pd.Timestamp(target_date)])

        # Rename variable to simpler name for storage
        daily_ds = daily_ds.rename({
            'flash_extent_density_30min_max': 'fed_30min_max',
            'max_30min_timestamp': 'fed_30min_time'
        })

        # Apply Latin America bounding box
        bbox = settings_obj.latam_bbox_raster  # (W, S, E, N)
        W, S, E, N = bbox

        # Get coordinate names (might be 'latitude'/'longitude' or 'lat'/'lon')
        lat_name = 'latitude' if 'latitude' in daily_ds.dims else 'lat'
        lon_name = 'longitude' if 'longitude' in daily_ds.dims else 'lon'

        # Clip to bbox
        daily_ds_clipped = daily_ds.sel(
            {lat_name: slice(S, N), lon_name: slice(W, E)}
        )

        if year_file.exists():
            # Append to existing file
            logger.info(f"Appending to existing file: {year_file.name}")

            # Open existing file
            existing_ds = xr.open_dataset(year_file, chunks='auto')

            # Check if date already exists
            existing_times = pd.to_datetime(existing_ds.time.values)
            target_time = pd.Timestamp(target_date)

            if target_time in existing_times:
                logger.info(f"  Date {target_date} already exists in historical file")
                existing_ds.close()
                daily_ds.close()
                return year_file

            # Concatenate along time dimension
            combined = xr.concat([existing_ds, daily_ds_clipped], dim='time')

            # Sort by time
            combined = combined.sortby('time')

            existing_ds.close()

            # Write back with chunking
            combined.to_netcdf(
                year_file,
                mode='w',
                engine='netcdf4',
                encoding={
                    'fed_30min_max': {
                        'zlib': True,
                        'complevel': 5,
                        'dtype': 'float32',
                        'chunksizes': (1, 20, 20)  # time, lat, lon
                    },
                    'fed_30min_time': {
                        'zlib': True,
                        'complevel': 5,
                        'dtype': 'int64',
                        'chunksizes': (1, 20, 20)
                    },
                    'time': {'dtype': 'int64'},
                    lat_name: {'dtype': 'float32'},
                    lon_name: {'dtype': 'float32'}
                }
            )

            combined.close()
            logger.info(f"✓ Appended {target_date} to {year_file.name}")

        else:
            # Create new file
            logger.info(f"Creating new yearly file: {year_file.name}")

            daily_ds_clipped.to_netcdf(
                year_file,
                engine='netcdf4',
                encoding={
                    'fed_30min_max': {
                        'zlib': True,
                        'complevel': 5,
                        'dtype': 'float32',
                        'chunksizes': (1, 20, 20)
                    },
                    'fed_30min_time': {
                        'zlib': True,
                        'complevel': 5,
                        'dtype': 'int64',
                        'chunksizes': (1, 20, 20)
                    },
                    'time': {'dtype': 'int64'},
                    lat_name: {'dtype': 'float32'},
                    lon_name: {'dtype': 'float32'}
                }
            )

            logger.info(f"✓ Created {year_file.name}")

        daily_ds.close()
        return year_file

    except Exception as e:
        logger.error(f"✗ Failed to append to historical NetCDF: {e}")
        logger.exception(e)
        return None


@flow(
    name="process-glm-fed-data",
    description="Download and process GOES GLM Flash Extent Density data",
    retries=1,
    retry_delay_seconds=600
)
def glm_fed_flow(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    GLM FED data processing flow.
    
    Downloads minute-level GLM FED data from NASA GHRC DAAC
    and aggregates to daily GeoTIFF + NetCDF files.
    """
    logger = get_run_logger()
    
    # Default: yesterday
    if start_date is None or end_date is None:
        yesterday = date.today() - timedelta(days=1)
        start_date = end_date = yesterday
    
    logger.info("=" * 80)
    logger.info("GLM FED DATA PROCESSING FLOW")
    logger.info("=" * 80)
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Source: NASA GHRC DAAC - GLM Gridded Flash Extent Density")
    logger.info(f"Resolution: 8km × 8km")
    logger.info("=" * 80)
    
    # Check credentials
    try:
        username, password = check_earthdata_credentials()
    except ValueError as e:
        logger.error(str(e))
        return []
    
    # Check missing dates
    missing_info = check_missing_dates_fed(start_date, end_date)
    missing_download = missing_info['download']
    
    if not missing_download:
        logger.info("✓ All dates already processed")
        return []
    
    logger.info(f"Processing {len(missing_download)} missing dates")
    
    processed_files = []
    
    for target_date in missing_download:
        logger.info(f"\nProcessing date: {target_date}")
        
        try:
            # Download and aggregate daily
            daily_nc = download_glm_fed_daily(target_date, username, password)
            
            if daily_nc is None:
                logger.warning(f"  ⊘ Skipping {target_date} - download not implemented yet")
                continue
            
            # Process to GeoTIFF
            geotiff = process_glm_fed_to_geotiff(daily_nc, target_date)
            if geotiff:
                processed_files.append(geotiff)
            
            # Append to historical
            hist_file = append_to_yearly_historical_fed(daily_nc, target_date)
            
        except Exception as e:
            logger.error(f"  ✗ Failed to process {target_date}: {e}")
            continue
    
    logger.info(f"\n✓ Processed {len(processed_files)} files")
    return processed_files


if __name__ == "__main__":
    # Test run
    result = glm_fed_flow()
    print(f"Processed {len(result)} files")
