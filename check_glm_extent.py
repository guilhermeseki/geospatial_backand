#!/usr/bin/env python3
"""Check the geographic extent of GLM FED data"""

import xarray as xr
import numpy as np
from pyproj import Proj, Transformer

file_path = "/mnt/workwork/geoserver_data/raw/glm_fed/glm_fed_daily_20250415.nc"

print("Loading GLM data...")
ds = xr.open_dataset(file_path)

# GOES-19 geostationary projection parameters
sat_lon = -75.2  # GOES-19 longitude position
sat_height = 35786023.0  # Geostationary orbit height in meters

print(f"\n🛰️ GOES-19 Parameters:")
print(f"  Satellite longitude: {sat_lon}°")
print(f"  Satellite height: {sat_height/1e6:.1f} million meters")

# Create projection transformer
goes_proj = Proj(f"+proj=geos +lon_0={sat_lon} +h={sat_height} +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs +sweep=x")
wgs84 = Proj("EPSG:4326")
transformer = Transformer.from_proj(goes_proj, wgs84)

# Get x, y coordinates in radians
x_rad = ds.x.values
y_rad = ds.y.values

print(f"\n📐 Native Coordinates (radians):")
print(f"  X range: {x_rad.min():.6f} to {x_rad.max():.6f}")
print(f"  Y range: {y_rad.min():.6f} to {y_rad.max():.6f}")

# Convert radians to meters
x_m = x_rad * sat_height
y_m = y_rad * sat_height

print(f"\n📐 Coordinates in meters:")
print(f"  X range: {x_m.min()/1e6:.2f} to {x_m.max()/1e6:.2f} million m")
print(f"  Y range: {y_m.min()/1e6:.2f} to {y_m.max()/1e6:.2f} million m")

# Get corner coordinates
corners_x = [x_m[0], x_m[-1], x_m[0], x_m[-1]]
corners_y = [y_m[0], y_m[0], y_m[-1], y_m[-1]]

print(f"\n🌍 Converting corners to Lat/Lon:")
for i, (x, y) in enumerate(zip(corners_x, corners_y)):
    lon, lat = transformer.transform(x, y)
    print(f"  Corner {i+1}: ({x/1e6:.2f}M, {y/1e6:.2f}M) → Lat {lat:.2f}°, Lon {lon:.2f}°")

# Create a coarse grid to check extent
x_grid_m, y_grid_m = np.meshgrid(x_m[::100], y_m[::100])  # Every 100th point
lon_grid, lat_grid = transformer.transform(x_grid_m.flatten(), y_grid_m.flatten())

# Filter out invalid coordinates (outside Earth disk)
valid = ~np.isnan(lon_grid) & ~np.isnan(lat_grid)
lon_valid = lon_grid[valid]
lat_valid = lat_grid[valid]

print(f"\n📍 Geographic Extent:")
print(f"  Longitude: {lon_valid.min():.2f}° to {lon_valid.max():.2f}°")
print(f"  Latitude: {lat_valid.min():.2f}° to {lat_valid.max():.2f}°")

# Check Latin America bbox
latam_bbox = (-53, -94, 25, -34)  # S, W, N, E
print(f"\n🌎 Latin America Bounding Box:")
print(f"  Target: Lat {latam_bbox[0]}° to {latam_bbox[2]}°, Lon {latam_bbox[1]}° to {latam_bbox[3]}°")

# Check overlap
lat_overlap = not (lat_valid.max() < latam_bbox[0] or lat_valid.min() > latam_bbox[2])
lon_overlap = not (lon_valid.max() < latam_bbox[1] or lon_valid.min() > latam_bbox[3])

print(f"\n{'✅' if (lat_overlap and lon_overlap) else '❌'} Data overlaps with Latin America: {lat_overlap and lon_overlap}")

if lat_overlap and lon_overlap:
    # Find the indices that cover Latin America
    # Create full grid (might be memory intensive for 2000x2500)
    print(f"\n🔍 Finding Latin America coverage in data...")
    print(f"  (This may take a moment for {len(x_m)} x {len(y_m)} = {len(x_m)*len(y_m):,} points)")

    # Sample more densely
    x_grid_m_fine, y_grid_m_fine = np.meshgrid(x_m[::10], y_m[::10])
    lon_grid_fine, lat_grid_fine = transformer.transform(x_grid_m_fine.flatten(), y_grid_m_fine.flatten())

    # Find points in LatAm bbox
    in_bbox = (
        (lat_grid_fine >= latam_bbox[0]) & (lat_grid_fine <= latam_bbox[2]) &
        (lon_grid_fine >= latam_bbox[1]) & (lon_grid_fine <= latam_bbox[3])
    )

    if in_bbox.any():
        latam_lon = lon_grid_fine[in_bbox]
        latam_lat = lat_grid_fine[in_bbox]
        print(f"  ✅ Found {in_bbox.sum():,} points covering Latin America")
        print(f"  Coverage: Lat {latam_lat.min():.2f}° to {latam_lat.max():.2f}°")
        print(f"            Lon {latam_lon.min():.2f}° to {latam_lon.max():.2f}°")
    else:
        print(f"  ❌ No points found in Latin America bounding box")

ds.close()
print("\n✅ Done!")
