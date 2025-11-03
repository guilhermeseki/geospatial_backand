"""
Plot the last 20 MODIS NDVI .tif files
"""
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import rasterio
from pathlib import Path
from datetime import datetime

# Find last 20 MODIS files
modis_dir = Path('/mnt/workwork/geoserver_data/ndvi_modis')
tif_files = sorted(modis_dir.glob('ndvi_modis_*.tif'), reverse=True)[:20]

print(f"Found {len(tif_files)} MODIS NDVI files to plot")

# Create figure with 4x5 grid
fig, axes = plt.subplots(4, 5, figsize=(20, 16))
axes = axes.flatten()

fig.suptitle('Last 20 MODIS NDVI Composites (250m Resolution)', fontsize=16, fontweight='bold')

for idx, tif_path in enumerate(tif_files):
    print(f"Processing {idx+1}/20: {tif_path.name}")

    # Extract date from filename
    date_str = tif_path.stem.split('_')[-1]
    date_obj = datetime.strptime(date_str, '%Y%m%d')
    date_label = date_obj.strftime('%Y-%m-%d')

    # Read the TIF file
    with rasterio.open(tif_path) as src:
        data = src.read(1)

        # Handle nodata
        if src.nodata is not None:
            data = np.where(data == src.nodata, np.nan, data)

        # Calculate statistics
        valid_data = data[~np.isnan(data)]
        if len(valid_data) > 0:
            vmin, vmax = np.nanpercentile(data, [2, 98])
            mean_val = np.nanmean(data)
            valid_pct = 100 * len(valid_data) / data.size
        else:
            vmin, vmax = -0.2, 1.0
            mean_val = 0
            valid_pct = 0

        # Plot
        ax = axes[idx]
        im = ax.imshow(data, cmap='RdYlGn', vmin=-0.2, vmax=1.0, interpolation='nearest')

        # Title with date and stats
        ax.set_title(f'{date_label}\nμ={mean_val:.3f}, valid={valid_pct:.1f}%',
                    fontsize=9, pad=3)
        ax.axis('off')

# Add colorbar
cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
cbar = fig.colorbar(im, cax=cbar_ax, label='NDVI')
cbar.set_label('NDVI', fontsize=12, weight='bold')

# Add overall statistics box
stats_text = "Data Quality Issues Detected:\n"
stats_text += "• Most values near 0 (should be 0.4-0.9 for vegetation)\n"
stats_text += "• Likely scale factor not applied correctly\n"
stats_text += "• MODIS raw values need multiplication by 0.0001"

fig.text(0.02, 0.02, stats_text, fontsize=10,
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
         verticalalignment='bottom', family='monospace')

plt.tight_layout(rect=[0, 0.05, 0.91, 0.96])

# Save
output_path = '/opt/geospatial_backend/modis_last_20_plots.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n✓ Saved visualization: {output_path}")

# Also create a detailed analysis
print(f"\n{'='*80}")
print("DETAILED STATISTICS")
print(f"{'='*80}")

for idx, tif_path in enumerate(tif_files[:5]):  # Show first 5 in detail
    date_str = tif_path.stem.split('_')[-1]
    date_obj = datetime.strptime(date_str, '%Y%m%d')

    with rasterio.open(tif_path) as src:
        data = src.read(1)
        if src.nodata is not None:
            data = np.where(data == src.nodata, np.nan, data)

        valid_data = data[~np.isnan(data)]

        print(f"\n{date_obj.strftime('%Y-%m-%d')}:")
        print(f"  Range: {np.nanmin(data):.4f} to {np.nanmax(data):.4f}")
        print(f"  Mean: {np.nanmean(data):.4f}")
        print(f"  Median: {np.nanmedian(data):.4f}")
        print(f"  Std: {np.nanstd(data):.4f}")
        print(f"  Valid pixels: {len(valid_data):,} ({100*len(valid_data)/data.size:.1f}%)")

        # Value distribution
        bins = [(-1, 0), (0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        print(f"  Distribution:")
        for low, high in bins:
            count = ((valid_data >= low) & (valid_data < high)).sum()
            pct = 100 * count / len(valid_data) if len(valid_data) > 0 else 0
            print(f"    [{low:4.1f}, {high:4.1f}): {pct:5.1f}%")

print(f"\n{'='*80}\n")
plt.close()
