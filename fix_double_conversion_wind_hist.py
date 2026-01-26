#!/usr/bin/env python3
"""
Fix double conversion in wind_speed historical NetCDF files.
The files were converted from m/s to km/h TWICE (once during build, once by our script).
This divides by 3.6 to revert the second conversion.
"""
from pathlib import Path
import xarray as xr
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    data_dir = Path("/mnt/workwork/geoserver_data")
    hist_dir = data_dir / "wind_speed_hist"

    if not hist_dir.exists():
        logger.error(f"Wind speed historical directory not found: {hist_dir}")
        return

    # Find all wind speed historical NetCDF files
    nc_files = sorted(hist_dir.glob("wind_speed_*.nc"))

    if not nc_files:
        logger.error(f"No wind speed NetCDF files found in {hist_dir}")
        return

    logger.info("=" * 80)
    logger.info("FIXING DOUBLE CONVERSION IN WIND SPEED HISTORICAL NetCDF")
    logger.info("=" * 80)
    logger.info(f"Directory: {hist_dir}")
    logger.info(f"Files to fix: {len(nc_files)}")
    logger.info(f"Fix: Divide by 3.6 to revert second conversion")
    logger.info("=" * 80)

    # Convert all files
    success_count = 0
    fail_count = 0

    for nc_file in nc_files:
        try:
            logger.info(f"\nProcessing {nc_file.name}...")

            # Load the NetCDF file
            ds = xr.open_dataset(nc_file)

            # Get statistics before fix
            before_min = float(ds['wind_speed'].min().values)
            before_max = float(ds['wind_speed'].max().values)
            before_mean = float(ds['wind_speed'].mean().values)

            logger.info(f"  Before: min={before_min:.2f}, max={before_max:.2f}, mean={before_mean:.2f}")

            # Revert second conversion (divide by 3.6)
            ds['wind_speed'] = ds['wind_speed'] / 3.6

            # Update metadata
            ds['wind_speed'].attrs['units'] = 'km/h'
            ds.attrs['units'] = 'km/h'
            ds.attrs['description'] = 'Daily maximum wind speed at 10m, calculated as sqrt(u² + v²), converted to km/h'

            # Get statistics after fix
            after_min = float(ds['wind_speed'].min().values)
            after_max = float(ds['wind_speed'].max().values)
            after_mean = float(ds['wind_speed'].mean().values)

            logger.info(f"  After:  min={after_min:.2f}, max={after_max:.2f}, mean={after_mean:.2f}")

            # Encoding for efficient storage
            encoding = {
                'wind_speed': {
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

            # Write back to the same file (FUSE-safe)
            import tempfile
            import shutil
            temp_dir = Path(tempfile.mkdtemp(prefix="wind_hist_fix_"))
            temp_file = temp_dir / nc_file.name

            ds.to_netcdf(temp_file, mode='w', encoding=encoding, engine='netcdf4')
            shutil.copy2(temp_file, nc_file)
            shutil.rmtree(temp_dir, ignore_errors=True)

            ds.close()

            logger.info(f"  ✓ Fixed successfully")
            success_count += 1

        except Exception as e:
            logger.error(f"  ✗ Failed to fix {nc_file.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            fail_count += 1

    logger.info("\n" + "=" * 80)
    logger.info("FIX COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Successfully fixed: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
