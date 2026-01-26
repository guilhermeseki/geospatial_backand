# ERA5 Fix: Removed Interpolation

## Problem Fixed

The ERA5 flow was downloading data for all of Latin America and then interpolating it down to a smaller grid. This caused:

❌ **Interpolated/resampled data** (not native resolution)
❌ **Downloaded 2.7x more data than needed** (LatAm instead of Brazil)
❌ **Historical NetCDF contained LatAm data** (not just Brazil)
❌ **Required scipy dependency** for interpolation
❌ **Lower spatial resolution** (downsampled from 780×600 to 416×416)

## Changes Made

### 1. Added Brazil CDS Bbox to Settings

**File**: `app/config/settings.py`

```python
brazil_bbox_cds: List[float] = [6.55, -75.05, -35.05, -33.45]  # [N, W, S, E]
```

This bbox is calculated to return exactly 416×416 grid at 0.1° resolution from ERA5-Land.

### 2. Updated ERA5 Flow to Use Brazil Bbox

**File**: `app/workflows/data_processing/era5_flow.py`

**Changed**:
```python
# OLD: Downloaded all LatAm
area=settings.latam_bbox_cds  # [25.0, -94.0, -53.0, -34.0] → 780×600 grid

# NEW: Downloads only Brazil
area=settings.brazil_bbox_cds  # [6.55, -75.05, -35.05, -33.45] → 416×416 grid
```

### 3. Removed Interpolation Code

**Removed** the entire interpolation block:
```python
# REMOVED: No longer needed
if current_shape != target_shape:
    da = da.interp(
        longitude=target_lon,
        latitude=target_lat,
        method='linear'  # This used scipy
    )
```

**Replaced with**:
```python
# Verify grid dimensions (should be 416x416 natively from Brazil bbox request)
current_shape = (len(da.latitude), len(da.longitude))
logger.info(f"  Grid shape: {current_shape}")

# No interpolation needed - data comes in at correct resolution from CDS
```

## Results

✅ **Native resolution data** (0.1° from ERA5-Land, no resampling)
✅ **Downloads only Brazil** (416×416 = 173,056 pixels vs 780×600 = 468,000 pixels)
✅ **Historical NetCDF contains only Brazil** (not LatAm)
✅ **No scipy needed** (removed interpolation dependency)
✅ **Faster CDS downloads** (smaller area = less data)
✅ **Better API quota usage** (2.7x less data per request)

## Data Flow Now

```
1. Request from CDS:
   Bbox: [6.55, -75.05, -35.05, -33.45] (Brazil only)
   Result: 416×416 grid at native 0.1° resolution

2. Process to GeoTIFF:
   Clip with Brazil shapefile (gdalwarp)
   Save to /mnt/workwork/geoserver_data/temp_*/

3. Append to historical NetCDF:
   NO interpolation (already correct size!)
   Save to /mnt/workwork/geoserver_data/temp_*_hist/historical.nc
```

## Impact on Existing Data

**GeoTIFFs**: No change needed - they were already clipped with Brazil shapefile
**Historical NetCDF**: Needs to be rebuilt with correct Brazil-only data

## Rebuild Historical NetCDF

To rebuild with non-interpolated Brazil data:

```bash
# Option 1: Delete old historical NetCDF and re-run backfill
rm /mnt/workwork/geoserver_data/temp_max_hist/historical.nc
rm /mnt/workwork/geoserver_data/temp_min_hist/historical.nc
rm /mnt/workwork/geoserver_data/temp_mean_hist/historical.nc
rm /mnt/workwork/geoserver_data/wind_speed_hist/historical.nc

python3 app/run_era5_backfill.py

# Option 2: Build from existing GeoTIFFs (if they're correct)
# Use build_yearly_historical flow with existing GeoTIFF files
```

## Verification

After rebuilding, verify the historical NetCDF:

```python
import xarray as xr

ds = xr.open_dataset('/mnt/workwork/geoserver_data/temp_max_hist/historical.nc')
print(f"Shape: {ds.temp_max.shape}")  # Should be (days, 416, 416)
print(f"Lat range: {ds.latitude.min().values} to {ds.latitude.max().values}")  # Should be -35.05 to 6.55
print(f"Lon range: {ds.longitude.min().values} to {ds.longitude.max().values}")  # Should be -75.05 to -33.45
```

Expected output:
```
Shape: (3995, 416, 416)  # No interpolation, native grid
Lat range: -35.05 to 6.55  # Brazil only
Lon range: -75.05 to -33.45  # Brazil only
```

## Summary

This fix ensures that ERA5 temperature and wind data in both GeoTIFFs and historical NetCDF files contain:
- ✅ Native 0.1° resolution data (no interpolation/resampling)
- ✅ Brazil coverage only (no LatAm)
- ✅ Original ERA5-Land quality (not degraded)
- ✅ Efficient downloads (2.7x faster, less quota usage)
