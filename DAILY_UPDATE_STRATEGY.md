# Daily Update Strategy - Date Range Checking

## Overview

Each dataset checks a specific date range based on its characteristics, data lag, and operational requirements. All flows skip files that already exist locally, making it safe to run with wide date ranges.

## Date Range Strategy by Dataset

| Dataset | Check Range | Reason | Data Lag |
|---------|-------------|--------|----------|
| **CHIRPS** | Last 30 days | Recent gaps + daily availability | 1-2 days |
| **MERGE** | Last 30 days | Recent gaps + daily availability | 1-2 days |
| **ERA5 Temperature** | Last 30 days (with 7-day offset) | CDS API lag + recent gaps | 5-7 days |
| **ERA5 Wind** | Last 30 days (with 7-day offset) | CDS API lag + recent gaps | 5-7 days |
| **GLM Lightning** | April 15, 2025 → yesterday | Only 8 months operational, fill all gaps | 1-2 days |

## Detailed Strategy

### 1. CHIRPS Precipitation

**Date Range**: `today - 30 days` → `yesterday`

```python
start_date = today - timedelta(days=30)
end_date = today - timedelta(days=1)
```

**Why 30 days**:
- Has 10 years of historical data (2015-2025)
- Daily availability from UCSB CHIRPS server
- 30-day window catches recent gaps from server issues
- Files exist check makes it fast (only downloads missing)

**Current Status**: 3,685 files (2015-10-01 → 2025-11-01)

---

### 2. MERGE Precipitation

**Date Range**: `today - 30 days` → `yesterday`

```python
start_date = today - timedelta(days=30)
end_date = today - timedelta(days=1)
```

**Why 30 days**:
- Has 11 years of historical data (2014-2025)
- Daily availability from CPTEC/INPE server
- 30-day window catches recent gaps from server issues
- Files exist check makes it fast (only downloads missing)

**Current Status**: 4,008 files (2014-11-01 → 2025-10-22)

---

### 3. ERA5 Temperature (max/min/mean)

**Date Range**: `(today - 7 days) - 30 days` → `today - 7 days`

```python
end_date = date.today() - timedelta(days=7)
start_date = end_date - timedelta(days=30)
```

**Why 30 days with 7-day offset**:
- ERA5-Land has 5-7 day publication lag from Copernicus CDS
- 30-day window catches recent gaps from CDS API issues
- Requesting data before 7-day lag returns empty results
- Files exist check makes it fast (only downloads missing)

**Current Status**: 3,960 files (temp_max)

**Special handling**:
- Downloads all 3 variables in single CDS request (efficient)
- Converts Kelvin → Celsius automatically
- Creates separate GeoTIFFs for temp_max, temp_min, temp_mean

---

### 4. ERA5 Wind Speed

**Date Range**: `(today - 7 days) - 30 days` → `today - 7 days`

```python
end_date = date.today() - timedelta(days=7)
start_date = end_date - timedelta(days=30)
```

**Why 30 days with 7-day offset**:
- Same as temperature (uses ERA5-Land source)
- Downloads u and v wind components
- Calculates wind speed: sqrt(u² + v²)

**Special handling**:
- Single CDS request for both components
- Wind speed calculation in processing step

---

### 5. GLM Lightning (Flash Extent Density)

**Date Range**: `April 15, 2025` → `today - 2 days`

```python
start_date = date(2025, 4, 15)  # GOES-19 operational date
end_date = date.today() - timedelta(days=2)  # 2-day lag
```

**Why full operational period**:
- GOES-19 only operational since April 15, 2025 (~8 months)
- Only 213 files currently (should have ~245 by Dec 15)
- Need to fill gaps from entire operational period
- NASA Earthdata can be unreliable, need multiple attempts

**Current Status**: 213 files (2025-04-01 → 2025-11-30)

**Special handling**:
- Downloads 1,440 minute files per day
- Aggregates to daily Flash Extent Density (FED)
- Requires NASA Earthdata credentials

---

