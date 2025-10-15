from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    GEOSERVER_ADMIN_PASSWORD: str = "todosabordo25!"
    DATA_DIR: str = "/mnt/workwork/geoserver_data/"
    ENVIRONMENT: str = "development"
    GEOSERVER_PORT: str = "8080"
    GEOSERVER_HOST: str = "127.0.0.1"
    #GEOSERVER_PUBLIC_URL: str = "https://gs.seki-tech.com/geoserver"
    GEOSERVER_ADMIN_USER: str = "admin"
    GEOSERVER_WORKSPACE: str = "precipitation_ws"
    GEOSERVER_LAYER: str = "chirps"
    APP_VERSION: str = "0.1.0"
    PRECIPITATION_STYLE: str = "precipitation_style"
    width : str = "1200" 
    height: str = "1560"
    ALLOWED_ORIGINS: List[str] = [
        "https://seki-tech.com",
        "https://api.seki-tech.com",
        "https://gs.seki-tech.com",
        "http://localhost",
        "http://localhost:8002",
        "http://127.0.0.1:8002",
        "https://howndenmap.vercel.app/",
        "http://localhost:3005", 
    ]
    # Coordenadas "canônicas" (lon, lat)
    min_lon: float = -94.0
    min_lat: float = -53.0
    max_lon: float = -34.5
    max_lat: float = 25.05
    latam_bbox: Tuple[float, float, float, float] = (min_lat, min_lon, max_lat, max_lon)
    latam_bbox_raster: Tuple[float, float, float, float] = (min_lon, min_lat, max_lon, max_lat)
    latam_bbox_cds: List[float] = [max_lat, min_lon, min_lat, max_lon]
    geoserver_local_url: str = "http://127.0.0.1:8080/geoserver"
    #geoserver_base_url: str = "https://gs.seki-tech.com/geoserver"
    #netcdf_data_dir: str = "/opt/geoserver/data_dir/chirps_final"
    geoserver_timeout: int = 30
    BRAZIL_SHAPEFILE: str = "/opt/geospatial_backend/data/shapefiles/BR_Pais_2024/BR_Pais_2024.shp"
    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
logger.debug(f"Settings loaded: DATA_DIR={settings.DATA_DIR}")

def get_settings() -> Settings:
    return settings