"""
CAMS Global Radiation Flow - Download from Atmosphere Data Store

Downloads CAMS global radiation data (solar radiation from satellite observations)
and processes it into:
1. Daily GeoTIFF files for GeoServer time-enabled mosaics
2. Yearly historical NetCDF files for fast API queries

Data Source: CAMS global radiation (satellite-based)
Dataset: cams-global-radiation
URL: https://ads.atmosphere.copernicus.eu/datasets/cams-global-radiation

Variables available:
- global_horizontal_irradiance (GHI)
- direct_normal_irradiance (DNI)
- beam_horizontal_irradiance (BHI)
- diffuse_horizontal_irradiance (DHI)

Characteristics:
- Spatial Resolution: 0.05° x 0.05° (~5.5 km)
- Temporal Resolution: 1-minute, 15-minute, hourly, daily, monthly
- Period: 2004-02-01 to present (~2-3 days lag)
- Coverage: Global (-66° to 66° latitude)
- Accuracy: Better than ERA5 for solar applications
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
import subprocess


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
    geotiff_dir = Path(settings.DATA_DIR) / "cams_ghi"
    hist_dir = Path(settings.DATA_DIR) / "cams_ghi_hist"

    # Check GeoTIFF files
    existing_geotiff_dates = set()
    if geotiff_dir.exists():
        for tif_file in geotiff_dir.glob("cams_ghi_*.tif"):
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
        for year_file in hist_dir.glob("cams_ghi_*.nc"):
            try:
                ds = xr.open_dataset(year_file, chunks='auto')
                if 'cams_ghi' in ds.data_vars:
                    file_dates = set(pd.to_datetime(ds['cams_ghi'].time.values).date)
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


@task(retries=2, retry_delay_seconds=600, timeout_seconds=7200)
def download_cams_radiation_batch(
    start_date: date,
    end_date: date
) -> Path:
    """
    Download CAMS global radiation data for a date range.

    Uses the cams-global-radiation dataset from ADS which provides
    satellite-based solar radiation estimates.
    """
    logger = get_run_logger()
    settings = get_settings()

    raw_dir = Path(settings.DATA_DIR) / "raw" / "cams_radiation"
    raw_dir.mkdir(parents=True, exist_ok=True)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    output_path = raw_dir / f"cams_ghi_{start_str}_{end_str}.nc"

    if output_path.exists():
        logger.info(f"Batch already downloaded: {output_path}")
        return output_path

    # Generate date list
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # Get unique time components
    years = sorted(list(set([d.split('-')[0] for d in dates])))
    months = sorted(list(set([d.split('-')[1] for d in dates])))
    days = sorted(list(set([d.split('-')[2] for d in dates])))

    # CAMS dataset has specific time_step options
    # For daily totals, we use 'day' which gives integrated daily values
    request = {
        'sky_type': 'all_sky',  # All-sky conditions (realistic)
        'irradiation': 'global_horizontal_irradiance',  # GHI
        'time_step': 'day',  # Daily integrated values
        'year': years,
        'month': months,
        'day': days,
        'area': [
            settings.latam_bbox_cds[0],  # North
            settings.latam_bbox_cds[1],  # West
            settings.latam_bbox_cds[2],  # South
            settings.latam_bbox_cds[3],  # East
        ],
        'format': 'netcdf',
    }

    logger.info(f"Downloading CAMS global radiation: {start_date} to {end_date}")
    logger.info("=" * 80)
    logger.info("ADS REQUEST:")
    logger.info(f"  Dataset: cams-global-radiation")
    logger.info(f"  Variable: {request['irradiation']}")
    logger.info(f"  Sky type: {request['sky_type']}")
    logger.info(f"  Time step: {request['time_step']}")
    logger.info(f"  Years: {years}")
    logger.info(f"  Months: {months}")
    logger.info(f"  Days: {len(days)} days")
    logger.info(f"  Area [N,W,S,E]: {request['area']}")
    logger.info("=" * 80)

    try:
        # Use ADS client
        client = cdsapi.Client(url='https://ads.atmosphere.copernicus.eu/api')
        logger.info("Submitting request to ADS...")

        client.retrieve('cams-gridded-solar-radiation', request, str(output_path))

        file_size_mb = output_path.stat().st_size / 1024 / 1024
        logger.info(f"✓ Downloaded: {output_path.name} ({file_size_mb:.2f} MB)")
        return output_path

    except Exception as e:
        logger.error(f"Download failed: {e}")
        if output_path.exists():
            output_path.unlink()
        raise


@task
def process_cams_to_geotiff(
    nc_path: Path,
    dates_to_process: List[date]
) -> List[Path]:
    """
    Process CAMS NetCDF to daily GeoTIFF files.

    CAMS daily data comes in Wh/m² and we convert to kWh/m²/day
    """
    logger = get_run_logger()
    settings = get_settings()

    output_dir = Path(settings.DATA_DIR) / "cams_ghi"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load the CAMS data
    ds = xr.open_dataset(nc_path)
    logger.info(f"Loaded CAMS data: {ds.dims}")
    logger.info(f"Variables: {list(ds.data_vars)}")
    logger.info(f"Coordinates: {list(ds.coords)}")

    # Identify GHI variable (names vary: GHI, global_irradiance, etc.)
    ghi_var = None
    for var in ds.data_vars:
        if 'global' in var.lower() or 'ghi' in var.lower():
            ghi_var = var
            break

    if ghi_var is None:
        raise ValueError(f"Could not find GHI variable in {list(ds.data_vars)}")

    logger.info(f"Using GHI variable: {ghi_var}")

    # Convert to xarray DataArray if needed
    data = ds[ghi_var]

    # Set CRS
    data = data.rio.write_crs("EPSG:4326")

    # Apply Brazil shapefile clip if available
    shapefile = Path("/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp")

    output_paths = []
    dates_set = set(dates_to_process)

    for time_idx in range(len(data.time)):
        time_val = pd.Timestamp(data.time.values[time_idx])
        day_date = time_val.date()

        if day_date not in dates_set:
            continue

        daily_data = data.isel(time=time_idx)

        # Convert Wh/m² to kWh/m²/day
        # CAMS daily integrated values are in Wh/m²
        daily_data = daily_data / 1000.0  # Wh to kWh
        daily_data.attrs['units'] = 'kWh/m2/day'
        daily_data.attrs['long_name'] = 'Global Horizontal Irradiance'

        output_path = output_dir / f"cams_ghi_{day_date.strftime('%Y%m%d')}.tif"

        # Write to temporary file first
        temp_output = output_path.parent / f"{output_path.stem}_temp.tif"
        daily_data.rio.to_raster(temp_output, driver="COG", compress="LZW")

        # Clip with Brazil shapefile if it exists (preserves grid alignment)
        if shapefile.exists():
            try:
                result = subprocess.run([
                    "gdalwarp",
                    "-q",
                    "-cutline", str(shapefile),
                    "-dstnodata", "nan",
                    "-overwrite",
                    str(temp_output),
                    str(output_path)
                ], capture_output=True, text=True, timeout=30, check=True)
                temp_output.unlink()
                logger.info(f"✓ Processed & clipped: {day_date}")
            except Exception as e:
                logger.warning(f"Shapefile clipping failed, using original: {e}")
                if temp_output.exists():
                    temp_output.rename(output_path)
        else:
            temp_output.rename(output_path)
            logger.info(f"✓ Processed: {day_date}")

        output_paths.append(output_path)

    ds.close()
    logger.info(f"✓ Created {len(output_paths)} GeoTIFF files")
    return output_paths


@task
def append_to_yearly_netcdf(
    nc_path: Path,
    dates_to_append: List[date]
) -> Dict[int, Path]:
    """
    Append CAMS data to yearly historical NetCDF files.

    Organizes data by year: cams_ghi_2023.nc, cams_ghi_2024.nc, etc.
    """
    logger = get_run_logger()
    settings = get_settings()

    hist_dir = Path(settings.DATA_DIR) / "cams_ghi_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    # Load source data
    ds_source = xr.open_dataset(nc_path)

    # Find GHI variable
    ghi_var = None
    for var in ds_source.data_vars:
        if 'global' in var.lower() or 'ghi' in var.lower():
            ghi_var = var
            break

    if ghi_var is None:
        raise ValueError(f"Could not find GHI variable")

    data_source = ds_source[ghi_var]

    # Convert Wh/m² to kWh/m²/day
    data_source = data_source / 1000.0
    data_source.attrs['units'] = 'kWh/m2/day'
    data_source.attrs['long_name'] = 'Global Horizontal Irradiance (CAMS)'

    # Rename variable to cams_ghi
    data_source.name = 'cams_ghi'

    # Group dates by year
    dates_by_year = {}
    for d in dates_to_append:
        year = d.year
        if year not in dates_by_year:
            dates_by_year[year] = []
        dates_by_year[year].append(d)

    updated_files = {}

    for year, year_dates in dates_by_year.items():
        year_file = hist_dir / f"cams_ghi_{year}.nc"

        # Filter source data for this year
        year_data = data_source.sel(
            time=slice(f"{year}-01-01", f"{year}-12-31")
        )

        if len(year_data.time) == 0:
            logger.warning(f"No data for year {year}, skipping")
            continue

        if year_file.exists():
            # Append to existing file
            logger.info(f"Appending to existing: {year_file.name}")
            ds_existing = xr.open_dataset(year_file, chunks='auto')

            # Combine and remove duplicates
            ds_combined = xr.concat([ds_existing, year_data], dim='time')
            _, unique_indices = np.unique(ds_combined.time.values, return_index=True)
            ds_combined = ds_combined.isel(time=sorted(unique_indices))

            ds_existing.close()
        else:
            # Create new file
            logger.info(f"Creating new: {year_file.name}")
            ds_combined = year_data

        # Sort by time
        ds_combined = ds_combined.sortby('time')

        # Save with compression
        encoding = {
            'cams_ghi': {
                'dtype': 'float32',
                'zlib': True,
                'complevel': 4,
                'chunksizes': (1, 20, 20)
            }
        }

        ds_combined.to_netcdf(year_file, encoding=encoding, engine='netcdf4')
        logger.info(f"✓ Saved {year_file.name} ({len(ds_combined.time)} dates)")

        updated_files[year] = year_file

    ds_source.close()
    return updated_files


@flow(name="cams-radiation-flow")
def cams_radiation_flow(
    start_date: date,
    end_date: date,
    batch_days: int = 30
) -> Dict:
    """
    Main flow to download and process CAMS global radiation data.

    Args:
        start_date: First date to process
        end_date: Last date to process
        batch_days: Number of days to download per batch (default: 30)
    """
    logger = get_run_logger()

    # Check what's missing
    missing_info = check_missing_dates(start_date, end_date)

    if not missing_info['download']:
        logger.info("✓ All dates already processed!")
        return {'status': 'complete', 'files_created': 0}

    # Process in batches
    batch_start = min(missing_info['download'])
    final_end = max(missing_info['download'])

    total_geotiffs = []

    while batch_start <= final_end:
        batch_end = min(batch_start + timedelta(days=batch_days - 1), final_end)

        logger.info(f"Processing batch: {batch_start} to {batch_end}")

        # Download
        nc_path = download_cams_radiation_batch(batch_start, batch_end)

        # Determine which dates from this batch to process
        batch_dates = []
        current = batch_start
        while current <= batch_end:
            batch_dates.append(current)
            current += timedelta(days=1)

        geotiff_dates = [d for d in batch_dates if d in missing_info['geotiff']]
        hist_dates = [d for d in batch_dates if d in missing_info['historical']]

        # Process to GeoTIFF
        if geotiff_dates:
            geotiff_paths = process_cams_to_geotiff(nc_path, geotiff_dates)
            total_geotiffs.extend(geotiff_paths)

        # Append to historical NetCDF
        if hist_dates:
            yearly_files = append_to_yearly_netcdf(nc_path, hist_dates)

        # Cleanup raw file
        if nc_path.exists():
            nc_path.unlink()
            logger.info(f"Cleaned up: {nc_path.name}")

        batch_start = batch_end + timedelta(days=1)

    logger.info("=" * 80)
    logger.info(f"✓ CAMS Radiation Flow Complete")
    logger.info(f"✓ Created {len(total_geotiffs)} GeoTIFF files")
    logger.info("=" * 80)

    return {
        'status': 'success',
        'files_created': len(total_geotiffs),
        'date_range': f"{start_date} to {end_date}"
    }
