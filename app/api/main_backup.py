#app/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.services.geoserver import GeoServerService
from app.config.settings import settings # Assuming you have settings module
import logging
from logging.handlers import RotatingFileHandler
import os
import asyncio
from app.api.routers import test, data, precipitation, map, health  
from pathlib import Path
from typing import Optional
from datetime import datetime 
# --- Initialization Status Tracking ---
from app.state import app_state

# --- Configuration ---
CONFIG_SOURCES = ["chirps_final"]  # Make configurable via settings if needed
INIT_RETRIES = 3
INIT_RETRY_DELAY = 2

# --- Logging Setup ---
log_dir = "/var/log/fastapi"
os.makedirs(log_dir, exist_ok=True)

class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return "/health" not in record.getMessage()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            f"{log_dir}/geospatial_backend.log",
            maxBytes=5*1024*1024,
            backupCount=3
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler replacing @app.on_event"""
    # Startup code
    app_state.initialization_start = datetime.now()
    geoserver = GeoServerService()
    
    try:
        # 1. Verify GeoServer connection (direct call without retry wrapper)
        logger.info("🔗 Connecting to GeoServer...")
        for attempt in range(1, 10):
            if await geoserver.check_geoserver_alive():
                break
            await asyncio.sleep(5)
        else:
            raise RuntimeError("GeoServer connection failed after retries")
        logger.info("✅ GeoServer connection verified")

        # 2. Verify data directory
        data_path = Path(settings.NETCDF_DATA_DIR)
        if not data_path.exists():
            raise RuntimeError(f"Data directory not found: {data_path}")
        logger.info(f"✅ Data directory found: {data_path}")

        # 3. Initialize mosaic configurations with simple retry
        for source in CONFIG_SOURCES:
            logger.info(f"⚙️ Initializing mosaic config for {source}...")
            for attempt in range(1, INIT_RETRIES + 1):
                try:
                    await geoserver._ensure_mosaic_config(source)
                    logger.info(f"✅ Mosaic configuration initialized for {source}")
                    break
                except Exception as e:
                    if attempt == INIT_RETRIES:
                        raise RuntimeError(f"Mosaic config failed for {source}: {str(e)}")
                    logger.warning(f"⚠️ Mosaic config attempt {attempt} failed for {source}: {str(e)}")
                    await asyncio.sleep(INIT_RETRY_DELAY)

        app_state.ready = True
        app_state.initialization_end = datetime.now()
        logger.info(f"🟢 Application initialized in {(app_state.initialization_end - app_state.initialization_start).total_seconds()}s")
        
        yield  # Application runs here
        
    except Exception as e:
        app_state.failure_reason = str(e)
        logger.critical(f"🔴 Initialization failed: {str(e)}")
        if settings.ENVIRONMENT == "production":
            import sys
            sys.exit(1)
        raise  # Re-raise for test visibility

# Replace the existing app = FastAPI() with:
app = FastAPI(
    title="Geospatial Backend",
    description="API for geospatial data processing",
    version="1.0.0",
    lifespan=lifespan  # Connect the lifespan handler
)

# Keep all other middleware and router setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health Check Endpoint ---
@app.get("/health", include_in_schema=False)
async def health_check():
    """Kubernetes/Docker health check endpoint"""
    return {"status": "healthy"}


# --- Startup Sequence ---

async def initialize_services():
    """Enhanced initialization with state tracking"""
    geoserver = GeoServerService()
    app_state.initialization_start = datetime.now()
    
    try:
        # 1. Verify GeoServer connection
        if not await _initialize_with_retry(
            operation="GeoServer connection",
            task=geoserver.check_geoserver_alive,
            success_msg="GeoServer connection verified",
            failure_msg="GeoServer unavailable"
        ):
            raise RuntimeError("GeoServer connection failed after retries")

        # 2. Verify data directory
        data_path = Path(settings.NETCDF_DATA_DIR)
        if not data_path.exists():
            raise RuntimeError(f"Data directory not found: {data_path}")
        if not os.access(data_path, os.R_OK):
            raise RuntimeError(f"Insufficient permissions for data directory: {data_path}")

        # 3. Initialize mosaic configurations
        for source in CONFIG_SOURCES:
            await _initialize_with_retry(
                operation=f"Mosaic config for {source}",
                task=lambda: geoserver._ensure_mosaic_config(source),
                success_msg=f"Mosaic configuration initialized for {source}",
                failure_msg=f"Mosaic config failed for {source}"
            )

        # 4. Verify layer publishing
        if not await _initialize_with_retry(
            operation="Layer publishing test",
            task=lambda: geoserver.verify_layer_publishing("chirps_final"),
            success_msg="Layer publishing verified",
            failure_msg="Layer publishing test failed"
        ):
            raise RuntimeError("Layer publishing verification failed")

        app_state.ready = True
        app_state.initialization_end = datetime.now()
        logger.info(f"🟢 Application initialized in {(app_state.initialization_end - app_state.initialization_start).total_seconds()}s")

    except Exception as e:
        app_state.failure_reason = str(e)
        logger.critical(f"🔴 Initialization failed: {str(e)}")
        if settings.ENVIRONMENT == "production":
            import sys
            sys.exit(1)  # Crash the app in production if initialization fails

async def _initialize_with_retry(operation: str, task: callable, 
                               success_msg: str, failure_msg: str):
    """Retry wrapper for initialization tasks"""
    for attempt in range(1, INIT_RETRIES + 1):
        try:
            result = await task() if asyncio.iscoroutinefunction(task) else task()
            if result is not False:  # Allow for False returns indicating failure
                logger.info(success_msg)
                return
            logger.warning(f"{failure_msg} (attempt {attempt}/{INIT_RETRIES})")
        except Exception as e:
            logger.warning(f"{operation} failed: {str(e)} (attempt {attempt}/{INIT_RETRIES})")
        await asyncio.sleep(INIT_RETRY_DELAY)
    raise RuntimeError(failure_msg)

# --- Readiness Check Middleware ---
@app.middleware("http")
async def readiness_check(request, call_next):
    if not app_state.ready and request.url.path != "/health":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"Service initializing: {app_state.failure_reason or 'Not ready'}"}
        )
    return await call_next(request)

# --- Router Setup ---
app.include_router(test.router)
app.include_router(data.router)
app.include_router(precipitation.router)
app.include_router(map.router)
app.include_router(health.router) 
