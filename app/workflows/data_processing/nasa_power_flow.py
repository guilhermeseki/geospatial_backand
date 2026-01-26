"""
NASA POWER Solar Radiation Flow - Daily GHI Processing

This flow downloads NASA POWER solar radiation data (Global Horizontal Irradiance)
via their free REST API and processes it into:
1. Daily GeoTIFF files for GeoServer time-enabled mosaics
2. Yearly historical NetCDF files for fast API queries

Data Source: NASA POWER (Prediction Of Worldwide Energy Resources)
- Parameter: ALLSKY_SFC_SW_DWN (All Sky Surface Shortwave Downward Irradiance = GHI)
- Spatial Resolution: 0.5° (~55km)
- Temporal Resolution: Daily totals
- Coverage: Global (all of Brazil and Latin America)
- Period: 1981-present (near real-time, ~3-7 day lag)
- Units: kWh/m²/day (already computed, no conversion needed!)
- API: Free, no authentication required
"""
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import requests
import xarray as xr
import numpy as np
import pandas as pd
import rioxarray
from prefect import flow, task, get_run_logger
from app.config.settings import get_settings


@task
def check_missing_dates(
    start_date: date,
    end_date: date
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
    geotiff_dir = Path(settings.DATA_DIR) / "solar_radiation"
    hist_dir = Path(settings.DATA_DIR) / "solar_radiation_hist"

    # Check GeoTIFF files
    existing_geotiff_dates = set()
    if geotiff_dir.exists():
        for tif_file in geotiff_dir.glob("solar_radiation_*.tif"):
            try:
                date_str = tif_file.stem.split('_')[-1]
                file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
                existing_geotiff_dates.add(file_date)
            except Exception as e:
                logger.warning(f"Could not parse date from {tif_file.name}: {e}")

    logger.info(f"Found {len(existing_geotiff_dates)} existing GeoTIFF files")

    # Check historical NetCDF (yearly files)
    existing_hist_dates = set()
    if hist_dir.exists():
        for year_file in hist_dir.glob("solar_radiation_*.nc"):
            try:
                ds = xr.open_dataset(year_file, chunks='auto')
                if 'solar_radiation' in ds.data_vars:
                    file_dates = set(pd.to_datetime(ds['solar_radiation'].time.values).date)
                    existing_hist_dates.update(file_dates)
                ds.close()
            except Exception as e:
                logger.warning(f"Could not read {year_file.name}: {e}")

    logger.info(f"Found {len(existing_hist_dates)} dates in historical NetCDF")

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


@task(retries=3, retry_delay_seconds=60)
def download_nasa_power_tile(
    start_date: date,
    end_date: date,
    tile_bbox: tuple,
    tile_index: int
) -> Path:
    """
    Download NASA POWER GHI data for a single 10° × 10° tile.

    NASA POWER regional API has a maximum of 10° range in both lat and lon.

    Args:
        start_date: First date to download
        end_date: Last date to download
        tile_bbox: Bounding box (west, south, east, north) for this tile
        tile_index: Tile number for filename

    Returns:
        Path to downloaded NetCDF file
    """
    logger = get_run_logger()
    settings = get_settings()

    west, south, east, north = tile_bbox

    # Validate tile size (NASA POWER limit: max 10° in lat/lon)
    lat_range = north - south
    lon_range = east - west

    if lat_range > 10 or lon_range > 10:
        raise ValueError(f"Tile too large: {lat_range}° × {lon_range}° (max 10° × 10°)")

    # Prepare output path
    raw_dir = Path(settings.DATA_DIR) / "raw" / "nasa_power"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    output_path = raw_dir / f"ghi_tile{tile_index:02d}_{start_str}_{end_str}.nc"

    if output_path.exists():
        logger.info(f"Tile {tile_index} already downloaded: {output_path.name}")
        return output_path

    # Build NASA POWER API URL
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/regional"

    params = {
        'parameters': 'ALLSKY_SFC_SW_DWN',  # GHI parameter
        'community': 'RE',  # Renewable Energy community
        'latitude-min': south,
        'latitude-max': north,
        'longitude-min': west,
        'longitude-max': east,
        'start': start_str,
        'end': end_str,
        'format': 'NETCDF'
    }

    logger.info(f"Downloading tile {tile_index}: ({south}, {west}) to ({north}, {east})")
    logger.info(f"  Size: {lat_range:.1f}° × {lon_range:.1f}°")

    try:
        response = requests.get(base_url, params=params, timeout=300)
        response.raise_for_status()

        # Save NetCDF content
        with open(output_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"✓ Tile {tile_index} downloaded: {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return output_path

    except Exception as e:
        logger.error(f"✗ Tile {tile_index} download failed: {e}")
        if output_path.exists():
            output_path.unlink()
        raise


@task
def merge_tiles(tile_paths: List[Path], output_path: Path) -> Path:
    """
    Merge multiple NASA POWER tiles into a single NetCDF file.

    Args:
        tile_paths: List of paths to tile NetCDF files
        output_path: Path for merged output file

    Returns:
        Path to merged NetCDF file
    """
    logger = get_run_logger()

    if output_path.exists():
        logger.info(f"Merged file already exists: {output_path}")
        return output_path

    logger.info(f"Merging {len(tile_paths)} tiles...")

    # Open all tiles
    tiles = []
    for tile_path in tile_paths:
        ds = xr.open_dataset(tile_path)
        tiles.append(ds)

    # Combine tiles
    # NASA POWER tiles should have the same time dimension but different spatial coverage
    merged = xr.combine_by_coords(tiles, combine_attrs='override')

    # Save merged file
    merged.to_netcdf(output_path)
    merged.close()

    # Close individual tiles
    for tile_ds in tiles:
        tile_ds.close()

    logger.info(f"✓ Merged tiles saved: {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")
    return output_path


def create_brazil_tiles(brazil_bbox: tuple, tile_size: float = 10.0) -> List[tuple]:
    """
    Split Brazil bounding box into 10° × 10° tiles for NASA POWER API.

    Args:
        brazil_bbox: Brazil bounding box (west, south, east, north)
        tile_size: Size of each tile in degrees (default: 10°)

    Returns:
        List of tile bounding boxes (west, south, east, north)
    """
    west, south, east, north = brazil_bbox
    tiles = []

    # Create grid of tiles
    current_west = west
    while current_west < east:
        tile_east = min(current_west + tile_size, east)

        current_south = south
        while current_south < north:
            tile_north = min(current_south + tile_size, north)

            tiles.append((current_west, current_south, tile_east, tile_north))

            current_south = tile_north

        current_west = tile_east

    return tiles


@task
def process_nasa_power_to_geotiff(
    netcdf_path: Path,
    bbox: tuple,
    dates_to_process: Optional[List[date]] = None
) -> List[Path]:
    """
    Convert NASA POWER NetCDF to daily GeoTIFFs.
    Only processes dates specified in dates_to_process (if provided).

    Args:
        netcdf_path: Path to NASA POWER NetCDF file
        bbox: Bounding box (west, south, east, north)
        dates_to_process: List of dates to process (if None, process all)

    Returns:
        List of processed GeoTIFF file paths
    """
    logger = get_run_logger()
    settings = get_settings()

    output_dir = Path(settings.DATA_DIR) / "solar_radiation"
    output_dir.mkdir(parents=True, exist_ok=True)

    if dates_to_process:
        logger.info(f"Processing only {len(dates_to_process)} specific dates")

    processed_paths = []

    try:
        # Open NASA POWER NetCDF
        ds = xr.open_dataset(netcdf_path)
        logger.info(f"NetCDF variables: {list(ds.data_vars)}")

        # NASA POWER uses 'ALLSKY_SFC_SW_DWN' as variable name
        if 'ALLSKY_SFC_SW_DWN' not in ds.data_vars:
            raise ValueError(f"ALLSKY_SFC_SW_DWN not found. Available: {list(ds.data_vars)}")

        da = ds['ALLSKY_SFC_SW_DWN']

        # Process each day
        for time_val in da.time.values:
            daily_data = da.sel(time=time_val)

            # Convert time to date
            day_date = pd.Timestamp(time_val).date()

            # Skip if not in dates_to_process (if specified)
            if dates_to_process and day_date not in dates_to_process:
                logger.debug(f"Skipping {day_date} (already exists)")
                continue

            # Rename coordinates to standard names
            if 'lat' in daily_data.dims:
                daily_data = daily_data.rename({'lat': 'latitude', 'lon': 'longitude'})

            # NASA POWER data is already in kWh/m²/day - no conversion needed!
            # Set CRS
            daily_data = daily_data.rio.write_crs("EPSG:4326")

            # Clip to bbox if needed
            west, south, east, north = bbox
            try:
                daily_data = daily_data.rio.clip_box(minx=west, miny=south, maxx=east, maxy=north)
            except Exception as e:
                logger.warning(f"Could not clip to bbox: {e}")

            # Save as Cloud Optimized GeoTIFF (COG)
            date_str = day_date.strftime("%Y%m%d")
            output_path = output_dir / f"solar_radiation_{date_str}.tif"

            daily_data.rio.to_raster(
                output_path,
                driver="COG",
                compress="DEFLATE",
                predictor=2
            )

            processed_paths.append(output_path)
            logger.info(f"✓ Created GeoTIFF: {output_path.name}")

        ds.close()
        logger.info(f"✓ Processed {len(processed_paths)} GeoTIFF files")
        return processed_paths

    except Exception as e:
        logger.error(f"✗ Error processing to GeoTIFF: {e}")
        raise


@task
def append_to_yearly_historical(
    source_netcdf: Path,
    bbox: tuple,
    dates_to_append: Optional[List[date]] = None
) -> List[Path]:
    """
    Append NASA POWER data to yearly historical NetCDF files.

    Args:
        source_netcdf: Path to source NetCDF file
        bbox: Bounding box (west, south, east, north)
        dates_to_append: List of dates to append (if None, append all)

    Returns:
        List of yearly historical files that were created/updated
    """
    logger = get_run_logger()
    settings = get_settings()

    hist_dir = Path(settings.DATA_DIR) / "solar_radiation_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    if dates_to_append:
        logger.info(f"Appending only {len(dates_to_append)} specific dates to historical")

    try:
        # Open source NetCDF
        ds = xr.open_dataset(source_netcdf)

        if 'ALLSKY_SFC_SW_DWN' not in ds.data_vars:
            raise ValueError(f"ALLSKY_SFC_SW_DWN not found in {source_netcdf}")

        da = ds['ALLSKY_SFC_SW_DWN']

        # Standardize coordinates
        if 'lat' in da.dims:
            da = da.rename({'lat': 'latitude', 'lon': 'longitude'})

        # Rename variable to match our schema
        da.name = 'solar_radiation'

        # Filter by dates if specified
        if dates_to_append:
            time_filter = [pd.Timestamp(d) for d in dates_to_append]
            da = da.sel(time=da.time.isin(time_filter))

        # Group by year
        years = pd.to_datetime(da.time.values).year.unique()
        updated_files = []

        for year in years:
            year_file = hist_dir / f"solar_radiation_{year}.nc"
            year_data = da.sel(time=da.time.dt.year == year)

            if year_file.exists():
                # Append to existing file
                logger.info(f"  Appending {len(year_data.time)} days to {year_file.name}")
                existing_ds = xr.open_dataset(year_file)
                combined = xr.concat([existing_ds['solar_radiation'], year_data], dim='time')
                combined = combined.sortby('time').drop_duplicates('time')
                existing_ds.close()

                # Save combined
                combined_ds = combined.to_dataset(name='solar_radiation')
            else:
                # Create new file
                logger.info(f"  Creating new file: {year_file.name} ({len(year_data.time)} days)")
                combined_ds = year_data.to_dataset(name='solar_radiation')

            # Add metadata
            combined_ds['solar_radiation'].attrs = {
                'long_name': 'All Sky Surface Shortwave Downward Irradiance (GHI)',
                'units': 'kWh/m²/day',
                'source': 'NASA POWER',
                'resolution': '0.5 degrees',
            }

            # Save with chunking
            encoding = {
                'solar_radiation': {
                    'dtype': 'float32',
                    'zlib': True,
                    'complevel': 4,
                    'chunksizes': (365, 20, 20)
                }
            }

            combined_ds.to_netcdf(year_file, encoding=encoding, mode='w')
            updated_files.append(year_file)
            logger.info(f"  ✓ Saved {year_file.name}")

        ds.close()
        return updated_files

    except Exception as e:
        logger.error(f"✗ Error appending to historical: {e}")
        raise


@task
def cleanup_raw_files(netcdf_path: Path):
    """Clean up raw downloaded files"""
    logger = get_run_logger()
    try:
        if netcdf_path.exists():
            netcdf_path.unlink()
            logger.info(f"✓ Cleaned up raw file: {netcdf_path.name}")
    except Exception as e:
        logger.warning(f"Could not cleanup {netcdf_path}: {e}")


@flow(name="process-nasa-power-solar")
def nasa_power_solar_flow(
    start_date: date,
    end_date: date,
    batch_days: int = 365
) -> List[Path]:
    """
    Download and process NASA POWER solar radiation data (GHI).

    Args:
        start_date: First date to process
        end_date: Last date to process
        batch_days: Number of days to download per batch (default: 365)

    Returns:
        List of processed GeoTIFF file paths
    """
    logger = get_run_logger()
    settings = get_settings()

    logger.info(f"Processing NASA POWER GHI from {start_date} to {end_date}")

    # Check what's missing
    missing_info = check_missing_dates(start_date, end_date)
    missing_download = missing_info['download']
    missing_geotiff = missing_info['geotiff']
    missing_historical = missing_info['historical']

    if not missing_download:
        logger.info(f"✓ All data already exists for solar radiation")
        return []

    logger.info(f"Need to download {len(missing_download)} dates")

    # Create tiles for Brazil (max 10° × 10° per NASA POWER API limits)
    brazil_tiles = create_brazil_tiles(settings.brazil_bbox_raster, tile_size=10.0)
    logger.info(f"Brazil will be downloaded in {len(brazil_tiles)} tiles (10° × 10° each)")

    # Download in batches
    all_processed = []
    current_start = min(missing_download)

    while current_start <= max(missing_download):
        current_end = min(current_start + timedelta(days=batch_days - 1), max(missing_download))

        # Get dates in this batch that need downloading
        batch_dates = [d for d in missing_download if current_start <= d <= current_end]

        if not batch_dates:
            current_start = current_end + timedelta(days=1)
            continue

        geotiff_dates_in_batch = [d for d in batch_dates if d in missing_geotiff]
        hist_dates_in_batch = [d for d in batch_dates if d in missing_historical]

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing batch: {current_start} to {current_end} ({len(batch_dates)} days)")
            logger.info(f"  Will process {len(geotiff_dates_in_batch)} GeoTIFFs")
            logger.info(f"  Will append {len(hist_dates_in_batch)} to historical")
            logger.info(f"{'='*80}")

            # Download all tiles for this batch
            logger.info(f"Downloading {len(brazil_tiles)} tiles...")
            tile_paths = []
            for i, tile_bbox in enumerate(brazil_tiles):
                tile_path = download_nasa_power_tile(
                    start_date=current_start,
                    end_date=current_end,
                    tile_bbox=tile_bbox,
                    tile_index=i
                )
                tile_paths.append(tile_path)

            # Merge tiles into single NetCDF
            raw_dir = Path(settings.DATA_DIR) / "raw" / "nasa_power"
            start_str = current_start.strftime("%Y%m%d")
            end_str = current_end.strftime("%Y%m%d")
            merged_path = raw_dir / f"ghi_brazil_{start_str}_{end_str}.nc"

            batch_path = merge_tiles(tile_paths, merged_path)

            # Process to GeoTIFFs (only missing dates)
            if geotiff_dates_in_batch:
                processed = process_nasa_power_to_geotiff(
                    netcdf_path=batch_path,
                    bbox=settings.brazil_bbox_raster,
                    dates_to_process=geotiff_dates_in_batch
                )
                all_processed.extend(processed)
            else:
                logger.info("  Skipping GeoTIFF processing (all exist)")

            # Append to yearly historical NetCDF (only missing dates)
            if hist_dates_in_batch:
                yearly_files = append_to_yearly_historical(
                    source_netcdf=batch_path,
                    bbox=settings.brazil_bbox_raster,
                    dates_to_append=hist_dates_in_batch
                )
                logger.info(f"✓ Updated {len(yearly_files)} yearly historical file(s)")
            else:
                logger.info("  Skipping historical append (all exist)")

            # Clean up raw files (tiles and merged file)
            for tile_path in tile_paths:
                cleanup_raw_files(tile_path)
            cleanup_raw_files(batch_path)

            logger.info(f"✓ Completed batch: {current_start} to {current_end}")

        except Exception as e:
            logger.error(f"✗ Failed batch {current_start} to {current_end}: {e}")
            import traceback
            logger.error(traceback.format_exc())

        current_start = current_end + timedelta(days=1)

    if all_processed:
        logger.info(f"\n✓ Successfully processed {len(all_processed)} total files")

    return all_processed
