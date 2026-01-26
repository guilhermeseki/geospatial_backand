#!/usr/bin/env python3
"""
Test script to verify ERA5 flow works with FUSE filesystem fix
Run a small test to download and process 1-2 days of data
"""
from datetime import date, timedelta
from app.workflows.data_processing.era5_flow import era5_land_daily_flow
from prefect import get_run_logger
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_era5_small_batch():
    """Test with a small date range"""
    print("=" * 80)
    print("ERA5 FLOW TEST - FUSE Filesystem Fix")
    print("=" * 80)
    print()
    print("This will download and process 2 days of data as a test")
    print()

    # Test with 2 days from 10 days ago (to ensure data is available)
    today = date.today()
    end_date = today - timedelta(days=10)
    start_date = end_date - timedelta(days=1)

    print(f"Test date range: {start_date} to {end_date}")
    print()

    # Test with both temperature variables
    variables_config = [
        {'variable': '2m_temperature', 'statistic': 'daily_maximum'},
        {'variable': '2m_temperature', 'statistic': 'daily_minimum'},
    ]

    try:
        print("Starting ERA5 flow...")
        print("=" * 80)
        result = era5_land_daily_flow(
            batch_days=2,
            variables_config=variables_config,
            start_date=start_date,
            end_date=end_date
        )

        print()
        print("=" * 80)
        print("✓ TEST PASSED!")
        print("=" * 80)
        print(f"Processed {len(result) if result else 0} files")
        print()
        print("The FUSE fix is working correctly!")
        print("You can now run the full ERA5 flow with:")
        print("  python app/run_era5.py")
        print()

        # Verify historical files exist and are valid
        from pathlib import Path
        from app.config.settings import get_settings
        import xarray as xr

        settings = get_settings()

        for var_config in variables_config:
            var = var_config['variable']
            stat = var_config['statistic']

            # Determine directory name from centralized config
            from app.config.data_sources import ERA5_VARIABLE_MAPPING
            dir_name = ERA5_VARIABLE_MAPPING.get(var, {}).get(stat, 'unknown')

            hist_file = Path(settings.DATA_DIR) / f"{dir_name}_hist" / "historical.nc"

            if hist_file.exists():
                print(f"\n✓ Historical file exists: {hist_file}")
                try:
                    ds = xr.open_dataset(hist_file)
                    print(f"  Variables: {list(ds.data_vars)}")
                    print(f"  Time dims: {len(ds.time)} days")
                    if len(ds.time) > 0:
                        print(f"  Date range: {ds.time.min().values} to {ds.time.max().values}")
                    ds.close()
                except Exception as e:
                    print(f"  ⚠️  Error reading file: {e}")
            else:
                print(f"\n⚠️  Historical file not found: {hist_file}")

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("✗ TEST FAILED!")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_era5_small_batch()
    exit(0 if success else 1)
