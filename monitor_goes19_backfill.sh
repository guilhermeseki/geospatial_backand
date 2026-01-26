#!/bin/bash
# Monitor GOES-19 backfill progress

echo "================================================================================"
echo "GOES-19 BACKFILL PROGRESS MONITOR"
echo "================================================================================"
echo ""

# Check if process is running
if pgrep -f "run_goes19_backfill_2025.py" > /dev/null; then
    echo "✓ Backfill process is RUNNING"
    PID=$(pgrep -f "run_goes19_backfill_2025.py")
    echo "  PID: $PID"
else
    echo "✗ Backfill process is NOT running"
fi

echo ""
echo "Log file: /tmp/goes19_backfill.log"
echo ""

# Count processed dates
PROCESSED=$(grep -c "Processing date:" /tmp/goes19_backfill.log 2>/dev/null || echo "0")
echo "Dates processed: $PROCESSED / 107"

# Show current date being processed
CURRENT_DATE=$(grep "Processing date:" /tmp/goes19_backfill.log 2>/dev/null | tail -1)
if [ ! -z "$CURRENT_DATE" ]; then
    echo "Current: $CURRENT_DATE"
fi

echo ""
echo "Recent log entries:"
echo "--------------------------------------------------------------------------------"
tail -20 /tmp/goes19_backfill.log
echo "================================================================================"
