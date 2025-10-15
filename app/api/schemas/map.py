# app/schemas/map.py
from pydantic import BaseModel
from typing import Optional

class MapRequest(BaseModel):
    source: str
    date: str
    width: Optional[int] = 1200
    height: Optional[int] = 1560
    lat: Optional[float] = None
    lon: Optional[float] = None
    zoom: Optional[int] = None
    format: Optional[str] = "png" 

class MapHistoryRequest(BaseModel):
    source: str
    lat: float
    lon: float
    start_date: str
    end_date: str

class TriggerRequest(BaseModel):
    source: str
    lat: float
    lon: float
    start_date: str
    end_date: str
    trigger: float

class TriggerAreaRequest(BaseModel):
    source: str
    lat: float
    lon: float
    start_date: str
    end_date: str
    trigger: float
    radius: float