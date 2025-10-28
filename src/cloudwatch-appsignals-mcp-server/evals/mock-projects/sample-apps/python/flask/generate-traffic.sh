#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
