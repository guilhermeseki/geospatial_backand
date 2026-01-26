"""
Test CHIRPS polygon clipping with a single date
"""
from datetime import date
from app.workflows.data_processing.precipitation_flow import chirps_daily_flow
from app.workflows.data_processing.schemas import DataSource
import rioxarray
import numpy as np

# Pick a recent date to test
test_date = date(2024, 12, 15)

print(f"Testing CHIRPS polygon clipping for {test_date}")
print("=" * 80)

# Delete existing file to force re-download and processing
import shutil
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()
test_file = Path(settings.DATA_DIR) / "chirps" / f"chirps_{test_date.strftime('%Y%m%d')}.tif"

if test_file.exists():
    print(f"Deleting existing file: {test_file}")
    test_file.unlink()

# Process the date
print(f"\nRunning chirps_daily_flow for {test_date}...")
result = chirps_daily_flow(
    source=DataSource.CHIRPS,
    start_date=test_date,
    end_date=test_date
)

print(f"\nResult: {result}")

# Verify the output
if test_file.exists():
    print(f"\n✓ File created: {test_file}")

    # Load and check
    ds = rioxarray.open_rasterio(test_file, masked=True).squeeze()
    print(f"  Shape: {ds.shape}")
    print(f"  Bounds: {ds.rio.bounds()}")

    total_pixels = ds.size
    valid_pixels = np.count_nonzero(~np.isnan(ds.values))
    nan_pixels = total_pixels - valid_pixels
    nan_percentage = (nan_pixels / total_pixels) * 100

    print(f"  Total pixels: {total_pixels}")
    print(f"  Valid pixels: {valid_pixels} ({valid_pixels/total_pixels*100:.1f}%)")
    print(f"  NaN pixels: {nan_pixels} ({nan_percentage:.1f}%)")

    if nan_percentage > 40:
        print("\n✅ SUCCESS! File is polygon-clipped (>40% NaN = ocean/outside Brazil)")
    else:
        print("\n❌ FAILED! File is NOT polygon-clipped (too few NaN pixels)")
else:
    print(f"\n❌ File NOT created: {test_file}")
