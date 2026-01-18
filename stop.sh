#!/bin/bash

# Stop uvicorn using saved PID file
if [ -f /var/www/job_api/uvicorn.pid ]; then
    PID=$(cat /var/www/job_api/uvicorn.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping uvicorn (PID: $PID)..."
        kill $PID
        sleep 2

        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            echo "Force stopping uvicorn..."
            kill -9 $PID
        fi
    else
        echo "Process $PID is not running"
    fi
    rm -f /var/www/job_api/uvicorn.pid
else
    echo "PID file not found, attempting to kill by port..."
    timeout 5 lsof -t -i:7080 | xargs -r kill -9 2>/dev/null || true
fi

echo "Uvicorn stopped"
