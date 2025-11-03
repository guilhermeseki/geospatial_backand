# GeoServer Styles for Wind Speed and NDVI MODIS

This document describes the custom styles created for the wind_speed and ndvi_modis layers.

## Styles Overview

### 1. Wind Speed Style (`wind_speed_style`)

**File**: `/opt/geospatial_backend/geoserver/styles/wind_speed_style.sld`

**Color Ramp**: White → Light Blue → Cyan → Yellow-Green → Yellow → Orange → Red → Dark Red

**Value Ranges**:
- 0 m/s (Calm): White (transparent)
- 0.5-3 m/s (Light breeze): Light Blue shades
- 4-6 m/s (Gentle to moderate breeze): Blue to Cyan
- 7-9 m/s (Fresh to strong breeze): Cyan to Yellow-Green
- 10-13 m/s (Strong breeze to gale): Yellow to Orange
- 15-20 m/s (Gale to storm): Orange to Red
- 25+ m/s (Violent storm): Red to Dark Red
- 40 m/s (Extreme): Very Dark Red

**Beaufort Scale Reference**: Colors map to standard wind speed classifications

**Legend URL**:
```
http://127.0.0.1:8080/geoserver/wind_ws/wms?service=WMS&version=1.1.1&request=GetLegendGraphic&layer=wind_speed&format=image/png
```

**Example WMS Request**:
```
http://127.0.0.1:8080/geoserver/wind_ws/wms?service=WMS&version=1.1.1&request=GetMap&layers=wind_speed&bbox=-75,-35,-33,6&width=800&height=600&srs=EPSG:4326&time=2025-10-15&format=image/png
```

---

### 2. NDVI MODIS Style (`ndvi_modis_style`)

**File**: `/opt/geospatial_backend/geoserver/styles/ndvi_modis_style.sld`

**Color Ramp**: Blue → Tan → Yellow → Light Green → Green → Dark Green

**Value Ranges**:
- -1.0 to -0.2 (Water/non-vegetation): Blue shades
- -0.1 to 0.1 (Bare soil/very sparse vegetation): Brown to Tan
- 0.2 to 0.4 (Low to healthy vegetation): Yellow to Light Green
- 0.5 to 0.7 (Dense vegetation/forest): Green shades
- 0.8 to 1.0 (Very dense forest): Dark Green

**NDVI Interpretation**:
- **Negative values**: Water bodies, clouds, snow
- **Near zero**: Bare rock, sand, urban areas
- **0.1-0.3**: Sparse vegetation, grasslands
- **0.3-0.6**: Moderate to healthy vegetation
- **0.6-0.8**: Dense vegetation, forests
- **0.8-1.0**: Very dense tropical forests

**Legend URL**:
```
http://127.0.0.1:8080/geoserver/ndvi_ws/wms?service=WMS&version=1.1.1&request=GetLegendGraphic&layer=ndvi_modis&format=image/png
```

**Example WMS Request** (use valid composite dates - every ~16 days):
```
http://127.0.0.1:8080/geoserver/ndvi_ws/wms?service=WMS&version=1.1.1&request=GetMap&layers=ndvi_modis&bbox=-75,-35,-33,6&width=800&height=600&srs=EPSG:4326&time=2025-06-10&format=image/png
```

---

## Managing Styles

### Viewing Styles in GeoServer Admin

1. Access GeoServer admin: `http://127.0.0.1:8080/geoserver/web`
2. Navigate to: **Data → Styles**
3. Filter by workspace: `wind_ws` or `ndvi_ws`
4. Click on style name to view/edit SLD

### Updating Styles via REST API

**Update wind_speed_style**:
```bash
curl -u admin:password -X PUT \
  -H "Content-Type: application/vnd.ogc.sld+xml" \
  --data-binary @wind_speed_style.sld \
  "http://127.0.0.1:8080/geoserver/rest/workspaces/wind_ws/styles/wind_speed_style"
```

**Update ndvi_modis_style**:
```bash
curl -u admin:password -X PUT \
  -H "Content-Type: application/vnd.ogc.sld+xml" \
  --data-binary @ndvi_modis_style.sld \
  "http://127.0.0.1:8080/geoserver/rest/workspaces/ndvi_ws/styles/ndvi_modis_style"
```

### Changing Layer Default Style

To change the default style for a layer:

```bash
curl -u admin:password -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "layer": {
      "defaultStyle": {
        "name": "your_style_name",
        "workspace": "your_workspace"
      }
    }
  }' \
  "http://127.0.0.1:8080/geoserver/rest/layers/workspace:layer_name"
```

---

## Style Files Location

- Wind Speed Style: `/opt/geospatial_backend/geoserver/styles/wind_speed_style.sld`
- NDVI MODIS Style: `/opt/geospatial_backend/geoserver/styles/ndvi_modis_style.sld`

## Testing Styles

Test images are saved to `/tmp/`:
- `/tmp/wind_speed_styled.png` - Wind speed with color ramp
- `/tmp/ndvi_modis_styled.png` - NDVI MODIS with color ramp
- `/tmp/wind_speed_legend.png` - Wind speed legend
- `/tmp/ndvi_modis_legend.png` - NDVI MODIS legend

---

## Notes

- **Wind Speed**: Uses continuous color ramp optimized for meteorological visualization
- **NDVI**: Uses vegetation-focused color ramp based on standard remote sensing practices
- **Transparency**: Wind speed has partial transparency for low values (0-1 m/s) to avoid cluttering calm areas
- **SLD Version**: Both styles use OGC SLD 1.0.0 standard

---

## Quick Links

- GeoServer Admin: http://127.0.0.1:8080/geoserver/web
- WMS Capabilities (Wind): http://127.0.0.1:8080/geoserver/wind_ws/wms?service=WMS&request=GetCapabilities
- WMS Capabilities (NDVI): http://127.0.0.1:8080/geoserver/ndvi_ws/wms?service=WMS&request=GetCapabilities
- Layer Preview: http://127.0.0.1:8080/geoserver/web/wicket/bookmarkable/org.geoserver.web.demo.MapPreviewPage
