# GLM FED Normalization - COMPLETED ✓

**Date:** 2026-01-14  
**Status:** Successfully completed

---

## What Was Done

### 1. ✅ Normalized All GeoTIFF Files
- **Files processed:** 252 GeoTIFF files
- **Time taken:** 23 seconds
- **Backup created:** All originals saved as `.bak` files
- **Conversion:** Raw flash counts → flashes/km²/30min
- **Verification:** All values correct and match expected ranges

### 2. ✅ Updated Processing Flow
- **Modified:** `app/workflows/data_processing/glm_fed_flow.py`
- **Change:** All future GeoTIFF files will be automatically normalized
- **Location:** Lines 699-722

### 3. ✅ Updated API Endpoints
- **History endpoint:** Keeps conversion (NetCDF still has raw values)
- **Featureinfo endpoint:** Removed conversion (GeoTIFF now normalized)
- **Consistency:** Both endpoints return identical values

---

## Results

### Test Location (lat=-15.8, lon=-47.9, date=2025-11-07)

| Source | Before | After | Unit |
|--------|--------|-------|------|
| GeoTIFF | 94 | 9.33 | flashes/km²/30min |
| NetCDF | 94 | 94* | raw (converted by API) |
| API /history | 9.33 | 9.33 | flashes/km²/30min |
| API /featureinfo | 9.33 | 9.33 | flashes/km²/30min |
| WMS visualization | Wrong colors | ✓ Correct colors | - |

*NetCDF still stores raw values; API converts on-the-fly

### Value Statistics (Nov 7, 2025)

```
Min:    0.10 flashes/km²/30min
Max:  100.40 flashes/km²/30min
Mean:   3.28 flashes/km²/30min
90%:    8.04 flashes/km²/30min

97.2% of values in 0-20 range (perfect for SLD)
```

---

## SLD Color Mapping (Now Correct)

| Range | Label | Color | Example Location |
|-------|-------|-------|------------------|
| 0 | No activity | Transparent | Most pixels |
| 1-3 | Very weak | Purple | Light activity |
| 3-5 | Weak | Dark purple | |
| 5-8 | Weak to moderate | Purple-blue | |
| 8-12 | Moderate | Blue | **Test location (9.33)** |
| 12-20 | Moderate to strong | Light blue | |
| 20-35 | Moderate to strong | Blue | |
| 35-50 | Strong | Cyan | |
| 50+ | Very strong to extreme | Green → Yellow → Red | |

---

## Verification Tests

### ✓ GeoTIFF Normalization
```bash
Test location value: 9.33 flashes/km²/30min
Expected value: 9.33 flashes/km²/30min
Result: PASS ✓
```

### ✓ API Consistency
```bash
/lightning/history: 9.33 flashes/km²/30min
/lightning/featureinfo: 9.33 flashes/km²/30min
Match: PASS ✓
```

### ✓ WMS Rendering
```bash
WMS query: Successful (2.4KB PNG)
Colors: Match SLD ranges
Result: PASS ✓
```

---

## File Locations

### Normalized Data
```
/mnt/workwork/geoserver_data/glm_fed/*.tif (252 files, normalized)
/mnt/workwork/geoserver_data/glm_fed/*.bak (252 backups, original raw)
```

### Code Changes
```
app/workflows/data_processing/glm_fed_flow.py (lines 699-722, 806)
app/api/routers/lightning.py (line 590-591)
```

### Documentation
```
/opt/geospatial_backend/GLM_NORMALIZATION_PLAN.md
/opt/geospatial_backend/GLM_NORMALIZATION_COMPLETE.md (this file)
```

---

## Future Processing

**Automatic normalization enabled:**
- All new GeoTIFF files will be normalized during creation
- No manual intervention required
- Daily updates will produce normalized files

**To process new data:**
```bash
python app/run_glm_fed.py --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

Files will automatically be normalized to flashes/km²/30min.

---

## Optional: Clean Up Backups

Once everything is verified working (after a few days):

```bash
# Remove backup files to save disk space
rm /mnt/workwork/geoserver_data/glm_fed/*.bak

# This will save: 217 MB
```

**Warning:** Only do this after confirming everything works perfectly!

---

## Summary

✅ **All 252 GeoTIFF files normalized**  
✅ **WMS colors now match API values**  
✅ **Future files will auto-normalize**  
✅ **API endpoints consistent**  
✅ **SLD style working correctly**

**Units:** All lightning data now in **flashes/km²/30min** ⚡

---

## Contact

For questions or issues:
- Check API docs: http://localhost:8000/docs
- Review this document: `/opt/geospatial_backend/GLM_NORMALIZATION_COMPLETE.md`
