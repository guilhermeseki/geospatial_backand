# app/api/routers/temperature.py
"""
Temperature API endpoints (ERA5 temp_max, temp_min, temp)
Uses shared climate data service with shared Dask client
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.services.geoserver import GeoServerService
from app.services.climate_data import get_dataset
from app.utils.geo import haversine_distance, retry_on_failure, DEGREES_TO_KM
from app.api.schemas.era5 import (
    ERA5Request, 
    ERA5HistoryRequest, 
    ERA5TriggerRequest, 
    ERA5TriggerAreaRequest
)
from app.config.settings import get_settings
from datetime import datetime
import httpx
import time
import xarray as xr
import pandas as pd
import numpy as np
from io import BytesIO
import asyncio
import traceback

router = APIRouter(prefix="/temperature", tags=["Temperature"])
logger = logging.getLogger(__name__)
geoserver = GeoServerService()
settings = get_settings()

GEOSERVER_WMS = f"{geoserver.base_url}/wms"

# ERA5 sources - temperature variables
TEMPERATURE_SOURCES = ["temp_max", "temp_min", "temp"]


# --- SYNCHRONOUS HELPER FOR POINT QUERIES ---
def _query_temperature_point_data_sync(
    historical_ds: xr.Dataset, 
    request: ERA5HistoryRequest | ERA5TriggerRequest, 
    variable_name: str,
    is_trigger: bool
):
    """
    Synchronous helper for temperature point-based queries.
    Handles both history and trigger logic for temperature data.
    """
    start_date = pd.to_datetime(request.start_date)
    end_date = pd.to_datetime(request.end_date)
    
    ts = historical_ds.sel(
        latitude=request.lat,
        longitude=request.lon,
        method="nearest",
        tolerance=0.05
    ).sel(time=slice(start_date, end_date))

    # Get the temperature variable (temp_max, temp_min, or temp)
    ts_values = ts[variable_name].compute().squeeze()

    data_vals = np.atleast_1d(ts_values.values)
    time_vals = np.atleast_1d(ts_values.time.values)
    
    if is_trigger:
        # Trigger logic - temperature threshold exceedances
        if request.trigger_type == "above":
            exceedances = data_vals > request.trigger
        else:  # below
            exceedances = data_vals < request.trigger
            
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
            "trigger_type": request.trigger_type,
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


# --- ASYNC ENDPOINTS ---
@router.post("/history")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_temperature_history(request: ERA5HistoryRequest):
    """Returns historical temperature values for a given lat/lon and date range."""
    source = request.source
    
    # Validate dates
    try:
        start_date = pd.to_datetime(request.start_date)
        end_date = pd.to_datetime(request.end_date)
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    # Validate source
    if source not in TEMPERATURE_SOURCES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid source. Must be one of: {', '.join(TEMPERATURE_SOURCES)}"
        )
    
    # Get dataset from shared service
    historical_ds = get_dataset('temperature', source)
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )

    try:
        result = await asyncio.to_thread(
            _query_temperature_point_data_sync, 
            historical_ds, 
            request, 
            source,  # variable name
            False
        )
        return result
    except Exception as e:
        logger.error(f"Error querying temperature history for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying historical temperature data")


@router.post("/triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_temperature_triggers(request: ERA5TriggerRequest):
    """Returns temperature threshold exceedances for a given lat/lon and date range."""
    source = request.source
    
    # Validate source
    if source not in TEMPERATURE_SOURCES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid source. Must be one of: {', '.join(TEMPERATURE_SOURCES)}"
        )

    # Get dataset from shared service
    historical_ds = get_dataset('temperature', source)
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )

    try:
        result = await asyncio.to_thread(
            _query_temperature_point_data_sync, 
            historical_ds, 
            request,
            source,  # variable name
            True
        )
        return result
    except Exception as e:
        logger.error(f"Error querying temperature triggers for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying temperature trigger data")


# --- SYNCHRONOUS HELPER FOR AREA QUERIES ---
def _calculate_temperature_area_exceedances_sync(
    historical_ds: xr.Dataset, 
    request: ERA5TriggerAreaRequest,
    variable_name: str
):
    """
    Synchronous function for temperature area-based trigger calculation.
    Returns: (grouped_exceedances_dict, num_trigger_dates)
    """
    radius_km = request.radius
    radius_deg = radius_km / DEGREES_TO_KM
    
    lat_min = request.lat - radius_deg
    lat_max = request.lat + radius_deg
    lon_min = request.lon - radius_deg
    lon_max = request.lon + radius_deg

    start_date = pd.to_datetime(request.start_date).date()
    end_date = pd.to_datetime(request.end_date).date()

    # Slice the bounding box
    ds_slice = historical_ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max),
        time=slice(start_date, end_date)
    )
    
    temp_data = ds_slice[variable_name]
    
    # Compute circular distance mask
    distances_km = haversine_distance(
        lon1=request.lon, 
        lat1=request.lat, 
        lon2=ds_slice.longitude, 
        lat2=ds_slice.latitude
    )
    circular_mask = (distances_km <= request.radius).compute()

    # Apply trigger condition
    if request.trigger_type == "above":
        trigger_mask_3D = (temp_data > request.trigger) & circular_mask
    else:  # below
        trigger_mask_3D = (temp_data < request.trigger) & circular_mask
    
    # Extract values
    exceeding_values = temp_data.where(trigger_mask_3D)
    exceeding_flat = exceeding_values.stack(point=['time', 'latitude', 'longitude'])
    
    # Compute and convert
    computed_array = exceeding_flat.compute()
    exceeding_flat_computed = computed_array.to_series().dropna()
    
    # Format output
    grouped_exceedances = {}
    
    for index, value in exceeding_flat_computed.items():
        time_val, lat_val, lon_val = index
        date_str = str(pd.to_datetime(time_val).date())
        
        point_data = {
            "latitude": round(float(lat_val), 5),
            "longitude": round(float(lon_val), 5),
            "temperature_c": round(float(value), 2)
        }
        
        if date_str not in grouped_exceedances:
            grouped_exceedances[date_str] = []
        
        grouped_exceedances[date_str].append(point_data)

    num_trigger_dates = len(grouped_exceedances)
    
    return grouped_exceedances, num_trigger_dates


@router.post("/area_triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_temperature_area_triggers(request: ERA5TriggerAreaRequest):
    """Area-based temperature trigger calculation."""
    source = request.source
    
    # Validate source
    if source not in TEMPERATURE_SOURCES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid source. Must be one of: {', '.join(TEMPERATURE_SOURCES)}"
        )

    # Get dataset from shared service
    historical_ds = get_dataset('temperature', source)
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )

    try:
        grouped_exceedances, num_trigger_dates = await asyncio.to_thread(
            _calculate_temperature_area_exceedances_sync, 
            historical_ds, 
            request,
            source  # variable name
        )

        total_exceedances = sum(len(points) for points in grouped_exceedances.values())
        
        return {
            "location": {"lat": request.lat, "lon": request.lon, "radius_km": request.radius},
            "source": source,
            "trigger_c": request.trigger,
            "trigger_type": request.trigger_type,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "total_exceedances": total_exceedances,
            "total_trigger_dates": num_trigger_dates,
            "exceedances_by_date": grouped_exceedances,
        }
    except Exception as e:
        logger.error(f"Error processing temperature area triggers for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing area data: {str(e)}")


# --- WMS ENDPOINTS ---

@router.post("/image")
@retry_on_failure(max_retries=2, exceptions=(httpx.HTTPError, httpx.TimeoutException))
async def get_temperature_wms_image(request: ERA5Request):
    """WMS GetMap proxy for temperature image."""
    try:
        # Validate date
        try:
            request_date = datetime.strptime(request.date, "%Y-%m-%d")
            if request_date.date() > datetime.now().date():
                raise HTTPException(status_code=400, detail="Future dates are not supported.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Validate source
        if request.source not in TEMPERATURE_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Must be one of: {', '.join(TEMPERATURE_SOURCES)}"
            )

        # Build WMS parameters
        layer_name = f"era5_ws:{request.source}"
        north, west, south, east = settings.latam_bbox_cds  # [N, W, S, E]
        
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
            "styles": "temperature_style",
            "crs": "EPSG:4326",
            "bbox": f"{south},{west},{north},{east}",  # WMS 1.3.0 uses lat,lon order
            "tiled": "false",
            "_": str(int(time.time()))
        }

        async with httpx.AsyncClient(auth=geoserver.auth, timeout=60.0) as client:
            resp = await client.get(GEOSERVER_WMS, params=wms_params)

            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"GeoServer returned {resp.status_code}")

        # Validate response is image
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            raise HTTPException(status_code=502, detail=f"GeoServer error: {resp.text}")

        return StreamingResponse(
            BytesIO(resp.content),
            media_type="image/png"
        )

    except HTTPException as e:
        logger.error(f"Client error: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"WMS proxy failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch WMS image: {str(e)}")


@router.post("/featureinfo")
@retry_on_failure(max_retries=2, exceptions=(httpx.HTTPError, httpx.TimeoutException))
async def get_temperature_featureinfo(request: ERA5Request):
    """Returns the temperature value for a given lat/lon from the ERA5 raster."""
    if request.lat is None or request.lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required")
    
    # Validate source
    if request.source not in TEMPERATURE_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {', '.join(TEMPERATURE_SOURCES)}"
        )
    
    layer_name = f"era5_ws:{request.source}"
    north, west, south, east = settings.latam_bbox_cds
    width, height = request.width, request.height
    
    # Calculate pixel coordinates
    x = int((request.lon - west) / (east - west) * width)
    y = int((north - request.lat) / (north - south) * height)
    
    wms_params = {
        "service": "WMS",
        "version": "1.1.1",
        "request": "GetFeatureInfo",
        "layers": layer_name,
        "query_layers": layer_name,
        "styles": "",
        "bbox": f"{west},{south},{east},{north}",
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
            resp = await client.get(GEOSERVER_WMS, params=wms_params)
        
        if "ServiceExceptionReport" in resp.text:
            return {
                "lat": request.lat,
                "lon": request.lon,
                "date": request.date,
                "value": None,
                "message": "No data at requested location"
            }
        
        try:
            data = resp.json()
        except ValueError as e:
            logger.error(f"Invalid JSON from GeoServer: {resp.text[:200]}")
            raise HTTPException(status_code=502, detail="Invalid response from GeoServer")
        
        features = data.get("features", [])
        
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
            "source": request.source,
            "temperature_c": pixel_value
        }
    
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning(f"HTTP error fetching feature info: {e}")
        raise
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in featureinfo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing feature info request")