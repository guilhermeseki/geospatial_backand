#!/bin/bash
# Monitor GLM FED processing progress

echo "================================================================================"
echo "GLM FED PROCESSING MONITOR"
echo "================================================================================"
echo ""

# Check if process is running
PID=$(ps aux | grep "run_glm_fed_resume" | grep -v grep | awk '{print $2}')
if [ -z "$PID" ]; then
    echo "❌ Process is NOT running"
    echo ""
    echo "To restart:"
    echo "  cd /opt/geospatial_backend"
    echo "  nohup python app/run_glm_fed_resume.py > logs/glm_resume_nohup.log 2>&1 &"
else
    echo "✓ Process is running (PID: $PID)"
    ps -p $PID -o pid,etime,%cpu,%mem,cmd
    echo ""
fi

# Count files
TOTAL_FILES=$(ls /mnt/workwork/geoserver_data/glm_fed/glm_fed_*.tif 2>/dev/null | wc -l)
TARGET=221
REMAINING=$((TARGET - TOTAL_FILES))

echo "Progress:"
echo "  Files created:  $TOTAL_FILES / $TARGET"
echo "  Remaining:      $REMAINING dates"
echo "  Progress:       $(awk "BEGIN {printf \"%.1f\", ($TOTAL_FILES/$TARGET)*100}")%"
echo ""

# Latest files
echo "Latest 5 files created:"
ls -lht /mnt/workwork/geoserver_data/glm_fed/glm_fed_*.tif 2>/dev/null | head -5 | awk '{print "  " $9, "-", $6, $7, $8}'
echo ""

# Latest log entries
echo "Latest log entries:"
tail -15 /opt/geospatial_backend/logs/glm_resume_nohup.log 2>/dev/null | grep -E "Processing date|Created GeoTIFF|⚠|ERROR" | tail -5 | sed 's/^/  /'
echo ""

# Estimate completion
if [ ! -z "$PID" ]; then
    # Get process start time
    ELAPSED=$(ps -p $PID -o etime= | tr -d ' ')
    echo "Time estimates:"
    echo "  Running for:    $ELAPSED"
    if [ $TOTAL_FILES -gt 94 ]; then
        NEW_FILES=$((TOTAL_FILES - 94))
        echo "  New files:      $NEW_FILES created this run"
        echo "  Remaining:      ~$(awk "BEGIN {printf \"%.1f\", ($REMAINING * 7.5 / 60)}") hours"
        echo "                  (assuming ~7.5 min/date average)"
    fi
fi

echo ""
echo "================================================================================"
echo "Commands:"
echo "  Watch live:     tail -f logs/glm_resume_nohup.log"
echo "  Kill process:   kill $PID"
echo "  This monitor:   bash monitor_glm_progress.sh"
echo "================================================================================"
