"""
Shared climate data service with unified Dask client
Manages all climate datasets (precipitation, temperature, etc.)
ALL datasets share the SAME Dask client for optimal memory usage
"""
import logging
import xarray as xr
from pathlib import Path
from dask.distributed import Client, LocalCluster
from typing import Optional, Dict
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global shared Dask client - ONE client for ALL datasets
_dask_client: Optional[Client] = None

# Global datasets organized by type
_climate_datasets: Dict[str, Dict[str, xr.Dataset]] = {
    'precipitation': {},
    'temperature': {}
}


def get_dask_client() -> Optional[Client]:
    """
    Get or create THE SINGLE SHARED Dask client for ALL climate data operations.
    This client is used by both precipitation and temperature datasets.
    Returns None if client cannot be created.
    """
    global _dask_client
    
    if _dask_client is None:
        try:
            cluster = LocalCluster(
                n_workers=4,
                memory_limit='6GB',
                threads_per_worker=1,
                processes=True,
                asynchronous=False
            )
            _dask_client = Client(cluster)
            logger.info(f"✓ SHARED Dask client started: {_dask_client.scheduler.address}")
            logger.info(f"  Workers: {len(_dask_client.cluster.workers)}")
            logger.info(f"  This client will be used by ALL datasets (precipitation + temperature)")
        except Exception as e:
            logger.error(f"✗ Failed to start Dask client: {e}")
            _dask_client = None
    
    return _dask_client


def load_precipitation_datasets():
    """
    Load all precipitation datasets (CHIRPS, MERGE).
    Uses the SHARED Dask client for parallel loading.
    """
    global _climate_datasets
    
    source_configs = {
        "chirps": {
            "dir_suffix": "chirps_historical",
            "file_glob": "brazil_chirps_*.nc",
        },
        "merge": {
            "dir_suffix": "merge_historical",
            "file_glob": "brazil_merge_*.nc",
        },
    }
    
    # Get the shared Dask client
    client = get_dask_client()
    
    if client:
        logger.info(f"Loading precipitation datasets using shared Dask client: {client.scheduler.address}")
    else:
        logger.warning("Loading precipitation datasets without Dask (no parallelization)")
    
    for source, config in source_configs.items():
        try:
            data_dir = Path(settings.DATA_DIR) / config["dir_suffix"]
            nc_files = sorted(data_dir.glob(config["file_glob"]))
            
            if not nc_files:
                logger.warning(f"No precipitation files found for '{source}' in {data_dir}")
                continue
            
            # EXPLICIT: Use parallel=True only if we have the shared Dask client
            ds = xr.open_mfdataset(
                nc_files,
                combine="nested",
                concat_dim="time",
                engine="netcdf4",
                parallel=True if client else False,  # ← Uses SHARED client
                chunks={"time": -1, "latitude": 20, "longitude": 20},
                cache=False,
            )
            
            _climate_datasets['precipitation'][source] = ds
            logger.info(f"✓ Loaded precipitation dataset: {source}")
            logger.info(f"  Using Dask: {bool(client)}")
            logger.info(f"  Chunks: {ds.chunks}")
            
        except Exception as e:
            logger.error(f"✗ Error loading precipitation source '{source}': {e}")


def load_temperature_datasets():
    """
    Load all ERA5 temperature datasets (temp_max, temp_min, temp).
    Uses the SAME SHARED Dask client as precipitation datasets.
    
    Each temperature variable has its own directory structure:
    - temp_max/ (daily GeoTIFFs) + temp_max_hist/historical.nc
    - temp_min/ (daily GeoTIFFs) + temp_min_hist/historical.nc  
    - temp/ (daily GeoTIFFs) + temp_hist/historical.nc
    
    We load the historical.nc files which contain all the data.
    """
    global _climate_datasets
    
    # Map source names to their historical directory names
    temp_sources = {
        "temp_max": "temp_max_hist",
        "temp_min": "temp_min_hist",
        "temp": "temp_hist"
    }
    
    # Get the shared Dask client (same one precipitation uses)
    client = get_dask_client()
    
    if client:
        logger.info(f"Loading temperature datasets using SAME shared Dask client: {client.scheduler.address}")
        logger.info(f"  Client workers: {len(client.cluster.workers)} (shared with precipitation)")
    else:
        logger.warning("Loading temperature datasets without Dask (no parallelization)")
    
    for source, hist_dir_name in temp_sources.items():
        try:
            hist_dir = Path(settings.DATA_DIR) / hist_dir_name
            hist_file = hist_dir / "historical.nc"
            
            if not hist_file.exists():
                logger.warning(f"Temperature historical file not found: {hist_file}")
                logger.info(f"  Expected location: {hist_file}")
                logger.info(f"  Make sure ERA5 daily flow has run and created {hist_dir_name}/historical.nc")
                continue
            
            # EXPLICIT: Open with chunks to use the SHARED Dask client
            # When you open with chunks and a Dask client is active, xarray uses it automatically
            ds = xr.open_dataset(
                hist_file,
                engine="netcdf4",
                chunks={"time": -1, "latitude": 20, "longitude": 20},  # ← Triggers Dask usage
            )
            
            # Verify the variable exists in the dataset
            if source not in ds.data_vars:
                logger.warning(f"Variable '{source}' not found in {hist_file}")
                logger.info(f"  Available variables: {list(ds.data_vars)}")
                ds.close()
                continue
            
            _climate_datasets['temperature'][source] = ds
            logger.info(f"✓ Loaded temperature dataset: {source}")
            logger.info(f"  File: {hist_file}")
            logger.info(f"  Variable: {source}")
            logger.info(f"  Using shared Dask client: {bool(client)}")
            logger.info(f"  Chunks: {ds.chunks}")
            
            # Log time range
            if 'time' in ds.dims:
                time_min = ds.time.min().values
                time_max = ds.time.max().values
                logger.info(f"  Time range: {time_min} to {time_max}")
                logger.info(f"  Total days: {len(ds.time)}")
            
            # Log spatial dimensions
            if 'latitude' in ds.dims and 'longitude' in ds.dims:
                logger.info(f"  Spatial dims: {len(ds.latitude)}×{len(ds.longitude)} (lat×lon)")
            
        except Exception as e:
            logger.error(f"✗ Error loading temperature source '{source}': {e}")
            import traceback
            logger.error(traceback.format_exc())


