# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a geospatial climate data API backend built with FastAPI that provides access to precipitation (CHIRPS, MERGE), temperature (ERA5), and NDVI data through both direct NetCDF processing and GeoServer WMS integration. The system uses a shared Dask cluster for efficient parallel data processing and maintains dual storage formats: daily GeoTIFF files for GeoServer mosaics and historical NetCDF files for fast time-series queries.

## Architecture

### Data Flow Architecture

The system follows a dual-storage pattern:

1. **Raw Data Ingestion (Prefect Flows)**
   - `app/workflows/data_processing/flows.py` - CHIRPS/MERGE precipitation flows
   - `app/workflows/data_processing/era5_flow.py` - ERA5 temperature data (temp_max, temp_min, temp)
   - `app/workflows/data_processing/ndvi_flow.py` - Sentinel-2 and MODIS NDVI data via Microsoft Planetary Computer (free, no auth)

2. **Dual Storage System**
   - **GeoTIFF mosaics**: Individual daily `.tif` files in `DATA_DIR/{source}/` directories for GeoServer time-enabled WMS layers
   - **Historical NetCDF**: Consolidated `DATA_DIR/{source}_hist/historical.nc` files with chunked storage (time=1, lat=20, lon=20) for fast xarray queries

3. **Shared Climate Data Service** (`app/services/climate_data.py`)
   - Single shared Dask client used by ALL datasets (precipitation + temperature)
   - Loads historical NetCDF files into memory on startup
   - Provides unified access via `get_dataset(data_type, source)` function
   - ~50% memory savings vs. separate Dask clients per dataset

4. **API Layer** (`app/api/routers/`)
   - Point queries (history, triggers) → Use historical NetCDF via `get_dataset()`
   - Area queries → Use historical NetCDF with spatial slicing
   - WMS image requests → Proxy to GeoServer for rendered map tiles
   - Polygon queries → Use historical NetCDF with Shapely geometry clipping

### Critical Data Processing Pattern

When processing new data in flows (ERA5, CHIRPS, MERGE, NDVI):

```python
# 1. Check what's missing from BOTH storage formats
missing_info = check_missing_dates(start_date, end_date, variable, statistic)
missing_geotiff = missing_info['geotiff']      # Missing from GeoTIFF mosaics
missing_historical = missing_info['historical']  # Missing from historical.nc
missing_download = missing_info['download']     # Union of both (need to download)

# 2. Download only what's needed
batch_path = download_era5_land_daily_batch(...)  # Download raw NetCDF

# 3. Process to GeoTIFF (only dates missing from mosaics)
if missing_geotiff:
    process_era5_land_daily_to_geotiff(batch_path, dates_to_process=missing_geotiff)

# 4. Append to historical NetCDF (only dates missing from historical)
if missing_historical:
    append_to_historical_netcdf(batch_path, dates_to_append=missing_historical)

# 5. Cleanup raw files
cleanup_raw_files(batch_path)
```

This pattern ensures:
- No duplicate downloads
- No redundant processing
- Efficient incremental updates to both storage systems

### API Query Patterns

**Point-based queries** (precipitation/temperature history, triggers):
```python
# ❌ DON'T: Query synchronously in async endpoint
result = historical_ds.sel(lat=lat, lon=lon).compute()  # Blocks event loop!

# ✅ DO: Run Dask compute in thread pool
async def get_history(request):
    ds = get_dataset('precipitation', request.source)
    result = await asyncio.to_thread(_query_sync, ds, request)
    return result

def _query_sync(ds, request):
    # Synchronous Dask .compute() runs in separate thread
    ts = ds.sel(lat=request.lat, lon=request.lon, method="nearest")
    return ts.compute()  # OK in thread
```

**Area-based queries** (area triggers, polygon queries):
```python
# Same pattern - always use asyncio.to_thread for .compute()
result = await asyncio.to_thread(_calculate_area_exceedances_sync, ds, request)
```

