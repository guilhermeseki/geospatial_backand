#app/api/schemas/precipitation.py
from pydantic import BaseModel
from typing import Optional

class PrecipitationRequest(BaseModel):
    lat: float
    lon: float
    date: str
    source: str
    width: Optional[int] = 800
    height: Optional[int] = 600
    format: Optional[str] = "png" 