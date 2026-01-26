"""
API endpoints for querying available dates for each data layer.
Provides frontend with date ranges and available dates for time-series data.
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List
from pydantic import BaseModel
import re

router = APIRouter(prefix="/available-dates", tags=["available-dates"])


class DateRange(BaseModel):
    """Date range with start and end dates."""
    start_date: str
    end_date: str


class LayerDates(BaseModel):
    """Available dates for a specific layer."""
    layer: str
    source: str
    date_range: DateRange


def extract_dates_from_geotiffs(directory: Path, pattern: str) -> List[date]:
    """
    Extract dates from GeoTIFF filenames in a directory.

    Args:
        directory: Path to directory containing GeoTIFF files
        pattern: Regex pattern to extract date from filename (should have one capture group for YYYYMMDD)

    Returns:
        Sorted list of dates
    """
    if not directory.exists():
        return []

    dates = []
    regex = re.compile(pattern)

    for file in directory.glob("*.tif"):
        match = regex.match(file.name)
        if match:
            try:
                date_str = match.group(1)
                file_date = datetime.strptime(date_str, '%Y%m%d').date()
                dates.append(file_date)
            except (ValueError, IndexError):
                continue

    return sorted(dates)


@router.get("/precipitation/chirps", response_model=DateRange)
async def get_chirps_dates():
    """Get available dates for CHIRPS precipitation data."""
    data_dir = Path("/mnt/workwork/geoserver_data/chirps")
    dates = extract_dates_from_geotiffs(data_dir, r"chirps_(\d{8})\.tif")

    if not dates:
        raise HTTPException(status_code=404, detail="No CHIRPS data found")

    return DateRange(
        start_date=dates[0].isoformat(),
        end_date=dates[-1].isoformat()
    )


@router.get("/precipitation/merge", response_model=DateRange)
async def get_merge_dates():
    """Get available dates for MERGE precipitation data."""
    data_dir = Path("/mnt/workwork/geoserver_data/merge")
    dates = extract_dates_from_geotiffs(data_dir, r"merge_(\d{8})\.tif")

    if not dates:
        raise HTTPException(status_code=404, detail="No MERGE data found")

    return DateRange(
        start_date=dates[0].isoformat(),
        end_date=dates[-1].isoformat()
    )


@router.get("/temperature/{variable}", response_model=DateRange)
async def get_temperature_dates(variable: str):
    """Get available dates for temperature data."""
    if variable not in ["temp_max", "temp_min", "temp_mean"]:
        raise HTTPException(status_code=400, detail=f"Invalid variable: {variable}")

    data_dir = Path(f"/mnt/workwork/geoserver_data/{variable}")
    dates = extract_dates_from_geotiffs(data_dir, rf"{variable}_(\d{{8}})\.tif")

    if not dates:
        raise HTTPException(status_code=404, detail=f"No {variable} data found")

    return DateRange(
        start_date=dates[0].isoformat(),
        end_date=dates[-1].isoformat()
    )


@router.get("/wind", response_model=DateRange)
async def get_wind_dates():
    """Get available dates for wind speed data."""
    data_dir = Path("/mnt/workwork/geoserver_data/wind_speed")
    dates = extract_dates_from_geotiffs(data_dir, r"wind_speed_(\d{8})\.tif")

    if not dates:
        raise HTTPException(status_code=404, detail="No wind speed data found")

    return DateRange(
        start_date=dates[0].isoformat(),
        end_date=dates[-1].isoformat()
    )


@router.get("/ndvi/{source}", response_model=DateRange)
async def get_ndvi_dates(source: str):
    """Get available dates for NDVI data."""
    if source not in ["s2", "modis"]:
        raise HTTPException(status_code=400, detail=f"Invalid source: {source}")

    data_dir = Path(f"/mnt/workwork/geoserver_data/ndvi_{source}")
    dates = extract_dates_from_geotiffs(data_dir, rf"ndvi_{source}_(\d{{8}})\.tif")

    if not dates:
        raise HTTPException(status_code=404, detail=f"No NDVI {source} data found")

    return DateRange(
        start_date=dates[0].isoformat(),
        end_date=dates[-1].isoformat()
    )


@router.get("/lightning", response_model=DateRange)
async def get_lightning_dates():
    """Get available dates for GLM lightning data."""
    data_dir = Path("/mnt/workwork/geoserver_data/glm_fed")
    dates = extract_dates_from_geotiffs(data_dir, r"glm_fed_(\d{8})\.tif")

    if not dates:
        raise HTTPException(status_code=404, detail="No lightning data found")

    return DateRange(
        start_date=dates[0].isoformat(),
        end_date=dates[-1].isoformat()
    )


@router.get("/all", response_model=Dict[str, DateRange])
async def get_all_available_dates():
    """Get available dates for all layers (start and end dates only)."""
    result = {}

    try:
        result["chirps"] = await get_chirps_dates()
    except HTTPException:
        pass

    try:
        result["merge"] = await get_merge_dates()
    except HTTPException:
        pass

    try:
        result["temp_max"] = await get_temperature_dates("temp_max")
    except HTTPException:
        pass

    try:
        result["temp_min"] = await get_temperature_dates("temp_min")
    except HTTPException:
        pass

    try:
        result["temp_mean"] = await get_temperature_dates("temp_mean")
    except HTTPException:
        pass

    try:
        result["wind_speed"] = await get_wind_dates()
    except HTTPException:
        pass

    try:
        result["ndvi_s2"] = await get_ndvi_dates("s2")
    except HTTPException:
        pass

    try:
        result["ndvi_modis"] = await get_ndvi_dates("modis")
    except HTTPException:
        pass

    try:
        result["glm_fed"] = await get_lightning_dates()
    except HTTPException:
        pass

    return result
