"""
Central configuration for all climate data sources.
This is the SINGLE SOURCE OF TRUTH for data source names and mappings.

If you need to add/rename a data source, do it HERE ONLY.
"""
from typing import Dict, List, Tuple

# ============================================================================
# TEMPERATURE SOURCES (ERA5)
# ============================================================================
TEMPERATURE_SOURCES = ["temp_max", "temp_min", "temp_mean"]

# ERA5 variable mapping: (variable, statistic) -> directory_name
ERA5_VARIABLE_MAPPING: Dict[str, Dict[str, str]] = {
    "2m_temperature": {
        "daily_maximum": "temp_max",
        "daily_minimum": "temp_min",
        "daily_mean": "temp_mean",
    },
    "total_precipitation": {
        "daily_sum": "precipitation",
    },
    "10m_u_component_of_wind": {
        "daily_mean": "wind_u",
        "daily_maximum": "wind_u_max",
        "daily_minimum": "wind_u_min",
    },
    "10m_v_component_of_wind": {
        "daily_mean": "wind_v",
        "daily_maximum": "wind_v_max",
        "daily_minimum": "wind_v_min",
    },
    "maximum_10m_wind_gust_since_previous_post_processing": {
        "daily_maximum": "wind_speed",
    },
    "surface_solar_radiation_downwards": {
        "daily_sum": "solar_radiation",
    },
}

# Temperature source -> historical directory mapping
TEMPERATURE_HIST_DIRS = {
    "temp_max": "temp_max_hist",
    "temp_min": "temp_min_hist",
    "temp_mean": "temp_mean_hist",
}

# Temperature source -> NetCDF variable name mapping
TEMPERATURE_VAR_NAMES = {
    "temp_max": "temp_max",
    "temp_min": "temp_min",
    "temp_mean": "temp_mean",
}

# Temperature source -> long name mapping
TEMPERATURE_LONG_NAMES = {
    "temp_max": "Daily Maximum Temperature at 2m",
    "temp_min": "Daily Minimum Temperature at 2m",
    "temp_mean": "Daily Mean Temperature at 2m",
}

# ============================================================================
# PRECIPITATION SOURCES
# ============================================================================
PRECIPITATION_SOURCES = ["chirps", "merge"]

PRECIPITATION_HIST_DIRS = {
    "chirps": "chirps_hist",
    "merge": "merge_hist",
}

# ============================================================================
# NDVI SOURCES
# ============================================================================
NDVI_SOURCES = ["sentinel2", "modis"]

NDVI_HIST_DIRS = {
    "sentinel2": "ndvi_s2_hist",
    "modis": "ndvi_modis_hist",
}

# ============================================================================
# WIND SOURCES
# ============================================================================
WIND_SOURCES = ["wind_speed"]

# ============================================================================
# LIGHTNING SOURCES
# ============================================================================
LIGHTNING_SOURCES = ["glm_fed"]

# ============================================================================
# SOLAR RADIATION SOURCES (ERA5)
# ============================================================================
SOLAR_SOURCES = ["solar_radiation"]

SOLAR_HIST_DIRS = {
    "solar_radiation": "solar_radiation_hist",
}

SOLAR_VAR_NAMES = {
    "solar_radiation": "solar_radiation",
}

SOLAR_LONG_NAMES = {
    "solar_radiation": "Surface Solar Radiation Downwards (GHI equivalent)",
}

# ============================================================================
# ECV (Essential Climate Variables) SOURCES - Monthly Climatology 1991-2020
# ============================================================================
# Long-term monthly averages from Copernicus for baseline climate analysis
# Using temperature and relative humidity
ECV_SOURCES = ["ecv_temp", "ecv_humidity"]

# ECV variable mapping: CDS variable name -> directory name
ECV_VARIABLE_MAPPING = {
    "surface_air_temperature": "ecv_temp",
    "surface_air_relative_humidity": "ecv_humidity",
}

# ECV origins (resolutions) - both support climatology product type
ECV_ORIGINS = {
    "era5": "0.25° × 0.25° resolution",
    "era5_land": "0.1° × 0.1° resolution (higher detail)"
}

# ECV product type (fixed: climatology = long-term monthly averages)
ECV_PRODUCT_TYPE = "climatology"

# ECV reference period (fixed: 1991-2020)
ECV_REFERENCE_PERIOD = "1991_2020"

