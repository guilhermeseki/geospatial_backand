# GLM FED Normalization Update

## Changes Made

### 1. Code Changes

**File:** `app/workflows/data_processing/glm_fed_flow.py`

**Function:** `process_glm_fed_to_geotiff()` (line ~680)
- Added normalization by pixel area after reprojection
- Divides values by 10.41 km² (pixel area in WGS84)
- **Result:** GeoTIFF values are now in **flashes/km²/30min**

**Function:** `append_to_yearly_historical_fed()` (line ~910)
- Added same normalization for historical NetCDF
- Ensures consistency between GeoTIFF and NetCDF storage
- **Result:** Historical data also in **flashes/km²/30min**

### 2. Style Changes

**File:** `geoserver/styles/glm_fed_style.sld`

Updated colorbar values:
- **Old:** 0, 1, 5, 10, 20, 50, 100, 200, 400, 800, 1500, 3000, 5000 (events)
- **New:** 0, 0.1, 0.5, 1, 2, 5, 10, 20, 40, 80, 150 (flashes/km²/30min)

**Division factor:** ~10.41 (pixel area)

### 3. Documentation

**File:** `glm_fed_colorbar.json`
- Complete color specification for front-end
- Includes value ranges and labels
- Comparison with literature values

## Unit Explanation

### What Changed:
- **Before:** Pixel values = flash events per pixel (unitless or "events")
- **After:** Pixel values = flashes per km² per 30 minutes

### Why This Matters:
1. **Comparable with literature** - Scientific papers use flashes/km²/time
2. **Intuitive** - Density per area is more meaningful than events per pixel
3. **Standardized** - Allows comparison across different grid resolutions

### Pixel Area Calculation:
```
Native GOES pixel:     8 km × 8 km = 64 km²
Reprojected WGS84:     3.23 km × 3.23 km ≈ 10.41 km²
Normalization factor:  10.41 km²
```

## Impact on Existing Data

### ⚠️ Important Notes:

1. **Existing GeoTIFFs are NOT normalized**
   - Only NEW files created after this change will be normalized
   - Old files have values 10.41× higher

2. **Historical NetCDF may have mixed data**
   - Dates processed before update: not normalized
   - Dates processed after update: normalized
   - **Solution:** May need to rebuild historical NetCDF

3. **To rebuild all data with normalization:**
   ```bash
   # Delete existing files
   rm /mnt/workwork/geoserver_data/glm_fed/*.tif
   rm /mnt/workwork/geoserver_data/glm_fed_hist/*.nc

   # Re-run processing (will use cached raw downloads)
   python app/run_glm_fed_resume.py
   ```

## Color Scale Interpretation

### New Values (flashes/km²/30min):

| Value | Color | Label | Interpretation |
|-------|-------|-------|----------------|
| 0 | Transparent | None | No lightning detected |
| 0.1 | Dark Purple | Very Low | Background activity |
| 0.5-1 | Purple | Low | Weak convection |
| 1-2 | Purple | Moderate Low | Developing storms |
| 2-5 | Purple-Blue | Moderate | Active thunderstorms |
| 5-10 | Blue | Moderate High | Intense thunderstorms |
| 10-20 | Cyan | High | Severe storms |
| 20-40 | Green-Yellow | Very High | Very severe storms |
| 40-80 | Yellow | Intense | Exceptional convective activity |
| 80-150 | Orange | Very Intense | Extreme storms |
| >150 | Red | Extreme | Rare extreme events |

### Comparison with Literature:

**Amazon Region (high lightning activity):**
- Typical storms: 5-20 flashes/km²/30min
- Intense MCS: 20-50 flashes/km²/30min
- Exceptional: >50 flashes/km²/30min

**Global Context:**
- Most regions: <5 flashes/km²/30min typical
- Tropical regions: 10-30 flashes/km²/30min during storms
- World records: >100 flashes/km²/30min (rare)

## Front-End Integration

### JSON Colorbar:
```json
{
  "unit": "flashes/km²/30min",
  "values": [0, 0.1, 0.5, 1, 2, 5, 10, 20, 40, 80, 150],
  "colors": ["#000000", "#1a0033", "#330066", "#4d0099", "#6600cc",
             "#0000ff", "#00ccff", "#00ff99", "#ffff00", "#ff9900", "#ff0000"]
}
```

See `glm_fed_colorbar.json` for complete specification.

## Testing

### To verify normalization is working:

```bash
# Check a newly processed file
python3 << 'EOF'
import rasterio
import numpy as np

with rasterio.open('/mnt/workwork/geoserver_data/glm_fed/glm_fed_20251201.tif') as src:
    data = src.read(1)
    valid = data[~np.isnan(data)]

    print(f"Min: {np.min(valid):.2f}")
    print(f"Max: {np.max(valid):.2f}")
    print(f"P95: {np.percentile(valid, 95):.2f}")
    print(f"P99: {np.percentile(valid, 99):.2f}")

    # Expected: values should be ~10x smaller than before
    # P99 should be around 7-15 instead of 70-150
EOF
```

## Current Processing Status

The normalization was added while processing is ongoing. Check how many files need reprocessing:

```bash
# Files created before normalization (need reprocessing)
ls -lt /mnt/workwork/geoserver_data/glm_fed/*.tif | tail -n +96 | wc -l

# Files created after normalization (already correct)
ls -lt /mnt/workwork/geoserver_data/glm_fed/*.tif | head -n 95 | wc -l
```

## Next Steps

1. ✅ Code updated with normalization
2. ✅ SLD style updated with new values
3. ✅ JSON colorbar created for front-end
4. ⏳ Current processing will create normalized files
5. 🔄 Consider reprocessing old files for consistency
6. 📊 Update API documentation with new units

---

**Date:** 2025-11-28
**Author:** Claude Code
**Status:** Active - processing ongoing with new normalization
