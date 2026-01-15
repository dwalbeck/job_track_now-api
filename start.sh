#!/bin/bash

# Kill off any previously running instance of the api
lsof -t -i:7080 | xargs -r kill -9 2>/dev/null || true

# Wait a moment for port to be released
sleep 2

# Start uvicorn with nohup, fully detached from terminal
# Redirect stdin, stdout, and stderr to break SSH attachment
nohup python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 7080 \
    --workers 4 \
    --timeout-graceful-shutdown 200 \
    --timeout-keep-alive 200 \
    </dev/null >/var/www/job_api/uvicorn.log 2>&1 &

# Save PID for later management
echo $! > /var/www/job_api/uvicorn.pid

# Give uvicorn a moment to start
sleep 2

# Verify it started
if lsof -t -i:7080 >/dev/null 2>&1; then
    echo "Uvicorn started successfully (PID: $(cat /var/www/job_api/uvicorn.pid))"
    exit 0
else
    echo "ERROR: Uvicorn failed to start"
    exit 1
fi
