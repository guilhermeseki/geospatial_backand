"""
GLM (Geostationary Lightning Mapper) Flash Extent Density (FED) Flow - 30-Minute Resolution

Downloads and processes GOES-16/18/19 GLM Gridded FED data from NASA GHRC DAAC
Outputs 48 GeoTIFF files per day (one per 30-minute bin)

Data: 1440 minute files per day -> 48 x 30-minute GeoTIFFs per day
Source: https://ghrc.nsstc.nasa.gov/home/about-ghrc/ghrc-science-disciplines/lightning
Resolution: 8km x 8km
Output: glm_fed_30min/glm_fed_YYYYMMDD_HHMM.tif (48 files per day)
"""
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import xarray as xr
import pandas as pd
import rasterio
import rioxarray
from pyproj import CRS
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

    # Check Settings object first (from .env file)
    if settings.EARTHDATA_USERNAME and settings.EARTHDATA_PASSWORD:
        logger.info("Found Earthdata credentials in Settings (.env file)")
        return (settings.EARTHDATA_USERNAME, settings.EARTHDATA_PASSWORD)

    # Check environment variables
    import os
    username = os.getenv('EARTHDATA_USERNAME')
    password = os.getenv('EARTHDATA_PASSWORD')

    if username and password:
        logger.info("Found Earthdata credentials in environment variables")
        return (username, password)

    # Check .netrc file
    netrc_file = Path.home() / '.netrc'
    if netrc_file.exists():
        logger.info("Found .netrc file for Earthdata authentication")
        try:
            import netrc
            netrc_obj = netrc.netrc(str(netrc_file))
            auth = netrc_obj.authenticators('urs.earthdata.nasa.gov')
            if auth:
                username, account, password = auth
                logger.info(f"Retrieved credentials for user: {username}")
                return (username, password)
        except Exception as e:
            logger.warning(f"Could not parse .netrc: {e}")
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
                            break

                        if username and password:
                            logger.info(f"Retrieved credentials for user: {username}")
                            return (username, password)

    logger.error("NASA Earthdata credentials not found!")
    logger.error("Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD environment variables")
    raise ValueError("NASA Earthdata credentials required")


