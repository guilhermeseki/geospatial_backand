"""
Plot the FIXED MODIS NDVI data to verify it's really working
Compare with an old broken file if available
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pathlib import Path

print("=" * 80)
print("VISUALIZING FIXED MODIS NDVI DATA")
print("=" * 80)

modis_dir = Path('/mnt/workwork/geoserver_data/ndvi_modis')

# The newly fixed file
fixed_file = modis_dir / 'ndvi_modis_20250610.tif'

# Try to find an old file to compare
old_files = sorted(modis_dir.glob('ndvi_modis_202506*.tif'))
old_file = None
for f in old_files:
    if f != fixed_file:
        old_file = f
        break

if old_file is None:
    # Use a different date
    old_files = sorted(modis_dir.glob('ndvi_modis_*.tif'))
    for f in old_files:
        if f != fixed_file:
            old_file = f
            break

print(f"\n✓ Fixed file: {fixed_file.name}")
if old_file:
    print(f"✓ Old file (for comparison): {old_file.name}")

# Create figure
if old_file:
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
else:
    fig, axes = plt.subplots(1, 1, figsize=(10, 8))
    axes = [axes]

fig.suptitle('MODIS NDVI - Before & After Fix', fontsize=16, fontweight='bold')

# Plot fixed file
print(f"\n📊 Processing fixed file: {fixed_file.name}")
with rasterio.open(fixed_file) as src:
    data = src.read(1)
    valid_data = data[~np.isnan(data)]

    print(f"  Shape: {data.shape}")
    print(f"  Valid pixels: {len(valid_data):,}/{data.size:,} ({100*len(valid_data)/data.size:.1f}%)")
    print(f"  Range: {np.nanmin(data):.4f} to {np.nanmax(data):.4f}")
    print(f"  Mean: {np.nanmean(data):.4f}")
    print(f"  Unique values: {len(np.unique(valid_data)):,}")

    # Check for the bug
    neg_03_count = np.sum(np.abs(data + 0.3) < 0.001)
    print(f"  -0.3 values (the bug): {neg_03_count}")

    ax = axes[0]
    im = ax.imshow(data, cmap='RdYlGn', vmin=-0.2, vmax=1.0, interpolation='nearest')

    title = f'FIXED: {fixed_file.stem}\n'
    title += f'μ={np.nanmean(data):.3f}, range=[{np.nanmin(data):.2f}, {np.nanmax(data):.2f}]\n'
    title += f'{len(np.unique(valid_data)):,} unique values'
    if neg_03_count == 0:
        title += ' ✅'
    else:
        title += f' ❌ ({neg_03_count} bad values)'
    ax.set_title(title, fontsize=12, pad=10)
    ax.axis('off')

# Plot old file if available
if old_file and len(axes) > 1:
    print(f"\n📊 Processing old file: {old_file.name}")
    with rasterio.open(old_file) as src:
        data = src.read(1)
        valid_data = data[~np.isnan(data)]

        print(f"  Shape: {data.shape}")
        print(f"  Valid pixels: {len(valid_data):,}/{data.size:,}")
        print(f"  Range: {np.nanmin(data):.4f} to {np.nanmax(data):.4f}")
        print(f"  Mean: {np.nanmean(data):.4f}")
        print(f"  Unique values: {len(np.unique(valid_data)):,}")

        # Check for the bug
        neg_03_count = np.sum(np.abs(data + 0.3) < 0.001)
        zero_count = np.sum(np.abs(data - 0.0) < 0.00001)
        print(f"  -0.3 values (the bug): {neg_03_count}")
        print(f"  0.0 values: {zero_count}")

        ax = axes[1]
        im = ax.imshow(data, cmap='RdYlGn', vmin=-0.2, vmax=1.0, interpolation='nearest')

        title = f'OLD (BROKEN): {old_file.stem}\n'
        title += f'μ={np.nanmean(data):.3f}, range=[{np.nanmin(data):.2f}, {np.nanmax(data):.2f}]\n'
        if len(np.unique(valid_data)) == 2:
            title += f'Only 2 unique values ❌'
        else:
            title += f'{len(np.unique(valid_data)):,} unique values'
        ax.set_title(title, fontsize=12, pad=10)
        ax.axis('off')

# Add colorbar
cbar = fig.colorbar(im, ax=axes, orientation='horizontal',
                     fraction=0.05, pad=0.08, aspect=40)
cbar.set_label('NDVI', fontsize=12, weight='bold')

plt.tight_layout()

# Save
output_path = '/opt/geospatial_backend/modis_fixed_comparison.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n✓ Saved visualization: {output_path}")

plt.close()

print("\n" + "=" * 80)
print("✓ VISUALIZATION COMPLETE")
print("=" * 80)
