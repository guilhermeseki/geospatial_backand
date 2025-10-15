from enum import Enum

class DataSource(str, Enum):
    CHIRPS = "chirps"
    MERGE = "merge"
    ERA5 = "era5"

class ERA5Variable(str, Enum):
    """ERA5 variables available for download"""
    TEMP_2M = "2m_temperature"
    PRECIP = "total_precipitation"
    WIND_U = "10m_u_component_of_wind"
    WIND_V = "10m_v_component_of_wind"
    DEWPOINT = "2m_dewpoint_temperature"
    PRESSURE = "surface_pressure"