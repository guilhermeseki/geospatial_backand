import shapefile
from datetime import datetime, date
from pathlib import Path
from typing import Tuple
import requests
import fsspec
import rioxarray
import xarray as xr
from prefect import task, get_run_logger
from .schemas import DataSource
from app.config.settings import get_settings
import os
import tempfile
import time
import cdsapi
import cdsapi

c = cdsapi.Client()
settings = get_settings()

def is_success(status_code: int) -> bool:
    return status_code in (200, 201, 202)

@task(retries=2, retry_delay_seconds=60)
def setup_mosaic(mosaic_dir: Path, source: DataSource):
    """Set up a GeoServer ImageMosaic store for the given source."""
    logger = get_run_logger()
    mosaic_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Mosaic folder ready at {mosaic_dir}")

    # Create indexer.properties if missing
    indexer_file = mosaic_dir / "indexer.properties"
    if not indexer_file.exists():
        indexer_content = f"""\
TimeAttribute=ingestion
TimeRegex={source.value}_(\\d{{8}})
TimeFormat=yyyyMMdd
"""
        indexer_file.write_text(indexer_content)
        logger.info(f"indexer.properties created at {indexer_file}")
    else:
        logger.info(f"indexer.properties already exists at {indexer_file}")

    # Create ImageMosaic store in GeoServer
    geoserver_store_url = (
        f"http://{settings.GEOSERVER_HOST}:{settings.GEOSERVER_PORT}/geoserver/rest/workspaces/"
        f"{settings.GEOSERVER_WORKSPACE}/coveragestores/{source.value}_final/external.imagemosaic"
    )
    data = f"{mosaic_dir.resolve()}"
    headers = {"Content-Type": "text/plain"}
    response = requests.post(
        geoserver_store_url,
        data=data,
        headers=headers,
        auth=(settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD)
    )
    if is_success(response.status_code):
        logger.info(f"GeoServer ImageMosaic store created for {source.value}")
    elif response.status_code == 400 and "already exists" in response.text:
        logger.info(f"Mosaic store already exists for {source.value}")
    else:
        raise ValueError(f"Failed to create mosaic store: {response.status_code} - {response.text}")

    # Ensure time dimension is enabled
    coverages_url = (
        f"http://{settings.GEOSERVER_HOST}:{settings.GEOSERVER_PORT}/geoserver/rest/workspaces/"
        f"{settings.GEOSERVER_WORKSPACE}/coveragestores/{source.value}_final/coverages.json"
    )
    response = requests.get(
        coverages_url,
        auth=(settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD)
    )
    response.raise_for_status()
    coverages = response.json().get("coverages", {}).get("coverage", [])
    for cov in coverages:
        cov_name = cov["name"]
        cov_url = (
            f"http://{settings.GEOSERVER_HOST}:{settings.GEOSERVER_PORT}/geoserver/rest/workspaces/"
            f"{settings.GEOSERVER_WORKSPACE}/coveragestores/{source.value}_final/coverages/{cov_name}.json"
        )
        payload = {
            "coverage": {
                "metadata": {
                    "entry": [
                        {"@key": "time", "dimensionInfo": {"enabled": True, "presentation": "LIST"}}
                    ]
                }
            }
        }
        resp = requests.put(
            cov_url,
            json=payload,
            auth=(settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD)
        )
        if is_success(resp.status_code):
            logger.info(f"Time dimension enabled for coverage '{cov_name}'")
        else:
            logger.warning(f"Failed to enable time dimension for '{cov_name}': {resp.status_code} - {resp.text}")

