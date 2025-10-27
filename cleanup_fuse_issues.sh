#!/bin/bash
# Cleanup script for FUSE filesystem issues
# Run this to clean up corrupted historical.nc files and FUSE hidden files

set -e

DATA_DIR="/mnt/workwork/geoserver_data"

echo "=========================================="
echo "FUSE Filesystem Cleanup Script"
echo "=========================================="
echo ""

# 1. Check for running processes that might have files open
echo "1. Checking for running Python processes..."
PYTHON_PROCS=$(ps aux | grep -E "(python|prefect|uvicorn)" | grep -v grep | wc -l)
if [ $PYTHON_PROCS -gt 0 ]; then
    echo "⚠️  WARNING: Found $PYTHON_PROCS running Python processes"
    echo "   It's recommended to stop them first:"
    echo "   - Stop FastAPI: pkill -f 'uvicorn main:app'"
    echo "   - Stop Prefect flows: pkill -f 'python app/run_'"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 2. Find and report FUSE hidden files
echo ""
echo "2. Finding FUSE hidden files..."
HIDDEN_FILES=$(find "$DATA_DIR" -name ".fuse_hidden*" -type f 2>/dev/null || true)
HIDDEN_COUNT=$(echo "$HIDDEN_FILES" | grep -c "fuse_hidden" || echo "0")

if [ "$HIDDEN_COUNT" -gt 0 ]; then
    echo "   Found $HIDDEN_COUNT hidden lock files"
    HIDDEN_SIZE=$(du -sh $DATA_DIR/.fuse_hidden* 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "unknown")
    echo "   Total size: $HIDDEN_SIZE"

    echo ""
    echo "   Files:"
    echo "$HIDDEN_FILES" | head -5
    if [ "$HIDDEN_COUNT" -gt 5 ]; then
        echo "   ... and $((HIDDEN_COUNT - 5)) more"
    fi

    echo ""
    read -p "Delete these files? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        find "$DATA_DIR" -name ".fuse_hidden*" -type f -delete
        echo "   ✓ Deleted $HIDDEN_COUNT FUSE hidden files"
    fi
else
    echo "   ✓ No FUSE hidden files found"
fi

# 3. Check historical.nc files for corruption
echo ""
echo "3. Checking historical.nc files for corruption..."
HIST_FILES=$(find "$DATA_DIR" -name "historical.nc" -type f 2>/dev/null || true)

if [ -n "$HIST_FILES" ]; then
    echo "$HIST_FILES" | while read -r hist_file; do
        echo ""
        echo "   Checking: $hist_file"

        # Check file size
        FILE_SIZE=$(stat -c%s "$hist_file" 2>/dev/null || echo "0")
        echo "     Size: $FILE_SIZE bytes"

        # Try to open with Python and check time dimension
        TIME_DIMS=$(python3 -c "
import xarray as xr
import sys
try:
    ds = xr.open_dataset('$hist_file')
    if 'time' in ds.dims:
        print(len(ds.time))
    else:
        print('0')
    ds.close()
except Exception as e:
    print('ERROR')
" 2>&1)

        echo "     Time dims: $TIME_DIMS"

        # If file is corrupted (0 time dims or error), offer to delete
        if [ "$TIME_DIMS" = "0" ] || [ "$TIME_DIMS" = "ERROR" ] || [ "$FILE_SIZE" -lt 50000 ]; then
            echo "     ⚠️  File appears corrupted!"
            read -p "     Delete this file? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -f "$hist_file"
                echo "     ✓ Deleted corrupted file"
            fi
        else
            echo "     ✓ File looks OK"
        fi
    done
else
    echo "   No historical.nc files found"
fi

echo ""
echo "=========================================="
echo "Cleanup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run the ERA5 flow to recreate historical files"
echo "   python app/run_era5.py"
echo ""
echo "2. The flow will now use /tmp for safe writes"
echo "   (avoiding FUSE filesystem issues)"
