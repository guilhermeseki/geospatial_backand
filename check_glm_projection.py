#!/usr/bin/env python3
"""Get the full GOES projection details from GLM data"""

import xarray as xr
import netCDF4

file_path = "/mnt/workwork/geoserver_data/raw/glm_fed/glm_fed_daily_20250415.nc"

nc = netCDF4.Dataset(file_path)

print("🛰️ GOES IMAGER PROJECTION DETAILS:")
print("=" * 80)

if 'goes_imager_projection' in nc.variables:
    proj = nc.variables['goes_imager_projection']
    print(f"Variable: goes_imager_projection")
    print(f"Dimensions: {proj.dimensions}")
    print(f"\nAttributes:")
    for attr in proj.ncattrs():
        print(f"  {attr}: {proj.getncattr(attr)}")
else:
    print("No goes_imager_projection variable found")
    print("\nAll variables:")
    for var in nc.variables:
        print(f"  - {var}")

nc.close()

# Now try to convert x,y radians to lat/lon
print("\n\n🌍 CONVERTING RADIANS TO LAT/LON:")
print("=" * 80)

import numpy as np
from pyproj import Proj, Transformer

ds = xr.open_dataset(file_path)

# GOES-East/West geostationary projection parameters
# For GOES-19 (GOES-East), longitude is typically -75.2 degrees
# We need to construct the proj string from the grid_mapping attributes

# Sample some x,y points to convert
x_sample = ds.x.values[::500]  # Every 500th point
y_sample = ds.y.values[::500]

print(f"X sample (radians): {x_sample}")
print(f"Y sample (radians): {y_sample}")

# GOES-19 is at 75.2°W
# Create a transformer from GOES projection to lat/lon
# GOES geostationary projection formula
sat_lon = -75.2  # GOES-19 position
sat_height = 35786023.0  # Geostationary height in meters

# Create the GOES projection
goes_proj = Proj(f"+proj=geos +lon_0={sat_lon} +h={sat_height} +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs +sweep=x")
wgs84 = Proj("EPSG:4326")

transformer = Transformer.from_proj(goes_proj, wgs84)

# Convert radians to meters (multiply by satellite height)
x_m = x_sample * sat_height
y_m = y_sample * sat_height

print(f"\nX in meters: {x_m}")
print(f"Y in meters: {y_m}")

# Transform to lat/lon
lon, lat = transformer.transform(x_m, y_m)

print(f"\nLongitude: {lon}")
print(f"Latitude: {lat}")

# Check full data extent
x_full = ds.x.values * sat_height
y_full = ds.y.values * sat_height

lon_full, lat_full = transformer.transform(
    np.meshgrid(x_full, y_full)[0].flatten(),
    np.meshgrid(x_full, y_full)[1].flatten()
)

print(f"\n📍 FULL DATA EXTENT:")
print(f"  Longitude: {np.nanmin(lon_full):.2f} to {np.nanmax(lon_full):.2f}")
print(f"  Latitude: {np.nanmin(lat_full):.2f} to {np.nanmax(lat_full):.2f}")

print(f"\n🌎 LATIN AMERICA BBOX:")
latam_bbox = (-53, -94, 25, -34)  # S, W, N, E
print(f"  Target: S={latam_bbox[0]}, W={latam_bbox[1]}, N={latam_bbox[2]}, E={latam_bbox[3]}")
print(f"  Data covers: Lat {np.nanmin(lat_full):.2f} to {np.nanmax(lat_full):.2f}")
print(f"               Lon {np.nanmin(lon_full):.2f} to {np.nanmax(lon_full):.2f}")

# Check overlap
lat_overlap = not (np.nanmax(lat_full) < latam_bbox[0] or np.nanmin(lat_full) > latam_bbox[2])
lon_overlap = not (np.nanmax(lon_full) < latam_bbox[1] or np.nanmin(lon_full) > latam_bbox[3])

print(f"\n✓ Overlaps with Latin America: {lat_overlap and lon_overlap}")

ds.close()
