#!/usr/bin/env python3
"""
Batch clip all temp_max files to Brazil boundaries using gdalwarp
AUTO-CONFIRMED VERSION - No user prompt
"""
import subprocess
from pathlib import Path
from datetime import datetime

# Paths
temp_dir = Path("/mnt/workwork/geoserver_data/temp_max")
backup_dir = Path("/mnt/workwork/geoserver_data/temp_max_backup_original")
shapefile = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp"
temp_working_dir = Path("/mnt/workwork/geoserver_data/temp_max_clipping_temp")

# Create directories
backup_dir.mkdir(exist_ok=True)
temp_working_dir.mkdir(exist_ok=True)

# Get all temp_max .tif files
temp_files = sorted(list(temp_dir.glob("temp_max_*.tif")))
total_files = len(temp_files)

print("=" * 80)
print("BATCH CLIPPING ALL TEMP_MAX FILES TO BRAZIL")
print("=" * 80)
print(f"Total files to process: {total_files}")
print(f"Source directory: {temp_dir}")
print(f"Backup directory: {backup_dir}")
print(f"Shapefile: {shapefile}")
print()

start_time = datetime.now()
processed = 0
errors = 0
skipped = 0

for i, temp_file in enumerate(temp_files, 1):
    filename = temp_file.name
    backup_file = backup_dir / filename
    temp_output = temp_working_dir / filename

    # Skip if backup already exists
    if backup_file.exists():
        skipped += 1
        if i % 100 == 0:
            print(f"[{i}/{total_files}] ⊙ Skipping {filename} (already processed)")
        continue

    try:
        # Create backup by moving original
        temp_file.rename(backup_file)

        # Clip with gdalwarp (WITHOUT crop_to_cutline to preserve grid)
        cmd = [
            "gdalwarp",
            "-q",
            "-cutline", shapefile,
            "-dstnodata", "nan",
            "-overwrite",
            str(backup_file),
            str(temp_output)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            backup_file.rename(temp_file)
            errors += 1
            print(f"[{i}/{total_files}] ❌ Error: {filename}")
            print(f"   {result.stderr[:100]}")
            continue

        # Move clipped file to final location
        temp_output.rename(temp_file)
        processed += 1

        # Progress update every 100 files
        if i % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = (total_files - i) / rate if rate > 0 else 0
            print(f"[{i}/{total_files}] ✓ Processed: {processed} | Errors: {errors} | "
                  f"Rate: {rate:.1f} files/sec | ETA: {remaining/60:.1f} min")

    except subprocess.TimeoutExpired:
        if backup_file.exists():
            backup_file.rename(temp_file)
        errors += 1
        print(f"[{i}/{total_files}] ⏱️  Timeout: {filename}")

    except Exception as e:
        if backup_file.exists():
            backup_file.rename(temp_file)
        errors += 1
        print(f"[{i}/{total_files}] ❌ Exception: {filename} - {str(e)[:50]}")

# Final summary
end_time = datetime.now()
duration = (end_time - start_time).total_seconds()

print()
print("=" * 80)
print("BATCH PROCESSING COMPLETE")
print("=" * 80)
print(f"Total files: {total_files}")
print(f"Processed: {processed}")
print(f"Skipped (already done): {skipped}")
print(f"Errors: {errors}")
print(f"Duration: {duration/60:.1f} minutes")
print(f"Average rate: {processed/duration:.2f} files/sec" if duration > 0 else "N/A")
print()

if errors == 0:
    print("✅ All files processed successfully!")
else:
    print(f"⚠️  {errors} files had errors.")

print("=" * 80)
