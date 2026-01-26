#!/usr/bin/env python3
"""
Clip CHIRPS file with Brazil shapefile
Date: 2024-04-24
"""
import rasterio
from rasterio.mask import mask
import geopandas as gpd
import numpy as np
import shutil

# File paths
chirps_file = "/mnt/workwork/geoserver_data/chirps/chirps_20240424.tif"
shapefile = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp"
backup_file = "/tmp/chirps_20240424_original_backup.tif"
temp_file = "/mnt/workwork/geoserver_data/chirps/chirps_20240424_temp.tif"

print("=" * 80)
print("Clipping CHIRPS file to Brazil boundaries")
print("=" * 80)
print(f"Input: {chirps_file}")
print(f"Shapefile: {shapefile}")
print()

# Backup original
print("💾 Creating backup...")
shutil.copy2(chirps_file, backup_file)
print(f"   Backup: {backup_file}")
print()

# Read shapefile
print("📍 Reading shapefile...")
gdf = gpd.read_file(shapefile)

# Read raster and clip
print("🗺️  Clipping raster...")
with rasterio.open(chirps_file) as src:
    print(f"   Original size: {src.shape}")
    print(f"   Original bounds: {src.bounds}")

    # Reproject shapefile to match raster if needed
    if gdf.crs != src.crs:
        print(f"   Reprojecting shapefile...")
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
        "compress": "lzw"
    })

    # Write to temp file
    with rasterio.open(temp_file, "w", **out_meta) as dest:
        dest.write(out_image)

print("✅ Clipping complete!")

# Replace original
print("🔄 Replacing original file...")
shutil.move(temp_file, chirps_file)
print("✅ Original file replaced!")

# Get file sizes
import os
original_size = os.path.getsize(backup_file) / (1024 * 1024)
clipped_size = os.path.getsize(chirps_file) / (1024 * 1024)
reduction = ((original_size - clipped_size) / original_size) * 100

# Statistics
data = out_image[0]
valid_data = data[~np.isnan(data)]
print()
print("📊 Results:")
print(f"   New shape: {out_image.shape[1]} x {out_image.shape[2]}")
print(f"   Valid pixels: {len(valid_data):,}")
print(f"   Original size: {original_size:.2f} MB")
print(f"   Clipped size: {clipped_size:.2f} MB")
print(f"   Reduction: {reduction:.1f}%")
if len(valid_data) > 0:
    print(f"   Min precip: {valid_data.min():.2f} mm")
    print(f"   Max precip: {valid_data.max():.2f} mm")
    print(f"   Mean precip: {valid_data.mean():.2f} mm")
print()
print("=" * 80)
