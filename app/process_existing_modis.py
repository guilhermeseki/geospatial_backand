#!/usr/bin/env python3
"""
Process Existing MODIS Raw Files to GeoTIFFs

This script processes already-downloaded MODIS raw NetCDF files to create
GeoTIFFs without re-downloading. Useful when downloads succeeded but
GeoTIFF creation failed.
"""
from pathlib import Path
from app.config.settings import settings
from app.workflows.data_processing.ndvi_flow import process_ndvi_to_geotiff
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    raw_dir = Path(settings.DATA_DIR) / "raw" / "modis"

    if not raw_dir.exists():
        logger.error(f"Raw MODIS directory not found: {raw_dir}")
        exit(1)

    # Find all raw NetCDF files
    raw_files = sorted(raw_dir.glob("modis_ndvi_*.nc"))

    if not raw_files:
        logger.error(f"No raw MODIS files found in {raw_dir}")
        exit(1)

    logger.info("="*80)
    logger.info("PROCESS EXISTING MODIS RAW FILES")
    logger.info("="*80)
    logger.info(f"Found {len(raw_files)} raw files to process")
    logger.info(f"Source: {raw_dir}")
    logger.info(f"Output: {Path(settings.DATA_DIR) / 'ndvi_modis'}")
    logger.info("="*80)
    print()

    success_count = 0
    fail_count = 0
    total_geotiffs = 0

    for i, raw_file in enumerate(raw_files, 1):
        logger.info(f"[{i}/{len(raw_files)}] Processing: {raw_file.name}")

        try:
            # Process to GeoTIFFs (no date filtering - process all composites)
            processed_paths = process_ndvi_to_geotiff(
                netcdf_path=raw_file,
                source='modis',
                bbox=settings.latam_bbox_raster,
                dates_to_process=None  # Process all composites in the file
            )

            geotiff_count = len(processed_paths)
            total_geotiffs += geotiff_count
            success_count += 1

            logger.info(f"  ✓ Created {geotiff_count} GeoTIFF files")

        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            fail_count += 1
            import traceback
            traceback.print_exc()
            continue

    print()
    logger.info("="*80)
    logger.info("PROCESSING SUMMARY")
    logger.info("="*80)
    logger.info(f"Raw files processed: {success_count}/{len(raw_files)}")
    logger.info(f"Failed: {fail_count}")
    logger.info(f"Total GeoTIFFs created: {total_geotiffs}")
    logger.info("="*80)

    if total_geotiffs > 0:
        logger.info(f"\n✓ Success! Check {Path(settings.DATA_DIR) / 'ndvi_modis'} for GeoTIFF files")
    else:
        logger.error(f"\n✗ No GeoTIFFs created. Check errors above.")