### GeoServer Integration

- **ImageMosaic stores**: Auto-created from GeoTIFF directories with `indexer.properties` config
- **Time dimension**: Extracted from filenames using regex `.*_(\d{8})\.tif` → timestamp field
- **WMS proxy**: FastAPI endpoint `/precipitation/wms` proxies to GeoServer to hide internal URLs
- **Reindexing**: After adding new GeoTIFFs, call `refresh_mosaic_shapefile(source)` task

## Development Commands

### Running the Application

```bash
# Start FastAPI server
cd /opt/geospatial_backend
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

# The app initializes on startup:
# 1. Starts shared Dask client (4 workers, 6GB each)
# 2. Loads precipitation datasets (chirps, merge) into memory
# 3. Loads temperature datasets (temp_max, temp_min, temp) into memory
# Check logs to verify all datasets loaded successfully
```

### Running Data Processing Flows

```bash
# ERA5 temperature data (creates GeoTIFFs + historical NetCDF)
python app/run_era5.py

# CHIRPS precipitation data
python app/run_chirps.py

# MERGE precipitation data
python app/run_merge.py

# NDVI data (Sentinel-2 + MODIS via Microsoft Planetary Computer)
python app/run_ndvi.py

# Debug ERA5 flow
python app/run_era5_debug.py
```

### Running Tests

```bash
# Run all tests
pytest app/tests/

# Run specific test categories
pytest app/tests/unit/              # Unit tests
pytest app/tests/integration/       # Integration tests (require GeoServer)

# Run specific test file
pytest app/tests/test_request_historical.py
pytest app/tests/test_request_triggers.py
pytest app/tests/test_request_triggers_area.py
```

### GeoServer Management

```bash
# Restart GeoServer (requires sudo)
sudo systemctl restart geoserver

# Check GeoServer status
curl -u admin:password http://localhost:8080/geoserver/rest/about/version.json

# Reindex mosaic time dimension (via REST API)
curl -u admin:password -X POST \
  "http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/chirps/external.imagemosaic?recalculate=all"

# Test WMS GetMap request
curl "http://localhost:8080/geoserver/wms?service=WMS&version=1.1.1&request=GetMap&layers=precipitation_ws:chirps&bbox=-94,-53,-34,25&width=800&height=600&srs=EPSG:4326&time=2025-07-05&format=image/png" --output test.png
```

## Important Configuration

### Settings (`app/config/settings.py`)

- `DATA_DIR`: Base directory for all geospatial data (default: `/mnt/workwork/geoserver_data/`)
- `latam_bbox`: Bbox formats for different libraries:
  - `latam_bbox` = (S, W, N, E) for general use
  - `latam_bbox_raster` = (W, S, E, N) for rasterio
  - `latam_bbox_cds` = [N, W, S, E] for CDS API
- GeoServer credentials and endpoints
- Copernicus CDS API credentials

### Directory Structure

```
DATA_DIR/
├── chirps/                    # CHIRPS GeoTIFF mosaic (daily files)
├── chirps_hist/
│   └── historical.nc         # CHIRPS historical NetCDF (all dates)
├── merge/                     # MERGE GeoTIFF mosaic
├── merge_hist/
│   └── historical.nc
├── temp_max/                  # ERA5 daily max temp GeoTIFFs
├── temp_max_hist/
│   └── historical.nc
├── temp_min/                  # ERA5 daily min temp GeoTIFFs
├── temp_min_hist/
│   └── historical.nc
├── temp/                      # ERA5 daily mean temp GeoTIFFs
├── temp_hist/
│   └── historical.nc
├── ndvi_s2/                   # Sentinel-2 NDVI GeoTIFFs
├── ndvi_s2_hist/
│   └── historical.nc
├── ndvi_modis/                # MODIS NDVI GeoTIFFs
├── ndvi_modis_hist/
│   └── historical.nc
└── raw/                       # Temporary download cache
    ├── era5_land_daily/
    ├── chirps/
    ├── merge/
    ├── sentinel2/
    └── modis/
```

