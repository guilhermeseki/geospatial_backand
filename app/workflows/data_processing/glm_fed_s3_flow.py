"""
GLM (Geostationary Lightning Mapper) Flash Extent Density (FED) Flow - NOAA S3 Version
Downloads raw GLM L2 point data from NOAA S3 and grids to Brazil bbox

Data: ~4320 files per day (20-second intervals) → 48 x 30-minute FED grids → daily max GeoTIFF
Source: s3://noaa-goes19/GLM-L2-LCFA/ (free, no auth required)
Resolution: ~2km (0.02°)
Coverage: Full Brazil (-75 to -33.5 lon, -35 to 6.5 lat)

Output: Daily GeoTIFF with max FED (flash count per cell) across all 30-min windows
"""
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
import xarray as xr
import pandas as pd
import rasterio
from rasterio.transform import from_bounds
import requests
from prefect import flow, task, get_run_logger
from app.config.settings import get_settings
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

settings = get_settings()

# Grid configuration for Brazil (full coverage)
BRAZIL_BBOX = {
    'west': -75.0,
    'east': -33.5,
    'south': -35.0,
    'north': 6.5
}
GRID_RESOLUTION = 0.02  # ~2.2km at equator
TIME_BIN_MINUTES = 30
S3_BASE_URL = "https://noaa-goes19.s3.amazonaws.com"


def get_satellite_for_date(target_date: date) -> str:
    """
    Determine which GOES satellite to use based on date.
    GOES-19 became GOES-East operational in early 2025.
    """
    goes19_start = date(2025, 2, 1)
    if target_date >= goes19_start:
        return "G19"
    else:
        return "G16"


@task(retries=2, retry_delay_seconds=30)
def list_glm_files_for_day(target_date: date) -> List[str]:
    """
    List all GLM L2 files available for a given day from NOAA S3.
    Returns list of S3 URLs for the day's files.
    """
    logger = get_run_logger()

    satellite = get_satellite_for_date(target_date)
    day_of_year = target_date.timetuple().tm_yday
    year = target_date.year

    # Determine S3 bucket based on satellite
    if satellite == "G19":
        s3_base = "https://noaa-goes19.s3.amazonaws.com"
    elif satellite == "G18":
        s3_base = "https://noaa-goes18.s3.amazonaws.com"
    else:
        s3_base = "https://noaa-goes16.s3.amazonaws.com"

    logger.info(f"Listing GLM files for {target_date} (day {day_of_year}) from {satellite}")

    all_urls = []

    # Query each hour directory
    for hour in range(24):
        prefix = f"GLM-L2-LCFA/{year}/{day_of_year:03d}/{hour:02d}/"
        list_url = f"{s3_base}/?prefix={prefix}&max-keys=1000"

        try:
            response = requests.get(list_url, timeout=30)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)
            ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}

            for contents in root.findall('.//s3:Contents', ns):
                key = contents.find('s3:Key', ns).text
                if key.endswith('.nc') and f'_{satellite}_' in key:
                    all_urls.append(f"{s3_base}/{key}")

        except Exception as e:
            logger.warning(f"Error listing hour {hour:02d}: {e}")
            continue

    logger.info(f"Found {len(all_urls)} GLM files for {target_date}")
    return all_urls


def download_single_file(url: str, temp_dir: Path) -> Optional[Path]:
    """Download a single GLM file."""
    try:
        filename = url.split('/')[-1]
        local_path = temp_dir / filename

        if local_path.exists():
            return local_path

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with open(local_path, 'wb') as f:
            f.write(response.content)

        return local_path
    except Exception:
        return None


