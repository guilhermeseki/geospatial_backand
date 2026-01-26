"""
CAMS Solar Radiation Flow - Daily GHI Processing with Historical NetCDF Management

This flow downloads CAMS gridded solar radiation data (GHI - Global Horizontal Irradiance)
from the Atmosphere Data Store (ADS) and processes it into:
1. Daily GeoTIFF files for GeoServer time-enabled mosaics
2. Yearly historical NetCDF files for fast API queries

Data Source: CAMS gridded solar radiation (cams-gridded-solar-radiation)
- Spatial Resolution: 0.1° (~11km)
- Temporal Resolution: 15-minute → aggregated to daily totals
- Coverage: Brazil (Eastern South America)
- Accuracy: 17.3% RMS, 4% bias (validated in Brazil)
- Period: 2005-present (updates yearly with ~6 month lag)
"""
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import cdsapi
import xarray as xr
import pandas as pd
import numpy as np
from prefect import flow, task, get_run_logger
from app.config.settings import get_settings


@task
def check_missing_dates(
    start_date: date,
    end_date: date
) -> Dict[str, List[date]]:
    """
    Check which dates are missing from GeoTIFF and historical NetCDF separately.

    Returns:
        Dictionary with 'geotiff' and 'historical' keys containing lists of missing dates
    """
    logger = get_run_logger()
    settings = get_settings()

    # Generate list of requested dates
    requested_dates = []
    current = start_date
    while current <= end_date:
        requested_dates.append(current)
        current += timedelta(days=1)

    logger.info(f"Checking for {len(requested_dates)} dates: {start_date} to {end_date}")

    # Get directories
    geotiff_dir = Path(settings.DATA_DIR) / "ghi"
    hist_dir = Path(settings.DATA_DIR) / "ghi_hist"

    # Check GeoTIFF files
    existing_geotiff_dates = set()
    if geotiff_dir.exists():
        for tif_file in geotiff_dir.glob("ghi_*.tif"):
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
        for year_file in hist_dir.glob("ghi_*.nc"):
            try:
                ds = xr.open_dataset(year_file, chunks='auto')
                if 'ghi' in ds.data_vars:
                    file_dates = set(pd.to_datetime(ds['ghi'].time.values).date)
                    existing_hist_dates.update(file_dates)
                ds.close()
            except Exception as e:
                logger.warning(f"Could not read {year_file.name}: {e}")

    logger.info(f"Found {len(existing_hist_dates)} dates in historical NetCDF")

    # Calculate missing dates separately
    requested_dates_set = set(requested_dates)
    missing_geotiff = sorted(list(requested_dates_set - existing_geotiff_dates))
    missing_historical = sorted(list(requested_dates_set - existing_hist_dates))

    # Dates to download = union (missing from either source)
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


