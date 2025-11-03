#!/usr/bin/env python3
"""
Visualize MODIS NDVI data to verify quality
"""
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from app.config.settings import get_settings
import pandas as pd

# Custom NDVI colormap (brown to yellow to green)
colors = ['#8B4513', '#CD853F', '#F4A460', '#FFFACD', '#FFFF00', '#ADFF2F', '#32CD32', '#228B22', '#006400']
n_bins = 100
ndvi_cmap = LinearSegmentedColormap.from_list('ndvi', colors, N=n_bins)

settings = get_settings()
data_dir = Path(settings.DATA_DIR)

print("="*80)
print("MODIS NDVI VISUALIZATION")
print("="*80)

# Try to read the raw NetCDF file first
raw_file = data_dir / "raw" / "modis" / "modis_ndvi_20240901_20240930.nc"
yearly_file = data_dir / "ndvi_modis_hist" / "ndvi_modis_2024.nc"

if raw_file.exists():
    print(f"\nReading raw NetCDF: {raw_file}")
    ds = xr.open_dataset(raw_file)
    data_source = "Raw composites"
elif yearly_file.exists():
    print(f"\nReading yearly NetCDF: {yearly_file}")
    ds = xr.open_dataset(yearly_file)
    data_source = "Yearly historical"
else:
    print("\n✗ No NetCDF file found!")
    exit(1)

print(f"\nDataset info:")
print(f"  Source: {data_source}")
print(f"  Time steps: {len(ds.time)}")
print(f"  Spatial extent: {len(ds.latitude)} x {len(ds.longitude)} pixels")
print(f"  Date range: {pd.to_datetime(ds.time.values[0]).strftime('%Y-%m-%d')} to {pd.to_datetime(ds.time.values[-1]).strftime('%Y-%m-%d')}")

# Get NDVI data
ndvi = ds['ndvi'].values

# Print statistics for each time step
print(f"\nNDVI statistics per time step:")
print(f"  {'Date':<12} {'Valid %':<10} {'Min':<8} {'Mean':<8} {'Max':<8}")
print(f"  {'-'*12} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")
for i, t in enumerate(ds.time.values):
    date_str = pd.to_datetime(t).strftime('%Y-%m-%d')
    data_i = ndvi[i]
    valid_pct = 100 * np.sum(~np.isnan(data_i)) / data_i.size
    if valid_pct > 0:
        min_val = np.nanmin(data_i)
        mean_val = np.nanmean(data_i)
        max_val = np.nanmax(data_i)
        print(f"  {date_str:<12} {valid_pct:>6.1f}%    {min_val:>6.3f}  {mean_val:>6.3f}  {max_val:>6.3f}")
    else:
        print(f"  {date_str:<12} {valid_pct:>6.1f}%    {'N/A':<6}  {'N/A':<6}  {'N/A':<6}")

# Create plots - show up to 6 time steps
n_plots = min(len(ds.time), 6)
cols = 3
rows = (n_plots + cols - 1) // cols

fig, axes = plt.subplots(rows, cols, figsize=(15, 5*rows))
if rows == 1:
    axes = axes.reshape(1, -1)

print(f"\nGenerating plots for {n_plots} time steps...")

for i in range(n_plots):
    row = i // cols
    col = i % cols
    ax = axes[row, col]

    date_str = pd.to_datetime(ds.time.values[i]).strftime('%Y-%m-%d')
    data_i = ndvi[i]

    # Plot NDVI
    im = ax.imshow(data_i, cmap=ndvi_cmap, vmin=-0.2, vmax=1.0, interpolation='nearest')
    ax.set_title(f'{date_str}\n{np.sum(~np.isnan(data_i))/data_i.size*100:.1f}% valid pixels', fontsize=10)
    ax.axis('off')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('NDVI', fontsize=8)
    cbar.ax.tick_params(labelsize=7)

# Hide extra subplots
for i in range(n_plots, rows * cols):
    row = i // cols
    col = i % cols
    axes[row, col].axis('off')

plt.suptitle(f'MODIS NDVI - {data_source}\nSeptember 2024', fontsize=14, fontweight='bold')
plt.tight_layout()

# Save plot
output_file = Path('modis_ndvi_visualization.png')
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\n✓ Plot saved: {output_file}")
print(f"  Resolution: 150 DPI")
print(f"  Size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")

# Create a single composite plot showing the most recent data
if len(ds.time) > 0:
    fig2, ax = plt.subplots(1, 1, figsize=(12, 10))

    # Get most recent time step with most valid data
    valid_counts = [np.sum(~np.isnan(ndvi[i])) for i in range(len(ds.time))]
    best_idx = np.argmax(valid_counts)

    date_str = pd.to_datetime(ds.time.values[best_idx]).strftime('%Y-%m-%d')
    data_best = ndvi[best_idx]

    im = ax.imshow(data_best, cmap=ndvi_cmap, vmin=-0.2, vmax=1.0, interpolation='bilinear')

    valid_pct = 100 * np.sum(~np.isnan(data_best)) / data_best.size
    ax.set_title(f'MODIS NDVI - {date_str}\n{valid_pct:.1f}% valid pixels | Mean NDVI: {np.nanmean(data_best):.3f}',
                 fontsize=14, fontweight='bold')
    ax.axis('off')

    # Add colorbar with labels
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('NDVI Value', fontsize=11)
    cbar.ax.tick_params(labelsize=10)

    # Add text annotations
    textstr = '\n'.join([
        'NDVI Interpretation:',
        '< 0.1: Water, bare soil',
        '0.1-0.2: Sparse vegetation',
        '0.2-0.4: Moderate vegetation',
        '0.4-0.6: Dense vegetation',
        '> 0.6: Very dense vegetation'
    ])
    props = dict(boxstyle='round', facecolor='white', alpha=0.8)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=props)

    plt.tight_layout()

    output_file2 = Path('modis_ndvi_best_composite.png')
    plt.savefig(output_file2, dpi=200, bbox_inches='tight')
    print(f"\n✓ Best composite saved: {output_file2}")
    print(f"  Date: {date_str}")
    print(f"  Valid pixels: {valid_pct:.1f}%")
    print(f"  NDVI range: {np.nanmin(data_best):.3f} to {np.nanmax(data_best):.3f}")

ds.close()

print("\n" + "="*80)
print("✓ VISUALIZATION COMPLETE")
print("="*80)
print("\nFiles created:")
print(f"  1. modis_ndvi_visualization.png - Grid of multiple time steps")
print(f"  2. modis_ndvi_best_composite.png - Highest quality composite")
print("\nYou can view these images to verify MODIS data quality.")
