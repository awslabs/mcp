#!/bin/bash

# Traffic generator script for Flask application
PORT=${PORT:-5000}
BASE_URL="http://localhost:${PORT}"

echo "Starting continuous traffic generation to ${BASE_URL}"

while true; do
    echo "[$(date '+%H:%M:%S')] Generating traffic..."

    # Health check
    curl -sf "${BASE_URL}/health" > /dev/null
    if [ $? -ne 0 ]; then
        echo "[$(date '+%H:%M:%S')] ERROR: Health check failed!"
    fi

    # API call (S3 buckets)
    curl -sf "${BASE_URL}/api/buckets" > /dev/null
    if [ $? -ne 0 ]; then
        echo "[$(date '+%H:%M:%S')] ERROR: API call to /api/buckets failed!"
    fi

    # Sleep between requests
    sleep 2
done
