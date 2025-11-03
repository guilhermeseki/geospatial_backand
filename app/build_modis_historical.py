#!/usr/bin/env python3
"""
Build MODIS yearly historical NetCDF files from existing GeoTIFF files.
Creates yearly files with optimized chunking for 10km² farm queries.

Chunking strategy: time=-1 (entire year), lat=1000, lon=1000
"""
from pathlib import Path
import pandas as pd
import xarray as xr
import rioxarray
import tempfile
import shutil
from collections import defaultdict
from app.config.settings import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_modis_yearly_historical(
    start_year: int = None,
    end_year: int = None
):
    """
    Create yearly historical NetCDF files from existing MODIS GeoTIFF mosaics.
    """
    settings = get_settings()

    # Get directories
    geotiff_dir = Path(settings.DATA_DIR) / "ndvi_modis"
    hist_dir = Path(settings.DATA_DIR) / "ndvi_modis_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    if not geotiff_dir.exists():
        logger.error(f"GeoTIFF directory does not exist: {geotiff_dir}")
        return []

    logger.info("=" * 80)
    logger.info("BUILDING MODIS YEARLY HISTORICAL FILES")
    logger.info("=" * 80)

    # Find all GeoTIFF files
    geotiff_files = sorted(geotiff_dir.glob("ndvi_modis_*.tif"))
    logger.info(f"Found {len(geotiff_files)} MODIS GeoTIFF files")

    if not geotiff_files:
        logger.warning("No GeoTIFF files found!")
        return []

    # Extract dates and group by year
    files_by_year = defaultdict(list)
    for tif_file in geotiff_files:
        try:
            date_str = tif_file.stem.split('_')[-1]
            file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
            year = file_date.year

            # Filter by year range if specified
            if start_year and year < start_year:
                continue
            if end_year and year > end_year:
                continue

            files_by_year[year].append((file_date, tif_file))
        except Exception as e:
            logger.warning(f"Could not parse date from {tif_file.name}: {e}")

    logger.info(f"Files span {len(files_by_year)} year(s): {sorted(files_by_year.keys())}")

    updated_files = []

    # Process each year
    for year in sorted(files_by_year.keys()):
        year_files = sorted(files_by_year[year])
        logger.info(f"\n📅 Processing year {year} ({len(year_files)} files)")

        year_file = hist_dir / f"ndvi_modis_{year}.nc"

        if year_file.exists():
            logger.info(f"  Year file already exists: {year_file.name}, skipping")
            continue

        # FUSE FIX: Create temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix=f"ndvi_modis_{year}_"))
        temp_file = temp_dir / f"ndvi_modis_{year}.nc"

        try:
            # Load all GeoTIFFs for this year WITH LAZY LOADING
            data_arrays = []
            time_coords = []

            for file_date, tif_file in year_files:
                try:
                    # IMPORTANT: Use chunks='auto' for lazy loading - keeps data on disk
                    da = rioxarray.open_rasterio(tif_file, masked=True, chunks='auto').squeeze()
                    # Remove band dimension if present
                    if 'band' in da.dims:
                        da = da.isel(band=0)
                    data_arrays.append(da)
                    time_coords.append(pd.Timestamp(file_date))
                except Exception as e:
                    logger.warning(f"  Could not load {tif_file.name}: {e}")
                    continue

            if not data_arrays:
                logger.warning(f"  No valid data for year {year}, skipping")
                continue

            logger.info(f"  Loaded {len(data_arrays)} files (lazy loading with Dask)")

            # Stack along time dimension (still lazy - no compute yet)
            combined = xr.concat(data_arrays, dim='time')
            combined = combined.assign_coords(time=time_coords)

            # Rename spatial coordinates
            coord_mapping = {}
            for coord in combined.dims:
                if coord in ['x', 'longitude', 'lon']:
                    coord_mapping[coord] = 'longitude'
                elif coord in ['y', 'latitude', 'lat']:
                    coord_mapping[coord] = 'latitude'
            if coord_mapping:
                combined = combined.rename(coord_mapping)

            # Create dataset
            var_name = 'ndvi'
            ds = combined.to_dataset(name=var_name)
            ds.attrs['source'] = 'MODIS MOD13Q1'
            ds.attrs['year'] = year
            ds.attrs['resolution'] = '250m'
            ds.attrs['provider'] = 'Microsoft Planetary Computer'

            # OPTIMIZED CHUNKING for 10km² farms (40x40 pixels at 250m)
            # time=full_year: Entire year in one chunk (only ~15-23 composites per year)
            # lat=1000, lon=1000: 250km x 250km spatial chunks (2500 farms per chunk)
            n_times = len(time_coords)
            lat_size = min(1000, ds.sizes['latitude'])
            lon_size = min(1000, ds.sizes['longitude'])

            encoding = {
                var_name: {
                    'chunksizes': (n_times, lat_size, lon_size),  # Full year, 250km chunks
                    'zlib': True,
                    'complevel': 5,
                    'dtype': 'float32'
                },
                'time': {
                    'units': 'days since 1970-01-01',
                    'calendar': 'proleptic_gregorian',
                    'dtype': 'float64'
                }
            }

            # Rechunk for optimal write pattern (this is still lazy)
            logger.info(f"  Rechunking for optimal storage...")
            ds_chunked = ds.chunk({'time': n_times, 'latitude': lat_size, 'longitude': lon_size})

            # Write to temp file (Dask will handle compute in chunks)
            logger.info(f"  Writing to temp file with optimized chunking...")
            logger.info(f"    Chunks: time={n_times} (entire year), lat={lat_size}, lon={lon_size}")
            logger.info(f"    This will take a while - Dask is processing {len(time_coords)} files...")
            ds_chunked.to_netcdf(str(temp_file), mode='w', encoding=encoding, engine='netcdf4', compute=True)

            # Copy to final location
            logger.info(f"  Copying to: {year_file}")
            shutil.copy2(temp_file, year_file)

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

            updated_files.append(year_file)
            logger.info(f"  ✓ Created {year_file.name}")
            logger.info(f"    Time range: {time_coords[0].date()} to {time_coords[-1].date()}")
            logger.info(f"    Total composites: {len(time_coords)}")

        except Exception as e:
            logger.error(f"  ✗ Failed to process year {year}: {e}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            continue

    logger.info(f"\n✓ Created {len(updated_files)} yearly file(s)")
    logger.info("=" * 80)
    return updated_files


if __name__ == "__main__":
    build_modis_yearly_historical()
