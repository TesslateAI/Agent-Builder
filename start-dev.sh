#!/bin/bash
# Development start script for Agent-Builder using local TFrameX

set -e

echo "🚀 Starting Agent-Builder with local TFrameX 1.1.0"
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
    
    # Install TFrameX from local folder
    echo "📦 Installing TFrameX from local folder..."
    uv pip install -e ../TFrameX
    
    # Install TFrameX dependencies first
    echo "📦 Installing TFrameX dependencies..."
    uv pip install mcp openai
    
    # Install other dependencies
    echo "📦 Installing Agent-Builder dependencies..."
    uv pip install "flask[async]" flask-cors python-dotenv httpx pydantic PyYAML aiohttp
    
else
    source .venv/bin/activate
    
    # Always reinstall TFrameX to get latest changes
    echo "🔄 Updating TFrameX from local folder..."
    uv pip install -e ../TFrameX --force-reinstall --no-deps
    
    # Ensure all dependencies are installed
    echo "📦 Checking dependencies..."
    uv pip install mcp openai "flask[async]" flask-cors python-dotenv httpx pydantic PyYAML aiohttp
fi

# Check if frontend is built
if [ ! -d "builder/frontend/dist" ]; then
    echo "🏗️  Building frontend..."
    cd builder/frontend
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run build
    cd ../..
else
    echo "✅ Frontend already built"
fi

# Start the application
echo ""
echo "✅ Starting Agent-Builder!"
echo "   URL: http://localhost:5000"
echo "   Using TFrameX from: ../TFrameX"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd builder/backend
python app.py