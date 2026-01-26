"""
ERA5 Daily Wind Gust Flow
Downloads daily maximum wind gust from ERA5 daily statistics dataset.
Dataset: sis-agrometeorological-indicators (ERA5 post-processed daily statistics)
"""
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional
import cdsapi
import xarray as xr
import numpy as np
import pandas as pd
from prefect import flow, task, get_run_logger
from app.config.settings import get_settings


@task(retries=2, retry_delay_seconds=600, timeout_seconds=14400)
def download_daily_wind_gust_era5(
    start_date: date,
    end_date: date,
    area: List[float]  # [N, W, S, E]
) -> Path:
    """
    Download daily maximum wind gust from ERA5 daily statistics.

    Dataset: sis-agrometeorological-indicators
    This has pre-computed daily statistics including max wind gust.

    Args:
        start_date: Start date
        end_date: End date
        area: Bounding box [N, W, S, E]

    Returns:
        Path to downloaded NetCDF file
    """
    logger = get_run_logger()
    settings = get_settings()

    # Generate date list
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)

    # Extract components for CDS API
    years = sorted(list(set([d.strftime("%Y") for d in dates])))
    months = sorted(list(set([d.strftime("%m") for d in dates])))
    days = sorted(list(set([d.strftime("%d") for d in dates])))

    # Prepare output path
    raw_dir = Path(settings.DATA_DIR) / "raw" / "wind_gust_daily"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    output_path = raw_dir / f"wind_gust_daily_{start_str}_{end_str}.nc"

    if output_path.exists():
        logger.info(f"Daily wind gust already downloaded: {output_path}")
        return output_path

    request = {
        "variable": "10m_wind_gust",
        "statistic": "maximum",
        "year": years,
        "month": months,
        "day": days,
        "area": area,  # [N, W, S, E]
        "format": "netcdf"
    }

    logger.info(f"Downloading daily max wind gust: {start_date} to {end_date}")
    logger.info(f"Dataset: sis-agrometeorological-indicators")
    logger.info(f"Variable: 10m_wind_gust")
    logger.info(f"Statistic: maximum (daily)")
    logger.info(f"Area [N,W,S,E]: {area}")
    logger.info("="*80)

    try:
        client = cdsapi.Client()
        logger.info("Submitting request to CDS...")
        result = client.retrieve("sis-agrometeorological-indicators", request)
        result.download(str(output_path))
        logger.info(f"✓ Downloaded: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"✗ Download failed: {e}")
        if output_path.exists():
            output_path.unlink()
        raise


@task
def process_wind_gust_to_geotiff(
    netcdf_path: Path,
    dates_to_process: Optional[List[date]] = None
) -> List[Path]:
    """
    Process daily wind gust NetCDF to GeoTIFFs.

    Args:
        netcdf_path: Path to daily wind gust NetCDF
        dates_to_process: Optional list of specific dates to process

    Returns:
        List of created GeoTIFF paths
    """
    logger = get_run_logger()
    settings = get_settings()

    output_dir = Path(settings.DATA_DIR) / "wind_speed"
    output_dir.mkdir(parents=True, exist_ok=True)

    processed_paths = []

    try:
        # Open daily data
        ds = xr.open_dataset(netcdf_path)
        logger.info(f"NetCDF variables: {list(ds.data_vars)}")

        # Find the wind gust variable
        var_name = None
        for possible_name in ['10m_wind_gust', 'fg10', 'wind_gust', 'max_10m_wind_gust']:
            if possible_name in ds.data_vars:
                var_name = possible_name
                break

        if not var_name:
            raise ValueError(f"Wind gust variable not found. Available: {list(ds.data_vars)}")

        logger.info(f"Using variable: {var_name}")

        # Get the data
        gust_data = ds[var_name]

        logger.info(f"Processing {len(gust_data.time)} days")

        # Process each day
        for time_val in gust_data.time.values:
            day_date = pd.Timestamp(time_val).date()

            # Skip if not in dates_to_process
            if dates_to_process and day_date not in dates_to_process:
                logger.debug(f"Skipping {day_date} (not in requested dates)")
                continue

            # Get daily gust for this date
            daily_gust = gust_data.sel(time=time_val)

            # Convert from m/s to km/h
            daily_gust = daily_gust * 3.6

            # Set CRS
            daily_gust = daily_gust.rio.write_crs("EPSG:4326")

            # Clip to Brazil bbox
            bbox = settings.latam_bbox_raster  # (W, S, E, N)
            try:
                daily_gust = daily_gust.rio.clip_box(*bbox)
            except Exception as e:
                logger.warning(f"Could not clip to bbox: {e}")

            # Reproject to consistent grid (416x416, 0.1° resolution)
            target_shape = (416, 416)
            target_bounds = (-75.05, -35.05, -33.45, 6.55)  # (minx, miny, maxx, maxy)

            if daily_gust.shape != target_shape:
                from rasterio.transform import from_bounds
                target_transform = from_bounds(*target_bounds, target_shape[1], target_shape[0])

                logger.info(f"  Reprojecting from {daily_gust.shape} to {target_shape}")

                daily_gust = daily_gust.rio.reproject(
                    "EPSG:4326",
                    shape=target_shape,
                    transform=target_transform,
                    resampling=5  # bilinear
                )

            # Output path
            output_path = output_dir / f"wind_speed_{day_date.strftime('%Y%m%d')}.tif"

            # Write to temporary file first
            temp_output = output_path.parent / f"{output_path.stem}_temp.tif"
            daily_gust.rio.to_raster(temp_output, driver="COG", compress="LZW")

            # Clip with Brazil shapefile if exists
            shapefile = Path("/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp")
            if shapefile.exists():
                import subprocess
                clip_output = output_path.parent / f"{output_path.stem}_clipped.tif"

                result = subprocess.run([
                    "gdalwarp",
                    "-cutline", str(shapefile),
                    "-crop_to_cutline",
                    "-dstnodata", "-9999",
                    "-co", "COMPRESS=LZW",
                    "-co", "TILED=YES",
                    "-overwrite",
                    str(temp_output),
                    str(clip_output)
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    clip_output.rename(output_path)
                    temp_output.unlink(missing_ok=True)
                else:
                    logger.warning(f"Shapefile clip failed, using unclipped: {result.stderr}")
                    temp_output.rename(output_path)
            else:
                temp_output.rename(output_path)

            logger.info(f"✓ Created: {output_path.name}")
            processed_paths.append(output_path)

        ds.close()

        return processed_paths

    except Exception as e:
        logger.error(f"Failed to process wind gust data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@flow(name="process-wind-gust-daily-era5")
def wind_gust_daily_era5_flow(
    start_date: date,
    end_date: date,
    skip_existing: bool = True
) -> List[Path]:
    """
    Download daily maximum wind gust from ERA5 and create GeoTIFFs.

    Args:
        start_date: Start date
        end_date: End date
        skip_existing: Skip dates that already have GeoTIFFs

    Returns:
        List of created GeoTIFF paths
    """
    logger = get_run_logger()
    settings = get_settings()

    logger.info("="*80)
    logger.info("WIND GUST DAILY PROCESSING (ERA5)")
    logger.info("="*80)
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Source: ERA5 daily statistics (sis-agrometeorological-indicators)")
    logger.info(f"Variable: 10m_wind_gust")
    logger.info(f"Statistic: Daily maximum")
    logger.info("="*80)

    # Check which dates are missing
    output_dir = Path(settings.DATA_DIR) / "wind_speed"
    existing_dates = set()

    if skip_existing and output_dir.exists():
        for tif_file in output_dir.glob("wind_speed_*.tif"):
            try:
                date_str = tif_file.stem.split('_')[-1]
                file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
                existing_dates.add(file_date)
            except:
                pass

    # Generate requested dates
    requested_dates = []
    current = start_date
    while current <= end_date:
        if not skip_existing or current not in existing_dates:
            requested_dates.append(current)
        current += timedelta(days=1)

    if not requested_dates:
        logger.info("No missing dates to process")
        return []

    logger.info(f"Processing {len(requested_dates)} dates (skipping {len(existing_dates)} existing)")

    # Download daily wind gust data (Brazil bbox)
    brazil_bbox = [6.55, -75.05, -35.05, -33.45]  # [N, W, S, E]
    netcdf_path = download_daily_wind_gust_era5(
        start_date=min(requested_dates),
        end_date=max(requested_dates),
        area=brazil_bbox
    )

    # Process to GeoTIFFs
    processed = process_wind_gust_to_geotiff(
        netcdf_path=netcdf_path,
        dates_to_process=requested_dates
    )

    logger.info(f"\n✓ Successfully processed {len(processed)} files")

    # Cleanup raw file
    try:
        netcdf_path.unlink()
        logger.info(f"Cleaned up: {netcdf_path.name}")
    except:
        pass

    return processed
