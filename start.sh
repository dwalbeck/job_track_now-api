#!/bin/bash

# Start nginx in the background
sudo /usr/sbin/service nginx restart

# Wait a moment for nginx to start
sleep 2

# Start uvicorn
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 7080 --workers 4 --timeout-graceful-shutdown 200 --timeout-keep-alive 200
