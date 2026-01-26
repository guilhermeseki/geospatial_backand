# GLM FED Processing - Crash Analysis & Fix

## Issue Summary

**Problem:** GLM FED processing has been stopping/crashing over multiple days, only completing 94 out of 221 target dates.

**Timeline:**
- Started: Nov 25, 2025 at 09:06
- Last activity: Nov 25, 2025 at 16:39 (stopped ~42 hours ago)
- Currently: No process running

## Root Cause Analysis

### 1. Primary Issue: Permission Errors on Historical NetCDF
```
ERROR: [Errno 13] Permission denied: '/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc'
```
- The historical NetCDF append function was failing due to file permission/lock issues
- When this failed, the **entire date processing failed** and flow stopped
- File appears to have correct permissions now, but may have been locked during concurrent access

### 2. Process Termination
- Process stopped mid-download (800/1471 files for Aug 16)
- No evidence of:
  - OOM (Out of Memory) killer
  - Disk space issues (2.3TB free)
  - Memory exhaustion (43GB available)
- Likely causes:
  - User Ctrl+C / manual termination
  - System restart
  - Session timeout
  - External kill signal

### 3. Performance Not as Expected
- Initial calculation showed 427 dates/hour (WRONG)
- **Actual rate: ~12.4 dates/hour**
- Why the discrepancy:
  - Cached dates process in ~8 seconds
  - BUT dates needing NASA download take ~7 minutes
  - Many dates are being downloaded fresh from NASA

## Current Progress

**Coverage:**
- April: 2 days (missing 13)
- May: 16 days (missing first 15)
- June: 30 days ✓
- July: 31 days ✓
- August: 15 days (missing 16-31)
- Sept-Nov: 0 days (completely missing)

**Total:** 94/221 dates completed (43%)

## Solution Implemented

### Code Changes

**File:** `app/workflows/data_processing/glm_fed_flow.py`

**Change 1:** Wrap historical NetCDF append in try-except
```python
# Before (line 1134):
hist_file = append_to_yearly_historical_fed(daily_nc, target_date)

# After:
try:
    hist_file = append_to_yearly_historical_fed(daily_nc, target_date)
    if hist_file:
        logger.info(f"  ✓ Historical NetCDF updated")
except Exception as e:
    logger.warning(f"  ⚠ Failed to append to historical NetCDF (continuing anyway): {e}")
    # Continue processing - GeoTIFF is the critical output
```

**Change 2:** Add progress counter
```python
# Show "Processing date 45/221" instead of just "Processing date"
for idx, target_date in enumerate(missing_download, 1):
    logger.info(f"Processing date {idx}/{total_dates}: {target_date}")
```

### New Resume Script

**File:** `app/run_glm_fed_resume.py`
- Resumes from where it left off (checks for existing files)
- Appends to existing log file
- Better error messages
- Continues even if historical NetCDF append fails

## How to Resume Processing

### Option 1: Run Resume Script
```bash
cd /opt/geospatial_backend
python app/run_glm_fed_resume.py
```

### Option 2: Run in Background (Recommended)
```bash
cd /opt/geospatial_backend
nohup python app/run_glm_fed_resume.py > logs/glm_resume_nohup.log 2>&1 &

# Monitor progress:
tail -f logs/glm_fed_backfill_resume.log
```

### Option 3: Use screen/tmux for Long-Running Process
```bash
# Start screen session
screen -S glm_processing

# Run the script
python app/run_glm_fed_resume.py

# Detach: Ctrl+A, then D
# Reattach: screen -r glm_processing
```

## Expected Timeline

**Remaining work:** 127 dates

**Time estimate:**
- At 12.4 dates/hour: ~10.2 hours
- With potential downloads: ~12-15 hours
- **Expected completion:** ~12-15 hours from start

## Monitoring Commands

```bash
# Check if process is running
ps aux | grep run_glm_fed_resume

# Watch log file
tail -f logs/glm_fed_backfill_resume.log

# Count completed files
ls /mnt/workwork/geoserver_data/glm_fed/glm_fed_*.tif | wc -l

# Check latest file
ls -lh /mnt/workwork/geoserver_data/glm_fed/glm_fed_*.tif | tail -1

# Check coverage gaps
python3 -c "
import os, re
from datetime import datetime, timedelta
files = [f for f in os.listdir('/mnt/workwork/geoserver_data/glm_fed/') if f.endswith('.tif')]
dates = sorted([datetime.strptime(re.search(r'(\d{8})', f).group(1), '%Y%m%d') for f in files])
print(f'Total: {len(dates)} files')
print(f'Range: {dates[0].strftime(\"%Y-%m-%d\")} to {dates[-1].strftime(\"%Y-%m-%d\")}')
"
```

## Key Improvements

1. **Resilience:** Won't stop if historical NetCDF fails (GeoTIFF is priority)
2. **Visibility:** Progress counter shows remaining work
3. **Resumable:** Can be stopped/started without losing progress
4. **Logging:** Appends to existing log for complete history

## Notes

- GeoTIFF files are the critical output (used by GeoServer for WMS)
- Historical NetCDF is for API queries (can be rebuilt later if needed)
- The flow automatically skips dates that already have GeoTIFF files
- Safe to run multiple times - it's idempotent
