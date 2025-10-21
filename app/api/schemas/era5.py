# app/api/schemas/era5.py
"""
Pydantic schemas for ERA5 temperature API endpoints
Follows the same pattern as precipitation schemas (map.py)
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class ERA5Request(BaseModel):
    """Base ERA5 temperature request (analogous to MapRequest)"""
    source: Literal["temp_max", "temp_min", "temp"] = Field(
        ..., 
        description="Temperature variable: temp_max, temp_min, or temp (mean)"
    )
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    width: Optional[int] = Field(1200, description="Image width in pixels")
    height: Optional[int] = Field(1560, description="Image height in pixels")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")
    zoom: Optional[int] = Field(None, description="Zoom level")
    format: Optional[str] = Field("png", description="Output format")


class ERA5HistoryRequest(BaseModel):
    """Request for historical temperature time series (analogous to MapHistoryRequest)"""
    source: Literal["temp_max", "temp_min", "temp"] = Field(
        ...,
        description="Temperature variable"
    )
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


class ERA5TriggerRequest(BaseModel):
    """Request for temperature threshold exceedances (analogous to TriggerRequest)"""
    source: Literal["temp_max", "temp_min", "temp"] = Field(
        ...,
        description="Temperature variable"
    )
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    trigger: float = Field(
        ..., 
        description="Temperature threshold in Celsius"
    )
    trigger_type: Literal["above", "below"] = Field(
        "above",
        description="Trigger when temperature is 'above' or 'below' threshold"
    )


class ERA5TriggerAreaRequest(BaseModel):
    """Request for temperature threshold exceedances in an area (analogous to TriggerAreaRequest)"""
    source: Literal["temp_max", "temp_min", "temp"] = Field(
        ...,
        description="Temperature variable"
    )
    lat: float = Field(..., description="Center latitude")
    lon: float = Field(..., description="Center longitude")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    trigger: float = Field(
        ..., 
        description="Temperature threshold in Celsius"
    )
    radius: float = Field(
        ..., 
        description="Search radius in kilometers"
    )
    trigger_type: Literal["above", "below"] = Field(
        "above",
        description="Trigger when temperature is 'above' or 'below' threshold"
    )