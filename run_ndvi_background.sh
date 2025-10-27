#!/bin/bash
# Script to run MODIS NDVI download in background with logging

LOG_FILE="/opt/geospatial_backend/logs/ndvi_download_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="/opt/geospatial_backend/logs/ndvi_download.pid"

# Create logs directory if it doesn't exist
mkdir -p /opt/geospatial_backend/logs

echo "Starting MODIS NDVI download in background..."
echo "Log file: $LOG_FILE"
echo "PID file: $PID_FILE"

# Run in background with nohup
cd /opt/geospatial_backend
nohup python app/run_ndvi.py > "$LOG_FILE" 2>&1 &

# Save PID
echo $! > "$PID_FILE"

echo "Process started with PID: $(cat $PID_FILE)"
echo ""
echo "To monitor progress:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To check status:"
echo "  ps aux | grep $(cat $PID_FILE)"
echo "  python check_ndvi_progress.py"
echo ""
echo "To stop the download:"
echo "  kill $(cat $PID_FILE)"
