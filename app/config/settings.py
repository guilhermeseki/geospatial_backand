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
    GEOSERVER_ADMIN_USER: str = "admin"
    GEOSERVER_WORKSPACE: str = "precipitation_ws"
    GEOSERVER_LAYER: str = "chirps"
    APP_VERSION: str = "0.1.0"
    PRECIPITATION_STYLE: str = "precipitation_style"
    width: str = "1200" 
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
    
    # 🇧🇷 BRAZIL BOUNDING BOX (with 1° buffer)
    # Much more efficient than full LatAm!
    min_lon: float = -75.0   # West (Acre + buffer)
    min_lat: float = -35.0   # South (RS + buffer)
    max_lon: float = -33.5   # East (Paraíba coast + buffer)
    max_lat: float = 6.5     # North (Roraima + buffer)
    
    # Different bbox formats for different libraries
    latam_bbox: Tuple[float, float, float, float] = (-35.0, -75.0, 6.5, -33.5)  # (S, W, N, E)
    latam_bbox_raster: Tuple[float, float, float, float] = (-75.0, -35.0, -33.5, 6.5)  # (W, S, E, N)
    latam_bbox_cds: List[float] = [6.5, -75.0, -35.0, -33.5]  # [N, W, S, E]
    
    geoserver_local_url: str = "http://127.0.0.1:8080/geoserver"
    geoserver_timeout: int = 30
    
    BRAZIL_SHAPEFILE: str = "/opt/geospatial_backend/data/shapefiles/BR_Pais_2024/BR_Pais_2024.shp"
    
    COPERNICUS_USERNAME: str = "guilhermeseki@gmail.com"
    COPERNICUS_PASSWORD: str = "Seentregueaoamor25!"

settings = Settings()
logger.debug(f"Settings loaded: DATA_DIR={settings.DATA_DIR}")

def get_settings() -> Settings:
    return settings