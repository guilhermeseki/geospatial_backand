#!/bin/bash
# Monitor script for GLM test

echo "================================================================================"
echo "GLM FED TEST MONITOR"
echo "================================================================================"
echo ""

# Check if process is running
if ps aux | grep -q "[t]est_glm_single_day.py"; then
    echo "✓ Test process is RUNNING"
    PID=$(ps aux | grep "[t]est_glm_single_day.py" | awk '{print $2}')
    echo "  PID: $PID"

    # Show memory usage
    MEM=$(ps aux | grep "[t]est_glm_single_day.py" | awk '{print $4"%"}')
    echo "  Memory: $MEM"
else
    echo "✗ Test process is NOT running"
fi

echo ""
echo "Recent log entries:"
echo "--------------------------------------------------------------------------------"
tail -20 logs/glm_test_single.log | grep -E "INFO|ERROR|WARNING|✓|✗|Downloaded|Batch|Created|append"

echo ""
echo "================================================================================"
echo "Check outputs:"
echo "--------------------------------------------------------------------------------"

# Check for GeoTIFF
if ls /mnt/workwork/geoserver_data/glm_fed/glm_fed_20250427.tif >/dev/null 2>&1; then
    SIZE=$(ls -lh /mnt/workwork/geoserver_data/glm_fed/glm_fed_20250427.tif | awk '{print $5}')
    echo "✓ GeoTIFF created: glm_fed_20250427.tif ($SIZE)"
else
    echo "⊘ GeoTIFF not created yet"
fi

# Check for historical NetCDF
if ls /mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc >/dev/null 2>&1; then
    SIZE=$(ls -lh /mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc | awk '{print $5}')
    echo "✓ Historical NetCDF exists: glm_fed_2025.nc ($SIZE)"

    # Check for duplicate coordinates
    python3 -c "
import xarray as xr
import numpy as np
from pathlib import Path

hist_file = Path('/mnt/workwork/geoserver_data/glm_fed_hist/glm_fed_2025.nc')
if hist_file.exists():
    with xr.open_dataset(hist_file) as ds:
        if 'longitude' in ds.coords:
            lon_vals = ds.longitude.values
            lat_vals = ds.latitude.values
            unique_lon = len(np.unique(lon_vals))
            unique_lat = len(np.unique(lat_vals))

            if unique_lon == len(lon_vals) and unique_lat == len(lat_vals):
                print('  ✓ No duplicate coordinates (GOOD!)')
            else:
                print(f'  ✗ Has duplicates: lon {len(lon_vals)}/{unique_lon}, lat {len(lat_vals)}/{unique_lat}')

            # Check how many dates
            if 'time' in ds.dims:
                print(f'  Dates in file: {len(ds.time)}')
" 2>/dev/null
else
    echo "⊘ Historical NetCDF not created yet"
fi

echo "================================================================================"
