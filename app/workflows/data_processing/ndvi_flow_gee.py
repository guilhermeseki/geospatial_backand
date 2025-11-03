#!/usr/bin/env python3
"""
NDVI MODIS Data Download using Google Earth Engine
Uses pre-mosaicked global MODIS MOD13Q1 data - MUCH faster and more reliable!
"""
import ee
import numpy as np
import xarray as xr
from datetime import date, timedelta
from pathlib import Path
from typing import List
import logging
from prefect import task, flow, get_run_logger
from app.config.settings import get_settings
import pandas as pd

# Initialize Earth Engine
try:
    ee.Initialize(project='535508181914')
    logger = logging.getLogger(__name__)
    logger.info("✓ Earth Engine initialized successfully")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize Earth Engine: {e}")
    logger.error("Run: earthengine authenticate")
    raise


@task(retries=2, retry_delay_seconds=60)
def download_modis_gee_batch(
    start_date: date,
    end_date: date,
    bbox: List[float]  # [west, south, east, north]
) -> Path:
    """
    Download MODIS NDVI using Google Earth Engine's pre-mosaicked data.
    Much faster and more reliable than tile-by-tile approach!

    Args:
        start_date: Start date
        end_date: End date
        bbox: [west, south, east, north] in WGS84

    Returns:
        Path to NetCDF file with NDVI data
    """
    logger = get_run_logger()
    settings = get_settings()

    # Prepare output
    raw_dir = Path(settings.DATA_DIR) / "raw" / "modis_gee"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    output_path = raw_dir / f"modis_ndvi_{start_str}_{end_str}.nc"

    if output_path.exists():
        logger.info(f"Batch already downloaded: {output_path}")
        return output_path

    logger.info("=" * 80)
    logger.info("MODIS NDVI DOWNLOAD (Google Earth Engine - Pre-mosaicked!)")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Region: {bbox}")

    # Define region of interest
    west, south, east, north = bbox
    roi = ee.Geometry.Rectangle([west, south, east, north])

    # Load MODIS NDVI ImageCollection
    # MOD13Q1: 16-day composites, 250m resolution
    modis = ee.ImageCollection("MODIS/061/MOD13Q1") \
        .filterBounds(roi) \
        .filterDate(start_date.isoformat(), (end_date + timedelta(days=1)).isoformat()) \
        .select(['NDVI'])

    # Get list of images
    image_list = modis.toList(modis.size())
    count = image_list.size().getInfo()

    logger.info(f"Found {count} MODIS composites (pre-mosaicked!)")

    if count == 0:
        raise ValueError("No MODIS data found for date range")

    # Process each image
    ndvi_data_list = []
    time_list = []

    # Define target grid (250m resolution)
    lat_range = north - south
    lon_range = east - west
    resolution_deg = 0.0023  # ~250m at equator

    n_lat = int(lat_range / resolution_deg)
    n_lon = int(lon_range / resolution_deg)

    # Limit grid size
    max_pixels = 10000
    if n_lat > max_pixels:
        n_lat = max_pixels
    if n_lon > max_pixels:
        n_lon = max_pixels

    logger.info(f"Target grid: {n_lat} x {n_lon} pixels")

    # Create coordinate arrays
    lats = np.linspace(north, south, n_lat)
    lons = np.linspace(west, east, n_lon)

    # Process each composite
    for i in range(count):
        try:
            image = ee.Image(image_list.get(i))

            # Get image date
            timestamp_ms = image.get('system:time_start').getInfo()
            img_date = pd.to_datetime(timestamp_ms, unit='ms')

            logger.info(f"Processing composite {i+1}/{count}: {img_date.date()}")

            # Get NDVI band and clip to ROI
            ndvi_img = image.select('NDVI').clip(roi)

            # Export to numpy array
            # Scale: MODIS NDVI is scaled by 10000
            # We'll download at target resolution
            ndvi_array = ndvi_img.sampleRectangle(
                region=roi,
                defaultValue=-3000  # MODIS fill value
            ).get('NDVI').getInfo()

            # Convert to numpy array
            ndvi_raw = np.array(ndvi_array)

            logger.info(f"  Downloaded: {ndvi_raw.shape}")

            # Resample to target grid if needed
            if ndvi_raw.shape != (n_lat, n_lon):
                from scipy.ndimage import zoom
                zoom_factors = (n_lat / ndvi_raw.shape[0], n_lon / ndvi_raw.shape[1])
                ndvi_raw = zoom(ndvi_raw, zoom_factors, order=1)
                logger.info(f"  Resampled to: {ndvi_raw.shape}")

            # Scale MODIS NDVI: divide by 10000
            ndvi = ndvi_raw.astype(np.float32) / 10000.0

            # Apply valid range: NDVI should be -1 to 1
            ndvi = np.where((ndvi < -1) | (ndvi > 1), np.nan, ndvi)

            # Check for valid data
            valid_pct = 100 * np.sum(~np.isnan(ndvi)) / ndvi.size

            if valid_pct < 1:
                logger.warning(f"  < 1% valid data, skipping")
                continue

            logger.info(f"  ✓ Valid data: {valid_pct:.1f}%")

            ndvi_data_list.append(ndvi)
            time_list.append(img_date.to_pydatetime().replace(tzinfo=None))

        except Exception as e:
            logger.error(f"  Failed to process composite {i+1}: {e}")
            continue

    if len(ndvi_data_list) == 0:
        raise ValueError("No valid MODIS data processed")

    logger.info(f"\nSuccessfully processed {len(ndvi_data_list)} composites")

    # Create xarray Dataset
    ndvi_stack = np.stack(ndvi_data_list, axis=0)

    ds = xr.Dataset(
        {'ndvi': (['time', 'lat', 'lon'], ndvi_stack)},
        coords={
            'time': pd.to_datetime(time_list),
            'lat': lats,
            'lon': lons,
        },
        attrs={
            'source': 'MODIS/061/MOD13Q1',
            'provider': 'Google Earth Engine',
            'resolution': '250m',
            'description': 'MODIS NDVI 16-day composites'
        }
    )

    # Write to NetCDF with compression
    logger.info(f"\nWriting to: {output_path}")
    encoding = {
        'ndvi': {'zlib': True, 'complevel': 4, 'dtype': 'float32'},
        'time': {'dtype': 'float64'},
    }
    ds.to_netcdf(output_path, encoding=encoding)

    file_size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info(f"✓ Saved: {file_size_mb:.1f} MB")

    ds.close()
    return output_path


