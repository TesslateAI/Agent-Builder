#!/bin/bash
# Script to run Agent-Builder with TFrameX 1.1.0

echo "Starting Agent-Builder with TFrameX 1.1.0..."
echo "============================================"

# Navigate to backend directory
cd builder/backend

# Install/update dependencies
echo "Installing backend dependencies..."
pip install -r requirements.txt

# Start the backend server
echo "Starting backend server on port 5000..."
python app.py &
BACKEND_PID=$!

echo "Backend started with PID: $BACKEND_PID"
echo ""
echo "Backend API available at: http://localhost:5000"
echo "Test endpoints:"
echo "  - http://localhost:5000/api/tframex/components"
echo "  - http://localhost:5000/api/tframex/mcp/status"
echo ""
echo "To start the frontend (in another terminal):"
echo "  cd builder/frontend"
echo "  npm install"
echo "  npm run dev"
echo ""
echo "Press Ctrl+C to stop the backend server"

# Wait for interrupt
wait $BACKEND_PID