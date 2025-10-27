# Migration to Yearly Historical Files

## What Changed

Your geospatial backend now uses **yearly historical NetCDF files** instead of single large files for ALL data types (precipitation, temperature, NDVI).

### Before (Old Structure)
```
DATA_DIR/
├── chirps_historical/           # Old naming
│   └── brazil_chirps_2024.nc   # Already yearly, just wrong directory name
├── temp_max_hist/
│   └── historical.nc            # ❌ One big file, hard to manage
```

### After (New Structure)
```
DATA_DIR/
├── chirps_hist/                 # ✅ Consistent naming
│   ├── chirps_2024.nc          # ✅ Consistent file naming
│   └── chirps_2025.nc
├── temp_max_hist/
│   ├── temp_max_2024.nc        # ✅ Yearly files
│   └── temp_max_2025.nc
```

## Benefits

✅ **Manageable file sizes**: ~150MB per year instead of 10+ GB single file
✅ **Fast updates**: Only write to current year's file
✅ **Better performance**: Load only years you need
✅ **Consistent architecture**: Same pattern for all data types
✅ **Easy migration**: Rename directories, run flows

## Step-by-Step Migration

### Step 1: Rename Historical Directories

```bash
cd /mnt/workwork/geoserver_data

# Precipitation directories (if they exist)
if [ -d "chirps_historical" ]; then
    mv chirps_historical chirps_hist
    echo "✓ Renamed chirps_historical → chirps_hist"
fi

if [ -d "merge_historical" ]; then
    mv merge_historical merge_hist
    echo "✓ Renamed merge_historical → merge_hist"
fi
```

### Step 2: Rename Precipitation Historical Files

```bash
cd /mnt/workwork/geoserver_data

# CHIRPS: brazil_chirps_2024.nc → chirps_2024.nc
if [ -d "chirps_hist" ]; then
    cd chirps_hist
    for f in brazil_chirps_*.nc; do
        if [ -f "$f" ]; then
            new_name=$(echo "$f" | sed 's/brazil_chirps_/chirps_/')
            mv "$f" "$new_name"
            echo "✓ Renamed $f → $new_name"
        fi
    done
    cd ..
fi

# MERGE: brazil_merge_2024.nc → merge_2024.nc
if [ -d "merge_hist" ]; then
    cd merge_hist
    for f in brazil_merge_*.nc; do
        if [ -f "$f" ]; then
            new_name=$(echo "$f" | sed 's/brazil_merge_/merge_/')
            mv "$f" "$new_name"
            echo "✓ Renamed $f → $new_name"
        fi
    done
    cd ..
fi
```

### Step 3: Split ERA5 historical.nc into Yearly Files (Optional)

You have two options:

**Option A: Keep existing historical.nc (works but not optimal)**
- The new code will work with old `historical.nc` files
- But new data will create yearly files
- You'll have both formats mixed

**Option B: Split into yearly files (recommended)**

```python
# Run this script to split existing historical.nc into yearly files
python /opt/geospatial_backend/migrate_era5_to_yearly.py
```

I'll create this script for you below.

**Option C: Delete and redownload (cleanest)**
- Delete old `temp_max_hist/historical.nc`
- Run ERA5 flow - it will create yearly files from scratch

### Step 4: Test the Migration

```bash
cd /opt/geospatial_backend

# Test that yearly files load correctly
python test_yearly_loading.py
```

### Step 5: Run Flows Normally

After migration, all flows create/update yearly files automatically:

```bash
# ERA5 temperature (creates yearly files)
python app/run_era5.py

# Precipitation (updates yearly files)
# These scripts need to be updated to match new architecture
# See UNIFIED_DATA_ARCHITECTURE.md for details
```

## Migration Scripts

### Script 1: Migrate ERA5 to Yearly Files

Create `/opt/geospatial_backend/migrate_era5_to_yearly.py`:

