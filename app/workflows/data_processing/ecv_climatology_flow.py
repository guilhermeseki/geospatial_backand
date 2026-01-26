"""
ECV (Essential Climate Variables) Monthly Climatology Flow - Copernicus CDS
Downloads monthly climatology data (1991-2020 reference period) for Brazil.

Dataset: ecv-for-climate-change
Available variables:
- surface_air_temperature
- surface_air_relative_humidity
- volumetric_soil_moisture_for_0_to_7cm_layer
- precipitation
- sea_ice_cover (not relevant for Brazil)

Product types:
- climatology: Long-term monthly means for reference period
- monthly_mean: Actual monthly values
- anomaly: Deviations from climatology

Origins:
- era5: 0.25° × 0.25° resolution
- era5_land: 0.1° × 0.1° resolution
"""
from datetime import date
from pathlib import Path
from typing import List, Dict, Optional
import cdsapi
import xarray as xr
import rioxarray
import numpy as np
from prefect import flow, task, get_run_logger
from app.config.settings import get_settings
import geopandas as gpd


# ECV variable mapping: CDS variable name -> output directory name
ECV_VARIABLE_MAPPING = {
    "surface_air_temperature": "ecv_temp",
    "surface_air_relative_humidity": "ecv_humidity",
    "volumetric_soil_moisture_for_0_to_7cm_layer": "ecv_soil_moisture",
    "precipitation": "ecv_precipitation",
}

# Available origins (data sources)
ECV_ORIGINS = ["era5", "era5_land"]

# Available product types
ECV_PRODUCT_TYPES = ["climatology", "monthly_mean", "anomaly"]

# Climate reference periods
ECV_REFERENCE_PERIODS = ["1981_2010", "1991_2020"]


@task
def check_existing_files(
    variable: str,
    origin: str,
    product_type: str,
    reference_period: str
) -> Dict[str, bool]:
    """
    Check which ECV climatology files already exist.

    Returns:
        Dictionary with file existence information
    """
    logger = get_run_logger()
    settings = get_settings()

    dir_name = ECV_VARIABLE_MAPPING.get(variable)
    if not dir_name:
        raise ValueError(f"Unknown variable: {variable}")

    # Construct directory structure: ecv_temp/era5/climatology_1991_2020/
    origin_short = origin
    product_short = product_type
    ref_short = reference_period

    geotiff_dir = Path(settings.DATA_DIR) / dir_name / origin_short / f"{product_short}_{ref_short}"
    netcdf_file = geotiff_dir / f"{dir_name}_{origin_short}_{product_short}_{ref_short}_monthly.nc"

    existing_geotiffs = []
    if geotiff_dir.exists():
        existing_geotiffs = list(geotiff_dir.glob(f"{dir_name}_*_month*.tif"))

    result = {
        'geotiff_dir_exists': geotiff_dir.exists(),
        'geotiff_count': len(existing_geotiffs),
        'netcdf_exists': netcdf_file.exists(),
        'geotiff_dir': str(geotiff_dir),
        'netcdf_file': str(netcdf_file)
    }

    logger.info(f"Existing files check:")
    logger.info(f"  GeoTIFF directory: {geotiff_dir}")
    logger.info(f"  GeoTIFFs found: {len(existing_geotiffs)}")
    logger.info(f"  NetCDF exists: {netcdf_file.exists()}")

    return result


