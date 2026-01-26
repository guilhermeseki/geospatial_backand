# Full Backfill - Started

## Status: RUNNING IN BACKGROUND

The full backfill process has been started and is running in the background. This will take several hours to complete.

## What's Happening

The backfill is processing datasets in this order:

1. **CHIRPS Precipitation** (2015-01-01 → yesterday)
   - ~316 missing files to download
   - Skipping 3,685 existing files

2. **MERGE Precipitation** (2014-11-01 → yesterday)
   - ~54 missing files to download
   - Skipping 4,008 existing files

3. **ERA5 Temperature & Wind** (2015-01-01 → 7 days ago)
   - Temperature: ~35 missing temp_max, ~21 temp_min, ~35 temp_mean
   - Wind: ~46 missing wind_speed files
   - Skipping 3,900+ existing files per dataset

4. **GLM Lightning** (April 15, 2025 → 2 days ago)
   - ~30 missing files to download
   - Skipping 213 existing files

## Monitoring Progress

### Real-time Monitoring

```bash
cd /opt/geospatial_backend
./monitor_backfill.sh
```

### Check Logs

```bash
# View latest backfill log
tail -f /opt/geospatial_backend/logs/backfill_*.log | tail -50

# Check for errors
grep -i "error\|failed" /opt/geospatial_backend/logs/backfill_*.log
```

### Check Process Status

```bash
# Check if backfill is still running
ps aux | grep run_full_backfill.sh

# Check dataset file counts
ls -1 /mnt/workwork/geoserver_data/chirps/*.tif | wc -l
ls -1 /mnt/workwork/geoserver_data/merge/*.tif | wc -l
ls -1 /mnt/workwork/geoserver_data/temp_max/*.tif | wc -l
ls -1 /mnt/workwork/geoserver_data/glm_fed/*.tif | wc -l
```

## Expected Duration

Based on dataset sizes:

| Dataset | Files to Download | Est. Time |
|---------|------------------|-----------|
| CHIRPS | ~316 | 2-3 hours |
| MERGE | ~54 | 30-45 min |
| ERA5 Temp | ~91 | 1-2 hours |
| ERA5 Wind | ~46 | 1 hour |
| GLM | ~30 | 1-2 hours |

**Total estimated time**: 5-8 hours

## What Happens During Backfill

For each missing file:
1. Downloads raw data from source
2. Clips to Brazil shapefile polygon
3. Saves as Cloud-Optimized GeoTIFF
4. Appends to historical NetCDF
5. Deletes raw file (cleanup)
6. Logs progress

At the end of each dataset:
7. Deletes shapefile index
8. GeoServer will rebuild on next WMS request

## After Backfill Completes

### 1. Verify Completeness

```bash
python3 /opt/geospatial_backend/verify_datasets.py
```

Expected output:
- All datasets should show 95%+ coverage
- Recent data (last 7 days) should be present

### 2. Test GeoServer

Make a WMS request to verify data is accessible:

```bash
curl -s "http://localhost:8080/geoserver/wms?service=WMS&version=1.1.1&request=GetMap&layers=precipitation_ws:chirps&bbox=-94,-53,-34,25&width=100&height=100&srs=EPSG:4326&time=2025-12-14&format=image/png" -o test.png

ls -lh test.png  # Should be a valid PNG file
```

### 3. Install Operational Cron Schedule

Once backfill is complete and verified:

```bash
cd /opt/geospatial_backend
./install_cron_schedule.sh
```

This will set up the 2:00 AM daily updates.

## Troubleshooting

### Backfill Stopped/Failed

Check the log for errors:
```bash
grep -i "error\|failed" /opt/geospatial_backend/logs/backfill_*.log | tail -20
```

Common issues:
- **Connection timeout**: CHIRPS/MERGE servers can be slow, Prefect will retry
- **CDS API error**: ERA5 may need credentials refresh
- **NASA Earthdata**: GLM requires valid credentials in .env

### Resume After Failure

Simply re-run the backfill - it will skip existing files:
```bash
./run_full_backfill.sh
```

### Individual Dataset Backfill

If only one dataset failed, run its specific backfill:
```bash
python3 app/run_chirps_backfill.py
python3 app/run_merge_backfill.py
python3 app/run_era5_backfill.py
python3 app/run_glm_backfill.py
```

## Files Created

### Backfill Scripts
- `app/run_chirps_backfill.py` - CHIRPS full backfill
- `app/run_merge_backfill.py` - MERGE full backfill
- `app/run_era5_backfill.py` - ERA5 temperature & wind backfill
- `app/run_glm_backfill.py` - GLM lightning backfill
- `run_full_backfill.sh` - Master script (runs all)

### Daily Update Scripts (for operational use)
- `app/run_chirps_daily.py` - Last 30 days only
- `app/run_merge_daily.py` - Last 30 days only
- `app/run_era5_daily.py` - Last 30 days (with 7-day lag)
- `app/run_glm_daily.py` - From April 2025 to yesterday
- `run_daily_updates_2am.sh` - Operational 2 AM cron job

### Verification & Monitoring
- `verify_datasets.py` - Check dataset completeness
- `monitor_backfill.sh` - Real-time progress monitoring

## Next Steps

1. **Wait for backfill to complete** (5-8 hours)
2. **Verify datasets** with `python3 verify_datasets.py`
3. **Test GeoServer** WMS requests
4. **Install cron schedule** with `./install_cron_schedule.sh`
5. **Monitor daily updates** at 2 AM

Your geospatial backend will then be fully operational with automatic daily updates!
