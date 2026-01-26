#!/bin/bash
# Restart the FastAPI application to reload temp_mean datasets

echo "Finding FastAPI processes..."
PID=$(ps aux | grep "uvicorn main:app" | grep -v grep | awk '{print $2}' | head -1)

if [ -z "$PID" ]; then
    echo "No FastAPI process found"
    exit 1
fi

echo "Found FastAPI process: $PID"
echo "Restarting..."

# Kill the main process (this will restart workers)
kill -HUP $PID

sleep 2

# Check if still running
if ps -p $PID > /dev/null; then
    echo "✓ API restarted successfully (PID: $PID)"
else
    echo "⚠️  Main process died, checking if new one started..."
    NEW_PID=$(ps aux | grep "uvicorn main:app" | grep -v grep | awk '{print $2}' | head -1)
    if [ -n "$NEW_PID" ]; then
        echo "✓ New API process running (PID: $NEW_PID)"
    else
        echo "✗ API not running. You may need to start it manually."
    fi
fi

echo ""
echo "Testing API status..."
sleep 3
curl -s http://localhost:8000/status | python3 -m json.tool | grep -A 5 "temperature_sources"
