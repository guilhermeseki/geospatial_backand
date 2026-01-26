# Lightning API Endpoints - Issues Fixed

**Date:** 2026-01-14
**Status:** ✅ ALL ENDPOINTS NOW PASSING (7/7 - 100%)

## Summary

All lightning API endpoints are now fully functional. Fixed 2 critical bugs that were causing 500 errors in area-based queries.

---

## Issues Found and Fixed

### Issue 1: Area Triggers - Incorrect Latitude Slicing ❌ → ✅

**File:** `app/api/routers/lightning.py:254-260`

**Problem:**
The code assumed GLM FED latitude coordinates were in decreasing order (north to south), but they are actually in **increasing order** (south to north: -35.02° to 6.52°). This caused an empty slice with 0 latitude points, resulting in all area-based calculations failing.

**Root Cause:**
```python
# BEFORE (WRONG)
ds_slice = historical_ds.sel(
    latitude=slice(lat_max, lat_min),  # Reversed - returns empty slice!
    longitude=slice(lon_min, lon_max),
    time=slice(start_date, end_date)
)
# Result: latitude dimension = 0 points
```

**Fix:**
```python
# AFTER (CORRECT)
ds_slice = historical_ds.sel(
    latitude=slice(lat_min, lat_max),  # Standard order for increasing coords
    longitude=slice(lon_min, lon_max),
    time=slice(start_date, end_date)
)
# Result: latitude dimension = 31 points (for 50km radius)
```

**Test Results:**
- ✅ Area triggers now successfully returns 22 dates with exceedances
- ✅ Correctly finds multiple points within 50km radius of test location
- ✅ Response time: 0.41s (acceptable for spatial queries)

---

### Issue 2: Polygon Endpoint - Wrong PolygonProcessor Usage ❌ → ✅

**File:** `app/api/routers/lightning.py:386-414`

**Problem:**
The code tried to instantiate `PolygonProcessor` as a class with arguments, but it's actually a **static utility class** with only static methods.

**Root Cause:**
```python
# BEFORE (WRONG)
processor = PolygonProcessor(historical_ds, 'fed_30min_max')
result = await asyncio.to_thread(
    processor.calculate_polygon_stats,
    request
)
# Error: TypeError: PolygonProcessor() takes no arguments
```

**Fix:**
Created a sync helper function that uses static methods correctly:

```python
# AFTER (CORRECT)
def _calculate_lightning_polygon_sync(ds: xr.Dataset, request: PolygonRequest):
    """Synchronous helper for lightning polygon processing."""
    polygon = PolygonProcessor.create_polygon_from_coords(request.coordinates)

    result = PolygonProcessor.process_polygon_request(
        ds=ds,
        polygon=polygon,
        variable_name="fed_30min_max",
        start_date=request.start_date,
        end_date=request.end_date,
        statistic=request.statistic,
        trigger=request.trigger,
        consecutive_days=request.consecutive_days
    )
    return result

# In endpoint:
result = await asyncio.to_thread(
    _calculate_lightning_polygon_sync,
    historical_ds,
    request
)
```

**Test Results:**
- ✅ Polygon endpoint now successfully calculates statistics
- ✅ Returns mean FED values for 30 days within polygon area
- ✅ Polygon area: 474.23 km²
- ✅ Response time: 0.50s

---

## Final Test Results (After Fixes)

| Endpoint | Status | Response Time | Notes |
|----------|--------|---------------|-------|
| POST /lightning/history | ✅ PASS | 0.46s | Returns 30 days of FED history |
| POST /lightning/triggers | ✅ PASS | 0.46s | Found 11 threshold exceedances |
| POST /lightning/triggers/area | ✅ PASS | 0.41s | **FIXED** - Found 22 dates with area triggers |
| GET /lightning/wms (GetCapabilities) | ✅ PASS | 0.06s | Returns valid WMS capabilities |
| GET /lightning/wms (GetMap) | ✅ PASS | 0.09s | Returns 32KB PNG image |
| POST /lightning/polygon | ✅ PASS | 0.50s | **FIXED** - Calculates mean statistics |
| POST /lightning/featureinfo | ✅ PASS | 0.04s | Returns FED value = 3.0 |

**Overall:** 7/7 endpoints passing (100%) ✅

---

## Detailed Test Output Examples

### Area Triggers (Now Working)

**Request:**
```json
{
  "lat": -15.8,
  "lon": -47.9,
  "radius": 50,
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "trigger": 3.0,
  "trigger_type": "above"
}
```

