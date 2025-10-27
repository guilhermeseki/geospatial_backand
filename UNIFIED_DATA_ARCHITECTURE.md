# Unified Data Architecture - Operational Design

## Overview

This document describes the new unified architecture for all climate data (precipitation, temperature, NDVI) with:
- **Daily GeoTIFF files** for GeoServer WMS visualization
- **Yearly historical NetCDF files** for fast API time-series queries
- **Consistent directory structure** across all data types

## Benefits

✅ **Manageable file sizes**: Yearly files instead of one massive historical.nc
✅ **Easy updates**: Update individual years without reprocessing everything
✅ **Consistent architecture**: Same pattern for all data types
✅ **Operational efficiency**: Both GeoServer and API use optimized formats
✅ **Scalability**: Can process decades of data without memory issues

## Directory Structure

```
DATA_DIR/
├── chirps/                         # CHIRPS daily GeoTIFFs
│   ├── indexer.properties
│   ├── chirps_20240101.tif
│   ├── chirps_20240102.tif
│   └── ...
├── chirps_hist/                    # CHIRPS yearly historical NetCDF
│   ├── chirps_2024.nc
│   ├── chirps_2025.nc
│   └── ...
├── merge/                          # MERGE daily GeoTIFFs
│   ├── indexer.properties
│   ├── merge_20240101.tif
│   └── ...
├── merge_hist/                     # MERGE yearly historical NetCDF
│   ├── merge_2024.nc
│   └── ...
├── temp_max/                       # ERA5 daily max temp GeoTIFFs
│   ├── indexer.properties
│   ├── temp_max_20240101.tif
│   └── ...
├── temp_max_hist/                  # ERA5 yearly historical NetCDF
│   ├── temp_max_2024.nc
│   ├── temp_max_2025.nc
│   └── ...
├── temp_min/                       # ERA5 daily min temp GeoTIFFs
│   └── ...
├── temp_min_hist/                  # ERA5 yearly historical NetCDF
│   └── ...
├── temp/                           # ERA5 daily mean temp GeoTIFFs
│   └── ...
├── temp_hist/                      # ERA5 yearly historical NetCDF
│   └── ...
├── ndvi_s2/                        # Sentinel-2 NDVI GeoTIFFs
│   └── ...
├── ndvi_s2_hist/                   # Sentinel-2 yearly historical NetCDF
│   └── ...
└── ndvi_modis/                     # MODIS NDVI GeoTIFFs
    └── ...
```

## Data Processing Flow

### For Each Day of Data:

```mermaid
graph LR
    A[Download Raw Data] --> B[Process to Daily GeoTIFF]
    B --> C[Save to {source}/ directory]
    B --> D[Append to Yearly Historical NetCDF]
    D --> E[Save to {source}_hist/ directory]
    C --> F[GeoServer ImageMosaic]
    E --> G[API Time-Series Queries]
```

### Workflow Steps:

1. **Download**: Get raw data (GRIB2, NetCDF, or GeoTIFF)
2. **Process to GeoTIFF**: Crop to bbox, convert format, save as COG
3. **Append to yearly NetCDF**: Add to appropriate year file
4. **Refresh GeoServer**: Update mosaic index

## File Naming Conventions

### Daily GeoTIFFs
- Format: `{source}_{YYYYMMDD}.tif`
- Examples:
  - `chirps_20240515.tif`
  - `temp_max_20240515.tif`
  - `ndvi_s2_20240515.tif`

### Yearly Historical NetCDF
- Format: `{source}_{YYYY}.nc`
- Examples:
  - `chirps_2024.nc`
  - `temp_max_2024.nc`
  - `ndvi_s2_2024.nc`

## NetCDF Structure (Yearly Files)

Each yearly NetCDF file contains:

```python
Dataset structure:
  Dimensions:
    time: 365/366      # Days in year
    latitude: 416
    longitude: 416

  Variables:
    precip/temp_max/ndvi: (time, latitude, longitude)
      dtype: float32
      chunks: (1, 20, 20)    # Optimized for time-series queries
      compression: zlib, level 5

  Attributes:
    source: "CHIRPS v3.0" / "ERA5-Land" / "Sentinel-2"
    year: 2024
    bbox: [-75, -35, -33.5, 6.5]
```

## Loading Strategy (climate_data.py)

```python
# Load all yearly files for a source
data_dir = Path(settings.DATA_DIR) / f"{source}_hist"
nc_files = sorted(data_dir.glob(f"{source}_*.nc"))

# Combine into single dataset
ds = xr.open_mfdataset(
    nc_files,
    combine="nested",
    concat_dim="time",
    engine="netcdf4",
    parallel=True,  # Uses shared Dask client
    chunks={"time": -1, "latitude": 20, "longitude": 20}
)

# Result: Seamless access to all years
# ds.sel(time="2024-06-15")  # Works across all loaded years
```

