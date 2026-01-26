#!/usr/bin/env python3
"""
Clip all CHIRPS GeoTIFF files to Brazil bounding box.

This script processes all CHIRPS files in place, clipping them from the full
Latin America extent to Brazil's focused region.
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import subprocess
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/clip_chirps_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Brazil bounding box (W, S, E, N) for rasterio/GDAL
BRAZIL_BBOX = (-75.0, -35.0, -33.5, 6.5)

# Directories
CHIRPS_DIR = Path("/mnt/workwork/geoserver_data/chirps")
BACKUP_DIR = Path("/mnt/workwork/geoserver_data/chirps_backup")
TEMP_DIR = Path("/mnt/workwork/geoserver_data/chirps_temp")

def clip_single_file(input_file: Path) -> tuple[bool, str]:
    """
    Clip a single CHIRPS GeoTIFF file to Brazil bbox.

    Returns:
        tuple: (success, message)
    """
    try:
        temp_output = TEMP_DIR / input_file.name
        backup_file = BACKUP_DIR / input_file.name

        # Use gdalwarp to clip
        cmd = [
            "gdalwarp",
            "-te", str(BRAZIL_BBOX[0]), str(BRAZIL_BBOX[1]), str(BRAZIL_BBOX[2]), str(BRAZIL_BBOX[3]),
            "-te_srs", "EPSG:4326",
            "-co", "COMPRESS=LZW",
            "-co", "TILED=YES",
            "-co", "BIGTIFF=IF_SAFER",
            "-overwrite",
            str(input_file),
            str(temp_output)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return False, f"gdalwarp failed: {result.stderr}"

        # Verify output file was created and has data
        if not temp_output.exists() or temp_output.stat().st_size < 1000:
            return False, f"Output file is missing or too small"

        # Move original to backup
        shutil.move(str(input_file), str(backup_file))

        # Move clipped file to final location
        shutil.move(str(temp_output), str(input_file))

        return True, f"Successfully clipped {input_file.name}"

    except subprocess.TimeoutExpired:
        return False, f"Timeout processing {input_file.name}"
    except Exception as e:
        return False, f"Error processing {input_file.name}: {str(e)}"

def main():
    """Main processing function."""

    # Create temp directory
    TEMP_DIR.mkdir(exist_ok=True)

    # Get all CHIRPS files
    chirps_files = sorted(CHIRPS_DIR.glob("chirps_*.tif"))
    total_files = len(chirps_files)

    logger.info(f"Found {total_files} CHIRPS files to clip")
    logger.info(f"Target bbox (W, S, E, N): {BRAZIL_BBOX}")
    logger.info(f"Backup directory: {BACKUP_DIR}")
    logger.info(f"Temp directory: {TEMP_DIR}")

    # Process files in parallel
    successful = 0
    failed = 0

    # Use number of CPU cores for parallel processing
    max_workers = min(os.cpu_count() or 4, 8)
    logger.info(f"Using {max_workers} parallel workers")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        future_to_file = {
            executor.submit(clip_single_file, f): f
            for f in chirps_files
        }

        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_file), 1):
            file_path = future_to_file[future]
            try:
                success, message = future.result()
                if success:
                    successful += 1
                    if successful % 100 == 0:
                        logger.info(f"Progress: {successful}/{total_files} files clipped")
                else:
                    failed += 1
                    logger.error(message)
            except Exception as e:
                failed += 1
                logger.error(f"Exception processing {file_path.name}: {str(e)}")

            # Progress update every 200 files
            if i % 200 == 0:
                logger.info(f"Processed {i}/{total_files} files (✓ {successful}, ✗ {failed})")

    # Cleanup temp directory
    try:
        for temp_file in TEMP_DIR.glob("*.tif"):
            temp_file.unlink()
        TEMP_DIR.rmdir()
        logger.info(f"Cleaned up temp directory: {TEMP_DIR}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp directory: {e}")

    # Final summary
    logger.info("=" * 80)
    logger.info("CLIPPING COMPLETE")
    logger.info(f"Total files: {total_files}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Original files backed up to: {BACKUP_DIR}")
    logger.info("=" * 80)

    if failed > 0:
        logger.warning(f"⚠️  {failed} files failed to process - check logs above")
        return 1

    logger.info("✅ All CHIRPS files successfully clipped to Brazil bbox")
    return 0

if __name__ == "__main__":
    sys.exit(main())
