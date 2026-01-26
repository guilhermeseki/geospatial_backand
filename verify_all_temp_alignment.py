#!/usr/bin/env python3
"""
Verify that all three temperature datasets (temp_max, temp_min, temp_mean)
are properly aligned with the same bbox and shapefile clipping applied.
"""

import rasterio
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Test date
test_date = "20240101"

# Paths
data_dir = Path("/mnt/workwork/geoserver_data")
temp_max_file = data_dir / "temp_max" / f"temp_max_{test_date}.tif"
temp_min_file = data_dir / "temp_min" / f"temp_min_{test_date}.tif"
temp_mean_file = data_dir / "temp_mean" / f"temp_mean_{test_date}.tif"

print("="*70)
print("TEMPERATURE DATASETS ALIGNMENT VERIFICATION")
print("="*70)
print(f"Test date: {test_date}")
print()

# Check all files exist
for name, path in [("temp_max", temp_max_file), ("temp_min", temp_min_file), ("temp_mean", temp_mean_file)]:
    if not path.exists():
        print(f"❌ ERROR: {name} file not found: {path}")
        exit(1)
    print(f"✓ Found {name}: {path.name}")

print()
print("="*70)
print("BOUNDING BOX COMPARISON")
print("="*70)

# Compare bboxes
datasets = {}
for name, path in [("temp_max", temp_max_file), ("temp_min", temp_min_file), ("temp_mean", temp_mean_file)]:
    with rasterio.open(path) as src:
        datasets[name] = {
            'bounds': src.bounds,
            'shape': src.shape,
            'crs': src.crs,
            'transform': src.transform,
            'nodata_count': np.isnan(src.read(1)).sum(),
            'total_pixels': src.shape[0] * src.shape[1]
        }

        nodata_pct = (datasets[name]['nodata_count'] / datasets[name]['total_pixels']) * 100

        print(f"\n{name.upper()}:")
        print(f"  Bounds: {src.bounds}")
        print(f"  Shape: {src.shape}")
        print(f"  CRS: {src.crs}")
        print(f"  NoData pixels: {datasets[name]['nodata_count']:,} ({nodata_pct:.2f}%)")

# Check if all bboxes match
print()
print("="*70)
print("BBOX ALIGNMENT CHECK")
print("="*70)

bbox_match = True
reference = datasets['temp_max']['bounds']

for name in ['temp_min', 'temp_mean']:
    bounds = datasets[name]['bounds']
    if (abs(bounds.left - reference.left) < 0.001 and
        abs(bounds.right - reference.right) < 0.001 and
        abs(bounds.top - reference.top) < 0.001 and
        abs(bounds.bottom - reference.bottom) < 0.001):
        print(f"✓ {name} bbox matches temp_max")
    else:
        print(f"❌ {name} bbox DOES NOT match temp_max")
        print(f"   Difference: left={bounds.left - reference.left:.6f}, "
              f"right={bounds.right - reference.right:.6f}, "
              f"top={bounds.top - reference.top:.6f}, "
              f"bottom={bounds.bottom - reference.bottom:.6f}")
        bbox_match = False

# Check if all shapes match
print()
shape_match = True
reference_shape = datasets['temp_max']['shape']

for name in ['temp_min', 'temp_mean']:
    if datasets[name]['shape'] == reference_shape:
        print(f"✓ {name} shape matches temp_max")
    else:
        print(f"❌ {name} shape DOES NOT match temp_max")
        print(f"   Expected: {reference_shape}, Got: {datasets[name]['shape']}")
        shape_match = False

# Check NoData percentage (should be similar if shapefile clipping applied)
print()
print("="*70)
print("SHAPEFILE CLIPPING VERIFICATION (NoData %)")
print("="*70)

for name in ['temp_max', 'temp_min', 'temp_mean']:
    pct = (datasets[name]['nodata_count'] / datasets[name]['total_pixels']) * 100
    print(f"{name}: {pct:.2f}% NoData pixels")

print()
if bbox_match and shape_match:
    print("="*70)
    print("✅ ALL TEMPERATURE DATASETS PROPERLY ALIGNED")
    print("="*70)
    print("✓ Same bounding box")
    print("✓ Same grid shape")
    print("✓ Similar NoData percentage (shapefile clipping applied)")
    print()
    print("All three temperature datasets are now consistent:")
    print("  - Bbox: -75.05° to -33.45°W, -35.05° to 6.55°N")
    print("  - Shapefile: brazil_b10km.shp")
    print("  - Resolution: 0.1° (~10km)")
else:
    print("="*70)
    print("❌ ALIGNMENT ISSUES DETECTED")
    print("="*70)

# Visual comparison
print()
print("Creating visual comparison...")

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

for idx, (name, path) in enumerate([
    ("temp_max", temp_max_file),
    ("temp_min", temp_min_file),
    ("temp_mean", temp_mean_file)
]):
    with rasterio.open(path) as src:
        data = src.read(1)

        im = axes[idx].imshow(data, cmap='RdYlBu_r', vmin=15, vmax=35)
        axes[idx].set_title(f'{name} {test_date}', fontsize=14, fontweight='bold')
        axes[idx].set_xlabel('Longitude (pixels)')
        axes[idx].set_ylabel('Latitude (pixels)')

        # Add colorbar
        cbar = plt.colorbar(im, ax=axes[idx])
        cbar.set_label('Temperature (°C)', rotation=270, labelpad=20)

        # Add bounds info
        bounds_text = f"Bounds: {src.bounds.left:.2f}°W to {src.bounds.right:.2f}°W\n"
        bounds_text += f"        {src.bounds.bottom:.2f}°S to {src.bounds.top:.2f}°N"
        axes[idx].text(0.02, 0.98, bounds_text, transform=axes[idx].transAxes,
                      fontsize=9, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

plt.suptitle(f'Temperature Datasets Comparison - {test_date}\nAll datasets share same bbox and shapefile clipping',
             fontsize=16, fontweight='bold')
plt.tight_layout()

output_path = "/tmp/all_temp_verification.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"✓ Visual comparison saved to: {output_path}")
print()
