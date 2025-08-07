#!/bin/bash
set -e

echo "Starting Agent-Builder backend with init script..."

# Check if all requirements are installed (using nanoid as a test package)
if ! /opt/venv/bin/python -c "import nanoid" 2>/dev/null; then
    echo "Missing dependencies detected, installing from requirements.txt..."
    # Create a temporary directory for pip cache
    export PIP_CACHE_DIR=/tmp/pip-cache
    mkdir -p $PIP_CACHE_DIR
    
    # Install all requirements
    /opt/venv/bin/pip install --cache-dir=$PIP_CACHE_DIR -r /app/builder/backend/requirements.txt
    
    # Clean up
    rm -rf $PIP_CACHE_DIR
    echo "Installation complete!"
else
    echo "All requirements already installed"
fi

# Set up environment
export FLASK_APP=builder.backend.app
export PYTHONPATH=/app:$PYTHONPATH

# Change to backend directory
cd /app/builder/backend

# Start Flask in development mode
echo "Starting Flask application in development mode..."
exec su appuser -c 'python -m flask run --host=0.0.0.0 --port=5000 --reload'