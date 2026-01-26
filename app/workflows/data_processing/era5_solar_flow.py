"""
ERA5 Hourly Solar Radiation Flow - Complete Pipeline

Downloads ERA5 hourly surface_solar_radiation_downwards and processes it into:
1. Daily GeoTIFF files for GeoServer time-enabled mosaics
2. Yearly historical NetCDF files for fast API queries

This flow:
- Downloads hourly ERA5 solar radiation from CDS
- Aggregates 24 hourly values to daily totals
- Converts J/m² to kWh/m²/day
- Creates GeoTIFFs for each day
- Appends to yearly historical NetCDF files
"""
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import cdsapi
import xarray as xr
import numpy as np
import pandas as pd
import rioxarray
from prefect import flow, task, get_run_logger
from app.config.settings import get_settings


@task
def check_missing_dates(
    start_date: date,
    end_date: date
) -> Dict[str, List[date]]:
    """Check which dates are missing from GeoTIFF and historical NetCDF"""
    logger = get_run_logger()
    settings = get_settings()

    requested_dates = []
    current = start_date
    while current <= end_date:
        requested_dates.append(current)
        current += timedelta(days=1)

    logger.info(f"Checking for {len(requested_dates)} dates: {start_date} to {end_date}")

    # Get directories
    geotiff_dir = Path(settings.DATA_DIR) / "solar_radiation"
    hist_dir = Path(settings.DATA_DIR) / "solar_radiation_hist"

    # Check GeoTIFF files
    existing_geotiff_dates = set()
    if geotiff_dir.exists():
        for tif_file in geotiff_dir.glob("solar_radiation_*.tif"):
            try:
                date_str = tif_file.stem.split('_')[-1]
                file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
                existing_geotiff_dates.add(file_date)
            except Exception as e:
                logger.warning(f"Could not parse date from {tif_file.name}: {e}")

    logger.info(f"Found {len(existing_geotiff_dates)} existing GeoTIFF files")

    # Check historical NetCDF (yearly files)
    existing_hist_dates = set()
    if hist_dir.exists():
        for year_file in hist_dir.glob("solar_radiation_*.nc"):
            try:
                ds = xr.open_dataset(year_file, chunks='auto')
                if 'solar_radiation' in ds.data_vars:
                    file_dates = set(pd.to_datetime(ds['solar_radiation'].time.values).date)
                    existing_hist_dates.update(file_dates)
                ds.close()
            except Exception as e:
                logger.warning(f"Could not read {year_file.name}: {e}")

    logger.info(f"Found {len(existing_hist_dates)} dates in historical NetCDF")

    # Calculate missing dates
    requested_dates_set = set(requested_dates)
    missing_geotiff = sorted(list(requested_dates_set - existing_geotiff_dates))
    missing_historical = sorted(list(requested_dates_set - existing_hist_dates))
    missing_download = sorted(list(set(missing_geotiff) | set(missing_historical)))

    logger.info(f"Missing from GeoTIFF: {len(missing_geotiff)} dates")
    logger.info(f"Missing from historical: {len(missing_historical)} dates")
    logger.info(f"Need to download: {len(missing_download)} dates")

    if missing_download:
        logger.info(f"  Download range: {min(missing_download)} to {max(missing_download)}")

    return {
        'geotiff': missing_geotiff,
        'historical': missing_historical,
        'download': missing_download
    }


@task(retries=2, retry_delay_seconds=300, timeout_seconds=3600)
def download_era5_hourly_solar(start_date: date, end_date: date) -> Path:
    """Download ERA5 hourly solar radiation from CDS"""
    logger = get_run_logger()
    settings = get_settings()

    raw_dir = Path(settings.DATA_DIR) / "raw" / "era5_solar"
    raw_dir.mkdir(parents=True, exist_ok=True)

    output_path = raw_dir / f"hourly_{start_date}_{end_date}.nc"

    if output_path.exists():
        logger.info(f"Already downloaded: {output_path.name}")
        return output_path

    # Generate date components
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    years = sorted(list(set([d.split('-')[0] for d in dates])))
    months = sorted(list(set([d.split('-')[1] for d in dates])))
    days = sorted(list(set([d.split('-')[2] for d in dates])))

    request = {
        'product_type': 'reanalysis',
        'variable': 'surface_solar_radiation_downwards',
        'year': years,
        'month': months,
        'day': days,
        'time': [f'{h:02d}:00' for h in range(24)],
        'area': settings.latam_bbox_cds,  # [N, W, S, E]
        'format': 'netcdf',
    }

    logger.info(f"Downloading ERA5 hourly solar: {start_date} to {end_date}")
    logger.info(f"  Years: {years}, Months: {months}")
    logger.info(f"  Days: {len(days)} days × 24 hours = {len(days) * 24} hours")
    logger.info(f"  Area: {request['area']}")

    client = cdsapi.Client()
    client.retrieve('reanalysis-era5-single-levels', request, str(output_path))

    file_size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info(f"✓ Downloaded: {output_path.name} ({file_size_mb:.2f} MB)")
    return output_path