@task
def check_missing_30min_bins(
    start_date: date,
    end_date: date
) -> Dict[str, List[date]]:
    """
    Check which dates are missing 30-minute GeoTIFF bins.
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
    geotiff_dir = Path(settings.DATA_DIR) / "glm_fed_30min"

    # Check for complete days (should have 48 files per day)
    complete_dates = set()
    if geotiff_dir.exists():
        for target_date in requested_dates:
            date_str = target_date.strftime('%Y%m%d')
            # Count files for this date
            files = list(geotiff_dir.glob(f"glm_fed_{date_str}_*.tif"))
            if len(files) >= 48:
                complete_dates.add(target_date)
            elif len(files) > 0:
                logger.info(f"  {target_date}: Found {len(files)}/48 files (incomplete)")

    logger.info(f"Found {len(complete_dates)} complete dates (48 files each)")

    # Calculate missing dates
    requested_dates_set = set(requested_dates)
    missing_download = sorted(list(requested_dates_set - complete_dates))

    logger.info(f"Need to process: {len(missing_download)} dates")

    return {
        'download': missing_download
    }


def get_satellite_for_date(target_date: date) -> str:
    """
    Determine which GOES satellite to use based on date.

    GOES-16 (GOES-East): Jan 2018 - Dec 2024
    GOES-18 (GOES-West): Jan 2023 - present
    GOES-19 (GOES-East): Jan 2025 - present (replaced GOES-16)
    """
    if target_date.year >= 2025:
        return "G19"  # GOES-19 for 2025 onwards
    else:
        return "G16"  # GOES-16 for historical data


@task(retries=3, retry_delay_seconds=300, timeout_seconds=14400)  # 4 hours timeout
def download_glm_fed_30min_bins(
    target_date: date,
    username: str,
    password: str
) -> Optional[Path]:
    """
    Download GLM FED minute files and aggregate to 48 x 30-minute bins.

    Saves all 48 bins (not just the max) for subsequent GeoTIFF generation.
    """
    logger = get_run_logger()

    raw_dir = Path(settings.DATA_DIR) / "raw" / "glm_fed_30min"
    raw_dir.mkdir(parents=True, exist_ok=True)

    output_file = raw_dir / f"glm_fed_30min_{target_date.strftime('%Y%m%d')}.nc"

    if output_file.exists():
        logger.info(f"30-min bins already exist: {output_file.name}")
        return output_file

    logger.info(f"=" * 80)
    logger.info(f"DOWNLOADING GLM FED 30-MIN BINS FOR {target_date}")
    logger.info(f"=" * 80)

    # Determine satellite
    satellite = get_satellite_for_date(target_date)
    logger.info(f"Using satellite: GOES-{satellite.replace('G', '')}")

    # Calculate date range: need 29 minutes from previous day for complete first bin
    prev_date = target_date - timedelta(days=1)

    # CMR API endpoint
    cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json"

    logger.info(f"Need data from {prev_date} 23:31 to {target_date} 23:59")

    # Download previous day's files (last 29 minutes)
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
        "page_size": 100
    }

    try:
        response = requests.get(cmr_url, params=params_prev, timeout=60)
        response.raise_for_status()
        prev_granules_all = response.json()['feed']['entry']
        prev_granules = [g for g in prev_granules_all if f"_{satellite}_" in g['title']]
        logger.info(f"Found {len(prev_granules)} {satellite} granule(s) from previous day")
        all_granules.extend(prev_granules)
    except Exception as e:
        logger.warning(f"Could not get previous day data: {e}")
        logger.warning(f"Will proceed with target day only (first bin may be incomplete)")

    # Query for target day (all minutes) with pagination
    logger.info(f"Searching CMR for granules from target day...")
    params_target = {
        "short_name": "glmgoesL3",
        "provider": "GHRC_DAAC",
        "temporal": f"{start_datetime_target},{end_datetime_target}",
        "page_size": 1000
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
            total_hits = int(response.headers.get('CMR-Hits', 0))

            logger.info(f"  Page {page_num}: {len(page_granules)} granules (total: {len(target_granules_all)}/{total_hits})")

            if len(page_granules) < params_target['page_size']:
                break

            page_num += 1

        # Filter for specific satellite
        target_granules = [g for g in target_granules_all if f"_{satellite}_" in g['title']]
        logger.info(f"Found {len(target_granules)} {satellite} granule(s) from target day")
        all_granules.extend(target_granules)

        if len(target_granules) == 0:
            logger.warning(f"No {satellite} data available for {target_date}")
            return None

        # Download granules to temporary directory
        temp_dir = raw_dir / f"temp_{target_date.strftime('%Y%m%d')}"
        temp_dir.mkdir(exist_ok=True)

        logger.info(f"Downloading {len(all_granules)} files...")

        # Set up authentication session
        session = requests.Session()
        session.auth = HTTPBasicAuth(username, password)

        downloaded_files = []

        for i, granule in enumerate(all_granules):
            links = granule.get('links', [])
            download_url = None

            for link in links:
                if link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/data#':
                    download_url = link.get('href')
                    break

            if not download_url:
                continue

            filename = download_url.split('/')[-1]
            local_file = temp_dir / filename

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

        logger.info(f"Downloaded {len(downloaded_files)} files")

        if len(downloaded_files) == 0:
            logger.error("No files successfully downloaded")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        # Parse file timestamps
        logger.info(f"Parsing timestamps from {len(downloaded_files)} files...")
        sorted_files = sorted(downloaded_files, key=lambda f: f.name)
        file_metadata = []

        for nc_file in sorted_files:
            try:
                filename = nc_file.stem
                start_idx = filename.find('_s')
                if start_idx == -1:
                    continue

                start_time_str = filename[start_idx + 2:]
                if '_' in start_time_str:
                    start_time_str = start_time_str.split('_')[0]

                if len(start_time_str) < 13:
                    continue

                year = int(start_time_str[0:4])
                day_of_year = int(start_time_str[4:7])
                hour = int(start_time_str[7:9])
                minute = int(start_time_str[9:11])
                second = int(start_time_str[11:13])

                timestamp = pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=day_of_year - 1)
                timestamp = timestamp.replace(hour=hour, minute=minute, second=second)

                file_metadata.append({
                    'path': nc_file,
                    'timestamp': timestamp
                })

            except Exception as e:
                logger.warning(f"  Could not parse timestamp from {nc_file.name}: {e}")
                continue

        if len(file_metadata) == 0:
            logger.error("Failed to parse any file timestamps")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        logger.info(f"Parsed {len(file_metadata)} file timestamps")
        file_metadata.sort(key=lambda x: x['timestamp'])

        # Load files with Dask
        logger.info(f"Loading {len(file_metadata)} files with Dask...")
        minute_data_list = []
        files_loaded = 0

        for meta in file_metadata:
            try:
                ds = xr.open_dataset(meta['path'], chunks={'y': 200, 'x': 200})

                var_name = None
                if 'flash_extent_density' in ds.data_vars:
                    var_name = 'flash_extent_density'
                elif 'FED' in ds.data_vars:
                    var_name = 'FED'
                else:
                    possible_names = [v for v in ds.data_vars if 'fed' in v.lower() or 'flash' in v.lower()]
                    if possible_names:
                        var_name = possible_names[0]

                if var_name is None:
                    ds.close()
                    continue

                fed_data = ds[var_name]
                fed_data_with_time = fed_data.expand_dims(time=[meta['timestamp']])
                minute_data_list.append(fed_data_with_time)

                files_loaded += 1

                if files_loaded % 200 == 0:
                    logger.info(f"  Registered {files_loaded}/{len(file_metadata)} files")

            except Exception as e:
                logger.warning(f"  Failed to load {meta['path'].name}: {e}")
                continue

        if len(minute_data_list) == 0:
            logger.error("Failed to load any files")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        logger.info(f"Registered {files_loaded} files for lazy loading")

        # Combine into time series
        logger.info(f"Creating time series with {files_loaded} time steps...")
        time_series = xr.concat(minute_data_list, dim='time', join='outer', fill_value=np.nan)
        time_series = time_series.chunk({'time': 50, 'y': 200, 'x': 200})

        time_coords = time_series.coords['time'].values
        time_min = pd.Timestamp(time_coords.min())
        time_max = pd.Timestamp(time_coords.max())
        logger.info(f"  Time range: {time_min} to {time_max}")

        # Resample to fixed 30-minute bins
        logger.info(f"Resampling to 30-minute fixed bins...")
        binned_30min = time_series.resample(time='30min', label='left', closed='left').sum()

        # Filter to only bins from target date (00:00 to 23:30)
        target_start = pd.Timestamp(target_date)
        target_end = target_start + pd.Timedelta(days=1)

        bins_target_day = binned_30min.sel(
            time=slice(target_start, target_end - pd.Timedelta(seconds=1))
        )

        num_bins = len(bins_target_day.time)
        logger.info(f"Created {num_bins} fixed 30-minute bins for {target_date}")
        logger.info(f"Bin times: {bins_target_day.time.values[0]} to {bins_target_day.time.values[-1]}")

        # Compute all bins
        logger.info(f"Computing all {num_bins} bins...")
        all_bins_computed = bins_target_day.compute()

        # Create output dataset with all 48 bins
        output_ds = xr.Dataset({
            'flash_extent_density': all_bins_computed
        })

        # Add metadata
        output_ds.attrs['title'] = f"GLM Flash Extent Density - 30-Minute Bins"
        output_ds.attrs['date'] = target_date.strftime('%Y-%m-%d')
        output_ds.attrs['source'] = f"GOES-{satellite.replace('G', '')} GLM"
        output_ds.attrs['processing'] = f"30-minute bins aggregated from {files_loaded} minute files"
        output_ds.attrs['bin_size'] = "30 minutes"
        output_ds.attrs['num_bins'] = num_bins
        output_ds.attrs['provider'] = "NASA GHRC DAAC"
        output_ds.attrs['doi'] = "10.5067/GLM/GRIDDED/DATA101"

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

        logger.info(f"Created 30-min bins: {output_file.name}")
        logger.info(f"=" * 80)

        return output_file

    except requests.exceptions.RequestException as e:
        logger.error(f"CMR API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Download failed: {e}")
        logger.exception(e)
        return None


@task
def process_30min_bins_to_geotiffs(
    bins_netcdf: Path,
    target_date: date
) -> List[Path]:
    """
    Convert 30-minute bins NetCDF to 48 individual GeoTIFFs.

    Output files: glm_fed_YYYYMMDD_HHMM.tif
    Example: glm_fed_20251121_0000.tif, glm_fed_20251121_0030.tif, etc.
    """
    logger = get_run_logger()
    settings_obj = get_settings()

    output_dir = Path(settings_obj.DATA_DIR) / "glm_fed_30min"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_files = []

    try:
        ds = xr.open_dataset(bins_netcdf)

        if 'flash_extent_density' not in ds.data_vars:
            logger.error(f"Variable 'flash_extent_density' not found in {bins_netcdf}")
            ds.close()
            return []

        fed_data = ds['flash_extent_density']

        # Get satellite info for reprojection
        satellite_name = ds.attrs.get('source', 'GOES-19 GLM')
        if 'GOES-16' in satellite_name or 'G16' in satellite_name:
            sat_lon = -75.2
        elif 'GOES-18' in satellite_name or 'G18' in satellite_name:
            sat_lon = -137.2
        elif 'GOES-19' in satellite_name or 'G19' in satellite_name:
            sat_lon = -75.2
        else:
            sat_lon = -75.2

        sat_height = 35786023.0

        # Process each 30-minute bin
        time_coords = fed_data.coords['time'].values
        logger.info(f"Processing {len(time_coords)} 30-minute bins to GeoTIFFs...")

        for i, time_val in enumerate(time_coords):
            time_pd = pd.Timestamp(time_val)
            time_str = time_pd.strftime('%H%M')
            date_str = target_date.strftime('%Y%m%d')

            output_file = output_dir / f"glm_fed_{date_str}_{time_str}.tif"

            if output_file.exists():
                output_files.append(output_file)
                continue

            # Extract this time step
            bin_data = fed_data.sel(time=time_val)

            # Reproject from GOES to WGS84
            if 'x' in bin_data.dims and 'y' in bin_data.dims:
                # Convert x,y from radians to meters
                x_meters = ds.x.values * sat_height
                y_meters = ds.y.values * sat_height

                fed_geo = xr.DataArray(
                    bin_data.values,
                    coords={'y': y_meters, 'x': x_meters},
                    dims=['y', 'x']
                )

                # Set GOES geostationary CRS
                goes_crs = CRS.from_cf({
                    'grid_mapping_name': 'geostationary',
                    'perspective_point_height': sat_height,
                    'longitude_of_projection_origin': sat_lon,
                    'semi_major_axis': 6378137.0,
                    'semi_minor_axis': 6356752.31414,
                    'sweep_angle_axis': 'x'
                })
                fed_geo = fed_geo.rio.write_crs(goes_crs)

                # Reproject to WGS84
                bin_data = fed_geo.rio.reproject("EPSG:4326")
            else:
                if not bin_data.rio.crs:
                    bin_data = bin_data.rio.write_crs("EPSG:4326")

            # Clip to Brazil bbox
            bbox = settings_obj.brazil_bbox_raster  # (W, S, E, N)
            bin_clipped = bin_data.rio.clip_box(*bbox)

            # Write to Cloud Optimized GeoTIFF
            bin_clipped.rio.to_raster(
                output_file,
                driver="COG",
                compress="LZW",
                dtype="float32",
                tiled=True,
                blockxsize=256,
                blockysize=256
            )

            output_files.append(output_file)

            if (i + 1) % 12 == 0:
                logger.info(f"  Created {i+1}/{len(time_coords)} GeoTIFFs")

        ds.close()

        logger.info(f"Created {len(output_files)} GeoTIFFs in {output_dir}")
        return output_files

    except Exception as e:
        logger.error(f"Failed to process GeoTIFFs: {e}")
        logger.exception(e)
        return []


@task
def create_geoserver_indexer_30min(
    output_dir: Path
) -> Optional[Path]:
    """
    Create GeoServer ImageMosaic indexer for 30-minute resolution files.

    Filename pattern: glm_fed_YYYYMMDD_HHMM.tif
    """
    logger = get_run_logger()

    indexer_file = output_dir / "indexer.properties"
    timeregex_file = output_dir / "timeregex.properties"

    # indexer.properties - configure mosaic
    indexer_content = """TimeAttribute=timestamp
