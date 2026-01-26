# Lightning API Endpoints Test Results

**Test Date:** 2026-01-14
**Test Location:** Brasília (-15.8, -47.9)
**Date Range Tested:** 2025-11-01 to 2025-11-30
**Data Availability:** 2025-04-01 to 2025-11-30 (242 days)

## Summary

| Endpoint | Status | Response Time | Notes |
|----------|--------|---------------|-------|
| POST /lightning/history | ✅ PASS | 0.47s | Returns 30 days of FED history |
| POST /lightning/triggers | ✅ PASS | 0.36s | Found 11 threshold exceedances |
| POST /lightning/triggers/area | ❌ FAIL | 0.02s | Error: Dataset loading issue |
| GET /lightning/wms (GetCapabilities) | ✅ PASS | 0.06s | Returns valid WMS capabilities |
| GET /lightning/wms (GetMap) | ✅ PASS | 0.06s | Returns 32KB PNG image |
| POST /lightning/polygon | ❌ FAIL | 0.00s | Error: Dataset loading issue |
| POST /lightning/featureinfo | ✅ PASS | 0.05s | Returns FED value = 3.0 |

**Overall:** 5/7 endpoints passing (71%)

---

## Detailed Test Results

### 1. POST /lightning/history ✅

**Purpose:** Returns historical lightning FED (Flash Extent Density) values for a point location

**Request:**
```json
{
  "lat": -15.8,
  "lon": -47.9,
  "start_date": "2025-11-01",
  "end_date": "2025-11-30"
}
```

**Response:**
```json
{
  "lat": -15.8,
  "lon": -47.9,
  "history": {
    "2025-11-01": 0.0,
    "2025-11-02": 6.0,
    "2025-11-03": 34.0,
    "2025-11-04": 0.0,
    "2025-11-05": 6.0,
    "2025-11-06": 6.0,
    "2025-11-07": 94.0,
    ...
  }
}
```

**Status:** ✅ PASS
**Response Time:** 0.47s
**Notes:** Successfully returned 30 days of FED data with values ranging from 0 to 94 flashes/km²/30min

---

### 2. POST /lightning/triggers ✅

**Purpose:** Returns dates when FED exceeded a threshold at a point location

**Request:**
```json
{
  "lat": -15.8,
  "lon": -47.9,
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "trigger": 5.0,
  "trigger_type": "above"
}
```

**Response:**
```json
{
  "location": {"lat": -15.8, "lon": -47.9},
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "trigger": 5.0,
  "trigger_type": "above",
  "n_exceedances": 11,
  "exceedances": [
    {"date": "2025-11-02", "value": 6.0},
    {"date": "2025-11-03", "value": 34.0},
    {"date": "2025-11-05", "value": 6.0},
    ...
  ]
}
```

**Status:** ✅ PASS
**Response Time:** 0.36s
**Notes:** Found 11 days where FED exceeded 5.0 flashes/km²/30min

---

### 3. POST /lightning/triggers/area ❌

**Purpose:** Returns FED threshold exceedances within a circular area

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
  "detail": "Error calculating lightning area trigger data"
}
```

**Status:** ❌ FAIL
**Response Time:** 0.02s
**Issue:** Dataset may not be fully loaded at worker level or coordinate system mismatch
**Notes:** This endpoint requires spatial slicing and haversine distance calculations which may be failing due to dataset initialization issues

---

### 4. GET /lightning/wms (GetCapabilities) ✅

**Purpose:** Returns WMS capabilities document for GeoServer lightning layer

**Request:**
```
GET /lightning/wms?service=WMS&version=1.1.1&request=GetCapabilities
```

**Status:** ✅ PASS
**Response Time:** 0.06s
**Content-Type:** application/vnd.ogc.wms_xml
**Response Size:** 224,580 bytes
**Notes:** Successfully returns WMS capabilities with glm_fed layer information

---

### 5. GET /lightning/wms (GetMap) ✅

**Purpose:** Returns rendered map image from GeoServer

**Request:**
```
GET /lightning/wms?service=WMS&version=1.1.1&request=GetMap
  &layers=glm_ws:glm_fed
  &bbox=-60,-30,-40,-10
  &width=400&height=400
  &srs=EPSG:4326
  &format=image/png
  &time=2025-11-30
