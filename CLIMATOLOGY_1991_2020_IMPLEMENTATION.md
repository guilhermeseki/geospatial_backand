# Monthly Temperature Climatology 1991-2020 - Implementation Guide

## Overview
Implementation of monthly temperature max/min climatology using ERA5-Land data for Brazil (0.1° resolution).

## Current Status

### ✅ Completed
1. **Climatology calculation script created** (`app/calculate_temperature_climatology.py`)
2. **Temporary 2015-2020 climatology generated** (6-year baseline for testing)
3. **Historical backfill started** (downloading 1991-2014 data - **IN PROGRESS**)

### 🔄 In Progress
**ERA5 Historical Backfill (1991-2014)**
- Started: 2026-01-20
- Script: `app/run_era5_backfill_1991_2014.py`
- Variables: temp_max (daily_maximum) and temp_min (daily_minimum)
- Years: 24 years (1991-2014)
- Estimated time: Several hours (~10-15 minutes per year)
- Estimated download size: ~17 GB
- Status: Running in background (PID: 2122684)
- Log file: `logs/era5_backfill_1991_2014_YYYYMMDD_HHMMSS.log`

## Monitor Progress

```bash
# Quick monitoring script
/tmp/monitor_backfill.sh

# Or manually check log
tail -f logs/era5_backfill_1991_2014_*.log

# Check disk space
df -h / /mnt/workwork
```

## Files Created

### Scripts
1. **`app/calculate_temperature_climatology.py`**
   - Main climatology calculation script
   - Calculates monthly averages from daily data
   - Creates GeoTIFFs + NetCDF output

2. **`app/run_era5_backfill_1991_2014.py`**
   - Downloads ERA5-Land data for 1991-2014
   - Processes year-by-year to avoid timeouts
   - Automatically skips already downloaded dates

3. **`/tmp/monitor_backfill.sh`**
   - Progress monitoring script
   - Shows download status and disk usage

### Data Files Created

#### Current (2015-2020 Climatology)
```
/mnt/workwork/geoserver_data/temp_max_climatology/
├── temp_max_clim_month01.tif  (January)
├── temp_max_clim_month02.tif  (February)
├── ...
├── temp_max_clim_month12.tif  (December)
└── temp_max_climatology_monthly.nc  (3.8 MB)

/mnt/workwork/geoserver_data/temp_min_climatology/
├── temp_min_clim_month01.tif  (January)
├── ...
├── temp_min_clim_month12.tif  (December)
└── temp_min_climatology_monthly.nc  (3.9 MB)
```

#### Historical Data (Being Downloaded)
```
/mnt/workwork/geoserver_data/temp_max_hist/
├── temp_max_2015.nc  (existing)
├── ...
├── temp_max_2020.nc  (existing)
├── temp_max_1991.nc  ← downloading
├── ...
└── temp_max_2014.nc  ← will download

/mnt/workwork/geoserver_data/temp_min_hist/
├── temp_min_2015.nc  (existing)
├── ...
├── temp_min_2020.nc  (existing)
├── temp_min_1991.nc  ← downloading
├── ...
└── temp_min_2014.nc  ← will download
```

## After Backfill Completes

### Step 1: Verify Data
```bash
# Check that all years are present
ls -lh /mnt/workwork/geoserver_data/temp_max_hist/temp_max_*.nc | wc -l  # Should be 30
ls -lh /mnt/workwork/geoserver_data/temp_min_hist/temp_min_*.nc | wc -l  # Should be 30
```

### Step 2: Recalculate Climatology (1991-2020)
```bash
# This will overwrite the 2015-2020 climatology with the full 30-year climatology
python app/calculate_temperature_climatology.py --all --start-year 1991 --end-year 2020
```

This command will:
- Load all 30 years of daily data (1991-2020)
- Calculate monthly averages for each of 12 months
- Create new GeoTIFF files (one per month)
- Create consolidated NetCDF files
- Takes ~2-3 minutes to process

### Step 3: Verify Output
```bash
# Check the new climatology files
ls -lh /mnt/workwork/geoserver_data/temp_max_climatology/
ls -lh /mnt/workwork/geoserver_data/temp_min_climatology/

# View NetCDF metadata
ncdump -h /mnt/workwork/geoserver_data/temp_max_climatology/temp_max_climatology_monthly.nc
```

## Data Specifications

### Spatial Coverage
- **Region**: Brazil with buffer
- **Bounding Box**: -75.0°W to -33.5°W, -35.0°S to 6.5°N
- **Resolution**: 0.1° × 0.1° (~10 km)
- **Grid Size**: 416 × 416 pixels
- **CRS**: EPSG:4326 (WGS84)

### Temporal Coverage
- **Reference Period**: 1991-2020 (30 years - WMO standard)
- **Temporal Resolution**: Monthly climatology (12 months)
- **Source**: ERA5-Land daily statistics

### Variables
- **temp_max**: Daily maximum temperature at 2m
- **temp_min**: Daily minimum temperature at 2m
- **Units**: °C (Celsius)

### File Formats
1. **GeoTIFF** (12 files per variable)
   - One file per month (month01-month12)
   - Compressed (DEFLATE)
   - Tiled for efficient access
   - ~400 KB per file

