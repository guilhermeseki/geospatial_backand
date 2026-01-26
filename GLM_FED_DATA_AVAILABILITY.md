# GLM FED Data Availability Report

**Generated:** 2026-01-14
**Data Source:** GOES-16 GLM (Geostationary Lightning Mapper)

---

## Summary

| Metric | Value |
|--------|-------|
| **GeoTIFF Files** | 256 files |
| **NetCDF Dates** | 242 dates |
| **Date Range** | 2025-04-01 to 2025-12-14 |
| **Coverage** | 256 of 258 days (99.2%) |
| **Missing Dates** | 2 days (2025-04-05, 2025-04-06) |
| **Total Storage** | 217.3 MB (GeoTIFF) + 122 MB (NetCDF) |

---

## Detailed Breakdown

### GeoTIFF Files (for WMS/GeoServer)

**Location:** `/mnt/workwork/geoserver_data/glm_fed/`

**Coverage:**
- First date: **2025-04-01**
- Last date: **2025-12-14**
- Total files: **256 files**
- Date range span: **258 days**

**Files by Month:**
```
2025-04: 28 files (missing: 2025-04-05, 2025-04-06)
2025-05: 31 files (complete)
2025-06: 30 files (complete)
2025-07: 31 files (complete)
2025-08: 31 files (complete)
2025-09: 30 files (complete)
2025-10: 31 files (complete)
2025-11: 30 files (complete)
2025-12: 14 files (up to Dec 14)
```

**File Size Statistics:**
- Average: 869.1 KB
- Min: 196.0 KB
- Max: 1625.8 KB
- Total: 217.3 MB

---

### NetCDF Historical File (for API queries)

**Location:** `/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc`

**Coverage:**
- First date: **2025-04-01**
- Last date: **2025-11-30**
- Total dates: **242 dates**
- Date range span: **244 days**

**Dates by Month:**
```
2025-04: 28 dates
2025-05: 31 dates
2025-06: 30 dates
2025-07: 31 dates
2025-08: 31 dates
2025-09: 30 dates
2025-10: 31 dates
2025-11: 30 dates
```

**Dataset Details:**
- Variable: `fed_30min_max` (Maximum FED in any 30-minute window per day)
- Dimensions: 242 (time) × 2712 (lat) × 2662 (lon)
- Size: ~7 GB uncompressed
- Chunks: time=365, lat=20, lon=20

---

## Missing Dates

### Both GeoTIFF and NetCDF Missing:
1. **2025-04-05** (April 5)
2. **2025-04-06** (April 6)

These dates are missing from both the GeoTIFF files and the historical NetCDF, indicating the source data was never downloaded or processed.

### GeoTIFF Only (December 2025):
- **2025-12-01 to 2025-12-14**: GeoTIFF files exist (14 files)
- **NetCDF**: Does not include December 2025 data yet

**Note:** The NetCDF file (`glm_fed_2025.nc`) needs to be updated to include December dates.

---

## Data Gaps Impact

### API Endpoints Affected:

1. **`/lightning/history`**
   - ✅ Works for: 2025-04-01 to 2025-11-30 (excluding Apr 5-6)
   - ❌ No data: 2025-04-05, 2025-04-06, 2025-12-01 onwards

2. **`/lightning/triggers`**
   - Same as history endpoint

3. **`/lightning/triggers/area`**
   - Same as history endpoint

4. **`/lightning/polygon`**
   - Same as history endpoint

5. **`/lightning/featureinfo`**
   - ✅ Works for: 2025-04-01 to 2025-12-14 (excluding Apr 5-6)
   - Uses GeoTIFF files directly

6. **`/lightning/wms`**
   - ✅ Works for: 2025-04-01 to 2025-12-14 (excluding Apr 5-6)
   - Uses GeoTIFF files through GeoServer

---

## Recommendations

### 1. Fill Missing April Dates
Download and process data for 2025-04-05 and 2025-04-06:
```bash
# Run GLM FED backfill for missing dates
python app/run_glm_fed_backfill.py --start-date 2025-04-05 --end-date 2025-04-06
```

### 2. Update NetCDF with December Data
Add December 2025 dates to historical NetCDF:
```bash
# Process December dates into NetCDF
python app/run_glm_fed.py --start-date 2025-12-01 --end-date 2025-12-14
```

### 3. Set Up Daily Updates
Ensure automated daily processing is running to keep data current:
```bash
# Check if daily update service is running
systemctl status geospatial-daily-updates.timer

# Enable if not running
sudo systemctl enable --now geospatial-daily-updates.timer
```

---

## API Usage Notes

### For Frontend/Client Applications:

**Available Date Range:**
- **History/Triggers/Polygon:** `2025-04-01` to `2025-11-30`
- **FeatureInfo/WMS:** `2025-04-01` to `2025-12-14`

**Known Gaps:**
- `2025-04-05` and `2025-04-06` will return null/no data

**Request Example:**
```javascript
// Check if date is in available range before making request
const availableRange = {
  history: { start: '2025-04-01', end: '2025-11-30' },
  featureinfo: { start: '2025-04-01', end: '2025-12-14' }
};

const unavailableDates = ['2025-04-05', '2025-04-06'];

function isDateAvailable(date, endpoint) {
  if (unavailableDates.includes(date)) return false;
  const range = availableRange[endpoint];
  return date >= range.start && date <= range.end;
}
```

---

## Data Quality

### File Size Distribution:
The file sizes vary from 196 KB to 1.6 MB, which is normal:
- **Smaller files** (~200-500 KB): Days with low lightning activity
- **Larger files** (~1-1.6 MB): Days with high lightning activity
- **Average** (~869 KB): Typical activity level

### Consistency:
- ✅ Both GeoTIFF and NetCDF have the same missing dates
- ✅ All months (Apr-Nov) in NetCDF are complete except for the 2 missing days
- ✅ GeoTIFF files are being updated daily (December data present)

---

## Next Steps

1. **Immediate:** Update API documentation to reflect actual available dates
2. **Short-term:** Fill the 2 missing April dates
3. **Medium-term:** Update NetCDF with December data
4. **Ongoing:** Monitor daily update service for continuous data ingestion

---

## File Locations

```
# GeoTIFF files (for GeoServer/WMS)
/mnt/workwork/geoserver_data/glm_fed/glm_fed_YYYYMMDD.tif

# NetCDF historical file (for API queries)
/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc

# Data processing scripts
/opt/geospatial_backend/app/run_glm_fed.py
/opt/geospatial_backend/app/run_glm_fed_backfill.py
```

---

## Monitoring

To check data availability in real-time:

```bash
# Count GeoTIFF files
ls /mnt/workwork/geoserver_data/glm_fed/*.tif | wc -l

# Check latest GeoTIFF date
ls /mnt/workwork/geoserver_data/glm_fed/*.tif | tail -1

# Check NetCDF date range
python3 -c "import xarray as xr; ds=xr.open_dataset('/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc'); print(f'NetCDF: {ds.time.min().values} to {ds.time.max().values}')"
```
