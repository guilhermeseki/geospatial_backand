#!/usr/bin/env python3
"""
Fix NoData values in wind gust GeoTIFF files.
Replace -9999 with NaN in all existing files.
"""
import rasterio
import numpy as np
from pathlib import Path
from tqdm import tqdm

def fix_nodata(tif_path: Path) -> bool:
    """Replace -9999 with NaN in a GeoTIFF file."""
    try:
        with rasterio.open(tif_path) as src:
            data = src.read(1)
            profile = src.profile.copy()

        # Check if has -9999 values
        has_nodata = (data == -9999).any()

        if not has_nodata:
            return False  # Already fixed

        # Replace -9999 with NaN
        data[data == -9999] = np.nan

        # Update profile to use NaN as nodata
        profile.update(nodata=np.nan)

        # Write back
        with rasterio.open(tif_path, 'w', **profile) as dst:
            dst.write(data, 1)

        return True

    except Exception as e:
        print(f"Error fixing {tif_path.name}: {e}")
        return False

def main():
    """Fix all wind gust GeoTIFF files."""
    wind_dir = Path("/mnt/workwork/geoserver_data/wind_speed")
    tif_files = sorted(wind_dir.glob("wind_speed_*.tif"))

    print(f"Found {len(tif_files)} wind gust files")
    print("Replacing -9999 with NaN...")

    fixed = 0
    skipped = 0

    for tif_path in tqdm(tif_files, desc="Fixing NoData"):
        if fix_nodata(tif_path):
            fixed += 1
        else:
            skipped += 1

    print(f"\n✓ Fixed {fixed} files")
    print(f"  Skipped {skipped} files (already OK)")
    print(f"  Total: {len(tif_files)} files")

    # Verify one file
    print("\nVerifying first file...")
    with rasterio.open(tif_files[0]) as src:
        data = src.read(1)
        print(f"  NoData value: {src.nodata}")
        print(f"  Has -9999: {(data == -9999).any()}")
        print(f"  Has NaN: {np.isnan(data).any()}")
        valid = data[~np.isnan(data)]
        print(f"  Valid pixels: {len(valid):,}")
        print(f"  Min: {valid.min():.2f} km/h")
        print(f"  Max: {valid.max():.2f} km/h")

if __name__ == "__main__":
    main()