Schema=*the_geom:Polygon,location:String,timestamp:java.util.Date
PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](timestamp)
Recursive=false
Caching=false
"""

    # timeregex.properties - extract timestamp from filename
    # Pattern: glm_fed_YYYYMMDD_HHMM.tif -> capture YYYYMMDD_HHMM
    timeregex_content = """regex=.*glm_fed_(\\d{8})_(\\d{4})\\.tif
format=yyyyMMdd_HHmm
"""

    try:
        with open(indexer_file, 'w') as f:
            f.write(indexer_content)
        logger.info(f"Created {indexer_file}")

        with open(timeregex_file, 'w') as f:
            f.write(timeregex_content)
        logger.info(f"Created {timeregex_file}")

        return indexer_file

    except Exception as e:
        logger.error(f"Failed to create indexer files: {e}")
        return None


@flow(
    name="process-glm-fed-30min",
    description="Download and process GOES GLM FED data to 30-minute GeoTIFFs",
    retries=1,
    retry_delay_seconds=600
)
def glm_fed_30min_flow(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    GLM FED 30-minute resolution data processing flow.

    Downloads minute-level GLM FED data from NASA GHRC DAAC
    and creates 48 GeoTIFF files per day (one per 30-minute bin).

    Args:
        start_date: Start date for processing
        end_date: End date for processing
    """
    logger = get_run_logger()

    # Default: yesterday
    if start_date is None or end_date is None:
        yesterday = date.today() - timedelta(days=1)
        start_date = end_date = yesterday

    logger.info("=" * 80)
    logger.info("GLM FED 30-MINUTE RESOLUTION FLOW")
    logger.info("=" * 80)
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Output: 48 GeoTIFFs per day (30-minute bins)")
    logger.info(f"Format: glm_fed_YYYYMMDD_HHMM.tif")
    logger.info("=" * 80)

    # Check credentials
    try:
        username, password = check_earthdata_credentials()
    except ValueError as e:
        logger.error(str(e))
        return []

    # Check missing dates
    missing_info = check_missing_30min_bins(start_date, end_date)
    missing_download = missing_info['download']

    if not missing_download:
        logger.info("All dates already processed")
        return []

    logger.info(f"Processing {len(missing_download)} missing dates")

    all_output_files = []

    # Create output directory and indexer
    output_dir = Path(settings.DATA_DIR) / "glm_fed_30min"
    output_dir.mkdir(parents=True, exist_ok=True)
    create_geoserver_indexer_30min(output_dir)

    for target_date in missing_download:
        logger.info(f"\nProcessing date: {target_date}")

        try:
            # Download and aggregate to 30-minute bins
            bins_nc = download_glm_fed_30min_bins(target_date, username, password)

            if bins_nc is None:
                logger.warning(f"  Skipping {target_date} - download failed")
                continue

            # Process to 48 GeoTIFFs
            geotiffs = process_30min_bins_to_geotiffs(bins_nc, target_date)
            all_output_files.extend(geotiffs)

            logger.info(f"  Created {len(geotiffs)} GeoTIFFs for {target_date}")

        except Exception as e:
            logger.error(f"  Failed to process {target_date}: {e}")
            continue

    logger.info(f"\nTotal: Created {len(all_output_files)} GeoTIFF files")
    return all_output_files


if __name__ == "__main__":
    # Test run
    result = glm_fed_30min_flow()
    print(f"Processed {len(result)} files")
