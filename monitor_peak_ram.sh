#!/bin/bash
# Monitor peak RAM usage of NDVI processing

echo "Starting RAM monitoring (checking every 5 seconds for 5 minutes)..."
echo "Time | Process RAM (GB) | System RAM Used | Peak RAM (GB)"
echo "----------------------------------------------------------------"

PEAK_RAM=0
COUNT=0
MAX_COUNT=60  # 5 minutes at 5-second intervals

while [ $COUNT -lt $MAX_COUNT ]; do
    # Get current process RAM
    PID=$(pgrep -f "run_ndvi_2024_monitored.py" | head -1)

    if [ -n "$PID" ]; then
        CURRENT_RAM=$(ps -o rss= -p $PID | awk '{printf "%.2f", $1/1024/1024}')

        # Update peak if current is higher
        if [ $(echo "$CURRENT_RAM > $PEAK_RAM" | bc -l) -eq 1 ]; then
            PEAK_RAM=$CURRENT_RAM
        fi

        # Get system RAM
        SYS_RAM=$(free -h | grep Mem | awk '{print $3}')

        # Current time
        TIME=$(date +%H:%M:%S)

        echo "$TIME | $CURRENT_RAM GB | $SYS_RAM | $PEAK_RAM GB"
    else
        echo "Process not found, stopping monitoring"
        break
    fi

    COUNT=$((COUNT + 1))
    sleep 5
done

echo "----------------------------------------------------------------"
echo "PEAK RAM USAGE: $PEAK_RAM GB"
