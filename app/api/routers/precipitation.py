# app/api/routers/precipitation.py
"""
Precipitation API endpoints (CHIRPS, MERGE)
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
from app.utils.dates import get_available_dates_for_source
from app.api.schemas.precipitation import MapRequest, MapHistoryRequest, TriggerRequest, TriggerAreaRequest
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


router = APIRouter(prefix="/precipitation", tags=["Precipitation"])
logger = logging.getLogger(__name__)
geoserver = GeoServerService()
settings = get_settings()

GEOSERVER_WMS = f"{geoserver.base_url}/wms"


# --- AVAILABLE DATES ENDPOINT ---

@router.get("/available_dates")
async def get_available_dates(source: str = "chirps", full_list: bool = False):
    """
    Get available date range for precipitation data.

    Query params:
        source: "chirps" or "merge" (default: "chirps")
        full_list: If true, returns all dates (default: false)

    Returns (full_list=false):
        {
            "source": "chirps",
            "min_date": "2015-01-01",
            "max_date": "2025-12-04",
            "total_dates": 3949
        }
    """
    try:
        result = get_available_dates_for_source("precipitation", source)
        result["source"] = source

        # Remove full dates list unless requested
        if not full_list and "dates" in result:
            del result["dates"]

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

@router.options("/featureinfo")
async def options_featureinfo():
    """OPTIONS endpoint for CORS preflight - /featureinfo"""
    return {}

@router.options("/polygon")
async def options_polygon():
    """OPTIONS endpoint for CORS preflight - /polygon"""
    return {}


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

    # Synchronous .compute() call
    # Handle both variable names: 'precipitation' (CHIRPS) and 'precip' (MERGE)
    var_name = "precip"
    ts_values = ts[var_name].compute().squeeze() 

    data_vals = np.atleast_1d(ts_values.values)
    time_vals = np.atleast_1d(ts_values.time.values)
    
    if is_trigger:
        # Trigger logic
        exceedances = data_vals > request.trigger
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
async def get_precipitation_history(request: MapHistoryRequest):
    """
    Get historical precipitation time series for a specific location.

    Returns daily precipitation values (in millimeters) from satellite-based rainfall
    estimates for a given location and date range.

    **Data Sources:**
    - `chirps`: CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data)
      - Resolution: ~5km (0.05°)
      - Coverage: Global 50°S-50°N
      - Best for: Drought monitoring, agricultural applications
    - `merge`: MERGE (CPTEC/INPE precipitation product)
      - Resolution: ~10km (0.1°)
      - Coverage: South America
      - Best for: Real-time monitoring, flood forecasting

    **Temporal Coverage:** 2015-present (updated daily, ~2 day lag)

    **Example Request:**
    ```json
    {
        "source": "chirps",
        "lat": -15.8,
        "lon": -47.9,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
    ```

    **Example Response:**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "source": "chirps",
        "history": {
            "2024-01-01": 12.5,
            "2024-01-02": 0.0,
            "2024-01-03": 5.3,
            ...
        }
    }
    ```

    **Use Cases:**
    - Historical rainfall analysis for a farm or location
    - Drought severity assessment
    - Comparing different precipitation data sources
    - Input for agricultural models
    """
    source = request.source
    
    # Validate dates
    try:
        start_date = pd.to_datetime(request.start_date)
        end_date = pd.to_datetime(request.end_date)
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    # Get dataset from shared service
    historical_ds = get_dataset('precipitation', source)
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )

    try:
        # Run synchronous Dask query in a separate thread
        result = await asyncio.to_thread(_query_point_data_sync, historical_ds, request, False)
        return result
    except Exception as e:
        logger.error(f"Error querying history data for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying historical data")


@router.post("/triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_triggers(request: TriggerRequest):
    """
    Find dates when precipitation exceeded a threshold at a specific location.

    Returns all dates where daily precipitation exceeded the specified trigger value
    (in millimeters) for a given location and date range. Useful for identifying
    extreme rainfall events, flood risk periods, or irrigation triggers.

    **Example Request:**
    ```json
    {
        "source": "chirps",
        "lat": -15.8,
        "lon": -47.9,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "trigger": 50.0
    }
    ```

    **Example Response:**
    ```json
    {
        "location": {"lat": -15.8, "lon": -47.9},
        "source": "chirps",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "trigger": 50.0,
        "n_exceedances": 3,
        "exceedances": [
            {"date": "2024-01-15", "value": 67.3},
            {"date": "2024-03-22", "value": 52.1},
            {"date": "2024-11-08", "value": 78.5}
        ]
    }
    ```

    **Use Cases:**
    - Flood risk assessment (e.g., days with >100mm rainfall)
    - Agricultural triggers (e.g., heavy rain preventing field work)
    - Insurance payouts (parametric weather insurance)
    - Extreme weather event analysis
    - Drought breaking rain identification

    **Common Trigger Values:**
    - Light rain: 5-10mm
    - Moderate rain: 10-30mm
    - Heavy rain: 30-50mm
    - Very heavy rain: 50-100mm
    - Extreme rain: >100mm
    """
    source = request.source
    
    # Get dataset from shared service
    historical_ds = get_dataset('precipitation', source)
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )

    try:
        result = await asyncio.to_thread(_query_point_data_sync, historical_ds, request, True)
        return result
    except Exception as e:
        logger.error(f"Error querying triggers data for {source}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying historical data")


# --- SYNCHRONOUS HELPER FOR AREA QUERIES ---
def _calculate_area_exceedances_sync(historical_ds: xr.Dataset, request: TriggerAreaRequest):
    """
    Synchronous function for area-based trigger calculation.
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

    # FIX: Check latitude order to handle both ascending (ERA5) and descending (CHIRPS) coordinates
    # xarray slice requires the slice bounds to match the coordinate order
    lat_coords = historical_ds.latitude.values
    lat_ascending = lat_coords[0] < lat_coords[-1]

    if lat_ascending:
        lat_slice = slice(lat_min, lat_max)
    else:
        # Descending order (e.g., CHIRPS): swap min/max for slice
        lat_slice = slice(lat_max, lat_min)

    # Slice the bounding box
    ds_slice = historical_ds.sel(
        latitude=lat_slice,
        longitude=slice(lon_min, lon_max),
        time=slice(start_date, end_date)
    )

    # Variable name for precipitation
    var_name = "precip"
    precip_data = ds_slice[var_name]
    
    # Compute the circular distance mask
    distances_km = haversine_distance(
        lon1=request.lon, 
        lat1=request.lat, 
        lon2=ds_slice.longitude, 
        lat2=ds_slice.latitude
    )
    circular_mask = (distances_km <= request.radius).compute() 

    # Combine both masks
    trigger_mask_3D = (precip_data > request.trigger) & circular_mask

    # Extract values and stack
    exceeding_values = precip_data.where(trigger_mask_3D)

    # Check if there are any exceedances before stacking
    # This prevents "tuple index out of range" error when no matches found
    if exceeding_values.notnull().sum().compute() == 0:
        # No exceedances found - return empty result
        return {}, 0

    exceeding_flat = exceeding_values.stack(point=['time', 'latitude', 'longitude'])

    # Synchronous compute
    computed_array = exceeding_flat.compute()
    exceeding_flat_computed = computed_array.to_series().dropna()

    # Apply consecutive days filter if requested
    if request.consecutive_days and request.consecutive_days > 1:
        from collections import defaultdict

        # Reorganize by (lat, lon) to check consecutive dates
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

    # Format the output
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
            "precipitation_mm": round(float(value), 2)
        }

        if date_str not in grouped_exceedances:
            grouped_exceedances[date_str] = []

        grouped_exceedances[date_str].append(point_data)

    num_trigger_dates = len(grouped_exceedances)

    return grouped_exceedances, num_trigger_dates


@router.post("/area_triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_area_triggers(request: TriggerAreaRequest):
    """
    Find all locations within a radius where precipitation exceeded a threshold.

    Returns detailed spatial information about where and when precipitation exceeded
    a threshold within a circular area. Unlike the point-based `/triggers` endpoint,
    this provides the geographic distribution of exceedances, showing which grid cells
    within the radius experienced heavy rainfall.

    **Example Request:**
    ```json
    {
        "source": "chirps",
        "lat": -15.8,
        "lon": -47.9,
        "radius": 50,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "trigger": 50.0
    }
    ```

    **Example Response:**
    ```json
    {
        "location": {"lat": -15.8, "lon": -47.9, "radius_km": 50},
        "source": "chirps",
        "trigger_mm": 50.0,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "total_exceedances": 15,
        "total_trigger_dates": 3,
        "exceedances_by_date": {
            "2024-01-15": [
                {"latitude": -15.8, "longitude": -47.9, "precipitation_mm": 67.3},
                {"latitude": -15.85, "longitude": -47.95, "precipitation_mm": 52.1},
                ...
            ],
            "2024-01-22": [...],
            ...
        }
    }
    ```

    **Use Cases:**
    - Flood risk assessment for a region (city, municipality, watershed)
    - Agricultural impact analysis (multiple farms or fields)
    - Insurance portfolio exposure (area-based parametric triggers)
    - Regional extreme weather monitoring
    - Spatial extent of rainfall events

    **Performance Notes:**
    - Larger radius values increase computation time
    - Recommended maximum radius: 100km
    - Results include all grid cells within the circular area
    """
    source = request.source
    
    # Get dataset from shared service
    historical_ds = get_dataset('precipitation', source)
    
    if historical_ds is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Historical data for source '{source}' is not yet loaded or is unavailable."
        )

    try:
        grouped_exceedances, num_trigger_dates = await asyncio.to_thread(
            _calculate_area_exceedances_sync, historical_ds, request
        )

        total_exceedances = sum(len(points) for points in grouped_exceedances.values())

        result = {
            "location": {"lat": request.lat, "lon": request.lon, "radius_km": request.radius},
            "source": source,
            "trigger_mm": request.trigger,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "total_exceedances": total_exceedances,
            "total_trigger_dates": num_trigger_dates,
            "exceedances_by_date": grouped_exceedances,
        }

        if request.consecutive_days and request.consecutive_days > 1:
            result["consecutive_days"] = request.consecutive_days

        return result
    except Exception as e:
        logger.error(f"Error processing area triggers for {source}: {e}")
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
async def get_precipitation_featureinfo(request: MapRequest):
    """
    Get precipitation value at a specific location and date from GeoServer raster.

    This endpoint queries the GeoServer WMS layer directly using GetFeatureInfo,
    which is useful for validating map displays or getting values for a single date.
    For time-series queries, use `/history` endpoint instead (much faster).

    **Difference from /history:**
    - `/featureinfo`: Single date, queries GeoServer WMS layer (slower)
    - `/history`: Date range, queries NetCDF directly (faster, recommended)

    **Example Request:**
    ```json
    {
        "source": "chirps",
        "lat": -15.8,
        "lon": -47.9,
        "date": "2024-01-15",
        "width": 800,
        "height": 600
    }
    ```

    **Example Response:**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "date": "2024-01-15",
        "value": 12.5
    }
    ```

    **Use Cases:**
    - Validating WMS layer rendering
    - Single-date precipitation lookup
    - Interactive map "click for value" functionality
    - Debugging GeoServer layer configuration
    """
    if request.lat is None or request.lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required")
    
    layer_name = f"{geoserver.workspace}:{request.source}"

    # Get actual bbox and dimensions for this specific layer
    west, south, east, north = LAYER_BBOXES.get(request.source, (-94.0, -53.0, -34.0, 25.0))
    width, height = LAYER_DIMENSIONS.get(request.source, (1200, 1560))

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
        logger.warning(f"HTTP error fetching feature info: {e}")
        raise
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in featureinfo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing feature info request")


@router.post("/polygon")
async def precipitation_polygon(request: PolygonRequest):
    """
    Process polygon request for precipitation data.
    
    Example request:
    {
        "coordinates": [
            [-47.9, -15.8],
            [-47.8, -15.8],
            [-47.8, -15.9],
            [-47.9, -15.9]
        ],
        "source": "chirps",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "trigger": 50.0,
        "statistic": "pctl_50"
    }
    """
    source = request.source.lower()
    
    # Validate source
    if source not in ['chirps', 'merge']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source for precipitation. Must be 'chirps' or 'merge'"
        )
    
    # Get dataset
    ds = get_dataset('precipitation', source)
    
    if ds is None:
        raise HTTPException(
            status_code=503,
            detail=f"Precipitation data for source '{source}' is not loaded"
        )
    
    try:
        # Process in thread pool
        result = await asyncio.to_thread(
            _process_precipitation_polygon_sync,
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


def _process_precipitation_polygon_sync(ds, request: PolygonRequest):
    """Synchronous helper for precipitation polygon processing."""
    # Create polygon
    polygon = PolygonProcessor.create_polygon_from_coords(request.coordinates)

    # Variable name for precipitation (standardized to "precip")
    variable_name = "precip"

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

    # Add source to metadata
    result["metadata"]["source"] = request.source

    return result