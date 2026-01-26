#!/usr/bin/env python3
"""
Build GLM FED historical NetCDF from existing GeoTIFF files.

This ensures consistent resolution and normalization between
GeoTIFF (WMS) and historical NetCDF (API queries).
"""

import xarray as xr
import rasterio
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_historical_from_geotiffs(
    geotiff_dir: Path,
    output_file: Path,
    year: int = 2025
):
    """
    Build yearly historical NetCDF from GeoTIFF files.

    Args:
        geotiff_dir: Directory containing glm_fed_YYYYMMDD.tif files
        output_file: Output NetCDF file path
        year: Year to process
    """
    # Find all GeoTIFFs for this year
    pattern = f"glm_fed_{year}*.tif"
    geotiff_files = sorted(list(geotiff_dir.glob(pattern)))

    if not geotiff_files:
        logger.warning(f"No GeoTIFF files found for year {year}")
        return None

    logger.info(f"Found {len(geotiff_files)} GeoTIFF files for {year}")

    datasets = []

    for geotiff_file in geotiff_files:
        try:
            # Extract date from filename
            date_str = geotiff_file.stem.split('_')[-1]  # glm_fed_20250415 -> 20250415
            file_date = pd.Timestamp(date_str)

            logger.info(f"Processing {geotiff_file.name} ({file_date.date()})")

            # Load GeoTIFF
            with rasterio.open(geotiff_file) as src:
                data = src.read(1)
                transform = src.transform

                # Get coordinates from bounds
                height, width = data.shape
                bounds = src.bounds

                # Create coordinate arrays
                lons = np.linspace(bounds.left, bounds.right, width)
                lats = np.linspace(bounds.top, bounds.bottom, height)

            # Create xarray Dataset
            ds = xr.Dataset(
                {
                    'fed_30min_max': (['latitude', 'longitude'], data)
                },
                coords={
                    'latitude': lats,
                    'longitude': lons,
                    'time': file_date
                },
                attrs={
                    'source': 'GLM FED GeoTIFF',
                    'unit': 'flashes/km²/30min',
                    'description': 'Maximum lightning flash density in any 30-minute window',
                    'resolution': '~3.23 km × 3.23 km',
                    'pixel_area': '10.41 km²',
                    'normalization': 'Values normalized by pixel area'
                }
            )

            datasets.append(ds)

        except Exception as e:
            logger.error(f"Failed to process {geotiff_file.name}: {e}")
            continue

    if not datasets:
        logger.error("No datasets created")
        return None

    # Combine all datasets along time dimension
    logger.info(f"Combining {len(datasets)} datasets...")
    combined = xr.concat(datasets, dim='time')
    combined = combined.sortby('time')

    logger.info(f"Combined dataset: {combined.dims}")
    logger.info(f"Time range: {combined.time.min().values} to {combined.time.max().values}")

    # Write to NetCDF
    logger.info(f"Writing to {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    combined.to_netcdf(
        output_file,
        mode='w',
        engine='netcdf4',
        encoding={
            'fed_30min_max': {
                'zlib': True,
                'complevel': 5,
                'dtype': 'float32',
                'chunksizes': (1, min(500, len(combined.latitude)), min(500, len(combined.longitude)))
            },
            'time': {
                'units': 'days since 1970-01-01',
                'dtype': 'int64'
            },
            'latitude': {'dtype': 'float32'},
            'longitude': {'dtype': 'float32'}
        }
    )

    combined.close()
    logger.info(f"✓ Created {output_file}")
    logger.info(f"  - {len(datasets)} days")
    logger.info(f"  - {len(combined.latitude)} latitudes × {len(combined.longitude)} longitudes")

    return output_file


if __name__ == "__main__":
    from app.config.settings import get_settings

    settings = get_settings()

    geotiff_dir = Path(settings.DATA_DIR) / "glm_fed"
    hist_dir = Path(settings.DATA_DIR) / "glm_fed_hist"
    output_file = hist_dir / "glm_fed_2025.nc"

    logger.info("="*80)
    logger.info("BUILDING GLM FED HISTORICAL FROM GEOTIFF FILES")
    logger.info("="*80)
    logger.info(f"GeoTIFF directory: {geotiff_dir}")
    logger.info(f"Output file: {output_file}")
    logger.info("")

    result = build_historical_from_geotiffs(geotiff_dir, output_file, year=2025)

    if result:
        logger.info("")
        logger.info("="*80)
        logger.info("✓ SUCCESS!")
        logger.info("="*80)
    else:
        logger.error("✗ FAILED")
