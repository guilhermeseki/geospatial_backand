"""
XLSX/CSV validation utilities for geographic point data.

Validates uploaded files containing location data (local, latitude, longitude)
and ensures all points fall within Brazilian territory using GeoJSON geometry.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, BinaryIO, Optional
from io import BytesIO
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Cache for Brazil geometry (load once, reuse)
_brazil_geometry: Optional[gpd.GeoDataFrame] = None


def _load_brazil_geometry() -> gpd.GeoDataFrame:
    """
    Load Brazil GeoJSON geometry and cache it for reuse.
    Returns GeoDataFrame for fast point-in-polygon checks.
    """
    global _brazil_geometry

    if _brazil_geometry is None:
        from app.config.settings import get_settings
        settings = get_settings()

        geojson_path = Path(settings.BRAZIL_GEOJSON)
        if not geojson_path.exists():
            logger.warning(f"Brazil GeoJSON not found: {geojson_path}, falling back to shapefile")
            # Fallback to shapefile
            shapefile_path = Path(settings.BRAZIL_SHAPEFILE)
            if not shapefile_path.exists():
                raise FileNotFoundError(f"Brazil geometry files not found")
            _brazil_geometry = gpd.read_file(shapefile_path)
        else:
            # Load GeoJSON (much faster than shapefile)
            _brazil_geometry = gpd.read_file(geojson_path)

        logger.info(f"✓ Loaded Brazil geometry: {len(_brazil_geometry)} feature(s)")

    return _brazil_geometry


def validate_geographic_points(
    file_content: Union[bytes, BinaryIO],
    filename: str
) -> Dict[str, List[Dict]]:
    """
    Validates geographic point data from uploaded XLSX or CSV files.

    Ensures all points are within Brazil's geographic boundaries and that
    all required fields are present and properly formatted.

    Args:
        file_content: The uploaded file content (bytes or file-like object)
        filename: The name of the uploaded file (used to determine file type)

    Returns:
        Dictionary containing:
        - valid_rows: List of dictionaries with valid location data
        - invalid_rows: List of dictionaries with invalid data + failure_reason

    Example:
        >>> result = validate_geographic_points(file_content, "locations.xlsx")
        >>> print(f"Valid: {len(result['valid_rows'])}, Invalid: {len(result['invalid_rows'])}")
        >>> for row in result['invalid_rows']:
        ...     print(f"Row {row.get('_row_number')}: {row['failure_reason']}")
    """

    # Initialize result structure
    result = {
        "valid_rows": [],
        "invalid_rows": []
    }

    try:
        # Read file based on extension (XLSX primary, CSV fallback)
        if filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(BytesIO(file_content) if isinstance(file_content, bytes) else file_content)
        elif filename.lower().endswith('.csv'):
            # Try multiple encodings for CSV files (UTF-8, ISO-8859-1, Windows-1252)
            df = None
            encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin-1']
            encoding_errors = []

            for encoding in encodings:
                try:
                    df = pd.read_csv(
                        BytesIO(file_content) if isinstance(file_content, bytes) else file_content,
                        encoding=encoding,
                        sep=None,  # Auto-detect delimiter (comma, semicolon, tab, etc.)
                        engine='python'  # Required for sep=None
                    )
                    # If successful, break out of the loop
                    break
                except (UnicodeDecodeError, UnicodeError) as e:
                    encoding_errors.append(f"{encoding}: {str(e)}")
                    # Reset file position for next attempt
                    if isinstance(file_content, bytes):
                        continue
                    else:
                        file_content.seek(0)

            # If all encodings failed, return error with details
            if df is None:
                return {
                    "valid_rows": [],
                    "invalid_rows": [{
                        "failure_reason": (
                            f"Falha ao ler arquivo CSV com qualquer codificação suportada. "
                            f"Tentou: {', '.join(encodings)}. "
                            f"Por favor, certifique-se de que seu arquivo CSV está salvo com codificação UTF-8."
                        )
                    }]
                }
        else:
            # If file type is unsupported, return error for all rows
            return {
                "valid_rows": [],
                "invalid_rows": [{
                    "failure_reason": f"Formato de arquivo não suportado. Apenas arquivos XLSX e CSV são aceitos. Recebido: {filename}"
                }]
            }
    except Exception as e:
        # If file cannot be read, return error
        return {
            "valid_rows": [],
            "invalid_rows": [{
                "failure_reason": f"Falha ao ler arquivo: {str(e)}"
            }]
        }

    # Normalize column names to lowercase for case-insensitive matching
    df.columns = df.columns.str.strip().str.lower()

    # Remove duplicate columns if any exist after normalization
    df = df.loc[:, ~df.columns.duplicated()]

    # Check if required columns exist
    required_columns = {'local', 'latitude', 'longitude'}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        return {
            "valid_rows": [],
            "invalid_rows": [{
                "failure_reason": f"Faltam colunas obrigatórias: {', '.join(missing_columns)}. "
                                f"Colunas esperadas: local, latitude, longitude (não diferencia maiúsculas de minúsculas)"
            }]
        }

    # Process each row
    for idx, row in df.iterrows():
        row_number = idx + 2  # +2 because: +1 for 0-indexing, +1 for header row

        # Extract values (use bracket notation for pandas Series)
        local = row['local']
        lat_raw = row['latitude']
        lon_raw = row['longitude']

        # Skip completely empty rows (all three fields are empty)
        local_is_empty = pd.isna(local) or (isinstance(local, str) and local.strip() == "")
        lat_is_empty = pd.isna(lat_raw)
        lon_is_empty = pd.isna(lon_raw)

        if local_is_empty and lat_is_empty and lon_is_empty:
            # Completely empty row - skip silently
            continue

        # Create row data dictionary (convert NaN to None for JSON compatibility)
        row_data = {
            "_row_number": row_number,
            "local": None if local_is_empty else str(local).strip(),
            "latitude": None if lat_is_empty or pd.isna(lat_raw) else lat_raw,
            "longitude": None if lon_is_empty or pd.isna(lon_raw) else lon_raw
        }

        # Validation checks
        failure_reasons = []

        # 1. Presence Check: Ensure all fields are present and not null/empty
        if local_is_empty:
            failure_reasons.append("Campo 'local' está ausente ou vazio")

        if lat_is_empty:
            failure_reasons.append("Campo 'latitude' está ausente ou vazio")

        if lon_is_empty:
            failure_reasons.append("Campo 'longitude' está ausente ou vazio")

        # If any field is missing, skip numeric and geographic checks
        if failure_reasons:
            row_data["failure_reason"] = "; ".join(failure_reasons)
            result["invalid_rows"].append(row_data)
            continue

        # 2. Numeric Check: Ensure latitude and longitude are valid floats
        try:
            lat = float(lat_raw)
        except (ValueError, TypeError):
            failure_reasons.append(f"Latitude não é um valor numérico (recebido: '{lat_raw}')")
            lat = None

        try:
            lon = float(lon_raw)
        except (ValueError, TypeError):
            failure_reasons.append(f"Longitude não é um valor numérico (recebido: '{lon_raw}')")
            lon = None

        # If numeric conversion failed, skip geographic check
        if failure_reasons:
            row_data["failure_reason"] = "; ".join(failure_reasons)
            result["invalid_rows"].append(row_data)
            continue

        # 3. Brazil Geometry Check (point-in-polygon using GeoJSON)
        try:
            brazil_gdf = _load_brazil_geometry()
            point = Point(lon, lat)  # Point(longitude, latitude)

            # Check if point is within any Brazil polygon
            is_in_brazil = brazil_gdf.contains(point).any()

            if not is_in_brazil:
                failure_reasons.append(
                    f"Coordenada (lat: {lat}, lon: {lon}) está fora do território brasileiro. "
                    f"Verifique se as coordenadas estão corretas."
                )
        except Exception as e:
            # Fallback to approximate bbox check if geometry loading fails
            logger.error(f"Error checking Brazil geometry: {e}")
            lat_min, lat_max = -33.77, 5.28
            lon_min, lon_max = -74.0, -34.79

            if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
                failure_reasons.append(
                    f"Coordenada (lat: {lat}, lon: {lon}) está fora dos limites aproximados do Brasil."
                )

        # Add to appropriate list
        if failure_reasons:
            row_data["failure_reason"] = "; ".join(failure_reasons)
            result["invalid_rows"].append(row_data)
        else:
            # Store valid row with normalized numeric values
            valid_row_data = {
                "local": str(local).strip(),
                "latitude": lat,
                "longitude": lon
            }
            result["valid_rows"].append(valid_row_data)

    return result


def validate_geographic_points_file(file_path: str) -> Dict[str, List[Dict]]:
    """
    Convenience function to validate geographic points from a file path.

    Args:
        file_path: Path to the XLSX or CSV file

    Returns:
        Dictionary containing valid_rows and invalid_rows
    """
    with open(file_path, 'rb') as f:
        file_content = f.read()

    import os
    filename = os.path.basename(file_path)

    return validate_geographic_points(file_content, filename)