@task
def aggregate_hourly_to_daily(hourly_path: Path) -> Path:
    """Aggregate hourly solar to daily totals and convert units"""
    logger = get_run_logger()

    logger.info("Aggregating hourly data to daily totals...")

    # Open hourly data
    ds = xr.open_dataset(hourly_path)
    logger.info(f"  Input shape: {ds.dims}")

    # Get variable (ERA5 uses 'ssrd')
    var_name = 'ssrd' if 'ssrd' in ds.data_vars else 'surface_solar_radiation_downwards'
    da = ds[var_name]

    # Rename time dimension if needed
    if 'valid_time' in da.dims:
        da = da.rename({'valid_time': 'time'})

    # Sum 24 hourly values to get daily total (J/m²)
    logger.info("  Summing 24 hourly values...")
    daily = da.resample(time='1D').sum()

    # Convert from J/m² to kWh/m²/day
    logger.info("  Converting J/m² → kWh/m²/day...")
    daily = daily / 3600000

    # Save daily NetCDF
    daily_path = hourly_path.parent / f"daily_{hourly_path.name}"
    daily_ds = daily.to_dataset(name='solar_radiation')
    daily_ds['solar_radiation'].attrs = {
        'long_name': 'Surface Solar Radiation Downwards (Daily Total)',
        'units': 'kWh/m²/day',
        'source': 'ERA5 reanalysis (hourly aggregated)'
    }
    daily_ds.to_netcdf(daily_path)

    logger.info(f"✓ Daily data: {daily_path.name}")
    logger.info(f"  Days: {len(daily.time)}")
    logger.info(f"  Range: {float(daily.min().values):.2f} - {float(daily.max().values):.2f} kWh/m²/day")

    ds.close()
    return daily_path


@task
def process_daily_to_geotiff(
    daily_netcdf: Path,
    bbox: tuple,
    dates_to_process: Optional[List[date]] = None
) -> List[Path]:
    """Convert daily NetCDF to GeoTIFF files"""
    logger = get_run_logger()
    settings = get_settings()

    output_dir = Path(settings.DATA_DIR) / "solar_radiation"
    output_dir.mkdir(parents=True, exist_ok=True)

    if dates_to_process:
        logger.info(f"Processing {len(dates_to_process)} specific dates to GeoTIFF")

    processed_paths = []

    try:
        ds = xr.open_dataset(daily_netcdf)
        da = ds['solar_radiation']

        # Process each day
        for time_val in da.time.values:
            daily_data = da.sel(time=time_val)
            day_date = pd.Timestamp(time_val).date()

            # Skip if not in requested dates
            if dates_to_process and day_date not in dates_to_process:
                continue

            # Set CRS and clip to bbox
            daily_data = daily_data.rio.write_crs("EPSG:4326")

            west, south, east, north = bbox
            try:
                daily_data = daily_data.rio.clip_box(minx=west, miny=south, maxx=east, maxy=north)
            except Exception as e:
                logger.warning(f"Could not clip to bbox: {e}")

            # Save as Cloud Optimized GeoTIFF
            date_str = day_date.strftime("%Y%m%d")
            output_path = output_dir / f"solar_radiation_{date_str}.tif"

            daily_data.rio.to_raster(
                output_path,
                driver="COG",
                compress="DEFLATE",
                predictor=2
            )

            processed_paths.append(output_path)
            logger.info(f"  ✓ {output_path.name}")

        ds.close()
        logger.info(f"✓ Created {len(processed_paths)} GeoTIFF files")
        return processed_paths

    except Exception as e:
        logger.error(f"✗ Error creating GeoTIFFs: {e}")
        raise