## Critical Implementation Notes

### When Adding New Data Sources

1. **Create the flow** in `app/workflows/data_processing/` following the dual-storage pattern
2. **Add to climate_data.py**: Extend `load_*_datasets()` functions to load new historical NetCDF
3. **Create router** in `app/api/routers/` that uses `get_dataset()` for queries
4. **Update main.py**: Include the new router in `app.include_router()`
5. **Restart app**: New historical data is loaded on startup

### When Modifying Queries

- **Always use `asyncio.to_thread()`** for xarray `.compute()` operations in async endpoints
- **Never call `.compute()` directly** in FastAPI async handlers (blocks event loop)
- **Use `method="nearest"` with `tolerance`** for point queries to handle coordinate imprecision
- **Apply masks before `.compute()`** to minimize data loaded into memory

### When Working with Prefect Flows

- Flows automatically check for missing dates before downloading
- Tasks are retryable - use `@task(retries=N, retry_delay_seconds=M)` for network operations
- Long-running tasks should have `timeout_seconds` parameter
- Always cleanup raw files after processing to save disk space

### GeoServer Time-Enabled Mosaics

- **Filename format**: `{source}_{YYYYMMDD}.tif` (e.g., `chirps_20250705.tif`)
- **indexer.properties must exist** with:
  ```properties
  TimeAttribute=timestamp
  Schema=*the_geom:Polygon,location:String,timestamp:java.util.Date
  PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](timestamp)
  timeregex=.*_(\d{8})\.tif
  timeformat=yyyyMMdd
  ```
- After adding new files, trigger reindex via `refresh_mosaic_shapefile()` task or REST API

### Temperature Unit Conversion

ERA5 data comes in Kelvin and must be converted to Celsius:
- Conversion happens in `process_era5_land_daily_to_geotiff()` for GeoTIFFs
- Conversion happens in `append_to_historical_netcdf()` for historical NetCDF
- Both conversions use `da - 273.15`

### NDVI Data Sources

Both sources are **100% FREE via Microsoft Planetary Computer** (no authentication required):
- **Sentinel-2 L2A**: 10m resolution, collection="sentinel-2-l2a"
- **MODIS MOD13Q1**: 250m resolution, 16-day composites, collection="modis-13Q1-061"
- Install requirements: `pip install pystac-client planetary-computer`
- Uses signed URLs via `planetary_computer.sign(asset.href)`

## Common Issues & Solutions

### Issue: "Dataset not loaded" errors in API

**Cause**: Historical NetCDF not created yet or failed to load on startup

**Solution**:
1. Check logs for dataset loading errors
2. Run the appropriate flow to create historical NetCDF
3. Restart FastAPI app to reload datasets

### Issue: GeoServer mosaic time dimension shows wrong dates

**Cause**: Shapefile index out of sync with GeoTIFF files

**Solution**:
```bash
# Delete old index files
rm /path/to/mosaic/*.shp /path/to/mosaic/*.dbf /path/to/mosaic/*.shx

# Reindex via API
curl -u admin:password -X POST \
  "http://localhost:8080/geoserver/rest/workspaces/precipitation_ws/coveragestores/{source}/external.imagemosaic?recalculate=all"
```

### Issue: Dask workers running out of memory

**Cause**: Too many large datasets loaded simultaneously or inefficient chunking

**Solution**:
- Reduce memory_limit in `get_dask_client()` (currently 6GB per worker)
- Reduce n_workers (currently 4)
- Apply spatial/temporal slicing before `.compute()`
- Use smaller chunk sizes in encoding

### Issue: ERA5 download fails with "data not available"

**Cause**: ERA5-Land has 5-7 day lag from current date

**Solution**: Only request dates at least 7 days before today. The flow warns about this automatically.

## API Documentation

When server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health
- **Status with diagnostics**: http://localhost:8000/status