@task
def download_glm_files(urls: List[str], temp_dir: Path, max_workers: int = 15) -> List[Path]:
    """
    Download GLM files in parallel.
    """
    logger = get_run_logger()

    temp_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []

    logger.info(f"Downloading {len(urls)} files with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_single_file, url, temp_dir): url for url in urls}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            if result:
                downloaded.append(result)
            completed += 1

            if completed % 500 == 0:
                logger.info(f"  Downloaded {completed}/{len(urls)} files ({len(downloaded)} successful)")

    logger.info(f"Downloaded {len(downloaded)}/{len(urls)} files successfully")
    return downloaded


@task
def create_brazil_grid() -> Tuple[np.ndarray, np.ndarray]:
    """
    Create the target grid for Brazil.
    Returns (lon_centers, lat_centers) arrays.
    """
    lon_centers = np.arange(
        BRAZIL_BBOX['west'] + GRID_RESOLUTION/2,
        BRAZIL_BBOX['east'],
        GRID_RESOLUTION
    )
    lat_centers = np.arange(
        BRAZIL_BBOX['south'] + GRID_RESOLUTION/2,
        BRAZIL_BBOX['north'],
        GRID_RESOLUTION
    )

    return lon_centers, lat_centers


def parse_time_from_filename(filename: str) -> Optional[pd.Timestamp]:
    """
    Parse timestamp from GLM filename.
    Format: OR_GLM-L2-LCFA_G19_s20253200000000_e20253200000200_c20253200000217.nc
    """
    try:
        # Extract start time: s20253200000000 = sYYYYDDDHHMMSSS
        parts = filename.split('_')
        for part in parts:
            if part.startswith('s2'):
                time_str = part[1:]  # Remove 's'
                year = int(time_str[:4])
                doy = int(time_str[4:7])
                hour = int(time_str[7:9])
                minute = int(time_str[9:11])
                second = int(time_str[11:13])

                # Convert day of year to date
                base_date = datetime(year, 1, 1) + timedelta(days=doy - 1)
                return pd.Timestamp(
                    year=base_date.year,
                    month=base_date.month,
                    day=base_date.day,
                    hour=hour,
                    minute=minute,
                    second=second
                )
    except Exception:
        pass
    return None


@task
def grid_flashes_to_fed(
    files: List[Path],
    lon_centers: np.ndarray,
    lat_centers: np.ndarray,
    target_date: date
) -> xr.Dataset:
    """
    Grid flash point data to Flash Extent Density on regular lat/lon grid.

    Process:
    1. Read all flash lat/lon/time from files
    2. Bin flashes into 30-minute windows
    3. For each window, count flashes per grid cell
    4. Return max FED across all windows for each cell
    """
    logger = get_run_logger()

    # Create empty grids for each 30-minute bin (48 bins per day)
    n_bins = 24 * 60 // TIME_BIN_MINUTES  # 48
    n_lat = len(lat_centers)
    n_lon = len(lon_centers)

    # FED grids: count flashes per cell per time bin
    fed_bins = np.zeros((n_bins, n_lat, n_lon), dtype=np.float32)

    logger.info(f"Processing {len(files)} files into {n_bins} time bins of {TIME_BIN_MINUTES} minutes...")
    logger.info(f"Grid size: {n_lat} x {n_lon} = {n_lat * n_lon:,} cells")
    logger.info(f"Brazil bbox: W={BRAZIL_BBOX['west']}, E={BRAZIL_BBOX['east']}, S={BRAZIL_BBOX['south']}, N={BRAZIL_BBOX['north']}")

    # Process files in batches
    batch_size = 200
    total_flashes = 0
    brazil_flashes = 0
    files_processed = 0

    for batch_start in range(0, len(files), batch_size):
        batch_files = files[batch_start:batch_start + batch_size]

        for filepath in batch_files:
            try:
                # Parse time from filename first (faster than opening file)
                file_time = parse_time_from_filename(filepath.name)

                if file_time is None:
                    continue

                # Skip files not from target date
                if file_time.date() != target_date:
                    continue

                with xr.open_dataset(filepath, engine='h5netcdf') as ds:
                    if 'flash_lat' not in ds or 'flash_lon' not in ds:
                        continue

                    flash_lats = ds['flash_lat'].values
                    flash_lons = ds['flash_lon'].values

                    if len(flash_lats) == 0:
                        files_processed += 1
                        continue

                    total_flashes += len(flash_lats)

                    # Filter to Brazil bbox
                    mask = (
                        (flash_lats >= BRAZIL_BBOX['south']) &
                        (flash_lats <= BRAZIL_BBOX['north']) &
                        (flash_lons >= BRAZIL_BBOX['west']) &
                        (flash_lons <= BRAZIL_BBOX['east'])
                    )

                    flash_lats = flash_lats[mask]
                    flash_lons = flash_lons[mask]
                    brazil_flashes += len(flash_lats)

                    if len(flash_lats) == 0:
                        files_processed += 1
                        continue

                    # Determine time bin (0-47 for 30-min bins)
                    minutes_of_day = file_time.hour * 60 + file_time.minute
                    time_bin = min(minutes_of_day // TIME_BIN_MINUTES, n_bins - 1)

                    # Grid the flashes - find which cell each flash belongs to
                    lat_indices = np.searchsorted(lat_centers, flash_lats)
                    lon_indices = np.searchsorted(lon_centers, flash_lons)

                    # Adjust indices (searchsorted returns insertion point)
                    lat_indices = np.clip(lat_indices - 1, 0, n_lat - 1)
                    lon_indices = np.clip(lon_indices - 1, 0, n_lon - 1)

                    # Count flashes per cell using numpy bincount for efficiency
                    for lat_idx, lon_idx in zip(lat_indices, lon_indices):
                        fed_bins[time_bin, lat_idx, lon_idx] += 1

                    files_processed += 1

            except Exception as e:
                continue

        # Progress logging
        progress = batch_start + len(batch_files)
        if progress % 1000 == 0 or progress == len(files):
            logger.info(f"  Processed {progress}/{len(files)} files, {brazil_flashes:,} Brazil flashes")

    logger.info(f"Total flashes: {total_flashes:,}")
    logger.info(f"Brazil flashes: {brazil_flashes:,}")
    logger.info(f"Files processed: {files_processed}")

    # Find maximum FED across all time bins for each cell
    fed_max = np.nanmax(fed_bins, axis=0)
    fed_max_bin = np.nanargmax(fed_bins, axis=0)

    # Create time bin labels (HH:MM format)
    bin_times = [f"{(i * TIME_BIN_MINUTES) // 60:02d}:{(i * TIME_BIN_MINUTES) % 60:02d}" for i in range(n_bins)]

    # Create dataset
    ds = xr.Dataset(
        {
            'flash_extent_density': (['lat', 'lon'], fed_max.astype(np.float32)),
            'max_fed_time_bin': (['lat', 'lon'], fed_max_bin.astype(np.int16)),
        },
        coords={
            'lat': lat_centers,
            'lon': lon_centers,
        },
        attrs={
            'title': f'GLM Flash Extent Density - Daily Maximum ({TIME_BIN_MINUTES}-min bins)',
            'source': f'GOES-{get_satellite_for_date(target_date).replace("G", "")} GLM L2 from NOAA S3',
            'date': str(target_date),
            'resolution_deg': GRID_RESOLUTION,
            'resolution_km': f'{GRID_RESOLUTION * 111:.1f}',
            'time_bin_minutes': TIME_BIN_MINUTES,
            'total_flashes_hemisphere': int(total_flashes),
            'brazil_flashes': int(brazil_flashes),
            'bbox': f"W={BRAZIL_BBOX['west']}, E={BRAZIL_BBOX['east']}, S={BRAZIL_BBOX['south']}, N={BRAZIL_BBOX['north']}",
        }
    )

    # Also store all 48 time bins for optional analysis
    ds['fed_30min_bins'] = (['time_bin', 'lat', 'lon'], fed_bins)
    ds.coords['time_bin'] = bin_times

    return ds


@task
def save_fed_geotiff(
    ds: xr.Dataset,
    target_date: date,
    output_dir: Path
) -> Optional[Path]:
    """
    Save FED data as Cloud Optimized GeoTIFF.
    """
    logger = get_run_logger()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"glm_fed_{target_date.strftime('%Y%m%d')}.tif"

    fed_data = ds['flash_extent_density'].values

    # Validate data
    valid_pixels = np.sum(~np.isnan(fed_data) & (fed_data > 0))
    max_fed = np.nanmax(fed_data)
    total_fed = np.nansum(fed_data)

    logger.info(f"FED stats: max={max_fed:.0f}, total={total_fed:.0f}, pixels_with_lightning={valid_pixels:,}")

    # Create transform (note: lat array is south-to-north, but GeoTIFF needs north-to-south)
    transform = from_bounds(
        BRAZIL_BBOX['west'],
        BRAZIL_BBOX['south'],
        BRAZIL_BBOX['east'],
        BRAZIL_BBOX['north'],
        fed_data.shape[1],  # width (lon)
        fed_data.shape[0],  # height (lat)
    )

    # Write GeoTIFF (flip lat axis since rasterio expects top-to-bottom / north-to-south)
    with rasterio.open(
        output_file,
        'w',
        driver='GTiff',
        height=fed_data.shape[0],
        width=fed_data.shape[1],
        count=1,
        dtype='float32',
        crs='EPSG:4326',
        transform=transform,
        compress='LZW',
        tiled=True,
        blockxsize=256,
        blockysize=256,
        nodata=np.nan,
    ) as dst:
        # Flip vertically for correct geographic orientation
        dst.write(np.flipud(fed_data), 1)

    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"✓ Saved GeoTIFF: {output_file} ({file_size_mb:.1f} MB)")

    return output_file


@task
def cleanup_temp_files(temp_dir: Path):
    """Remove temporary downloaded files."""
    logger = get_run_logger()

    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        logger.info(f"✓ Cleaned up temp directory: {temp_dir}")


@flow(name="GLM FED S3 Daily Flow")
def glm_fed_s3_daily_flow(
    target_date: date,
    cleanup: bool = True,
    force: bool = False
) -> Optional[Path]:
    """
    Process one day of GLM data from NOAA S3 to FED GeoTIFF.

    Args:
        target_date: Date to process
        cleanup: Whether to remove temp files after processing
        force: Reprocess even if output exists

    Returns:
        Path to output GeoTIFF or None if failed
    """
    logger = get_run_logger()

    logger.info(f"=" * 80)
    logger.info(f"GLM FED S3 FLOW - {target_date}")
    logger.info(f"=" * 80)

    settings_obj = get_settings()
    output_dir = Path(settings_obj.DATA_DIR) / "glm_fed"
    temp_dir = Path(settings_obj.DATA_DIR) / "raw" / "glm_s3" / f"temp_{target_date.strftime('%Y%m%d')}"

    # Check if output already exists
    output_file = output_dir / f"glm_fed_{target_date.strftime('%Y%m%d')}.tif"
    if output_file.exists() and not force:
        logger.info(f"✓ Output already exists: {output_file}")
        return output_file

    # Step 1: List files for the day
    urls = list_glm_files_for_day(target_date)

    if not urls:
        logger.error(f"No GLM files found for {target_date}")
        return None

    # Step 2: Download files
    files = download_glm_files(urls, temp_dir, max_workers=15)

    if len(files) < 100:
        logger.warning(f"Only {len(files)} files downloaded, expected ~4300")
        if len(files) == 0:
            logger.error("No files downloaded, aborting")
            return None

    # Step 3: Create target grid
    lon_centers, lat_centers = create_brazil_grid()
    logger.info(f"Grid: {len(lon_centers)} lon x {len(lat_centers)} lat cells")

    # Step 4: Grid flashes to FED
    ds = grid_flashes_to_fed(files, lon_centers, lat_centers, target_date)

    # Step 5: Save GeoTIFF
    output_path = save_fed_geotiff(ds, target_date, output_dir)

    # Step 6: Cleanup
    if cleanup:
        cleanup_temp_files(temp_dir)

    logger.info(f"✓ GLM FED processing complete for {target_date}")
    return output_path


@flow(name="GLM FED S3 Backfill Flow")
def glm_fed_s3_backfill_flow(
    start_date: date,
    end_date: date,
    cleanup: bool = True
) -> List[Path]:
    """
    Process multiple days of GLM data.
    """
    logger = get_run_logger()

    logger.info(f"GLM FED S3 Backfill: {start_date} to {end_date}")

    outputs = []
    current = start_date

    while current <= end_date:
        try:
            result = glm_fed_s3_daily_flow(current, cleanup=cleanup)
            if result:
                outputs.append(result)
        except Exception as e:
            logger.error(f"Failed to process {current}: {e}")

        current += timedelta(days=1)

    logger.info(f"✓ Processed {len(outputs)} days")
    return outputs


if __name__ == "__main__":
    # Test with a single day
    test_date = date(2025, 11, 16)
    result = glm_fed_s3_daily_flow(test_date, cleanup=False)
    print(f"Result: {result}")
