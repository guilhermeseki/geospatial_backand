#!/bin/bash
# Run multiple GLM processing instances in parallel for faster completion
# Each process handles different months to avoid conflicts

# Initialize conda
eval "$(/home/guilherme/miniconda3/bin/conda shell.bash hook)"
conda activate horus

LOG_DIR="/opt/geospatial_backend/logs"

echo "=========================================="
echo "GLM FED Parallel Processing"
echo "=========================================="
echo "This will launch 3 parallel processes:"
echo "  Process 1: April dates"
echo "  Process 2: September-October dates"
echo "  Process 3: November dates"
echo ""

# Kill existing single process if running
if ps aux | grep -q "[p]ython /opt/geospatial_backend/app/run_glm_fed_resume.py"; then
    echo "Stopping existing single process..."
    pkill -f "run_glm_fed_resume.py"
    pkill -f "run_glm_with_autorestart.sh"
    sleep 3
fi

# Process 1: April (missing dates 1-14) - 14 days
echo "[$(date)] Starting Process 1: April dates (14 days)..."
python /opt/geospatial_backend/app/run_glm_april.py > "$LOG_DIR/glm_april.log" 2>&1 &
PID1=$!

# Process 2: September-October - 49 days
echo "[$(date)] Starting Process 2: Sept-Oct dates (49 days)..."
python /opt/geospatial_backend/app/run_glm_sept_oct.py > "$LOG_DIR/glm_sept_oct.log" 2>&1 &
PID2=$!

# Process 3: November - 30 days
echo "[$(date)] Starting Process 3: November dates (30 days)..."
python /opt/geospatial_backend/app/run_glm_nov.py > "$LOG_DIR/glm_nov.log" 2>&1 &
PID3=$!

echo ""
echo "Launched 3 parallel processes:"
echo "  Process 1 (April): PID $PID1"
echo "  Process 2 (Sept-Oct): PID $PID2"
echo "  Process 3 (November): PID $PID3"
echo ""
echo "Monitor progress:"
echo "  tail -f $LOG_DIR/glm_april.log"
echo "  tail -f $LOG_DIR/glm_sept_oct.log"
echo "  tail -f $LOG_DIR/glm_nov.log"
echo ""
echo "=========================================="

# Wait for all processes
wait $PID1
EXIT1=$?
wait $PID2
EXIT2=$?
wait $PID3
EXIT3=$?

echo "=========================================="
echo "All processes completed:"
echo "  Process 1 (April): Exit code $EXIT1"
echo "  Process 2 (Sept-Oct): Exit code $EXIT2"
echo "  Process 3 (November): Exit code $EXIT3"
echo "=========================================="
