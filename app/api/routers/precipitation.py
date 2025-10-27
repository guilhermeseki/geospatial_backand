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
from app.api.schemas.precipitation import MapRequest, MapHistoryRequest, TriggerRequest, TriggerAreaRequest
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


router = APIRouter(prefix="/precipitation", tags=["Precipitation"])
logger = logging.getLogger(__name__)
geoserver = GeoServerService()
settings = get_settings()

GEOSERVER_WMS = f"{geoserver.base_url}/wms"


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


# --- ASYNC ENDPOINTS ---
@router.post("/history")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_precipitation_history(request: MapHistoryRequest):
    """Returns historical precipitation values for a given lat/lon and date range."""
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
    """Returns trigger exceedances for a given lat/lon and date range."""
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

    # Slice the bounding box
    ds_slice = historical_ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max),
        time=slice(start_date, end_date)
    )
    
    precip_data = ds_slice["precip"]
    
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
    exceeding_flat = exceeding_values.stack(point=['time', 'latitude', 'longitude'])
    
    # Synchronous compute
    computed_array = exceeding_flat.compute() 
    exceeding_flat_computed = computed_array.to_series().dropna()
    
    # Format the output
    grouped_exceedances = {}
    
    for index, value in exceeding_flat_computed.items():
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
    """Area-based trigger calculation."""
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
        
        return {
            "location": {"lat": request.lat, "lon": request.lon, "radius_km": request.radius}, 
            "source": source,
            "trigger_mm": request.trigger,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "total_exceedances": total_exceedances,
            "total_trigger_dates": num_trigger_dates,
            "exceedances_by_date": grouped_exceedances,
        }
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
    """Returns the pixel value for a given lat/lon from the precipitation raster."""
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
    
    # Process request
    result = PolygonProcessor.process_polygon_request(
        ds=ds,
        polygon=polygon,
        variable_name="precip",  # Precipitation variable name
        start_date=request.start_date,
        end_date=request.end_date,
        statistic=request.statistic,
        trigger=request.trigger
    )
    
    # Add source to metadata
    result["metadata"]["source"] = request.source
    
    return result