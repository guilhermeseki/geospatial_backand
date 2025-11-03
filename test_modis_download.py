"""
Test script to download and visualize MODIS NDVI data to check quality
"""
from datetime import date, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import xarray as xr
import rasterio
from rasterio.plot import show

from app.workflows.data_processing.ndvi_flow import download_modis_batch
from app.config.settings import get_settings

def test_modis_download():
    """Download a recent MODIS composite and visualize it"""
    settings = get_settings()

    # Download recent data (last 30 days)
    end_date = date.today() - timedelta(days=5)  # Account for processing lag
    start_date = end_date - timedelta(days=30)

    print(f"\n{'='*80}")
    print(f"TESTING MODIS NDVI DOWNLOAD")
    print(f"{'='*80}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Area: Latin America bbox")
    print(f"{'='*80}\n")

    try:
        # Download MODIS data
        netcdf_path = download_modis_batch(
            start_date=start_date,
            end_date=end_date,
            area=settings.latam_bbox_cds
        )

        print(f"\n✓ Downloaded: {netcdf_path}")

        # Open and inspect the NetCDF
        ds = xr.open_dataset(netcdf_path)
        print(f"\n📊 Dataset Info:")
        print(f"  Variables: {list(ds.data_vars)}")
        print(f"  Dimensions: {dict(ds.dims)}")
        print(f"  Coordinates: {list(ds.coords)}")

        ndvi = ds['ndvi']
        print(f"\n📊 NDVI Info:")
        print(f"  Shape: {ndvi.shape}")
        print(f"  Data type: {ndvi.dtype}")
        print(f"  Time range: {ndvi.time.min().values} to {ndvi.time.max().values}")
        print(f"  Lat range: {ndvi.latitude.min().values:.2f} to {ndvi.latitude.max().values:.2f}")
        print(f"  Lon range: {ndvi.longitude.min().values:.2f} to {ndvi.longitude.max().values:.2f}")

        # Compute statistics for first time step
        first_time = ndvi.isel(time=0)
        stats = {
            'min': float(first_time.min().values),
            'max': float(first_time.max().values),
            'mean': float(first_time.mean().values),
            'std': float(first_time.std().values),
            'valid_pixels': int((~np.isnan(first_time.values)).sum()),
            'total_pixels': int(first_time.size),
        }
        stats['valid_percent'] = 100 * stats['valid_pixels'] / stats['total_pixels']

        print(f"\n📊 First Composite Statistics:")
        print(f"  Min: {stats['min']:.4f}")
        print(f"  Max: {stats['max']:.4f}")
        print(f"  Mean: {stats['mean']:.4f}")
        print(f"  Std: {stats['std']:.4f}")
        print(f"  Valid pixels: {stats['valid_pixels']:,} ({stats['valid_percent']:.1f}%)")

        # Create visualization
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'MODIS NDVI Quality Check\n{start_date} to {end_date}', fontsize=16)

        # Plot 1: First composite
        ax = axes[0, 0]
        im1 = ax.imshow(first_time.values, cmap='RdYlGn', vmin=-0.2, vmax=1.0)
        ax.set_title(f'First Composite: {first_time.time.dt.strftime("%Y-%m-%d").values}')
        ax.set_xlabel('Longitude Index')
        ax.set_ylabel('Latitude Index')
        plt.colorbar(im1, ax=ax, label='NDVI')

        # Plot 2: Histogram
        ax = axes[0, 1]
        valid_data = first_time.values[~np.isnan(first_time.values)]
        ax.hist(valid_data, bins=50, edgecolor='black', alpha=0.7)
        ax.set_title('NDVI Distribution (First Composite)')
        ax.set_xlabel('NDVI Value')
        ax.set_ylabel('Frequency')
        ax.axvline(stats['mean'], color='red', linestyle='--', label=f'Mean: {stats["mean"]:.3f}')
        ax.legend()

        # Plot 3: Last composite (if available)
        if len(ndvi.time) > 1:
            last_time = ndvi.isel(time=-1)
            ax = axes[1, 0]
            im3 = ax.imshow(last_time.values, cmap='RdYlGn', vmin=-0.2, vmax=1.0)
            ax.set_title(f'Last Composite: {last_time.time.dt.strftime("%Y-%m-%d").values}')
            ax.set_xlabel('Longitude Index')
            ax.set_ylabel('Latitude Index')
            plt.colorbar(im3, ax=ax, label='NDVI')
        else:
            axes[1, 0].text(0.5, 0.5, 'Only one composite available',
                          ha='center', va='center', transform=axes[1, 0].transAxes)
            axes[1, 0].axis('off')

        # Plot 4: Valid pixel coverage
        ax = axes[1, 1]
        valid_mask = ~np.isnan(first_time.values)
        ax.imshow(valid_mask, cmap='binary')
        ax.set_title(f'Valid Pixel Coverage\n{stats["valid_percent"]:.1f}% valid')
        ax.set_xlabel('Longitude Index')
        ax.set_ylabel('Latitude Index')

        plt.tight_layout()

        # Save figure
        output_dir = Path('/opt/geospatial_backend')
        fig_path = output_dir / 'modis_ndvi_quality_check.png'
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        print(f"\n✓ Visualization saved: {fig_path}")

        plt.close()

        # Check for issues
        print(f"\n🔍 Quality Check:")
        issues = []

        if stats['valid_percent'] < 50:
            issues.append(f"⚠ Low valid pixel coverage: {stats['valid_percent']:.1f}%")

        if stats['mean'] < 0:
            issues.append(f"⚠ Mean NDVI is negative: {stats['mean']:.4f}")

        if stats['max'] > 1.0 or stats['min'] < -1.0:
            issues.append(f"⚠ NDVI values out of range [-1, 1]: min={stats['min']:.4f}, max={stats['max']:.4f}")

        if stats['std'] > 0.5:
            issues.append(f"⚠ High standard deviation: {stats['std']:.4f}")

        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("  ✓ No obvious quality issues detected")

        ds.close()

        # Now check a GeoTIFF file
        print(f"\n{'='*80}")
        print("CHECKING EXISTING GEOTIFF FILE")
        print(f"{'='*80}")

        geotiff_dir = Path(settings.DATA_DIR) / "ndvi_modis"
        tif_files = sorted(geotiff_dir.glob("ndvi_modis_*.tif"))

        if tif_files:
            # Check a recent file
            tif_path = tif_files[-1]
            print(f"\nChecking: {tif_path.name}")

            with rasterio.open(tif_path) as src:
                print(f"\n📊 GeoTIFF Info:")
                print(f"  Size: {src.width} x {src.height}")
                print(f"  CRS: {src.crs}")
                print(f"  Bounds: {src.bounds}")
                print(f"  Data type: {src.dtypes[0]}")
                print(f"  NoData: {src.nodata}")

                # Read data
                data = src.read(1)

                # Calculate stats
                valid_mask = data != src.nodata if src.nodata is not None else ~np.isnan(data)
                valid_data = data[valid_mask]

                if len(valid_data) > 0:
                    tif_stats = {
                        'min': float(np.nanmin(valid_data)),
                        'max': float(np.nanmax(valid_data)),
                        'mean': float(np.nanmean(valid_data)),
                        'std': float(np.nanstd(valid_data)),
                        'valid_pixels': int(valid_mask.sum()),
                        'total_pixels': int(data.size),
                    }
                    tif_stats['valid_percent'] = 100 * tif_stats['valid_pixels'] / tif_stats['total_pixels']

                    print(f"\n📊 GeoTIFF Statistics:")
                    print(f"  Min: {tif_stats['min']:.4f}")
                    print(f"  Max: {tif_stats['max']:.4f}")
                    print(f"  Mean: {tif_stats['mean']:.4f}")
                    print(f"  Std: {tif_stats['std']:.4f}")
                    print(f"  Valid pixels: {tif_stats['valid_pixels']:,} ({tif_stats['valid_percent']:.1f}%)")

                    # Create visualization
                    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
                    fig.suptitle(f'GeoTIFF Quality Check: {tif_path.name}', fontsize=14)

                    # Plot 1: Data
                    ax = axes[0]
                    masked_data = np.ma.masked_where(~valid_mask, data)
                    im = ax.imshow(masked_data, cmap='RdYlGn', vmin=-0.2, vmax=1.0)
                    ax.set_title('NDVI Values')
                    plt.colorbar(im, ax=ax, label='NDVI')

                    # Plot 2: Histogram
                    ax = axes[1]
                    ax.hist(valid_data, bins=50, edgecolor='black', alpha=0.7)
                    ax.set_title('NDVI Distribution')
                    ax.set_xlabel('NDVI Value')
                    ax.set_ylabel('Frequency')
                    ax.axvline(tif_stats['mean'], color='red', linestyle='--',
                             label=f'Mean: {tif_stats["mean"]:.3f}')
                    ax.legend()

                    plt.tight_layout()

                    fig_path = output_dir / 'modis_geotiff_quality_check.png'
                    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                    print(f"\n✓ GeoTIFF visualization saved: {fig_path}")
                    plt.close()
                else:
                    print("\n⚠ No valid data in GeoTIFF!")
        else:
            print("\n⚠ No GeoTIFF files found")

        print(f"\n{'='*80}")
        print("TEST COMPLETE")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_modis_download()
