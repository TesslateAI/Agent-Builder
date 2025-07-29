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

# Execute the command passed to the container (or default command)
exec "$@"