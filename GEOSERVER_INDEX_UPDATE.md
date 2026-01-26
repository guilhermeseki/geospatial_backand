# GeoServer ImageMosaic Index Update - Production Guide

## Problem
GeoServer ImageMosaic does NOT automatically detect new GeoTIFF files added to the directory. The shapefile index must be updated manually.

## Solution for Production

### Option 1: Delete Shapefile (Recommended - Fast & Reliable)

When new files are added, simply delete the shapefile components. GeoServer will automatically rebuild the index on the next WMS request.

**Advantages:**
- ✅ No GeoServer restart needed
- ✅ Fast (2-5 seconds to rebuild)
- ✅ Always works
- ✅ Safe for production

**Script:**
```bash
python /opt/geospatial_backend/update_mosaic_index.py <dataset>
```

**Example:**
```bash
# After adding new CHIRPS files
python /opt/geospatial_backend/update_mosaic_index.py chirps
```

**What it does:**
1. Deletes `.shp`, `.dbf`, `.shx`, `.prj`, `.cpg`, `.fix`, `.qix` files
2. Deletes `<dataset>.properties` file
3. Keeps `indexer.properties` and `timeregex.properties`
4. GeoServer rebuilds index automatically on next WMS/WCS request

### Option 2: Integrated in Prefect Flows (Already Implemented)

Your data processing flows already call `refresh_mosaic_shapefile()` after processing new data:

**Files:**
- `app/workflows/data_processing/flows.py` - Line 68 (CHIRPS), Line 113 (MERGE)
- `app/workflows/data_processing/tasks.py` - Line 285 (`refresh_mosaic_shapefile` function)

**When it runs:**
- Automatically after `chirps_daily_flow()`
- Automatically after `merge_daily_flow()`
- Automatically after ERA5, NDVI flows

### Performance

| Dataset | Files | Rebuild Time |
|---------|-------|--------------|
| CHIRPS  | 3,685 | ~60 seconds |
| MERGE   | 4,008 | ~60 seconds |
| temp_*  | 3,500 | ~45 seconds |
| glm_fed | 2,000 | ~30 seconds |

**Note:** Rebuild time is only on the FIRST request after deletion. Subsequent requests are instant.

### Production Workflow

```
Daily Flow:
1. Prefect flow downloads new data
2. Processes to GeoTIFF
3. Appends to historical NetCDF
4. Calls refresh_mosaic_shapefile()  ← Deletes shapefile
5. Next WMS request auto-rebuilds index
```

### Manual Update

If you manually add files outside of Prefect:

```bash
# 1. Add your new GeoTIFF file
cp new_data.tif /mnt/workwork/geoserver_data/chirps/chirps_20251115.tif

# 2. Update the index
python /opt/geospatial_backend/update_mosaic_index.py chirps

# 3. Done! Next WMS request will include the new file
```

### Why NOT GeoServer REST API?

GeoServer's REST API for ImageMosaic harvesting is:
- ❌ Complex and version-dependent
- ❌ Often not enabled by default
- ❌ Requires special configuration
- ❌ Less reliable than delete-and-rebuild

The delete-and-rebuild approach is simpler and more reliable for production.

### Monitoring

Check if index needs updating:
```bash
# Count GeoTIFF files
ls /mnt/workwork/geoserver_data/chirps/*.tif | wc -l

# Count shapefile records
python3 -c "
import shapefile
sf = shapefile.Reader('/mnt/workwork/geoserver_data/chirps/chirps.shp', encoding='latin1')
print(f'Shapefile records: {len(sf)}')
"
```

If counts don't match, run `update_mosaic_index.py`.
