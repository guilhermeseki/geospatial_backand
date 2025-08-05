from pydantic import BaseModel
from typing import Optional

class MapRequest(BaseModel):
    lat: float
    lon: float
    source: str
    date: str
    zoom: Optional[int] = 10
    width: Optional[int] = 800
    height: Optional[int] = 600