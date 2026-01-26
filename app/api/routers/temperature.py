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
from app.api.schemas.polygon import PolygonRequest
from app.utils.polygon import PolygonProcessor
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

# Import centralized data source configuration
from app.config.data_sources import TEMPERATURE_SOURCES, LAYER_DIMENSIONS, LAYER_BBOXES, TEMPERATURE_VAR_NAMES


# --- OPTIONS ENDPOINTS FOR CORS ---

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

@router.options("/featureinfo")
async def options_featureinfo():
    """OPTIONS endpoint for CORS preflight - /featureinfo"""
    return {}

@router.options("/polygon")
async def options_polygon():
    """OPTIONS endpoint for CORS preflight - /polygon"""
    return {}


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
        method="nearest"
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

        # Apply consecutive days filter if requested
        if request.consecutive_days and request.consecutive_days > 1:
            # Build list of (date, value) tuples where trigger was met
            date_value_pairs = [
                (times[i].date(), data_vals[i])
                for i in range(len(times))
                if exceedances[i]
            ]

            # Find consecutive sequences
            valid_dates = set()
            consecutive_count = 1
            for i in range(1, len(date_value_pairs)):
                if (date_value_pairs[i][0] - date_value_pairs[i-1][0]).days == 1:
                    consecutive_count += 1
                    if consecutive_count >= request.consecutive_days:
                        # Add all dates in this consecutive sequence
                        for j in range(i - consecutive_count + 1, i + 1):
                            valid_dates.add(date_value_pairs[j][0])
                else:
                    consecutive_count = 1

            # Filter exceedances to only include valid dates
            exceedance_list = [
                {"date": str(date.date()), "value": float(value)}
                for date, value in zip(times[exceedances], data_vals[exceedances])
                if date.date() in valid_dates
            ]
        else:
            # No consecutive days filter - return all exceedances
            exceeded_dates = times[exceedances]
            exceeded_values = np.round(np.array(data_vals[exceedances], dtype=float), 2)
            exceedance_list = [
                {"date": str(date.date()), "value": float(value)}
                for date, value in zip(exceeded_dates, exceeded_values)
            ]

        result = {
            "location": {"lat": request.lat, "lon": request.lon},
            "source": request.source,
            "start_date": str(start_date.date()),
            "end_date": str(end_date.date()),
            "trigger": request.trigger,
            "trigger_type": request.trigger_type,
            "n_exceedances": len(exceedance_list),
            "exceedances": exceedance_list,
        }

        if request.consecutive_days and request.consecutive_days > 1:
            result["consecutive_days"] = request.consecutive_days

        return result
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
    """
    Get historical temperature time series for a specific location.

    Returns daily temperature values (in Celsius) from ERA5-Land reanalysis data
    for a given location and date range.

    **Data Sources:**
    - `temp_max`: Daily maximum temperature at 2m height
    - `temp_min`: Daily minimum temperature at 2m height
    - `temp_mean`: Daily mean temperature at 2m height

    **Spatial Resolution:** ~9km (0.1°)

    **Temporal Coverage:** 2015-2024 (updated regularly, ~7 day lag)

    **Example Request:**
    ```json
    {
        "source": "temp_max",
        "lat": -15.8,
        "lon": -47.9,
        "start_date": "2024-01-01",
        "end_date": "2024-01-07"
    }
    ```

    **Example Response:**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "source": "temp_max",
        "history": {
            "2024-01-01": 28.5,
            "2024-01-02": 29.3,
            "2024-01-03": 27.8,
            "2024-01-04": 30.1,
            "2024-01-05": 29.7,
            "2024-01-06": 28.9,
            "2024-01-07": 27.5
        }
    }
    ```
    """
    logger.info(f"[DEBUG] Received temperature history request: source={request.source}, lat={request.lat}, lon={request.lon}, dates={request.start_date} to {request.end_date}")
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
    """
    Identify dates when temperature exceeded a threshold at a specific location.

    Find all days within a date range where temperature was above or below a
    specified threshold. Useful for heatwave detection, frost analysis, etc.

    **Use Cases:**
    - Heatwave detection (temp_max > 35°C)
    - Frost events (temp_min < 0°C)
    - Growing degree days calculation
    - Climate risk assessment

    **Example Request (Heatwave Detection):**
    ```json
    {
        "source": "temp_max",
        "lat": -15.8,
        "lon": -47.9,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "trigger": 35.0,
        "trigger_type": "above"
    }
    ```

    **Example Response:**
    ```json
    {
        "location": {"lat": -15.8, "lon": -47.9},
        "source": "temp_max",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "trigger": 35.0,
        "trigger_type": "above",
        "n_exceedances": 3,
        "exceedances": [
            {"date": "2024-01-15", "value": 36.2},
            {"date": "2024-01-16", "value": 37.1},
            {"date": "2024-01-22", "value": 35.8}
        ]
    }
    ```
    """
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
    logger.info(f"[DEBUG area_triggers] Starting calculation for {variable_name}")
    logger.info(f"[DEBUG area_triggers] Request: lat={request.lat}, lon={request.lon}, radius={request.radius}km, trigger={request.trigger}, type={request.trigger_type}, consecutive_days={request.consecutive_days}")

    radius_km = request.radius
    radius_deg = radius_km / DEGREES_TO_KM

    lat_min = request.lat - radius_deg
    lat_max = request.lat + radius_deg
    lon_min = request.lon - radius_deg
    lon_max = request.lon + radius_deg

    start_date = pd.to_datetime(request.start_date).date()
    end_date = pd.to_datetime(request.end_date).date()

    logger.info(f"[DEBUG area_triggers] Bounding box: lat [{lat_min:.2f}, {lat_max:.2f}], lon [{lon_min:.2f}, {lon_max:.2f}]")
    logger.info(f"[DEBUG area_triggers] Date range: {start_date} to {end_date}")

    # FIX: Check latitude order to handle both ascending and descending coordinates
    # xarray slice requires the slice bounds to match the coordinate order
    lat_coords = historical_ds.latitude.values
    lat_ascending = lat_coords[0] < lat_coords[-1]

    if lat_ascending:
        lat_slice = slice(lat_min, lat_max)
    else:
        # Descending order: swap min/max for slice
        lat_slice = slice(lat_max, lat_min)

    # Slice the bounding box
    ds_slice = historical_ds.sel(
        latitude=lat_slice,
        longitude=slice(lon_min, lon_max),
        time=slice(start_date, end_date)
    )

    logger.info(f"[DEBUG area_triggers] Sliced dataset shape: {ds_slice.dims}")
    
    temp_data = ds_slice[variable_name]
    logger.info(f"[DEBUG area_triggers] temp_data shape: {temp_data.shape}")

    # Compute circular distance mask
    distances_km = haversine_distance(
        lon1=request.lon,
        lat1=request.lat,
        lon2=ds_slice.longitude,
        lat2=ds_slice.latitude
    )
    circular_mask = (distances_km <= request.radius).compute()
    n_in_circle = circular_mask.sum().values
    logger.info(f"[DEBUG area_triggers] Grid points within {request.radius}km: {n_in_circle}")

    # Apply trigger condition
    if request.trigger_type == "above":
        trigger_mask_3D = (temp_data > request.trigger) & circular_mask
    else:  # below
        trigger_mask_3D = (temp_data < request.trigger) & circular_mask

    logger.info(f"[DEBUG area_triggers] Computing trigger mask...")
    trigger_computed = trigger_mask_3D.compute()
    n_exceedances_raw = trigger_computed.sum().values
    logger.info(f"[DEBUG area_triggers] Raw exceedances (before consecutive filter): {n_exceedances_raw}")

    # Check if there are any exceedances before stacking
    if n_exceedances_raw == 0:
        logger.info(f"[DEBUG area_triggers] No exceedances found, returning empty result")
        return {}, 0

    # Extract values and compute BEFORE stacking to avoid dask reshape issues
    exceeding_values = temp_data.where(trigger_computed)
    logger.info(f"[DEBUG area_triggers] Computing exceeding values...")
    exceeding_values_computed = exceeding_values.compute()

    # Now stack the computed array (numpy operation, no dask reshape issues)
    exceeding_flat = exceeding_values_computed.stack(point=['time', 'latitude', 'longitude'])
    exceeding_flat_computed = exceeding_flat.to_series().dropna()
    logger.info(f"[DEBUG area_triggers] Exceeding flat computed length: {len(exceeding_flat_computed)}")

    # Check for consecutive days if requested
    if request.consecutive_days and request.consecutive_days > 1:
        # Reorganize by (lat, lon) to check consecutive dates
        from collections import defaultdict
        points_by_location = defaultdict(list)

        for index, value in exceeding_flat_computed.items():
            time_val, lat_val, lon_val = index
            date_val = pd.to_datetime(time_val).date()
            points_by_location[(lat_val, lon_val)].append((date_val, value))

        # Filter points that meet consecutive day requirement
        valid_points = {}
        for (lat_val, lon_val), date_values in points_by_location.items():
            # Sort by date
            date_values.sort(key=lambda x: x[0])
            dates = [dv[0] for dv in date_values]

            # Find consecutive sequences
            consecutive_count = 1
            for i in range(1, len(dates)):
                if (dates[i] - dates[i-1]).days == 1:
                    consecutive_count += 1
                    if consecutive_count >= request.consecutive_days:
                        # This location meets the requirement
                        # Include all dates in the consecutive sequence
                        for j in range(i - consecutive_count + 1, i + 1):
                            key = (dates[j], lat_val, lon_val)
                            valid_points[key] = date_values[j][1]
                else:
                    consecutive_count = 1

        # Rebuild exceeding_flat_computed with only valid points
        exceeding_flat_computed = pd.Series(valid_points)

    # Format output
    grouped_exceedances = {}

    for index, value in exceeding_flat_computed.items():
        if request.consecutive_days and request.consecutive_days > 1:
            date_val, lat_val, lon_val = index
            date_str = str(date_val)
        else:
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
    """
    Find temperature threshold exceedances within a circular area.

    Searches for all grid points within a specified radius where temperature
    exceeded a threshold. Returns exceedances grouped by date with coordinates.

    **Use Cases:**
    - Regional heatwave analysis (3+ consecutive days above threshold)
    - Frost risk mapping within agricultural zones
    - Urban heat island detection
    - Climate impact assessment for specific regions

    **Parameters:**
    - `consecutive_days` (optional): Minimum number of consecutive days the trigger
      condition must be met. If specified, only returns grid points where the
      temperature exceeded/fell below the threshold for N+ consecutive days.
      Perfect for detecting heatwaves or cold spells.

    **Example Request (Basic):**
    ```json
    {
        "source": "temp_max",
        "lat": -15.8,
        "lon": -47.9,
        "radius": 50,
        "start_date": "2024-01-15",
        "end_date": "2024-01-20",
        "trigger": 35.0,
        "trigger_type": "above"
    }
    ```

    **Example Request (Heatwave Detection - 3 consecutive days):**
    ```json
    {
        "source": "temp_max",
        "lat": -15.8,
        "lon": -47.9,
        "radius": 50,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "trigger": 30.0,
        "trigger_type": "above",
        "consecutive_days": 3
    }
    ```

    **Example Response:**
    ```json
    {
        "location": {"lat": -15.8, "lon": -47.9, "radius_km": 50},
        "source": "temp_max",
        "trigger_c": 35.0,
        "trigger_type": "above",
        "start_date": "2024-01-15",
        "end_date": "2024-01-20",
        "consecutive_days": 3,
        "total_exceedances": 15,
        "total_trigger_dates": 2,
        "exceedances_by_date": {
            "2024-01-16": [
                {"latitude": -15.75, "longitude": -47.95, "temperature_c": 36.2},
                {"latitude": -15.85, "longitude": -47.85, "temperature_c": 35.8}
            ],
            "2024-01-17": [
                {"latitude": -15.75, "longitude": -47.95, "temperature_c": 37.1}
            ]
        }
    }
    ```
    """
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
        
        result = {
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

        if request.consecutive_days:
            result["consecutive_days"] = request.consecutive_days

        return result
    except Exception as e:
        logger.error(f"Error processing temperature area triggers for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing area data: {str(e)}")


# --- WMS ENDPOINTS ---

@router.api_route("/wms", methods=["GET"])
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



@router.post("/featureinfo")
@retry_on_failure(max_retries=2, exceptions=(httpx.HTTPError, httpx.TimeoutException))
async def get_temperature_featureinfo(request: ERA5Request):
    """
    Get temperature value for a specific location and date from GeoServer raster.

    Query the temperature value at a single point for a specific date.
    Uses GeoServer's WMS GetFeatureInfo to extract pixel values from GeoTIFF mosaics.

    **Note:** This endpoint queries GeoTIFF mosaics (slower) while `/history` queries
    NetCDF files (faster). Use `/history` for time-series queries.

    **Example Request:**
    ```json
    {
        "source": "temp_max",
        "lat": -15.8,
        "lon": -47.9,
        "date": "2024-01-15"
    }
    ```

    **Example Response:**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "date": "2024-01-15",
        "source": "temp_max",
        "temperature_c": 28.5
    }
    ```
    """
    if request.lat is None or request.lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required")
    
    # Validate source
    if request.source not in TEMPERATURE_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {', '.join(TEMPERATURE_SOURCES)}"
        )
    
    layer_name = f"temperature_ws:{request.source}"

    # Get actual bbox and dimensions for this specific layer
    west, south, east, north = LAYER_BBOXES.get(request.source, (-94.0, -53.0, -34.0, 25.0))
    width, height = LAYER_DIMENSIONS.get(request.source, (1200, 1560))

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


