#!/bin/bash
#
# Full Backfill - Run ONCE before operational deployment
# Checks ALL dates for all datasets and fills any gaps
#
# This script runs backfill for:
# - CHIRPS (2015-present)
# - MERGE (2014-present)
# - ERA5 Temperature & Wind (2015-present)
# - GLM Lightning (April 2025-present)
#
# Usage: ./run_full_backfill.sh

set -e

SCRIPT_DIR="/opt/geospatial_backend"
LOG_DIR="$SCRIPT_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/backfill_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

echo "========================================================================"
echo "FULL BACKFILL - ONE-TIME OPERATION"
echo "========================================================================"
echo ""
echo "Log file: $LOG_FILE"
echo ""
echo "This will check ALL dates for all datasets and download only missing files."
echo "Existing files are skipped automatically (safe and fast)."
echo ""
echo "Starting backfill..."

echo "" | tee -a "$LOG_FILE"
echo "========================================================================" | tee -a "$LOG_FILE"
echo "BACKFILL STARTED - $(date)" | tee -a "$LOG_FILE"
echo "========================================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Function to run backfill and log
run_backfill() {
    local name=$1
    local script=$2

    echo "========================================================================" | tee -a "$LOG_FILE"
    echo "[$name] Starting at $(date)" | tee -a "$LOG_FILE"
    echo "========================================================================" | tee -a "$LOG_FILE"

    if python3 "$SCRIPT_DIR/$script" 2>&1 | tee -a "$LOG_FILE"; then
        echo "" | tee -a "$LOG_FILE"
        echo "[$name] ✓ Completed successfully at $(date)" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
    else
        echo "" | tee -a "$LOG_FILE"
        echo "[$name] ✗ Failed at $(date)" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
        exit 1
    fi
}

# 1. CHIRPS Precipitation (2015-present)
run_backfill "CHIRPS Precipitation" "app/run_chirps_backfill.py"

# 2. MERGE Precipitation (2014-present)
run_backfill "MERGE Precipitation" "app/run_merge_backfill.py"

# 3. ERA5 Temperature & Wind (2015-present)
run_backfill "ERA5 Temperature & Wind" "app/run_era5_backfill.py"

# 4. GLM Lightning (April 2025-present)
run_backfill "GLM Lightning" "app/run_glm_backfill.py"

echo "========================================================================" | tee -a "$LOG_FILE"
echo "FULL BACKFILL COMPLETED - $(date)" | tee -a "$LOG_FILE"
echo "========================================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Summary:" | tee -a "$LOG_FILE"
echo "  ✓ CHIRPS backfilled (2015-present)" | tee -a "$LOG_FILE"
echo "  ✓ MERGE backfilled (2014-present)" | tee -a "$LOG_FILE"
echo "  ✓ ERA5 Temperature & Wind backfilled (2015-present)" | tee -a "$LOG_FILE"
echo "  ✓ GLM Lightning backfilled (April 2025-present)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Next Steps:" | tee -a "$LOG_FILE"
echo "  1. Verify datasets are complete (check file counts)" | tee -a "$LOG_FILE"
echo "  2. Test GeoServer WMS requests" | tee -a "$LOG_FILE"
echo "  3. Install cron schedule: ./install_cron_schedule.sh" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Log file saved: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================================================" | tee -a "$LOG_FILE"