@task
def append_to_yearly_historical(
    daily_netcdf: Path,
    bbox: tuple,
    dates_to_append: Optional[List[date]] = None
) -> List[Path]:
    """Append daily data to yearly historical NetCDF files"""
    logger = get_run_logger()
    settings = get_settings()

    hist_dir = Path(settings.DATA_DIR) / "solar_radiation_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    if dates_to_append:
        logger.info(f"Appending {len(dates_to_append)} dates to historical")

    try:
        ds = xr.open_dataset(daily_netcdf)
        da = ds['solar_radiation']

        # Note: dates_to_append parameter exists for consistency with other flows,
        # but we process all dates in the daily_netcdf since it's already filtered
        # to only contain the dates we want to append

        # Group by year
        years = pd.to_datetime(da.time.values).year.unique()
        updated_files = []

        for year in years:
            year_file = hist_dir / f"solar_radiation_{year}.nc"
            year_data = da.sel(time=da.time.dt.year == year)

            if year_file.exists():
                # Append to existing
                logger.info(f"  Appending {len(year_data.time)} days to {year_file.name}")
                existing_ds = xr.open_dataset(year_file)
                combined = xr.concat([existing_ds['solar_radiation'], year_data], dim='time')
                combined = combined.sortby('time').drop_duplicates('time')
                existing_ds.close()
                combined_ds = combined.to_dataset(name='solar_radiation')
            else:
                # Create new
                logger.info(f"  Creating {year_file.name} ({len(year_data.time)} days)")
                combined_ds = year_data.to_dataset(name='solar_radiation')

            # Add metadata
            combined_ds['solar_radiation'].attrs = {
                'long_name': 'Surface Solar Radiation Downwards (Daily Total)',
                'units': 'kWh/m²/day',
                'source': 'ERA5 reanalysis',
                'resolution': '0.1 degrees',
            }

            # Save with chunking (adaptive to actual data size)
            n_time = len(combined_ds.time)
            n_lat = len(combined_ds.latitude)
            n_lon = len(combined_ds.longitude)

            encoding = {
                'solar_radiation': {
                    'dtype': 'float32',
                    'zlib': True,
                    'complevel': 4,
                    'chunksizes': (
                        min(365, n_time),  # Don't exceed actual time dimension
                        min(20, n_lat),
                        min(20, n_lon)
                    )
                }
            }

            combined_ds.to_netcdf(year_file, encoding=encoding, mode='w')
            updated_files.append(year_file)
            logger.info(f"  ✓ Saved {year_file.name}")

        ds.close()
        return updated_files

    except Exception as e:
        logger.error(f"✗ Error appending to historical: {e}")
        raise


@task
def cleanup_raw_files(*paths):
    """Clean up temporary files"""
    logger = get_run_logger()
    for path in paths:
        try:
            if path and path.exists():
                path.unlink()
                logger.info(f"  Cleaned up: {path.name}")
        except Exception as e:
            logger.warning(f"Could not cleanup {path}: {e}")


@flow(name="process-era5-hourly-solar")
def era5_hourly_solar_flow(
    start_date: date,
    end_date: date,
    batch_days: int = 31
) -> List[Path]:
    """
    Complete ERA5 hourly solar radiation pipeline.

    Downloads hourly data, aggregates to daily, creates GeoTIFFs and historical NetCDF.

    Args:
        start_date: First date to process
        end_date: Last date to process
        batch_days: Number of days per download batch (default: 31)

    Returns:
        List of created GeoTIFF paths
    """
    logger = get_run_logger()
    settings = get_settings()

    logger.info(f"Processing ERA5 hourly solar: {start_date} to {end_date}")

    # Check what's missing
    missing_info = check_missing_dates(start_date, end_date)
    missing_download = missing_info['download']
    missing_geotiff = missing_info['geotiff']
    missing_historical = missing_info['historical']

    if not missing_download:
        logger.info("✓ All data already exists")
        return []

    logger.info(f"Need to download {len(missing_download)} dates")

    # Process in batches
    all_processed = []
    current_start = min(missing_download)

    while current_start <= max(missing_download):
        current_end = min(current_start + timedelta(days=batch_days - 1), max(missing_download))

        batch_dates = [d for d in missing_download if current_start <= d <= current_end]

        if not batch_dates:
            current_start = current_end + timedelta(days=1)
            continue

        geotiff_dates = [d for d in batch_dates if d in missing_geotiff]
        hist_dates = [d for d in batch_dates if d in missing_historical]

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Batch: {current_start} to {current_end} ({len(batch_dates)} days)")
            logger.info(f"  GeoTIFFs: {len(geotiff_dates)}, Historical: {len(hist_dates)}")
            logger.info(f"{'='*80}")

            # Download hourly data
            hourly_path = download_era5_hourly_solar(current_start, current_end)

            # Aggregate to daily
            daily_path = aggregate_hourly_to_daily(hourly_path)

            # Create GeoTIFFs
            if geotiff_dates:
                processed = process_daily_to_geotiff(
                    daily_netcdf=daily_path,
                    bbox=settings.latam_bbox_raster,
                    dates_to_process=geotiff_dates
                )
                all_processed.extend(processed)
            else:
                logger.info("  Skipping GeoTIFF (all exist)")

            # Append to historical
            if hist_dates:
                yearly_files = append_to_yearly_historical(
                    daily_netcdf=daily_path,
                    bbox=settings.latam_bbox_raster,
                    dates_to_append=hist_dates
                )
                logger.info(f"✓ Updated {len(yearly_files)} yearly file(s)")
            else:
                logger.info("  Skipping historical (all exist)")

            # Cleanup
            cleanup_raw_files(hourly_path, daily_path)

            logger.info(f"✓ Completed batch: {current_start} to {current_end}")

        except Exception as e:
            logger.error(f"✗ Failed batch {current_start} to {current_end}: {e}")
            import traceback
            logger.error(traceback.format_exc())

        current_start = current_end + timedelta(days=1)

    if all_processed:
        logger.info(f"\n✓ Successfully processed {len(all_processed)} GeoTIFF files")

    return all_processed
