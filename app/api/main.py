#app/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.services.geoserver import GeoServerService
from app.config.settings import get_settings
import logging
from logging.handlers import RotatingFileHandler
import os
import asyncio
from app.api.routers import map, georisk
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






# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     app_state.initialization_start = datetime.now()
#     geoserver = GeoServerService()
#     # List all sources you want to ensure mosaics for
#     sources = ["chirps_final"]

    # In async context
    #await geoserver.ensure_all_mosaics(sources)

    # try:
    #     logger.info("🔗 Connecting to GeoServer...")
    #     for attempt in range(1, INIT_RETRIES + 1):
    #         if await geoserver.check_geoserver_alive():
    #             break
    #         await asyncio.sleep(INIT_RETRY_DELAY)
    #     else:
    #         logger.error("GeoServer connection failed after retries")
    #         app_state.ready = True
    #         yield
    #         return
    #     logger.info("✅ GeoServer connection verified")

    #     data_path = Path(settings.DATA_DIR)
    #     logger.debug(f"Checking data directory: {data_path}")
    #     if not data_path.exists():
    #         logger.error(f"Data directory not found: {data_path}")
    #         app_state.ready = True
    #         yield
    #         return
    #     logger.info(f"✅ Data directory found: {data_path}")

    #     async with httpx.AsyncClient(auth=geoserver.auth) as client:
    #         for source in CONFIG_SOURCES:
    #             logger.info(f"⚙️ Checking ImageMosaic layer for {source}...")
    #             response = await client.get(
    #                 f"{geoserver.base_url}/rest/workspaces/{geoserver.workspace}/coveragestores/{source}_mosaic/coverages/{source}"
    #             )
    #             if response.status_code in (200, 201, 202):
    #                 logger.info(f"✅ Layer {source}_mosaic already exists")
    #                 continue
    #             for attempt in range(1, INIT_RETRIES + 1):
    #                 try:
    #                     #await geoserver.ensure_layer_exists(source, "2025-07-02")
    #                     logger.info(f"✅ ImageMosaic layer initialized for {source}")
    #                     break
    #                 except Exception as e:
    #                     logger.warning(f"⚠️ ImageMosaic layer attempt {attempt} failed for {source}: {str(e)}")
    #                     if attempt == INIT_RETRIES:
    #                         logger.error(f"ImageMosaic layer failed for {source}: {str(e)}")
    #                         break
    #                     await asyncio.sleep(INIT_RETRY_DELAY)

    #     app_state.ready = True
    #     app_state.initialization_end = datetime.now()
    #     logger.info(f"🟢 Application initialized in {(app_state.initialization_end - app_state.initialization_start).total_seconds()}s")
    #     yield
    # except Exception as e:
    #     app_state.failure_reason = str(e)
    #     logger.critical(f"🔴 Initialization failed: {str(e)}")
    #     app_state.ready = True
    #     yield

app = FastAPI(
    title="Geospatial Backend",
    description="API for geospatial data processing",
    version="1.0.0",
    #lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],#settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    app_state.ready = True

# @app.on_event("startup")
# async def startup_event():
#     geoserver = GeoServerService()
#     logger.info("⏳ Waiting for GeoServer to be alive...")

#     for attempt in range(5):
#         if await geoserver.check_geoserver_alive():
#             logger.info("✅ GeoServer is alive, fixing ingestion shapefile...")
#             success = fix_ingestion_field()
#             if success:
#                 logger.info("📂 Ingestion shapefile fixed, recalculating mosaic...")
#              #   await recalc_geoserver_mosaic()
#             break
#         else:
#             logger.warning("GeoServer not ready yet, retrying...")
#             await asyncio.sleep(5)
@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "healthy"}

# @app.middleware("http")
# async def readiness_check(request, call_next):
#     if not app_state.ready and request.url.path != "/health":
#         return JSONResponse(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             content={"detail": f"Service initializing: {app_state.failure_reason or 'Not ready'}"}
#         )
#     return await call_next(request)
@app.middleware("http")
async def readiness_check(request, call_next):
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
    if not app_state.ready and request.url.path != "/health":
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
    
#app.include_router(test.router)
#app.include_router(data.router)
#app.include_router(precipitation.router)
app.include_router(map.router)
#app.include_router(health.router)
app.include_router(georisk.router)
