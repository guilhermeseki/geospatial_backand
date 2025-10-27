#!/usr/bin/env python3
"""
Test MODIS NDVI flow with a small date range
"""
from app.workflows.data_processing.ndvi_flow import ndvi_data_flow
from datetime import date
import xarray as xr
from pathlib import Path
from app.config.settings import get_settings

print("="*80)
print("MODIS NDVI FLOW TEST")
print("="*80)

# Test with just September 2024 (should have ~2 MODIS composites)
start_date = date(2024, 9, 1)
end_date = date(2024, 9, 30)

print(f"\nTest date range: {start_date} to {end_date}")
print("Expected: ~2 MODIS composites (16-day interval)")
print("\nStarting MODIS flow...")
print("="*80)
print()

try:
    result = ndvi_data_flow(
        start_date=start_date,
        end_date=end_date,
        sources=['modis'],
        batch_days=32
    )

    print("\n" + "="*80)
    print("✓ TEST PASSED!")
    print("="*80)
    print(f"Processed {len(result)} GeoTIFF files")

    # Check yearly historical files
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)
    hist_dir = data_dir / "ndvi_modis_hist"

    if hist_dir.exists():
        yearly_files = list(hist_dir.glob("ndvi_modis_*.nc"))
        print(f"\nYearly historical files created: {len(yearly_files)}")

        for yf in yearly_files:
            try:
                ds = xr.open_dataset(yf)
                year = yf.stem.split('_')[-1]
                composites = len(ds.time)
                print(f"  {year}: {composites} composites")
                if composites > 0:
                    dates = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in ds.time.values[:5]]
                    print(f"    First dates: {', '.join(dates)}")
                ds.close()
            except Exception as e:
                print(f"  {yf.name}: Error - {e}")

    print("\nYou can now run the full download with:")
    print("  python app/run_ndvi.py")
    print("  # or in background:")
    print("  ./run_ndvi_background.sh")

except Exception as e:
    print("\n" + "="*80)
    print("✗ TEST FAILED!")
    print("="*80)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
