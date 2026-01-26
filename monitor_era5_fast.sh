#!/bin/bash
# Monitor ERA5 2013-2014 FAST backfill progress

LOG_FILE="logs/era5_complete_2013_2014_fast.log"

echo "======================================"
echo "ERA5 2013-2014 FAST BACKFILL MONITOR"
echo "======================================"
echo ""

# Check if process is running
if pgrep -f "run_era5_complete_2013_2014_fast.py" > /dev/null; then
    echo "✓ Process is RUNNING"
else
    echo "✗ Process is NOT RUNNING"
fi
echo ""

# Count completed batches
completed_batches=$(grep "✓ Completed batch:" "$LOG_FILE" 2>/dev/null | wc -l)
echo "Progress: $completed_batches batches completed"
echo ""

# Check file counts
temp_max_2013=$(ls /mnt/workwork/geoserver_data/temp_max/temp_max_2013*.tif 2>/dev/null | wc -l)
temp_min_2013=$(ls /mnt/workwork/geoserver_data/temp_min/temp_min_2013*.tif 2>/dev/null | wc -l)
temp_max_2014=$(ls /mnt/workwork/geoserver_data/temp_max/temp_max_2014*.tif 2>/dev/null | wc -l)
temp_min_2014=$(ls /mnt/workwork/geoserver_data/temp_min/temp_min_2014*.tif 2>/dev/null | wc -l)

echo "GeoTIFF Files:"
echo "  2013 temp_max: $temp_max_2013 / 365 ($(( temp_max_2013 * 100 / 365 ))%)"
echo "  2013 temp_min: $temp_min_2013 / 365 ($(( temp_min_2013 * 100 / 365 ))%)"
echo "  2014 temp_max: $temp_max_2014 / 365"
echo "  2014 temp_min: $temp_min_2014 / 365"
echo ""

# Current activity
echo "Current Activity:"
tail -3 "$LOG_FILE" 2>/dev/null | sed 's/^/  /'
echo ""

echo "======================================"
echo "Run: bash monitor_era5_fast.sh"
echo "======================================"