2. **NetCDF** (1 file per variable)
   - Consolidated monthly climatology
   - Chunked for efficient queries (month=1, lat=100, lon=100)
   - Compressed (zlib level 5)
   - ~4 MB per file

## Usage Examples

### Python (xarray)
```python
import xarray as xr

# Load climatology
ds_max = xr.open_dataset('/mnt/workwork/geoserver_data/temp_max_climatology/temp_max_climatology_monthly.nc')
ds_min = xr.open_dataset('/mnt/workwork/geoserver_data/temp_min_climatology/temp_min_climatology_monthly.nc')

# Get January climatology
jan_max = ds_max['temp_max'].sel(month=1)
jan_min = ds_min['temp_min'].sel(month=1)

# Get climatology for specific location (e.g., São Paulo: -23.5°S, -46.6°W)
location_clim = ds_max['temp_max'].sel(
    longitude=-46.6,
    latitude=-23.5,
    method='nearest'
)
print(f"São Paulo monthly temperature max climatology:")
for month in range(1, 13):
    temp = float(location_clim.sel(month=month).values)
    print(f"  Month {month:02d}: {temp:.1f}°C")
```

### QGIS/GIS Applications
1. Add raster layer: `/mnt/workwork/geoserver_data/temp_max_climatology/temp_max_clim_month01.tif`
2. Style with temperature color ramp
3. Repeat for each month to create animation

### GeoServer (Optional)
```bash
# Create ImageMosaic store from monthly GeoTIFFs
# Can serve via WMS for web applications
```

## Technical Details

### Processing Flow
1. **Load yearly NetCDF files** (temp_max_1991.nc through temp_max_2020.nc)
2. **Concatenate along time dimension** (creates single 30-year timeseries)
3. **Group by month** (groups all January days, all February days, etc.)
4. **Calculate mean** (averages all values for each month across 30 years)
5. **Save outputs** (12 monthly GeoTIFFs + 1 consolidated NetCDF)

### Statistics (Expected for 1991-2020)
Based on preliminary 2015-2020 data, the full climatology should show:
- **Warmest months**: October-November (28-29°C mean max)
- **Coolest months**: June-July (25°C mean max, 17°C mean min)
- **Seasonal variation**: ~4°C amplitude
- **Spatial variation**: -15°C to +37°C (includes high elevation areas)

### Quality Assurance
- Uses official ERA5-Land daily statistics (pre-computed by ECMWF)
- 30-year period follows WMO climatological standard practice
- Spatial clipping to Brazil ensures relevant coverage
- NetCDF includes full metadata (source, period, method)

## Troubleshooting

### If backfill fails
```bash
# Check the log
tail -100 logs/era5_backfill_1991_2014_*.log

# Resume - the script automatically skips existing data
nohup python app/run_era5_backfill_1991_2014.py >> logs/era5_backfill_resume.log 2>&1 &
```

### If disk space runs out
```bash
# Check space
df -h / /mnt/workwork

# Clean up raw files (safe after yearly NetCDF is created)
rm -rf /mnt/workwork/geoserver_data/raw/era5_land_daily/*

# Clean home directory cache
rm -rf ~/.cache/*
```

### If Prefect fails
```bash
# Clean Prefect database
rm -rf ~/.prefect/prefect.db*

# Restart the download
python app/run_era5_backfill_1991_2014.py
```

## Next Steps After Completion

1. **Integrate into API** (optional)
   - Add climatology endpoints to FastAPI
   - Enable queries like "What is normal temperature for this location/month?"
   - Compare current values to climatology for anomaly detection

2. **Add to GeoServer** (optional)
   - Create ImageMosaic stores
   - Style for visualization
   - Enable WMS access

3. **Use for Analysis**
   - Calculate temperature anomalies (actual - climatology)
   - Identify unusual temperature events
   - Provide baseline for climate comparisons

## Storage Requirements

### Current (2015-2020)
- Climatology GeoTIFFs: ~10 MB (temp_max + temp_min)
- Climatology NetCDF: ~8 MB
- Source data: ~2 GB (6 years × 2 variables)

### After 1991-2020 Backfill
- Additional historical NetCDF: ~17 GB (24 years × 2 variables × ~350 MB/year)
- Final climatology: Same size (~10 MB GeoTIFFs + 8 MB NetCDF)
- Total: ~19 GB

## Contact / Support

### Monitor Commands
```bash
# Check progress
/tmp/monitor_backfill.sh

# View live log
tail -f logs/era5_backfill_1991_2014_*.log

# Check process
ps aux | grep run_era5_backfill
```

### Estimated Completion
- Start time: Check log file timestamp
- Duration: ~6-8 hours (24 years × 15 min/year average)
- **Expected completion**: Check after a few hours

---

## Summary

✅ **Climatology calculation infrastructure complete**
✅ **Test climatology generated (2015-2020)**
🔄 **Historical backfill in progress (1991-2014)**
⏳ **Final 1991-2020 climatology**: Run after backfill completes

All scripts are ready. Just wait for the download to finish, then run the final climatology calculation!
