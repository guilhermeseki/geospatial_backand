from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from prefect import flow, get_run_logger
from pathlib import Path
from .tasks import (
    check_data_availability,
    download_data,
    process_data,
    validate_output,
    refresh_mosaic_shapefile
)
from .schemas import DataSource
from app.config.settings import get_settings
import cdsapi
import pandas as pd
import xarray as xr
import rioxarray
import numpy as np
import shutil
import tempfile



"""
Alerting: Integrate Prefect notifications (e.g., Slack, email) for persistent failures:
from prefect.blocks.notifications import SlackWebhook

@flow(..., on_failure=[SlackWebhook.notify])
def merge_daily_flow(...):
    ...
"""
@flow(
    name="process-chirps-daily",
    description="Daily check and download of CHIRPS precipitation data for all missing days in the previous year until the last month",
    retries=2,
    retry_delay_seconds=300,
)
def chirps_daily_flow(
    source: DataSource = DataSource.CHIRPS,
    start_date: date = None,
    end_date: date = None
):
    logger = get_run_logger()
    settings = get_settings()
    processed_paths = []
    raw_dir = Path(settings.DATA_DIR) / "raw"
    mosaic_dir = Path(settings.DATA_DIR) / source.value
    # Setup mosaic store
    #setup_mosaic.submit(mosaic_dir, source).result()
    # Define date range - OPERATIONAL: Check only last 30 days (unless overridden)
    today = date.today()
    if start_date is None:
        start_date = today - timedelta(days=30)
    if end_date is None:
        end_date = today - timedelta(days=1)  # Yesterday

    logger.info(f"Processing date range: {start_date} to {end_date}")
    current_date = start_date

    while current_date <= end_date:
        output_path = mosaic_dir / f"{source.value}_{current_date.strftime('%Y%m%d')}.tif"
        if output_path.exists():
            logger.info(f"File already exists locally: {output_path}, skipping download and processing")
        else:
            is_available = check_data_availability.submit(current_date, source).result()
            if is_available:
                raw_path = download_data.submit(current_date, source).result()
                processed_path = process_data.submit(
                    raw_path, current_date, source, bbox=settings.latam_bbox_raster
                ).result()
                if validate_output.submit(processed_path).result():
                    processed_paths.append(processed_path)
            else:
                logger.warning(f"Data not available for {current_date}, skipping")
        current_date += timedelta(days=1)

    refresh_mosaic_shapefile.submit(source).result()

    return processed_paths if processed_paths else None

@flow(
    name="process-merge-daily",
    description="Daily check and download of MERGE precipitation data for all missing days in the previous year until the last month",
    retries=2,
    retry_delay_seconds=300,
)
def merge_daily_flow(
    source: DataSource = DataSource.MERGE,
    start_date: date = None,
    end_date: date = None
):
    logger = get_run_logger()
    settings = get_settings()
    processed_paths = []
    raw_dir = Path(settings.DATA_DIR) / "raw"
    mosaic_dir = Path(settings.DATA_DIR) / source.value
    # Setup mosaic store
    #setup_mosaic.submit(mosaic_dir, source).result()
    # Define date range - OPERATIONAL: Check only last 30 days (unless overridden)
    today = date.today()
    if start_date is None:
        start_date = today - timedelta(days=30)  # 30 days ago
    if end_date is None:
        end_date = today - timedelta(days=1)     # Yesterday (1-2 day lag)

    logger.info(f"Processing date range: {start_date} to {end_date}")
    current_date = start_date
    while current_date <= end_date:
        output_path = mosaic_dir / f"{source.value}_{current_date.strftime('%Y%m%d')}.tif"
        if output_path.exists():
            logger.info(f"File already exists locally: {output_path}, skipping download and processing")
        else:
            #is_available = check_data_availability.submit(current_date, source).result()
            is_available = True
            if is_available:
                raw_path = download_data.submit(current_date, source).result()
                processed_path = process_data.submit(
                    raw_path, current_date, source, bbox=settings.latam_bbox_raster
                ).result()
                if validate_output.submit(processed_path).result():
                    processed_paths.append(processed_path)
            else:
                logger.warning(f"Data not available for {current_date}, skipping")

        current_date += timedelta(days=1)
    # Reindex mosaic
    #recalculate_time.submit(mosaic_dir, source).result()
    refresh_mosaic_shapefile.submit(source).result()

    return processed_paths if processed_paths else None