@router.post("/polygon")
async def temperature_polygon(request: PolygonRequest):
    """
    Process polygon request for temperature data.
    
    Example request:
    {
        "coordinates": [
            [-47.9, -15.8],
            [-47.8, -15.8],
            [-47.8, -15.9],
            [-47.9, -15.9]
        ],
        "source": "temp_max",
        "start_date": "2023-06-01",
        "end_date": "2023-08-31",
        "trigger": 35.0,
        "statistic": "max"
    }
    """
    source = request.source.lower()
    
    # Validate source
    if source not in ['temp_max', 'temp_min', 'temp_mean']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source for temperature. Must be 'temp_max', 'temp_min', or 'temp_mean'"
        )
    
    # Get dataset
    ds = get_dataset('temperature', source)
    
    if ds is None:
        raise HTTPException(
            status_code=503,
            detail=f"Temperature data for source '{source}' is not loaded"
        )
    
    try:
        # Process in thread pool
        result = await asyncio.to_thread(
            _process_temperature_polygon_sync,
            ds,
            request,
            source
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing polygon request: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


def _process_temperature_polygon_sync(ds, request: PolygonRequest, source: str):
    """Synchronous helper for temperature polygon processing."""
    # Use centralized variable name mapping
    variable_name = TEMPERATURE_VAR_NAMES.get(source, 't2m')
    
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
        trigger=request.trigger,
        consecutive_days=request.consecutive_days
    )
    
    # Add source and variable to metadata
    result["metadata"]["source"] = request.source
    result["metadata"]["variable_name"] = variable_name
    
    return result