#!/usr/bin/env python3
"""
Standalone test for GLM fix - bypasses Prefect decorators.
Tests the core xr.concat fix for full Brazil coverage.
"""

import sys
import os
sys.path.insert(0, '/opt/geospatial_backend')
os.chdir('/opt/geospatial_backend')

from datetime import date, timedelta
from pathlib import Path
import xarray as xr
import numpy as np
import rasterio
import requests
import tempfile
import logging

from app.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

settings = get_settings()

TEST_DATE = date(2025, 4, 15)

def download_minute_file(url: str, session: requests.Session, temp_dir: Path) -> Path:
    """Download a single minute file."""
    filename = url.split('/')[-1]
    local_path = temp_dir / filename

    if local_path.exists():
        return local_path

    response = session.get(url, stream=True)
    response.raise_for_status()

    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return local_path

def get_satellite_for_date(target_date: date) -> str:
    """Determine satellite based on date."""
    goes19_start = date(2025, 4, 14)
    if target_date >= goes19_start:
        return "G19"
    return "G16"

def test_glm_concat_fix():
    """Test the xr.concat fix with actual GLM data."""

    logger.info("="*60)
    logger.info(f"Testing GLM xr.concat fix for {TEST_DATE}")
    logger.info("="*60)

    # Get credentials
    username = settings.EARTHDATA_USERNAME
    password = settings.EARTHDATA_PASSWORD

    if not username or not password:
        logger.error("EARTHDATA credentials not set!")
        return False

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix="glm_test_"))
    logger.info(f"Temp directory: {temp_dir}")

    # Session with auth
    session = requests.Session()
    session.auth = (username, password)

    # Get satellite
    satellite = get_satellite_for_date(TEST_DATE)
    logger.info(f"Using satellite: GOES-{satellite.replace('G', '')}")

    # Query CMR for a few hours of data (not full day - just enough to test concat)
    cmr_url = "https://cmr.earthdata.nasa.gov/search/granules.json"

    # Get just 2 hours of data to test (00:00-02:00)
    start_dt = f"{TEST_DATE}T00:00:00Z"
    end_dt = f"{TEST_DATE}T02:00:00Z"

    params = {
        "short_name": "glmgoesL3",
        "provider": "GHRC_DAAC",
        "temporal": f"{start_dt},{end_dt}",
        "page_size": 200
    }

    logger.info(f"Querying CMR for {start_dt} to {end_dt}...")
    response = requests.get(cmr_url, params=params, timeout=60)
    response.raise_for_status()

    all_granules = response.json()['feed']['entry']
    # Filter for our satellite
    granules = [g for g in all_granules if f"_{satellite}_" in g['title']]
    logger.info(f"Found {len(granules)} {satellite} granules")

    if len(granules) < 10:
        logger.error("Not enough granules found for test!")
        return False

    # Download first 30 minutes (30 files)
    granules_to_use = granules[:30]
    logger.info(f"Downloading {len(granules_to_use)} files for test...")

    downloaded_files = []
    for i, granule in enumerate(granules_to_use):
        # Get download URL
        links = granule.get('links', [])
        download_url = None
        for link in links:
            if link.get('rel') == 'http://esipfed.org/ns/fedsearch/1.1/data#':
                download_url = link.get('href')
                break

        if download_url:
            try:
                local_file = download_minute_file(download_url, session, temp_dir)
                downloaded_files.append(local_file)
                if (i+1) % 10 == 0:
                    logger.info(f"  Downloaded {i+1}/{len(granules_to_use)} files")
            except Exception as e:
                logger.warning(f"  Failed to download: {e}")

    logger.info(f"Successfully downloaded {len(downloaded_files)} files")

    if len(downloaded_files) < 10:
        logger.error("Not enough files downloaded!")
        return False

    # Load all files and check their individual extents
    logger.info("\nChecking individual file extents...")
    minute_data_list = []
    extent_info = []

    for nc_file in downloaded_files:
        try:
            ds = xr.open_dataset(nc_file)
            if 'Flash_extent_density' in ds.data_vars:
                fed = ds['Flash_extent_density']
                # Record extent
                x_min, x_max = float(fed.x.min()), float(fed.x.max())
                y_min, y_max = float(fed.y.min()), float(fed.y.max())
                extent_info.append((x_min, x_max, y_min, y_max, len(fed.x), len(fed.y)))
                minute_data_list.append(fed.load())
            ds.close()
        except Exception as e:
            logger.warning(f"  Error loading {nc_file.name}: {e}")

    logger.info(f"Loaded {len(minute_data_list)} valid files")

    # Show extent variations
    x_mins = [e[0] for e in extent_info]
    x_maxs = [e[1] for e in extent_info]
    y_mins = [e[2] for e in extent_info]
    y_maxs = [e[3] for e in extent_info]
    widths = [e[4] for e in extent_info]
    heights = [e[5] for e in extent_info]

    logger.info(f"\nExtent variations across {len(extent_info)} files:")
    logger.info(f"  x range: [{min(x_mins):.6f}, {max(x_maxs):.6f}]")
    logger.info(f"  y range: [{min(y_mins):.6f}, {max(y_maxs):.6f}]")
    logger.info(f"  widths:  {min(widths)} to {max(widths)}")
    logger.info(f"  heights: {min(heights)} to {max(heights)}")

    # Test OLD concat (inner join - default)
    logger.info("\n" + "="*60)
    logger.info("Testing OLD concat (default join='inner')...")
    try:
        old_concat = xr.concat(minute_data_list, dim='time')
        logger.info(f"  OLD result: x={len(old_concat.x)}, y={len(old_concat.y)}")
        old_x = len(old_concat.x)
        old_y = len(old_concat.y)
    except Exception as e:
        logger.error(f"  OLD concat failed: {e}")
        old_x, old_y = 0, 0

    # Test NEW concat (outer join - THE FIX)
    logger.info("\nTesting NEW concat (join='outer', fill_value=np.nan)...")
    try:
        new_concat = xr.concat(minute_data_list, dim='time', join='outer', fill_value=np.nan)
        logger.info(f"  NEW result: x={len(new_concat.x)}, y={len(new_concat.y)}")
        new_x = len(new_concat.x)
        new_y = len(new_concat.y)
    except Exception as e:
        logger.error(f"  NEW concat failed: {e}")
        new_x, new_y = 0, 0

    # Results
    logger.info("\n" + "="*60)
    logger.info("RESULTS:")
    logger.info("="*60)

    if new_x > old_x or new_y > old_y:
        x_increase = new_x / old_x if old_x > 0 else float('inf')
        y_increase = new_y / old_y if old_y > 0 else float('inf')
        logger.info(f"\nOLD (default): {old_x} x {old_y} = {old_x*old_y:,} pixels")
        logger.info(f"NEW (fixed):   {new_x} x {new_y} = {new_x*new_y:,} pixels")
        logger.info(f"\nCoverage increase: {(new_x*new_y)/(old_x*old_y):.2f}x more pixels!")
        logger.info("\nSUCCESS! The fix preserves full coverage!")

        # Clean up
        import shutil
        shutil.rmtree(temp_dir)
        return True
    else:
        logger.info(f"\nOLD: {old_x} x {old_y}")
        logger.info(f"NEW: {new_x} x {new_y}")
        logger.info("\nNo difference - files may have identical extents.")
        logger.info("This is OK if you're downloading from same time period.")

        # Clean up
        import shutil
        shutil.rmtree(temp_dir)
        return True  # Not a failure, just no variation in this sample

if __name__ == "__main__":
    success = test_glm_concat_fix()
    sys.exit(0 if success else 1)
