#!/bin/bash
# Monitor CHIRPS clipping progress

LOG_FILE=$(ls -t logs/clip_chirps_*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "No log file found"
    exit 1
fi

echo "Monitoring: $LOG_FILE"
echo "=========================================="
echo ""

# Show summary
tail -20 "$LOG_FILE" | grep -E "(Found|Progress|Processed|COMPLETE|Successful|Failed)"

echo ""
echo "=========================================="
echo "Last 5 log entries:"
tail -5 "$LOG_FILE"
