#!/usr/bin/env python3
"""
Visualize MODIS NDVI with better cropping and composite view
"""
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from app.config.settings import get_settings
import pandas as pd

# Custom NDVI colormap
colors = ['#8B4513', '#CD853F', '#F4A460', '#FFFACD', '#FFFF00', '#ADFF2F', '#32CD32', '#228B22', '#006400']
ndvi_cmap = LinearSegmentedColormap.from_list('ndvi', colors, N=100)

settings = get_settings()
data_dir = Path(settings.DATA_DIR)

print("="*80)
print("MODIS NDVI COMBINED VISUALIZATION")
print("="*80)

yearly_file = data_dir / "ndvi_modis_hist" / "ndvi_modis_2024.nc"

if not yearly_file.exists():
    print("\n✗ No NetCDF file found!")
    exit(1)

print(f"\nReading: {yearly_file}")
ds = xr.open_dataset(yearly_file)

print(f"\nDataset info:")
print(f"  Time steps: {len(ds.time)}")
print(f"  Grid size: {len(ds.latitude)} x {len(ds.longitude)} pixels")

# Get NDVI data
ndvi = ds['ndvi'].values

# Create a composite by taking the mean across all time steps (ignoring NaN)
print(f"\nCreating composite from {len(ds.time)} time steps...")
composite = np.nanmean(ndvi, axis=0)

# Find bounding box of valid data
valid_mask = ~np.isnan(composite)
rows, cols = np.where(valid_mask)

if len(rows) == 0:
    print("\n✗ No valid data found!")
    ds.close()
    exit(1)

# Add padding around valid region
padding = 100
row_min = max(0, rows.min() - padding)
row_max = min(composite.shape[0], rows.max() + padding)
col_min = max(0, cols.min() - padding)
col_max = min(composite.shape[1], cols.max() + padding)

print(f"\nValid data extent:")
print(f"  Rows: {rows.min()} to {rows.max()} (of {composite.shape[0]})")
print(f"  Cols: {cols.min()} to {cols.max()} (of {composite.shape[1]})")
print(f"  Valid pixels: {np.sum(valid_mask)} ({100*np.sum(valid_mask)/composite.size:.2f}%)")
print(f"  NDVI range: {np.nanmin(composite):.3f} to {np.nanmax(composite):.3f}")
print(f"  Mean NDVI: {np.nanmean(composite):.3f}")

# Crop to valid region
composite_crop = composite[row_min:row_max, col_min:col_max]
lats_crop = ds.latitude.values[row_min:row_max]
lons_crop = ds.longitude.values[col_min:col_max]

print(f"\nCropped to: {composite_crop.shape[0]} x {composite_crop.shape[1]} pixels")

# Create figure with composite and individual time steps
fig = plt.figure(figsize=(18, 12))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

# Large composite plot
ax_main = fig.add_subplot(gs[:2, :])
im = ax_main.imshow(composite_crop, cmap=ndvi_cmap, vmin=-0.2, vmax=1.0,
                     extent=[lons_crop.min(), lons_crop.max(), lats_crop.min(), lats_crop.max()],
                     interpolation='bilinear', aspect='auto')

ax_main.set_title(f'MODIS NDVI Composite - September 2024\n'
                  f'Mean of {len(ds.time)} composites | Mean NDVI: {np.nanmean(composite):.3f} | '
                  f'{100*np.sum(valid_mask)/composite.size:.2f}% coverage',
                  fontsize=14, fontweight='bold', pad=20)
ax_main.set_xlabel('Longitude', fontsize=11)
ax_main.set_ylabel('Latitude', fontsize=11)
ax_main.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

# Colorbar
cbar = plt.colorbar(im, ax=ax_main, fraction=0.02, pad=0.02)
cbar.set_label('NDVI Value', fontsize=11)
cbar.ax.tick_params(labelsize=10)

