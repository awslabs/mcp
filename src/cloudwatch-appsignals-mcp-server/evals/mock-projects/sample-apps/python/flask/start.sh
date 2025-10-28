#!/bin/bash
set -e

# Install Python dependencies
pip3 install -r requirements.txt

# Set default environment variables
export PORT=${PORT:-5000}
export SERVICE_NAME=${SERVICE_NAME:-python-flask-app}

# Start the Flask application
python3 app.py
