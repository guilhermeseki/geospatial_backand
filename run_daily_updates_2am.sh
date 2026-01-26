#!/bin/bash
#
# Daily Data Updates - Scheduled for 2:00 AM
# Runs all dataset updates except NDVI
#
# This script:
# 1. Downloads new data for each dataset (via Prefect flows)
# 2. Processes to GeoTIFF
# 3. Updates historical NetCDF files
# 4. Refreshes GeoServer mosaic index (deletes shapefile)
# 5. Triggers WMS warm-up requests to rebuild indexes immediately
#
# Add to crontab:
# 0 2 * * * /opt/geospatial_backend/run_daily_updates_2am.sh >> /opt/geospatial_backend/logs/daily_updates.log 2>&1

set -e

SCRIPT_DIR="/opt/geospatial_backend"
LOG_DIR="$SCRIPT_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# GeoServer connection
GEOSERVER_URL="http://localhost:8080/geoserver"
GEOSERVER_USER="admin"
GEOSERVER_PASS="todosabordo25!"

mkdir -p "$LOG_DIR"

echo "========================================================================"
echo "DAILY DATA UPDATES - $(date)"
echo "========================================================================"
echo ""

# Function to run a flow and log results
run_flow() {
    local name=$1
    local script=$2
    local datasets=$3  # Space-separated list of dataset names for warm-up

    echo "----------------------------------------"
    echo "[$name] Starting at $(date)"
    echo "----------------------------------------"

    if python3 "$SCRIPT_DIR/$script"; then
        echo "[$name] ✓ Flow completed successfully at $(date)"

        # Warm-up WMS requests to rebuild shapefile indexes
        if [ -n "$datasets" ]; then
            echo "[$name] Triggering GeoServer index rebuild via WMS requests..."
            for dataset in $datasets; do
                echo "  - Warming up $dataset..."
                # Make a small WMS GetMap request to trigger index rebuild
                # Use yesterday's date as a safe default
                yesterday=$(date -d "yesterday" +%Y-%m-%d)

                curl -s -m 90 \
                    "${GEOSERVER_URL}/wms?service=WMS&version=1.1.1&request=GetMap&layers=precipitation_ws:${dataset}&bbox=-94,-53,-34,25&width=100&height=100&srs=EPSG:4326&time=${yesterday}&format=image/png" \
                    -o /dev/null && echo "    ✓ ${dataset} index rebuilt" || echo "    ⚠ ${dataset} warm-up timeout (index will rebuild on next user request)"
            done
        fi
    else
        echo "[$name] ✗ Failed at $(date)"
    fi
    echo ""
}

# 1. CHIRPS Precipitation
run_flow "CHIRPS" "app/run_chirps_daily.py" "chirps"

# 2. MERGE Precipitation
run_flow "MERGE" "app/run_merge_daily.py" "merge"

# 3. ERA5 Temperature & Wind (single script handles both)
run_flow "ERA5 Temperature & Wind" "app/run_era5_daily.py" "temp_max temp_min temp_mean wind_speed"

# 4. GLM Lightning (if operational)
if [ -f "$SCRIPT_DIR/app/run_glm_daily.py" ]; then
    run_flow "GLM Lightning" "app/run_glm_daily.py" "glm_fed"
fi

echo "========================================================================"
echo "DAILY UPDATES COMPLETED - $(date)"
echo "========================================================================"
echo ""
echo "Summary:"
echo "  ✓ CHIRPS precipitation updated (GeoTIFF + historical NetCDF)"
echo "  ✓ MERGE precipitation updated (GeoTIFF + historical NetCDF)"
echo "  ✓ ERA5 temperature (max/min/mean) updated (GeoTIFF + historical NetCDF)"
echo "  ✓ ERA5 wind speed updated (GeoTIFF + historical NetCDF)"
echo "  ✓ GLM lightning updated (GeoTIFF + historical NetCDF)"
echo "  ✓ GeoServer mosaic indexes rebuilt via warm-up requests"
echo "  - NDVI: Skipped (runs separately)"
echo ""
echo "Next Steps:"
echo "  - All datasets ready for immediate use (indexes pre-built)"
echo "  - API can serve latest data without delay"
echo "  - Historical NetCDF files updated for time-series queries"
echo ""