```python
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
    print(f"\\n{'='*60}")
    print(f"Processing: {source}")
    print(f"{'='*60}")

    hist_dir = Path(settings.DATA_DIR) / f"{source}_hist"
    old_file = hist_dir / "historical.nc"

    if not old_file.exists():
        print(f"⚠️  No historical.nc found for {source}")
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
        print(f"\\n  📅 Year {year}")

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
    print(f"\\n{'='*60}")
    print(f"Migration complete for {source}!")
    print(f"Old file: {old_file}")
    print(f"New files: {list(hist_dir.glob(f'{source}_*.nc'))}")
    print(f"\\nYou can now delete the old historical.nc file:")
    print(f"  rm {old_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("\\n" + "="*60)
    print("ERA5 Historical → Yearly Migration")
    print("="*60)

    sources = ['temp_max', 'temp_min', 'temp']

    for source in sources:
        split_historical_to_yearly(source)

    print("\\n" + "="*60)
    print("✓ Migration Complete!")
    print("="*60)
    print("\\nNext steps:")
    print("1. Verify yearly files were created correctly")
    print("2. Delete old historical.nc files (optional)")
    print("3. Restart your FastAPI app to load yearly files")
    print("4. Test with: python test_yearly_loading.py")
```

### Script 2: Test Yearly Loading

Create `/opt/geospatial_backend/test_yearly_loading.py`:

```python
#!/usr/bin/env python3
"""
Test that yearly files load correctly
"""
import xarray as xr
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()

def test_source(source_type, source, hist_dir_name, file_pattern):
    print(f"\\n{'='*60}")
    print(f"Testing: {source} ({source_type})")
    print(f"{'='*60}")

    hist_dir = Path(settings.DATA_DIR) / hist_dir_name
    nc_files = sorted(hist_dir.glob(file_pattern))

    if not nc_files:
        print(f"✗ No files found in {hist_dir}")
        print(f"  Pattern: {file_pattern}")
        return False

    print(f"✓ Found {len(nc_files)} yearly files:")
    for f in nc_files:
        size_mb = f.stat().st_size / (1024**2)
        print(f"  - {f.name} ({size_mb:.1f} MB)")

    try:
        print(f"\\nLoading with open_mfdataset...")
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
        return False


if __name__ == "__main__":
    print("\\n" + "="*60)
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

    print("\\n" + "="*60)
    print("Test Results")
    print("="*60)
    print(f"Passed: {sum(results)}/{len(results)}")

    if all(results):
        print("✓ All tests passed!")
        print("\\nYou can now:")
        print("1. Restart your FastAPI app")
        print("2. Run data flows normally")
    else:
        print("✗ Some tests failed")
        print("\\nCheck the errors above and:")
        print("1. Verify files exist in correct locations")
        print("2. Check file naming matches patterns")
        print("3. Run migration scripts if needed")
```

## After Migration

### What Works Automatically

✅ **API queries**: No changes needed, `get_dataset()` works the same
✅ **GeoServer**: Continues to use daily GeoTIFFs
✅ **Data flows**: Automatically create/update yearly files
✅ **Loading**: All yearly files combine seamlessly

### What to Update

For **precipitation flows**, you'll want to create unified flows similar to ERA5. See `UNIFIED_DATA_ARCHITECTURE.md` for the design.

Key tasks to implement:
- `check_missing_dates()` - check both GeoTIFF and yearly historical
- `process_to_geotiff()` - create daily GeoTIFFs
- `append_to_yearly_historical()` - update yearly NetCDF

## Troubleshooting

### Files not loading

**Problem**: `No yearly files found for 'temp_max'`

**Solution**:
1. Check if files exist: `ls /mnt/workwork/geoserver_data/temp_max_hist/`
2. Check file naming: Should be `temp_max_2024.nc`, not `historical.nc`
3. Run migration script if needed

### Wrong directory names

**Problem**: `chirps_historical` instead of `chirps_hist`

**Solution**: Run Step 1 of migration (rename directories)

### Mixed old and new files

**Problem**: Have both `historical.nc` and `temp_max_2024.nc`

**Solution**:
1. Verify yearly files are complete
2. Delete old `historical.nc`: `rm temp_max_hist/historical.nc`
3. Restart FastAPI app

## Summary

The migration is simple:
1. **Rename directories**: `*_historical` → `*_hist`
2. **Rename files**: `brazil_{source}_` → `{source}_`
3. **Split ERA5** (optional): Run migration script
4. **Test**: Run test script
5. **Done**: Run flows normally!

All new data will automatically use yearly files. 🎉