@flow(name="process-modis-gee")
def modis_gee_flow(
    start_date: date,
    end_date: date,
    batch_days: int = 32  # Process ~2 composites per batch (16-day composites)
) -> List[Path]:
    """
    Download MODIS NDVI using Google Earth Engine.

    Args:
        start_date: Start date
        end_date: End date
        batch_days: Days per batch (default 32 = ~2 composites)

    Returns:
        List of NetCDF file paths
    """
    logger = get_run_logger()
    settings = get_settings()

    bbox = list(settings.latam_bbox_raster)  # [W, S, E, N]

    logger.info(f"Processing MODIS NDVI: {start_date} to {end_date}")
    logger.info(f"Using Google Earth Engine (pre-mosaicked data)")

    # Split into batches
    batches = []
    current = start_date

    while current <= end_date:
        batch_end = min(current + timedelta(days=batch_days - 1), end_date)
        batches.append((current, batch_end))
        current = batch_end + timedelta(days=1)

    logger.info(f"Processing {len(batches)} batch(es)")

    results = []
    for batch_start, batch_end in batches:
        logger.info(f"\nBatch: {batch_start} to {batch_end}")

        try:
            nc_path = download_modis_gee_batch(batch_start, batch_end, bbox)
            results.append(nc_path)
        except Exception as e:
            logger.error(f"Batch failed: {e}")
            continue

    logger.info(f"\n✓ Completed {len(results)}/{len(batches)} batches")
    return results


if __name__ == "__main__":
    # Test with a small date range
    test_start = date(2024, 1, 1)
    test_end = date(2024, 1, 31)

    print("Testing MODIS download via Google Earth Engine...")
    results = modis_gee_flow(test_start, test_end)
    print(f"\n✓ Success! Downloaded {len(results)} file(s)")
