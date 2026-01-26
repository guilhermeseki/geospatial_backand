#!/usr/bin/env python3
"""
Clip CHIRPS file using gdalwarp (more reliable than rasterio mask)
Date: 2024-04-24
"""
import subprocess
import os
import shutil

# File paths
chirps_file = "/mnt/workwork/geoserver_data/chirps/chirps_20240424.tif"
shapefile = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp"
backup_file = "/tmp/chirps_20240424_gdalwarp_backup.tif"
temp_file = "/tmp/chirps_20240424_clipped_gdalwarp.tif"

print("=" * 80)
print("Clipping CHIRPS with gdalwarp - 2024-04-24")
print("=" * 80)
print(f"Input: {chirps_file}")
print(f"Shapefile: {shapefile}")
print()

# Backup original
print("💾 Creating backup...")
shutil.copy2(chirps_file, backup_file)
print(f"   Backup: {backup_file}")
print()

# Use gdalwarp to clip
print("🗺️  Clipping with gdalwarp...")
print("   This preserves CRS and transform correctly...")

cmd = [
    "gdalwarp",
    "-cutline", shapefile,
    "-crop_to_cutline",
    "-dstnodata", "nan",
    "-co", "COMPRESS=LZW",
    "-co", "TILED=YES",
    "-overwrite",
    chirps_file,
    temp_file
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("✅ Clipping complete!")

    # Show any warnings
    if result.stderr:
        print("   Warnings:", result.stderr[:200])

except subprocess.CalledProcessError as e:
    print(f"❌ Error: {e}")
    print(f"   stderr: {e.stderr}")
    exit(1)

# Get file sizes
original_size = os.path.getsize(backup_file) / (1024 * 1024)
clipped_size = os.path.getsize(temp_file) / (1024 * 1024)
reduction = ((original_size - clipped_size) / original_size) * 100

print()
print("📊 Results:")
print(f"   Original size: {original_size:.2f} MB")
print(f"   Clipped size: {clipped_size:.2f} MB")
print(f"   Reduction: {reduction:.1f}%")
print()

# Check with gdalinfo
print("🔍 Verifying clipped file...")
info_cmd = ["gdalinfo", temp_file]
info_result = subprocess.run(info_cmd, capture_output=True, text=True)
for line in info_result.stdout.split('\n')[:30]:
    if any(x in line for x in ['Size', 'Origin', 'Pixel Size', 'Upper Left', 'Lower Right']):
        print(f"   {line}")

print()
input("⚠️  Press ENTER to replace original file, or Ctrl+C to cancel...")

# Replace original
print("🔄 Replacing original file...")
shutil.move(temp_file, chirps_file)
print("✅ Original file replaced!")
print()
print("=" * 80)
print("Done! Test in GeoServer and clear cache if needed:")
print('curl -u "admin:todosabordo25!" -X POST "http://127.0.0.1:8080/geoserver/rest/reset"')
print("=" * 80)
