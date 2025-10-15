from pydantic import BaseModel
from typing import Optional, List

class PlotRequest(BaseModel):
    bounds: Optional[str] = "1,10,20,30,40,60,80,100,150,200,300,400,600"  # Comma-separated string
    colors: Optional[str] = None  # Comma-separated string of hex colors
    format: Optional[str] = "png"
