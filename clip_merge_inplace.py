#!/usr/bin/env python3
"""
Clip MERGE file with Brazil shapefile and replace original
"""
import rasterio
from rasterio.mask import mask
import geopandas as gpd
import numpy as np
import os

# File paths
merge_file = "/mnt/workwork/geoserver_data/merge/merge_20240424.tif"
shapefile = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp"
temp_file = "/tmp/merge_20240424_clipped_temp.tif"

print("=" * 80)
print("Clipping MERGE file to Brazil boundaries")
print("=" * 80)
print(f"Input: {merge_file}")
print(f"Shapefile: {shapefile}")
print()

# Read shapefile
print("📍 Reading shapefile...")
gdf = gpd.read_file(shapefile)

# Read raster and clip
print("🗺️  Clipping raster...")
with rasterio.open(merge_file) as src:
    # Reproject shapefile to match raster if needed
    if gdf.crs != src.crs:
        gdf = gdf.to_crs(src.crs)

    # Clip
    out_image, out_transform = mask(src, gdf.geometry, crop=True, nodata=np.nan)
    out_meta = src.meta.copy()

    # Update metadata
    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform,
        "nodata": np.nan,
        "compress": "lzw"  # Compress to save space
    })

    # Write to temporary file
    print(f"   Writing to temporary file...")
    with rasterio.open(temp_file, "w", **out_meta) as dest:
        dest.write(out_image)

print("✅ Clipping complete!")

# Replace original file
print(f"🔄 Replacing original file...")
os.replace(temp_file, merge_file)
print("✅ Original file replaced!")

# Statistics
data = out_image[0]
valid_data = data[~np.isnan(data)]
print()
print("📊 New file statistics:")
print(f"   Shape: {out_image.shape[1]} x {out_image.shape[2]}")
print(f"   Valid pixels: {len(valid_data):,}")
print(f"   File: {merge_file}")
print()
print("=" * 80)