```

**Status:** ✅ PASS
**Response Time:** 0.06s
**Content-Type:** image/png
**Response Size:** 32,265 bytes
**Notes:** Successfully returns PNG map image showing lightning density over Brazil

---

### 6. POST /lightning/polygon ❌

**Purpose:** Calculate statistics for FED within a polygon area

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
  "detail": "Error calculating polygon statistics"
}
```

**Status:** ❌ FAIL
**Response Time:** 0.00s
**Issue:** Dataset initialization or polygon processing error
**Notes:** Similar to area triggers, this may be related to dataset loading or coordinate handling

---

### 7. POST /lightning/featureinfo ✅

**Purpose:** Get FED value at a specific point and date from GeoTIFF mosaic

**Request:**
```json
{
  "source": "glm_fed",
  "lat": -15.8,
  "lon": -47.9,
  "date": "2025-11-30"
}
```

**Response:**
```json
{
  "lat": -15.8,
  "lon": -47.9,
  "date": "2025-11-30",
  "source": "glm_fed",
  "fed": 3.0
}
```

**Status:** ✅ PASS
**Response Time:** 0.05s
**Notes:** Successfully queries GeoServer GetFeatureInfo to extract pixel value

---

## Known Issues

### Issue 1: Area Triggers and Polygon Endpoints Failing

**Affected Endpoints:**
- POST /lightning/triggers/area
- POST /lightning/polygon

**Symptoms:**
- Both endpoints return 500 errors immediately
- Error message: "Error calculating lightning area trigger data" or "Error calculating polygon statistics"

**Probable Cause:**
The GLM FED dataset may not be properly loaded in all API workers, or there may be an issue with:
1. Dataset coordinate system handling (latitude uses decreasing coordinates)
2. Shared Dask client initialization in multi-worker setup
3. Spatial slicing with reversed latitude coordinates

**Investigation Needed:**
- Check API startup logs for dataset loading errors
- Verify all uvicorn workers successfully loaded the glm_fed dataset
- Test coordinate slicing directly with the dataset
- Review haversine distance calculation compatibility with xarray coordinates

---

## Dataset Information

**File:** `/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc`
**Size:** 7 GB
**Dimensions:**
- time: 242 dates (2025-04-01 to 2025-11-30)
- latitude: 2,712 points (35.02°S to 6.52°N, **decreasing**)
- longitude: 2,662 points (75.03°W to 33.49°W)

**Variable:**
- `fed_30min_max`: Maximum FED in any 30-minute window per day
- Unit: flashes/km²/30min
- Resolution: ~3.23 km × 3.23 km
- Pixel area: 10.41 km²

**Coordinate Notes:**
- Latitude coordinates are in **decreasing order** (north to south)
- This requires `slice(lat_max, lat_min)` instead of `slice(lat_min, lat_max)`

---

## Recommendations

1. **Investigate worker-level dataset loading:** Ensure all uvicorn workers successfully load the GLM FED dataset on startup

2. **Add better error logging:** Modify the area triggers and polygon endpoints to log the actual exception before returning a generic error

3. **Test coordinate handling:** The decreasing latitude coordinates may require special handling in spatial queries

4. **Consider dataset caching:** If dataset loading is slow, consider pre-loading in a shared memory space

5. **Add integration tests:** Create automated tests that run after API deployment to catch these issues earlier

---

## Test Files

- `test_lightning_endpoints.py` - Main comprehensive test script
- `test_lightning_debug.py` - Debug script for failing endpoints
- `test_lightning_direct.py` - Direct function call tests bypassing API

## How to Run Tests

```bash
# Run all lightning endpoint tests
python test_lightning_endpoints.py

# Run debug tests for failing endpoints
python test_lightning_debug.py
```
