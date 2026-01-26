#!/bin/bash
# Monitor ERA5 2013-2014 backfill progress

LOG_FILE="logs/era5_complete_2013_2014.log"

echo "=================================="
echo "ERA5 2013-2014 BACKFILL MONITOR"
echo "=================================="
echo ""

# Check if process is running
if pgrep -f "run_era5_complete_2013_2014.py" > /dev/null; then
    echo "✓ Process is RUNNING"
else
    echo "✗ Process is NOT RUNNING"
fi
echo ""

# Show current year/variable being processed
echo "Current Processing:"
tail -100 "$LOG_FILE" | grep -E "Processing Year:|Processing: 2m_temperature" | tail -2
echo ""

# Count completed batches
echo "Progress Summary:"
completed_batches=$(grep "✓ Completed batch:" "$LOG_FILE" | wc -l)
echo "  Completed batches: $completed_batches"
echo ""

# Check file counts
echo "File Counts:"
temp_max_2013=$(ls /mnt/workwork/geoserver_data/temp_max/temp_max_2013*.tif 2>/dev/null | wc -l)
temp_min_2013=$(ls /mnt/workwork/geoserver_data/temp_min/temp_min_2013*.tif 2>/dev/null | wc -l)
temp_max_2014=$(ls /mnt/workwork/geoserver_data/temp_max/temp_max_2014*.tif 2>/dev/null | wc -l)
temp_min_2014=$(ls /mnt/workwork/geoserver_data/temp_min/temp_min_2014*.tif 2>/dev/null | wc -l)

echo "  2013 temp_max: $temp_max_2013 / 365 files"
echo "  2013 temp_min: $temp_min_2013 / 365 files"
echo "  2014 temp_max: $temp_max_2014 / 365 files"
echo "  2014 temp_min: $temp_min_2014 / 365 files"
echo ""

# Check for yearly NetCDF files
echo "Yearly NetCDF files:"
if [ -f /mnt/workwork/geoserver_data/temp_max_hist/temp_max_2013.nc ]; then
    size_2013_max=$(du -h /mnt/workwork/geoserver_data/temp_max_hist/temp_max_2013.nc | cut -f1)
    echo "  ✓ temp_max_2013.nc ($size_2013_max)"
else
    echo "  ✗ temp_max_2013.nc (not created yet)"
fi

if [ -f /mnt/workwork/geoserver_data/temp_min_hist/temp_min_2013.nc ]; then
    size_2013_min=$(du -h /mnt/workwork/geoserver_data/temp_min_hist/temp_min_2013.nc | cut -f1)
    echo "  ✓ temp_min_2013.nc ($size_2013_min)"
else
    echo "  ✗ temp_min_2013.nc (not created yet)"
fi

if [ -f /mnt/workwork/geoserver_data/temp_max_hist/temp_max_2014.nc ]; then
    size_2014_max=$(du -h /mnt/workwork/geoserver_data/temp_max_hist/temp_max_2014.nc | cut -f1)
    echo "  ✓ temp_max_2014.nc ($size_2014_max)"
else
    echo "  ✗ temp_max_2014.nc (not created yet)"
fi

if [ -f /mnt/workwork/geoserver_data/temp_min_hist/temp_min_2014.nc ]; then
    size_2014_min=$(du -h /mnt/workwork/geoserver_data/temp_min_hist/temp_min_2014.nc | cut -f1)
    echo "  ✓ temp_min_2014.nc ($size_2014_min)"
else
    echo "  ✗ temp_min_2014.nc (not created yet)"
fi
echo ""

# Show recent log activity
echo "Recent Activity (last 10 lines):"
tail -10 "$LOG_FILE" | sed 's/^/  /'
echo ""

# Check for errors
error_count=$(grep -i "error\|failed\|exception" "$LOG_FILE" | wc -l)
if [ $error_count -gt 0 ]; then
    echo "⚠️  Found $error_count potential errors/warnings in log"
    echo "Recent errors:"
    grep -i "error\|failed\|exception" "$LOG_FILE" | tail -5 | sed 's/^/  /'
else
    echo "✓ No errors detected"
fi
echo ""

echo "=================================="
echo "Run this script again to check progress:"
echo "  bash monitor_era5_2013_2014.sh"
echo "=================================="
