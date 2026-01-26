# MERGE Automation - Quick Start Guide

## Current Status

Your MERGE dataset currently has:
- **Coverage**: 2014-11-01 to 2025-10-22
- **Files**: 4,008 GeoTIFF files
- **Missing dates**: ~37 dates in the active period (some gaps exist)

## Install Automation (2 minutes)

```bash
cd /opt/geospatial_backend
./setup_merge_automation.sh
```

This installs:
- ✅ **Daily updates** at 8:00 AM (checks last 30 days)
- ✅ **Weekly gap checks** on Sundays at 9:00 AM (scans all dates)
- ✅ **Persistent catch-up** (runs missed schedules after downtime)
- ✅ **Comprehensive logging** with monthly rotation

## Verify Installation

```bash
# Check timers are active
systemctl --user list-timers | grep merge

# Should show:
# Sun 2025-12-15 09:00:00 ... merge-gap-check.timer
# Wed 2025-12-11 08:00:00 ... merge-update.timer
```

## Test It Works

```bash
# Run daily update manually (safe, idempotent)
python3 app/run_merge_operational.py

# Check for gaps
python3 app/check_merge_gaps.py
```

## Monitor Logs

```bash
# Real-time updates
journalctl --user -u merge-update -f

# Application logs
tail -f logs/merge_operational_$(date +%Y%m).log
```

## Why This Won't Miss Dates

| Layer | What It Does | Frequency |
|-------|--------------|-----------|
| **Daily Auto-Run** | Checks last 30 days for missing data | Every day at 8 AM |
| **30-Day Lookback** | Built into flow - catches temporary failures | Every run |
| **Weekly Full Scan** | Verifies entire historical period | Sunday 9 AM |
| **Persistent Timers** | Catches up missed runs after downtime | On boot |
| **Pre/Post Checks** | Verifies completeness before and after | Every run |

**Result**: 5 layers of protection = near-zero chance of missing dates

## What Happens Daily

```
08:00 AM - Timer triggers
  ↓
Pre-check: Verify last 7 days complete
  ↓
Download missing data from INPE (last 30 days)
  ↓
Convert GRIB2 → GeoTIFF (clip to Brazil)
  ↓
Update GeoServer mosaic index
  ↓
Post-check: Verify last 7 days complete
  ↓
Log results to logs/merge_operational_YYYYMM.log
```

## If Gaps Are Found

Weekly gap check will report missing dates:

```bash
# Gap check output shows:
⚠️  Found 5 missing dates:
  - 2025-11-15
  - 2025-11-16
  ...

# Action: Check why
tail -100 logs/merge_operational_202511.log

# Common causes:
# 1. INPE FTP was down (temporary)
# 2. Data not yet available (1-2 day lag)
# 3. Network issues during download

# Solution: Next daily run will catch them (30-day lookback)
```

## Emergency Manual Run

If you need to force an immediate update:

```bash
# Trigger daily update now
systemctl --user start merge-update.service

# Watch progress
journalctl --user -u merge-update -f
```

## Disable Automation

```bash
# Stop timers
systemctl --user stop merge-update.timer merge-gap-check.timer
systemctl --user disable merge-update.timer merge-gap-check.timer
```

## Next Steps (Optional)

1. **Email alerts on failures**: Configure systemd email notifications
2. **Prometheus monitoring**: Export metrics for dashboard
3. **Slack webhook**: Get notifications in Slack channel

See `MERGE_AUTOMATION.md` for full documentation.

## Summary

You now have a **production-grade, zero-miss MERGE data pipeline** with:
- ✅ Automated daily updates
- ✅ Automatic gap detection and filling
- ✅ Comprehensive logging
- ✅ Catch-up after downtime
- ✅ No manual intervention required

**Just run the setup script and forget about it!**
