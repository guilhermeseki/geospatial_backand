# app/api/schemas/batch_analysis.py
"""
Pydantic schemas for batch analysis endpoints.

Supports batch analysis for:
- Points (current implementation)
- Circle areas (future)
- Polygons (future)
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional


class BatchPointAnalysisRequest(BaseModel):
    """
    Request schema for batch point-based trigger analysis.

    Analyzes trigger exceedances for multiple point locations from an uploaded CSV/XLSX file.
    Each location in the file becomes one row in the output with trigger statistics.

    Trigger type logic:
    - temp_max: always "above" (detecting heat events)
    - temp_min: always "below" (detecting cold events)
    - temp_mean: user can specify "above" or "below"
    - precipitation/wind/lightning: always "above"

    Future: BatchCircleAnalysisRequest, BatchPolygonAnalysisRequest
    """
    variable_type: Literal["precipitation", "temp_max", "temp_min", "temp_mean", "wind", "lightning"] = Field(
        ...,
        description="Type of climate variable to analyze"
    )
    source: str = Field(
        ...,
        description="Data source (e.g., 'chirps', 'merge' for precipitation; 'era5' for temperature/wind; 'glm' for lightning)"
    )
    threshold: float = Field(
        ...,
        description="Threshold value for trigger detection"
    )
    start_date: str = Field(
        ...,
        description="Analysis start date (YYYY-MM-DD)"
    )
    end_date: str = Field(
        ...,
        description="Analysis end date (YYYY-MM-DD)"
    )
    consecutive_days: Optional[int] = Field(
        1,
        description="Minimum consecutive days for trigger (default: 1)"
    )
    trigger_type: Optional[Literal["above", "below"]] = Field(
        None,
        description="Only for temp_mean: 'above' or 'below' threshold. Auto-determined for other variables."
    )
