# app/api/schemas/ndvi.py
from pydantic import BaseModel
from typing import Optional

class NDVIRequest(BaseModel):
    source: str  # 'sentinel2' or 'modis'
    date: str
    width: Optional[int] = 12001
    height: Optional[int] = 1560
    lat: Optional[float] = None
    lon: Optional[float] = None
    zoom: Optional[int] = None
    format: Optional[str] = "png"

class NDVIHistoryRequest(BaseModel):
    source: str  # 'sentinel2' or 'modis'
    lat: float
    lon: float
    start_date: str
    end_date: str

class NDVITriggerRequest(BaseModel):
    source: str  # 'sentinel2' or 'modis'
    lat: float
    lon: float
    start_date: str
    end_date: str
    trigger: float  # NDVI threshold (e.g., 0.3 for vegetation health)
    trigger_type: Optional[str] = "below"  # 'below' or 'above'

class NDVITriggerAreaRequest(BaseModel):
    source: str  # 'sentinel2' or 'modis'
    lat: float
    lon: float
    start_date: str
    end_date: str
    trigger: float
    trigger_type: Optional[str] = "below"
    radius: float  # radius in kilometers
