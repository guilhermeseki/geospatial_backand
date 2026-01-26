#!/usr/bin/env python3
"""
Batch clip all MERGE files to Brazil boundaries using gdalwarp
Creates backups and processes files efficiently
"""
import subprocess
import os
from pathlib import Path
from datetime import datetime
import sys

# Paths
merge_dir = Path("/mnt/workwork/geoserver_data/merge")
backup_dir = Path("/mnt/workwork/geoserver_data/merge_backup_original")
shapefile = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp"
temp_dir = Path("/mnt/workwork/geoserver_data/merge_clipping_temp")

# Create temp directory
temp_dir.mkdir(exist_ok=True)

# Get all MERGE .tif files
merge_files = sorted(list(merge_dir.glob("merge_*.tif")))
total_files = len(merge_files)

print("=" * 80)
print("BATCH CLIPPING ALL MERGE FILES TO BRAZIL")
print("=" * 80)
print(f"Total files to process: {total_files}")
print(f"Source directory: {merge_dir}")
print(f"Backup directory: {backup_dir}")
print(f"Shapefile: {shapefile}")
print(f"Temp directory: {temp_dir}")
print()

# Check disk space
result = subprocess.run(['df', '-h', str(merge_dir)], capture_output=True, text=True)
print("Disk space:")
print(result.stdout)
print()

# Estimate final size (expect ~85% reduction based on test)
original_size_gb = 7.0
estimated_final_gb = original_size_gb * 0.15
estimated_savings_gb = original_size_gb - estimated_final_gb

print(f"Estimated space savings: ~{estimated_savings_gb:.1f} GB")
print(f"Expected final size: ~{estimated_final_gb:.1f} GB")
print()

# Auto-confirm for non-interactive execution
print("⚠️  Proceeding with batch clipping (auto-confirmed)...")

print()
print("=" * 80)
print("STARTING BATCH PROCESSING...")
print("=" * 80)
print()

start_time = datetime.now()
processed = 0
errors = 0
skipped = 0

for i, merge_file in enumerate(merge_files, 1):
    filename = merge_file.name
    backup_file = backup_dir / filename
    temp_file = temp_dir / filename

    # Skip if backup already exists (resume support)
    if backup_file.exists():
        skipped += 1
        if i % 100 == 0:
            print(f"[{i}/{total_files}] ⊙ Skipping {filename} (already processed)")
        continue

    try:
        # Create backup by moving original
        merge_file.rename(backup_file)

        # Clip with gdalwarp
        cmd = [
            "gdalwarp",
            "-q",  # Quiet mode
            "-cutline", shapefile,
            "-crop_to_cutline",
            "-dstnodata", "nan",
            "-co", "COMPRESS=LZW",
            "-co", "TILED=YES",
            "-overwrite",
            str(backup_file),
            str(temp_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            # Restore original on error
            backup_file.rename(merge_file)
            errors += 1
            print(f"[{i}/{total_files}] ❌ Error: {filename}")
            print(f"   {result.stderr[:100]}")
            continue

        # Move clipped file to final location
        temp_file.rename(merge_file)
        processed += 1

        # Progress update every 100 files
        if i % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = (total_files - i) / rate if rate > 0 else 0
            print(f"[{i}/{total_files}] ✓ Processed: {processed} | Errors: {errors} | "
                  f"Rate: {rate:.1f} files/sec | ETA: {remaining/60:.1f} min")

    except subprocess.TimeoutExpired:
        # Restore original on timeout
        if backup_file.exists():
            backup_file.rename(merge_file)
        errors += 1
        print(f"[{i}/{total_files}] ⏱️  Timeout: {filename}")

    except Exception as e:
        # Restore original on any error
        if backup_file.exists():
            backup_file.rename(merge_file)
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

# Check final disk usage
result = subprocess.run(['du', '-sh', str(merge_dir)], capture_output=True, text=True)
final_size = result.stdout.split()[0]
print(f"Final directory size: {final_size}")
print(f"Backup directory: {backup_dir}")
print()

if errors == 0:
    print("✅ All files processed successfully!")
    print()
    print("Next steps:")
    print('1. Clear GeoServer cache: curl -u "admin:todosabordo25!" -X POST "http://127.0.0.1:8080/geoserver/rest/reset"')
    print("2. Test WMS to verify clipped data displays correctly")
else:
    print(f"⚠️  {errors} files had errors. Check logs above.")
    print("   Original files are preserved in backup directory.")

print("=" * 80)
