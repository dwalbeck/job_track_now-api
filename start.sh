#!/bin/bash

# Start nginx in the background
#sudo /usr/sbin/service nginx restart

# Wait a moment for nginx to start
#sleep 2
# kill off any previously running instance of the api
lsof -t -i:7080 | xargs kill -9

# Start uvicorn
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7080 --workers 4 --timeout-graceful-shutdown 200 --timeout-keep-alive 200 &

exit 0
