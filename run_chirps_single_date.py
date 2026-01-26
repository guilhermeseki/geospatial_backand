"""
Regenerate single CHIRPS file for 2025-04-24
Uses the Prefect tasks directly
"""
from datetime import date
from pathlib import Path
from app.workflows.data_processing.schemas import DataSource
from app.workflows.data_processing.tasks import (
    check_data_availability,
    download_data,
    process_data,
    validate_output,
    refresh_mosaic_shapefile
)
from app.config.settings import get_settings

# Configuration
target_date = date(2025, 4, 24)
source = DataSource.CHIRPS
settings = get_settings()

print(f"Regenerating CHIRPS for {target_date}")
print("="*60)

# Step 1: Check if data is available
print(f"Step 1: Checking data availability for {target_date}...")
is_available = check_data_availability(target_date, source)
if not is_available:
    print(f"❌ Data not available for {target_date}")
    exit(1)
print("✓ Data is available")

# Step 2: Download
print(f"Step 2: Downloading data for {target_date}...")
raw_path = download_data(target_date, source)
print(f"✓ Downloaded to: {raw_path}")

# Step 3: Process to GeoTIFF
print(f"Step 3: Processing to GeoTIFF...")
processed_path = process_data(
    raw_path,
    target_date,
    source,
    bbox=settings.latam_bbox_raster
)
print(f"✓ Processed to: {processed_path}")

# Step 4: Validate
print(f"Step 4: Validating output...")
is_valid = validate_output(processed_path)
if not is_valid:
    print(f"❌ Validation failed")
    exit(1)
print("✓ Validation passed")

# Step 5: Refresh mosaic
print(f"Step 5: Refreshing mosaic shapefile...")
refresh_mosaic_shapefile(source)
print("✓ Mosaic refreshed")

print("="*60)
print(f"✓ Successfully regenerated chirps_20250424.tif")