@flow(
    name="build-precipitation-yearly-historical",
    description="Build yearly historical NetCDF files from existing GeoTIFF files",
    retries=1
)
def build_precipitation_yearly_historical(
    source: DataSource,
    start_year: int | None = None,
    end_year: int | None = None,
    clip_geojson: str | None = None
):
    """
    Create yearly historical NetCDF files from existing GeoTIFF mosaics.
    This is a one-time operation to backfill historical data.

    Args:
        source: Data source (CHIRPS or MERGE)
        start_year: Start year for processing
        end_year: End year for processing
        clip_geojson: Path to GeoJSON file for clipping (optional)
    """
    logger = get_run_logger()
    settings = get_settings()
    import pandas as pd
    import rioxarray
    import tempfile
    import shutil
    from collections import defaultdict
    import geopandas as gpd

    # Get directories
    geotiff_dir = Path(settings.DATA_DIR) / source.value
    hist_dir = Path(settings.DATA_DIR) / f"{source.value}_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)

    if not geotiff_dir.exists():
        logger.error(f"GeoTIFF directory does not exist: {geotiff_dir}")
        return []

    logger.info("=" * 80)
    logger.info(f"BUILDING YEARLY HISTORICAL FOR {source.value.upper()}")
    logger.info("=" * 80)

    # Load clipping geometry if provided
    clip_geometry = None
    if clip_geojson:
        try:
            gdf = gpd.read_file(clip_geojson)
            clip_geometry = gdf.geometry.unary_union
            logger.info(f"Loaded clipping geometry from: {clip_geojson}")
            logger.info(f"  Geometry type: {clip_geometry.geom_type}")
            logger.info(f"  Bounds: {clip_geometry.bounds}")
        except Exception as e:
            logger.warning(f"Could not load clipping geometry: {e}")
            logger.warning("Proceeding without clipping")
            clip_geometry = None

    # Find all GeoTIFF files
    geotiff_files = sorted(geotiff_dir.glob(f"{source.value}_*.tif"))
    logger.info(f"Found {len(geotiff_files)} GeoTIFF files")

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

        year_file = hist_dir / f"{source.value}_{year}.nc"

        if year_file.exists():
            logger.info(f"  Year file already exists: {year_file.name}, skipping")
            continue

        # FUSE FIX: Create temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{source.value}_{year}_"))
        temp_file = temp_dir / f"{source.value}_{year}.nc"

        try:
            # Load all GeoTIFFs for this year
            data_arrays = []
            time_coords = []

            # Load first file to get reference coordinates
            first_file_date, first_tif = year_files[0]
            ref_da = rioxarray.open_rasterio(first_tif, masked=True).squeeze()
            if 'band' in ref_da.dims:
                ref_da = ref_da.isel(band=0)
            ref_x = ref_da.x.values
            ref_y = ref_da.y.values

            for file_date, tif_file in year_files:
                try:
                    da = rioxarray.open_rasterio(tif_file, masked=True).squeeze()
                    # Remove band dimension if present
                    if 'band' in da.dims:
                        da = da.isel(band=0)

                    # FIX: Assign reference coordinates to all arrays to ensure perfect alignment
                    # This prevents tiny floating-point differences from creating union grids
                    if 'x' in da.coords and 'y' in da.coords:
                        da = da.assign_coords(x=ref_x, y=ref_y)

                    data_arrays.append(da)
                    time_coords.append(pd.Timestamp(file_date))
                except Exception as e:
                    logger.warning(f"  Could not load {tif_file.name}: {e}")
                    continue

            if not data_arrays:
                logger.warning(f"  No valid data for year {year}, skipping")
                continue

            logger.info(f"  Loaded {len(data_arrays)} files into memory")

            # Stack along time dimension
            # Use join='exact' since all arrays now have identical coordinates (assigned from first file)
            combined = xr.concat(data_arrays, dim='time', join='exact', combine_attrs='override')
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

            # Clip to geometry if provided
            if clip_geometry is not None:
                logger.info(f"  Clipping to geometry...")
                original_size = combined.sizes
                combined = combined.rio.write_crs("EPSG:4326")
                combined = combined.rio.clip([clip_geometry], crs="EPSG:4326", drop=True, all_touched=True)
                clipped_size = combined.sizes
                logger.info(f"    Original: {original_size.get('longitude', 'N/A')} x {original_size.get('latitude', 'N/A')}")
                logger.info(f"    Clipped: {clipped_size.get('longitude', 'N/A')} x {clipped_size.get('latitude', 'N/A')}")
                reduction = (1 - (clipped_size.get('longitude', 1) * clipped_size.get('latitude', 1)) /
                            (original_size.get('longitude', 1) * original_size.get('latitude', 1))) * 100
                logger.info(f"    Size reduction: {reduction:.1f}%")

            # Create dataset
            var_name = 'precip'
            ds = combined.to_dataset(name=var_name)
            ds.attrs['source'] = source.value
            ds.attrs['year'] = year
            ds.attrs['units'] = 'mm/day'

            # Encoding
            encoding = {
                var_name: {
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

            # Write to temp file
            logger.info(f"  Writing to temp file...")
            ds.to_netcdf(str(temp_file), mode='w', encoding=encoding, engine='netcdf4')

            # Copy to final location
            logger.info(f"  Copying to: {year_file}")
            shutil.copy2(temp_file, year_file)

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

            updated_files.append(year_file)
            logger.info(f"  ✓ Created {year_file.name}")
            logger.info(f"    Time range: {time_coords[0].date()} to {time_coords[-1].date()}")
            logger.info(f"    Total days: {len(time_coords)}")

        except Exception as e:
            logger.error(f"  ✗ Failed to process year {year}: {e}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            continue

    logger.info(f"\n✓ Created {len(updated_files)} yearly file(s)")
    return updated_files


@flow(
    name="process-precipitation-batch",
    description="Modernized batch processing for CHIRPS/MERGE with yearly historical files",
    retries=2
)
def precipitation_batch_flow(
    source: DataSource,
    start_date: date = None,
    end_date: date = None,
    create_historical: bool = True
):
    """
    Modern precipitation flow with ERA5-like architecture.
    - Batch processing
    - Checks existing files
    - Creates yearly historical NetCDF
    """
    logger = get_run_logger()
    settings = get_settings()

    # Default: yesterday
    if not end_date:
        end_date = date.today() - timedelta(days=1)
    if not start_date:
        # For CHIRPS: start from 2015 or existing files
        # For MERGE: start from 2014 or existing files
        start_date = end_date - timedelta(days=30)  # Default: last 30 days

    logger.info("=" * 80)
    logger.info(f"{source.value.upper()} PRECIPITATION PROCESSING")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Create historical: {create_historical}")

    # Check what files already exist
    mosaic_dir = Path(settings.DATA_DIR) / source.value
    mosaic_dir.mkdir(parents=True, exist_ok=True)

    existing_dates = set()
    for tif_file in mosaic_dir.glob(f"{source.value}_*.tif"):
        try:
            date_str = tif_file.stem.split('_')[-1]
            existing_dates.add(pd.to_datetime(date_str, format='%Y%m%d').date())
        except:
            pass

    logger.info(f"Found {len(existing_dates)} existing GeoTIFF files")

    # Determine what needs downloading
    current = start_date
    missing_dates = []
    while current <= end_date:
        if current not in existing_dates:
            missing_dates.append(current)
        current += timedelta(days=1)

    logger.info(f"Need to download: {len(missing_dates)} dates")

    if not missing_dates:
        logger.info("✓ All data already exists")
        if create_historical:
            logger.info("Creating yearly historical files from existing data...")
            return build_precipitation_yearly_historical(source)
        return []

    # Download missing dates
    processed_paths = []
    for missing_date in missing_dates:
        try:
            is_available = check_data_availability.submit(missing_date, source).result()
            if is_available:
                raw_path = download_data.submit(missing_date, source).result()
                processed_path = process_data.submit(
                    raw_path, missing_date, source, bbox=settings.latam_bbox_raster
                ).result()
                if validate_output.submit(processed_path).result():
                    processed_paths.append(processed_path)
                    logger.info(f"✓ Processed: {missing_date}")
            else:
                logger.warning(f"Data not available for {missing_date}")
        except Exception as e:
            logger.error(f"Failed to process {missing_date}: {e}")

    # Refresh mosaic
    if processed_paths:
        refresh_mosaic_shapefile.submit(source).result()
        logger.info(f"✓ Processed {len(processed_paths)} new files")

    # Create yearly historical files
    if create_historical and processed_paths:
        logger.info("\nCreating yearly historical files...")
        # Get years from processed files
        years = set()
        for p in processed_paths:
            date_str = p.stem.split('_')[-1]
            file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
            years.add(file_date.year)

        for year in sorted(years):
            build_precipitation_yearly_historical(source, start_year=year, end_year=year)

    return processed_paths

