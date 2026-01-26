"""
Compare the two different GLM FED grid sizes
"""
import rioxarray
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Two files with different grid sizes
file1 = Path("/mnt/workwork/geoserver_data/glm_fed/glm_fed_20250417.tif")  # Small grid: 1063 x 999
file2 = Path("/mnt/workwork/geoserver_data/glm_fed/glm_fed_20250504.tif")  # Large grid: 1910 x ???

print("Loading GeoTIFF files...")
print(f"File 1: {file1.name}")
da1 = rioxarray.open_rasterio(file1).squeeze()
print(f"  Shape: {da1.shape}")
print(f"  CRS: {da1.rio.crs}")
print(f"  Bounds: {da1.rio.bounds()}")

print(f"\nFile 2: {file2.name}")
da2 = rioxarray.open_rasterio(file2).squeeze()
print(f"  Shape: {da2.shape}")
print(f"  CRS: {da2.rio.crs}")
print(f"  Bounds: {da2.rio.bounds()}")

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

# Plot file 1
vmax = max(np.nanmax(da1.values), np.nanmax(da2.values))
im1 = da1.plot(ax=ax1, cmap='YlOrRd', vmin=0, vmax=vmax, add_colorbar=False)
ax1.set_title(f'{file1.name}\nGrid: {da1.shape[0]} x {da1.shape[1]} pixels', fontsize=12, fontweight='bold')
ax1.set_xlabel('Longitude')
ax1.set_ylabel('Latitude')

# Plot file 2
im2 = da2.plot(ax=ax2, cmap='YlOrRd', vmin=0, vmax=vmax, add_colorbar=False)
ax2.set_title(f'{file2.name}\nGrid: {da2.shape[0]} x {da2.shape[1]} pixels', fontsize=12, fontweight='bold')
ax2.set_xlabel('Longitude')
ax2.set_ylabel('Latitude')

# Add shared colorbar
cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
cbar = fig.colorbar(im2, cax=cbar_ax)
cbar.set_label('Flash Extent Density (flashes/30min/8km²)', rotation=270, labelpad=20)

plt.suptitle('GLM FED Grid Size Comparison', fontsize=16, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0, 0.9, 0.96])

output_file = 'glm_grid_comparison.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\n✓ Saved comparison plot: {output_file}")

# Print statistics
print("\n" + "="*60)
print("STATISTICS")
print("="*60)
print(f"\nFile 1 ({file1.name}):")
print(f"  Grid size: {da1.shape[0]} x {da1.shape[1]} = {da1.shape[0] * da1.shape[1]:,} pixels")
print(f"  Min value: {np.nanmin(da1.values):.2f}")
print(f"  Max value: {np.nanmax(da1.values):.2f}")
print(f"  Mean value: {np.nanmean(da1.values):.2f}")

print(f"\nFile 2 ({file2.name}):")
print(f"  Grid size: {da2.shape[0]} x {da2.shape[1]} = {da2.shape[0] * da2.shape[1]:,} pixels")
print(f"  Min value: {np.nanmin(da2.values):.2f}")
print(f"  Max value: {np.nanmax(da2.values):.2f}")
print(f"  Mean value: {np.nanmean(da2.values):.2f}")

print(f"\nResolution difference: {(da2.shape[0] * da2.shape[1]) / (da1.shape[0] * da1.shape[1]):.2f}x more pixels in File 2")
print("="*60)
