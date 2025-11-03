#!/usr/bin/env python3
"""
STREAMING MODIS NDVI Downloader (Microsoft Planetary Computer)
Processes ONE composite at a time - no memory issues, no expired URLs!
100% FREE - No registration needed!
"""
import pystac_client
import planetary_computer
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.crs import CRS
import numpy as np
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple
import dateutil.parser
from prefect import task, flow, get_run_logger
from app.config.settings import get_settings


@task(retries=3, retry_delay_seconds=10)
def download_and_process_single_modis_composite(
    item,
    output_dir: Path,
    bbox: Tuple[float, float, float, float],  # (W, S, E, N)
    target_resolution: float = 0.0023  # ~250m
) -> List[Path]:
    """
    Download and process a SINGLE MODIS composite to GeoTIFF.
    Memory efficient - processes one tile at a time!

    Returns:
        List of GeoTIFF paths created (may be empty if all data invalid)
    """
    logger = get_run_logger()

    west, south, east, north = bbox

    # Get composite date
    if item.datetime:
        composite_date = item.datetime
    elif 'start_datetime' in item.properties:
        composite_date = dateutil.parser.isoparse(item.properties['start_datetime'])
        if composite_date.tzinfo:
            composite_date = composite_date.replace(tzinfo=None)
    else:
        logger.warning(f"No datetime for item {item.id}, skipping")
        return []

    composite_date = composite_date.date()

    # Check if GeoTIFF already exists
    output_path = output_dir / f"ndvi_modis_{composite_date.strftime('%Y%m%d')}.tif"
    if output_path.exists():
        logger.info(f"Already exists: {composite_date}, skipping")
        return [output_path]

    logger.info(f"Processing: {item.id} (date: {composite_date})")

    try:
        # Sign the URL (fresh signature for each download)
        ndvi_href = planetary_computer.sign(item.assets["250m_16_days_NDVI"].href)

        with rasterio.open(ndvi_href) as src:
            # Calculate transform for target resolution
            dst_crs = CRS.from_epsg(4326)

            # Reproject bounds to source CRS to get correct window
            src_bounds = rasterio.warp.transform_bounds(dst_crs, src.crs, west, south, east, north)

            # Read the window
            window = rasterio.windows.from_bounds(*src_bounds, src.transform)

            # Ensure window is valid
            window = window.intersection(rasterio.windows.Window(0, 0, src.width, src.height))

            if window.width <= 0 or window.height <= 0:
                logger.info(f"  No intersection with target area, skipping")
                return []

            # Read data
            ndvi_raw = src.read(1, window=window)
            src_transform = src.window_transform(window)
            src_crs = src.crs

            logger.info(f"  Read: {ndvi_raw.shape}")

            # Calculate output dimensions at target resolution (TRUE 250m - no limits!)
            width = int((east - west) / target_resolution)
            height = int((north - south) / target_resolution)

            logger.info(f"  Target grid: {width}x{height} pixels at 250m resolution")

            # Calculate destination transform
            dst_transform = rasterio.transform.from_bounds(west, south, east, north, width, height)

            # Reproject to WGS84
            ndvi_reprojected = np.empty((height, width), dtype=np.float32)

            reproject(
                source=ndvi_raw,
                destination=ndvi_reprojected,
                src_transform=src_transform,
                src_crs=src_crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear
            )

            # Scale MODIS NDVI: values are * 10000
            ndvi = ndvi_reprojected.astype(np.float32) / 10000.0

            # Apply valid range [-1, 1]
            ndvi = np.where((ndvi < -1) | (ndvi > 1), np.nan, ndvi)

            # Check for valid data
            valid_pct = 100 * np.sum(~np.isnan(ndvi)) / ndvi.size

            if valid_pct < 1:
                logger.warning(f"  < 1% valid data, skipping")
                return []

            logger.info(f"  Valid data: {valid_pct:.1f}%")

            # Write GeoTIFF
            output_dir.mkdir(parents=True, exist_ok=True)

            with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=1,
                dtype=ndvi.dtype,
                crs=dst_crs,
                transform=dst_transform,
                compress='lzw',
                tiled=True,
                blockxsize=256,
                blockysize=256
            ) as dst:
                dst.write(ndvi, 1)

            logger.info(f"  ✓ Saved: {output_path.name}")
            return [output_path]

    except Exception as e:
        logger.error(f"  Failed: {e}")
        return []


@flow(name="process-modis-streaming")
def modis_streaming_flow(
    start_date: date,
    end_date: date,
    batch_days: int = 16  # MODIS composites are 16-day periods
) -> List[Path]:
    """
    Download MODIS NDVI using streaming approach.
    Processes one composite at a time - no memory issues!

    Args:
        start_date: Start date
        end_date: End date
        batch_days: Days per search window (16 = typical composite period)

    Returns:
        List of GeoTIFF paths created
    """
    logger = get_run_logger()
    settings = get_settings()

    bbox = list(settings.latam_bbox_raster)  # [W, S, E, N]
    output_dir = Path(settings.DATA_DIR) / "ndvi_modis"

    logger.info("=" * 80)
    logger.info("MODIS NDVI STREAMING DOWNLOAD")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Source: Microsoft Planetary Computer (100% FREE!)")
    logger.info(f"Strategy: Process ONE composite at a time (memory efficient)")
    logger.info("=" * 80)

    all_results = []

    # Split into smaller search windows
    current = start_date
    while current <= end_date:
        batch_end = min(current + timedelta(days=batch_days - 1), end_date)

        logger.info(f"\nSearching: {current} to {batch_end}")

        try:
            # Search for MODIS composites
            catalog = pystac_client.Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1",
                modifier=planetary_computer.sign_inplace
            )

            search = catalog.search(
                collections=["modis-13Q1-061"],
                bbox=bbox,
                datetime=f"{current.isoformat()}/{batch_end.isoformat()}"
            )

            items = list(search.items())
            logger.info(f"Found {len(items)} MODIS composites")

            if len(items) == 0:
                logger.warning("No composites found in this window")
                current = batch_end + timedelta(days=1)
                continue

            # Limit to most recent 5 composites per window to avoid too many tiles
            if len(items) > 5:
                logger.info(f"Limiting to 5 most recent composites (out of {len(items)})")

                def get_item_time(item):
                    if item.datetime:
                        return item.datetime
                    elif 'start_datetime' in item.properties:
                        return dateutil.parser.isoparse(item.properties['start_datetime'])
                    return None

                items = sorted(items, key=get_item_time, reverse=True)[:5]

            # Process each composite individually
            for i, item in enumerate(items):
                logger.info(f"\nComposite {i+1}/{len(items)}: {item.id}")

                results = download_and_process_single_modis_composite(
                    item=item,
                    output_dir=output_dir,
                    bbox=tuple(bbox)
                )

                all_results.extend(results)

        except Exception as e:
            logger.error(f"Window failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

        current = batch_end + timedelta(days=1)

    logger.info(f"\n{'='*80}")
    logger.info(f"COMPLETED: Created {len(all_results)} GeoTIFF files")
    logger.info(f"{'='*80}")

    return all_results


if __name__ == "__main__":
    # Test with a small window
    test_results = modis_streaming_flow(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31)
    )
    print(f"\n✓ Created {len(test_results)} files")