# ============================================================================
# REVERSE MAPPING (for historical merging)
# ============================================================================
VARIABLE_REVERSE_MAPPING: Dict[str, Tuple[str, str]] = {
    # Temperature
    "temp_max": ("2m_temperature", "daily_maximum"),
    "temp_min": ("2m_temperature", "daily_minimum"),
    "temp_mean": ("2m_temperature", "daily_mean"),
    # Wind
    "wind_u": ("10m_u_component_of_wind", "daily_mean"),
    "wind_u_max": ("10m_u_component_of_wind", "daily_maximum"),
    "wind_u_min": ("10m_u_component_of_wind", "daily_minimum"),
    "wind_v": ("10m_v_component_of_wind", "daily_mean"),
    "wind_v_max": ("10m_v_component_of_wind", "daily_maximum"),
    "wind_v_min": ("10m_v_component_of_wind", "daily_minimum"),
    "wind_speed": ("maximum_10m_wind_gust_since_previous_post_processing", "daily_maximum"),
    # Solar radiation
    "solar_radiation": ("surface_solar_radiation_downwards", "daily_sum"),
}

# ============================================================================
# GEOSERVER MOSAIC DIRECTORIES
# ============================================================================
LIGHTNING_HIST_DIRS = {
    "glm_fed": "glm_fed_hist",
}

# ============================================================================
# LAYER DIMENSIONS (width, height) FOR WMS GetFeatureInfo
# ============================================================================
# These dimensions match the actual GeoTIFF raster sizes for accurate
# pixel coordinate calculations in GetFeatureInfo requests.
# Values obtained from: gdalinfo <first_geotiff_in_mosaic>

LAYER_DIMENSIONS: Dict[str, Tuple[int, int]] = {
    # Precipitation
    "chirps": (1191, 1562),
    "merge": (393, 391),

    # Temperature (ERA5)
    "temp_max": (416, 416),
    "temp_min": (393, 392),
    "temp_mean": (416, 416),

    # Lightning (GLM FED)
    "glm_fed": (1356, 1349),

    # NDVI
    "sentinel2": (1200, 1560),  # Default - update when GeoTIFFs available
    "modis": (10000, 10000),

    # Wind (ERA5)
    "wind_speed": (416, 416),  # Same as temperature
}

# ============================================================================
# LAYER BBOXES (west, south, east, north) FOR WMS GetFeatureInfo
# ============================================================================
# Each dataset has its own bbox based on the actual GeoTIFF extent.
# Values obtained from: gdalinfo <first_geotiff_in_mosaic>
# Format: (west, south, east, north) - consistent across all datasets

LAYER_BBOXES: Dict[str, Tuple[float, float, float, float]] = {
    # Precipitation
    "chirps": (-94.049999, -53.000002, -34.499998, 25.099999),  # Full Latin America
    "merge": (-74.000000, -33.800000, -34.700000, 5.300000),    # Brazil region

    # Temperature (ERA5)
    "temp_max": (-75.050000, -35.050000, -33.450000, 6.550000),   # Brazil with buffer
    "temp_min": (-74.050000, -33.850000, -34.750000, 5.350000),   # Brazil region
    "temp_mean": (-75.050000, -35.050000, -33.450000, 6.550000),  # Brazil with buffer

    # Lightning (GLM FED)
    "glm_fed": (-74.097548, -33.857815, -34.679965, 5.356286),  # Brazil region (GOES-16 view)

    # NDVI
    "sentinel2": (-94.049999, -53.000002, -34.499998, 25.099999),  # Assume same as CHIRPS
    "modis": (-94.049999, -53.000002, -34.499998, 25.099999),      # Assume same as CHIRPS

    # Wind (ERA5)
    "wind_speed": (-75.050000, -35.050000, -33.450000, 6.550000),  # Same as temp_max/mean
}


def get_geoserver_mosaic_dirs() -> List[str]:
    """Get list of all directories that should have GeoServer indexers."""
    return [
        # Temperature GeoTIFFs
        "temp_max",
        "temp_min",
        "temp_mean",
        # Temperature historical
        *TEMPERATURE_HIST_DIRS.values(),
        # Precipitation
        "chirps",
        "merge",
        "chirps_historical",  # Legacy
        "merge_historical",   # Legacy
        *PRECIPITATION_HIST_DIRS.values(),
        # NDVI
        *NDVI_HIST_DIRS.values(),
        # Lightning
        "glm_fed",
        *LIGHTNING_HIST_DIRS.values(),
    ]
