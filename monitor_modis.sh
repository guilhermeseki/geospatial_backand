#!/bin/bash
# Monitor MODIS reprocessing progress

# Check which process is running
if ps aux | grep "python app/run_ndvi_2025.py" | grep -v grep > /dev/null; then
    LOG_FILE="/tmp/modis_2025.log"
    PROCESS_NAME="2025 Priority Run"
elif ps aux | grep "python app/run_ndvi.py" | grep -v grep > /dev/null; then
    LOG_FILE="/tmp/modis_reprocess_fixed.log"
    PROCESS_NAME="Full Reprocess (2015-2025)"
else
    LOG_FILE="/tmp/modis_2025.log"
    PROCESS_NAME="None"
fi

echo "==================================="
echo "MODIS Processing Status"
echo "==================================="
echo "Process: $PROCESS_NAME"
echo ""

# Check if process is running
if [ "$PROCESS_NAME" != "None" ]; then
    if ps aux | grep "python app/run_ndvi" | grep -v grep > /dev/null; then
        PID=$(ps aux | grep "python app/run_ndvi" | grep -v grep | awk '{print $2}')
        MEM=$(ps aux | grep "python app/run_ndvi" | grep -v grep | awk '{print $6}')
        MEM_GB=$(echo "scale=1; $MEM / 1024 / 1024" | bc)
        echo "✓ Process running (PID: $PID, RAM: ${MEM_GB}GB)"
    else
        echo "✗ Process not running"
        exit 1
    fi
else
    echo "✗ No MODIS process running"
    exit 1
fi

echo ""

# Count files created
GEOTIFF_COUNT=$(ls -1 /mnt/workwork/geoserver_data/ndvi_modis/*.tif 2>/dev/null | wc -l)
NC_COUNT=$(ls -1 /mnt/workwork/geoserver_data/ndvi_modis_hist/*.nc 2>/dev/null | wc -l)

echo "Files created:"
echo "  GeoTIFFs: $GEOTIFF_COUNT"
echo "  NetCDF:   $NC_COUNT"
echo ""

# Check current batch progress
echo "Current batch progress:"
tail -30 "$LOG_FILE" | grep -E "Processing composite [0-9]+/[0-9]+" | tail -1
echo ""

# Check for merge operations
echo "Recent merge operations:"
grep -E "Merging.*tiles|Merged mosaic:" "$LOG_FILE" | tail -5
echo ""

# Check for historical append operations
echo "Historical NetCDF appends:"
grep -E "Adding.*new dates|Writing to temp|Year.*complete" "$LOG_FILE" | tail -5
echo ""

# Check for errors
echo "Recent errors:"
grep -iE "error|failed|invalid pointer|FutureWarning" "$LOG_FILE" | tail -5
echo ""

echo "==================================="
echo "To watch live: tail -f $LOG_FILE"
echo "==================================="
