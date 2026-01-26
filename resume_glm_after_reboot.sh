#!/bin/bash
# Resume GLM FED processing after system reboot
# Run this script after reboot to continue where we left off

# Initialize conda
eval "$(/home/guilherme/miniconda3/bin/conda shell.bash hook)"
conda activate horus

cd /opt/geospatial_backend

echo "=========================================="
echo "Resuming GLM FED Processing After Reboot"
echo "=========================================="
echo ""

# Check how many files we have
COMPLETED=$(ls /mnt/workwork/geoserver_data/glm_fed/*.tif 2>/dev/null | wc -l)
echo "Current progress: $COMPLETED / 244 dates"
echo ""

if [ $COMPLETED -eq 244 ]; then
    echo "🎉 ALL 244 DATES ALREADY COMPLETE! 🎉"
    echo "Nothing to do!"
    exit 0
fi

REMAINING=$((244 - COMPLETED))
echo "Remaining dates: $REMAINING"
echo ""
echo "Starting processing in background..."
echo ""

# Run the final 6 dates script (will auto-skip completed dates)
nohup bash -c 'eval "$(/home/guilherme/miniconda3/bin/conda shell.bash hook)" && conda activate horus && python /opt/geospatial_backend/app/run_glm_final_6.py' > logs/glm_final_6_resume.log 2>&1 &

PID=$!
echo "Process started with PID: $PID"
echo ""
echo "Monitor progress:"
echo "  /opt/geospatial_backend/monitor_glm_final.sh"
echo "  tail -f logs/glm_final_6_resume.log"
echo ""
echo "=========================================="
