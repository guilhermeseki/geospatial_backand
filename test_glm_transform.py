#!/usr/bin/env python3
"""Test the proper GOES projection transformation"""

import xarray as xr
import numpy as np
import rioxarray
from pyproj import CRS, Transformer

file_path = "/mnt/workwork/geoserver_data/raw/glm_fed/glm_fed_daily_20250415.nc"

print("Testing different projection approaches...")

ds = xr.open_dataset(file_path)

# Read the actual data
fed = ds['flash_extent_density_30min_max'].isel(time=0)

print(f"\n📊 Data shape: {fed.shape}")
print(f"📊 Data range: {fed.min().values:.2f} to {fed.max().values:.2f}")
print(f"📊 Non-NaN values: {np.count_nonzero(~np.isnan(fed.values)):,}")

# Try setting CRS manually and using rioxarray
# GOES-19 Fixed Grid projection (Geostationary)
# Standard parameters for GOES-East
sat_lon = -75.2
sat_height = 35786023.0
sweep = 'x'  # GOES satellites use x-sweep

# CF-compliant proj string for GOES geostationary
goes_crs = CRS.from_cf({
    'grid_mapping_name': 'geostationary',
    'perspective_point_height': sat_height,
    'longitude_of_projection_origin': sat_lon,
    'semi_major_axis': 6378137.0,
    'semi_minor_axis': 6356752.31414,
    'sweep_angle_axis': sweep
})

print(f"\n🛰️ GOES CRS:")
print(f"  {goes_crs.to_proj4()}")

# Apply CRS to data using x,y in radians converted to meters
x_meters = ds.x.values * sat_height
y_meters = ds.y.values * sat_height

# Create a DataArray with proper coordinates
fed_geo = xr.DataArray(
    fed.values,
    coords={
        'y': y_meters,
        'x': x_meters
    },
    dims=['y', 'x']
)

# Write CRS
fed_geo = fed_geo.rio.write_crs(goes_crs)

print(f"\n📐 Data with CRS:")
print(f"  CRS: {fed_geo.rio.crs}")
print(f"  Bounds (native): {fed_geo.rio.bounds()}")

# Reproject to EPSG:4326 (WGS84)
print(f"\n🔄 Reprojecting to WGS84...")
fed_latlon = fed_geo.rio.reproject("EPSG:4326")

print(f"\n✅ Reprojected data:")
print(f"  Shape: {fed_latlon.shape}")
print(f"  Bounds: {fed_latlon.rio.bounds()}")  # (minx, miny, maxx, maxy) = (W, S, E, N)
print(f"  X (lon) range: {fed_latlon.x.min().values:.2f} to {fed_latlon.x.max().values:.2f}")
print(f"  Y (lat) range: {fed_latlon.y.min().values:.2f} to {fed_latlon.y.max().values:.2f}")

# Check overlap with Latin America
latam_bbox = (-53, -94, 25, -34)  # S, W, N, E
bounds = fed_latlon.rio.bounds()  # W, S, E, N
data_bbox = (bounds[1], bounds[0], bounds[3], bounds[2])  # S, W, N, E

print(f"\n🌎 Bounding Box Comparison:")
print(f"  Latin America: S={latam_bbox[0]}, W={latam_bbox[1]}, N={latam_bbox[2]}, E={latam_bbox[3]}")
print(f"  GLM Data:      S={data_bbox[0]:.1f}, W={data_bbox[1]:.1f}, N={data_bbox[2]:.1f}, E={data_bbox[3]:.1f}")

# Check overlap
lat_overlap = not (data_bbox[2] < latam_bbox[0] or data_bbox[0] > latam_bbox[2])
lon_overlap = not (data_bbox[3] < latam_bbox[1] or data_bbox[1] > latam_bbox[3])

print(f"\n{'✅' if (lat_overlap and lon_overlap) else '❌'} Overlaps: {lat_overlap and lon_overlap}")

# Save a sample plot
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Plot native projection
fed_geo.plot(ax=ax1, cmap='hot', add_colorbar=True)
ax1.set_title('GLM FED (Native GOES projection)')
ax1.set_xlabel('X (meters)')
ax1.set_ylabel('Y (meters)')

# Plot reprojected
fed_latlon.plot(ax=ax2, cmap='hot', add_colorbar=True)
ax2.set_title('GLM FED (Reprojected to WGS84)')
ax2.set_xlabel('Longitude')
ax2.set_ylabel('Latitude')

# Add Latin America bbox
ax2.plot([latam_bbox[1], latam_bbox[3], latam_bbox[3], latam_bbox[1], latam_bbox[1]],
         [latam_bbox[0], latam_bbox[0], latam_bbox[2], latam_bbox[2], latam_bbox[0]],
         'r-', linewidth=2, label='Latin America bbox')
ax2.legend()

plt.tight_layout()
plt.savefig('glm_reprojected_test.png', dpi=150, bbox_inches='tight')
print(f"\n💾 Saved plot to: glm_reprojected_test.png")

ds.close()
