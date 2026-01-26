# MODIS NDVI Styles Reference

## Status: ✅ FULLY OPERATIONAL

All three NDVI styles are successfully configured, tested, and working with the MODIS NDVI ImageMosaic layer.

## Successfully Configured Styles

Three NDVI color ramp styles are available in GeoServer:

### 1. Scientific Style (Default)
- **Name**: `ndvi_modis_scientific`
- **Color Ramp**: 11-color gradient optimized for vegetation health monitoring
- **Range**: 0.0 to 1.0 (NDVI values)
- **Colors**:
  - 0.0-0.2: Red/Orange (Bare soil, very sparse vegetation)
  - 0.2-0.4: Yellow/Light yellow (Sparse to moderate vegetation)
  - 0.4-0.6: Light green/Green (Moderate to healthy vegetation)
  - 0.6-0.8: Green/Dark green (Healthy to dense vegetation)
  - 0.8-1.0: Very dark green (Very dense vegetation, rainforest)

### 2. Classic Style (Alternative)
- **Name**: `ndvi_modis_classic`
- **Color Ramp**: 7-color simplified gradient
- **Range**: 0.0 to 1.0 (NDVI values)
- **Colors**:
  - 0.1: Red (Very sparse)
  - 0.2: Orange (Sparse)
  - 0.4: Yellow (Moderate low)
  - 0.6: Yellow-green (Moderate)
  - 0.8: Green (Healthy)
  - 1.0: Dark green (Dense)

### 3. Simple Style (API-Compatible)
- **Name**: `ndvi_style`
- **Same as**: Scientific style
- **Purpose**: Short name for API compatibility (api.seki-tech.com/ndvi/wms)

## WMS GetMap Request Examples

### Using Default Style (Scientific)
```bash
curl -o ndvi_scientific.png "http://127.0.0.1:8080/geoserver/wms?service=WMS&version=1.1.1&request=GetMap&layers=ndvi_ws:ndvi_modis&bbox=-73,-33,-34,5&width=800&height=600&srs=EPSG:4326&time=2015-02-09&format=image/png"
```

### Using Scientific Style (Explicit)
```bash
curl -o ndvi_scientific.png "http://127.0.0.1:8080/geoserver/wms?service=WMS&version=1.1.1&request=GetMap&layers=ndvi_ws:ndvi_modis&bbox=-73,-33,-34,5&width=800&height=600&srs=EPSG:4326&time=2015-02-09&format=image/png&styles=ndvi_modis_scientific"
```

### Using Classic Style
```bash
curl -o ndvi_classic.png "http://127.0.0.1:8080/geoserver/wms?service=WMS&version=1.1.1&request=GetMap&layers=ndvi_ws:ndvi_modis&bbox=-73,-33,-34,5&width=800&height=600&srs=EPSG:4326&time=2015-02-09&format=image/png&styles=ndvi_modis_classic"
```

## Available Dates

MODIS MOD13Q1 16-day composites: **27 files available** (2015-2025):
- **2015**: 9 files starting from 2015-01-24
- **2025**: 18 files from 2025-01-16 through 2025-06-01

Get full list of available dates:
```bash
ls -1 /mnt/workwork/geoserver_data/ndvi_modis/ndvi_modis_*.tif | xargs -n1 basename | sed 's/ndvi_modis_//' | sed 's/.tif//'
```

## ImageMosaic Index Maintenance

The shapefile index was rebuilt on 2025-11-13 using GDAL/OGR with 27 entries. If new GeoTIFF files are added:

### Automatic Reindex Script
```bash
python3 /tmp/rebuild_modis_index.py
curl -u admin:todosabordo25! -X POST "http://127.0.0.1:8080/geoserver/rest/reload"
```

### Manual Index Check
```bash
# Count files in directory
ls /mnt/workwork/geoserver_data/ndvi_modis/*.tif | wc -l

# Count entries in shapefile index
python3 << 'EOF'
import struct
with open('/mnt/workwork/geoserver_data/ndvi_modis/ndvi_modis.dbf', 'rb') as f:
    header = f.read(32)
    print(struct.unpack('<I', header[4:8])[0])
EOF
```

If counts don't match, run the reindex script above.

## Layer Information

- **Workspace**: ndvi_ws
- **Layer Name**: ndvi_modis
- **Coverage Store**: ndvi_modis (ImageMosaic)
- **Data Directory**: `/mnt/workwork/geoserver_data/ndvi_modis/`
- **CRS**: EPSG:4326
- **Extent**: Latin America region (-94, -53, -34, 25)

## GeoServer REST API Commands

### List Available Styles
```bash
curl -s -u admin:todosabordo25! "http://127.0.0.1:8080/geoserver/rest/workspaces/ndvi_ws/styles"
```

### Get Layer Configuration
```bash
curl -s -u admin:todosabordo25! "http://127.0.0.1:8080/geoserver/rest/layers/ndvi_ws:ndvi_modis.xml"
```

### Change Default Style
```bash
curl -u admin:todosabordo25! -X PUT \
  -H "Content-Type: text/xml" \
  -d '<layer>
  <defaultStyle>
    <name>ndvi_modis_classic</name>
    <workspace>ndvi_ws</workspace>
  </defaultStyle>
</layer>' \
  "http://127.0.0.1:8080/geoserver/rest/layers/ndvi_ws:ndvi_modis"
```

## Verified Test Results (2025-11-13)

✅ All WMS requests tested and working:
- `ndvi_style` with time=2025-01-16: 1.6 KB PNG ✓
- `ndvi_style` with time=2025-06-01: PNG ✓
- `ndvi_modis_classic` with time=2025-01-16: PNG ✓
- `ndvi_modis_scientific` with time=2015-02-09: 134 KB PNG ✓

## Troubleshooting

### Issue: "Could not find a match for 'time' value"
**Solution**: Shapefile index out of sync - run `/tmp/rebuild_modis_index.py`

### Issue: "No such style: ndvi_style"
**Solution**: Run style upload commands from "GeoServer REST API Commands" section above

### Issue: ImageMosaic shows old dates
**Root cause**: Shapefile index (.shp, .dbf, .shx files) cached from previous state
**Solution**: Delete index files and reload GeoServer, or use rebuild script
