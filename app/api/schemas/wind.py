# app/api/schemas/wind.py
"""
Pydantic schemas for Wind Speed API endpoints
Follows the same pattern as ERA5 temperature schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class WindRequest(BaseModel):
    """Base wind speed request"""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    width: Optional[int] = Field(1200, description="Image width in pixels")
    height: Optional[int] = Field(1560, description="Image height in pixels")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")
    zoom: Optional[int] = Field(None, description="Zoom level")
    format: Optional[str] = Field("png", description="Output format")


class WindHistoryRequest(BaseModel):
    """Request for historical wind speed time series"""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


class WindTriggerRequest(BaseModel):
    """Request for wind speed threshold exceedances"""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    trigger: float = Field(
        ..., 
        description="Wind speed threshold in m/s"
    )
    trigger_type: Literal["above", "below"] = Field(
        "above",
        description="Trigger when wind speed is 'above' or 'below' threshold"
    )


class WindTriggerAreaRequest(BaseModel):
    """Request for wind speed threshold exceedances in an area"""
    lat: float = Field(..., description="Center latitude")
    lon: float = Field(..., description="Center longitude")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    trigger: float = Field(
        ..., 
        description="Wind speed threshold in m/s"
    )
    radius: float = Field(
        ..., 
        description="Search radius in kilometers"
    )
    trigger_type: Literal["above", "below"] = Field(
        "above",
        description="Trigger when wind speed is 'above' or 'below' threshold"
    )
