#!/usr/bin/env python3
"""
Test MODIS with a single composite - minimal test
"""
import pystac_client
import planetary_computer
import rasterio
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.crs import CRS
import numpy as np
import xarray as xr
import pandas as pd
from pathlib import Path
from app.config.settings import settings
import dateutil.parser

print("="*80)
print("MINIMAL MODIS TEST - SINGLE COMPOSITE")
print("="*80)

try:
    # 1. Search for MODIS composites
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace
    )

    bbox = list(settings.latam_bbox_raster)  # (W, S, E, N)
    print(f"Searching MODIS for bbox: {bbox}")

    search = catalog.search(
        collections=["modis-13Q1-061"],
        bbox=bbox,
        datetime="2024-01-01/2024-01-16"
    )

    items = list(search.items())
    print(f"Found {len(items)} MODIS items")

    if not items:
        print("No items found!")
        exit(1)

    # 2. Take just the FIRST item
    item = items[0]
    print(f"\nProcessing item: {item.id}")
    print(f"  item.datetime: {item.datetime}")
    print(f"  start_datetime: {item.properties.get('start_datetime')}")
    print(f"  end_datetime: {item.properties.get('end_datetime')}")

    # 3. Extract datetime using our fix
    if item.datetime:
        composite_time = item.datetime
    elif 'start_datetime' in item.properties:
        composite_time = dateutil.parser.isoparse(item.properties['start_datetime'])
        # Remove timezone for NetCDF compatibility
        if composite_time.tzinfo:
            composite_time = composite_time.replace(tzinfo=None)
    else:
        print("ERROR: No datetime found!")
        exit(1)

    print(f"  Using datetime: {composite_time}")

    # 4. Download and process the NDVI data
    ndvi_href = planetary_computer.sign(item.assets["250m_16_days_NDVI"].href)
    print(f"\nDownloading from: {ndvi_href[:80]}...")

    # Simple processing - just grab a small window
    with rasterio.open(ndvi_href) as src:
        print(f"  Image size: {src.width}x{src.height}")
        print(f"  CRS: {src.crs}")

        # Read a small 100x100 window
        ndvi_data = src.read(1, window=((0, 100), (0, 100)))
        print(f"  Read window: {ndvi_data.shape}")

        # Scale MODIS NDVI (values are * 10000)
        ndvi_scaled = ndvi_data.astype(np.float32) * 0.0001
        ndvi_scaled = np.where((ndvi_scaled < -1) | (ndvi_scaled > 1), np.nan, ndvi_scaled)

        valid_pct = 100 * np.sum(~np.isnan(ndvi_scaled)) / ndvi_scaled.size
        print(f"  Valid pixels: {valid_pct:.1f}%")

    # 5. Create a minimal xarray Dataset
    print(f"\nCreating xarray Dataset...")

    ds = xr.Dataset(
        {'ndvi': (['time', 'y', 'x'], ndvi_scaled[np.newaxis, :, :])},
        coords={
            'time': pd.to_datetime([composite_time]),
            'y': np.arange(100),
            'x': np.arange(100),
        }
    )

    print(f"  Dataset created")
    print(f"  Time coord: {ds.time.values}")
    print(f"  Time dtype: {ds.time.dtype}")

    # 6. Check for NaT
    if pd.isna(ds.time.values[0]):
        print(f"\n✗ FAILED: Time is NaT!")
        exit(1)

    print(f"\n✓ SUCCESS: Time coordinate is valid!")
    print(f"  Time value: {ds.time.values[0]}")

    # 7. Write to NetCDF
    output_path = Path(settings.DATA_DIR) / "raw" / "modis" / "test_single.nc"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nWriting to: {output_path}")
    ds.to_netcdf(output_path)

    # 8. Re-read and verify
    print(f"Reading back to verify...")
    ds_verify = xr.open_dataset(output_path)
    print(f"  Time values: {ds_verify.time.values}")

    if pd.isna(ds_verify.time.values[0]):
        print(f"\n✗ FAILED: Time became NaT after write!")
        exit(1)

    print(f"\n✓✓ COMPLETE SUCCESS!")
    print(f"  NetCDF file created with valid time coordinate")
    print(f"  File: {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")

    ds.close()
    ds_verify.close()

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
