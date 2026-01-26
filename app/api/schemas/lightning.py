# app/api/schemas/lightning.py
"""
Pydantic schemas for Lightning (GLM FED) API endpoints
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional


class LightningMapRequest(BaseModel):
    """Request schema for lightning WMS GetFeatureInfo queries"""
    source: str = Field(..., description="Lightning source (e.g., 'goes19', 'glm_fed')")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")


class LightningRequest(BaseModel):
    """Base request schema for lightning queries"""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


class LightningHistoryRequest(LightningRequest):
    """Request schema for historical lightning FED time series"""
    pass


class LightningTriggerRequest(LightningRequest):
    """Request schema for lightning FED threshold exceedances"""
    trigger: float = Field(..., gt=0, description="Flash extent density threshold")
    trigger_type: Literal["above", "below"] = Field(
        default="above",
        description="Trigger when FED is above or below threshold"
    )


class LightningTriggerAreaRequest(LightningTriggerRequest):
    """Request schema for area-based lightning FED triggers"""
    radius: float = Field(
        ...,
        gt=0,
        le=500,
        description="Radius in kilometers for circular area query"
    )
