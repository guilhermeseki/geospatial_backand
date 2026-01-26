#!/usr/bin/env python3
"""Test GLM fix by processing a single day and checking coverage."""

import sys
import os
sys.path.insert(0, '/opt/geospatial_backend')

from datetime import date
from pathlib import Path
import xarray as xr
import numpy as np
import rasterio

from app.config.settings import get_settings

settings = get_settings()

# We need to remove the existing daily aggregate to force regeneration with the fix
TEST_DATE = date(2025, 4, 15)

def test_glm_single_day():
    """Process one day and verify full coverage."""

    print(f"\n{'='*60}")
    print(f"Testing GLM fix for {TEST_DATE}")
    print(f"{'='*60}\n")

    # Check for existing daily aggregate
    raw_dir = Path(settings.DATA_DIR) / "raw" / "glm_fed"
    daily_nc = raw_dir / f"glm_fed_daily_{TEST_DATE.strftime('%Y%m%d')}.nc"

    # Delete existing daily aggregate to force reprocessing with fix
    if daily_nc.exists():
        print(f"Removing existing daily aggregate to test fix...")
        daily_nc.unlink()
        print(f"  Deleted: {daily_nc}")

    # Delete existing GeoTIFF to force reprocessing
    output_dir = Path(settings.DATA_DIR) / "glm_fed"
    existing_tif = output_dir / f"glm_fed_{TEST_DATE.strftime('%Y%m%d')}.tif"

    # Backup old file for comparison
    old_bounds = None
    old_width = None
    old_height = None
    if existing_tif.exists():
        with rasterio.open(existing_tif) as old_src:
            old_width = old_src.width
            old_height = old_src.height
            old_bounds = old_src.bounds
        print(f"\nOLD (cropped) file: {old_width} x {old_height} pixels")
        print(f"  Bounds: W={old_bounds.left:.2f}, S={old_bounds.bottom:.2f}, E={old_bounds.right:.2f}, N={old_bounds.top:.2f}")

        # Move to backup
        backup_path = existing_tif.with_suffix('.tif.backup')
        existing_tif.rename(backup_path)
        print(f"  Backed up to: {backup_path}")

    # Now run the flow for this single day using Prefect
    print(f"\n{'='*60}")
    print("Running GLM flow with the fix...")
    print(f"{'='*60}\n")

    # Import and run the flow directly
    from app.workflows.data_processing.glm_fed_flow import (
        download_glm_fed_daily,
        process_glm_fed_to_geotiff
    )

    # Get credentials
    username, password = settings.EARTHDATA_USERNAME, settings.EARTHDATA_PASSWORD

    if not username or not password:
        print("ERROR: EARTHDATA_USERNAME and EARTHDATA_PASSWORD must be set!")
        return False

    # Run download (this uses the fixed xr.concat)
    print("Step 1: Download and aggregate GLM data...")
    daily_nc_result = download_glm_fed_daily.fn(TEST_DATE, username, password)

    if not daily_nc_result:
        print("ERROR: Download failed!")
        return False

    print(f"  Created: {daily_nc_result}")

    # Check the NetCDF coverage
    ds = xr.open_dataset(daily_nc_result)
    print(f"\n  NetCDF dimensions:")
    if 'x' in ds.dims:
        print(f"    x: {len(ds.x)} points")
        print(f"    y: {len(ds.y)} points")
    else:
        print(f"    lat: {len(ds.lat)} points")
        print(f"    lon: {len(ds.lon)} points")
    ds.close()

    # Run GeoTIFF conversion
    print("\nStep 2: Convert to GeoTIFF...")
    geotiff_result = process_glm_fed_to_geotiff.fn(daily_nc_result, TEST_DATE)

    if not geotiff_result:
        print("ERROR: GeoTIFF conversion failed!")
        return False

    print(f"  Created: {geotiff_result}")

    # Verify GeoTIFF coverage
    print(f"\n{'='*60}")
    print("RESULTS:")
    print(f"{'='*60}")

    with rasterio.open(geotiff_result) as src:
        width = src.width
        height = src.height
        bounds = src.bounds

    print(f"\nNEW file: {width} x {height} pixels")
    print(f"  Bounds: W={bounds.left:.2f}, S={bounds.bottom:.2f}, E={bounds.right:.2f}, N={bounds.top:.2f}")

    if old_width:
        coverage_increase = (width * height) / (old_width * old_height)
        print(f"\n  Coverage change: {coverage_increase:.2f}x ({'+' if coverage_increase > 1 else ''}{(coverage_increase-1)*100:.0f}%)")

    # Success criteria
    expected_min_width = 2000  # Should be much larger than 1233
    if width > expected_min_width and height > expected_min_width:
        print(f"\n{'='*60}")
        print("SUCCESS! The fix works - full coverage restored!")
        print(f"{'='*60}")
        return True
    else:
        print(f"\n{'='*60}")
        print(f"ISSUE - Coverage may still be limited (got {width}x{height})")
        print(f"{'='*60}")
        return False

if __name__ == "__main__":
    success = test_glm_single_day()
    sys.exit(0 if success else 1)
