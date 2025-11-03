#!/usr/bin/env python3
"""
Quick test of MODIS fix - downloads just 1 day to verify time coord is written correctly
"""
from app.workflows.data_processing.ndvi_flow import download_modis_batch, process_ndvi_to_geotiff
from app.config.settings import settings
from datetime import date
import xarray as xr
from pathlib import Path

print("="*80)
print("TESTING MODIS FIX - 1 DAY DOWNLOAD")
print("="*80)

try:
    # Download just one day
    # area needs to be [W, S, E, N]
    area = list(settings.latam_bbox_raster)  # Already (W, S, E, N)
    print(f"Using area: {area}")

    raw_path = download_modis_batch(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        area=area
    )

    print(f"\n✓ Download completed: {raw_path}")
    print(f"  File size: {raw_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Inspect the file
    print(f"\nInspecting NetCDF file...")
    ds = xr.open_dataset(raw_path)

    print(f"  Variables: {list(ds.variables)}")
    print(f"  Dimensions: {dict(ds.dims)}")
    print(f"  Time values: {ds.time.values[:5]}")
    print()

    # Check for NaT
    import pandas as pd
    import numpy as np
    nat_count = sum(1 for t in ds.time.values if pd.isna(t))
    print(f"  NaT values: {nat_count} / {len(ds.time.values)}")

    if nat_count > 0:
        print("\n✗ FAILED: Still has NaT values!")
        ds.close()
        exit(1)

    print(f"\n✓ SUCCESS: All time values are valid!")
    print(f"  First time: {ds.time.values[0]}")
    print(f"  Last time: {ds.time.values[-1]}")

    # Now test GeoTIFF creation
    print(f"\nTesting GeoTIFF creation...")
    geotiffs = process_ndvi_to_geotiff(
        netcdf_path=raw_path,
        source='modis',
        bbox=settings.latam_bbox_raster,
        dates_to_process=None
    )

    print(f"  Created {len(geotiffs)} GeoTIFF files")

    if len(geotiffs) > 0:
        print(f"\n✓ COMPLETE SUCCESS!")
        print(f"  GeoTIFFs created: {len(geotiffs)}")
        print(f"  Example: {geotiffs[0].name}")
    else:
        print(f"\n✗ No GeoTIFFs created!")
        exit(1)

    ds.close()

except Exception as e:
    print(f"\n✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
