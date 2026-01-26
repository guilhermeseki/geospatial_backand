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
        logger.info("✓ Found Earthdata credentials in Settings (.env file)")
        return (settings.EARTHDATA_USERNAME, settings.EARTHDATA_PASSWORD)

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
                if 'fed_30min_max' in ds.data_vars:
                    existing_hist_dates.update(set(pd.to_datetime(ds['fed_30min_max'].time.values).date))
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

    GOES-16 (GOES-East): Jan 2018 - April 6, 2025
    GOES-18 (GOES-West): Jan 2023 - present
    GOES-19 (GOES-East): April 7, 2025 - present (replaced GOES-16)

    Strategy: Use GOES-19 for April 7 2025+, GOES-16 for earlier dates
    """
    # GOES-19 became operational on April 7, 2025
    goes19_start = date(2025, 4, 7)

    if target_date >= goes19_start:
        return "G19"  # GOES-19 for April 7, 2025 onwards
    else:
        return "G16"  # GOES-16 for historical data


@task(retries=3, retry_delay_seconds=300, timeout_seconds=14400)  # 4 hours timeout
def download_glm_fed_daily(
    target_date: date,
    username: str,
    password: str,
    rolling_step_minutes: int = 10
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

        # Build file metadata without loading data into memory
        file_metadata = []

        for nc_file in sorted_files:
            try:
                # Extract timestamp from filename first (before opening file)
                # NASA GLM format: OR_GLM-L3-GLMF-M6_G{sat}_sYYYYDDDHHMMSS[SS]_e..._c...nc
                # where s = start time, YYYY = year, DDD = day of year, HHMMSS = time
                # GOES-16/18: 13 digits (YYYYDDDHHMMSS)
                # GOES-19: 15 digits (YYYYDDDHHMMSSSS) - has extra subsecond precision
                filename = nc_file.stem
                start_idx = filename.find('_s')
                if start_idx == -1:
                    logger.warning(f"  No start time '_s' found in {nc_file.name}")
                    continue

                # Extract start time string after '_s'
                start_time_str = filename[start_idx + 2:]  # Skip '_s'
                # Get just the timestamp part (before next underscore)
                if '_' in start_time_str:
                    start_time_str = start_time_str.split('_')[0]

                # Parse: YYYYDDDHHMMSS[SS] (13 or 15 digits)
                # First 13 characters are always: YYYYDDDHHMMSS
                if len(start_time_str) < 13:
                    logger.warning(f"  Timestamp too short in {nc_file.name}: {start_time_str}")
                    continue

                year = int(start_time_str[0:4])
                day_of_year = int(start_time_str[4:7])
                hour = int(start_time_str[7:9])
                minute = int(start_time_str[9:11])
                second = int(start_time_str[11:13])
                # Ignore extra digits (subsecond precision) if present

                # Convert day-of-year to datetime
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
            logger.error("✗ Failed to parse any file timestamps")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        logger.info(f"✓ Parsed {len(file_metadata)} file timestamps")

        # Sort by timestamp
        file_metadata.sort(key=lambda x: x['timestamp'])

        # MEMORY-EFFICIENT APPROACH: Process files in small batches
        # Instead of loading all 1400+ files at once, we:
        # 1. Process files in batches of 60 (1 hour of data)
        # 2. Compute running max across batches
        # 3. Never hold more than 60 files in memory at once

        logger.info(f"Processing {len(file_metadata)} files in memory-efficient batches...")

        # First, read one file to get the spatial grid
        first_file = file_metadata[0]['path']
        with xr.open_dataset(first_file) as ds_template:
            # Find FED variable name
            var_name = None
            if 'flash_extent_density' in ds_template.data_vars:
                var_name = 'flash_extent_density'
            elif 'FED' in ds_template.data_vars:
                var_name = 'FED'
            else:
                possible_names = [v for v in ds_template.data_vars if 'fed' in v.lower() or 'flash' in v.lower()]
                if possible_names:
                    var_name = possible_names[0]

            if var_name is None:
                logger.error("✗ Could not find FED variable in files")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None

            # Get spatial shape
            template_da = ds_template[var_name]
            spatial_shape = template_da.shape
            y_coords = ds_template.y.values if 'y' in ds_template.coords else ds_template.latitude.values
            x_coords = ds_template.x.values if 'x' in ds_template.coords else ds_template.longitude.values
            logger.info(f"  Spatial grid: {spatial_shape} (y={len(y_coords)}, x={len(x_coords)})")

        # Initialize running max array (in memory, one 2D grid)
        global_max = np.full(spatial_shape, -np.inf, dtype=np.float32)
        global_max_time = np.full(spatial_shape, pd.Timestamp('1970-01-01').value, dtype='int64')

        # Group files into 30-minute bins based on their timestamps
        # Then compute max for each bin and update running max
        logger.info(f"Grouping {len(file_metadata)} files into 30-minute bins...")

        # Create bins for target date (00:00, 00:30, 01:00, ..., 23:30)
        target_start = pd.Timestamp(target_date)
        bin_edges = pd.date_range(target_start, target_start + pd.Timedelta(days=1), freq='30min')

        # Group files by their 30-minute bin
        files_by_bin = {bin_start: [] for bin_start in bin_edges[:-1]}

        for meta in file_metadata:
            ts = meta['timestamp']
            # Find which bin this file belongs to
            for i, bin_start in enumerate(bin_edges[:-1]):
                bin_end = bin_edges[i + 1]
                if bin_start <= ts < bin_end:
                    files_by_bin[bin_start].append(meta)
                    break

        # Count non-empty bins
        non_empty_bins = [(t, files) for t, files in files_by_bin.items() if files]
        logger.info(f"  {len(non_empty_bins)} bins have data (out of 48 possible)")

        # Process each bin
        for bin_idx, (bin_time, bin_files) in enumerate(non_empty_bins):
            if not bin_files:
                continue

            if (bin_idx + 1) % 12 == 0 or bin_idx == 0:
                logger.info(f"  Processing bin {bin_idx + 1}/{len(non_empty_bins)}: {bin_time} ({len(bin_files)} files)")

            # Sum all FED values in this bin (memory efficient - one file at a time)
            bin_sum = np.zeros(spatial_shape, dtype=np.float32)

            for meta in bin_files:
                try:
                    with xr.open_dataset(meta['path']) as ds:
                        fed_data = ds[var_name].values
                        # Replace NaN with 0 for summing
                        fed_data = np.nan_to_num(fed_data, nan=0.0)
                        bin_sum += fed_data.astype(np.float32)
                except Exception as e:
                    logger.warning(f"    Failed to read {meta['path'].name}: {e}")
                    continue

            # Update running max where this bin's sum is larger
            mask = bin_sum > global_max
            global_max[mask] = bin_sum[mask]
            global_max_time[mask] = bin_time.value  # Store as int64 nanoseconds

        logger.info(f"  ✓ Processed all {len(non_empty_bins)} bins")

        # Convert results to xarray
        max_30min_fed = xr.DataArray(
            global_max,
            dims=['y', 'x'],
            coords={'y': y_coords, 'x': x_coords}
        )

        max_timestamp = xr.DataArray(
            global_max_time.astype('datetime64[ns]'),
            dims=['y', 'x'],
            coords={'y': y_coords, 'x': x_coords}
        )

        # Replace -inf with NaN (no data)
        max_30min_fed = max_30min_fed.where(max_30min_fed > -np.inf)

        logger.info(f"✓ Calculated maximum 30-minute fixed bin for {target_date}")

        # Create output dataset
        output_ds = xr.Dataset({
            'flash_extent_density_30min_max': max_30min_fed,
            'max_30min_timestamp': max_timestamp
        })

        # Add metadata
        output_ds.attrs['title'] = f"GLM Flash Extent Density - Maximum 30-Minute Fixed Bin"
        output_ds.attrs['date'] = target_date.strftime('%Y-%m-%d')
        output_ds.attrs['source'] = f"GOES-{satellite.replace('G', '')} GLM"
        output_ds.attrs['processing'] = f"Fixed 30-minute bins aggregated from {len(downloaded_files)} minute files"
        output_ds.attrs['bin_size'] = "30 minutes"
        output_ds.attrs['bin_method'] = "Fixed bins (00:00-00:30, 00:30-01:00, ..., 23:30-00:00 UTC)"
        output_ds.attrs['aggregation'] = "Sum of flash extent density within each 30-minute bin"
        output_ds.attrs['description'] = f"Maximum flash extent density in any fixed 30-minute bin on {target_date}"
        output_ds.attrs['provider'] = "NASA GHRC DAAC"
        output_ds.attrs['doi'] = "10.5067/GLM/GRIDDED/DATA101"
        output_ds.attrs['note'] = "Uses fixed time bins as standard in research papers, not rolling windows"

        # Add time coordinate for the date (not the specific 30-min window)
        output_ds = output_ds.expand_dims(time=[pd.Timestamp(target_date)])

        # Save to NetCDF
        output_ds.to_netcdf(
            output_file,
            engine='netcdf4',
            encoding={
                'flash_extent_density_30min_max': {
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

        # GLM data is in GOES geostationary projection with x,y in radians
        # Convert to meters and set proper CRS before reprojecting
        if 'x' in fed_data.dims and 'y' in fed_data.dims:
            logger.info("Converting GOES projection to WGS84...")

            # Determine satellite from file metadata
            satellite_name = ds.attrs.get('source', 'GOES-19 GLM')
            if 'GOES-16' in satellite_name or 'G16' in satellite_name:
                sat_lon = -75.2
            elif 'GOES-18' in satellite_name or 'G18' in satellite_name:
                sat_lon = -137.2
            elif 'GOES-19' in satellite_name or 'G19' in satellite_name:
                sat_lon = -75.2
            else:
                logger.warning(f"Unknown satellite in source: {satellite_name}, defaulting to -75.2°W")
                sat_lon = -75.2

            sat_height = 35786023.0  # Geostationary orbit height in meters
            logger.info(f"  Using satellite longitude: {sat_lon}°W")

            # Convert x,y from radians to meters
            x_meters = ds.x.values * sat_height
            y_meters = ds.y.values * sat_height

            # Create new DataArray with meters
            fed_geo = xr.DataArray(
                fed_data.values,
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
            fed_data = fed_geo.rio.reproject("EPSG:4326")
            logger.info(f"  Reprojected to WGS84: {fed_data.shape}")
        else:
            # Already in lat/lon
            if not fed_data.rio.crs:
                fed_data = fed_data.rio.write_crs("EPSG:4326")

        # Clip to Brazil using shapefile
        import geopandas as gpd
        brazil_shp = settings_obj.BRAZIL_SHAPEFILE

        if Path(brazil_shp).exists():
            logger.info(f"  Clipping to Brazil shapefile: {brazil_shp}")
            brazil_gdf = gpd.read_file(brazil_shp)
            # Ensure shapefile is in WGS84
            if brazil_gdf.crs != "EPSG:4326":
                brazil_gdf = brazil_gdf.to_crs("EPSG:4326")

            # Clip using shapefile geometry
            fed_clipped = fed_data.rio.clip(brazil_gdf.geometry.values, brazil_gdf.crs, drop=True, all_touched=False)
            logger.info(f"  Clipped to Brazil shapefile: {fed_clipped.shape}")
        else:
            logger.warning(f"  Brazil shapefile not found: {brazil_shp}")
            logger.info(f"  Falling back to bounding box clipping")
            bbox = settings_obj.brazil_bbox_raster  # (W, S, E, N)
            fed_clipped = fed_data.rio.clip_box(*bbox)
            logger.info(f"  Clipped to Brazil bbox: {fed_clipped.shape}")

        # Normalize to flashes/km²/30min
        # GLM FED grid is ~0.029° in EPSG:4326, pixel area varies with latitude
        logger.info("  Normalizing to flashes/km²/30min...")

        # Get transform to calculate pixel size
        transform = fed_clipped.rio.transform()
        pixel_width = abs(transform.a)  # lon spacing in degrees
        pixel_height = abs(transform.e)  # lat spacing in degrees

        # Create latitude array for normalization
        rows, cols = fed_clipped.shape
        lats = np.zeros((rows, cols))
        for row in range(rows):
            lat = transform.f + (row * transform.e) + (transform.e / 2)
            lats[row, :] = lat

        # Calculate pixel area in km² (varies with latitude)
        km_per_deg_lat = 111.32
        km_per_deg_lon = 111.32 * np.cos(np.radians(lats))
        pixel_area_km2 = (pixel_height * km_per_deg_lat) * (pixel_width * km_per_deg_lon)

        # Normalize: convert from total flashes to flashes/km²/30min
        fed_normalized = fed_clipped / pixel_area_km2
        logger.info(f"  Normalized: mean = {float(fed_normalized.mean()):.2f} flashes/km²/30min")

        # Write to Cloud Optimized GeoTIFF
        fed_normalized.rio.to_raster(
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
    """
    Append GLM FED data to yearly historical NetCDF.

    NOTE: Now builds historical from GeoTIFF files instead of raw NetCDF
    to ensure consistent resolution and normalization.
    """
    logger = get_run_logger()
    settings_obj = get_settings()

    year = target_date.year
    hist_dir = Path(settings_obj.DATA_DIR) / "glm_fed_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    year_file = hist_dir / f"glm_fed_{year}.nc"

    try:
        # Load from GeoTIFF instead of raw NetCDF to ensure consistency
        geotiff_dir = Path(settings_obj.DATA_DIR) / "glm_fed"
        geotiff_file = geotiff_dir / f"glm_fed_{target_date.strftime('%Y%m%d')}.tif"

        if not geotiff_file.exists():
            logger.warning(f"GeoTIFF not found: {geotiff_file.name}, skipping historical append")
            return None

        # Load GeoTIFF as xarray Dataset
        import rasterio
        with rasterio.open(geotiff_file) as src:
            data = src.read(1)
            transform = src.transform

            # Get coordinates from transform
            height, width = data.shape

            # Generate coordinates for first row (longitudes) and first column (latitudes)
            # Use pixel centers (0.5 offset)
            lons = np.array([transform * (col + 0.5, 0.5) for col in range(width)])[:, 0]
            lats = np.array([transform * (0.5, row + 0.5) for row in range(height)])[:, 1]

        # Create xarray Dataset from GeoTIFF
        daily_ds = xr.Dataset(
            {
                'fed_30min_max': (['latitude', 'longitude'], data)
            },
            coords={
                'latitude': lats,
                'longitude': lons,
                'time': pd.Timestamp(target_date)
            }
        )

        # Expand time dimension
        daily_ds = daily_ds.expand_dims('time')

        logger.info(f"Loaded from GeoTIFF: {daily_ds.dims}")

        # NOTE: GeoTIFF data is normalized to flashes/km²/30min during creation
        # And already in WGS84 projection with correct resolution
        # So we just need to append to the yearly file

        if 'latitude' not in daily_ds.dims or 'longitude' not in daily_ds.dims:
            logger.error(f"Missing latitude/longitude dimensions in dataset")
            return None

        # Data is ready - just need to append or create new file
        if year_file.exists():
            # Append to existing file
            logger.info(f"Appending to existing file: {year_file.name}")

            # Data loaded from GeoTIFF is already in WGS84 with lat/lon coordinates
            # No reprojection needed - just append directly
            try:
                with xr.open_dataset(year_file) as existing_ds:
                    # Concatenate along time dimension
                    combined_ds = xr.concat([existing_ds, daily_ds], dim='time')

                    # Sort by time
                    combined_ds = combined_ds.sortby('time')

                    # Save with compression
                    encoding = {var: {'zlib': True, 'complevel': 4} for var in combined_ds.data_vars}
                    combined_ds.to_netcdf(year_file, encoding=encoding)

                    logger.info(f"✓ Appended to historical NetCDF: {year_file.name}")
                    return year_file
            except Exception as e:
                logger.error(f"✗ Failed to append to historical NetCDF: {e}")
                logger.error(traceback.format_exc())
                return None
        else:
            # Create new file
            logger.info(f"Creating new historical file: {year_file.name}")

            # Save with compression
            encoding = {var: {'zlib': True, 'complevel': 4} for var in daily_ds.data_vars}
            try:
                daily_ds.to_netcdf(year_file, encoding=encoding)
                logger.info(f"✓ Created new historical NetCDF: {year_file.name}")
                return year_file
            except Exception as e:
                logger.error(f"✗ Failed to create historical NetCDF: {e}")
                logger.error(traceback.format_exc())
                return None

    except Exception as e:
        logger.error(f"✗ Failed to process GLM historical data: {e}")
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
    end_date: Optional[date] = None,
    rolling_step_minutes: int = 10
):
    """
    GLM FED data processing flow.

    Downloads minute-level GLM FED data from NASA GHRC DAAC
    and aggregates to daily GeoTIFF + NetCDF files.

    Args:
        start_date: Start date for processing
        end_date: End date for processing
        rolling_step_minutes: Step size for rolling windows (default 10).
                              With 30-minute windows:
                              - step=1 → 1440 windows/day (every minute)
                              - step=10 → 144 windows/day (every 10 minutes)
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
    total_dates = len(missing_download)

    for idx, target_date in enumerate(missing_download, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing date {idx}/{total_dates}: {target_date}")
        logger.info(f"{'='*80}")
        
        try:
            # Download and aggregate daily
            daily_nc = download_glm_fed_daily(target_date, username, password, rolling_step_minutes)

            if daily_nc is None:
                logger.warning(f"  ⊘ Skipping {target_date} - download not implemented yet")
                continue
            
            # Process to GeoTIFF
            geotiff = process_glm_fed_to_geotiff(daily_nc, target_date)
            if geotiff:
                processed_files.append(geotiff)

            # Append to yearly historical NetCDF for fast time-series queries
            # Wrapped in try-except to continue processing even if historical append fails
            try:
                hist_file = append_to_yearly_historical_fed(daily_nc, target_date)
                if hist_file:
                    logger.info(f"  ✓ Historical NetCDF updated")
            except Exception as e:
                logger.warning(f"  ⚠ Failed to append to historical NetCDF (continuing anyway): {e}")
                # Continue processing - GeoTIFF is the critical output

        except Exception as e:
            logger.error(f"  ✗ Failed to process {target_date}: {e}")
            continue
    
    logger.info(f"\n✓ Processed {len(processed_files)} files")
    return processed_files


if __name__ == "__main__":
    # Test run
    result = glm_fed_flow()
    print(f"Processed {len(result)} files")
