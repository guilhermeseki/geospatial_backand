"""Debug why historical NetCDF files aren't being created"""
import xarray as xr
import pandas as pd
from pathlib import Path
from datetime import date

# Paths
daily_path = Path("/mnt/workwork/geoserver_data/raw/era5_solar/daily_hourly_2025-11-18_2025-11-21.nc")

# Test dates
dates_to_append = [
    date(2025, 11, 18),
    date(2025, 11, 19),
    date(2025, 11, 20),
    date(2025, 11, 21)
]

print("="*80)
print("Debugging Solar Historical NetCDF Issue")
print("="*80)

# Check if daily file exists
if not daily_path.exists():
    print(f"❌ Daily file not found: {daily_path}")
    print("   (It was cleaned up after processing)")
    print("\nLet's re-run the pipeline without cleanup to debug...")
else:
    print(f"✓ Daily file exists: {daily_path}")

    # Open and inspect
    ds = xr.open_dataset(daily_path)
    da = ds['solar_radiation']

    print(f"\n📊 Dataset info:")
    print(f"   Variables: {list(ds.data_vars)}")
    print(f"   Dimensions: {dict(ds.dims)}")
    print(f"   Time coord type: {type(da.time.values[0])}")
    print(f"   Time values:\n{da.time.values}")

    print(f"\n🔍 Testing time filter...")
    time_filter = [pd.Timestamp(d) for d in dates_to_append]
    print(f"   Filter timestamps: {time_filter}")

    # Test isin()
    mask = da.time.isin(time_filter)
    print(f"   Mask result: {mask.values}")
    print(f"   Any True values? {mask.any().values}")

    # Try filtering
    filtered = da.sel(time=mask)
    print(f"   Filtered data shape: {filtered.shape}")
    print(f"   Filtered time coord: {filtered.time.values if len(filtered.time) > 0 else 'EMPTY!'}")

    # Test grouping by year
    print(f"\n📅 Testing year grouping...")
    years = pd.to_datetime(da.time.values).year.unique()
    print(f"   Years found: {years}")

    for year in years:
        year_data = da.sel(time=da.time.dt.year == year)
        print(f"   Year {year}: {len(year_data.time)} days")

    ds.close()

print("\n" + "="*80)
