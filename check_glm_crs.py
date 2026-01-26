#!/usr/bin/env python3
"""Check the CRS of GLM FED data"""

import xarray as xr
import rioxarray

file_path = "/mnt/workwork/geoserver_data/raw/glm_fed/glm_fed_daily_20250415.nc"

print(f"Loading: {file_path}")
ds = xr.open_dataset(file_path)

# Check for CRS info
print("\n🗺️ CRS INFORMATION:")
print("=" * 80)

# Check attributes
if 'crs' in ds.attrs:
    print(f"Dataset CRS attr: {ds.attrs['crs']}")

if 'spatial_ref' in ds:
    print(f"Spatial ref: {ds.spatial_ref}")
    if hasattr(ds.spatial_ref, 'attrs'):
        for key, val in ds.spatial_ref.attrs.items():
            print(f"  {key}: {val}")

# Check if any variable has CRS
for var in ds.data_vars:
    if hasattr(ds[var], 'crs'):
        print(f"{var} CRS: {ds[var].crs}")
    if hasattr(ds[var], 'grid_mapping'):
        print(f"{var} grid_mapping: {ds[var].grid_mapping}")

# Check coordinates
print("\n📐 COORDINATE ATTRIBUTES:")
for coord in ['x', 'y']:
    if coord in ds.coords:
        print(f"\n{coord}:")
        for key, val in ds[coord].attrs.items():
            print(f"  {key}: {val}")

# Try to load with rioxarray
print("\n🔍 TRYING RIOXARRAY:")
try:
    ds_rio = rioxarray.open_rasterio(file_path)
    print(f"RioXarray CRS: {ds_rio.rio.crs}")
    print(f"RioXarray bounds: {ds_rio.rio.bounds()}")
except Exception as e:
    print(f"Could not load with rioxarray: {e}")

# Check if we can find projection info in the file
import netCDF4
nc = netCDF4.Dataset(file_path)
print("\n📦 NETCDF VARIABLES:")
for var in nc.variables:
    print(f"  {var}: {nc.variables[var].dimensions}")
    if var in ['goes_imager_projection', 'projection', 'crs', 'spatial_ref']:
        print(f"    Attributes:")
        for attr in nc.variables[var].ncattrs():
            print(f"      {attr}: {nc.variables[var].getncattr(attr)}")

nc.close()
ds.close()
