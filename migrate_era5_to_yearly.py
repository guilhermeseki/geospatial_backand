#!/usr/bin/env python3
"""
Split existing ERA5 historical.nc files into yearly files
Run this ONCE after updating the code
"""
import xarray as xr
import pandas as pd
from pathlib import Path
from app.config.settings import get_settings
import tempfile
import shutil

settings = get_settings()

def split_historical_to_yearly(source):
    """Split historical.nc into yearly files for a temperature source"""
    print(f"\n{'='*60}")
    print(f"Processing: {source}")
    print(f"{'='*60}")

    hist_dir = Path(settings.DATA_DIR) / f"{source}_hist"
    old_file = hist_dir / "historical.nc"

    if not old_file.exists():
        print(f"⚠️  No historical.nc found for {source}")
        print(f"   (This is OK if you haven't run ERA5 flow yet or already migrated)")
        return

    print(f"📂 Reading: {old_file}")
    ds = xr.open_dataset(old_file)

    if source not in ds.data_vars:
        print(f"✗ Variable '{source}' not found in dataset")
        print(f"  Available: {list(ds.data_vars)}")
        ds.close()
        return

    da = ds[source]
    all_dates = pd.to_datetime(da.time.values)

    # Group by year
    years = sorted(set(d.year for d in all_dates))
    print(f"  Years in data: {years}")
    print(f"  Total days: {len(all_dates)}")

    for year in years:
        print(f"\n  📅 Year {year}")

        # Extract year's data
        year_data = da.sel(time=str(year))

        if len(year_data.time) == 0:
            print(f"    No data for {year}, skipping")
            continue

        # Create yearly file
        year_file = hist_dir / f"{source}_{year}.nc"

        if year_file.exists():
            print(f"    ⚠️  File already exists: {year_file.name}")
            continue

        # FUSE-safe write
        temp_dir = Path(tempfile.mkdtemp(prefix=f"migrate_{year}_"))
        temp_file = temp_dir / f"{source}_{year}.nc"

        try:
            year_ds = year_data.to_dataset()
            year_ds.attrs['year'] = year

            encoding = {
                source: {
                    'chunksizes': (1, 20, 20),
                    'zlib': True,
                    'complevel': 5,
                    'dtype': 'float32'
                }
            }

            print(f"    Writing {len(year_data.time)} days...")
            year_ds.to_netcdf(str(temp_file), mode='w', encoding=encoding, engine='netcdf4')

            print(f"    Copying to: {year_file.name}")
            shutil.copy2(temp_file, year_file)

            shutil.rmtree(temp_dir, ignore_errors=True)

            file_size_mb = year_file.stat().st_size / (1024**2)
            print(f"    ✓ Created {year_file.name} ({file_size_mb:.1f} MB)")

        except Exception as e:
            print(f"    ✗ Failed: {e}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    ds.close()

    # Ask if user wants to delete old file
    print(f"\n{'='*60}")
    print(f"Migration complete for {source}!")
    print(f"Old file: {old_file}")
    new_files = list(hist_dir.glob(f'{source}_*.nc'))
    print(f"New files: {len(new_files)} yearly files created")
    print(f"\nYou can now delete the old historical.nc file:")
    print(f"  rm {old_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ERA5 Historical → Yearly Migration")
    print("="*60)

    sources = ['temp_max', 'temp_min', 'temp']

    for source in sources:
        split_historical_to_yearly(source)

    print("\n" + "="*60)
    print("✓ Migration Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Verify yearly files were created correctly")
    print("2. Delete old historical.nc files:")
    print("   rm /mnt/workwork/geoserver_data/temp_*_hist/historical.nc")
    print("3. Restart your FastAPI app to load yearly files")
    print("4. Test with: python test_yearly_loading.py")
