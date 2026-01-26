#!/usr/bin/env python3
"""
Test clipping MERGE precipitation data with Brazil shapefile
Date: 2024-04-24
"""
import rasterio
from rasterio.mask import mask
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# File paths
merge_file = "/mnt/workwork/geoserver_data/merge/merge_20240424.tif"
shapefile = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp"
output_file = "/tmp/merge_20240424_clipped.tif"

print("=" * 80)
print("MERGE Precipitation Clip Test - Brazil")
print("=" * 80)
print(f"Date: 2024-04-24")
print(f"Merge file: {merge_file}")
print(f"Shapefile: {shapefile}")
print(f"Output: {output_file}")
print()

# Read shapefile
print("📍 Reading shapefile...")
gdf = gpd.read_file(shapefile)
print(f"   CRS: {gdf.crs}")
print(f"   Geometries: {len(gdf)}")
print(f"   Bounds: {gdf.total_bounds}")
print()

# Read raster and clip
print("🗺️  Reading and clipping MERGE raster...")
with rasterio.open(merge_file) as src:
    print(f"   Raster CRS: {src.crs}")
    print(f"   Raster bounds: {src.bounds}")
    print(f"   Raster shape: {src.shape}")
    print(f"   Raster resolution: {src.res}")

    # Reproject shapefile to match raster if needed
    if gdf.crs != src.crs:
        print(f"   Reprojecting shapefile from {gdf.crs} to {src.crs}...")
        gdf = gdf.to_crs(src.crs)

    # Clip
    print("   Clipping...")
    out_image, out_transform = mask(src, gdf.geometry, crop=True, nodata=np.nan)
    out_meta = src.meta.copy()

    # Update metadata
    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform,
        "nodata": np.nan
    })

    # Write clipped raster
    print(f"   Writing clipped raster to {output_file}...")
    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(out_image)

print("✅ Clipping complete!")
print()

# Statistics
print("📊 Statistics:")
data = out_image[0]
valid_data = data[~np.isnan(data)]
if len(valid_data) > 0:
    print(f"   Valid pixels: {len(valid_data):,}")
    print(f"   Min precipitation: {valid_data.min():.2f} mm")
    print(f"   Max precipitation: {valid_data.max():.2f} mm")
    print(f"   Mean precipitation: {valid_data.mean():.2f} mm")
    print(f"   Median precipitation: {np.median(valid_data):.2f} mm")
    print(f"   Total area rainfall: {valid_data.sum():.2f} mm")
else:
    print("   No valid data found!")
print()

# Create visualization
print("📈 Creating visualization...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Plot 1: Clipped precipitation
im1 = ax1.imshow(data, cmap='Blues', vmin=0, vmax=50)
ax1.set_title('MERGE Precipitation - Brazil Clip\n2024-04-24', fontsize=14, fontweight='bold')
ax1.set_xlabel('Longitude')
ax1.set_ylabel('Latitude')
plt.colorbar(im1, ax=ax1, label='Precipitation (mm)')

# Plot 2: Histogram
ax2.hist(valid_data, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
ax2.set_title('Precipitation Distribution', fontsize=14, fontweight='bold')
ax2.set_xlabel('Precipitation (mm)')
ax2.set_ylabel('Frequency')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
output_plot = "/tmp/merge_20240424_clip_test.png"
plt.savefig(output_plot, dpi=150, bbox_inches='tight')
print(f"✅ Visualization saved to {output_plot}")
print()

print("=" * 80)
print("Test complete!")
print("=" * 80)
