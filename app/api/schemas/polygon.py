# app/schemas/polygon.py
"""
Polygon request schema for climate data routes.
The variable is determined by the route path (e.g., /precipitation/polygon, /temperature/polygon).
"""
from pydantic import BaseModel, field_validator
from typing import List, Tuple, Optional


class PolygonRequest(BaseModel):
    """
    Universal polygon request schema.
    Variable is determined by the route, not the request body.
    
    Example for /api/precipitation/polygon:
    {
        "coordinates": [
            [-47.9, -15.8],
            [-47.8, -15.8],
            [-47.8, -15.9],
            [-47.9, -15.9]
        ],
        "source": "chirps",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "trigger": 50.0,
        "statistic": "pctl_50"
    }
    
    Example for /api/temperature/polygon:
    {
        "coordinates": [
            [-47.9, -15.8],
            [-47.8, -15.8],
            [-47.8, -15.9],
            [-47.9, -15.9]
        ],
        "source": "temp_max",
        "start_date": "2023-06-01",
        "end_date": "2023-08-31",
        "trigger": 35.0,
        "statistic": "max"
    }
    """
    coordinates: List[Tuple[float, float]]  # [(lon, lat), (lon, lat), ...]
    source: str  # "chirps", "merge", "temp_max", "temp_min", etc.
    start_date: str  # "YYYY-MM-DD"
    end_date: str  # "YYYY-MM-DD"
    trigger: Optional[float] = None  # Optional: threshold for trigger calculations
    statistic: Optional[str] = None  # Optional: "mean", "sum", "max", "min", "pctl_50", etc.
    
    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v):
        """Validate polygon has at least 3 coordinates and auto-close if needed."""
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 coordinates")
        
        # Auto-close polygon if first and last points are different
        if v[0] != v[-1]:
            v.append(v[0])
        
        return v
    
    @field_validator('statistic')
    @classmethod
    def validate_statistic(cls, v):
        """Validate statistic type if provided."""
        if v is None:
            return v
        
        valid_stats = [
            'mean', 'sum', 'max', 'min', 'std', 'median',
            'pctl_10', 'pctl_25', 'pctl_50', 'pctl_75', 'pctl_90', 'pctl_95', 'pctl_99'
        ]
        
        if v not in valid_stats:
            raise ValueError(
                f"statistic must be one of: {', '.join(valid_stats)}"
            )
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "coordinates": [
                    [-47.9, -15.8],
                    [-47.8, -15.8],
                    [-47.8, -15.9],
                    [-47.9, -15.9]
                ],
                "source": "chirps",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "trigger": 50.0,
                "statistic": "pctl_50"
            }
        }