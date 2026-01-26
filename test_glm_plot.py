#!/usr/bin/env python3
"""Test script to plot GLM FED data and check its structure"""

import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

# Load the data
file_path = "/mnt/workwork/geoserver_data/raw/glm_fed/glm_fed_daily_20250415.nc"
print(f"Loading: {file_path}")
print("=" * 80)

ds = xr.open_dataset(file_path)

# Print dataset info
print("\n📊 DATASET INFO:")
print(ds)

print("\n📐 DIMENSIONS:")
for dim in ds.dims:
    print(f"  {dim}: {ds.dims[dim]}")

print("\n🗺️ COORDINATES:")
for coord in ds.coords:
    print(f"  {coord}: {ds.coords[coord].shape}")
    if ds.coords[coord].size <= 10:
        print(f"    Values: {ds.coords[coord].values}")
    else:
        print(f"    Min: {ds.coords[coord].min().values}, Max: {ds.coords[coord].max().values}")

print("\n📦 DATA VARIABLES:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].shape} - {ds[var].dims}")
    print(f"    Min: {ds[var].min().values}, Max: {ds[var].max().values}")
    print(f"    Non-zero count: {np.count_nonzero(~np.isnan(ds[var].values))}")

# Check if it has spatial_ref
if 'spatial_ref' in ds.coords:
    print("\n🌐 SPATIAL REFERENCE:")
    print(f"  CRS: {ds.spatial_ref}")

# Try to plot the max FED
print("\n📈 PLOTTING...")
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Plot 1: Max FED
var_name = 'flash_extent_density_30min_max'
if var_name in ds:
    data = ds[var_name].isel(time=0)

    # Plot raw data
    im1 = axes[0].imshow(data, cmap='hot', interpolation='nearest')
    axes[0].set_title(f'GLM FED Max (Raw)\n{file_path.split("/")[-1]}')
    axes[0].set_xlabel('X index')
    axes[0].set_ylabel('Y index')
    plt.colorbar(im1, ax=axes[0], label='Flash Extent Density')

    # Plot with bounds if available
    if 'x' in ds.coords and 'y' in ds.coords:
        x = ds.x.values
        y = ds.y.values
        im2 = axes[1].pcolormesh(x, y, data, cmap='hot', shading='auto')
        axes[1].set_title('GLM FED Max (Georeferenced)')
        axes[1].set_xlabel('X (m)')
        axes[1].set_ylabel('Y (m)')
        plt.colorbar(im2, ax=axes[1], label='Flash Extent Density')

        # Show coordinate ranges
        print(f"  X range: {x.min()} to {x.max()}")
        print(f"  Y range: {y.min()} to {y.max()}")
    elif 'lon' in ds.coords and 'lat' in ds.coords:
        lon = ds.lon.values
        lat = ds.lat.values
        im2 = axes[1].pcolormesh(lon, lat, data, cmap='hot', shading='auto')
        axes[1].set_title('GLM FED Max (Georeferenced)')
        axes[1].set_xlabel('Longitude')
        axes[1].set_ylabel('Latitude')
        plt.colorbar(im2, ax=axes[1], label='Flash Extent Density')

        print(f"  Lon range: {lon.min()} to {lon.max()}")
        print(f"  Lat range: {lat.min()} to {lat.max()}")

plt.tight_layout()
plt.savefig('glm_fed_test_plot.png', dpi=150, bbox_inches='tight')
print(f"\n✅ Plot saved to: glm_fed_test_plot.png")

# Check Latin America bounding box
print("\n🌎 LATIN AMERICA CHECK:")
latam_bbox = (-53, -94, 25, -34)  # S, W, N, E
print(f"  Target bbox (S, W, N, E): {latam_bbox}")

# Try to see if we can extract lat/lon from the CRS
try:
    import rioxarray
    ds_rio = xr.open_dataset(file_path)
    ds_rio = ds_rio.rio.write_crs("EPSG:32615")  # Try UTM Zone 15N
    print(f"\n  Trying to extract geographic coordinates...")

    # Get bounds in the native CRS
    bounds = ds_rio.rio.bounds()
    print(f"  Native bounds: {bounds}")

except Exception as e:
    print(f"  Could not extract geographic coordinates: {e}")

ds.close()
print("\n✅ Done!")