@task(retries=2, retry_delay_seconds=600, timeout_seconds=7200)  # 2 hours
def download_cams_solar_batch(
    start_date: date,
    end_date: date,
    area: List[float]
) -> Path:
    """
    Download CAMS gridded solar radiation for a date range.

    Note: CAMS gridded data is delivered as monthly files with 15-minute resolution.
    We download full months and extract the specific dates we need.

    Args:
        start_date: First date to download
        end_date: Last date to download
        area: Bounding box [N, W, S, E] for ADS API

    Returns:
        Path to downloaded NetCDF file
    """
    logger = get_run_logger()
    settings = get_settings()

    # Validate bbox: North must be > South
    north, west, south, east = area[0], area[1], area[2], area[3]

    if north <= south:
        raise ValueError(f"Invalid bbox: North ({north}) must be > South ({south})")

    if west >= east:
        raise ValueError(f"Invalid bbox: West ({west}) must be < East ({east})")

    logger.info(f"Using ADS bbox [N, W, S, E]: {area}")
    logger.info(f"  North: {north}, South: {south} (span: {north - south}°)")
    logger.info(f"  West: {west}, East: {east} (span: {east - west}°)")

    # CAMS gridded data updates yearly with ~6 month lag
    # Check if requesting very recent data
    today = date.today()
    max_available_date = date(today.year - 1, 12, 31)  # Last complete year

    if end_date > max_available_date:
        logger.warning(f"End date {end_date} may not be available yet")
        logger.warning(f"CAMS gridded solar radiation typically lags ~6 months")
        logger.warning(f"Latest likely available: {max_available_date}")

    # Get unique years and months needed
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)

    years = sorted(list(set([d.year for d in dates])))
    months = sorted(list(set([d.month for d in dates])))

    # Prepare output path
    raw_dir = Path(settings.DATA_DIR) / "raw" / "cams_solar"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    output_path = raw_dir / f"ghi_{start_str}_{end_str}.nc"

    if output_path.exists():
        logger.info(f"Batch already downloaded: {output_path}")
        return output_path

    # Build ADS request
    # NOTE: CAMS gridded solar radiation is in Atmosphere Data Store (ADS), not CDS
    request = {
        'variable': 'all_sky_global_horizontal_irradiance',  # GHI
        'sky_type': 'observed_cloud',  # All-sky conditions (vs clear-sky)
        'year': [str(y) for y in years],
        'month': [f"{m:02d}" for m in months],
        'area': area,  # [N, W, S, E]
        'format': 'netcdf',
        'version': '4.6'  # Latest version
    }

    logger.info(f"Downloading CAMS solar radiation: {start_date} to {end_date}")
    logger.info("=" * 80)
    logger.info("ADS API REQUEST:")
    logger.info("=" * 80)

    import json
    logger.info(json.dumps(request, indent=2, default=str))

    logger.info("=" * 80)
    logger.info("REQUEST DETAILS:")
    logger.info(f"  Dataset: cams-gridded-solar-radiation")
    logger.info(f"  Variable: {request['variable']} (GHI)")
    logger.info(f"  Sky type: {request['sky_type']}")
    logger.info(f"  Years: {request['year']}")
    logger.info(f"  Months: {request['month']}")
    logger.info(f"  Area [N,W,S,E]: {request['area']}")
    logger.info(f"  Area interpretation:")
    logger.info(f"    North: {request['area'][0]}°")
    logger.info(f"    West: {request['area'][1]}°")
    logger.info(f"    South: {request['area'][2]}°")
    logger.info(f"    East: {request['area'][3]}°")
    logger.info(f"  Format: {request['format']}")
    logger.info(f"  Version: {request['version']}")
    logger.info("=" * 80)

    try:
        # ADS uses same cdsapi client but with different URL
        # Try to load credentials from .adsapirc first, fall back to .cdsapirc
        import os

        ads_rc = Path.home() / ".adsapirc"
        cds_rc = Path.home() / ".cdsapirc"

        if ads_rc.exists():
            # Use ADS-specific config
            client = cdsapi.Client(url="https://ads.atmosphere.copernicus.eu/api")
            logger.info("Using ADS credentials from ~/.adsapirc")
        elif cds_rc.exists():
            # Try using CDS credentials with ADS URL (sometimes works)
            client = cdsapi.Client(
                url="https://ads.atmosphere.copernicus.eu/api",
                key=None,  # Will try to load from .cdsapirc
                verify=True
            )
            logger.info("Using CDS credentials from ~/.cdsapirc with ADS URL")
        else:
            raise ValueError("No API credentials found. Create ~/.adsapirc or ~/.cdsapirc")

        logger.info("Submitting request to ADS...")
        result = client.retrieve("cams-gridded-solar-radiation", request)
        result.download(str(output_path))
        logger.info(f"✓ CAMS solar radiation downloaded: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"✗ Download failed: {e}")
        if output_path.exists():
            output_path.unlink()
        raise


@task
def process_cams_solar_to_geotiff(
    netcdf_path: Path,
    bbox: tuple,
    dates_to_process: Optional[List[date]] = None
) -> List[Path]:
    """
    Convert CAMS solar radiation NetCDF (15-min resolution) to daily GeoTIFFs.

    Aggregates 15-minute GHI values to daily totals in kWh/m²/day.
    Only processes dates specified in dates_to_process (if provided).

    Args:
        netcdf_path: Path to downloaded CAMS NetCDF file
        bbox: Bounding box (W, S, E, N) for clipping
        dates_to_process: Optional list of specific dates to process

    Returns:
        List of created GeoTIFF file paths
    """
    logger = get_run_logger()
    settings = get_settings()

    output_dir = Path(settings.DATA_DIR) / "ghi"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving GHI to: {output_dir}")

    if dates_to_process:
        logger.info(f"Processing only {len(dates_to_process)} specific dates")

    processed_paths = []

    try:
        ds = xr.open_dataset(netcdf_path)
        logger.info(f"NetCDF variables: {list(ds.data_vars)}")
        logger.info(f"NetCDF dimensions: {dict(ds.dims)}")
        logger.info(f"NetCDF coordinates: {list(ds.coords)}")

        # Find GHI variable (may have different names)
        var_name = None
        possible_names = ['GHI', 'ghi', 'global_horizontal_irradiance', 'ssrd', 'irradiance']
        for name in possible_names:
            if name in ds.data_vars:
                var_name = name
                break

        if not var_name:
            # Try to find any variable with 'irrad' or 'ghi' in name
            for v in ds.data_vars:
                if 'ghi' in v.lower() or 'irrad' in v.lower():
                    var_name = v
                    break

        if not var_name:
            raise ValueError(f"GHI variable not found. Available: {list(ds.data_vars)}")

        logger.info(f"Using variable: {var_name}")
        da = ds[var_name]

        # Check units and convert if needed
        units = da.attrs.get('units', 'unknown')
        logger.info(f"Variable units: {units}")

        # CAMS provides Wh/m² integrated over 15 minutes
        # We need to aggregate to daily totals in kWh/m²/day

        # Resample to daily sums
        logger.info("Aggregating 15-minute data to daily totals...")

        # Group by date and sum
        daily_da = da.resample(time='1D').sum(dim='time')

        # Convert from Wh/m² to kWh/m²
        daily_da = daily_da / 1000.0
        daily_da.attrs['units'] = 'kWh/m²/day'
        daily_da.attrs['long_name'] = 'Daily total global horizontal irradiance'

        # Clip to bbox if needed
        try:
            west, south, east, north = bbox
            # Rename coordinates if needed
            if 'longitude' in daily_da.dims and 'latitude' in daily_da.dims:
                daily_da = daily_da.sel(
                    longitude=slice(west, east),
                    latitude=slice(north, south)
                )
            elif 'lon' in daily_da.dims and 'lat' in daily_da.dims:
                daily_da = daily_da.sel(
                    lon=slice(west, east),
                    lat=slice(north, south)
                )
            logger.info(f"Clipped to bbox: {bbox}")
        except Exception as e:
            logger.warning(f"Could not clip to bbox: {e}")

        # Ensure CRS is set
        if 'longitude' in daily_da.dims or 'lon' in daily_da.dims:
            daily_da = daily_da.rio.write_crs("EPSG:4326")

        # Process each day
        time_values = daily_da.time.values
        logger.info(f"Processing {len(time_values)} days")

        for time_val in time_values:
            day_data = daily_da.sel(time=time_val)
            day_date = pd.Timestamp(time_val).date()

            # Skip if not in dates_to_process (if specified)
            if dates_to_process and day_date not in dates_to_process:
                logger.debug(f"Skipping {day_date} (already exists)")
                continue

            # Prepare for rasterio export
            # Rename coordinates to x/y for rioxarray
            coord_mapping = {}
            for coord in day_data.dims:
                coord_lower = coord.lower()
                if coord_lower in ['longitude', 'lon', 'long']:
                    coord_mapping[coord] = 'x'
                elif coord_lower in ['latitude', 'lat']:
                    coord_mapping[coord] = 'y'

            if coord_mapping:
                day_data = day_data.rename(coord_mapping)

            # Ensure CRS
            day_data = day_data.rio.write_crs("EPSG:4326")

            output_path = output_dir / f"ghi_{day_date.strftime('%Y%m%d')}.tif"

            day_data.rio.to_raster(output_path, driver="COG", compress="LZW")
            processed_paths.append(output_path)
            logger.info(f"✓ Processed: {day_date} -> {output_path.name}")

        logger.info(f"✓ Successfully processed {len(processed_paths)} days")
        return processed_paths

    except Exception as e:
        logger.error(f"✗ Failed to process: {e}")
        raise


@task(retries=3, retry_delay_seconds=30)
def append_to_yearly_historical(
    source_netcdf: Path,
    bbox: tuple,
    dates_to_append: Optional[List[date]] = None
) -> List[Path]:
    """
    Append processed daily GHI data to YEARLY historical NetCDF files.
    Creates separate files for each year: ghi_2024.nc, ghi_2025.nc, etc.

    Aggregates 15-minute CAMS data to daily totals and stores in yearly files.

    FUSE FILESYSTEM FIX: Writes to /tmp first, then copies to final location.
    """
    logger = get_run_logger()
    settings = get_settings()
    import tempfile
    import shutil
    import os
    from collections import defaultdict

    hist_dir = Path(settings.DATA_DIR) / "ghi_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"📦 Appending data from {source_netcdf.name} to yearly historical files")

    if dates_to_append:
        logger.info(f"  Processing {len(dates_to_append)} specific dates")
    else:
        logger.info(f"  Processing all dates in source file")

    updated_files = []

    try:
        # Open source NetCDF
        ds = xr.open_dataset(source_netcdf)
        logger.info(f"  Source variables: {list(ds.data_vars)}")

        # Find GHI variable
        var_name = None
        possible_names = ['GHI', 'ghi', 'global_horizontal_irradiance', 'ssrd', 'irradiance']
        for name in possible_names:
            if name in ds.data_vars:
                var_name = name
                break

        if not var_name:
            for v in ds.data_vars:
                if 'ghi' in v.lower() or 'irrad' in v.lower():
                    var_name = v
                    break

        if not var_name:
            raise ValueError(f"GHI variable not found. Available: {list(ds.data_vars)}")

        da = ds[var_name]

        # Aggregate 15-minute to daily totals
        logger.info("  Aggregating 15-minute data to daily totals...")
        daily_da = da.resample(time='1D').sum(dim='time')

        # Convert from Wh/m² to kWh/m²
        daily_da = daily_da / 1000.0

        # Standardize variable name and attributes
        daily_da.name = 'ghi'
        daily_da.attrs.update({
            'long_name': 'Daily total global horizontal irradiance',
            'units': 'kWh/m²/day',
            'source': 'CAMS gridded solar radiation',
            'aggregation': 'daily sum from 15-minute data'
        })

        # Standardize spatial dimensions
        coord_mapping = {}
        for coord in daily_da.dims:
            coord_lower = coord.lower()
            if coord_lower in ['longitude', 'lon', 'long']:
                coord_mapping[coord] = 'longitude'
            elif coord_lower in ['latitude', 'lat']:
                coord_mapping[coord] = 'latitude'
        if coord_mapping:
            daily_da = daily_da.rename(coord_mapping)

        # Clip to bbox
        if isinstance(bbox, list):
            bbox = (bbox[1], bbox[2], bbox[3], bbox[0])
        try:
            west, south, east, north = bbox
            daily_da = daily_da.sel(longitude=slice(west, east), latitude=slice(north, south))
            logger.info(f"  Clipped to bbox: {bbox}")
        except Exception as e:
            logger.warning(f"  Could not clip to bbox: {e}")

        # Get and filter dates
        all_dates = set(pd.to_datetime(daily_da.time.values).date)
        if dates_to_append:
            all_dates = all_dates & set(dates_to_append)
            dates_to_keep = set(all_dates)
            time_mask = [pd.Timestamp(t).date() in dates_to_keep for t in daily_da.time.values]
            daily_da = daily_da.isel(time=time_mask)

        logger.info(f"  Processing {len(all_dates)} dates")

        # Group dates by year
        dates_by_year = defaultdict(list)
        for d in all_dates:
            dates_by_year[d.year].append(d)

        logger.info(f"  Dates span {len(dates_by_year)} year(s): {sorted(dates_by_year.keys())}")

        # Process each year
        for year, year_dates in sorted(dates_by_year.items()):
            logger.info(f"\n  📅 Processing year {year} ({len(year_dates)} dates)")

            year_file = hist_dir / f"ghi_{year}.nc"

            # FUSE FIX: Create temp directory for this year
            temp_dir = Path(tempfile.mkdtemp(prefix=f"cams_solar_{year}_"))
            temp_file = temp_dir / f"ghi_{year}.nc"

            try:
                # Extract data for this year
                year_dates_set = set(year_dates)
                year_time_mask = [pd.Timestamp(t).date() in year_dates_set for t in daily_da.time.values]
                year_da = daily_da.isel(time=year_time_mask)

                # Check if yearly file already exists
                if year_file.exists():
                    logger.info(f"    Year file exists, checking for duplicates...")
                    shutil.copy2(year_file, temp_file)
                    existing = xr.open_dataset(temp_file, chunks='auto')
                    existing_da = existing['ghi']

                    existing_dates = set(pd.to_datetime(existing_da.time.values).date)
                    new_dates = set(year_dates) - existing_dates

                    if not new_dates:
                        logger.info(f"    All {len(year_dates)} dates already exist, skipping")
                        existing.close()
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        continue

                    logger.info(f"    Adding {len(new_dates)} new dates")
                    new_dates_set = set(new_dates)
                    new_dates_mask = [pd.Timestamp(t).date() in new_dates_set for t in year_da.time.values]
                    year_da_filtered = year_da.isel(time=new_dates_mask)
                    combined = xr.concat([existing_da, year_da_filtered], dim='time').sortby('time')
                    existing.close()
                else:
                    logger.info(f"    Creating new year file with {len(year_dates)} dates")
                    combined = year_da

                # Compute time range
                time_count = len(combined.time)
                if time_count > 0:
                    time_min = pd.Timestamp(combined.time.min().values).date()
                    time_max = pd.Timestamp(combined.time.max().values).date()

                # Convert to Dataset with encoding
                year_ds = combined.to_dataset()
                year_ds.attrs['year'] = year
                year_ds.attrs['source'] = 'CAMS gridded solar radiation'

                encoding = {
                    'ghi': {
                        'chunksizes': (1, 20, 20),
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

                # FUSE FIX: Write to temp, then copy
                logger.info(f"    Writing to temp file...")
                try:
                    year_ds.to_netcdf(str(temp_file), mode='w', encoding=encoding, engine='netcdf4')
                    os.sync()
                    logger.info(f"    ✓ Temp file written successfully")
                except Exception as write_error:
                    logger.error(f"    ✗ Failed to write NetCDF: {write_error}")
                    if temp_file.exists():
                        temp_file.unlink()
                    raise

                logger.info(f"    Copying to: {year_file}")
                shutil.copy2(temp_file, year_file)
                os.sync()

                # Cleanup temp
                shutil.rmtree(temp_dir, ignore_errors=True)

                updated_files.append(year_file)
                logger.info(f"    ✓ Updated {year_file.name}")
                if time_count > 0:
                    logger.info(f"      Time range: {time_min} to {time_max}")
                    logger.info(f"      Total days: {time_count}")

            except Exception as e:
                logger.error(f"    ✗ Failed to process year {year}: {e}")
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                raise

        ds.close()

        logger.info(f"\n✓ Updated {len(updated_files)} yearly file(s)")
        return updated_files

    except Exception as e:
        logger.error(f"✗ Failed to append to yearly historical: {e}")
        raise


@task
def cleanup_raw_files(netcdf_path: Path):
    """Delete raw NetCDF file after processing."""
    logger = get_run_logger()
    try:
        if netcdf_path.exists():
            netcdf_path.unlink()
            logger.info(f"✓ Cleaned up: {netcdf_path.name}")
    except Exception as e:
        logger.warning(f"Could not delete {netcdf_path}: {e}")


@flow(
    name="process-cams-solar",
    description="Download and process CAMS solar radiation (GHI) with historical archiving",
    retries=1,
    retry_delay_seconds=600
)
def cams_solar_flow(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    batch_months: int = 1  # Download 1 month at a time (CAMS provides monthly files)
):
    """
    CAMS Solar Radiation processing with historical NetCDF management.

    Downloads CAMS gridded solar radiation (GHI) and creates:
    - Daily GeoTIFF files for GeoServer mosaics
    - Yearly historical NetCDF files for API queries

    Args:
        start_date: First date to process (default: first day of last month)
        end_date: Last date to process (default: last day of last complete month)
        batch_months: Number of months to download per batch (default: 1)
    """
    logger = get_run_logger()
    settings = get_settings()

    if start_date is None or end_date is None:
        today = date.today()
        if end_date is None:
            # CAMS gridded has ~6 month lag, default to last complete year
            end_date = date(today.year - 1, 12, 31)
        if start_date is None:
            # Default to January of last year
            start_date = date(today.year - 1, 1, 1)

    logger.info(f"Processing CAMS solar radiation from {start_date} to {end_date}")
    all_processed = []

    # Check which dates are missing
    try:
        missing_info = check_missing_dates(
            start_date=start_date,
            end_date=end_date
        )
        missing_download = missing_info.get('download', [])
        missing_geotiff = missing_info.get('geotiff', [])
        missing_historical = missing_info.get('historical', [])
    except Exception as e:
        logger.error(f"Failed to check missing dates: {e}")
        return []

    if not missing_download:
        logger.info(f"✓ All data already exists for GHI")
        return []

    logger.info(f"Need to download {len(missing_download)} dates")

    # Group missing dates into monthly batches (CAMS provides monthly files)
    from calendar import monthrange

    # Get unique year-months
    year_months = sorted(list(set([(d.year, d.month) for d in missing_download])))

    logger.info(f"Organized into {len(year_months)} month(s)")

    # Process each month
    for year, month in year_months:
        # Get first and last day of this month
        _, last_day = monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)

        # Clip to requested range
        batch_start = max(month_start, start_date)
        batch_end = min(month_end, end_date)

        # Get the specific dates in this month
        month_dates = [d for d in missing_download if d.year == year and d.month == month]

        if not month_dates:
            continue

        # Which dates need GeoTIFF processing?
        geotiff_dates_in_month = [d for d in month_dates if d in missing_geotiff]

        # Which dates need historical appending?
        hist_dates_in_month = [d for d in month_dates if d in missing_historical]

        try:
            logger.info(f"\nDownloading month: {year}-{month:02d}")
            logger.info(f"  Will process {len(geotiff_dates_in_month)} GeoTIFFs")
            logger.info(f"  Will append {len(hist_dates_in_month)} to historical")

            # Download batch (full month)
            batch_path = download_cams_solar_batch(
                start_date=batch_start,
                end_date=batch_end,
                area=settings.latam_bbox_cds  # [N, W, S, E]
            )

            # Process to GeoTIFFs (only missing dates)
            if geotiff_dates_in_month:
                processed = process_cams_solar_to_geotiff(
                    netcdf_path=batch_path,
                    bbox=settings.latam_bbox_raster,
                    dates_to_process=geotiff_dates_in_month
                )
                all_processed.extend(processed)
            else:
                logger.info("  Skipping GeoTIFF processing (all exist)")

            # Append to yearly historical NetCDF (only missing dates)
            if hist_dates_in_month:
                yearly_files = append_to_yearly_historical(
                    source_netcdf=batch_path,
                    bbox=settings.latam_bbox_raster,
                    dates_to_append=hist_dates_in_month
                )
                logger.info(f"✓ Updated {len(yearly_files)} yearly historical file(s)")
            else:
                logger.info("  Skipping historical append (all exist)")

            # Clean up raw file
            cleanup_raw_files(batch_path)

            logger.info(f"✓ Completed month: {year}-{month:02d}")

        except Exception as e:
            logger.error(f"✗ Failed month {year}-{month:02d}: {e}")

    # Refresh GeoServer mosaics
    if all_processed:
        from .tasks import refresh_mosaic_shapefile
        from .schemas import DataSource

        logger.info(f"\n{'='*80}")
        logger.info("Refreshing GeoServer mosaics")
        logger.info(f"Processed {len(all_processed)} GeoTIFF files")

        try:
            # TODO: Add GHI to DataSource enum
            # For now, we'll just log
            logger.info("Note: Add DataSource.GHI to schemas.py to enable mosaic refresh")
            # refresh_mosaic_shapefile(DataSource.GHI)
        except Exception as e:
            logger.error(f"Failed to refresh mosaic: {e}")

        logger.info(f"\n✓ Successfully processed {len(all_processed)} total files")

    return all_processed
