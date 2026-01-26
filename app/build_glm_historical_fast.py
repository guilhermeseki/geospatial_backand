"""
Fast historical NetCDF builder for GLM FED data.
Converts existing GeoTIFF files to historical NetCDF without re-downloading.
"""
from datetime import date
from pathlib import Path
import xarray as xr
import rioxarray
import pandas as pd
import numpy as np
from app.config.settings import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

settings = get_settings()

def build_historical_from_geotiffs():
    """Build historical NetCDF from existing GeoTIFF files."""

    geotiff_dir = Path(settings.DATA_DIR) / "glm_fed"
    hist_dir = Path(settings.DATA_DIR) / "glm_fed_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    # Get all GeoTIFF files
    geotiff_files = sorted(list(geotiff_dir.glob("glm_fed_*.tif")))
    logger.info(f"Found {len(geotiff_files)} GeoTIFF files")

    if not geotiff_files:
        logger.error("No GeoTIFF files found!")
        return

    # Group by year
    files_by_year = {}
    for tif_file in geotiff_files:
        try:
            date_str = tif_file.stem.split('_')[-1]
            file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
            year = file_date.year
            if year not in files_by_year:
                files_by_year[year] = []
            files_by_year[year].append((file_date, tif_file))
        except Exception as e:
            logger.warning(f"Could not parse date from {tif_file.name}: {e}")

    logger.info(f"Processing {len(files_by_year)} years: {sorted(files_by_year.keys())}")

    # Process each year
    for year in sorted(files_by_year.keys()):
        year_file = hist_dir / f"glm_fed_{year}.nc"
        year_files = sorted(files_by_year[year], key=lambda x: x[0])

        logger.info(f"\nYear {year}: {len(year_files)} files")

        # Check existing historical file
        existing_dates = set()
        if year_file.exists():
            try:
                ds = xr.open_dataset(year_file, chunks='auto')
                if 'time' in ds.coords:
                    existing_dates = set(pd.to_datetime(ds.coords['time'].values).date)
                ds.close()
                logger.info(f"  Existing historical has {len(existing_dates)} dates")
            except Exception as e:
                logger.warning(f"  Could not read existing file: {e}")

        # Filter to only missing dates
        files_to_process = [(d, f) for d, f in year_files if d not in existing_dates]

        if not files_to_process:
            logger.info(f"  ✓ All dates already in historical")
            continue

        logger.info(f"  Processing {len(files_to_process)} missing dates")

        # Read first GeoTIFF to get standard coordinates
        logger.info(f"    Reading first file to establish coordinate grid...")
        first_tif = files_to_process[0][1]
        first_da = rioxarray.open_rasterio(first_tif, chunks='auto').squeeze()
        standard_lat = first_da.y.values
        standard_lon = first_da.x.values
        logger.info(f"    Grid shape: {len(standard_lat)} x {len(standard_lon)}")

        # Read all GeoTIFFs
        datasets = []
        for file_date, tif_file in files_to_process:
            try:
                logger.info(f"    Reading {tif_file.name}...")

                # Read GeoTIFF
                da = rioxarray.open_rasterio(tif_file, chunks='auto').squeeze()

                # Create dataset with standard coordinates (use first file's grid)
                ds = xr.Dataset({
                    'fed_30min_max': (['time', 'latitude', 'longitude'],
                                      da.values.reshape(1, da.shape[0], da.shape[1]))
                })

                # Use standard coordinates from first file
                ds.coords['time'] = [pd.Timestamp(file_date)]
                ds.coords['latitude'] = standard_lat
                ds.coords['longitude'] = standard_lon

                # Add attributes
                ds.attrs['source'] = 'GOES GLM Flash Extent Density'
                ds.attrs['resolution'] = '8km'
                ds.attrs['units'] = 'flashes per 30 minutes per 8km grid cell'

                datasets.append(ds)

            except Exception as e:
                logger.error(f"    ✗ Failed to read {tif_file.name}: {e}")
                continue

        if not datasets:
            logger.warning(f"  No valid datasets for {year}")
            continue

        # Combine new datasets
        logger.info(f"  Combining {len(datasets)} datasets...")
        new_combined = xr.concat(datasets, dim='time', join='override', combine_attrs='override')
        new_combined = new_combined.sortby('time')

        # Merge with existing if needed
        if year_file.exists() and len(existing_dates) > 0:
            logger.info(f"  Merging with existing historical file...")
            try:
                # Remove old file first to avoid lock issues
                import os
                temp_old = hist_dir / f"glm_fed_{year}_old.nc"
                if temp_old.exists():
                    temp_old.unlink()
                os.rename(year_file, temp_old)

                existing_ds = xr.open_dataset(temp_old, chunks='auto')

                # Use the new grid as standard (from GeoTIFFs)
                # Reindex existing data to new grid if needed
                if not np.allclose(existing_ds.latitude.values, standard_lat, rtol=1e-6):
                    logger.info(f"  Reindexing existing data to new coordinate grid...")
                    existing_ds = existing_ds.interp(
                        latitude=standard_lat,
                        longitude=standard_lon,
                        method='nearest'
                    )

                combined = xr.concat([existing_ds, new_combined], dim='time', join='override', combine_attrs='override')
                combined = combined.sortby('time')
                existing_ds.close()

                # Remove old backup
                temp_old.unlink()
            except Exception as e:
                logger.error(f"  Failed to merge with existing: {e}")
                logger.info(f"  Continuing with new data only...")
                combined = new_combined
        else:
            combined = new_combined

        # Write to file
        logger.info(f"  Writing {year_file.name}...")
        encoding = {
            'fed_30min_max': {
                'zlib': True,
                'complevel': 5,
                'dtype': 'float32',
                'chunksizes': (1, 20, 20)
            }
        }

        try:
            # Write to temp file first
            temp_file = hist_dir / f"glm_fed_{year}_temp.nc"
            combined.to_netcdf(
                temp_file,
                mode='w',
                engine='netcdf4',
                encoding=encoding
            )

            # Move temp to final location
            import os
            if year_file.exists():
                year_file.unlink()
            os.rename(temp_file, year_file)

            logger.info(f"  ✓ Created {year_file.name} with {len(combined.time)} dates")
        except Exception as e:
            logger.error(f"  ✗ Failed to write: {e}")

        # Cleanup
        combined.close()
        for ds in datasets:
            ds.close()

    logger.info("\n" + "="*80)
    logger.info("✓ Historical NetCDF build complete!")
    logger.info("="*80)


if __name__ == "__main__":
    logger.info("="*80)
    logger.info("FAST GLM FED HISTORICAL BUILDER")
    logger.info("Converting existing GeoTIFFs to historical NetCDF")
    logger.info("="*80)
    build_historical_from_geotiffs()
