#!/bin/bash
# Quick start script for Agent-Builder

set -e

echo "🚀 Starting Agent-Builder with TFrameX 1.1.0"
echo "=========================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "🔧 Setting up Python environment..."
    uv venv
    source .venv/bin/activate
    
    # Check for local TFrameX
    if [ -d "../TFrameX" ]; then
        echo "📦 Found local TFrameX, installing from ../TFrameX"
        uv pip install -e ../TFrameX
        uv pip install flask flask-cors python-dotenv httpx pydantic PyYAML aiohttp
    else
        echo "📦 Installing from pyproject.toml"
        echo "⚠️  Note: This requires TFrameX 1.1.0 to be published on PyPI"
        uv pip install -e .
    fi
else
    source .venv/bin/activate
fi

# Check if frontend is built
if [ ! -d "builder/frontend/dist" ]; then
    echo "🏗️  Building frontend..."
    cd builder/frontend
    npm install
    npm run build
    cd ../..
fi

# Start the application
echo ""
echo "✅ Starting Agent-Builder!"
echo "   URL: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd builder/backend
python app.py