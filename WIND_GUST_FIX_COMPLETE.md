# Wind Gust Data Fix - COMPLETE ✅

## Problem Summary

The existing wind data had TWO critical issues:

### Issue 1: Only 6-hourly snapshots (not daily maximum)
- Old data showed wind at ~18:00 UTC only
- Missing ~55% of peak wind speeds
- Example: Showed 3.60 m/s when actual daily max was 7.99 m/s

### Issue 2: Incorrect dataset (ERA5-Land has NO wind gust)
- ERA5-Land only has U/V wind components
- User needed **wind GUST** for insurance risk assessment
- Wind gust = short-duration maximum (3-second average)
- Gusts are typically 30-50% higher than sustained wind speed

## Solution Implemented

### ✅ Dataset: Full ERA5 (not ERA5-Land)
- **CDS Dataset**: `reanalysis-era5-single-levels`
- **Variable**: `instantaneous_10m_wind_gust` (short name: `i10fg`)
- **Coverage**: 1940-present, hourly data
- **Resolution**: ~0.25° (27.75 km at equator)

### ✅ Processing: Daily Maximum from 24 Hourly Values
1. Download all 24 hourly wind gust values per day
2. Compute daily maximum using `resample(valid_time='1D').max()`
3. Convert from m/s to km/h (multiply by 3.6)
4. Reproject to consistent 0.1° grid (416x416)
5. Clip to Brazil shapefile

### ✅ New Flow Created
- **File**: `app/workflows/data_processing/era5_wind_gust_flow.py`
- **Flow**: `era5_wind_gust_flow(start_date, end_date, skip_existing=True)`
- **Output**: Daily GeoTIFFs in `DATA_DIR/wind_speed/wind_speed_YYYYMMDD.tif`

## Verification Results

### Test Date: 2020-06-30 (Ciclone Bomba)

**Statistics**:
- Min: 10.40 km/h
- Mean: 34.77 km/h
- Median: 31.87 km/h
- Max: **119.06 km/h** ← Much more realistic than old >200 km/h errors
- 90th percentile: 52.21 km/h
- 95th percentile: 58.98 km/h
- 99th percentile: 80.72 km/h

**Porto Alegre (-30.0, -51.0)**:
- Wind gust: **61.94 km/h** (17.21 m/s)
- Appropriate for major storm event
- Only 1.06% of pixels exceeded 80 km/h (localized extreme event)

✅ **Values are realistic and suitable for insurance risk assessment**

## Next Steps

### 1. Rebuild Historical Data (2015-2024)
```bash
# This will take several hours (downloads ~24 files per day)
python rebuild_wind_gust_historical.py
```

The script processes year-by-year with automatic retry on failure.

### 2. Test Additional Dates
```bash
# Edit the date in test_era5_wind_gust.py
python test_era5_wind_gust.py
```

### 3. Daily Updates
For operational use, add to cron schedule:
```bash
# Download yesterday's wind gust data daily at 2 AM
0 2 * * * cd /opt/geospatial_backend && python -c "from datetime import date, timedelta; from app.workflows.data_processing.era5_wind_gust_flow import era5_wind_gust_flow; yesterday = date.today() - timedelta(days=1); era5_wind_gust_flow(yesterday, yesterday)"
```

### 4. Update API (if needed)
If you want to expose wind gust via API:
1. Add wind gust to `app/api/routers/wind.py`
2. Optionally build historical NetCDF for fast time-series queries
3. Restart API to load new datasets

## Technical Details

### Time Dimension Handling
ERA5 uses `valid_time` instead of `time`:
```python
time_dim = 'valid_time' if 'valid_time' in gust_data.dims else 'time'
daily_max = gust_data.resample({time_dim: '1D'}).max()
```

### Variable Name Detection
Flow automatically detects variable name:
```python
for possible_name in ['i10fg', '10fg', 'fg10', 'wind_gust', '10m_wind_gust', 'instantaneous_10m_wind_gust']:
    if possible_name in ds.data_vars:
        var_name = possible_name
        break
```

### Data Lag
ERA5 has ~5-7 day lag from current date. The flow will fail if requesting recent dates.

## References

- [ERA5 hourly data on single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download)
- [Metview wind gust example](https://metview.readthedocs.io/en/latest/examples/wind_gust_nc_era5_cds.html)
- [ERA5 Technical Documentation](https://docs.meteoblue.com/en/meteo/data-sources/era5)

## Files Created/Modified

### New Files
- `app/workflows/data_processing/era5_wind_gust_flow.py` - Main flow
- `test_era5_wind_gust.py` - Test script
- `rebuild_wind_gust_historical.py` - Rebuild all years
- `WIND_GUST_FIX_COMPLETE.md` - This document

### Failed Attempts (can be deleted)
- `app/workflows/data_processing/wind_gust_flow.py` - Tried ERA5-Land (no gust)
- `app/workflows/data_processing/wind_gust_daily_flow.py` - Tried agrometeorological (deprecated)
- `test_wind_gust_hourly.py` - ERA5-Land test (failed)
- `test_wind_gust_era5_daily.py` - Agro dataset test (failed)

## Summary

✅ **Problem**: Old wind data showed 6-hourly snapshots instead of daily max, and didn't have wind gust
✅ **Solution**: Download hourly wind gust from full ERA5, compute daily maximum
✅ **Result**: Realistic wind gust values (10-119 km/h) suitable for insurance risk assessment
✅ **Ready**: Flow tested and working, rebuild script created

**Status**: READY FOR PRODUCTION USE 🎉
