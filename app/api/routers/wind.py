# app/api/routers/wind.py
"""
Wind Speed API endpoints (ERA5 Land wind_speed)
Uses shared climate data service with shared Dask client
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.services.geoserver import GeoServerService
from app.services.climate_data import get_dataset
from app.api.schemas.polygon import PolygonRequest
from app.utils.polygon import PolygonProcessor
from app.utils.geo import haversine_distance, retry_on_failure, DEGREES_TO_KM
from app.api.schemas.wind import (
    WindRequest,
    WindHistoryRequest,
    WindTriggerRequest,
    WindTriggerAreaRequest
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

router = APIRouter(prefix="/wind", tags=["Wind"])
logger = logging.getLogger(__name__)
geoserver = GeoServerService()
settings = get_settings()

GEOSERVER_WMS = f"{geoserver.base_url}/wms"


# --- SYNCHRONOUS HELPER FOR POINT QUERIES ---
def _query_wind_point_data_sync(
    historical_ds: xr.Dataset, 
    request: WindHistoryRequest | WindTriggerRequest, 
    is_trigger: bool
):
    """
    Synchronous helper for wind speed point-based queries.
    Handles both history and trigger logic for wind data.
    """
    start_date = pd.to_datetime(request.start_date)
    end_date = pd.to_datetime(request.end_date)
    
    ts = historical_ds.sel(
        latitude=request.lat,
        longitude=request.lon,
        method="nearest",
        tolerance=0.05
    ).sel(time=slice(start_date, end_date))

    # Get the wind_speed variable
    ts_values = ts['wind_speed'].compute().squeeze()

    data_vals = np.atleast_1d(ts_values.values)
    time_vals = np.atleast_1d(ts_values.time.values)
    
    if is_trigger:
        # Trigger logic - wind speed threshold exceedances
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
            "history": history
        }


# --- ASYNC ENDPOINTS ---
@router.post("/history")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_wind_history(request: WindHistoryRequest):
    """Returns historical wind speed values for a given lat/lon and date range."""
    
    # Validate dates
    try:
        start_date = pd.to_datetime(request.start_date)
        end_date = pd.to_datetime(request.end_date)
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    # Get dataset from shared service
    historical_ds = get_dataset('wind', 'wind_speed')
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Wind speed historical data is not yet loaded or is unavailable."
        )

    try:
        result = await asyncio.to_thread(
            _query_wind_point_data_sync, 
            historical_ds, 
            request, 
            False
        )
        return result
    except Exception as e:
        logger.error(f"Error querying wind history: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying historical wind data")


@router.post("/triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_wind_triggers(request: WindTriggerRequest):
    """Returns wind speed threshold exceedances for a given lat/lon and date range."""
    
    # Get dataset from shared service
    historical_ds = get_dataset('wind', 'wind_speed')
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Wind speed historical data is not yet loaded or is unavailable."
        )

    try:
        result = await asyncio.to_thread(
            _query_wind_point_data_sync, 
            historical_ds, 
            request,
            True
        )
        return result
    except Exception as e:
        logger.error(f"Error querying wind triggers: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying wind trigger data")


# --- SYNCHRONOUS HELPER FOR AREA QUERIES ---
def _calculate_wind_area_exceedances_sync(
    historical_ds: xr.Dataset, 
    request: WindTriggerAreaRequest
):
    """
    Synchronous function for wind speed area-based trigger calculation.
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
    
    wind_data = ds_slice['wind_speed']
    
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
        trigger_mask_3D = (wind_data > request.trigger) & circular_mask
    else:  # below
        trigger_mask_3D = (wind_data < request.trigger) & circular_mask
    
    # Extract values
    exceeding_values = wind_data.where(trigger_mask_3D)
    exceeding_flat = exceeding_values.stack(point=['time', 'latitude', 'longitude'])
    
    # Compute and convert
    computed_array = exceeding_flat.compute()
    exceeding_flat_computed = computed_array.to_series().dropna()
    
    # Format output
    grouped_exceedances = {}
    
    for index, value in exceeding_flat_computed.items():
        time_val, lat_val, lon_val = index
        date_str = str(pd.Timestamp(time_val).date())
        
        if date_str not in grouped_exceedances:
            grouped_exceedances[date_str] = []
        
        grouped_exceedances[date_str].append({
            "lat": round(float(lat_val), 4),
            "lon": round(float(lon_val), 4),
            "value": round(float(value), 2)
        })

    num_trigger_dates = len(grouped_exceedances)
    return grouped_exceedances, num_trigger_dates


@router.post("/triggers/area")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_wind_area_triggers(request: WindTriggerAreaRequest):
    """Returns wind speed threshold exceedances in a circular area."""
    
    # Get dataset
    historical_ds = get_dataset('wind', 'wind_speed')
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Wind speed historical data is not yet loaded or is unavailable."
        )

    try:
        # Run computation in thread pool
        grouped_exceedances, num_trigger_dates = await asyncio.to_thread(
            _calculate_wind_area_exceedances_sync,
            historical_ds,
            request
        )

        return {
            "center": {"lat": request.lat, "lon": request.lon},
            "radius_km": request.radius,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "trigger": request.trigger,
            "trigger_type": request.trigger_type,
            "n_trigger_dates": num_trigger_dates,
            "exceedances_by_date": grouped_exceedances
        }

    except Exception as e:
        logger.error(f"Error calculating wind area triggers: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error calculating wind area trigger data")


@router.get("/wms")
async def proxy_wind_wms(request: Request):
    """
    Proxy WMS requests to GeoServer for wind speed layer.
    This hides the internal GeoServer URL and provides a clean API endpoint.
    """
    query_params = dict(request.query_params)
    
    # Ensure we're requesting the wind_speed layer from wind_ws workspace
    if 'layers' not in query_params:
        query_params['layers'] = 'wind_ws:wind_speed'
    
    # Default to WMS if service not specified
    if 'service' not in query_params:
        query_params['service'] = 'WMS'
    
    # Construct GeoServer WMS URL
    geoserver_wms_url = f"{geoserver.base_url}/wind_ws/wms"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(geoserver_wms_url, params=query_params)
            
            return StreamingResponse(
                iter([response.content]),
                media_type=response.headers.get('content-type', 'image/png'),
                headers={'Cache-Control': 'public, max-age=3600'}
            )
    except Exception as e:
        logger.error(f"WMS proxy error: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch WMS data from GeoServer")


@router.post("/polygon")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_wind_polygon(request: PolygonRequest):
    """Calculate statistics for wind speed within a polygon area."""
    
    # Get dataset
    historical_ds = get_dataset('wind', 'wind_speed')
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503,
            detail="Wind speed historical data is not yet loaded or is unavailable."
        )
    
    try:
        # Use PolygonProcessor for computation
        processor = PolygonProcessor(historical_ds, 'wind_speed')
        
        result = await asyncio.to_thread(
            processor.calculate_polygon_stats,
            request
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating wind polygon stats: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error calculating polygon statistics")
