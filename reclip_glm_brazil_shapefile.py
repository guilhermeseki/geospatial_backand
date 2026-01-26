"""
Reprocess existing GLM FED GeoTIFF files to clip using Brazil shapefile instead of bbox
"""
from pathlib import Path
import xarray as xr
import geopandas as gpd
import rioxarray
from app.config.settings import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

def reclip_glm_with_shapefile():
    """Reprocess all GLM FED GeoTIFF files to use shapefile clipping"""

    glm_dir = Path(settings.DATA_DIR) / "glm_fed"
    geotiff_files = sorted(glm_dir.glob("glm_fed_*.tif"))

    logger.info(f"Found {len(geotiff_files)} GLM FED files to reprocess")

    # Load Brazil shapefile once
    brazil_shp = settings.BRAZIL_SHAPEFILE
    if not Path(brazil_shp).exists():
        logger.error(f"Brazil shapefile not found: {brazil_shp}")
        return

    logger.info(f"Loading Brazil shapefile: {brazil_shp}")
    brazil_gdf = gpd.read_file(brazil_shp)

    # Ensure shapefile is in WGS84
    if brazil_gdf.crs != "EPSG:4326":
        brazil_gdf = brazil_gdf.to_crs("EPSG:4326")

    logger.info(f"Brazil shapefile CRS: {brazil_gdf.crs}")

    # Create backup directory
    backup_dir = glm_dir / "backup_bbox"
    backup_dir.mkdir(exist_ok=True)

    failed = []

    for i, geotiff_file in enumerate(geotiff_files, 1):
        try:
            logger.info(f"[{i}/{len(geotiff_files)}] Processing {geotiff_file.name}")

            # Read original GeoTIFF
            fed_data = rioxarray.open_rasterio(geotiff_file, masked=True).squeeze()

            # Backup original file
            backup_file = backup_dir / geotiff_file.name
            if not backup_file.exists():
                import shutil
                shutil.copy2(geotiff_file, backup_file)
                logger.info(f"  Backed up to {backup_file.name}")

            # Clip using Brazil shapefile
            fed_clipped = fed_data.rio.clip(
                brazil_gdf.geometry.values,
                brazil_gdf.crs,
                drop=True,
                all_touched=False
            )

            logger.info(f"  Clipped: {fed_data.shape} → {fed_clipped.shape}")

            # Write back to same file with Cloud Optimized GeoTIFF format
            fed_clipped.rio.to_raster(
                geotiff_file,
                driver="COG",
                compress="LZW",
                dtype="float32",
                tiled=True,
                blockxsize=256,
                blockysize=256
            )

            logger.info(f"  ✓ Saved {geotiff_file.name}")

            # Clean up
            fed_data.close()

            if (i % 10) == 0:
                logger.info(f"Progress: {i}/{len(geotiff_files)} files completed")

        except Exception as e:
            logger.error(f"  ✗ Failed to process {geotiff_file.name}: {e}")
            failed.append(geotiff_file.name)
            continue

    logger.info("=" * 80)
    logger.info(f"✓ Reprocessing complete!")
    logger.info(f"  Total files: {len(geotiff_files)}")
    logger.info(f"  Successful: {len(geotiff_files) - len(failed)}")
    logger.info(f"  Failed: {len(failed)}")
    if failed:
        logger.info(f"  Failed files: {failed}")
    logger.info(f"  Backups saved to: {backup_dir}")

if __name__ == "__main__":
    reclip_glm_with_shapefile()