@task(retries=3, retry_delay_seconds=60)
def check_data_availability(date: date, source: DataSource) -> bool:
    """Check if data exists locally first, then on the respective server"""
    logger = get_run_logger()
    # Check local file
    local_path = Path(settings.DATA_DIR) / f"{source.value}" / f"{source.value}_{date.strftime('%Y%m%d')}.tif"
    if local_path.exists():
        logger.info(f"Data already available locally for {date} at {local_path}")
        return True

    # Fallback: check remote server
    if source == DataSource.CHIRPS:
        url = f"https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/sat/{date.year}/chirps-v3.0.sat.{date.strftime('%Y.%m.%d')}.tif"
    elif source == DataSource.MERGE:
        url = f"https://ftp.cptec.inpe.br/modelos/tempo/MERGE/GPM/DAILY/{date.year}/{date.strftime('%m')}/MERGE_CPTEC_{date.strftime('%Y%m%d')}.grib2"

    else:
        raise ValueError(f"Unsupported data source: {source}")

    try:
        response = requests.head(url, timeout=10)
        if is_success(response.status_code):
            logger.info(f"Data available on server for {date} at {url}")
            return True
        logger.warning(f"No data available for {date} (HTTP {response.status_code})")
        return False
    except Exception as e:
        logger.error(f"Availability check failed: {str(e)}")
        raise

@task(retries=3, retry_delay_seconds=300)
def download_data(date: date, source: DataSource) -> Path:
    """Download the raw data file to a temporary location"""
    logger = get_run_logger()
    if source == DataSource.CHIRPS:
        url = f"https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/sat/{date.year}/chirps-v3.0.sat.{date.strftime('%Y.%m.%d')}.tif"
        suffix = ".tif"
    elif source == DataSource.MERGE:
        url = f"https://ftp.cptec.inpe.br/modelos/tempo/MERGE/GPM/DAILY/{date.year}/{date.strftime('%m')}/MERGE_CPTEC_{date.strftime('%Y%m%d')}.grib2"
        suffix = ".grib2"

    else:
        raise ValueError(f"Unsupported data source: {source}")

    try:
        # Use temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            logger.info(f"Downloading from {url} to temporary file {temp_path}")
            with fsspec.open(url) as remote_file:
                temp_file.write(remote_file.read())
        return temp_path
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise

@task
def process_data(
    input_path: Path,
    date: date,
    source: DataSource,
    bbox: Tuple[float, float, float, float]
) -> Path:
    """Crop data to the specified bounding box, save as TIFF, and delete raw file"""
    logger = get_run_logger()
    output_path = Path(settings.DATA_DIR) / f"{source.value}" / f"{source.value}_{date.strftime('%Y%m%d')}.tif"
    try:
        # Load and clip data
        if source == DataSource.CHIRPS:
            ds = rioxarray.open_rasterio(input_path)
        elif source == DataSource.MERGE:
                    ds = xr.open_dataset(input_path, engine="cfgrib")
                    
                    # --- Standard Longitude Correction ---
                    # This corrects the 0-360 longitude range to -180-180
                    ds = ds.assign_coords(longitude=(((ds.longitude + 180) % 360) - 180)).sortby('longitude')
                    # ds = ds.sortby("latitude") # This line can be uncommented if you want to explicitly sort lat

                    # --- Variable Selection Logic ---
                    possible_vars = ["prec", "rdp", "pr"]
                    selected_var = None
                    for var in possible_vars: 
                        if var in ds.data_vars:
                            selected_var = var
                            break
                    if selected_var is None:
                        raise ValueError(f"No precipitation variable found in {ds.data_vars.keys()}")
                    
                    logger.info(f"Selected variable for {source.value} on {date}: {selected_var}")

                    # --- Select the variable and assign CRS ---
                    # Now 'ds' is the DataArray containing your precipitation data
                    ds = ds[selected_var].rio.write_crs("EPSG:4326")
                    
                    # -----------------------------------------------------------------
                    # 🚨 FIX FOR INVERTED IMAGE (VERTICAL FLIP) 
                    # -----------------------------------------------------------------
                    # The DataArray variable is now 'ds' (overwriting the Dataset variable)
                    if ds.latitude.values[0] < ds.latitude.values[-1]:
                        # If latitudes are increasing (South -> North), reverse the order 
                        # This flips the array data to ensure North-Up orientation for the raster
                        ds = ds.sel(latitude=slice(None, None, -1)) 
                        logger.info("Flipped latitude axis to ensure North-Up raster orientation.")
                    # -----------------------------------------------------------------
                    
                    # Your next step would be to save 'ds' to a file:
                    # ds.rio.to_raster(output_path)

        else:
            raise ValueError(f"Unsupported data source: {source}")

        ds = ds.rio.clip_box(*bbox)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first
        temp_output = output_path.parent / f"{output_path.stem}_temp.tif"
        ds.rio.to_raster(
            temp_output,
            driver="COG",
            tiled=True,
            compress="LZW",
            overview_level=5
        )

        # Clip with Brazil shapefile if it exists (preserves grid alignment)
        shapefile = Path("/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp")
        if shapefile.exists():
            import subprocess
            try:
                result = subprocess.run([
                    "gdalwarp",
                    "-q",
                    "-cutline", str(shapefile),
                    "-crop_to_cutline",
                    "-dstnodata", "nan",
                    "-overwrite",
                    str(temp_output),
                    str(output_path)
                ], capture_output=True, text=True, timeout=30, check=True)
                temp_output.unlink()  # Remove temp file
                logger.info(f"Processed & clipped with shapefile: {output_path}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Shapefile clipping failed, using bbox-only clip: {e.stderr[:100]}")
                temp_output.rename(output_path)
            except Exception as e:
                logger.warning(f"Shapefile clipping error, using bbox-only clip: {e}")
                if temp_output.exists():
                    temp_output.rename(output_path)
        else:
            # No shapefile, just use temp file (bbox-only clip)
            temp_output.rename(output_path)
            logger.info(f"Processed TIFF saved to {output_path}")

        # Delete temporary raw file
        if input_path.exists():
            input_path.unlink()
            logger.info(f"Deleted temporary raw file: {input_path}")

        return output_path
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        # Ensure temp file is deleted on failure
        if input_path.exists():
            input_path.unlink()
            logger.info(f"Deleted temporary raw file on failure: {input_path}")
        raise

