#!/usr/bin/env python3
"""
Fix double conversion in wind_speed GeoTIFF files.
Divides all values by 3.6 to revert the second conversion.
"""
from pathlib import Path
import numpy as np
import rasterio
import logging
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fix_wind_file(tif_file: Path) -> bool:
    """Fix double conversion in a single wind speed GeoTIFF."""
    try:
        # Read the file
        with rasterio.open(tif_file) as src:
            data = src.read(1).astype(np.float32)
            profile = src.profile.copy()
            nodata = profile.get('nodata')

        # Revert second conversion (divide by 3.6)
        data_fixed = data / 3.6

        # Preserve nodata values
        if nodata is not None:
            mask = data == nodata
            data_fixed[mask] = nodata

        # Write back to the same file
        with rasterio.open(tif_file, 'w', **profile) as dst:
            dst.write(data_fixed.astype(rasterio.float32), 1)

        return True

    except Exception as e:
        logger.error(f"Failed to fix {tif_file.name}: {e}")
        return False


def main():
    data_dir = Path("/mnt/workwork/geoserver_data")
    wind_dir = data_dir / "wind_speed"

    if not wind_dir.exists():
        logger.error(f"Wind speed directory not found: {wind_dir}")
        return

    # Find all wind speed GeoTIFF files
    tif_files = sorted(wind_dir.glob("wind_speed_*.tif"))

    if not tif_files:
        logger.error(f"No wind speed GeoTIFF files found in {wind_dir}")
        return

    logger.info("=" * 80)
    logger.info("FIXING DOUBLE CONVERSION IN WIND SPEED GeoTIFF FILES")
    logger.info("=" * 80)
    logger.info(f"Directory: {wind_dir}")
    logger.info(f"Files to fix: {len(tif_files)}")
    logger.info(f"Fix: Divide by 3.6 to revert second conversion")
    logger.info("=" * 80)
    logger.info("\nStarting fix...")

    # Fix all files
    success_count = 0
    fail_count = 0

    for tif_file in tqdm(tif_files, desc="Fixing GeoTIFFs"):
        if fix_wind_file(tif_file):
            success_count += 1
        else:
            fail_count += 1

    logger.info("\n" + "=" * 80)
    logger.info("FIX COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Successfully fixed: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("=" * 80)

    # Verify with a sample file
    if tif_files:
        sample_file = tif_files[len(tif_files)//2]
        logger.info(f"\nVerifying fix with {sample_file.name}...")

        with rasterio.open(sample_file) as src:
            data = src.read(1)
            valid_data = data[~np.isnan(data)]
            if len(valid_data) > 0:
                logger.info(f"  Min: {valid_data.min():.2f} km/h")
                logger.info(f"  Max: {valid_data.max():.2f} km/h")
                logger.info(f"  Mean: {valid_data.mean():.2f} km/h")


if __name__ == "__main__":
    main()
