#!/bin/bash
# Auto-restart wrapper for GLM FED processing
# Automatically restarts processing if it crashes

# Initialize conda
eval "$(/home/guilherme/miniconda3/bin/conda shell.bash hook)"
conda activate horus

LOG_DIR="/opt/geospatial_backend/logs"
MAIN_LOG="$LOG_DIR/glm_autorestart.log"
PYTHON_SCRIPT="/opt/geospatial_backend/app/run_glm_fed_resume.py"
MAX_CONSECUTIVE_CRASHES=10
CRASH_COUNT=0
LAST_CRASH_TIME=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MAIN_LOG"
}

log "=========================================="
log "GLM FED Auto-Restart Monitor Started"
log "=========================================="
log "Script: $PYTHON_SCRIPT"
log "Python: $(which python)"
log "Max consecutive crashes before giving up: $MAX_CONSECUTIVE_CRASHES"
log ""

while true; do
    START_TIME=$(date +%s)
    log "Starting GLM FED processing (attempt $((CRASH_COUNT + 1)))..."

    # Run the Python script
    python "$PYTHON_SCRIPT"
    EXIT_CODE=$?

    END_TIME=$(date +%s)
    RUNTIME=$((END_TIME - START_TIME))

    # Check if process completed successfully
    if [ $EXIT_CODE -eq 0 ]; then
        log "✓ Processing completed successfully!"
        log "Total runtime: $((RUNTIME / 3600))h $((RUNTIME % 3600 / 60))m"
        break
    else
        log "✗ Processing crashed with exit code: $EXIT_CODE"
        log "Runtime before crash: $((RUNTIME / 60))m $((RUNTIME % 60))s"

        # Check if this is a quick crash (< 5 minutes = likely config error)
        if [ $RUNTIME -lt 300 ]; then
            log "⚠ Quick crash detected (< 5 minutes) - possible configuration error"
            CRASH_COUNT=$((CRASH_COUNT + 1))
        else
            # Reset crash count if it ran for a while (> 5 min)
            log "Process ran for a while before crashing, resetting crash counter"
            CRASH_COUNT=0
        fi

        # Check if we've hit max crashes
        if [ $CRASH_COUNT -ge $MAX_CONSECUTIVE_CRASHES ]; then
            log "✗ ERROR: Hit maximum consecutive crashes ($MAX_CONSECUTIVE_CRASHES)"
            log "✗ Stopping auto-restart to prevent infinite loop"
            log "✗ Please investigate the issue manually"
            exit 1
        fi

        # Wait a bit before restarting
        WAIT_TIME=30
        log "Waiting ${WAIT_TIME}s before restart..."
        sleep $WAIT_TIME

        log "Restarting processing..."
    fi
done

log "=========================================="
log "GLM FED Auto-Restart Monitor Finished"
log "=========================================="
