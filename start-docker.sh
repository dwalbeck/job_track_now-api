#!/bin/bash

# Start nginx in the background
nginx -g 'daemon off;' &

# Wait a moment for nginx to start
sleep 2

# Start uvicorn in the foreground (this keeps the container running)
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7080 --workers 4 --timeout-graceful-shutdown 200 --timeout-keep-alive 200