## File Existence Check

All flows use this pattern:

```python
output_path = mosaic_dir / f"{source}_{date.strftime('%Y%m%d')}.tif"
if output_path.exists():
    logger.info(f"File already exists, skipping")
else:
    download_and_process()
```

This makes it **safe and fast** to run with wide date ranges:
- ✅ No duplicate downloads
- ✅ No wasted processing
- ✅ Only downloads truly missing files
- ✅ Idempotent (can run multiple times safely)

## Historical NetCDF Updates

All flows update **both storage formats**:

1. **GeoTIFF mosaics**: Individual daily files for GeoServer WMS
2. **Historical NetCDF**: Consolidated time-series for API queries

The flows automatically:
- Check which dates are missing from historical NetCDF
- Append only new dates (no duplicates)
- Use efficient chunking: `time=1, lat=20, lon=20`
- Compress with zlib level 4

## Brazil Clipping

All datasets are clipped to Brazil boundaries using:

**Shapefile**: `/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp`

**Method**:
- CHIRPS/MERGE/ERA5: `gdalwarp -cutline`
- GLM: `rasterio` with shapefile mask

This happens automatically during processing - no manual intervention needed.

## Performance Expectations

### Daily Run (when up-to-date)

| Dataset | Files Checked | Files Downloaded | Processing Time |
|---------|---------------|------------------|-----------------|
| CHIRPS | 30 | 0-1 | ~2 min |
| MERGE | 30 | 0-1 | ~2 min |
| ERA5 Temp | 30 | 0-1 | ~5 min |
| ERA5 Wind | 30 | 0-1 | ~5 min |
| GLM | ~245 | 0-1 | ~3 min |

**Total**: ~15-20 minutes when up-to-date

### Backfill Run (catching up)

If system is down for a week:

| Dataset | Files Checked | Files Downloaded | Processing Time |
|---------|---------------|------------------|-----------------|
| CHIRPS | 30 | ~7 | ~15 min |
| MERGE | 30 | ~7 | ~15 min |
| ERA5 Temp | 30 | ~7 | ~30 min |
| ERA5 Wind | 30 | ~7 | ~30 min |
| GLM | ~245 | ~7 | ~30 min |

**Total**: ~2 hours for 1-week backfill

## Monitoring

Check if updates are working:

```bash
# View today's update log
grep "$(date +%Y%m%d)" /opt/geospatial_backend/logs/daily_updates.log

# Check for failures
grep "✗ Failed" /opt/geospatial_backend/logs/daily_updates.log

# Check latest files
ls -lt /mnt/workwork/geoserver_data/chirps/*.tif | head -3
ls -lt /mnt/workwork/geoserver_data/merge/*.tif | head -3
ls -lt /mnt/workwork/geoserver_data/temp_max/*.tif | head -3
ls -lt /mnt/workwork/geoserver_data/glm_fed/*.tif | head -3
```

## Adjusting Date Ranges

If you need to change the date ranges, edit the flow files:

- `/opt/geospatial_backend/app/workflows/data_processing/precipitation_flow.py` (CHIRPS, MERGE)
- `/opt/geospatial_backend/app/workflows/data_processing/era5_flow.py` (ERA5 Temperature & Wind)
- `/opt/geospatial_backend/app/workflows/data_processing/glm_fed_flow.py` (GLM Lightning)

Example: Change CHIRPS to check last 60 days:

```python
start_date = today - timedelta(days=60)  # Changed from 30
end_date = today - timedelta(days=1)
```

The file existence check ensures only missing files are downloaded.

## Summary

✅ **CHIRPS & MERGE**: Last 30 days (catches recent gaps)
✅ **ERA5**: Last 30 days with 7-day offset (respects CDS lag)
✅ **GLM**: Full operational period (only 8 months, need to fill gaps)
✅ **All datasets**: Skip existing files (fast and safe)
✅ **All datasets**: Update both GeoTIFF + historical NetCDF
✅ **All datasets**: Clip to Brazil shapefile automatically
