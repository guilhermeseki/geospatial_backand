#!/usr/bin/env python3
"""
Rechunk CHIRPS NetCDF files for better time-series query performance.

Problem: Current CHIRPS files have chunksizes=(1, 20, 20) - only 1 time step per chunk
Solution: Rechunk to (365, 20, 20) or (122, 20, 20) for much faster queries

This reads each yearly CHIRPS file and writes it back with optimized chunking.
"""
import xarray as xr
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path("/mnt/workwork/geoserver_data/chirps_hist")
BACKUP_DIR = DATA_DIR / "backup_original_chunks"

# Optimal chunk sizes for time-series queries
# Time: 365 days (1 year) - optimized for long-term historical queries (10+ years)
# Spatial: Keep at 20x20 to match original
TARGET_CHUNKS = {"time": 365, "latitude": 20, "longitude": 20}


def rechunk_file(file_path: Path):
    """Rechunk a single NetCDF file."""
    logger.info(f"Processing: {file_path.name}")

    # Open original file
    ds = xr.open_dataset(file_path)
    logger.info(f"  Original chunks: {ds['precipitation'].encoding.get('chunksizes')}")
    logger.info(f"  Dimensions: {dict(ds.dims)}")

    # Create backup
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_path = BACKUP_DIR / file_path.name
    if not backup_path.exists():
        logger.info(f"  Creating backup: {backup_path.name}")
        import shutil
        shutil.copy2(file_path, backup_path)

    # Rechunk and write
    temp_path = file_path.with_suffix('.nc.tmp')

    # Adjust chunk size if file has fewer time steps than target
    actual_time_dim = ds.dims['time']
    time_chunk = min(TARGET_CHUNKS['time'], actual_time_dim)

    actual_chunks = {
        'time': time_chunk,
        'latitude': TARGET_CHUNKS['latitude'],
        'longitude': TARGET_CHUNKS['longitude']
    }

    logger.info(f"  Rechunking to: {actual_chunks}")

    # Rechunk the dataset
    ds_rechunked = ds.chunk(actual_chunks)

    # Write with new chunking
    encoding = {
        'precipitation': {
            'chunksizes': (time_chunk, actual_chunks['latitude'], actual_chunks['longitude']),
            'zlib': True,
            'complevel': 4,
            'dtype': 'float32'
        },
        'time': {'dtype': 'int64'},
        'latitude': {'dtype': 'float64'},
        'longitude': {'dtype': 'float64'}
    }

    logger.info(f"  Writing rechunked file to: {temp_path.name}")
    ds_rechunked.to_netcdf(
        temp_path,
        engine='netcdf4',
        encoding=encoding,
        format='NETCDF4'
    )

    ds.close()
    ds_rechunked.close()

    # Replace original with rechunked version
    temp_path.replace(file_path)
    logger.info(f"  ✓ Successfully rechunked: {file_path.name}")


def main():
    logger.info("=" * 80)
    logger.info("CHIRPS NetCDF Rechunking Tool")
    logger.info("=" * 80)
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Target chunks: {TARGET_CHUNKS}")
    logger.info("")

    # Find all CHIRPS yearly files
    nc_files = sorted(DATA_DIR.glob("brazil_chirps_*.nc"))
    logger.info(f"Found {len(nc_files)} CHIRPS NetCDF files")
    logger.info("")

    if not nc_files:
        logger.error("No CHIRPS files found!")
        return

    # Rechunk each file
    for i, nc_file in enumerate(nc_files, 1):
        logger.info(f"[{i}/{len(nc_files)}] Processing {nc_file.name}")
        try:
            rechunk_file(nc_file)
        except Exception as e:
            logger.error(f"  ✗ Error rechunking {nc_file.name}: {e}")
            logger.exception(e)
        logger.info("")

    logger.info("=" * 80)
    logger.info("Rechunking complete!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Restart the API to reload datasets with new chunks")
    logger.info("2. Test query performance with: /precipitation/history")
    logger.info("")
    logger.info("Backups saved to:")
    logger.info(f"  {BACKUP_DIR}")


if __name__ == "__main__":
    main()
