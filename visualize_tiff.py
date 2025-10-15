#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
from osgeo import gdal
import os

def visualize_tiff(tiff_path, date_str):
    """Visualize a TIFF file and display its statistics"""
    # Open the TIFF file
    dataset = gdal.Open(tiff_path)
    band = dataset.GetRasterBand(1)
    
    # Read data as numpy array
    data = band.ReadAsArray()
    
    # Get statistics
    min_val = np.nanmin(data)
    max_val = np.nanmax(data)
    mean_val = np.nanmean(data)
    
    # Create plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot the data
    im = ax1.imshow(data, cmap='viridis')
    ax1.set_title(f'Precipitation - {date_str}')
    plt.colorbar(im, ax=ax1, label='Precipitation (mm)')
    
    # Plot histogram
    ax2.hist(data[~np.isnan(data)].flatten(), bins=50, alpha=0.7)
    ax2.set_title(f'Value Distribution\nMin: {min_val:.2f}, Max: {max_val:.2f}, Mean: {mean_val:.2f}')
    ax2.set_xlabel('Precipitation (mm)')
    ax2.set_ylabel('Frequency')
    
    plt.tight_layout()
    plt.show()
    
    # Print detailed statistics
    print(f"\n=== {date_str} ===")
    print(f"Shape: {data.shape}")
    print(f"Min: {min_val:.4f}")
    print(f"Max: {max_val:.4f}")
    print(f"Mean: {mean_val:.4f}")
    print(f"Std: {np.nanstd(data):.4f}")
    print(f"NaN values: {np.sum(np.isnan(data))}")
    
    dataset = None
    return data

def compare_tiffs(tiff1_path, tiff2_path, date1, date2):
    """Compare two TIFF files"""
    # Load both datasets
    data1 = visualize_tiff(tiff1_path, date1)
    data2 = visualize_tiff(tiff2_path, date2)
    
    # Calculate differences
    diff = data1 - data2
    diff_abs = np.abs(diff)
    
    print(f"\n=== COMPARISON {date1} vs {date2} ===")
    print(f"Max difference: {np.nanmax(diff_abs):.6f}")
    print(f"Mean absolute difference: {np.nanmean(diff_abs):.6f}")
    print(f"Number of different pixels: {np.sum(diff_abs > 0.001)}")
    print(f"Percentage different: {np.mean(diff_abs > 0.001) * 100:.2f}%")
    
    # Plot difference
    plt.figure(figsize=(10, 8))
    im = plt.imshow(diff, cmap='RdBu_r', vmin=-1, vmax=1)
    plt.colorbar(im, label=f'Difference ({date1} - {date2})')
    plt.title(f'Difference Map: {date1} - {date2}')
    plt.show()

# Install required packages if needed
try:
    import matplotlib.pyplot as plt
    from osgeo import gdal
except ImportError:
    print("Installing required packages...")
    os.system("pip install matplotlib numpy gdal")
    import matplotlib.pyplot as plt
    from osgeo import gdal

# Example usage
tiff_dir = "/opt/geoserver/data_dir/chirps_final/"

# Visualize specific files
visualize_tiff(f"{tiff_dir}/chirps_final_latam_20250710.tif", "2025-07-10")
visualize_tiff(f"{tiff_dir}/chirps_final_latam_20250731.tif", "2025-07-31")

# Compare them
compare_tiffs(
    f"{tiff_dir}/chirps_final_latam_20250710.tif",
    f"{tiff_dir}/chirps_final_latam_20250731.tif",
    "2025-07-10",
    "2025-07-31"
)