@task
def validate_output(output_path: Path) -> bool:
    """Verify the processed TIFF file meets requirements"""
    logger = get_run_logger()
    try:
        ds = rioxarray.open_rasterio(output_path)
        if ds.rio.crs is None:
            raise ValueError("Missing CRS in TIFF")
        band_data = ds.isel(band=0)
        if band_data.where(band_data >= 0).isnull().all():
            raise ValueError("All precipitation values are invalid or null")
        logger.info(f"Validated TIFF at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise


@task(retries=2, retry_delay_seconds=60)
def refresh_mosaic_shapefile(source: DataSource):
    logger = get_run_logger()
    #remove indexers .shp
    mosaic_dir = Path(settings.DATA_DIR)/source.value
    for f in mosaic_dir.glob(f"{source.value}.*"):
        try:
            f.unlink()
        except Exception as e:
            logger.error(f"❌ Failed to delete {f}: {e}")

    # Reload GeoServer
    logger.info("Reloading GeoServer...")
    reload_url = f"{settings.geoserver_local_url}/rest/reload"
    resp = requests.post(reload_url, auth=(settings.GEOSERVER_ADMIN_USER, settings.GEOSERVER_ADMIN_PASSWORD))
    if resp.status_code == 200:
        logger.info("GeoServer reload triggered.")
    else:
        logger.error(f"❌ Failed to reload GeoServer: {resp.status_code} {resp.text}")

    time.sleep(3)  # Give GeoServer a moment

    # Trigger WMS GetCapabilities for the mosaic
    logger.info("Triggering WMS GetCapabilities...")
    cap_url = f"{settings.geoserver_local_url}/wms?service=WMS&version=1.3.0&request=GetCapabilities&layers={settings.GEOSERVER_WORKSPACE}:{source.value}"
    resp = requests.get(cap_url)
    if resp.status_code == 200:
        logger.info("GetCapabilities request successful — mosaic index refreshed.")
    else:
        logger.error(f"❌Failed to fetch GetCapabilities: {resp.status_code} {resp.text}")
        raise

#zm pedra estrada de teerra 1km
