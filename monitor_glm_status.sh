#!/bin/bash
# Quick GLM processing status monitor

echo "=========================================="
echo "GLM FED Processing Status"
echo "=========================================="
echo ""

# Check if process is running
if ps aux | grep -q "[p]ython /opt/geospatial_backend/app/run_glm_fed_resume.py"; then
    echo "✓ Processing is RUNNING"
    PID=$(ps aux | grep "[p]ython /opt/geospatial_backend/app/run_glm_fed_resume.py" | awk '{print $2}')
    RUNTIME=$(ps -p $PID -o etime= | tr -d ' ')
    echo "  PID: $PID"
    echo "  Runtime: $RUNTIME"
else
    echo "✗ Processing is NOT running"
fi
echo ""

# Count completed files
TOTAL_FILES=$(ls /mnt/workwork/geoserver_data/glm_fed/*.tif 2>/dev/null | wc -l)
echo "Completed dates: $TOTAL_FILES"

# Show latest file
LATEST=$(ls -t /mnt/workwork/geoserver_data/glm_fed/*.tif 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    LATEST_DATE=$(echo "$LATEST" | grep -oP '\d{8}' | head -1)
    LATEST_TIME=$(stat -c %y "$LATEST" | cut -d' ' -f1-2 | cut -d'.' -f1)
    echo "Latest file: $LATEST_DATE (created: $LATEST_TIME)"
fi
echo ""

# Show auto-restart status
echo "Auto-restart monitor:"
tail -3 /opt/geospatial_backend/logs/glm_autorestart.log
echo ""

# Show current activity from processing log
echo "Recent activity:"
tail -5 /opt/geospatial_backend/logs/glm_fed_backfill_resume.log | grep -E "(Processing date|Downloaded|Finished|ERROR)" | tail -3
echo ""

echo "=========================================="
echo "To monitor continuously: watch -n 10 /opt/geospatial_backend/monitor_glm_status.sh"
echo "To view full log: tail -f /opt/geospatial_backend/logs/glm_fed_backfill_resume.log"
echo "=========================================="
