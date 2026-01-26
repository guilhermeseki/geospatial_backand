# MERGE Data Automation - Zero-Miss Strategy

## Overview

This document describes the **multi-layer reliability system** for MERGE precipitation data updates, designed to ensure **zero missed dates** with multiple safety mechanisms.

## Architecture

### Layer 1: Daily Automated Updates (Primary)
- **Frequency**: Daily at 8:00 AM (via systemd timer)
- **Coverage**: Checks last 30 days for missing data
- **Logic**: Idempotent - safe to run multiple times
- **Features**:
  - Pre-check: Verifies recent data completeness
  - Downloads and processes missing files only
  - Post-check: Confirms all recent dates present
  - Comprehensive logging with monthly rotation

### Layer 2: Weekly Gap Detection (Safety Net)
- **Frequency**: Weekly on Sundays at 9:00 AM
- **Coverage**: Scans **entire historical period** (2000-present)
- **Purpose**: Catch any gaps that slipped through daily runs
- **Action**: Alerts if gaps found, provides backfill guidance

### Layer 3: Persistent Timers
- **Catch-up on boot**: If system was down during scheduled run
- **Persistent flag**: Runs missed timers immediately on system start
- **Randomized delay**: Avoids thundering herd (±15 min)

### Layer 4: 30-Day Lookback Window
- Built into the flow itself (`app/workflows/data_processing/flows.py:86`)
- Every run checks 30 days back, not just "new" data
- Catches gaps from temporary download failures

## Installation

### Quick Setup
```bash
cd /opt/geospatial_backend
./setup_merge_automation.sh
```

This will:
1. Make scripts executable
2. Install systemd service + timer files
3. Enable and start timers
4. Enable linger (so timers run when not logged in)

### Manual Setup
```bash
# 1. Copy systemd files
mkdir -p ~/.config/systemd/user/
cp systemd/merge-*.{service,timer} ~/.config/systemd/user/

# 2. Reload systemd
systemctl --user daemon-reload

# 3. Enable timers
systemctl --user enable merge-update.timer
systemctl --user enable merge-gap-check.timer

# 4. Start timers
systemctl --user start merge-update.timer
systemctl --user start merge-gap-check.timer

# 5. Enable linger (CRITICAL - allows timers to run when not logged in)
sudo loginctl enable-linger $USER
```

## Monitoring & Verification

### Check Timer Status
```bash
# List all timers
systemctl --user list-timers

# Check specific timer status
systemctl --user status merge-update.timer
systemctl --user status merge-gap-check.timer

# See next scheduled run
systemctl --user list-timers merge-update.timer
```

### View Logs
```bash
# Real-time systemd logs
journalctl --user -u merge-update -f

# Application logs (with rotation)
tail -f /opt/geospatial_backend/logs/merge_operational_$(date +%Y%m).log

# View logs for specific date
journalctl --user -u merge-update --since "2025-12-10" --until "2025-12-11"
```

### Manual Testing
```bash
# Test daily update (dry run)
python3 app/run_merge_operational.py

# Test gap detection
python3 app/check_merge_gaps.py

# Trigger timer manually (without waiting for schedule)
systemctl --user start merge-update.service
```

## Files Created

### Scripts
- `app/run_merge_operational.py` - Enhanced daily update script with logging
- `app/check_merge_gaps.py` - Full historical gap detection

### Systemd Units
- `systemd/merge-update.service` - Daily update service
- `systemd/merge-update.timer` - Daily schedule (8:00 AM)
- `systemd/merge-gap-check.service` - Weekly gap check service
- `systemd/merge-gap-check.timer` - Weekly schedule (Sunday 9:00 AM)

### Logs
- `/opt/geospatial_backend/logs/merge_operational_YYYYMM.log` - Monthly rotated logs

## Why This Won't Miss Dates

1. **Daily runs check 30 days back** - catches temporary failures
2. **Weekly full scan** - catches long-term gaps
3. **Persistent timers** - runs missed schedules after system downtime
4. **Idempotent processing** - safe to run multiple times
5. **Pre/post verification** - confirms data completeness
6. **Comprehensive logging** - easy to diagnose issues

## Troubleshooting

### Timer Not Running
```bash
# Check if timer is enabled
systemctl --user is-enabled merge-update.timer

# Check if linger is enabled (CRITICAL)
loginctl show-user $USER | grep Linger

# If Linger=no, enable it:
sudo loginctl enable-linger $USER
```

### Missing Dates Detected
```bash
# 1. Check logs for download failures
tail -100 /opt/geospatial_backend/logs/merge_operational_$(date +%Y%m).log

# 2. Verify INPE FTP is accessible
curl -I https://ftp.cptec.inpe.br/modelos/tempo/MERGE/GPM/DAILY/2025/12/

# 3. Manual backfill (will be created if needed)
python3 app/run_merge_backfill.py --start-date 2025-01-01 --end-date 2025-01-31
```

### Stop Automation
```bash
# Stop and disable timers
systemctl --user stop merge-update.timer
systemctl --user disable merge-update.timer

# Remove service files
rm ~/.config/systemd/user/merge-{update,gap-check}.{service,timer}
systemctl --user daemon-reload
```

## Adding Email Alerts (Optional)

To get email notifications on failures, add to service files:

```ini
[Service]
OnFailure=status-email@%n.service
```

Then configure `status-email@.service` with your email settings.

## Performance

- **Daily run time**: ~1-5 minutes (if no new data)
- **Daily run time**: ~10-30 minutes (if processing new data)
- **Weekly gap check**: ~5-10 seconds (scanning file existence)
- **Resource usage**: Max 8GB RAM, 400% CPU (4 cores)

## Integration with Historical NetCDF

After daily GeoTIFF updates, remember to:

1. **Append to historical NetCDF** (if not already automatic):
   ```bash
   python app/merge_historical.py
   ```

2. **Restart API** to reload new data:
   ```bash
   sudo systemctl restart fastapi
   # or
   pkill -f "uvicorn app.api.main:app" && \
   python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload &
   ```

## Summary

This system provides **five layers of protection** against missing dates:

1. ✅ **Daily automated runs** (8:00 AM)
2. ✅ **30-day lookback window** (built into flow)
3. ✅ **Weekly full verification** (Sunday 9:00 AM)
4. ✅ **Persistent catch-up** (runs missed schedules)
5. ✅ **Pre/post verification** (confirms completeness)

**Result**: Near-zero chance of missing dates in production.
