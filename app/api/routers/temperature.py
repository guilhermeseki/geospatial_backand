from app.services.geoserver import GeoServerService
import logging
from fastapi import APIRouter, HTTPException, Response, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse

# Global variables
client = None
historical_datasets = None

router = APIRouter(prefix="/map", tags=["GeoServer Maps"])
logger = logging.getLogger(__name__)
geoserver = GeoServerService()
settings = get_settings()
sources_historical = ["chirps", "merge"]

GEOSERVER_WMS = f"{geoserver.base_url}/wms"

# --- CONSTANT FOR CONVERSION ---
DEGREES_TO_KM = 111.32

def haversine_distance(lon1, lat1, lon2, lat2):
    """
    Calculate the great-circle distance between two points (in decimal degrees).
    Returns distance in kilometers.
    """
    R = 6371  # Radius of earth in kilometers
    
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = R * c
    return km


@router.on_event("startup")
async def load_rasters(sources_list=sources_historical):
    """Load raster datasets into xarray + Dask for historical queries."""
    global historical_datasets
    global client
    historical_datasets = {}
    MAX_CORES = 4
    
    try:
        # Start Dask components synchronously here, as it's a one-time startup task.
        # Running the rest of the Dask compute work in asyncio.to_thread() makes this safe.
        cluster = LocalCluster(
            n_workers=MAX_CORES, 
            memory_limit='6GB',
            threads_per_worker=1, 
            processes=True,
            # IMPORTANT: Revert to synchronous Dask client for max compatibility
            asynchronous=False 
        )
        client = Client(cluster)
        logger.info(f"Dask client started on {client.scheduler.address} with {MAX_CORES} workers.")
    except Exception as e:
        logger.error(f"Could not start Dask Client: {e}")
        client = None
        pass

    # ... (Rest of the dataset loading logic remains the same) ...
    # Ensure parallel=True is only set if client is not None
    
    source_configs = {
        "era5": {
            "dir_suffix": "era5_historical",
            "file_glob": "brazil_era5_*.nc",
        },

    }

    for source in sources_list:
        if source in source_configs:
            config = source_configs[source]
            try:
                DATA_DIR = Path(settings.DATA_DIR) / config["dir_suffix"]
                nc_files = sorted(DATA_DIR.glob(config["file_glob"]))

                if not nc_files:
                    logger.warning(f"No netcdf files found for source '{source}' in directory: {DATA_DIR}")
                    continue

                ds = xr.open_mfdataset(
                    nc_files,
                    combine="nested",
                    concat_dim="time",
                    engine="netcdf4",
                    parallel=True if client else False,
                    chunks={"time": -1, "latitude": 20, "longitude": 20},
                    cache=False,
                )

                historical_datasets[source] = ds
                logger.info(f"Loaded dataset: {source}")

            except Exception as e:
                logger.error(f"Error loading source '{source}': {e}")
        else:
            logger.warning(f"Source '{source}' is not configured for loading.")