**Response:**
```json
{
  "center": {"lat": -15.8, "lon": -47.9},
  "radius_km": 50.0,
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "trigger": 3.0,
  "trigger_type": "above",
  "n_trigger_dates": 22,
  "exceedances_by_date": {
    "2025-11-01": [
      {"lat": -15.7925, "lon": -48.3237, "value": 10.0},
      {"lat": -15.7925, "lon": -48.2946, "value": 10.0},
      ...12 points total
    ],
    "2025-11-02": [...],
    ...22 dates total
  }
}
```

### Polygon (Now Working)

**Request:**
```json
{
  "coordinates": [
    [-48.0, -15.7],
    [-47.8, -15.7],
    [-47.8, -15.9],
    [-48.0, -15.9],
    [-48.0, -15.7]
  ],
  "source": "glm_fed",
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "statistic": "mean"
}
```

**Response:**
```json
{
  "metadata": {
    "polygon_area_km2": 474.23,
    "bounds": {
      "min_lon": -48.0,
      "min_lat": -15.9,
      "max_lon": -47.8,
      "max_lat": -15.7
    },
    "start_date": "2025-11-01",
    "end_date": "2025-11-30",
    "statistic": "mean"
  },
  "time_series": [
    {"date": "2025-11-01", "value": 0.0},
    {"date": "2025-11-02", "value": 4.37},
    {"date": "2025-11-03", "value": 46.33},
    ...30 dates total
  ]
}
```

---

## Code Changes Made

### File: `app/api/routers/lightning.py`

**Change 1 - Lines 254-260:**
```diff
- # GLM FED has decreasing latitude coordinates (north to south)
+ # GLM FED has increasing latitude coordinates (south to north)
  ds_slice = historical_ds.sel(
-     latitude=slice(lat_max, lat_min),  # Reversed for decreasing coords
+     latitude=slice(lat_min, lat_max),  # Standard order for increasing coords
      longitude=slice(lon_min, lon_max),
      time=slice(start_date, end_date)
  )
```

**Change 2 - Lines 386-439:**
```diff
+ def _calculate_lightning_polygon_sync(
+     ds: xr.Dataset,
+     request: PolygonRequest
+ ):
+     """Synchronous helper for lightning polygon processing."""
+     polygon = PolygonProcessor.create_polygon_from_coords(request.coordinates)
+     variable_name = "fed_30min_max"
+     result = PolygonProcessor.process_polygon_request(
+         ds=ds,
+         polygon=polygon,
+         variable_name=variable_name,
+         start_date=request.start_date,
+         end_date=request.end_date,
+         statistic=request.statistic,
+         trigger=request.trigger,
+         consecutive_days=request.consecutive_days
+     )
+     return result
+

  @router.post("/polygon")
  async def get_lightning_polygon(request: PolygonRequest):
      try:
-         processor = PolygonProcessor(historical_ds, 'fed_30min_max')
          result = await asyncio.to_thread(
-             processor.calculate_polygon_stats,
+             _calculate_lightning_polygon_sync,
+             historical_ds,
              request
          )
          return result
```

---

## Lessons Learned

1. **Always verify coordinate ordering:** Don't assume latitude is decreasing - check the actual data
2. **Check actual class design:** Static utility classes should be called via static methods, not instantiated
3. **Test spatial queries early:** Empty slices fail silently until you try to compute
4. **Follow existing patterns:** The precipitation router had the correct pattern for polygon processing

---

## Performance Notes

All endpoints perform well:
- Point queries: 0.04-0.46s
- Area queries (50km radius): 0.41s
- Polygon queries (474 km²): 0.50s
- WMS queries: 0.04-0.09s

The spatial queries (area/polygon) are computationally intensive but complete in under 1 second, which is acceptable for user-facing APIs.

---

## Testing

To verify all endpoints work:

```bash
# Run comprehensive test suite
python test_lightning_endpoints.py

# Expected output: All 7 endpoints passing ✅
```

---

## Data Availability

- **Dataset:** `/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc`
- **Date Range:** 2025-04-01 to 2025-11-30 (242 days)
- **Coverage:** Brazil and surrounding areas
- **Resolution:** ~3.23 km × 3.23 km
- **Variable:** `fed_30min_max` - Maximum FED in any 30-minute window per day
- **Unit:** flashes/km²/30min
- **Coordinates:**
  - Latitude: -35.02° to 6.52° (INCREASING, south to north)
  - Longitude: -75.03° to -33.49° (increasing, west to east)
