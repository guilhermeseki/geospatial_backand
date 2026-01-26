# app/api/routers/lightning.py
"""
Lightning (GLM FED) API endpoints
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
from app.api.schemas.lightning import (
    LightningRequest,
    LightningHistoryRequest,
    LightningTriggerRequest,
    LightningTriggerAreaRequest,
    LightningMapRequest
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

router = APIRouter(prefix="/lightning", tags=["Lightning"])
logger = logging.getLogger(__name__)
geoserver = GeoServerService()
settings = get_settings()

GEOSERVER_WMS = f"{geoserver.base_url}/wms"


# --- OPTIONS ENDPOINTS FOR CORS ---

@router.options("/history")
async def options_history():
    """OPTIONS endpoint for CORS preflight - /history"""
    return {}

@router.options("/triggers")
async def options_triggers():
    """OPTIONS endpoint for CORS preflight - /triggers"""
    return {}

@router.options("/triggers/area")
async def options_triggers_area():
    """OPTIONS endpoint for CORS preflight - /triggers/area"""
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
def _query_lightning_point_data_sync(
    historical_ds: xr.Dataset,
    request: LightningHistoryRequest | LightningTriggerRequest,
    is_trigger: bool
):
    """
    Synchronous helper for lightning FED point-based queries.
    Handles both history and trigger logic for GLM FED data.
    """
    start_date = pd.to_datetime(request.start_date)
    end_date = pd.to_datetime(request.end_date)

    # Validate requested dates are within available data range
    data_start = pd.Timestamp(historical_ds.time.min().values)
    data_end = pd.Timestamp(historical_ds.time.max().values)

    if end_date < data_start or start_date > data_end:
        # Requested range is completely outside available data
        raise ValueError(
            f"Requested date range ({start_date.date()} to {end_date.date()}) is outside "
            f"available data range ({data_start.date()} to {data_end.date()})"
        )

    ts = historical_ds.sel(
        latitude=request.lat,
        longitude=request.lon,
        method="nearest",
        tolerance=0.05
    ).sel(time=slice(start_date, end_date))

    # Get the fed_30min_max variable (maximum 30-minute window)
    ts_values = ts['fed_30min_max'].compute().squeeze()

    # Convert from total flashes per pixel to flashes/km²/30min
    # GLM FED grid is ~0.029° × ~0.029° in geographic projection (EPSG:4326)
    # Pixel area varies with latitude: area = (deg_lat * 111.32) * (deg_lon * 111.32 * cos(lat))
    actual_lat = float(ts_values.latitude.values)
    lat_spacing = 0.029069  # degrees
    lon_spacing = 0.029069  # degrees

    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * np.cos(np.radians(actual_lat))

    pixel_area_km2 = (lat_spacing * km_per_deg_lat) * (lon_spacing * km_per_deg_lon)

    # Convert values to flashes/km²/30min
    data_vals = np.atleast_1d(ts_values.values) / pixel_area_km2
    time_vals = np.atleast_1d(ts_values.time.values)

    if is_trigger:
        # Trigger logic - FED threshold exceedances
        # Filter out NaN and inf values before comparison
        valid_mask = np.isfinite(data_vals)

        if request.trigger_type == "above":
            exceedances = valid_mask & (data_vals > request.trigger)
        else:  # below
            exceedances = valid_mask & (data_vals < request.trigger)

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
        # History logic - convert NaN to 0 (no lightning activity)
        history = {
            str(pd.Timestamp(t).date()): (round(float(v), 2) if np.isfinite(v) else 0.0)
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
async def get_lightning_history(request: LightningHistoryRequest):
    """Returns historical lightning FED values for a given lat/lon and date range."""

    # Validate dates
    try:
        start_date = pd.to_datetime(request.start_date)
        end_date = pd.to_datetime(request.end_date)
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Get dataset from shared service
    historical_ds = get_dataset('lightning', 'glm_fed')

    if historical_ds is None:
        raise HTTPException(
            status_code=503,
            detail=f"Lightning FED historical data is not yet loaded or is unavailable."
        )

    try:
        result = await asyncio.to_thread(
            _query_lightning_point_data_sync,
            historical_ds,
            request,
            False
        )
        return result
    except ValueError as e:
        # Date range validation errors (user error)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying lightning history: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying historical lightning data")


@router.post("/triggers")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_lightning_triggers(request: LightningTriggerRequest):
    """Returns lightning FED threshold exceedances for a given lat/lon and date range."""

    # Get dataset from shared service
    historical_ds = get_dataset('lightning', 'glm_fed')

    if historical_ds is None:
        raise HTTPException(
            status_code=503,
            detail=f"Lightning FED historical data is not yet loaded or is unavailable."
        )

    try:
        result = await asyncio.to_thread(
            _query_lightning_point_data_sync,
            historical_ds,
            request,
            True
        )
        return result
    except ValueError as e:
        # Date range validation errors (user error)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying lightning triggers: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error querying lightning trigger data")


# --- SYNCHRONOUS HELPER FOR AREA QUERIES ---
def _calculate_lightning_area_exceedances_sync(
    historical_ds: xr.Dataset,
    request: LightningTriggerAreaRequest
):
    """
    Synchronous function for lightning FED area-based trigger calculation.
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

    # Validate requested dates are within available data range
    data_start = pd.Timestamp(historical_ds.time.min().values).date()
    data_end = pd.Timestamp(historical_ds.time.max().values).date()

    if end_date < data_start or start_date > data_end:
        raise ValueError(
            f"Requested date range ({start_date} to {end_date}) is outside "
            f"available data range ({data_start} to {data_end})"
        )

    # Slice the bounding box
    # GLM FED has increasing latitude coordinates (south to north)
    ds_slice = historical_ds.sel(
        latitude=slice(lat_min, lat_max),  # Standard order for increasing coords
        longitude=slice(lon_min, lon_max),
        time=slice(start_date, end_date)
    )

    fed_data = ds_slice['fed_30min_max']

    # Convert from total flashes per pixel to flashes/km²/30min
    # GLM FED grid is ~0.029° × ~0.029° in geographic projection (EPSG:4326)
    # Pixel area varies with latitude
    lat_spacing = 0.029069  # degrees
    lon_spacing = 0.029069  # degrees
    km_per_deg_lat = 111.32

    # Create a 2D array of pixel areas based on latitude
    lats_2d = ds_slice.latitude
    km_per_deg_lon_2d = 111.32 * np.cos(np.radians(lats_2d))
    pixel_area_km2_2d = (lat_spacing * km_per_deg_lat) * (lon_spacing * km_per_deg_lon_2d)

    # Convert FED values to flashes/km²/30min
    fed_data_converted = fed_data / pixel_area_km2_2d

    # Compute circular distance mask
    distances_km = haversine_distance(
        lon1=request.lon,
        lat1=request.lat,
        lon2=ds_slice.longitude,
        lat2=ds_slice.latitude
    )
    circular_mask = (distances_km <= request.radius).compute()

    # Apply trigger condition (now using converted values)
    if request.trigger_type == "above":
        trigger_mask_3D = (fed_data_converted > request.trigger) & circular_mask
    else:  # below
        trigger_mask_3D = (fed_data_converted < request.trigger) & circular_mask

    # Extract values (use converted values for output)
    exceeding_values = fed_data_converted.where(trigger_mask_3D)
    exceeding_flat = exceeding_values.stack(point=['time', 'latitude', 'longitude'])

    # Compute and convert
    computed_array = exceeding_flat.compute()
    exceeding_flat_computed = computed_array.to_series().dropna()

    # Format output
    grouped_exceedances = {}

    for index, value in exceeding_flat_computed.items():
        # Skip inf values
        if not np.isfinite(value):
            continue

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
async def get_lightning_area_triggers(request: LightningTriggerAreaRequest):
    """Returns lightning FED threshold exceedances in a circular area."""

    # Get dataset
    historical_ds = get_dataset('lightning', 'glm_fed')

    if historical_ds is None:
        raise HTTPException(
            status_code=503,
            detail=f"Lightning FED historical data is not yet loaded or is unavailable."
        )

    try:
        # Run computation in thread pool
        grouped_exceedances, num_trigger_dates = await asyncio.to_thread(
            _calculate_lightning_area_exceedances_sync,
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

    except ValueError as e:
        # Date range validation errors (user error)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating lightning area triggers: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error calculating lightning area trigger data")


@router.get("/wms")
async def proxy_lightning_wms(request: Request):
    """
    Proxy WMS requests to GeoServer for GLM FED layer.
    This hides the internal GeoServer URL and provides a clean API endpoint.
    """
    query_params = dict(request.query_params)

    # Ensure we're requesting the glm_fed layer from glm_ws workspace
    if 'layers' not in query_params:
        query_params['layers'] = 'glm_ws:glm_fed'

    # Default to WMS if service not specified
    if 'service' not in query_params:
        query_params['service'] = 'WMS'

    # Construct GeoServer WMS URL
    geoserver_wms_url = f"{geoserver.base_url}/glm_ws/wms"

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


def _calculate_lightning_polygon_sync(
    ds: xr.Dataset,
    request: PolygonRequest
):
    """Synchronous helper for lightning polygon processing."""
    # Create polygon
    polygon = PolygonProcessor.create_polygon_from_coords(request.coordinates)

    # Variable name for lightning (fed_30min_max)
    variable_name = "fed_30min_max"

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

    return result


@router.post("/polygon")
@retry_on_failure(max_retries=2, exceptions=(RuntimeError, ValueError, KeyError))
async def get_lightning_polygon(request: PolygonRequest):
    """Calculate statistics for lightning FED within a polygon area."""

    # Get dataset
    historical_ds = get_dataset('lightning', 'glm_fed')

    if historical_ds is None:
        raise HTTPException(
            status_code=503,
            detail="Lightning FED historical data is not yet loaded or is unavailable."
        )

    try:
        # Run polygon processing in thread pool
        result = await asyncio.to_thread(
            _calculate_lightning_polygon_sync,
            historical_ds,
            request
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating lightning polygon stats: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error calculating polygon statistics")


@router.post("/featureinfo")
@retry_on_failure(max_retries=2, exceptions=(httpx.HTTPError, httpx.TimeoutException))
async def get_lightning_featureinfo(request: LightningMapRequest):
    """
    Get lightning FED value for a specific location and date from GeoServer raster.

    Query the lightning FED value at a single point for a specific date.
    Uses GeoServer's WMS GetFeatureInfo to extract pixel values from GeoTIFF mosaics.

    **Note:** This endpoint queries GeoTIFF mosaics (slower) while `/history` queries
    NetCDF files (faster). Use `/history` for time-series queries.

    **Example Request:**
    ```json
    {
        "source": "glm_fed",
        "lat": -15.8,
        "lon": -47.9,
        "date": "2025-11-30"
    }
    ```

    **Example Response:**
    ```json
    {
        "lat": -15.8,
        "lon": -47.9,
        "date": "2024-04-05",
        "source": "glm_fed",
        "value": 2.5
    }
    ```
    """
    if request.lat is None or request.lon is None:
        raise HTTPException(status_code=400, detail="lat and lon are required")

    # CRITICAL: Validate that the requested date actually exists in GeoTIFF mosaics
    # GeoServer returns "nearest" date by default, which is misleading
    from pathlib import Path
    geotiff_dir = Path(settings.DATA_DIR) / "glm_fed"
    expected_file = geotiff_dir / f"glm_fed_{request.date.replace('-', '')}.tif"

    if not expected_file.exists():
        # Get available date range from historical dataset
        historical_ds = get_dataset('lightning', 'glm_fed')
        if historical_ds is not None:
            data_start = pd.Timestamp(historical_ds.time.min().values).date()
            data_end = pd.Timestamp(historical_ds.time.max().values).date()
            return {
                "lat": request.lat,
                "lon": request.lon,
                "date": request.date,
                "source": request.source,
                "value": None,
                "message": f"No data available for {request.date}. Available range: {data_start} to {data_end}"
            }
        else:
            return {
                "lat": request.lat,
                "lon": request.lon,
                "date": request.date,
                "source": request.source,
                "value": None,
                "message": f"No data available for {request.date}"
            }

    # Map source to layer name (glm_fed is the main layer, goes19 might be an alias)
    layer_name = f"glm_ws:{request.source}"

    # Get actual bbox and dimensions for this specific layer
    west, south, east, north = LAYER_BBOXES.get(request.source, settings.latam_bbox_cds)
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
                "source": request.source,
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
                # GeoTIFF files are now normalized to flashes/km²/30min
                pixel_value = round(float(pixel_value), 2)
        else:
            pixel_value = None

        return {
            "lat": request.lat,
            "lon": request.lon,
            "date": request.date,
            "source": request.source,
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
