"""
Test the MODIS NDVI fix - verify that nodata values are properly masked
"""
import numpy as np
import pystac_client
import planetary_computer
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.crs import CRS

print("=" * 80)
print("TESTING MODIS NDVI FIX")
print("=" * 80)

# Search for a recent MODIS item
catalog = pystac_client.Client.open(
    'https://planetarycomputer.microsoft.com/api/stac/v1',
    modifier=planetary_computer.sign_inplace
)

bbox = [-94, -53, -34, 25]  # LATAM
search = catalog.search(
    collections=['modis-13Q1-061'],
    bbox=bbox,
    limit=50
)

items = list(search.items())
print(f"\n✓ Found {len(items)} MODIS items")

# Find an item with good coverage
item = None
for test_item in items:
    ndvi_href_test = planetary_computer.sign(test_item.assets['250m_16_days_NDVI'].href)
    with rasterio.open(ndvi_href_test) as src:
        # Check if this tile has valid data (not all -3000)
        sample = src.read(1, window=((1000, 1200), (1000, 1200)))
        if np.sum(sample != -3000) > 100:  # Has at least some valid pixels
            item = test_item
            print(f"✓ Selected item with good data: {item.id}")
            break

if item is None:
    raise ValueError("No items with valid data found")

# Get the NDVI asset
ndvi_href = planetary_computer.sign(item.assets['250m_16_days_NDVI'].href)

# Use the center of the tile as test area
with rasterio.open(ndvi_href) as src:
    bounds = src.bounds
    # Use middle 25% of the tile
    margin_x = (bounds.right - bounds.left) * 0.375
    margin_y = (bounds.top - bounds.bottom) * 0.375
    west = bounds.left + margin_x
    east = bounds.right - margin_x
    south = bounds.bottom + margin_y
    north = bounds.top - margin_y

print(f"Test area bounds: W={west:.0f}, S={south:.0f}, E={east:.0f}, N={north:.0f}")
resolution = 0.0023  # ~250m
n_lat = int((north - south) / resolution)
n_lon = int((east - west) / resolution)

print(f"\nTest grid: {n_lat} x {n_lon} pixels")
common_transform = transform_from_bounds(west, south, east, north, n_lon, n_lat)

with rasterio.open(ndvi_href) as src:
    print(f"\nRasterio metadata:")
    print(f"  NoData: {src.nodata}")
    print(f"  Data type: {src.dtypes[0]}")

    # Read entire tile
    ndvi_src = src.read(1).astype(np.float32)
    src_transform = src.transform
    src_crs = src.crs
    nodata_value = src.nodata

    print(f"\n📊 RAW DATA (before masking):")
    print(f"  Shape: {ndvi_src.shape}")
    print(f"  Min: {np.nanmin(ndvi_src)}, Max: {np.nanmax(ndvi_src)}")
    print(f"  Unique values count: {len(np.unique(ndvi_src))}")
    print(f"  First 10 unique: {np.unique(ndvi_src)[:10]}")
    print(f"  Count of -3000 values: {np.sum(ndvi_src == -3000)}")

    # Apply the fix: Mask nodata BEFORE scaling
    if nodata_value is not None:
        print(f"\n🔧 APPLYING FIX: Masking nodata value {nodata_value}")
        ndvi_src_masked = np.where(ndvi_src == nodata_value, np.nan, ndvi_src)
    else:
        ndvi_src_masked = ndvi_src

    print(f"\n📊 AFTER MASKING (before reprojection):")
    print(f"  Min: {np.nanmin(ndvi_src_masked)}, Max: {np.nanmax(ndvi_src_masked)}")
    print(f"  NaN count: {np.isnan(ndvi_src_masked).sum()}/{ndvi_src_masked.size}")
    print(f"  Unique values count: {len(np.unique(ndvi_src_masked[~np.isnan(ndvi_src_masked)]))}")

    # Reproject to test area
    ndvi_raw = np.empty((n_lat, n_lon), dtype=np.float32)
    ndvi_raw[:] = np.nan

    reproject(
        source=ndvi_src_masked,
        destination=ndvi_raw,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=common_transform,
        dst_crs=CRS.from_epsg(4326),
        resampling=Resampling.bilinear,
        src_nodata=np.nan,
        dst_nodata=np.nan
    )

    # Scale
    ndvi = ndvi_raw * 0.0001
    ndvi = np.where((ndvi < -0.2) | (ndvi > 1.0), np.nan, ndvi)

    print(f"\n📊 FINAL RESULT (after reprojection & scaling):")
    print(f"  Shape: {ndvi.shape}")
    print(f"  Min: {np.nanmin(ndvi):.4f}, Max: {np.nanmax(ndvi):.4f}")
    print(f"  Mean: {np.nanmean(ndvi):.4f}")
    print(f"  Valid pixels: {np.sum(~np.isnan(ndvi))}/{ndvi.size}")
    print(f"  Valid %: {100 * np.sum(~np.isnan(ndvi)) / ndvi.size:.1f}%")

    # Check distribution
    valid_data = ndvi[~np.isnan(ndvi)]
    if len(valid_data) > 0:
        print(f"\n📈 VALUE DISTRIBUTION:")
        bins = [(-0.2, 0), (0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        for low, high in bins:
            count = ((valid_data >= low) & (valid_data < high)).sum()
            pct = 100 * count / len(valid_data)
            print(f"  [{low:4.1f}, {high:4.1f}): {pct:5.1f}%")

        print(f"\n  Unique values in sample: {len(np.unique(valid_data))}")
        print(f"  Sample values: {np.unique(valid_data)[:20]}")

print("\n" + "=" * 80)
print("✓ TEST COMPLETE")
print("=" * 80)
print("\n🎯 Expected results:")
print("  - Should have MANY unique values (not just 2)")
print("  - Min should be > -0.2, Max should be < 1.0")
print("  - Should have a reasonable distribution across NDVI range")
print("  - No -0.3 values (which would indicate unmasked nodata)")
print("=" * 80)
