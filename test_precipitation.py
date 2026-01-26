#!/usr/bin/env python3
"""
Test precipitation yearly historical build with a single year
"""
from app.workflows.data_processing.precipitation_flow import build_precipitation_yearly_historical
from app.workflows.data_processing.schemas import DataSource
from pathlib import Path
from app.config.settings import get_settings
import xarray as xr

print("="*80)
print("PRECIPITATION YEARLY HISTORICAL TEST")
print("="*80)
print("\nThis will create yearly NetCDF for 2024 only (as a test)")
print("="*80)
print()

try:
    # Test CHIRPS for year 2024
    print("[1/2] Testing CHIRPS 2024...")
    chirps_files = build_precipitation_yearly_historical(
        DataSource.CHIRPS,
        start_year=2024,
        end_year=2024
    )

    # Test MERGE for year 2024
    print("\n[2/2] Testing MERGE 2024...")
    merge_files = build_precipitation_yearly_historical(
        DataSource.MERGE,
        start_year=2024,
        end_year=2024
    )

    print("\n" + "="*80)
    print("✓ TEST PASSED!")
    print("="*80)

    # Verify files
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)

    for source in ['chirps', 'merge']:
        hist_file = data_dir / f"{source}_hist" / f"{source}_2024.nc"
        if hist_file.exists():
            ds = xr.open_dataset(hist_file)
            print(f"\n✓ {source.upper()} 2024:")
            print(f"  File: {hist_file}")
            print(f"  Days: {len(ds.time)}")
            print(f"  Variable: {list(ds.data_vars)}")
            print(f"  Shape: {ds['precipitation'].shape}")
            ds.close()
        else:
            print(f"\n✗ {source.upper()} 2024: File not found")

    print("\nYou can now run the full build with:")
    print("  python app/run_precipitation.py")
    print("  # or in background:")
    print("  ./run_precipitation_background.sh")

except Exception as e:
    print("\n" + "="*80)
    print("✗ TEST FAILED!")
    print("="*80)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
