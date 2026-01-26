# GLM FED Lightning Data - NASA Earthdata Setup

## ✅ Credentials Configured

Your NASA Earthdata credentials are now properly configured and accessible:

- **Username**: `guilhermeseki@gmail.com`
- **Password**: `Vidaquesegue26!`
- **Storage**: `.env` file (secure)
- **Access**: Loaded via `app/config/settings.py`

## Your Production System vs. ChatGPT Example

### ChatGPT Example (Simplified)
The example you provided downloads a **single 30-minute file** for a specific hour:
```python
# Downloads ONE file like:
# GLM-L3-G19_Fed30_20250301_t1400.nc  (2pm on March 1, 2025)
```

### Your Production System (Advanced) ✨

Your system (`app/workflows/data_processing/glm_fed_flow.py`) is **much more sophisticated**:

1. **Downloads entire days** (1440+ minute-level files per day)
2. **Queries NASA CMR API** to find all available granules
3. **Handles midnight boundaries** (downloads 29 min from previous day)
4. **Calculates 30-minute fixed bins** (standard for research papers)
5. **Finds maximum FED** across all 30-min bins per day
6. **Dual storage**:
   - GeoTIFF files for GeoServer WMS visualization
   - Yearly NetCDF files for fast time-series queries
7. **Auto-selects satellite** based on date:
   - GOES-16 (G16) for dates before 2025
   - GOES-19 (G19) for 2025 onwards
   - GOES-18 (G18) also available

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ NASA GHRC DAAC                                              │
│ https://data.ghrc.earthdata.nasa.gov                        │
│                                                             │
│ GLM Gridded Flash Extent Density (FED)                      │
│ - Resolution: 8km × 8km                                     │
│ - Frequency: 1 minute files                                 │
│ - Coverage: Full GOES disk                                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ 1. Query CMR API for granules
                          │ 2. Download ~1440 minute files/day
                          │    (~3 GB compressed)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Download & Aggregate (download_glm_fed_daily)              │
│                                                             │
│ • Downloads day D-1 (23:31-23:59) + day D (00:00-23:59)    │
│ • Spatially subset to Brazil region (saves memory)         │
│ • Calculate 30-min fixed bins (00:00-00:30, 00:30-01:00..) │
│ • Find maximum FED per grid cell across all bins           │
│ • Output: glm_fed_daily_YYYYMMDD.nc (~1.5 MB)              │
└─────────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
┌──────────────────────┐  ┌──────────────────────────┐
│ GeoTIFF (GeoServer)  │  │ Yearly Historical NetCDF │
│                      │  │                          │
│ glm_fed/             │  │ glm_fed_hist/            │
│   glm_fed_20250101.tif│  │   glm_fed_2025.nc        │
│   glm_fed_20250102.tif│  │   glm_fed_2024.nc        │
│   ...                │  │   ...                    │
│                      │  │                          │
│ For: WMS images      │  │ For: Time-series queries │
└──────────────────────┘  └──────────────────────────┘
```

## Data Processing Details

### Fixed 30-Minute Bins (Research Standard)

Your system uses **fixed time bins**, not rolling windows:

```
Day 2025-03-01:
├── Bin 00:00-00:30  → Sum FED from all 1-min files in this period
├── Bin 00:30-01:00  → Sum FED from all 1-min files in this period
├── Bin 01:00-01:30  → ...
├── ...
└── Bin 23:30-00:00  → Last bin of the day

Result: Maximum FED across all 48 bins per grid cell
```

This is the **standard approach in lightning research papers** and provides:
- Consistent time windows across days
- No overlap between bins
- Easy comparison with other studies

### Output Variables

**Daily NetCDF** (`glm_fed_daily_YYYYMMDD.nc`):
- `flash_extent_density_30min_max`: Maximum FED in any 30-min bin (flashes/km²)
- `max_30min_timestamp`: Timestamp of the bin with maximum FED
- Dimensions: `[time=1, y, x]` (GOES projection or WGS84)

**Historical NetCDF** (`glm_fed_YYYY.nc`):
- `fed_30min_max`: Same as above, multiple days concatenated
- `fed_30min_time`: Timestamps of maximum bins
- Dimensions: `[time=365, latitude, longitude]` (WGS84, Brazil bbox)
- Chunking: `time=1, lat=20, lon=20` for fast queries

## Testing the Download

### Option 1: Simple Single-Day Test (Fast)

I created a simple test script for you:

```bash
python test_glm_download_simple.py
```

This will:
- Download 1 day of data (3 days ago)
- Process to 30-minute bins
- Save daily aggregate NetCDF
- Take ~10-20 minutes

### Option 2: Full Flow Test (Comprehensive)

Use the existing test script:

```bash
python app/run_glm_fed_test.py
```

This will:
- Download 3 days of data
- Process to GeoTIFF + historical NetCDF
- Take ~30-60 minutes

### Option 3: Production Flow

Full backfill for a date range:

```bash
# Process entire year
python -c "
from app.workflows.data_processing.glm_fed_flow import glm_fed_flow
from datetime import date
glm_fed_flow(
    start_date=date(2025, 1, 1),
    end_date=date(2025, 3, 1)
)
"
```

## Download Estimates

| Period | Files | Download Size | Processing Time | Final Storage |
|--------|-------|---------------|-----------------|---------------|
| 1 day  | ~1440 | ~3 GB         | 10-20 min       | ~1.5 MB       |
| 1 week | ~10,000 | ~21 GB      | 1-2 hours       | ~10 MB        |
| 1 month| ~43,000 | ~90 GB      | 5-10 hours      | ~45 MB        |
| 1 year | ~525,000 | ~1 TB      | 60-120 hours    | ~540 MB       |

## API Usage After Download

Once you have data downloaded, the API endpoints are:

### Point History
```bash
curl -X POST http://localhost:8000/lightning/history \
  -H "Content-Type: application/json" \
  -d '{
    "lat": -15.7801,
    "lon": -47.9292,
    "start_date": "2025-01-01",
    "end_date": "2025-03-01"
  }'
