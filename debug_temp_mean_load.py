#!/usr/bin/env python3
"""Debug temp_mean loading to see what's happening"""

import xarray as xr
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()

# Test loading temp_mean exactly as the service does
hist_dir = Path(settings.DATA_DIR) / "temp_mean_hist"
nc_files = sorted(hist_dir.glob("temp_mean_*.nc"))

print(f"Loading temp_mean from: {hist_dir}")
print(f"Files found: {len(nc_files)}")
for f in nc_files:
    print(f"  - {f.name}")

print("\nLoading with open_mfdataset...")
ds = xr.open_mfdataset(
    nc_files,
    combine="nested",
    concat_dim="time",
    engine="netcdf4",
    parallel=False,  # Test without Dask first
    chunks={"time": -1, "latitude": 20, "longitude": 20},
    cache=False,
)

print(f"\n✓ Dataset loaded")
print(f"  Variables: {list(ds.data_vars)}")
print(f"  Coordinates: {list(ds.coords)}")
print(f"  Dims: {dict(ds.dims)}")

# Check if 'temp_mean' exists
if 'temp_mean' in ds.data_vars:
    print(f"\n✓ Variable 'temp_mean' exists")
    print(f"  Shape: {ds['temp_mean'].shape}")
    print(f"  Dtype: {ds['temp_mean'].dtype}")
    print(f"  Chunks: {ds['temp_mean'].chunks}")
else:
    print(f"\n✗ Variable 'temp_mean' NOT FOUND!")
    print(f"  Available: {list(ds.data_vars)}")

# Test a simple query
print(f"\nTesting point query at -15.8, -47.9 on 2025-01-25:")
import pandas as pd
test_data = ds.sel(
    latitude=-15.8,
    longitude=-47.9,
    time='2025-01-25',
    method='nearest'
)
print(f"  temp_mean value: {test_data['temp_mean'].values}")

# Test area query
print(f"\nTesting area query:")
DEGREES_TO_KM = 111.0
lat, lon, radius = -15.8, -47.9, 10.0
radius_deg = radius / DEGREES_TO_KM
lat_min, lat_max = lat - radius_deg, lat + radius_deg
lon_min, lon_max = lon - radius_deg, lon + radius_deg

print(f"  Bounds: lat[{lat_min:.2f}, {lat_max:.2f}] lon[{lon_min:.2f}, {lon_max:.2f}]")

ds_slice = ds.sel(
    latitude=slice(lat_max, lat_min),
    longitude=slice(lon_min, lon_max),
    time='2025-01-25'
)

print(f"  Slice shape: {ds_slice['temp_mean'].shape}")
print(f"  Slice dims: {dict(ds_slice.dims)}")

if ds_slice['temp_mean'].size > 0:
    temp_values = ds_slice['temp_mean'].compute()
    print(f"  Temp range: {temp_values.min().values:.2f} to {temp_values.max().values:.2f}°C")
    above_15 = (temp_values > 15.0).sum().values
    print(f"  Points above 15.0°C: {above_15}")
else:
    print(f"  ✗ Slice is empty!")

ds.close()
