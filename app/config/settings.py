from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

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
    # LATIN AMERICA (full region)
    latam_bbox: Tuple[float, float, float, float] = (-53.0, -94.0, 25.0, -34.0)  # (S, W, N, E) - Full Latin America
    latam_bbox_raster: Tuple[float, float, float, float] = (-94.0, -53.0, -34.0, 25.0)  # (W, S, E, N) - For rasterio
    latam_bbox_cds: List[float] = [25.0, -94.0, -53.0, -34.0]  # [N, W, S, E] - For CDS API

    # BRAZIL (focused region with buffer)
    brazil_bbox: Tuple[float, float, float, float] = (-35.0, -75.0, 6.5, -33.5)  # (S, W, N, E) - Brazil with buffer
    brazil_bbox_raster: Tuple[float, float, float, float] = (-75.0, -35.0, -33.5, 6.5)  # (W, S, E, N) - For rasterio/GLM
    brazil_bbox_cds: List[float] = [6.55, -75.05, -35.05, -33.45]  # [N, W, S, E] - For ERA5 CDS API (exactly 416×416 grid)
    
    geoserver_local_url: str = "http://127.0.0.1:8080/geoserver"
    geoserver_timeout: int = 30
    
    BRAZIL_SHAPEFILE: str = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp"
    BRAZIL_GEOJSON: str = "/opt/geospatial_backend/data/shapefiles/br_shp/brazil.geojson"
    
    COPERNICUS_USERNAME: str = "guilhermeseki@gmail.com"
    COPERNICUS_PASSWORD: str = "Seentregueaoamor25!"

    # NASA Earthdata credentials
    EARTHDATA_USERNAME: str = Field(default="")
    EARTHDATA_PASSWORD: str = Field(default="")

settings = Settings()
logger.debug(f"Settings loaded: DATA_DIR={settings.DATA_DIR}")

def get_settings() -> Settings:
    return settings