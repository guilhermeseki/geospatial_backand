"""
Test downloading and processing a SINGLE MODIS image with the fix
Using June 2025 where we know data exists
"""
from datetime import date
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, '/opt/geospatial_backend')

from app.workflows.data_processing.ndvi_flow import ndvi_data_flow

print("=" * 80)
print("TESTING SINGLE MODIS DOWNLOAD WITH FIX")
print("=" * 80)

# Use June 10, 2025 - we saw this date exists from earlier
# Delete any existing file first to force re-download
modis_dir = Path('/mnt/workwork/geoserver_data/ndvi_modis')
test_file = modis_dir / 'ndvi_modis_20250610.tif'
if test_file.exists():
    print(f"\n🗑️  Deleting existing file to test fresh download: {test_file.name}")
    test_file.unlink()

start_date = date(2025, 6, 8)
end_date = date(2025, 6, 12)

print(f"\n📅 Test period: {start_date} to {end_date}")
print(f"   (Should capture the June 10 MODIS composite)")
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

        # Sample of values
        sample_values = np.unique(valid_data)
        if len(sample_values) > 0:
            print(f"\n  Sample values (first 30):")
            print(f"     {sample_values[:30]}")

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
        zero_count = np.sum(np.abs(data - 0.0) < 0.00001)

        print(f"\n  🔍 CRITICAL CHECKS:")
        print(f"     Count of -0.3 values (the bug): {neg_03_count}")
        print(f"     Count of 0.0 values: {zero_count}")

        if neg_03_count > 0:
            print(f"     ❌ FAIL: Still has -0.3 values (unmasked nodata)!")
        else:
            print(f"     ✅ PASS: No -0.3 values found!")

        if len(np.unique(valid_data)) > 100:
            print(f"     ✅ PASS: Good variety of values ({len(np.unique(valid_data))})")
        elif len(np.unique(valid_data)) == 2:
            print(f"     ❌ FAIL: Only 2 unique values (the original bug!)")
        else:
            print(f"     ⚠️  WARNING: Only {len(np.unique(valid_data))} unique values")

else:
    print("\n❌ NO FILES PROCESSED!")

print("\n" + "=" * 80)
