"""
Plot the last 2 MODIS NDVI .tif files with detailed statistics
Memory-efficient version that won't crash
"""
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pathlib import Path
from datetime import datetime

# Find last 2 MODIS files
modis_dir = Path('/mnt/workwork/geoserver_data/ndvi_modis')
tif_files = sorted(modis_dir.glob('ndvi_modis_*.tif'), reverse=True)[:2]

print(f"Found {len(tif_files)} MODIS NDVI files to plot")

# Create figure with 1x2 grid (side by side)
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

fig.suptitle('Latest MODIS NDVI Composites (250m Resolution)', fontsize=16, fontweight='bold')

for idx, tif_path in enumerate(tif_files):
    print(f"\nProcessing {idx+1}/2: {tif_path.name}")

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
            median_val = np.nanmedian(data)
            std_val = np.nanstd(data)
            valid_pct = 100 * len(valid_data) / data.size
            data_min = np.nanmin(data)
            data_max = np.nanmax(data)
        else:
            vmin, vmax = -0.2, 1.0
            mean_val = median_val = std_val = 0
            valid_pct = 0
            data_min = data_max = 0

        # Plot
        ax = axes[idx]
        im = ax.imshow(data, cmap='RdYlGn', vmin=-0.2, vmax=1.0, interpolation='nearest')

        # Title with date and detailed stats
        title = f'{date_label}\n'
        title += f'μ={mean_val:.3f}, σ={std_val:.3f}\n'
        title += f'range=[{data_min:.3f}, {data_max:.3f}]\n'
        title += f'valid={valid_pct:.1f}%'
        ax.set_title(title, fontsize=11, pad=5)
        ax.axis('off')

        # Print detailed statistics
        print(f"  Date: {date_label}")
        print(f"  Range: {data_min:.4f} to {data_max:.4f}")
        print(f"  Mean: {mean_val:.4f}")
        print(f"  Median: {median_val:.4f}")
        print(f"  Std Dev: {std_val:.4f}")
        print(f"  Valid pixels: {len(valid_data):,} ({valid_pct:.1f}%)")

        # Value distribution
        if len(valid_data) > 0:
            bins = [(-1, 0), (0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
            print(f"  Distribution:")
            for low, high in bins:
                count = ((valid_data >= low) & (valid_data < high)).sum()
                pct = 100 * count / len(valid_data)
                print(f"    [{low:4.1f}, {high:4.1f}): {pct:5.1f}%")

# Add colorbar
cbar = fig.colorbar(im, ax=axes, orientation='horizontal',
                     fraction=0.05, pad=0.08, aspect=40)
cbar.set_label('NDVI', fontsize=12, weight='bold')

plt.tight_layout()

# Save
output_path = '/opt/geospatial_backend/modis_last_2_plots.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n✓ Saved visualization: {output_path}")

plt.close()
print("\n✓ Complete - no memory issues!")
