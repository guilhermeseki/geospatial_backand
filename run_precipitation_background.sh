#!/bin/bash
# Script to run precipitation yearly historical build in background

LOG_FILE="/opt/geospatial_backend/logs/precipitation_historical_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="/opt/geospatial_backend/logs/precipitation_historical.pid"

# Create logs directory
mkdir -p /opt/geospatial_backend/logs

echo "Starting precipitation yearly historical build in background..."
echo "Log file: $LOG_FILE"
echo "PID file: $PID_FILE"

# Run in background
cd /opt/geospatial_backend
nohup python app/run_precipitation.py > "$LOG_FILE" 2>&1 &

# Save PID
echo $! > "$PID_FILE"

echo "Process started with PID: $(cat $PID_FILE)"
echo ""
echo "This will process:"
echo "  - 3,623 CHIRPS GeoTIFFs → yearly NetCDF files"
echo "  - 4,009 MERGE GeoTIFFs → yearly NetCDF files"
echo ""
echo "Expected time: ~30 minutes"
echo ""
echo "To monitor progress:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To check status:"
echo "  python check_precipitation_progress.py"
echo ""
echo "To stop:"
echo "  kill $(cat $PID_FILE)"
