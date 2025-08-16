#!/bin/bash

# Docker entrypoint script for Agent-Builder
# Handles TFrameX installation and app startup

set -e

echo "Starting Agent-Builder container..."
echo "TFrameX is pre-installed via pip during image build"

# Change to the backend directory
cd /app/builder/backend

# Set environment variables for Flask
export FLASK_APP=app.py
export PYTHONPATH=/app:$PYTHONPATH

echo "Starting Flask application..."

# If no command is provided, run the Flask app
if [ $# -eq 0 ]; then
    exec python app.py
else
    # Execute the command passed to the container
    exec "$@"
fi