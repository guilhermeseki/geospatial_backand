#!/usr/bin/env python3
"""
Clip all temp_mean GeoTIFF files to Brazil shapefile boundaries.
This will reduce file sizes and focus data on Brazil territory only.
"""

import subprocess
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("/mnt/workwork/geoserver_data/temp_mean")
SHAPEFILE = Path("/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp")
BACKUP_DIR = Path("/mnt/workwork/geoserver_data/temp_mean_backup")

def clip_geotiff(input_file: Path, shapefile: Path) -> bool:
    """
    Clip a GeoTIFF file to shapefile boundaries.

    Args:
        input_file: Path to input GeoTIFF
        shapefile: Path to clipping shapefile

    Returns:
        True if successful, False otherwise
    """
    temp_output = input_file.parent / f"{input_file.stem}_clipped_temp.tif"

    # Brazil bbox (matching temp_max and temp_min)
    BRAZIL_BBOX = {
        'west': -75.05,
        'south': -35.05,
        'east': -33.45,
        'north': 6.55
    }

    try:
        # Run gdalwarp with shapefile cutline AND fixed bbox
        result = subprocess.run([
            "gdalwarp",
            "-q",  # Quiet mode
            "-cutline", str(shapefile),
            "-te", str(BRAZIL_BBOX['west']), str(BRAZIL_BBOX['south']),
                   str(BRAZIL_BBOX['east']), str(BRAZIL_BBOX['north']),  # Fixed bbox
            "-dstnodata", "nan",
            "-co", "COMPRESS=LZW",
            "-co", "TILED=YES",
            "-co", "COPY_SRC_OVERVIEWS=YES",
            "-overwrite",
            str(input_file),
            str(temp_output)
        ], capture_output=True, text=True, timeout=60, check=True)

        # Replace original with clipped version
        temp_output.replace(input_file)
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"gdalwarp failed for {input_file.name}: {e.stderr[:200]}")
        if temp_output.exists():
            temp_output.unlink()
        return False

    except Exception as e:
        logger.error(f"Error clipping {input_file.name}: {e}")
        if temp_output.exists():
            temp_output.unlink()
        return False


def main():
    # Validate inputs
    if not DATA_DIR.exists():
        logger.error(f"Data directory not found: {DATA_DIR}")
        return

    if not SHAPEFILE.exists():
        logger.error(f"Shapefile not found: {SHAPEFILE}")
        return

    # Find all temp_mean GeoTIFF files (excluding temporary files)
    geotiff_files = sorted([f for f in DATA_DIR.glob("temp_mean_*.tif")
                           if "_clipped_temp" not in f.name])

    if not geotiff_files:
        logger.warning(f"No temp_mean_*.tif files found in {DATA_DIR}")
        return

    logger.info(f"Found {len(geotiff_files)} temp_mean GeoTIFF files to clip")
    logger.info(f"Using shapefile: {SHAPEFILE}")

    # Log operation info
    logger.info("")
    logger.info("="*70)
    logger.info(f"CLIPPING {len(geotiff_files)} TEMP_MEAN FILES TO BRAZIL BOUNDARIES")
    logger.info("="*70)
    logger.info(f"Source directory: {DATA_DIR}")
    logger.info(f"Shapefile: {SHAPEFILE}")
    logger.info(f"Files will be MODIFIED IN-PLACE (originals backed up)")
    logger.info("="*70)
    logger.info("")

    # Create backup directory
    BACKUP_DIR.mkdir(exist_ok=True)
    logger.info(f"Backup directory: {BACKUP_DIR}")

    # Process files
    start_time = datetime.now()
    success_count = 0
    fail_count = 0

    for i, geotiff_file in enumerate(geotiff_files, 1):
        logger.info(f"Processing {i}/{len(geotiff_files)}: {geotiff_file.name}")

        # Backup original file before clipping
        backup_file = BACKUP_DIR / geotiff_file.name
        if not backup_file.exists():
            import shutil
            shutil.copy2(geotiff_file, backup_file)
            logger.debug(f"  Backed up to: {backup_file}")

        # Clip file
        if clip_geotiff(geotiff_file, SHAPEFILE):
            success_count += 1

            # Get file size info
            original_size = backup_file.stat().st_size / (1024 * 1024)  # MB
            clipped_size = geotiff_file.stat().st_size / (1024 * 1024)  # MB
            reduction = ((original_size - clipped_size) / original_size) * 100

            logger.info(f"  ✓ Success - Size: {original_size:.2f}MB → {clipped_size:.2f}MB ({reduction:.1f}% reduction)")
        else:
            fail_count += 1
            logger.error(f"  ✗ Failed")

        # Progress update every 100 files
        if i % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = i / elapsed
            remaining = len(geotiff_files) - i
            eta_seconds = remaining / rate if rate > 0 else 0
            logger.info(f"  Progress: {i}/{len(geotiff_files)} ({i/len(geotiff_files)*100:.1f}%) - ETA: {eta_seconds/60:.1f} min")

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("")
    logger.info("="*70)
    logger.info("CLIPPING COMPLETE")
    logger.info("="*70)
    logger.info(f"Total files processed: {len(geotiff_files)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info(f"Total time: {elapsed/60:.2f} minutes")
    logger.info(f"Backup location: {BACKUP_DIR}")
    logger.info("="*70)


if __name__ == "__main__":
    main()
