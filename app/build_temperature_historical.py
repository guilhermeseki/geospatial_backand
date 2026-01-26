#!/usr/bin/env python3
"""
Build temperature historical NetCDF files from temperature GeoTIFF mosaics.

This creates yearly historical NetCDF files (temp_max_2015.nc, temp_min_2015.nc, etc.)
from the temperature GeoTIFF files for fast time-series API queries.
"""
from pathlib import Path
import xarray as xr
import rioxarray  # noqa
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_temperature_historical(
    data_dir: str = "/mnt/workwork/geoserver_data",
    sources: list = None
):
    """
    Build yearly historical NetCDF files from temperature GeoTIFF mosaics.

    Args:
        data_dir: Base data directory containing temperature folders
        sources: List of sources to process (defaults to all temperature sources from central config)
    """
    if sources is None:
        from app.config.data_sources import TEMPERATURE_SOURCES
        sources = TEMPERATURE_SOURCES

    data_dir = Path(data_dir)

    logger.info("=" * 80)
    logger.info("BUILDING TEMPERATURE HISTORICAL NETCDF FILES")
    logger.info("=" * 80)
    logger.info(f"Base directory: {data_dir}")
    logger.info(f"Sources to process: {sources}")

    for source in sources:
        logger.info("\n" + "=" * 80)
        logger.info(f"Processing {source.upper()}")
        logger.info("=" * 80)

        # Input: temperature GeoTIFFs
        source_dir = data_dir / source

        # Output: temperature_hist NetCDF files
        hist_dir = data_dir / f"{source}_hist"
        hist_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Input directory: {source_dir}")
        logger.info(f"Output directory: {hist_dir}")

        # Find all temperature GeoTIFF files
        tif_files = sorted(source_dir.glob(f"{source}_*.tif"))

        if not tif_files:
            logger.error(f"No {source} GeoTIFF files found in {source_dir}")
            continue

        logger.info(f"Found {len(tif_files)} {source} GeoTIFF files")

        # Group files by year
        files_by_year = defaultdict(list)

        for tif_file in tif_files:
            try:
                # Extract date from filename: temp_max_YYYYMMDD.tif
                date_str = tif_file.stem.split('_')[-1]
                file_date = pd.to_datetime(date_str, format='%Y%m%d')
                year = file_date.year
                files_by_year[year].append((file_date, tif_file))
            except Exception as e:
                logger.warning(f"Could not parse date from {tif_file.name}: {e}")
                continue

        logger.info(f"Data spans {len(files_by_year)} years: {sorted(files_by_year.keys())}")

        # Process each year
        for year in sorted(files_by_year.keys()):
            year_files = sorted(files_by_year[year])
            output_file = hist_dir / f"{source}_{year}.nc"

            # Skip if already exists
            if output_file.exists():
                logger.info(f"✓ {year}: Already exists ({output_file.name}), skipping")
                continue

            logger.info(f"\nProcessing year {year} ({len(year_files)} files)...")

            try:
                # Load all GeoTIFFs for this year
                datasets = []
                dates = []

                for file_date, tif_file in year_files:
                    try:
                        # Read GeoTIFF with rioxarray
                        da = xr.open_dataarray(tif_file, engine='rasterio')

                        # Extract data array (first band)
                        if len(da.shape) == 3:
                            da = da.isel(band=0)

                        # Rename spatial coordinates
                        da = da.rename({'x': 'longitude', 'y': 'latitude'})

                        # Store
                        datasets.append(da)
                        dates.append(file_date)

                    except Exception as e:
                        logger.warning(f"  Failed to read {tif_file.name}: {e}")
                        continue

                if not datasets:
                    logger.error(f"  ✗ No valid data for year {year}")
                    continue

                logger.info(f"  Loaded {len(datasets)} files")

                # Concatenate along time dimension
                combined = xr.concat(datasets, dim='time')
                combined['time'] = dates

                # Convert to Dataset with proper variable name
                ds = combined.to_dataset(name=source)

                # Add metadata from centralized config
                from app.config.data_sources import TEMPERATURE_LONG_NAMES

                ds.attrs['title'] = f'{TEMPERATURE_LONG_NAMES.get(source, "Temperature")} {year}'
                ds.attrs['source'] = 'ERA5 Land'
                ds.attrs['units'] = 'degrees_Celsius'
                ds.attrs['description'] = f'{TEMPERATURE_LONG_NAMES.get(source, "Temperature")} from ERA5 Land reanalysis'
                ds.attrs['created'] = datetime.now().isoformat()

                # Set variable attributes
                ds[source].attrs['long_name'] = TEMPERATURE_LONG_NAMES.get(source, 'Temperature')
                ds[source].attrs['units'] = 'degrees_Celsius'
                ds[source].attrs['standard_name'] = 'air_temperature'

                # Encoding for efficient storage
                encoding = {
                    source: {
                        'chunksizes': (1, 20, 20),
                        'zlib': True,
                        'complevel': 5,
                        'dtype': 'float32',
                        '_FillValue': -9999.0
                    },
                    'time': {
                        'units': 'days since 1970-01-01',
                        'calendar': 'proleptic_gregorian',
                        'dtype': 'float64'
                    },
                    'latitude': {
                        'dtype': 'float32'
                    },
                    'longitude': {
                        'dtype': 'float32'
                    }
                }

                # Write to NetCDF
                logger.info(f"  Writing to {output_file.name}...")

                # FUSE FIX: Write to temp first, then move
                import tempfile
                import shutil
                temp_dir = Path(tempfile.mkdtemp(prefix="temp_hist_"))
                temp_file = temp_dir / output_file.name

                ds.to_netcdf(temp_file, mode='w', encoding=encoding, engine='netcdf4')
                shutil.copy2(temp_file, output_file)
                shutil.rmtree(temp_dir, ignore_errors=True)

                # Get stats
                time_count = len(ds.time)
                time_min = pd.Timestamp(ds.time.min().values).date()
                time_max = pd.Timestamp(ds.time.max().values).date()

                logger.info(f"  ✓ Year {year} complete")
                logger.info(f"    Time range: {time_min} to {time_max}")
                logger.info(f"    Total days: {time_count}")
                logger.info(f"    Output: {output_file}")

            except Exception as e:
                logger.error(f"  ✗ Failed to process year {year}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)

    # List all created files for each source
    for source in sources:
        hist_dir = data_dir / f"{source}_hist"
        hist_files = sorted(hist_dir.glob(f"{source}_*.nc"))
        logger.info(f"\n{source.upper()} Historical NetCDF files: {len(hist_files)}")

        for hist_file in hist_files:
            size_mb = hist_file.stat().st_size / 1024 / 1024
            logger.info(f"  - {hist_file.name} ({size_mb:.2f} MB)")

    logger.info("=" * 80)


if __name__ == "__main__":
    build_temperature_historical()
