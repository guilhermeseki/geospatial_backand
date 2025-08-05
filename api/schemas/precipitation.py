from pydantic import BaseModel

class PrecipitationRequest(BaseModel):
    lat: float
    lon: float
    date: str
    source: str