#!/usr/bin/env python3
"""
Test clipping a single CHIRPS file with Brazil shapefile using gdalwarp
Date: 2024-04-24
"""
import subprocess
import os
import shutil

# File paths
test_date = "20240424"
chirps_file = f"/mnt/workwork/geoserver_data/chirps/chirps_{test_date}.tif"
shapefile = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp"
backup_file = f"/tmp/chirps_{test_date}_test_backup.tif"
temp_file = f"/mnt/workwork/geoserver_data/chirps/chirps_{test_date}_temp.tif"

print("=" * 80)
print(f"TEST: Clipping CHIRPS {test_date} with gdalwarp")
print("=" * 80)
print(f"Input: {chirps_file}")
print(f"Shapefile: {shapefile}")
print()

# Backup original
print("💾 Creating backup...")
shutil.copy2(chirps_file, backup_file)
print(f"   Backup: {backup_file}")
print()

# Get original info
print("📊 Original file:")
info_cmd = ["gdalinfo", chirps_file]
info_result = subprocess.run(info_cmd, capture_output=True, text=True)
for line in info_result.stdout.split('\n')[:35]:
    if any(x in line for x in ['Size', 'Origin', 'Pixel Size', 'Upper Left', 'Lower Right']):
        print(f"   {line}")
print()

# Use gdalwarp to clip
print("🗺️  Clipping with gdalwarp...")

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

    if result.stderr:
        print(f"   Warnings: {result.stderr[:200]}")

except subprocess.CalledProcessError as e:
    print(f"❌ Error: {e}")
    print(f"   stderr: {e.stderr}")
    exit(1)

# Get file sizes
original_size = os.path.getsize(chirps_file) / (1024 * 1024)
clipped_size = os.path.getsize(temp_file) / (1024 * 1024)
reduction = ((original_size - clipped_size) / original_size) * 100

print()
print("📊 Results:")
print(f"   Original size: {original_size:.2f} MB")
print(f"   Clipped size: {clipped_size:.2f} MB")
print(f"   Reduction: {reduction:.1f}%")
print()

# Check clipped file
print("🔍 Clipped file info:")
info_cmd = ["gdalinfo", temp_file]
info_result = subprocess.run(info_cmd, capture_output=True, text=True)
for line in info_result.stdout.split('\n')[:35]:
    if any(x in line for x in ['Size', 'Origin', 'Pixel Size', 'Upper Left', 'Lower Right']):
        print(f"   {line}")
print()

# Replace original
print("🔄 Replacing original file...")
shutil.move(temp_file, chirps_file)
print("✅ Original file replaced!")
print()

print("=" * 80)
print("Next: Clear GeoServer cache and test WMS")
print('curl -u "admin:todosabordo25!" -X POST "http://127.0.0.1:8080/geoserver/rest/reset"')
print("=" * 80)
