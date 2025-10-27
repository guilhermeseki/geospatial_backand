#!/usr/bin/env python3
"""
Test that yearly files load correctly
"""
import xarray as xr
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()

def test_source(source_type, source, hist_dir_name, file_pattern):
    print(f"\n{'='*60}")
    print(f"Testing: {source} ({source_type})")
    print(f"{'='*60}")

    hist_dir = Path(settings.DATA_DIR) / hist_dir_name
    nc_files = sorted(hist_dir.glob(file_pattern))

    if not nc_files:
        print(f"⚠️  No files found in {hist_dir}")
        print(f"   Pattern: {file_pattern}")
        print(f"   (This is OK if you haven't run the flow yet)")
        return None

    print(f"✓ Found {len(nc_files)} yearly files:")
    for f in nc_files:
        size_mb = f.stat().st_size / (1024**2)
        print(f"  - {f.name} ({size_mb:.1f} MB)")

    try:
        print(f"\nLoading with open_mfdataset...")
        ds = xr.open_mfdataset(
            nc_files,
            combine="nested",
            concat_dim="time",
            engine="netcdf4",
            chunks={"time": -1, "latitude": 20, "longitude": 20},
        )

        print(f"✓ Successfully loaded!")
        print(f"  Variables: {list(ds.data_vars)}")
        print(f"  Dimensions: {dict(ds.dims)}")
        if 'time' in ds.dims:
            print(f"  Time range: {ds.time.min().values} to {ds.time.max().values}")
            print(f"  Total days: {len(ds.time)}")

        ds.close()
        return True

    except Exception as e:
        print(f"✗ Failed to load: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Yearly Files Loading Test")
    print("="*60)

    results = []

    # Test precipitation
    results.append(test_source("precipitation", "chirps", "chirps_hist", "chirps_*.nc"))
    results.append(test_source("precipitation", "merge", "merge_hist", "merge_*.nc"))

    # Test temperature
    results.append(test_source("temperature", "temp_max", "temp_max_hist", "temp_max_*.nc"))
    results.append(test_source("temperature", "temp_min", "temp_min_hist", "temp_min_*.nc"))
    results.append(test_source("temperature", "temp", "temp_hist", "temp_*.nc"))

    # Filter out None results (sources that don't have files yet)
    results = [r for r in results if r is not None]

    print("\n" + "="*60)
    print("Test Results")
    print("="*60)
    if results:
        print(f"Passed: {sum(results)}/{len(results)}")

        if all(results):
            print("\n✓ All tests passed!")
            print("\nYou can now:")
            print("1. Restart your FastAPI app")
            print("2. Run data flows normally")
            print("3. All yearly files will load automatically")
        else:
            print("\n✗ Some tests failed")
            print("\nCheck the errors above and:")
            print("1. Verify files exist in correct locations")
            print("2. Check file naming matches patterns")
            print("3. Run migration scripts if needed")
    else:
        print("⚠️  No yearly files found yet")
        print("\nThis is normal if you haven't:")
        print("1. Run any data flows yet, OR")
        print("2. Migrated existing historical.nc files")
        print("\nNext steps:")
        print("- Run migration: python migrate_era5_to_yearly.py")
        print("- OR run flows: python app/run_era5.py")
