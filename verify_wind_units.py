#!/usr/bin/env python3
"""
Download fresh wind data for a specific date and verify units.
This will help confirm whether ERA5 data comes in m/s or km/h.
"""
import cdsapi
import xarray as xr
import numpy as np
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_wind_data(date: str, output_path: Path):
    """Download ERA5 wind components for a specific date."""
    logger.info(f"Downloading ERA5 wind data for {date}...")

    c = cdsapi.Client()

    year, month, day = date.split('-')

    c.retrieve(
        'reanalysis-era5-land',
        {
            'product_type': 'reanalysis',
            'variable': [
                '10m_u_component_of_wind',
                '10m_v_component_of_wind',
            ],
            'year': year,
            'month': month,
            'day': day,
            'time': [
                '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
                '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
                '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
                '18:00', '19:00', '20:00', '21:00', '22:00', '23:00',
            ],
            'area': [5, -75, -35, -33],  # Brazil bounding box [N, W, S, E]
            'format': 'netcdf',
        },
        str(output_path)
    )

    logger.info(f"✓ Downloaded to {output_path}")


def analyze_wind_data(nc_path: Path, date_str: str):
    """Analyze the downloaded wind data to check units."""
    logger.info(f"\nAnalyzing downloaded wind data...")

    with xr.open_dataset(nc_path) as ds:
        logger.info(f"\nDataset variables: {list(ds.data_vars)}")
        logger.info(f"Dataset dimensions: {dict(ds.dims)}")

        # Get u and v components
        u = ds['u10']
        v = ds['v10']

        logger.info(f"\nU component metadata:")
        logger.info(f"  Units: {u.attrs.get('units', 'NOT SPECIFIED')}")
        logger.info(f"  Long name: {u.attrs.get('long_name', 'N/A')}")

        logger.info(f"\nV component metadata:")
        logger.info(f"  Units: {v.attrs.get('units', 'NOT SPECIFIED')}")
        logger.info(f"  Long name: {v.attrs.get('long_name', 'N/A')}")

        # Calculate wind speed (no conversion yet)
        wind_speed = np.sqrt(u**2 + v**2)

        # Get the time dimension name (could be 'time' or 'valid_time')
        time_dim = 'valid_time' if 'valid_time' in wind_speed.dims else 'time'

        # Get daily maximum
        daily_max = wind_speed.max(dim=time_dim)

        # Find the maximum value and its location
        max_value = float(daily_max.max().values)
        max_loc = daily_max.where(daily_max == max_value, drop=True)

        if len(max_loc.latitude) > 0:
            max_lat = float(max_loc.latitude.values[0])
            max_lon = float(max_loc.longitude.values[0])
            logger.info(f"\nRAW DOWNLOADED DATA (NO CONVERSION):")
            logger.info(f"  Maximum wind speed: {max_value:.2f} (units from metadata)")
            logger.info(f"  Location: lat={max_lat:.2f}, lon={max_lon:.2f}")
            logger.info(f"  Date: {date_str}")

            # Calculate some statistics
            mean_wind = float(daily_max.mean().values)
            min_wind = float(daily_max.min().values)

            logger.info(f"\n  Statistics (daily maximum across Brazil):")
            logger.info(f"    Min: {min_wind:.2f}")
            logger.info(f"    Mean: {mean_wind:.2f}")
            logger.info(f"    Max: {max_value:.2f}")

            # Convert to km/h for comparison
            max_kmh = max_value * 3.6
            mean_kmh = mean_wind * 3.6

            logger.info(f"\n  IF DATA IS IN m/s, THEN in km/h:")
            logger.info(f"    Mean: {mean_kmh:.2f} km/h")
            logger.info(f"    Max: {max_kmh:.2f} km/h")

            return {
                'raw_max': max_value,
                'raw_mean': mean_wind,
                'units': u.attrs.get('units', 'UNKNOWN'),
                'lat': max_lat,
                'lon': max_lon
            }


def compare_with_existing(date_str: str, raw_stats: dict):
    """Compare with existing processed data."""
    logger.info(f"\n{'='*80}")
    logger.info("COMPARING WITH EXISTING PROCESSED DATA")
    logger.info('='*80)

    # Check GeoTIFF
    date_formatted = date_str.replace('-', '')
    geotiff_path = Path(f"/mnt/workwork/geoserver_data/wind_speed/wind_speed_{date_formatted}.tif")

    if geotiff_path.exists():
        import rasterio
        with rasterio.open(geotiff_path) as src:
            data = src.read(1)
            valid_data = data[~np.isnan(data)]

            if len(valid_data) > 0:
                existing_max = valid_data.max()
                existing_mean = valid_data.mean()

                logger.info(f"\nExisting GeoTIFF ({geotiff_path.name}):")
                logger.info(f"  Mean: {existing_mean:.2f}")
                logger.info(f"  Max: {existing_max:.2f}")

                # Calculate ratio
                ratio = existing_max / raw_stats['raw_max']
                logger.info(f"\nRATIO (existing/raw): {ratio:.2f}")

                if abs(ratio - 3.6) < 0.1:
                    logger.info("  ✓ Ratio ≈ 3.6: Raw data is in m/s, existing data was converted to km/h")
                    logger.info("  ✓ This confirms SINGLE conversion is correct")
                elif abs(ratio - 12.96) < 0.5:  # 3.6²
                    logger.info("  ✗ Ratio ≈ 12.96 (3.6²): DOUBLE CONVERSION CONFIRMED")
                    logger.info("  ✗ Raw data in m/s → converted once → converted again")
                elif abs(ratio - 1.0) < 0.1:
                    logger.info("  ? Ratio ≈ 1.0: Raw data might already be in km/h (unlikely)")
                else:
                    logger.info(f"  ? Unexpected ratio: {ratio:.2f}")
    else:
        logger.warning(f"GeoTIFF not found: {geotiff_path}")


def main():
    # Date to verify (Ciclone Bomba)
    verify_date = "2020-06-30"

    output_dir = Path("/tmp/wind_verification")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"era5_wind_{verify_date}.nc"
    extracted_file = output_dir / "data_0.nc"

    logger.info("="*80)
    logger.info("WIND DATA UNIT VERIFICATION")
    logger.info("="*80)
    logger.info(f"Date: {verify_date} (Ciclone Bomba)")
    logger.info(f"Purpose: Verify if ERA5 data is in m/s or km/h")
    logger.info("="*80)

    # Download fresh data (if not already downloaded)
    if not extracted_file.exists():
        download_wind_data(verify_date, output_file)

        # Extract zip
        import zipfile
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        logger.info(f"✓ Extracted to {extracted_file}")

    # Analyze raw data
    raw_stats = analyze_wind_data(extracted_file, verify_date)

    # Compare with existing
    compare_with_existing(verify_date, raw_stats)

    logger.info("\n" + "="*80)
    logger.info("VERIFICATION COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