```

### Trigger Detection
```bash
curl -X POST http://localhost:8000/lightning/triggers \
  -H "Content-Type: application/json" \
  -d '{
    "lat": -15.7801,
    "lon": -47.9292,
    "start_date": "2025-01-01",
    "end_date": "2025-03-01",
    "trigger": 10.0,
    "trigger_type": "above"
  }'
```

### Area Triggers
```bash
curl -X POST http://localhost:8000/lightning/triggers/area \
  -H "Content-Type: application/json" \
  -d '{
    "lat": -15.7801,
    "lon": -47.9292,
    "radius": 50,
    "start_date": "2025-01-01",
    "end_date": "2025-03-01",
    "trigger": 5.0,
    "trigger_type": "above"
  }'
```

### WMS Image
```bash
curl "http://localhost:8000/lightning/wms?service=WMS&version=1.1.1&request=GetMap&layers=glm_ws:glm_fed&bbox=-75,-35,-33.5,6.5&width=800&height=600&srs=EPSG:4326&time=2025-03-01&format=image/png" --output lightning.png
```

## Key Files Modified

1. **`.env`** - Added Earthdata credentials
2. **`app/config/settings.py`** - Added credential fields
3. **`app/workflows/data_processing/glm_fed_flow.py`** - Updated to check Settings first

## Troubleshooting

### Issue: "No files successfully downloaded"
**Cause**: Data not available for this date yet (GLM has ~2-3 day lag)

**Solution**: Use older dates (3+ days ago)

### Issue: "Authentication failed"
**Cause**: Earthdata credentials incorrect

**Solution**: Verify credentials at https://urs.earthdata.nasa.gov/

### Issue: "Out of memory"
**Cause**: Processing too many files at once

**Solution**: Reduce `rolling_step_minutes` parameter (currently 10)

### Issue: "CMR API timeout"
**Cause**: Network issues or NASA server problems

**Solution**: Retry with `retries=3` in task decorator (already configured)

## Comparison with ChatGPT Example

| Feature | ChatGPT Example | Your System |
|---------|----------------|-------------|
| **Files per day** | 1 file (single 30-min window) | 1440+ files (all minutes) |
| **Coverage** | Single time slot | Full day maximum |
| **Processing** | Direct download → clip → save | CMR query → download → aggregate → dual storage |
| **Output** | Single GeoTIFF | GeoTIFF + yearly NetCDF |
| **Spatial subset** | Manual bbox clip | Auto Brazil bbox + reprojection |
| **Time handling** | Single timestamp | Midnight-crossing bins |
| **API integration** | None | Full REST API with queries |
| **GeoServer** | Not integrated | Time-enabled WMS layer |
| **Use case** | Quick test/demo | Production time-series analysis |

## Next Steps

1. **Test the download**:
   ```bash
   python test_glm_download_simple.py
   ```

2. **Check the output**:
   ```bash
   ls -lh /mnt/workwork/geoserver_data/raw/glm_fed/
   ```

3. **Process to GeoTIFF** (if test successful):
   ```bash
   python app/run_glm_fed_test.py
   ```

4. **View in GeoServer**:
   - Layer: `glm_ws:glm_fed`
   - Time-enabled: Yes
   - Style: `lightning_style`

5. **Query via API**:
   ```bash
   curl http://localhost:8000/lightning/history -X POST ...
   ```

## References

- NASA GHRC DAAC: https://ghrc.nsstc.nasa.gov/
- GLM Data Product: https://doi.org/10.5067/GLM/GRIDDED/DATA101
- GOES Satellites: https://www.goes-r.gov/
- CMR API: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html

---

**Ready to test!** Run `python test_glm_download_simple.py` to start downloading GLM FED data from NASA Earthdata.