@task(retries=2, retry_delay_seconds=300, timeout_seconds=3600)
def download_ecv_climatology(
    variable: str,
    origin: str,
    product_type: str,
    reference_period: str
) -> Path:
    """
    Download ECV climatology data from Copernicus CDS.

    Args:
        variable: One of the ECV variables (e.g., "surface_air_temperature")
        origin: Data source - "era5" (0.25°) or "era5_land" (0.1°)
        product_type: "climatology", "monthly_mean", or "anomaly"
        reference_period: "1981_2010" or "1991_2020"

    Returns:
        Path to downloaded GRIB file
    """
    logger = get_run_logger()
    settings = get_settings()

    # Validate inputs
    if variable not in ECV_VARIABLE_MAPPING:
        raise ValueError(f"Unknown variable: {variable}. Choose from {list(ECV_VARIABLE_MAPPING.keys())}")

    if origin not in ECV_ORIGINS:
        raise ValueError(f"Unknown origin: {origin}. Choose from {ECV_ORIGINS}")

    if product_type not in ECV_PRODUCT_TYPES:
        raise ValueError(f"Unknown product type: {product_type}. Choose from {ECV_PRODUCT_TYPES}")

    if reference_period not in ECV_REFERENCE_PERIODS:
        raise ValueError(f"Unknown reference period: {reference_period}. Choose from {ECV_REFERENCE_PERIODS}")

    logger.info(f"Downloading ECV {product_type} data")
    logger.info(f"  Variable: {variable}")
    logger.info(f"  Origin: {origin}")
    logger.info(f"  Reference period: {reference_period}")

    # Prepare output path
    raw_dir = Path(settings.DATA_DIR) / "raw" / "ecv_climatology"
    raw_dir.mkdir(parents=True, exist_ok=True)

    var_short = variable.replace("surface_air_", "").replace("volumetric_", "").replace("_for_0_to_7cm_layer", "")
    output_path = raw_dir / f"ecv_{var_short}_{origin}_{product_type}_{reference_period}.grib"

    if output_path.exists():
        logger.info(f"File already downloaded: {output_path}")
        return output_path

    # Build CDS request (using the exact structure from your example)
    request = {
        "variable": [variable],
        "origin": [origin],
        "product_type": [product_type],
        "climate_reference_period": [reference_period],
        "month": [
            "01", "02", "03",
            "04", "05", "06",
            "07", "08", "09",
            "10", "11", "12"
        ]
    }

    logger.info("=" * 80)
    logger.info("CDS API REQUEST:")
    logger.info("=" * 80)

    import json
    logger.info(json.dumps(request, indent=2))
    logger.info("=" * 80)

    try:
        client = cdsapi.Client()
        logger.info("Submitting request to CDS API...")
        logger.info(f"Dataset: {dataset}")

        dataset = "ecv-for-climate-change"
        result = client.retrieve(dataset, request)
        result.download(str(output_path))

        logger.info(f"✓ ECV data downloaded: {output_path}")
        logger.info(f"  File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        return output_path
    except Exception as e:
        logger.error(f"✗ Download failed: {e}")
        if output_path.exists():
            output_path.unlink()
        raise


@task
def process_ecv_to_geotiff(
    grib_path: Path,
    variable: str,
    origin: str,
    product_type: str,
    reference_period: str,
    clip_to_brazil: bool = True
) -> List[Path]:
    """
    Process downloaded GRIB file to GeoTIFF files (one per month).
    Optionally clip to Brazil boundary.

    Args:
        grib_path: Path to downloaded GRIB file
        variable: ECV variable name
        origin: Data source (era5 or era5_land)
        product_type: Product type (climatology, monthly_mean, anomaly)
        reference_period: Climate reference period
        clip_to_brazil: Whether to clip to Brazil shapefile

    Returns:
        List of created GeoTIFF paths
    """
    logger = get_run_logger()
    settings = get_settings()

    dir_name = ECV_VARIABLE_MAPPING[variable]

    # Output directory structure: ecv_temp/era5/climatology_1991_2020/
    geotiff_dir = Path(settings.DATA_DIR) / dir_name / origin / f"{product_type}_{reference_period}"
    geotiff_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Processing GRIB to GeoTIFFs: {grib_path}")
    logger.info(f"  Output directory: {geotiff_dir}")

    try:
        # Open GRIB file with cfgrib engine
        ds = xr.open_dataset(grib_path, engine='cfgrib')
        logger.info(f"  Loaded dataset with variables: {list(ds.data_vars)}")
        logger.info(f"  Dimensions: {dict(ds.dims)}")
        logger.info(f"  Coordinates: {list(ds.coords)}")

        # Load Brazil shapefile for clipping if requested
        brazil_gdf = None
        if clip_to_brazil:
            brazil_shp = Path(settings.BRAZIL_SHAPEFILE)
            if brazil_shp.exists():
                brazil_gdf = gpd.read_file(brazil_shp)
                logger.info(f"  Loaded Brazil shapefile: {brazil_shp}")
            else:
                logger.warning(f"  Brazil shapefile not found: {brazil_shp}, skipping clip")
                clip_to_brazil = False

        # Identify the data variable (first non-coordinate variable)
        data_vars = [v for v in ds.data_vars if v not in ['latitude', 'longitude', 'time', 'valid_time']]
        if not data_vars:
            raise ValueError(f"No data variables found in GRIB file")

        var_name = data_vars[0]
        logger.info(f"  Processing variable: {var_name}")

        # Get the data array
        da = ds[var_name]

        # Rename coordinates to standard names for rioxarray
        if 'latitude' in da.coords:
            da = da.rename({'latitude': 'y', 'longitude': 'x'})
        elif 'lat' in da.coords:
            da = da.rename({'lat': 'y', 'lon': 'x'})

        # Ensure CRS is set
        if not da.rio.crs:
            da = da.rio.write_crs("EPSG:4326")

        created_files = []

        # If there's a time dimension, process each month separately
        if 'time' in da.dims:
            for i, time_val in enumerate(da.time.values):
                month_num = i + 1
                da_month = da.isel(time=i)

                # Clip to Brazil if requested
                if clip_to_brazil and brazil_gdf is not None:
                    da_month = da_month.rio.clip(brazil_gdf.geometry, brazil_gdf.crs, drop=True)

                # Generate output filename
                output_file = geotiff_dir / f"{dir_name}_{origin}_{product_type}_{reference_period}_month{month_num:02d}.tif"

                # Save as GeoTIFF
                da_month.rio.to_raster(output_file, compress='DEFLATE', tiled=True)
                created_files.append(output_file)
                logger.info(f"  ✓ Created: {output_file.name}")
        else:
            # No time dimension - single file
            if clip_to_brazil and brazil_gdf is not None:
                da = da.rio.clip(brazil_gdf.geometry, brazil_gdf.crs, drop=True)

            output_file = geotiff_dir / f"{dir_name}_{origin}_{product_type}_{reference_period}.tif"
            da.rio.to_raster(output_file, compress='DEFLATE', tiled=True)
            created_files.append(output_file)
            logger.info(f"  ✓ Created: {output_file.name}")

        logger.info(f"✓ Created {len(created_files)} GeoTIFF files")
        return created_files

    except Exception as e:
        logger.error(f"✗ Failed to process GRIB to GeoTIFF: {e}")
        raise


@task
def create_netcdf_from_geotiffs(
    geotiff_paths: List[Path],
    variable: str,
    origin: str,
    product_type: str,
    reference_period: str
) -> Path:
    """
    Consolidate monthly GeoTIFFs into a single NetCDF file for fast queries.

    Args:
        geotiff_paths: List of GeoTIFF file paths
        variable: ECV variable name
        origin: Data source
        product_type: Product type
        reference_period: Climate reference period

    Returns:
        Path to created NetCDF file
    """
    logger = get_run_logger()
    settings = get_settings()

    if not geotiff_paths:
        raise ValueError("No GeoTIFF files provided")

    dir_name = ECV_VARIABLE_MAPPING[variable]
    geotiff_dir = Path(settings.DATA_DIR) / dir_name / origin / f"{product_type}_{reference_period}"
    netcdf_file = geotiff_dir / f"{dir_name}_{origin}_{product_type}_{reference_period}_monthly.nc"

    logger.info(f"Creating NetCDF from {len(geotiff_paths)} GeoTIFFs")
    logger.info(f"  Output: {netcdf_file}")

    try:
        # Load all GeoTIFFs
        datasets = []
        months = []

        for tif_path in sorted(geotiff_paths):
            # Extract month number from filename
            # Format: ecv_temp_era5_climatology_1991_2020_month01.tif
            month_str = tif_path.stem.split('_month')[-1]
            month_num = int(month_str)
            months.append(month_num)

            # Load GeoTIFF
            da = rioxarray.open_rasterio(tif_path, masked=True).squeeze()
            da = da.drop_vars(['band'], errors='ignore')
            datasets.append(da)

        # Concatenate along new month dimension
        combined = xr.concat(datasets, dim='month')
        combined['month'] = months

        # Create dataset with proper metadata
        ds = xr.Dataset({
            dir_name: combined
        })

        # Add attributes
        ds[dir_name].attrs['long_name'] = variable.replace('_', ' ').title()
        ds[dir_name].attrs['source'] = f'Copernicus ECV - {origin}'
        ds[dir_name].attrs['product_type'] = product_type
        ds[dir_name].attrs['reference_period'] = reference_period.replace('_', '-')
        ds[dir_name].attrs['units'] = 'K' if 'temperature' in variable else 'unknown'

        # Chunk for efficient access
        ds = ds.chunk({'month': 1, 'y': 100, 'x': 100})

        # Save to NetCDF with compression
        encoding = {
            dir_name: {
                'zlib': True,
                'complevel': 5,
                'chunksizes': (1, 100, 100)
            }
        }

        ds.to_netcdf(netcdf_file, encoding=encoding)
        logger.info(f"✓ NetCDF created: {netcdf_file}")
        logger.info(f"  File size: {netcdf_file.stat().st_size / 1024 / 1024:.2f} MB")

        return netcdf_file

    except Exception as e:
        logger.error(f"✗ Failed to create NetCDF: {e}")
        raise


@task
def cleanup_raw_files(grib_path: Path):
    """Remove temporary GRIB file after processing."""
    logger = get_run_logger()
    try:
        if grib_path.exists():
            grib_path.unlink()
            logger.info(f"✓ Cleaned up raw file: {grib_path}")
    except Exception as e:
        logger.warning(f"Could not delete raw file: {e}")


@flow(name="download_ecv_climatology")
def download_ecv_climatology_flow(
    variable: str = "surface_air_temperature",
    origin: str = "era5",
    product_type: str = "climatology",
    reference_period: str = "1991_2020",
    clip_to_brazil: bool = True,
    cleanup: bool = True
):
    """
    Download and process ECV monthly climatology data for Brazil.

    Args:
        variable: ECV variable to download (e.g., "surface_air_temperature")
        origin: Data source - "era5" (0.25°) or "era5_land" (0.1°)
        product_type: "climatology", "monthly_mean", or "anomaly"
        reference_period: "1981_2010" or "1991_2020"
        clip_to_brazil: Whether to clip data to Brazil boundary
        cleanup: Whether to delete raw GRIB file after processing

    Example:
        # Download temperature climatology (1991-2020 monthly averages)
        download_ecv_climatology_flow(
            variable="surface_air_temperature",
            origin="era5",
            product_type="climatology",
            reference_period="1991_2020"
        )
    """
    logger = get_run_logger()
    settings = get_settings()

    logger.info("=" * 80)
    logger.info("ECV CLIMATOLOGY DOWNLOAD FLOW")
    logger.info("=" * 80)
    logger.info(f"Variable: {variable}")
    logger.info(f"Origin: {origin}")
    logger.info(f"Product type: {product_type}")
    logger.info(f"Reference period: {reference_period}")
    logger.info(f"Clip to Brazil: {clip_to_brazil}")
    logger.info("=" * 80)

    # Check existing files
    existing = check_existing_files(variable, origin, product_type, reference_period)

    if existing['netcdf_exists'] and existing['geotiff_count'] == 12:
        logger.info("✓ All files already exist (12 monthly GeoTIFFs + NetCDF)")
        logger.info(f"  GeoTIFF directory: {existing['geotiff_dir']}")
        logger.info(f"  NetCDF file: {existing['netcdf_file']}")
        return

    # Download from CDS
    grib_path = download_ecv_climatology(
        variable=variable,
        origin=origin,
        product_type=product_type,
        reference_period=reference_period
    )

    # Process to GeoTIFFs
    geotiff_paths = process_ecv_to_geotiff(
        grib_path=grib_path,
        variable=variable,
        origin=origin,
        product_type=product_type,
        reference_period=reference_period,
        clip_to_brazil=clip_to_brazil
    )

    # Create consolidated NetCDF
    netcdf_path = create_netcdf_from_geotiffs(
        geotiff_paths=geotiff_paths,
        variable=variable,
        origin=origin,
        product_type=product_type,
        reference_period=reference_period
    )

    # Cleanup raw files
    if cleanup:
        cleanup_raw_files(grib_path)

    logger.info("=" * 80)
    logger.info("✓ ECV CLIMATOLOGY FLOW COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Created {len(geotiff_paths)} monthly GeoTIFF files")
    logger.info(f"Created consolidated NetCDF: {netcdf_path}")
