# Daily Data Updates Schedule - 2:00 AM

## Overview

All datasets (except NDVI) are scheduled to update automatically at **2:00 AM** every day. This low-demand time ensures minimal impact on production API users.

## Datasets Included

| Dataset | Source | Update Frequency |
|---------|--------|------------------|
| CHIRPS | Precipitation | Daily at 2:00 AM |
| MERGE | Precipitation | Daily at 2:00 AM |
| ERA5 Temperature | temp_max, temp_min, temp_mean | Daily at 2:00 AM |
| ERA5 Wind | wind_speed | Daily at 2:00 AM |
| GLM Lightning | glm_fed | Daily at 2:00 AM |
| **NDVI** | **NOT included** | Schedule separately |

## Installation

### Quick Install

```bash
cd /opt/geospatial_backend
./install_cron_schedule.sh
```

### Manual Install

```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * * /opt/geospatial_backend/run_daily_updates_2am.sh >> /opt/geospatial_backend/logs/daily_updates.log 2>&1
```

## What Happens During Update

For each dataset, the update process:

1. **Downloads** new data from source (CHIRPS, MERGE, ERA5 CDS API, GLM from NASA Earthdata)
2. **Clips to Brazil polygon** using `/opt/geospatial_backend/data/shapefiles/br_shp/brazil_b10km.shp`
3. **Processes** to GeoTIFF format (Cloud-Optimized GeoTIFF with LZW compression)
4. **Appends** to historical NetCDF files (time-series data for API queries)
5. **Refreshes** GeoServer mosaic index (deletes shapefile)
6. **Triggers warm-up WMS request** to rebuild index immediately at 2 AM
7. **Logs** results

### GeoServer Index Refresh

- Shapefile is **deleted** (takes 1 second)
- **Warm-up WMS request** triggers immediate rebuild (30-60 seconds during update)
- GeoServer indexes are **ready before users arrive**
- **No GeoServer restart** needed
- All subsequent requests are instant

## Timing Considerations

### Why 2:00 AM?

- ✅ Low API traffic
- ✅ Users won't notice 60-second rebuild delay
- ✅ Completes before business hours
- ✅ ERA5 has 7-day lag, so no rush needed

### Total Duration

| Dataset | Download | Process + Clip | Historical NetCDF | Index Rebuild |
|---------|----------|----------------|-------------------|---------------|
| CHIRPS | ~2 min | ~1 min | ~30 sec | 60 sec (warm-up) |
| MERGE | ~2 min | ~1 min | ~30 sec | 60 sec (warm-up) |
| ERA5 Temp | ~5 min | ~2 min | ~1 min | 45 sec (warm-up) |
| ERA5 Wind | ~5 min | ~2 min | ~1 min | 45 sec (warm-up) |
| GLM | ~3 min | ~1 min | ~30 sec | 30 sec (warm-up) |

**Total:** ~35-45 minutes for all updates (including warm-up)
**Index rebuild happens during update** - users don't wait!

## Monitoring

### View Logs

```bash
# Live monitoring
tail -f /opt/geospatial_backend/logs/daily_updates.log

# Check today's logs
grep "$(date +%Y%m%d)" /opt/geospatial_backend/logs/daily_updates.log

# Check for errors
grep "✗ Failed" /opt/geospatial_backend/logs/daily_updates.log
```

### Check Last Run

```bash
# Check if cron job ran today
grep "DAILY DATA UPDATES" /opt/geospatial_backend/logs/daily_updates.log | tail -1

# Check completion status
grep "DAILY UPDATES COMPLETED" /opt/geospatial_backend/logs/daily_updates.log | tail -1
```

### Verify Data Updated

```bash
# Check latest GeoTIFF files
ls -lt /mnt/workwork/geoserver_data/chirps/*.tif | head -5
ls -lt /mnt/workwork/geoserver_data/merge/*.tif | head -5
ls -lt /mnt/workwork/geoserver_data/temp_mean/*.tif | head -5
```

## Testing

### Test Run (Manual)

```bash
# Run all updates manually
/opt/geospatial_backend/run_daily_updates_2am.sh

# Run single dataset
python3 /opt/geospatial_backend/app/run_chirps.py
python3 /opt/geospatial_backend/app/run_merge.py
```

### Verify Cron Schedule

```bash
# List cron jobs
crontab -l

# Check cron is running
systemctl status cron
```

## NDVI Scheduling (Separate)

NDVI is **not included** in the 2 AM daily updates. Schedule it separately if needed:

```bash
# Add to crontab for NDVI updates on Mondays and Thursdays at 4 AM
0 4 * * 1,4 python3 /opt/geospatial_backend/app/run_ndvi.py >> /opt/geospatial_backend/logs/ndvi_updates.log 2>&1
```

## Troubleshooting

### Updates Not Running

```bash
# Check cron service
systemctl status cron

# Check crontab entry
crontab -l | grep "run_daily_updates_2am"

# Check script permissions
ls -l /opt/geospatial_backend/run_daily_updates_2am.sh
```

### GeoServer Not Rebuilding Index

```bash
# Manually refresh a dataset
python3 /opt/geospatial_backend/update_mosaic_index.py chirps

# Check GeoServer status
systemctl status geoserver

# Check GeoServer logs
tail -f /opt/geoserver/logs/geoserver.log
```

### Download Failures

- **ERA5:** Check CDS API credentials in `.env`
- **CHIRPS:** Check UCSB server availability
- **MERGE:** Check CPTEC/INPE server availability

## Uninstall

```bash
# Remove cron entry
crontab -e
# Delete the line with 'run_daily_updates_2am.sh'

# Or remove via command
crontab -l | grep -v "run_daily_updates_2am.sh" | crontab -
```

## Files Created

```
/opt/geospatial_backend/
├── run_daily_updates_2am.sh           # Main update script
├── install_cron_schedule.sh           # Cron installation script
├── cron_schedule.txt                  # Cron configuration reference
├── update_mosaic_index.py             # Manual index update tool
└── logs/
    └── daily_updates.log              # Update logs
```

## Support

For issues or questions, check:
1. Logs: `/opt/geospatial_backend/logs/daily_updates.log`
2. GeoServer logs: `/opt/geoserver/logs/geoserver.log`
3. Prefect logs (if using Prefect server)
