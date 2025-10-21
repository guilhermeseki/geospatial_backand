"""
Shared geographic and utility functions for climate data APIs
"""
import numpy as np
import asyncio
import functools
import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Geographic constant
DEGREES_TO_KM = 111.32


def haversine_distance(lon1, lat1, lon2, lat2):
    """
    Calculate the great-circle distance between two points (in decimal degrees).
    
    Args:
        lon1: Longitude of point 1 (or array)
        lat1: Latitude of point 1 (or array)
        lon2: Longitude of point 2 (or array)
        lat2: Latitude of point 2 (or array)
    
    Returns:
        Distance in kilometers (scalar or array)
    
    Example:
        >>> haversine_distance(-46.6333, -23.5505, -43.1729, -22.9068)
        357.4  # São Paulo to Rio de Janeiro ~357km
    """
    R = 6371  # Radius of Earth in kilometers
    
    # Convert to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c


def retry_on_failure(max_retries: int = 2, exceptions: tuple = (Exception,)):
    """
    Decorator to retry async functions on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 2)
        exceptions: Tuple of exceptions to catch and retry on
    
    Example:
        @retry_on_failure(max_retries=3, exceptions=(HTTPException, TimeoutError))
        async def fetch_data():
            # This will retry up to 3 times on HTTPException or TimeoutError
            pass
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = 0.5 * (attempt + 1)  # Progressive backoff
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for "
                            f"{func.__name__}: {e}. Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            # If all retries failed, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


def km_to_degrees(km: float, latitude: float = 0) -> float:
    """
    Convert kilometers to degrees at a given latitude.
    
    Args:
        km: Distance in kilometers
        latitude: Latitude for longitude calculation (default: 0 for equator)
    
    Returns:
        Approximate degrees
    
    Note:
        - For latitude: 1 degree ≈ 111.32 km (constant)
        - For longitude: varies by latitude (smaller near poles)
    """
    # Latitude degrees (constant)
    lat_degrees = km / DEGREES_TO_KM
    
    # Longitude degrees (varies by latitude)
    lon_degrees = km / (DEGREES_TO_KM * np.cos(np.radians(latitude)))
    
    return lat_degrees  # Return latitude degrees as conservative estimate


def degrees_to_km(degrees: float, latitude: float = 0) -> float:
    """
    Convert degrees to kilometers at a given latitude.
    
    Args:
        degrees: Distance in degrees
        latitude: Latitude for calculation (default: 0 for equator)
    
    Returns:
        Approximate distance in kilometers
    """
    return degrees * DEGREES_TO_KM * np.cos(np.radians(latitude))


def validate_coordinates(lat: float, lon: float) -> tuple[bool, str]:
    """
    Validate latitude and longitude values.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not -90 <= lat <= 90:
        return False, f"Latitude must be between -90 and 90, got {lat}"
    
    if not -180 <= lon <= 180:
        return False, f"Longitude must be between -180 and 180, got {lon}"
    
    return True, ""


def validate_date_range(start_date, end_date) -> tuple[bool, str]:
    """
    Validate that start_date is before end_date.
    
    Args:
        start_date: Start date (datetime-like)
        end_date: End date (datetime-like)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if start_date > end_date:
        return False, f"start_date ({start_date}) must be before end_date ({end_date})"
    
    return True, ""