#!/bin/bash
# Monitor final 6 dates processing

echo "=========================================="
echo "GLM FED - Final 6 Dates Processing"
echo "=========================================="
date
echo ""

# Check if process is running
PID=$(ps aux | grep "python.*run_glm_final_6" | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$PID" ]; then
    RUNTIME=$(ps -p $PID -o etime= 2>/dev/null | tr -d ' ')
    echo "✓ Processing is RUNNING (PID $PID, runtime $RUNTIME)"
    echo ""

    # Get current progress
    CURRENT=$(tail -50 logs/glm_final_6.log 2>/dev/null | grep "Processing date" | tail -1)
    if [ -n "$CURRENT" ]; then
        echo "$CURRENT"
    fi

    # Get download progress
    DOWNLOAD=$(tail -20 logs/glm_final_6.log 2>/dev/null | grep "Downloaded" | tail -1)
    if [ -n "$DOWNLOAD" ]; then
        echo "  $DOWNLOAD"
    fi
else
    echo "✗ Processing NOT running (may have completed or crashed)"
fi

echo ""

# Count completed files
TOTAL=$(ls /mnt/workwork/geoserver_data/glm_fed/*.tif 2>/dev/null | wc -l)
echo "Total completed dates: $TOTAL / 244"

if [ $TOTAL -eq 244 ]; then
    echo ""
    echo "🎉 ✓ ALL 244 DATES COMPLETE! 🎉"
fi

echo ""
echo "=========================================="
echo "Monitor: watch -n 5 $0"
echo "Full log: tail -f logs/glm_final_6.log"
echo "=========================================="
