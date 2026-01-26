"""
Utility functions for handling available dates across datasets
"""
from typing import List, Dict, Optional
import pandas as pd
import xarray as xr
from pathlib import Path
from app.config.settings import get_settings

settings = get_settings()


def get_available_dates_from_dataset(ds: xr.Dataset) -> Dict:
    """
    Extract available dates from an xarray Dataset.

    Args:
        ds: xarray Dataset with time dimension

    Returns:
        {
            "min_date": "2015-01-01",
            "max_date": "2025-12-04",
            "total_dates": 3949,
            "dates": ["2015-01-01", "2015-01-02", ...]
        }
    """
    time_values = ds.time.values
    dates = [pd.Timestamp(t).date().isoformat() for t in time_values]

    return {
        "min_date": dates[0] if dates else None,
        "max_date": dates[-1] if dates else None,
        "total_dates": len(dates),
        "dates": dates
    }


def get_available_dates_from_geotiffs(data_dir: Path, pattern: str) -> Dict:
    """
    Extract available dates from GeoTIFF filenames.

    Args:
        data_dir: Directory containing GeoTIFF files
        pattern: File pattern (e.g., "wind_speed_*.tif")

    Returns:
        {
            "min_date": "2015-01-01",
            "max_date": "2025-12-04",
            "total_dates": 3949,
            "dates": ["2015-01-01", "2015-01-02", ...]
        }
    """
    files = sorted(data_dir.glob(pattern))
    dates = []

    for f in files:
        try:
            # Extract date from filename (e.g., wind_speed_20250101.tif)
            date_str = f.stem.split('_')[-1]
            date_obj = pd.to_datetime(date_str, format='%Y%m%d')
            dates.append(date_obj.date().isoformat())
        except Exception:
            continue

    return {
        "min_date": dates[0] if dates else None,
        "max_date": dates[-1] if dates else None,
        "total_dates": len(dates),
        "dates": dates
    }


def get_available_dates_for_source(data_type: str, source: str) -> Dict:
    """
    Get available dates for a specific data source from GeoTIFF files.

    Args:
        data_type: Type of data (e.g., "precipitation", "temperature", "wind")
        source: Source name (e.g., "chirps", "merge", "temp_max", "wind_speed")

    Returns:
        {
            "min_date": "2015-01-01",
            "max_date": "2025-12-04",
            "total_dates": 3949,
            "dates": ["2015-01-01", "2015-01-02", ...]
        }
    """
    data_dir = Path(settings.DATA_DIR) / source
    pattern = f"{source}_*.tif"

    if not data_dir.exists():
        return {
            "min_date": None,
            "max_date": None,
            "total_dates": 0,
            "dates": []
        }

    return get_available_dates_from_geotiffs(data_dir, pattern)
