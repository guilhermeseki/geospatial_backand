# app/api/routers/solar.py
"""
Solar Radiation API endpoints (NASA POWER GHI - Global Horizontal Irradiance)
Uses shared climate data service with shared Dask client
"""
import logging
from fastapi import APIRouter, HTTPException
from app.services.climate_data import get_dataset
from app.api.schemas.era5 import ERA5HistoryRequest  # Reuse ERA5 schema (same structure)
from datetime import datetime
import pandas as pd
import numpy as np
import asyncio

router = APIRouter(prefix="/solar", tags=["Solar Radiation"])
logger = logging.getLogger(__name__)


# --- OPTIONS ENDPOINTS FOR CORS ---

@router.options("/history")
async def options_history():
    """OPTIONS endpoint for CORS preflight - /history"""
    return {}


# --- SYNCHRONOUS HELPER FOR POINT QUERIES ---
def _query_solar_point_data_sync(
    historical_ds,
    request: ERA5HistoryRequest
):
    """
    Synchronous helper for solar radiation point-based queries.
    Returns daily GHI values (kWh/m²/day) for a location.
    """
    start_date = pd.to_datetime(request.start_date)
    end_date = pd.to_datetime(request.end_date)

    ts = historical_ds.sel(
        latitude=request.lat,
        longitude=request.lon,
        method="nearest"
    ).sel(time=slice(start_date, end_date))

    # Get solar radiation values
    ts_values = ts['solar_radiation'].compute().squeeze()

    data_vals = np.atleast_1d(ts_values.values)
    time_vals = np.atleast_1d(ts_values.time.values)

    # Build history response
    times = pd.to_datetime(time_vals)
    history = [
        {
            "date": str(date.date()),
            "ghi": round(float(value), 2) if not np.isnan(value) else None
        }
        for date, value in zip(times, data_vals)
    ]

    result = {
        "location": {"lat": request.lat, "lon": request.lon},
        "source": "ghi",
        "start_date": str(start_date.date()),
        "end_date": str(end_date.date()),
        "data": history,
        "stats": {
            "count": int(np.sum(~np.isnan(data_vals))),
            "mean": round(float(np.nanmean(data_vals)), 2) if len(data_vals) > 0 else None,
            "max": round(float(np.nanmax(data_vals)), 2) if len(data_vals) > 0 else None,
            "min": round(float(np.nanmin(data_vals)), 2) if len(data_vals) > 0 else None,
            "sum": round(float(np.nansum(data_vals)), 2) if len(data_vals) > 0 else None,
        },
        "units": "kWh/m²/day",
        "variable": "GHI (Global Horizontal Irradiance)"
    }

    return result


# --- API ENDPOINTS ---

@router.get("/history")
async def get_solar_history(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str
):
    """
    Get historical daily GHI (Global Horizontal Irradiance) values for a point location.

    **Data Source**: NASA POWER (Prediction Of Worldwide Energy Resources)
    - **Parameter**: ALLSKY_SFC_SW_DWN (All Sky Surface Shortwave Downward Irradiance)
    - **Resolution**: 0.5° (~55km)
    - **Units**: kWh/m²/day
    - **Coverage**: Global (including all of Brazil and Latin America)
    - **Period**: 1981-present (near real-time, ~3-7 day lag)
    - **Accuracy**: <1% bias for monthly GHI (validated in Brazil)

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Daily GHI time series with statistics

    Example:
        GET /solar/history?lat=-15.8&lon=-47.9&start_date=2024-01-01&end_date=2024-01-31
    """
    try:
        # Validate coordinates
        if not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
        if not (-180 <= lon <= 180):
            raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")

        # Validate dates
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            if start > end:
                raise HTTPException(status_code=400, detail="start_date must be before end_date")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Get solar radiation dataset from climate service
        historical_ds = get_dataset('solar', 'solar_radiation')

        if historical_ds is None:
            raise HTTPException(
                status_code=503,
                detail="Solar radiation dataset not loaded. Run 'python app/run_nasa_power_solar.py' to download data."
            )

        # Create request object (reuse ERA5 schema structure)
        request = ERA5HistoryRequest(
            lat=lat,
            lon=lon,
            start_date=start_date,
            end_date=end_date,
            source="ghi"  # Not used but required by schema
        )

        # Query data in thread pool (don't block event loop)
        result = await asyncio.to_thread(
            _query_solar_point_data_sync,
            historical_ds,
            request
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_solar_history: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/info")
async def get_solar_info():
    """
    Get information about the solar radiation dataset.

    Returns metadata about the loaded GHI dataset including time range,
    spatial coverage, and data source details.
    """
    try:
        historical_ds = get_dataset('solar', 'solar_radiation')

        if historical_ds is None:
            return {
                "loaded": False,
                "message": "Solar radiation dataset not loaded. Run 'python app/run_nasa_power_solar.py' to download data."
            }

        # Get dataset info
        time_min = pd.Timestamp(historical_ds.time.min().values).date()
        time_max = pd.Timestamp(historical_ds.time.max().values).date()

        return {
            "loaded": True,
            "variable": "ALLSKY_SFC_SW_DWN (Global Horizontal Irradiance)",
            "units": "kWh/m²/day",
            "source": "NASA POWER",
            "resolution": "0.5° (~55km)",
            "coverage": "Global (all of Brazil and Latin America)",
            "accuracy": "<1% bias for monthly GHI (validated in Brazil)",
            "time_range": {
                "start": str(time_min),
                "end": str(time_max),
                "total_days": len(historical_ds.time)
            },
            "spatial_extent": {
                "lat_min": float(historical_ds.latitude.min().values),
                "lat_max": float(historical_ds.latitude.max().values),
                "lon_min": float(historical_ds.longitude.min().values),
                "lon_max": float(historical_ds.longitude.max().values),
            },
            "dimensions": {
                "time": len(historical_ds.time),
                "latitude": len(historical_ds.latitude),
                "longitude": len(historical_ds.longitude)
            }
        }

    except Exception as e:
        logger.error(f"Error in get_solar_info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
