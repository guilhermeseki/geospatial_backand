"""
NDVI Data Flow - With Historical NetCDF Management
Uses Microsoft Planetary Computer for BOTH Sentinel-2 and MODIS
100% FREE - NO AUTHENTICATION REQUIRED!
"""
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import xarray as xr
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling, calculate_default_transform, transform_bounds
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.crs import CRS
from prefect import flow, task, get_run_logger
from .schemas import DataSource
from app.config.settings import get_settings

# Microsoft Planetary Computer imports (FREE, NO AUTH!)
try:
    import pystac_client
    import planetary_computer
    PLANETARY_COMPUTER_AVAILABLE = True
except ImportError:
    PLANETARY_COMPUTER_AVAILABLE = False


# Mapping from NDVI source to directory names
SOURCE_MAPPING = {
    "sentinel2": "ndvi_s2",
    "modis": "ndvi_modis"
}


def get_output_directory(source: str, settings) -> Path:
    """Get the appropriate output directory for an NDVI source."""
    if source in SOURCE_MAPPING:
        dir_name = SOURCE_MAPPING[source]
    else:
        dir_name = f"ndvi_{source}"
    
    output_dir = Path(settings.DATA_DIR) / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@task
def check_missing_dates(
    start_date: date,
    end_date: date,
    source: str
) -> Dict[str, List[date]]:
    """
    Check which dates are missing from GeoTIFF and historical NetCDF separately.
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
    dir_name = get_output_directory(source, settings).name
    geotiff_dir = Path(settings.DATA_DIR) / dir_name
    hist_dir = Path(settings.DATA_DIR) / f"{dir_name}_hist"
    hist_file = hist_dir / "historical.nc"
    
    # Check GeoTIFF files
    existing_geotiff_dates = set()
    if geotiff_dir.exists():
        for tif_file in geotiff_dir.glob(f"{dir_name}_*.tif"):
            try:
                date_str = tif_file.stem.split('_')[-1]
                file_date = pd.to_datetime(date_str, format='%Y%m%d').date()
                existing_geotiff_dates.add(file_date)
            except Exception as e:
                logger.warning(f"Could not parse date from {tif_file.name}: {e}")
    
    logger.info(f"Found {len(existing_geotiff_dates)} existing GeoTIFF files")
    
    # Check historical NetCDF
    existing_hist_dates = set()
    if hist_file.exists():
        try:
            ds = xr.open_dataset(hist_file, chunks='auto')
            if 'ndvi' in ds.data_vars:
                existing_hist_dates = set(pd.to_datetime(ds['ndvi'].time.values).date)
                logger.info(f"Found {len(existing_hist_dates)} dates in historical NetCDF")
            ds.close()
        except Exception as e:
            logger.warning(f"Could not read historical file: {e}")
    else:
        logger.info("Historical NetCDF does not exist yet")
    
    # Calculate missing dates
    requested_dates_set = set(requested_dates)
    missing_geotiff = sorted(list(requested_dates_set - existing_geotiff_dates))
    missing_historical = sorted(list(requested_dates_set - existing_hist_dates))
    missing_download = sorted(list(set(missing_geotiff) | set(missing_historical)))
    
    logger.info(f"Missing from GeoTIFF: {len(missing_geotiff)} dates")
    logger.info(f"Missing from historical: {len(missing_historical)} dates")
    logger.info(f"Need to download: {len(missing_download)} dates")
    
    return {
        'geotiff': missing_geotiff,
        'historical': missing_historical,
        'download': missing_download
    }


@task(retries=3, retry_delay_seconds=300, timeout_seconds=7200)
def download_sentinel2_batch(
    start_date: date,
    end_date: date,
    area: List[float],
    max_cloud_cover: float = 15.0
) -> Path:
    """
    Download Sentinel-2 data using Microsoft Planetary Computer.
    100% FREE - NO AUTHENTICATION REQUIRED!
    """
    logger = get_run_logger()
    settings = get_settings()
    
    if not PLANETARY_COMPUTER_AVAILABLE:
        raise ImportError(
            "Microsoft Planetary Computer packages not installed.\n"
            "Install with: pip install pystac-client planetary-computer"
        )
    
    # Convert bbox from CDS format [N, W, S, E] to [W, S, E, N]
    north, west, south, east = area[0], area[1], area[2], area[3]
    bbox = [west, south, east, north]
    
    logger.info(f"Using bbox [N, W, S, E]: {area}")
    
    # Prepare output path
    raw_dir = Path(settings.DATA_DIR) / "raw" / "sentinel2"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    output_path = raw_dir / f"s2_ndvi_{start_str}_{end_str}.nc"
    
    if output_path.exists():
        logger.info(f"Batch already downloaded: {output_path}")
        return output_path
    
    logger.info("=" * 80)
    logger.info("SENTINEL-2 DOWNLOAD (Microsoft Planetary Computer - FREE!)")
    logger.info("=" * 80)
    logger.info(f"  Date range: {start_date} to {end_date}")
    logger.info(f"  Max cloud cover: {max_cloud_cover}%")
    logger.info(f"  NO AUTHENTICATION REQUIRED!")
    logger.info(f"  Bbox [W, S, E, N]: [{west}, {south}, {east}, {north}]")
    logger.info(f"  Bbox area: {abs(east-west):.1f}° x {abs(north-south):.1f}°")
    logger.info("=" * 80)
    
    try:
        # Connect to Planetary Computer
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace
        )
        
        # Search for Sentinel-2 data
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
            query={"eo:cloud_cover": {"lt": max_cloud_cover}}
        )
        
        items = list(search.items())
        logger.info(f"Found {len(items)} Sentinel-2 scenes")
        
        if len(items) == 0:
            raise ValueError("No Sentinel-2 products found")
        
        # Limit scenes
        max_scenes = 50
        if len(items) > max_scenes:
            items = sorted(items, key=lambda x: x.datetime, reverse=True)[:max_scenes]
        
        # Process each image
        ndvi_data_list = []
        time_list = []
        
        # Define common grid from bbox at ~10m resolution
        # Calculate grid dimensions based on bbox
        lat_range = north - south
        lon_range = east - west
        
        # Approximate 10m in degrees (varies by latitude, but good enough)
        # At equator: 1 degree ≈ 111km, 10m ≈ 0.00009 degrees
        resolution = 0.0001  # ~10m
        
        n_lat = int(lat_range / resolution)
        n_lon = int(lon_range / resolution)
        
        # Limit grid size to prevent memory issues
        max_pixels = 50000  # Max 50k pixels per dimension
        if n_lat > max_pixels:
            n_lat = max_pixels
            logger.warning(f"Limiting latitude pixels to {max_pixels}")
        if n_lon > max_pixels:
            n_lon = max_pixels
            logger.warning(f"Limiting longitude pixels to {max_pixels}")
        
        # Create common grid
        lats = np.linspace(north, south, n_lat)
        lons = np.linspace(west, east, n_lon)
        
        # Create transform for common grid
        common_transform = transform_from_bounds(west, south, east, north, n_lon, n_lat)
        
        logger.info(f"Common grid: {n_lat} x {n_lon} pixels")
        logger.info(f"Grid covers: {west:.2f}°W to {east:.2f}°E, {south:.2f}°S to {north:.2f}°N")
        
        for i, item in enumerate(items):
            logger.info(f"Processing scene {i+1}/{len(items)}: {item.id}")
            
            try:
                # Get signed URLs
                nir_href = planetary_computer.sign(item.assets["B08"].href)
                red_href = planetary_computer.sign(item.assets["B04"].href)
                
                # Read and reproject NIR band
                with rasterio.open(nir_href) as src:
                    # Log scene info for debugging
                    scene_bounds = src.bounds
                    
                    # Calculate intersection of scene with requested bbox
                    intersect_west = max(west, scene_bounds.left)
                    intersect_south = max(south, scene_bounds.bottom)
                    intersect_east = min(east, scene_bounds.right)
                    intersect_north = min(north, scene_bounds.top)
                    
                    # Check if there's actual intersection
                    if intersect_west >= intersect_east or intersect_south >= intersect_north:
                        logger.warning(f"  Scene doesn't intersect bbox, skipping")
                        continue
                    
                    # Read the intersection area
                    window = from_bounds(intersect_west, intersect_south, 
                                        intersect_east, intersect_north, 
                                        src.transform)
                    
                    # Check window validity
                    if window.width <= 0 or window.height <= 0:
                        logger.warning(f"  Invalid window size, skipping")
                        continue
                    
                    nir_src = src.read(1, window=window).astype(np.float32)
                    src_transform = src.window_transform(window)
                    src_crs = src.crs
                    
                    # Skip if empty
                    if nir_src.size == 0:
                        logger.warning(f"  Scene has no data, skipping")
                        continue
                    
                    # Reproject to common grid
                    nir = np.empty((n_lat, n_lon), dtype=np.float32)
                    reproject(
                        source=nir_src,
                        destination=nir,
                        src_transform=src_transform,
                        src_crs=src_crs,
                        dst_transform=common_transform,
                        dst_crs=src_crs,
                        resampling=Resampling.bilinear
                    )
                
                # Read and reproject Red band
                with rasterio.open(red_href) as src:
                    scene_bounds = src.bounds
                    
                    # Calculate intersection
                    intersect_west = max(west, scene_bounds.left)
                    intersect_south = max(south, scene_bounds.bottom)
                    intersect_east = min(east, scene_bounds.right)
                    intersect_north = min(north, scene_bounds.top)
                    
                    if intersect_west >= intersect_east or intersect_south >= intersect_north:
                        logger.warning(f"  Red band doesn't intersect bbox, skipping")
                        continue
                    
                    window = from_bounds(intersect_west, intersect_south,
                                        intersect_east, intersect_north,
                                        src.transform)
                    
                    red_src = src.read(1, window=window).astype(np.float32)
                    src_transform = src.window_transform(window)
                    src_crs = src.crs
                    
                    # Reproject to common grid
                    red = np.empty((n_lat, n_lon), dtype=np.float32)
                    reproject(
                        source=red_src,
                        destination=red,
                        src_transform=src_transform,
                        src_crs=src_crs,
                        dst_transform=common_transform,
                        dst_crs=src_crs,
                        resampling=Resampling.bilinear
                    )
                
                # Calculate NDVI
                denominator = nir + red
                ndvi = np.where(denominator != 0, (nir - red) / denominator, np.nan)
                ndvi = np.clip(ndvi, -1, 1)
                
                # Check if we got any valid data
                if np.all(np.isnan(ndvi)):
                    logger.warning(f"  All NDVI values are NaN, skipping")
                    continue
                
                ndvi_data_list.append(ndvi)
                time_list.append(item.datetime)
                
                valid_pct = 100 * np.sum(~np.isnan(ndvi)) / ndvi.size
                logger.info(f"  ✓ Processed successfully ({valid_pct:.1f}% valid pixels)")
                
            except Exception as e:
                logger.error(f"  Failed to process scene: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        if len(ndvi_data_list) == 0:
            raise RuntimeError("All scenes failed to process")
        
        # Create dataset
        ndvi_array = np.stack(ndvi_data_list)
        
        ds = xr.Dataset(
            {'ndvi': (['time', 'latitude', 'longitude'], ndvi_array)},
            coords={
                'time': pd.to_datetime(time_list),
                'latitude': lats,
                'longitude': lons,
            },
            attrs={
                'source': 'Sentinel-2 L2A',
                'resolution': '10m',
                'provider': 'Microsoft Planetary Computer'
            }
        )

        # FUSE FIX: Write to /tmp first, then copy to FUSE filesystem
        import tempfile
        import shutil
        temp_dir = Path(tempfile.mkdtemp(prefix="ndvi_s2_"))
        temp_file = temp_dir / output_path.name

        logger.info(f"Writing to temp file (FUSE-safe): {temp_file}")
        ds.to_netcdf(str(temp_file))

        logger.info(f"Copying to final location: {output_path}")
        shutil.copy2(temp_file, output_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

        logger.info(f"✓ Sentinel-2 NDVI saved: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"✗ Download failed: {e}")
        # Cleanup
        try:
            if 'temp_dir' in locals() and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        if output_path.exists():
            output_path.unlink()
        raise


@task(retries=2, retry_delay_seconds=600, timeout_seconds=7200)
def download_modis_batch(
    start_date: date,
    end_date: date,
    area: List[float]
) -> Path:
    """
    Download MODIS NDVI data using Microsoft Planetary Computer.
    100% FREE - NO AUTHENTICATION REQUIRED!
    """
    logger = get_run_logger()
    settings = get_settings()
    
    if not PLANETARY_COMPUTER_AVAILABLE:
        raise ImportError(
            "Microsoft Planetary Computer packages not installed.\n"
            "Install with: pip install pystac-client planetary-computer"
        )
    
    north, west, south, east = area[0], area[1], area[2], area[3]
    bbox = [west, south, east, north]
    
    # Prepare output
    raw_dir = Path(settings.DATA_DIR) / "raw" / "modis"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    output_path = raw_dir / f"modis_ndvi_{start_str}_{end_str}.nc"
    
    if output_path.exists():
        logger.info(f"Batch already downloaded: {output_path}")
        return output_path
    
    logger.info("=" * 80)
    logger.info("MODIS NDVI DOWNLOAD (Microsoft Planetary Computer - FREE!)")
    logger.info("=" * 80)
    
    try:
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace
        )
        
        search = catalog.search(
            collections=["modis-13Q1-061"],
            bbox=bbox,
            datetime=f"{start_date.isoformat()}/{end_date.isoformat()}"
        )
        
        items = list(search.items())
        logger.info(f"Found {len(items)} MODIS composites")
        
        if len(items) == 0:
            raise ValueError("No MODIS data found")
        
        ndvi_data_list = []
        time_list = []
        
        # Define common grid from bbox at ~250m resolution for MODIS
        lat_range = north - south
        lon_range = east - west
        
        # 250m resolution in degrees
        resolution = 0.0025  # ~250m
        
        n_lat = int(lat_range / resolution)
        n_lon = int(lon_range / resolution)
        
        # Limit grid size
        max_pixels = 20000
        if n_lat > max_pixels:
            n_lat = max_pixels
        if n_lon > max_pixels:
            n_lon = max_pixels
        
        # Create common grid
        lats = np.linspace(north, south, n_lat)
        lons = np.linspace(west, east, n_lon)
        
        common_transform = transform_from_bounds(west, south, east, north, n_lon, n_lat)
        
        logger.info(f"Common grid: {n_lat} x {n_lon} pixels (~250m)")
        
        for i, item in enumerate(items):
            logger.info(f"Processing composite {i+1}/{len(items)}: {item.id}")
            
            try:
                ndvi_href = planetary_computer.sign(item.assets["250m_16_days_NDVI"].href)
                
                with rasterio.open(ndvi_href) as src:
                    # MODIS uses sinusoidal projection - need to transform bbox
                    src_crs = src.crs
                    logger.info(f"  MODIS CRS: {src_crs}")
                    
                    # Transform our WGS84 bbox to MODIS CRS
                    modis_bbox = transform_bounds(
                        CRS.from_epsg(4326),  # WGS84
                        src_crs,               # MODIS sinusoidal
                        west, south, east, north
                    )
                    
                    modis_west, modis_south, modis_east, modis_north = modis_bbox
                    logger.info(f"  Transformed bbox: W={modis_west:.0f}, S={modis_south:.0f}, E={modis_east:.0f}, N={modis_north:.0f}")
                    
                    # Get scene bounds
                    scene_bounds = src.bounds
                    logger.info(f"  Scene bounds: W={scene_bounds.left:.0f}, S={scene_bounds.bottom:.0f}, E={scene_bounds.right:.0f}, N={scene_bounds.top:.0f}")
                    
                    # Calculate intersection in MODIS coordinates
                    intersect_west = max(modis_west, scene_bounds.left)
                    intersect_south = max(modis_south, scene_bounds.bottom)
                    intersect_east = min(modis_east, scene_bounds.right)
                    intersect_north = min(modis_north, scene_bounds.top)
                    
                    # Check if there's actual intersection
                    if intersect_west >= intersect_east or intersect_south >= intersect_north:
                        logger.warning(f"  No intersection, skipping")
                        continue
                    
                    logger.info(f"  Intersection found: {intersect_east-intersect_west:.0f}m x {intersect_north-intersect_south:.0f}m")
                    
                    window = from_bounds(intersect_west, intersect_south,
                                        intersect_east, intersect_north,
                                        src.transform)
                    
                    if window.width <= 0 or window.height <= 0:
                        logger.warning(f"  Invalid window, skipping")
                        continue
                    
                    ndvi_src = src.read(1, window=window).astype(np.float32)
                    src_transform = src.window_transform(window)
                    src_crs = src.crs

                    logger.info(f"  Read {ndvi_src.shape[0]}x{ndvi_src.shape[1]} pixels")

                    # Skip if empty
                    if ndvi_src.size == 0:
                        logger.warning(f"  Empty data, skipping")
                        continue

                    # Reproject to common grid (WGS84)
                    ndvi_raw = np.empty((n_lat, n_lon), dtype=np.float32)
                    reproject(
                        source=ndvi_src,
                        destination=ndvi_raw,
                        src_transform=src_transform,
                        src_crs=src_crs,
                        dst_transform=common_transform,
                        dst_crs=CRS.from_epsg(4326),  # Reproject to WGS84
                        resampling=Resampling.bilinear
                    )
                
                # Scale MODIS NDVI
                ndvi = ndvi_raw * 0.0001
                ndvi = np.where((ndvi < -1) | (ndvi > 1), np.nan, ndvi)
                
                # Check for valid data
                if np.all(np.isnan(ndvi)):
                    logger.warning(f"  All values are NaN, skipping")
                    continue
                
                ndvi_data_list.append(ndvi)
                time_list.append(item.datetime)
                
                valid_pct = 100 * np.sum(~np.isnan(ndvi)) / ndvi.size
                logger.info(f"  ✓ Processed successfully ({valid_pct:.1f}% valid pixels)")
                
            except Exception as e:
                logger.error(f"  Failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        if len(ndvi_data_list) == 0:
            raise RuntimeError("All composites failed")
        
        ndvi_array = np.stack(ndvi_data_list)

        ds = xr.Dataset(
            {'ndvi': (['time', 'latitude', 'longitude'], ndvi_array)},
            coords={
                'time': pd.to_datetime(time_list),
                'latitude': lats,
                'longitude': lons,
            },
            attrs={
                'source': 'MODIS MOD13Q1',
                'resolution': '250m',
                'provider': 'Microsoft Planetary Computer'
            }
        )

        # FUSE FIX: Write to /tmp first, then copy to FUSE filesystem
        import tempfile
        import shutil
        temp_dir = Path(tempfile.mkdtemp(prefix="ndvi_modis_"))
        temp_file = temp_dir / output_path.name

        logger.info(f"Writing to temp file (FUSE-safe): {temp_file}")
        ds.to_netcdf(str(temp_file))

        logger.info(f"Copying to final location: {output_path}")
        shutil.copy2(temp_file, output_path)
        shutil.rmtree(temp_dir, ignore_errors=True)

        logger.info(f"✓ MODIS NDVI saved: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"✗ Download failed: {e}")
        # Cleanup
        try:
            if 'temp_dir' in locals() and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        if output_path.exists():
            output_path.unlink()
        raise


@task
def process_ndvi_to_geotiff(
    netcdf_path: Path,
    source: str,
    bbox: tuple,
    dates_to_process: Optional[List[date]] = None
) -> List[Path]:
    """Convert NDVI NetCDF to daily GeoTIFFs."""
    logger = get_run_logger()
    settings = get_settings()
    
    output_dir = get_output_directory(source, settings)
    processed_paths = []
    
    try:
        ds = xr.open_dataset(netcdf_path)
        da = ds['ndvi']
        
        if isinstance(bbox, list):
            bbox = (bbox[1], bbox[2], bbox[3], bbox[0])
        
        for time_val in da.time.values:
            daily_data = da.sel(time=time_val)
            day_date = pd.Timestamp(time_val).date()
            
            if dates_to_process and day_date not in dates_to_process:
                continue
            
            # Rename coords for rasterio
            coord_mapping = {}
            for coord in daily_data.dims:
                coord_lower = coord.lower()
                if coord_lower in ['longitude', 'lon']:
                    coord_mapping[coord] = 'x'
                elif coord_lower in ['latitude', 'lat']:
                    coord_mapping[coord] = 'y'
            
            if coord_mapping:
                daily_data = daily_data.rename(coord_mapping)
            
            daily_data = daily_data.rio.write_crs("EPSG:4326")
            
            try:
                daily_data = daily_data.rio.clip_box(*bbox)
            except Exception as e:
                logger.warning(f"Could not clip: {e}")
            
            output_path = output_dir / f"{output_dir.name}_{day_date.strftime('%Y%m%d')}.tif"
            daily_data.rio.to_raster(output_path, driver="COG", compress="LZW")
            processed_paths.append(output_path)
            logger.info(f"✓ Processed: {day_date}")
        
        return processed_paths
        
    except Exception as e:
        logger.error(f"✗ Failed to process: {e}")
        raise


@task
def append_to_historical_netcdf(
    source_netcdf: Path,
    source: str,
    bbox: tuple,
    dates_to_append: Optional[List[date]] = None
) -> Path:
    """
    Append NDVI data to historical NetCDF.

    FUSE FILESYSTEM FIX: Writes to /tmp first, then copies to final location.
    """
    logger = get_run_logger()
    settings = get_settings()

    dir_name = get_output_directory(source, settings).name
    hist_dir = Path(settings.DATA_DIR) / f"{dir_name}_hist"
    hist_dir.mkdir(parents=True, exist_ok=True)
    hist_file = hist_dir / "historical.nc"

    # FUSE FIX: Use /tmp for temporary writes
    import tempfile
    import shutil
    temp_dir = Path(tempfile.mkdtemp(prefix="ndvi_hist_"))
    temp_hist_file = temp_dir / "historical.nc"

    logger.info(f"Appending to: {hist_file}")
    logger.info(f"Using temp file: {temp_hist_file} (FUSE-safe write)")
    
    try:
        ds = xr.open_dataset(source_netcdf)
        da = ds['ndvi']
        
        # Standardize coords
        coord_mapping = {}
        for coord in da.dims:
            coord_lower = coord.lower()
            if coord_lower in ['longitude', 'lon']:
                coord_mapping[coord] = 'longitude'
            elif coord_lower in ['latitude', 'lat']:
                coord_mapping[coord] = 'latitude'
        
        if coord_mapping:
            da = da.rename(coord_mapping)
        
        # Filter dates - compare dates directly
        if dates_to_append:
            dates_to_keep = set(dates_to_append)
            time_mask = [pd.Timestamp(t).date() in dates_to_keep for t in da.time.values]
            da = da.isel(time=time_mask)
        
        # Append or create
        if hist_file.exists():
            # FUSE FIX: Copy existing file to temp location first
            logger.info(f"Copying existing historical file to temp for safe processing...")
            shutil.copy2(hist_file, temp_hist_file)

            existing = xr.open_dataset(temp_hist_file, chunks='auto')
            existing_dates = set(pd.to_datetime(existing['ndvi'].time.values).date)
            new_dates = set(pd.to_datetime(da.time.values).date)
            dates_to_add = new_dates - existing_dates

            if dates_to_add:
                dates_to_add_set = set(dates_to_add)
                time_mask = [pd.Timestamp(t).date() in dates_to_add_set for t in da.time.values]
                da_filtered = da.isel(time=time_mask)
                combined = xr.concat([existing['ndvi'], da_filtered], dim='time').sortby('time')
            else:
                logger.info("All dates exist")
                existing.close()
                ds.close()
                shutil.rmtree(temp_dir, ignore_errors=True)
                return hist_file

            existing.close()
        else:
            combined = da

        ds.close()

        hist_ds = combined.to_dataset(name='ndvi')
        encoding = {
            'ndvi': {
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

        # FUSE FIX: Write to temp file first
        logger.info(f"Writing to temp file (FUSE-safe): {temp_hist_file}")
        hist_ds.to_netcdf(temp_hist_file, mode='w', encoding=encoding, engine='netcdf4')

        # FUSE FIX: Copy completed file to final location
        logger.info(f"Copying to final location: {hist_file}")
        shutil.copy2(temp_hist_file, hist_file)

        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        logger.info(f"✓ Historical updated: {hist_file}")

        return hist_file

    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        # Cleanup temp directory on error
        try:
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        raise


@task
def append_to_yearly_historical_ndvi(
    source_netcdf: Path,
    source: str,
    bbox: tuple,
    dates_to_append: Optional[List[date]] = None
) -> List[Path]:
    """
    Append NDVI data to YEARLY historical NetCDF files.
    Creates separate files for each year: {source}_2015.nc, {source}_2016.nc, etc.

    FUSE FILESYSTEM FIX: Writes to /tmp first, then copies to final location.
    """
    logger = get_run_logger()
    settings = get_settings()
    import tempfile
    import shutil
    from collections import defaultdict

    dir_name = get_output_directory(source, settings).name
    hist_dir = Path(settings.DATA_DIR) / f"{dir_name}_hist"
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
        da = ds['ndvi']

        # Standardize coordinates
        coord_mapping = {}
        for coord in da.dims:
            coord_lower = coord.lower()
            if coord_lower in ['longitude', 'lon', 'long']:
                coord_mapping[coord] = 'longitude'
            elif coord_lower in ['latitude', 'lat']:
                coord_mapping[coord] = 'latitude'
        if coord_mapping:
            da = da.rename(coord_mapping)

        # Get and filter dates
        all_dates = set(pd.to_datetime(da.time.values).date)
        if dates_to_append:
            all_dates = all_dates & set(dates_to_append)
            # Filter to only dates we want to append - compare dates directly
            dates_to_keep = set(all_dates)
            time_mask = [pd.Timestamp(t).date() in dates_to_keep for t in da.time.values]
            da = da.isel(time=time_mask)

        logger.info(f"  Processing {len(all_dates)} dates")

        # Group dates by year
        dates_by_year = defaultdict(list)
        for d in all_dates:
            dates_by_year[d.year].append(d)

        logger.info(f"  Dates span {len(dates_by_year)} year(s): {sorted(dates_by_year.keys())}")

        # Process each year
        for year, year_dates in sorted(dates_by_year.items()):
            logger.info(f"\n  📅 Processing year {year} ({len(year_dates)} dates)")

            year_file = hist_dir / f"{dir_name}_{year}.nc"

            # FUSE FIX: Create temp directory for this year
            temp_dir = Path(tempfile.mkdtemp(prefix=f"ndvi_{year}_"))
            temp_file = temp_dir / f"{dir_name}_{year}.nc"

            try:
                # Extract data for this year - compare dates directly
                year_dates_set = set(year_dates)
                year_time_mask = [pd.Timestamp(t).date() in year_dates_set for t in da.time.values]
                year_da = da.isel(time=year_time_mask)

                # Check if yearly file already exists
                if year_file.exists():
                    logger.info(f"    Year file exists, checking for duplicates...")
                    # FUSE FIX: Copy to temp for safe processing
                    shutil.copy2(year_file, temp_file)
                    existing = xr.open_dataset(temp_file, chunks='auto')
                    existing_da = existing['ndvi']

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

                # Compute time range before writing (while data is still in memory)
                time_count = len(combined.time)
                if time_count > 0:
                    time_min = pd.Timestamp(combined.time.min().values).date()
                    time_max = pd.Timestamp(combined.time.max().values).date()

                # Convert to Dataset with encoding
                year_ds = combined.to_dataset(name='ndvi')
                year_ds.attrs['year'] = year

                encoding = {
                    'ndvi': {
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
                year_ds.to_netcdf(str(temp_file), mode='w', encoding=encoding, engine='netcdf4')

                logger.info(f"    Copying to: {year_file}")
                shutil.copy2(temp_file, year_file)

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
    """Delete raw NetCDF file."""
    logger = get_run_logger()
    try:
        if netcdf_path.exists():
            netcdf_path.unlink()
            logger.info(f"✓ Cleaned up: {netcdf_path.name}")
    except Exception as e:
        logger.warning(f"Could not delete: {e}")


@flow(
    name="process-ndvi-data",
    description="Download and process NDVI data - FREE via Microsoft Planetary Computer",
    retries=1,
    retry_delay_seconds=600
)
def ndvi_data_flow(
    batch_days: int = 16,
    sources: Optional[List[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """
    NDVI data processing flow.
    100% FREE - NO AUTHENTICATION REQUIRED!
    """
    logger = get_run_logger()
    settings = get_settings()
    
    if sources is None:
        sources = ['sentinel2', 'modis']
    
    # Default: last month
    if start_date is None or end_date is None:
        today = date.today()
        if end_date is None:
            first_day_current = today.replace(day=1)
            end_date = first_day_current - timedelta(days=1)
        if start_date is None:
            start_date = end_date.replace(day=1)
    
    logger.info("=" * 80)
    logger.info("NDVI DATA PROCESSING FLOW")
    logger.info("=" * 80)
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Sources: {', '.join(sources)}")
    logger.info("=" * 80)
    
    all_processed = []
    
    for source in sources:
        logger.info(f"\nProcessing: {source.upper()}")
        
        try:
            missing_info = check_missing_dates(start_date, end_date, source)
            missing_download = missing_info.get('download', [])
            missing_geotiff = missing_info.get('geotiff', [])
            missing_historical = missing_info.get('historical', [])
        except Exception as e:
            logger.error(f"Failed to check dates: {e}")
            continue
        
        if not missing_download:
            logger.info(f"✓ All data exists for {source}")
            continue
        
        # Group into batches
        date_batches = []
        if missing_download:
            current_start = missing_download[0]
            current_end = missing_download[0]
            
            for i in range(1, len(missing_download)):
                if missing_download[i] == current_end + timedelta(days=1):
                    current_end = missing_download[i]
                else:
                    date_batches.append((current_start, current_end))
                    current_start = missing_download[i]
                    current_end = missing_download[i]
            
            date_batches.append((current_start, current_end))
        
        # Process batches
        for batch_start, batch_end in date_batches:
            current_start = batch_start
            while current_start <= batch_end:
                current_end = min(current_start + timedelta(days=batch_days - 1), batch_end)
                
                chunk_dates = []
                d = current_start
                while d <= current_end:
                    chunk_dates.append(d)
                    d += timedelta(days=1)
                
                geotiff_dates = [d for d in chunk_dates if d in missing_geotiff]
                hist_dates = [d for d in chunk_dates if d in missing_historical]
                
                try:
                    logger.info(f"\nBatch: {current_start} to {current_end}")
                    
                    # Download
                    if source == 'sentinel2':
                        batch_path = download_sentinel2_batch(
                            current_start, current_end,
                            settings.latam_bbox_cds, 15.0
                        )
                    elif source == 'modis':
                        batch_path = download_modis_batch(
                            current_start, current_end,
                            settings.latam_bbox_cds
                        )
                    else:
                        logger.error(f"Unknown source: {source}")
                        continue
                    
                    # Process GeoTIFFs
                    if geotiff_dates:
                        processed = process_ndvi_to_geotiff(
                            batch_path, source,
                            settings.latam_bbox_raster,
                            geotiff_dates
                        )
                        all_processed.extend(processed)
                    
                    # Append to yearly historical
                    if hist_dates:
                        yearly_files = append_to_yearly_historical_ndvi(
                            batch_path, source,
                            settings.latam_bbox_raster,
                            hist_dates
                        )
                        logger.info(f"✓ Updated {len(yearly_files)} yearly historical file(s)")
                    
                    cleanup_raw_files(batch_path)
                    logger.info(f"✓ Completed batch")
                    
                except Exception as e:
                    logger.error(f"✗ Failed batch: {e}")
                
                current_start = current_end + timedelta(days=1)
    
    # Refresh mosaics
    if all_processed:
        try:
            from .tasks import refresh_mosaic_shapefile
            refresh_mosaic_shapefile(DataSource.NDVI)
        except Exception as e:
            logger.error(f"Failed to refresh mosaic: {e}")
    
    logger.info(f"\n✓ Processed {len(all_processed)} files")
    return all_processed


if __name__ == "__main__":
    print("=" * 80)
    print("NDVI DATA PROCESSING")
    print("=" * 80)
    print("\n🎉 100% FREE - NO AUTHENTICATION!")
    print("\nInstall: pip install pystac-client planetary-computer rasterio xarray netCDF4")
    print("\nBoth Sentinel-2 AND MODIS from Microsoft Planetary Computer")
    print("=" * 80)
    
    # Run for last month
    result = ndvi_data_flow()
    print(f"\n✓ Processed {len(result)} files")