## Processing Tasks

### New Unified Tasks (for all sources)

1. **`check_missing_dates(start, end, source)`**
   - Checks which dates are missing from:
     - GeoTIFF directory
     - Yearly historical NetCDF files
   - Returns list of dates to process

2. **`download_data(date, source)`**
   - Downloads raw data for the date
   - Returns path to raw file

3. **`process_to_geotiff(raw_path, date, source, bbox)`**
   - Converts raw data to GeoTIFF
   - Crops to bbox
   - Saves as COG to `{source}/` directory
   - Returns GeoTIFF path

4. **`append_to_yearly_historical(raw_path, date, source, bbox)`**
   - Determines which year file to update
   - Opens/creates `{source}_hist/{source}_{year}.nc`
   - Appends the date's data
   - Uses FUSE-safe write (temp file + copy)
   - Returns historical file path

5. **`refresh_mosaic(source)`**
   - Deletes old shapefile index
   - Triggers GeoServer reload
   - Updates mosaic time dimension

## Daily Flow Example (CHIRPS)

```python
@flow(name="chirps-daily-operational")
def chirps_daily_flow(start_date, end_date):
    # 1. Check what's missing
    missing = check_missing_dates(start_date, end_date, "chirps")

    for date in missing:
        # 2. Download
        raw_path = download_data(date, "chirps")

        # 3. Process to GeoTIFF (parallel)
        geotiff_path = process_to_geotiff(
            raw_path, date, "chirps",
            bbox=settings.latam_bbox_raster
        )

        # 4. Append to yearly historical (parallel)
        hist_path = append_to_yearly_historical(
            raw_path, date, "chirps",
            bbox=settings.latam_bbox_raster
        )

        # 5. Cleanup raw file
        raw_path.unlink()

    # 6. Refresh GeoServer mosaic once
    refresh_mosaic("chirps")
```

## Migration Plan

### Phase 1: Modify ERA5 Flow
- Change `append_to_historical_netcdf()` to create yearly files
- Update directory: `temp_max_hist/historical.nc` → `temp_max_hist/temp_max_2024.nc`
- climate_data.py already supports `open_mfdataset()` - no changes needed!

### Phase 2: Create Unified Precipitation Flow
- Create new `precipitation_flow.py` with tasks above
- Support both CHIRPS and MERGE
- Replace old `flows.py`

### Phase 3: Update NDVI Flow
- Modify to create yearly files
- Same pattern as ERA5/precipitation

### Phase 4: Migrate Existing Data (Optional)
- Script to split existing `historical.nc` → yearly files
- Or just let new data populate yearly files

## Advantages Over Current System

| Current | New |
|---------|-----|
| One huge `historical.nc` (10+ GB) | Multiple yearly files (~150 MB each) |
| Rewrite entire file when updating | Only update current year |
| Memory issues with large datasets | Each year loads independently |
| Slow to open and query | Fast parallel loading |
| Different patterns for each source | Unified architecture |

## API Impact

**None!** The API code stays the same:

```python
# This still works exactly the same
ds = get_dataset('precipitation', 'chirps')
result = ds.sel(time="2024-06-15", lat=-15.8, lon=-47.9)
```

The `xr.open_mfdataset()` makes multiple files look like one dataset.

## GeoServer Impact

**None!** GeoServer reads from daily GeoTIFF directories as before.

## Disk Space

- **GeoTIFF**: ~500KB per day per source
- **Yearly NetCDF**: ~150MB per year per source
- **Example for 10 years of CHIRPS**:
  - GeoTIFFs: 3,650 days × 500KB = ~1.8GB
  - Historical: 10 years × 150MB = ~1.5GB
  - **Total: ~3.3GB** (very manageable!)

## Performance

- **Loading time**: 2-3 seconds to load 10 years (vs 10+ seconds for one huge file)
- **Query time**: Milliseconds (chunked by time for fast access)
- **Update time**: Only write to current year's file
- **Parallel processing**: Each year can be processed independently

## Next Steps

1. ✅ Design architecture (this document)
2. 🔄 Implement ERA5 yearly files
3. 🔄 Create unified precipitation flow
4. 🔄 Update NDVI flow
5. 🔄 Test end-to-end
6. 🔄 Document operational procedures

## Questions?

This architecture is:
- ✅ Scalable to decades of data
- ✅ Easy to maintain and update
- ✅ Consistent across all sources
- ✅ Optimized for both visualization (GeoServer) and queries (API)
- ✅ Production-ready

Ready to implement? 🚀