# Add interpretation box
textstr = '\n'.join([
    'NDVI Interpretation:',
    '< 0.1: Water, bare soil',
    '0.1-0.2: Sparse vegetation',
    '0.2-0.4: Moderate vegetation',
    '0.4-0.6: Dense vegetation',
    '> 0.6: Very dense vegetation'
])
props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray')
ax_main.text(0.02, 0.98, textstr, transform=ax_main.transAxes, fontsize=9,
            verticalalignment='top', bbox=props, family='monospace')

# Show 3 individual time steps with best coverage
valid_counts = [np.sum(~np.isnan(ndvi[i])) for i in range(len(ds.time))]
best_indices = np.argsort(valid_counts)[-3:][::-1]  # Top 3

for plot_idx, time_idx in enumerate(best_indices):
    ax = fig.add_subplot(gs[2, plot_idx])

    data_crop = ndvi[time_idx, row_min:row_max, col_min:col_max]
    date_str = pd.to_datetime(ds.time.values[time_idx]).strftime('%Y-%m-%d')

    im_small = ax.imshow(data_crop, cmap=ndvi_cmap, vmin=-0.2, vmax=1.0,
                         extent=[lons_crop.min(), lons_crop.max(), lats_crop.min(), lats_crop.max()],
                         interpolation='nearest', aspect='auto')

    valid_pct = 100 * np.sum(~np.isnan(data_crop)) / data_crop.size
    ax.set_title(f'{date_str}\n{valid_pct:.1f}% valid', fontsize=9)
    ax.set_xlabel('Lon', fontsize=8)
    ax.set_ylabel('Lat', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.3)

plt.suptitle('MODIS NDVI Analysis - Latin America Coverage',
             fontsize=16, fontweight='bold', y=0.995)

output_file = Path('modis_ndvi_cropped_composite.png')
plt.savefig(output_file, dpi=200, bbox_inches='tight')
print(f"\n✓ Composite plot saved: {output_file}")

# Create a coverage map showing which pixels have any valid data
fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Coverage mask
coverage_mask = np.sum(~np.isnan(ndvi), axis=0)  # Count valid time steps per pixel
coverage_crop = coverage_mask[row_min:row_max, col_min:col_max]

im1 = ax1.imshow(coverage_crop, cmap='YlGnBu', vmin=0, vmax=len(ds.time),
                 extent=[lons_crop.min(), lons_crop.max(), lats_crop.min(), lats_crop.max()],
                 interpolation='nearest', aspect='auto')
ax1.set_title(f'Data Coverage Map\n(Number of valid observations per pixel)',
              fontsize=12, fontweight='bold')
ax1.set_xlabel('Longitude', fontsize=10)
ax1.set_ylabel('Latitude', fontsize=10)
ax1.grid(True, alpha=0.3)
cbar1 = plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
cbar1.set_label(f'Valid observations (max: {len(ds.time)})', fontsize=9)

# NDVI composite
im2 = ax2.imshow(composite_crop, cmap=ndvi_cmap, vmin=-0.2, vmax=1.0,
                 extent=[lons_crop.min(), lons_crop.max(), lats_crop.min(), lats_crop.max()],
                 interpolation='bilinear', aspect='auto')
ax2.set_title(f'Mean NDVI Composite\n(Average across all observations)',
              fontsize=12, fontweight='bold')
ax2.set_xlabel('Longitude', fontsize=10)
ax2.set_ylabel('Latitude', fontsize=10)
ax2.grid(True, alpha=0.3)
cbar2 = plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
cbar2.set_label('Mean NDVI', fontsize=9)

plt.suptitle('MODIS NDVI - Coverage and Composite Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()

output_file2 = Path('modis_ndvi_coverage_analysis.png')
plt.savefig(output_file2, dpi=200, bbox_inches='tight')
print(f"✓ Coverage analysis saved: {output_file2}")

ds.close()

print("\n" + "="*80)
print("✓ VISUALIZATION COMPLETE")
print("="*80)
print("\nGenerated files:")
print(f"  1. modis_ndvi_cropped_composite.png - Full composite view (cropped to data)")
print(f"  2. modis_ndvi_coverage_analysis.png - Coverage map + NDVI composite")
