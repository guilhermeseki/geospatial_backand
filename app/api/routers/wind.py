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
from app.utils.dates import get_available_dates_from_dataset
from app.api.schemas.wind import (
    WindRequest,
    WindHistoryRequest,
    WindTriggerRequest,
    WindTriggerAreaRequest
)
from app.config.settings import get_settings
from app.config.data_sources import LAYER_DIMENSIONS, LAYER_BBOXES
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


# --- AVAILABLE DATES ENDPOINT ---

@router.get("/available_dates")
async def get_available_dates(full_list: bool = False):
    """
    Get available date range for wind speed data.

    Query params:
        full_list: If true, returns all dates (default: false, returns only min/max/count)

    Returns (full_list=false):
        {
            "min_date": "2015-01-01",
            "max_date": "2025-12-04",
            "total_dates": 3949
        }

    Returns (full_list=true):
        {
            "min_date": "2015-01-01",
            "max_date": "2025-12-04",
            "total_dates": 3949,
            "dates": ["2015-01-01", "2015-01-02", ...]
        }
    """
    try:
        ds = get_dataset('wind', 'wind_speed')

        if ds is None:
            raise HTTPException(
                status_code=503,
                detail="Wind speed data is not yet loaded"
            )

        # Get time values
        time_values = ds.time.values
        dates = [pd.Timestamp(t).date().isoformat() for t in time_values]

        result = {
            "min_date": dates[0] if dates else None,
            "max_date": dates[-1] if dates else None,
            "total_dates": len(dates)
        }

        # Only include full list if requested
        if full_list:
            result["dates"] = dates

        return result
    except Exception as e:
        logger.error(f"Error getting available dates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- OPTIONS ENDPOINTS FOR CORS ---

@router.options("/available_dates")
async def options_available_dates():
    """OPTIONS endpoint for CORS preflight - /available_dates"""
    return {}

@router.options("/history")
async def options_history():
    """OPTIONS endpoint for CORS preflight - /history"""
    return {}

@router.options("/triggers")
async def options_triggers():
    """OPTIONS endpoint for CORS preflight - /triggers"""
    return {}

@router.options("/area_triggers")
async def options_area_triggers():
    """OPTIONS endpoint for CORS preflight - /area_triggers"""
    return {}

@router.options("/wms")
async def options_wms():
    """OPTIONS endpoint for CORS preflight - /wms"""
    return {}

@router.options("/polygon")
async def options_polygon():
    """OPTIONS endpoint for CORS preflight - /polygon"""
    return {}

@router.options("/featureinfo")
async def options_featureinfo():
    """OPTIONS endpoint for CORS preflight - /featureinfo"""
    return {}


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
        # Note: No consecutive_days filter for wind - gusts are instantaneous events
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
            "source": "wind_speed",
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
    """
    Identify dates when wind speed exceeded a threshold at a specific location.

    Find all days within a date range where wind speed was above or below a
    specified threshold. Useful for storm detection, high wind analysis, etc.

    **Use Cases:**
    - High wind event detection (wind_speed > 15 m/s)
    - Calm period analysis (wind_speed < 2 m/s)
    - Wind power generation assessment
    - Climate risk assessment

    **Example Request (High Wind Detection):**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "trigger": 15.0,
        "trigger_type": "above"
    }
    ```

    **Example Response:**
    ```json
    {
        "location": {"lat": -15.8, "lon": -47.9},
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "trigger": 15.0,
        "trigger_type": "above",
        "n_exceedances": 3,
        "exceedances": [
            {"date": "2024-01-15", "value": 16.2},
            {"date": "2024-01-16", "value": 17.1},
            {"date": "2024-01-22", "value": 15.8}
        ]
    }
    ```
    """
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
    # Note: latitude is decreasing (north to south), so use lat_max first
    ds_slice = historical_ds.sel(
        latitude=slice(lat_max, lat_min),
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

        point_data = {
            "latitude": round(float(lat_val), 5),
            "longitude": round(float(lon_val), 5),
            "wind_speed_ms": round(float(value), 2)
        }

        if date_str not in grouped_exceedances:
            grouped_exceedances[date_str] = []

        grouped_exceedances[date_str].append(point_data)

    num_trigger_dates = len(grouped_exceedances)
    return grouped_exceedances, num_trigger_dates


@router.post("/area_triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_wind_area_triggers(request: WindTriggerAreaRequest):
    """
    Find wind speed threshold exceedances within a circular area.

    Searches for all grid points within a specified radius where wind speed
    exceeded a threshold. Returns exceedances grouped by date with coordinates.

    **Use Cases:**
    - Regional storm analysis
    - High wind risk mapping within zones
    - Wind power site assessment
    - Climate impact assessment for specific regions

    **Example Request (Basic):**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "radius": 50,
        "start_date": "2024-01-15",
        "end_date": "2024-01-20",
        "trigger": 15.0,
        "trigger_type": "above"
    }
    ```

    **Example Response:**
    ```json
    {
        "location": {"lat": -15.8, "lon": -47.9, "radius_km": 50},
        "trigger_ms": 15.0,
        "trigger_type": "above",
        "start_date": "2024-01-15",
        "end_date": "2024-01-20",
        "total_exceedances": 15,
        "total_trigger_dates": 2,
        "exceedances_by_date": {
            "2024-01-16": [
                {"latitude": -15.75, "longitude": -47.95, "wind_speed_ms": 16.2},
                {"latitude": -15.85, "longitude": -47.85, "wind_speed_ms": 15.8}
            ],
            "2024-01-17": [
                {"latitude": -15.75, "longitude": -47.95, "wind_speed_ms": 17.1}
            ]
        }
    }
    ```
    """
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

        total_exceedances = sum(len(points) for points in grouped_exceedances.values())

        return {
            "location": {"lat": request.lat, "lon": request.lon, "radius_km": request.radius},
            "trigger_ms": request.trigger,
            "trigger_type": request.trigger_type,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "total_exceedances": total_exceedances,
            "total_trigger_dates": num_trigger_dates,
            "exceedances_by_date": grouped_exceedances
        }

    except Exception as e:
        logger.error(f"Error calculating wind area triggers: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing area data: {str(e)}")


@router.get("/wms")
async def proxy_wind_wms(request: Request):
    """
    Proxy WMS requests to GeoServer for wind speed layer.
    This hides the internal GeoServer URL and provides a clean API endpoint.
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
            resp.aiter_bytes(),
            media_type=resp.headers.get("content-type", "application/octet-stream"),
            headers={
                k: v for k, v in resp.headers.items()
                if k.lower() in ["content-disposition"]
            }
        )
    except Exception as e:
        logger.error(f"WMS proxy failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to proxy WMS request")


@router.post("/featureinfo")
@retry_on_failure(max_retries=2, exceptions=(httpx.HTTPError, httpx.TimeoutException))
async def get_wind_featureinfo(request: WindRequest):
    """
    Get wind speed value at a specific location and date from GeoServer raster.

    This endpoint queries the GeoServer WMS layer directly using GetFeatureInfo,
    which is useful for validating map displays or getting values for a single date.
    For time-series queries, use `/history` endpoint instead (much faster).

    **Difference from /history:**
    - `/featureinfo`: Single date, queries GeoServer WMS layer (slower)
    - `/history`: Date range, queries NetCDF directly (faster, recommended)

    **Example Request:**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "date": "2024-01-15",
        "width": 1200,
        "height": 1560
    }
    ```

    **Example Response:**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "date": "2024-01-15",
        "value": 3.45
    }
    ```

    **Use Cases:**
    - Validating WMS layer rendering
    - Single-date wind speed lookup
    - Interactive map "click for value" functionality
    - Debugging GeoServer layer configuration
    """
    if request.lat is None or request.lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required")

    layer_name = "wind_ws:wind_speed"

    # Get actual bbox and dimensions for this specific layer
    west, south, east, north = LAYER_BBOXES.get("wind_speed", (-94.0, -53.0, -34.0, 25.0))
    width, height = LAYER_DIMENSIONS.get("wind_speed", (1200, 1560))

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
            "value": pixel_value
        }

    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning(f"HTTP error fetching wind feature info: {e}")
        raise

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error in wind featureinfo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing feature info request")


@router.post("/polygon")
async def wind_polygon(request: PolygonRequest):
    """
    Process polygon request for wind speed data.

    Example request:
    {
        "coordinates": [
            [-47.9, -15.8],
            [-47.8, -15.8],
            [-47.8, -15.9],
            [-47.9, -15.9]
        ],
        "source": "wind_speed",
        "start_date": "2023-06-01",
        "end_date": "2023-08-31",
        "trigger": 10.0,
        "statistic": "max"
    }
    """
    # Validate source (wind only has one source)
    if request.source.lower() not in ['wind_speed', 'wind']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source for wind. Must be 'wind_speed' or 'wind'"
        )

    # Get dataset
    ds = get_dataset('wind', 'wind_speed')

    if ds is None:
        raise HTTPException(
            status_code=503,
            detail=f"Wind speed data is not loaded"
        )

    try:
        # Process in thread pool
        result = await asyncio.to_thread(
            _process_wind_polygon_sync,
            ds,
            request
        )

        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing polygon request: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


def _process_wind_polygon_sync(ds, request: PolygonRequest):
    """Synchronous helper for wind polygon processing."""
    variable_name = 'wind_speed'

    # Create polygon
    polygon = PolygonProcessor.create_polygon_from_coords(request.coordinates)

    # Process request
    result = PolygonProcessor.process_polygon_request(
        ds=ds,
        polygon=polygon,
        variable_name=variable_name,
        start_date=request.start_date,
        end_date=request.end_date,
        statistic=request.statistic,
        trigger=request.trigger
    )

    # Add source and variable to metadata
    result["metadata"]["source"] = "wind_speed"
    result["metadata"]["variable_name"] = variable_name

    return result
