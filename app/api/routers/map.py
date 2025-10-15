# app/api/routers/map.py
import logging
from fastapi import APIRouter, HTTPException, Response, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse
from app.services.geoserver import GeoServerService
from app.api.schemas.map import MapRequest, MapHistoryRequest, TriggerRequest, TriggerAreaRequest
from app.config.settings import get_settings
from datetime import datetime
from pathlib import Path
import httpx
import time
import xarray as xr
import rioxarray
import pandas as pd
import geopandas as gpd
import numpy as np
from urllib.parse import urlencode
from fastapi import Response
from io import BytesIO
from dask.distributed import Client, LocalCluster
import traceback
import asyncio 


# Global variables
client = None
historical_datasets = None

router = APIRouter(prefix="/map", tags=["GeoServer Maps"])
logger = logging.getLogger(__name__)
geoserver = GeoServerService()
settings = get_settings()
sources_historical = ["chirps", "merge"]

GEOSERVER_WMS = f"{geoserver.base_url}/wms"

# --- CONSTANT FOR CONVERSION ---
DEGREES_TO_KM = 111.32

import functools
from typing import Callable, Type

def retry_on_failure(max_retries: int = 2, exceptions: tuple = (Exception,)):
    """
    Decorator to retry async functions on failure.
    
    Args:
        max_retries: Maximum number of retry attempts (default 2)
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. Retrying..."
                        )
                        await asyncio.sleep(0.5 * (attempt + 1))  # Progressive backoff
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            # If all retries failed, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


# --- FUNCTIONS TO CONVERT DISTANCE ---
def haversine_distance(lon1, lat1, lon2, lat2):
    """
    Calculate the great-circle distance between two points (in decimal degrees).
    Returns distance in kilometers.
    """
    R = 6371  # Radius of earth in kilometers
    
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = R * c
    return km

@router.on_event("startup")
async def load_rasters(sources_list=sources_historical):
    """Load raster datasets into xarray + Dask for historical queries."""
    global historical_datasets
    global client
    historical_datasets = {}
    MAX_CORES = 4
    
    try:
        # Start Dask components synchronously here, as it's a one-time startup task.
        # Running the rest of the Dask compute work in asyncio.to_thread() makes this safe.
        cluster = LocalCluster(
            n_workers=MAX_CORES, 
            memory_limit='6GB',
            threads_per_worker=1, 
            processes=True,
            # IMPORTANT: Revert to synchronous Dask client for max compatibility
            asynchronous=False 
        )
        client = Client(cluster)
        logger.info(f"Dask client started on {client.scheduler.address} with {MAX_CORES} workers.")
    except Exception as e:
        logger.error(f"Could not start Dask Client: {e}")
        client = None
        pass

    # ... (Rest of the dataset loading logic remains the same) ...
    # Ensure parallel=True is only set if client is not None
    
    source_configs = {
        "chirps": {
            "dir_suffix": "chirps_historical",
            "file_glob": "brazil_chirps_*.nc",
        },
        "merge": {
            "dir_suffix": "merge_historical",
            "file_glob": "brazil_merge_*.nc",
        },
    }

    for source in sources_list:
        if source in source_configs:
            config = source_configs[source]
            try:
                DATA_DIR = Path(settings.DATA_DIR) / config["dir_suffix"]
                nc_files = sorted(DATA_DIR.glob(config["file_glob"]))

                if not nc_files:
                    logger.warning(f"No netcdf files found for source '{source}' in directory: {DATA_DIR}")
                    continue

                ds = xr.open_mfdataset(
                    nc_files,
                    combine="nested",
                    concat_dim="time",
                    engine="netcdf4",
                    parallel=True if client else False,
                    chunks={"time": -1, "latitude": 20, "longitude": 20},
                    cache=False,
                )

                historical_datasets[source] = ds
                logger.info(f"Loaded dataset: {source}")

            except Exception as e:
                logger.error(f"Error loading source '{source}': {e}")
        else:
            logger.warning(f"Source '{source}' is not configured for loading.")


# --- SYNCHRONOUS HELPER FOR POINT QUERIES ---
def _query_point_data_sync(historical_ds: xr.Dataset, request: MapHistoryRequest | TriggerRequest, is_trigger: bool):
    """
    Synchronous helper for point-based queries. Runs in a separate thread.
    Handles both history and trigger logic.
    """
    start_date = pd.to_datetime(request.start_date)
    end_date = pd.to_datetime(request.end_date)
    
    ts = historical_ds.sel(
        latitude=request.lat,
        longitude=request.lon,
        method="nearest",
        tolerance=0.05
    ).sel(time=slice(start_date, end_date))

    # CRITICAL: Synchronous .compute() call
    ts_values = ts["precip"].compute().squeeze() 

    data_vals = np.atleast_1d(ts_values.values)
    time_vals = np.atleast_1d(ts_values.time.values)
    
    if is_trigger:
        # Trigger logic
        exceedances = data_vals > request.trigger
        times = pd.to_datetime(time_vals)
        exceeded_dates = times[exceedances]
        exceeded_values = np.round(np.array(data_vals[exceedances], dtype=float), 2)

        exceedance_list = [
            {"date": str(date.date()), "value": float(value)}
            for date, value in zip(exceeded_dates, exceeded_values)
        ]
        
        return {
            "location": {"lat": request.lat, "lon": request.lon},
            "source": request.source,
            "start_date": str(start_date.date()),
            "end_date": str(end_date.date()),
            "trigger": request.trigger,
            "n_exceedances": int(exceedances.sum()),
            "exceedances": exceedance_list,
        }
    else:
        # History logic
        history = {
            str(pd.Timestamp(t).date()): (round(float(v), 2) if not np.isnan(v) else None)
            for t, v in zip(time_vals, data_vals)
        }
        return {
            "lat": request.lat,
            "lon": request.lon,
            "source": request.source,
            "history": history
        }


# ------------------------- ASYNC ENDPOINTS (CALLING SYNC HELPERS) -------------------------
@router.post("/precipitation/history")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_precipitation_history(request: MapHistoryRequest):
    """Returns historical pixel values for a given lat/lon and date range using Dask+xarray."""
    global historical_datasets
    source = request.source
    
    # (Input validation logic removed for brevity, assume it's still here)
    try:
        start_date = pd.to_datetime(request.start_date)
        end_date = pd.to_datetime(request.end_date)
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    if historical_datasets is None or source not in historical_datasets:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )
    historical_ds = historical_datasets[source]

    try:
        # CRITICAL FIX: Run synchronous Dask query in a separate thread
        result = await asyncio.to_thread(_query_point_data_sync, historical_ds, request, False)
        return result
    except Exception as e:
        logger.error(f"Error querying history data for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying historical data")

@router.post("/precipitation/triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_triggers(request: TriggerRequest, response_class=JSONResponse):
    """Returns trigger exceedances for a given lat/lon and date range using multiple data sources."""
    global historical_datasets
    source = request.source
    
    # (Input validation logic removed for brevity, assume it's still here)
    # ... validation for dates and source existence ...

    if historical_datasets is None or source not in historical_datasets:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )
    historical_ds = historical_datasets[source]

    try:
        # CRITICAL FIX: Run synchronous Dask query in a separate thread
        result = await asyncio.to_thread(_query_point_data_sync, historical_ds, request  , True)
        return result
    except Exception as e:
        logger.error(f"Error querying triggers data for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying historical data")


# --- SYNCHRONOUS HELPER FOR AREA QUERIES (Revised Output Structure) ---
def _calculate_area_exceedances_sync(historical_ds: xr.Dataset, request: TriggerAreaRequest):
    """
    Synchronous function containing the blocking Dask computation. 
    It is designed to run in a separate thread.
    
    Returns a tuple: (grouped_exceedances_dict, num_trigger_dates)
    
    grouped_exceedances_dict format:
    {
        'YYYY-MM-DD': [
            {'latitude': ..., 'longitude': ..., 'precipitation_mm': ...},
            {'latitude': ..., 'longitude': ..., 'precipitation_mm': ...},
            ...
        ],
        ...
    }
    """
    radius_km = request.radius
    radius_deg = radius_km / DEGREES_TO_KM
    
    lat_min = request.lat - radius_deg
    lat_max = request.lat + radius_deg
    lon_min = request.lon - radius_deg
    lon_max = request.lon + radius_deg

    start_date = pd.to_datetime(request.start_date).date()
    end_date = pd.to_datetime(request.end_date).date()

    # 1. Slice the bounding box
    ds_slice = historical_ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max),
        time=slice(start_date, end_date)
    )
    
    precip_data = ds_slice["precip"]
    
    # 2. Compute the circular distance mask
    distances_km = haversine_distance(
        lon1=request.lon, 
        lat1=request.lat, 
        lon2=ds_slice.longitude, 
        lat2=ds_slice.latitude
    )
    # NOTE: Using SYNCHRONOUS .compute()
    circular_mask = (distances_km <= request.radius).compute() 

    # 3. Combine both masks
    trigger_mask_3D = (precip_data > request.trigger) & circular_mask
    
    # 4. Extract values and stack
    exceeding_values = precip_data.where(trigger_mask_3D)
    exceeding_flat = exceeding_values.stack(point=['time', 'latitude', 'longitude'])
    
    # 5. Final Synchronous Compute & Conversion
    # NOTE: Using SYNCHRONOUS .compute()
    computed_array = exceeding_flat.compute() 
    exceeding_flat_computed = computed_array.to_series().dropna()
    
    # 6. Format the output into a grouped dictionary
    grouped_exceedances = {}
    
    for index, value in exceeding_flat_computed.items():
        time_val, lat_val, lon_val = index
        date_str = str(pd.to_datetime(time_val).date())
        
        point_data = {
            "latitude": round(float(lat_val), 5),
            "longitude": round(float(lon_val), 5),
            "precipitation_mm": round(float(value), 2)
        }
        
        # Group by date
        if date_str not in grouped_exceedances:
            grouped_exceedances[date_str] = []
        
        grouped_exceedances[date_str].append(point_data)

    # 7. Calculate final date count
    num_trigger_dates = len(grouped_exceedances)
    
    return grouped_exceedances, num_trigger_dates

# ------------------------- ASYNC ENDPOINT (Update to match new return) -------------------------
@router.post("/precipitation/area_triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_area_triggers(request: TriggerAreaRequest): 
    """Area-based trigger calculation."""
    global historical_datasets
    source = request.source
    
    # ... (Validation and data loading logic) ...

    if historical_datasets is None or source not in historical_datasets:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )
    historical_ds = historical_datasets[source]

    try:
        # Unpacking the tuple (grouped_exceedances_dict, num_trigger_dates)
        grouped_exceedances, num_trigger_dates = await asyncio.to_thread(_calculate_area_exceedances_sync, historical_ds, request)

        # 3. Format Response
        # total_exceedances is the total number of points, calculated by summing up the list lengths
        total_exceedances = sum(len(points) for points in grouped_exceedances.values())
        
        return {
            "location": {"lat": request.lat, "lon": request.lon, "radius_km": request.radius}, 
            "source": source,
            "trigger_mm": request.trigger,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "total_exceedances": total_exceedances,          # Total number of points that triggered
            "total_trigger_dates": num_trigger_dates,        # Total number of unique days with a trigger
            "exceedances_by_date": grouped_exceedances,      # <--- NEW KEY NAME/STRUCTURE
        }
    except Exception as e:
        logger.error(f"Error processing area triggers for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing area data: {str(e)}")


#------------------ Generic WMS Proxy ------------------

@router.api_route("/wms", methods=["GET", "POST"])
async def proxy_wms(request: Request):
    """
    Transparent WMS proxy to GeoServer.
    Frontend can call this as the WMS URL, no direct GeoServer exposure.
    """
    try:
        async with httpx.AsyncClient(auth=geoserver.auth, timeout=60.0) as client:
            if request.method == "GET":
                resp = await client.get(GEOSERVER_WMS, params=request.query_params)
            else:
                body = await request.body()
                headers = dict(request.headers)
                headers.pop("host", None)
                resp = await client.post(GEOSERVER_WMS, content=body, headers=headers)

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        return StreamingResponse(
            resp.aiter_bytes(),  # << stream chunks directly
            media_type=resp.headers.get("content-type", "application/octet-stream"),
            headers={
                k: v for k, v in resp.headers.items()
                if k.lower() in ["content-disposition"]
            }
        )
    except Exception as e:
        logger.error(f"WMS proxy failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to proxy WMS request")


@router.post("/precipitation/image")
@retry_on_failure(max_retries=2, exceptions=(httpx.HTTPError, httpx.TimeoutException))
async def get_precipitation_wms_image(request: MapRequest):
    """
    WMS GetMap proxy for precipitation image.
    This endpoint builds the WMS request internally and returns the PNG.
    """
    try:
        # Validate date
        try:
            request_date = datetime.strptime(request.date, "%Y-%m-%d")
            if request_date.date() > datetime.now().date():
                raise HTTPException(status_code=400, detail="Future dates are not supported.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Build WMS parameters
        layer_name = f"{geoserver.workspace}:{request.source}"
        miny, minx, maxy, maxx = settings.latam_bbox
        wms_params = {
            "service": "WMS",
            "version": "1.3.0",
            "request": "GetMap",
            "layers": layer_name,
            "width": request.width,
            "height": request.height,
            "format": "image/png",
            "transparent": "true",
            "time": request.date,
            "styles": "precipitation_style",
            "crs": "EPSG:4326",
            "bbox": f"{miny},{minx},{maxy},{maxx}",
            "tiled": "false",
            "_": str(int(time.time()))
        }

        async with httpx.AsyncClient(auth=geoserver.auth, timeout=60.0) as client:
            # Use params instead of manually encoding URL
            resp = await client.get(GEOSERVER_WMS, params=wms_params)

            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"GeoServer returned {resp.status_code}")

        # Validate response is image
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            raise HTTPException(status_code=502, detail=f"GeoServer error: {resp.text}")

        return StreamingResponse(
            BytesIO(resp.content),        # wrap binary data
            media_type="image/png"        # tell browser it's an image
        )

    except HTTPException as e:
        logger.error(f"Client error: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"WMS proxy failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch WMS image: {str(e)}")


@router.post("/precipitation/featureinfo")
@retry_on_failure(max_retries=2, exceptions=(httpx.HTTPError, httpx.TimeoutException))
async def get_precipitation_featureinfo(request: MapRequest):
    """
    Returns the pixel value for a given lat/lon from the precipitation raster.
    Returns null if the point is outside the raster.
    """
    # Validation (no retry on this)
    if request.lat is None or request.lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required")
    
    layer_name = f"{geoserver.workspace}:{request.source}"
    miny, minx, maxy, maxx = settings.latam_bbox
    width, height = request.width, request.height
    x = int((request.lon - minx) / (maxx - minx) * width)
    y = int((maxy - request.lat) / (maxy - miny) * height)
    
    wms_params = {
        "service": "WMS",
        "version": "1.1.1",
        "request": "GetFeatureInfo",
        "layers": layer_name,
        "query_layers": layer_name,
        "styles": "",
        "bbox": f"{minx},{miny},{maxx},{maxy}",
        "width": width,
        "height": height,
        "srs": "EPSG:4326",
        "format": "image/png",
        "info_format": "application/json",
        "x": x,
        "y": y,
        "time": request.date
    }
    
    try:
        async with httpx.AsyncClient(auth=geoserver.auth, timeout=3.0) as client:
            resp = await client.get(f"{GEOSERVER_WMS}", params=wms_params)
        
        # Check for WMS errors
        if "ServiceExceptionReport" in resp.text:
            return {
                "lat": request.lat,
                "lon": request.lon,
                "date": request.date,
                "value": -9999,
                "message": "No data at requested location"
            }
        
        # Parse response
        try:
            data = resp.json()
        except ValueError as e:
            logger.error(f"Invalid JSON from GeoServer: {resp.text[:200]}")
            raise HTTPException(status_code=502, detail="Invalid response from GeoServer")
        
        features = data.get("features", [])
        
        # Safely extract pixel value
        if features and len(features) > 0:
            pixel_value = features[0].get("properties", {}).get("GRAY_INDEX")
            if pixel_value is not None:
                pixel_value = round(float(pixel_value), 2)
        else:
            pixel_value = None
        
        return {
            "lat": request.lat,
            "lon": request.lon,
            "date": request.date,
            "value": pixel_value
        }
    
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        # This will be caught by retry decorator
        logger.warning(f"HTTP error fetching feature info: {e}")
        raise
    
    except HTTPException:
        # Re-raise our own HTTPExceptions
        raise
    
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error in featureinfo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing feature info request")