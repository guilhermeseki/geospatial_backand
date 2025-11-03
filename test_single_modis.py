"""
Test downloading and processing a SINGLE MODIS image with the fix
"""
from datetime import date, timedelta
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, '/opt/geospatial_backend')

from app.workflows.data_processing.ndvi_flow import ndvi_data_flow

print("=" * 80)
print("TESTING SINGLE MODIS DOWNLOAD WITH FIX")
print("=" * 80)

# Download just the most recent available MODIS composite
# MODIS has 16-day composites, so go back ~20 days to ensure data is available
test_date = date.today() - timedelta(days=20)
start_date = test_date - timedelta(days=3)  # Small window
end_date = test_date + timedelta(days=3)

print(f"\n📅 Test period: {start_date} to {end_date}")
print(f"   (Will process any MODIS 16-day composites in this range)")
print("\n" + "=" * 80)

# Run the flow for MODIS only
result = ndvi_data_flow(
    batch_days=16,
    sources=['modis'],  # ONLY MODIS
    start_date=start_date,
    end_date=end_date
)

print("\n" + "=" * 80)
print(f"✓ FLOW COMPLETE - Processed {len(result)} files")
print("=" * 80)

# Now verify the data quality
if result:
    print("\n📊 VERIFYING DATA QUALITY:")
    import rasterio
    import numpy as np

    latest_file = sorted(result)[-1]
    print(f"\nChecking: {latest_file.name}")

    with rasterio.open(latest_file) as src:
        data = src.read(1)

        # Statistics
        valid_data = data[~np.isnan(data)]

        print(f"\n  Shape: {data.shape}")
        print(f"  Min: {np.nanmin(data):.4f}, Max: {np.nanmax(data):.4f}")
        print(f"  Mean: {np.nanmean(data):.4f}")
        print(f"  Valid pixels: {len(valid_data):,}/{data.size:,} ({100*len(valid_data)/data.size:.1f}%)")
        print(f"  Unique values: {len(np.unique(valid_data))}")

        # Distribution
        if len(valid_data) > 0:
            print(f"\n  📈 VALUE DISTRIBUTION:")
            bins = [(-0.2, 0), (0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
            for low, high in bins:
                count = ((valid_data >= low) & (valid_data < high)).sum()
                pct = 100 * count / len(valid_data)
                print(f"     [{low:4.1f}, {high:4.1f}): {pct:5.1f}%")

        # Check for the -0.3 problem
        neg_03_count = np.sum(np.abs(data + 0.3) < 0.001)
        print(f"\n  🔍 CHECK: Count of -0.3 values (the bug): {neg_03_count}")

        if neg_03_count > 0:
            print(f"     ❌ FAIL: Still has -0.3 values (unmasked nodata)!")
        else:
            print(f"     ✅ PASS: No -0.3 values found!")

        if len(np.unique(valid_data)) > 100:
            print(f"     ✅ PASS: Good variety of values ({len(np.unique(valid_data))})")
        else:
            print(f"     ⚠️  WARNING: Only {len(np.unique(valid_data))} unique values")

print("\n" + "=" * 80)
