#!/bin/bash
set -e

echo "Starting Agent-Builder backend with init script..."

# Check if SQLAlchemy is already installed
if ! /opt/venv/bin/python -c "import sqlalchemy" 2>/dev/null; then
    echo "SQLAlchemy not found, installing..."
    # Create a temporary directory for pip cache
    export PIP_CACHE_DIR=/tmp/pip-cache
    mkdir -p $PIP_CACHE_DIR
    
    # Install as root
    /opt/venv/bin/pip install --cache-dir=$PIP_CACHE_DIR SQLAlchemy==2.0.23 psycopg2-binary==2.9.9 alembic==1.13.1
    
    # Clean up
    rm -rf $PIP_CACHE_DIR
    echo "Installation complete!"
else
    echo "SQLAlchemy already installed"
fi

# Set up environment
export FLASK_APP=builder.backend.app
export PYTHONPATH=/app:$PYTHONPATH

# Change to backend directory
cd /app/builder/backend

# Start Flask in development mode
echo "Starting Flask application in development mode..."
exec su appuser -c 'python -m flask run --host=0.0.0.0 --port=5000 --reload'