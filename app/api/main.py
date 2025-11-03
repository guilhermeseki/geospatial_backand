# app/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.services.geoserver import GeoServerService
from app.services.climate_data import initialize_climate_data, shutdown_climate_data, get_available_sources, get_dask_client_info
from app.config.settings import get_settings
import logging
from logging.handlers import RotatingFileHandler
import os
import asyncio
from app.api.routers import temperature, precipitation, georisk, ndvi, wind, lightning
from pathlib import Path
from datetime import datetime
import httpx

settings = get_settings()  # Initialize settings

log_dir = "/var/log/fastapi"
try:
    os.makedirs(log_dir, exist_ok=True)
    os.chmod(log_dir, 0o775)  # Ensure directory is writable
except Exception as e:
    print(f"Failed to create log directory {log_dir}: {e}")

log_file = f"{log_dir}/geospatial_backend.log"
try:
    # Ensure log file is created with correct permissions
    if not os.path.exists(log_file):
        open(log_file, 'a').close()
    os.chmod(log_file, 0o664)
except Exception as e:
    print(f"Failed to initialize log file {log_file}: {e}")


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return "/health" not in record.getMessage()


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,
            backupCount=3
        ),
        logging.StreamHandler()
    ]
)

logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
logger = logging.getLogger(__name__)

from app.state import app_state

CONFIG_SOURCES = ["chirps_final"]
INIT_RETRIES = 3
INIT_RETRY_DELAY = 2


app = FastAPI(
    title="Geospatial Backend - Climate Data API",
    description="Unified API for precipitation and temperature data with shared Dask processing",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """
    Initialize application with shared climate data service.
    This replaces the old separate Dask clients in each router.
    """
    logger.info("=" * 80)
    logger.info("🚀 Starting Geospatial Backend - Climate Data API")
    logger.info("=" * 80)
    
    app_state.initialization_start = datetime.now()
    
    try:
        # Initialize shared climate data service
        # This creates ONE Dask client and loads ALL datasets (precipitation + temperature)
        logger.info("📊 Initializing shared climate data service...")
        initialize_climate_data()
        
        # Log what was loaded
        precip_sources = get_available_sources('precipitation')
        temp_sources = get_available_sources('temperature')
        ndvi_sources = get_available_sources('ndvi')
        lightning_sources = get_available_sources('lightning')
        dask_info = get_dask_client_info()

        logger.info("")
        logger.info("=" * 80)
        logger.info("📋 Climate Data Service Status")
        logger.info("=" * 80)
        logger.info(f"Precipitation sources: {len(precip_sources)} - {precip_sources}")
        logger.info(f"Temperature sources: {len(temp_sources)} - {temp_sources}")
        logger.info(f"NDVI sources: {len(ndvi_sources)} - {ndvi_sources}")
        logger.info(f"Lightning sources: {len(lightning_sources)} - {lightning_sources}")
        
        if dask_info:
            logger.info(f"Dask client: RUNNING")
            logger.info(f"  Scheduler: {dask_info['scheduler_address']}")
            logger.info(f"  Workers: {dask_info['num_workers']}")
            logger.info(f"  Dashboard: {dask_info['dashboard_link']}")
        else:
            logger.warning("Dask client: NOT AVAILABLE (running without parallelization)")
        
        logger.info("=" * 80)
        
        app_state.ready = True
        app_state.initialization_end = datetime.now()
        init_time = (app_state.initialization_end - app_state.initialization_start).total_seconds()
        
        logger.info("")
        logger.info(f"✅ Application initialized successfully in {init_time:.2f}s")
        logger.info(f"🌐 API ready at http://0.0.0.0:8000")
        logger.info(f"📚 Docs available at http://0.0.0.0:8000/docs")
        logger.info("=" * 80)
        
    except Exception as e:
        app_state.failure_reason = str(e)
        logger.critical(f"🔴 Initialization failed: {str(e)}")
        logger.exception(e)
        app_state.ready = True  # Set ready anyway to allow health checks


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    logger.info("🛑 Shutting down application...")
    shutdown_climate_data()
    logger.info("✅ Shutdown complete")


@app.get("/health", include_in_schema=False)
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy"}


@app.get("/status")
async def status_check():
    """Detailed status check with climate data information"""
    precip_sources = get_available_sources('precipitation')
    temp_sources = get_available_sources('temperature')
    ndvi_sources = get_available_sources('ndvi')
    lightning_sources = get_available_sources('lightning')
    dask_info = get_dask_client_info()

    return {
        "status": "ready" if app_state.ready else "initializing",
        "version": "2.0.0",
        "climate_data": {
            "precipitation_sources": precip_sources,
            "temperature_sources": temp_sources,
            "ndvi_sources": ndvi_sources,
            "lightning_sources": lightning_sources,
            "total_datasets": len(precip_sources) + len(temp_sources) + len(ndvi_sources) + len(lightning_sources)
        },
        "dask_client": {
            "available": dask_info is not None,
            "info": dask_info
        },
        "initialization_time": (
            (app_state.initialization_end - app_state.initialization_start).total_seconds()
            if app_state.initialization_end and app_state.initialization_start
            else None
        )
    }


@app.middleware("http")
async def readiness_check(request, call_next):
    """Middleware to check if service is ready and handle CORS"""
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Preflight OK"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )

    # Check readiness for all non-health routes
    if not app_state.ready and request.url.path not in ["/health", "/status"]:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"Service initializing: {app_state.failure_reason or 'Not ready'}"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            },
        )

    # Process the request normally
    response = await call_next(request)

    # Always add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "title": "Geospatial Backend - Climate Data API",
        "version": "2.0.0",
        "description": "Unified API for precipitation, temperature, NDVI, wind, and lightning data",
        "endpoints": {
            "precipitation": "/precipitation",
            "temperature": "/temperature",
            "ndvi": "/ndvi",
            "wind": "/wind",
            "lightning": "/lightning",
            "georisk": "/georisk"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "status": {
            "health": "/health",
            "detailed_status": "/status"
        }
    }


# Include routers
app.include_router(precipitation.router)
app.include_router(temperature.router)
app.include_router(ndvi.router)
app.include_router(wind.router)
app.include_router(lightning.router)
app.include_router(georisk.router)

logger.info("🔌 Routers registered: precipitation, temperature, ndvi, wind, lightning, georisk")