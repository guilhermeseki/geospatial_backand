# GLM FED Normalization Plan

## Current Status

The SLD style is already updated for normalized values (flashes/km²/30min).

**What needs to be done:**
1. Normalize existing GeoTIFF files (252 files)
2. Future GeoTIFF files will be normalized automatically

**What stays as-is:**
- NetCDF historical file (raw values, API converts on-the-fly)
- API endpoints (already have conversion logic)

## Step 1: Normalize Existing GeoTIFF Files

```bash
# Run the normalization script
cd /opt/geospatial_backend
python3 /tmp/normalize_glm_geotiffs.py
```

**What it does:**
- Backs up original files as `.bak`
- Converts each pixel: `normalized = raw_value / pixel_area_km²`
- Pixel area varies with latitude (7-10 km² depending on location)
- Processes all 252 files with progress bar

**Time estimate:** ~5-10 minutes

## Step 2: Verify Normalization

Test a sample file:

```bash
python3 << 'VERIFY'
import rasterio
import numpy as np

# Check normalized file
with rasterio.open('/mnt/workwork/geoserver_data/glm_fed/glm_fed_20251107.tif') as src:
    data = src.read(1)
    valid_data = data[data > 0]
    print(f"Normalized file stats:")
    print(f"  Min: {valid_data.min():.2f} flashes/km²/30min")
    print(f"  Max: {valid_data.max():.2f} flashes/km²/30min")
    print(f"  Mean: {valid_data.mean():.2f} flashes/km²/30min")
    print(f"  Expected range: 0-200 flashes/km²/30min")
VERIFY
```

## Step 3: Test WMS with New Values

```bash
# Query WMS for Nov 7 (high activity day)
curl -s "http://localhost:8080/geoserver/wms?service=WMS&version=1.1.1&request=GetMap&layers=glm_ws:glm_fed&bbox=-48.0,-16.0,-47.8,-15.6&width=400&height=400&srs=EPSG:4326&time=2025-11-07&format=image/png" --output /tmp/test_glm_wms.png

echo "Saved test image to /tmp/test_glm_wms.png"
```

Check that colors now match the SLD ranges (e.g., purple for 1-5, blue for 5-20, etc.)

## Step 4: Clean Up After Verification

Once verified, optionally remove backup files:

```bash
# Remove .bak files (only after confirming everything works!)
rm /mnt/workwork/geoserver_data/glm_fed/*.bak
```

## Future Data Processing

**Automated:** The GLM flow has been updated to normalize new GeoTIFF files automatically:
- `app/workflows/data_processing/glm_fed_flow.py` (lines 699-722)
- All new files will be created with normalized values
- No manual intervention needed

## API Behavior After Normalization

**GeoTIFF queries** (featureinfo):
- Will now return normalized values directly
- Should remove conversion code from `/lightning/featureinfo` endpoint

**NetCDF queries** (history, triggers, polygon):
- Keep existing conversion code (NetCDF still has raw values)
- Or rebuild NetCDF from normalized GeoTIFFs (optional)

## Summary

**Before normalization:**
- GeoTIFF: 94 flashes (raw)
- API: 9.33 flashes/km²/30min (converted)
- WMS: Purple color (wrong - based on raw value 94)

**After normalization:**
- GeoTIFF: 9.33 flashes/km²/30min (normalized)
- API: 9.33 flashes/km²/30min (same)
- WMS: Blue color (correct - based on normalized value 9.33)

**Consistency achieved:** ✓ WMS colors now match API values
