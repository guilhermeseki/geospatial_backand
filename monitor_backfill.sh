#!/bin/bash
#
# Monitor Backfill Progress
# Shows live updates of the backfill process
#

LATEST_LOG=$(ls -t /opt/geospatial_backend/logs/backfill_*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "No backfill log found"
    exit 1
fi

echo "========================================================================"
echo "MONITORING BACKFILL: $LATEST_LOG"
echo "========================================================================"
echo ""
echo "Press Ctrl+C to stop monitoring (backfill will continue running)"
echo ""

tail -f "$LATEST_LOG" | grep --line-buffered -E "Starting|Completed|Failed|Processing|✓|✗|Processed.*files|BACKFILL"
