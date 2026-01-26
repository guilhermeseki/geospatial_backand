"""
Run ERA5 Hourly Solar Radiation Flow - Download hourly and aggregate to daily

Downloads ERA5 hourly surface_solar_radiation_downwards and aggregates to daily totals.

Usage:
    python app/run_era5_hourly_solar.py --year 2024
    python app/run_era5_hourly_solar.py --start-date 2024-01-01 --end-date 2024-01-31
    python app/run_era5_hourly_solar.py --days 30
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import argparse
import logging
import cdsapi
import xarray as xr
import numpy as np
import pandas as pd
import rioxarray

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()


def download_era5_hourly_solar(start_date: date, end_date: date) -> Path:
    """Download ERA5 hourly solar radiation"""
    raw_dir = Path(settings.DATA_DIR) / "raw" / "era5_solar"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = raw_dir / f"solar_{start_date}_{end_date}.nc"
    
    if output_path.exists():
        logger.info(f"Already downloaded: {output_path}")
        return output_path
    
    # Generate date list
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    request = {
        'product_type': 'reanalysis',
        'variable': 'surface_solar_radiation_downwards',
        'year': list(set([d.split('-')[0] for d in dates])),
        'month': list(set([d.split('-')[1] for d in dates])),
        'day': list(set([d.split('-')[2] for d in dates])),
        'time': [f'{h:02d}:00' for h in range(24)],  # All 24 hours
        'area': settings.latam_bbox_cds,  # [N, W, S, E]
        'format': 'netcdf',
    }
    
    logger.info(f"Downloading ERA5 hourly solar: {start_date} to {end_date}")
    logger.info(f"  Years: {request['year']}")
    logger.info(f"  Months: {request['month']}")
    logger.info(f"  Days: {request['day'][:5]}... ({len(request['day'])} days)")
    logger.info(f"  Hours: 24 hours per day")
    
    client = cdsapi.Client()
    client.retrieve('reanalysis-era5-single-levels', request, str(output_path))
    
    logger.info(f"✓ Downloaded: {output_path} ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")
    return output_path


def process_hourly_to_daily(hourly_path: Path) -> Path:
    """Aggregate hourly solar to daily totals and convert to kWh/m²/day"""
    logger.info("Processing hourly data to daily totals...")
    
    # Open hourly data
    ds = xr.open_dataset(hourly_path)
    logger.info(f"  Variables: {list(ds.data_vars)}")
    logger.info(f"  Shape: {ds.dims}")
    
    # Get solar radiation variable (might be 'ssrd' or 'surface_solar_radiation_downwards')
    var_name = 'ssrd' if 'ssrd' in ds.data_vars else 'surface_solar_radiation_downwards'
    da = ds[var_name]

    # ERA5 uses 'valid_time' not 'time'
    if 'valid_time' in da.dims:
        da = da.rename({'valid_time': 'time'})

    # Sum hourly values to get daily total (J/m²)
    logger.info("  Summing 24 hourly values to daily totals...")
    daily = da.resample(time='1D').sum()
    
    # Convert from J/m² to kWh/m²/day
    logger.info("  Converting J/m² to kWh/m²/day...")
    daily = daily / 3600000  # 1 kWh = 3,600,000 J
    
    # Save
    daily_path = hourly_path.parent / f"daily_{hourly_path.name}"
    daily_ds = daily.to_dataset(name='solar_radiation')
    daily_ds['solar_radiation'].attrs = {
        'long_name': 'Surface Solar Radiation Downwards (Daily Total)',
        'units': 'kWh/m²/day',
        'source': 'ERA5 reanalysis'
    }
    daily_ds.to_netcdf(daily_path)
    
    logger.info(f"✓ Daily data saved: {daily_path}")
    logger.info(f"  Days: {len(daily.time)}")
    logger.info(f"  Value range: {float(daily.min().values):.2f} - {float(daily.max().values):.2f} kWh/m²/day")
    
    ds.close()
    return daily_path


def main():
    parser = argparse.ArgumentParser(description='Download ERA5 hourly solar and aggregate to daily')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--year', type=int, help='Process entire year')
    parser.add_argument('--days', type=int, help='Process last N days')
    
    args = parser.parse_args()
    
    # Determine date range
    today = date.today()
    era5_lag = 7
    
    if args.days:
        end_date = today - timedelta(days=era5_lag)
        start_date = end_date - timedelta(days=args.days)
    elif args.year:
        start_date = date(args.year, 1, 1)
        end_date = date(args.year, 12, 31)
    else:
        start_date = date.fromisoformat(args.start_date) if args.start_date else date(today.year, 1, 1)
        end_date = date.fromisoformat(args.end_date) if args.end_date else today - timedelta(days=era5_lag)
    
    logger.info("="*80)
    logger.info("ERA5 Hourly Solar Radiation → Daily Aggregation")
    logger.info("="*80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Days: {(end_date - start_date).days + 1}")
    logger.info("="*80)
    
    try:
        # Download hourly
        hourly_path = download_era5_hourly_solar(start_date, end_date)
        
        # Aggregate to daily
        daily_path = process_hourly_to_daily(hourly_path)
        
        logger.info("")
        logger.info("="*80)
        logger.info("✓ SUCCESS")
        logger.info("="*80)
        logger.info(f"Daily solar data: {daily_path}")
        logger.info("")
        logger.info("Next: Use this daily NetCDF in your existing ERA5 flow")
        logger.info("  (or integrate this into the main ERA5 flow)")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
