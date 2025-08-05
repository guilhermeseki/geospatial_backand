from pydantic import BaseSettings, PostgresDsn

class Settings(BaseSettings):
    GEOSERVER_URL: str
    GEOSERVER_ADMIN_PASSWORD: str
    DATABASE_URL: PostgresDsn
    
    class Config:
        env_file = ".env"
