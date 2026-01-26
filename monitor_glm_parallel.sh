#!/bin/bash
# Monitor all 3 parallel GLM processes

echo "=========================================="
echo "GLM FED Parallel Processing Status"
echo "=========================================="
date
echo ""

# Check each process
check_process() {
    NAME=$1
    PID_PATTERN=$2
    LOG_FILE=$3

    PID=$(ps aux | grep "$PID_PATTERN" | grep -v grep | awk '{print $2}' | head -1)
    if [ -n "$PID" ]; then
        RUNTIME=$(ps -p $PID -o etime= 2>/dev/null | tr -d ' ')
        echo "✓ $NAME (PID $PID, runtime $RUNTIME)"

        # Get current date being processed
        CURRENT=$(tail -50 "$LOG_FILE" 2>/dev/null | grep "Processing date" | tail -1)
        if [ -n "$CURRENT" ]; then
            echo "  $CURRENT"
        fi

        # Get download progress
        DOWNLOAD=$(tail -20 "$LOG_FILE" 2>/dev/null | grep "Downloaded" | tail -1)
        if [ -n "$DOWNLOAD" ]; then
            echo "  $DOWNLOAD"
        fi
    else
        echo "✗ $NAME - NOT RUNNING"
    fi
    echo ""
}

check_process "Process 1 (April)" "python.*run_glm_april" "/opt/geospatial_backend/logs/glm_april.log"
check_process "Process 2 (Sept-Oct)" "python.*run_glm_sept_oct" "/opt/geospatial_backend/logs/glm_sept_oct.log"
check_process "Process 3 (November)" "python.*run_glm_nov" "/opt/geospatial_backend/logs/glm_nov.log"

# Count total completed files
TOTAL=$(ls /mnt/workwork/geoserver_data/glm_fed/*.tif 2>/dev/null | wc -l)
echo "Total completed dates: $TOTAL / 244"
echo "Progress: $(echo "scale=1; $TOTAL * 100 / 244" | bc)%"
echo ""

echo "=========================================="
echo "Monitor commands:"
echo "  watch -n 10 $0"
echo "  tail -f logs/glm_april.log"
echo "  tail -f logs/glm_sept_oct.log"
echo "  tail -f logs/glm_nov.log"
echo "=========================================="