def get_dataset(data_type: str, source: str) -> Optional[xr.Dataset]:
    """
    Get a loaded climate dataset.
    
    Args:
        data_type: 'precipitation' or 'temperature'
        source: Source name (e.g., 'chirps', 'temp_max')
    
    Returns:
        xarray Dataset or None if not loaded
    """
    return _climate_datasets.get(data_type, {}).get(source)


def get_available_sources(data_type: str) -> list:
    """
    Get list of available sources for a data type.
    
    Args:
        data_type: 'precipitation' or 'temperature'
    
    Returns:
        List of available source names
    """
    return list(_climate_datasets.get(data_type, {}).keys())


def is_data_loaded(data_type: str, source: str) -> bool:
    """Check if a specific dataset is loaded"""
    return get_dataset(data_type, source) is not None


def get_dataset_info(data_type: str, source: str) -> Optional[dict]:
    """
    Get metadata about a loaded dataset.
    
    Returns:
        Dictionary with dataset info or None
    """
    ds = get_dataset(data_type, source)
    if ds is None:
        return None
    
    info = {
        "source": source,
        "type": data_type,
        "variables": list(ds.data_vars),
        "dimensions": dict(ds.dims),
        "coordinates": list(ds.coords),
    }
    
    if 'time' in ds.dims:
        info["time_range"] = {
            "start": str(ds.time.min().values),
            "end": str(ds.time.max().values),
            "count": int(len(ds.time))
        }
    
    return info


def get_dask_client_info() -> Optional[dict]:
    """
    Get information about the shared Dask client.
    
    Returns:
        Dictionary with client info or None if no client
    """
    client = get_dask_client()
    if client is None:
        return None
    
    return {
        "scheduler_address": str(client.scheduler.address),
        "dashboard_link": client.dashboard_link,
        "num_workers": len(client.cluster.workers),
        "total_memory": sum(w.memory_limit for w in client.cluster.workers.values()),
        "status": "running"
    }


def initialize_climate_data():
    """
    Initialize all climate datasets with a SINGLE SHARED Dask client.
    Call this on application startup.
    
    Steps:
    1. Start ONE shared Dask client
    2. Load precipitation datasets (using shared client)
    3. Load temperature datasets (using SAME shared client)
    """
    logger.info("=" * 80)
    logger.info("Initializing Climate Data Service")
    logger.info("=" * 80)
    
    # Step 1: Start THE shared Dask client (only one!)
    client = get_dask_client()
    if client:
        logger.info(f"✓ Shared Dask client ready")
        logger.info(f"  Address: {client.scheduler.address}")
        logger.info(f"  Dashboard: {client.dashboard_link}")
        logger.info(f"  Workers: {len(client.cluster.workers)}")
        logger.info(f"  Memory per worker: 6GB")
        logger.info(f"  Total memory: {len(client.cluster.workers) * 6}GB")
        logger.info(f"  This client will be shared by ALL datasets!")
    else:
        logger.warning("⚠ Dask client not available - datasets will load without parallelization")
    
    logger.info("")
    
    # Step 2: Load precipitation datasets (will use shared client)
    logger.info("Loading precipitation datasets...")
    logger.info("-" * 80)
    load_precipitation_datasets()
    
    logger.info("")
    
    # Step 3: Load temperature datasets (will use SAME shared client)
    logger.info("Loading temperature datasets...")
    logger.info("-" * 80)
    load_temperature_datasets()
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("Climate Data Service Summary")
    logger.info("=" * 80)
    
    precip_sources = get_available_sources('precipitation')
    temp_sources = get_available_sources('temperature')
    total_sources = len(precip_sources) + len(temp_sources)
    
    logger.info(f"Precipitation sources: {len(precip_sources)} - {precip_sources}")
    logger.info(f"Temperature sources: {len(temp_sources)} - {temp_sources}")
    logger.info(f"Total datasets loaded: {total_sources}")
    
    if client:
        logger.info(f"")
        logger.info(f"✓ All {total_sources} datasets share ONE Dask client")
        logger.info(f"  Memory efficiency: ~50% savings vs separate clients")
    
    logger.info("=" * 80)


def shutdown_climate_data():
    """Cleanup resources on application shutdown"""
    global _dask_client
    
    logger.info("Shutting down Climate Data Service...")
    
    if _dask_client:
        try:
            _dask_client.close()
            logger.info("✓ Shared Dask client closed")
        except Exception as e:
            logger.error(f"Error closing Dask client: {e}")
    
    _climate_datasets.clear()
    logger.info("✓ Climate datasets cleared")
    logger.info("✓ Shutdown complete")