#!/bin/bash

# Kill any existing servers
echo "🧹 Cleaning up existing servers..."
pkill -f "uvicorn.*api.main" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 2

# Start API server
echo "🚀 Starting API server on port 8000..."
cd /Users/joshuadell/Dev/AI_Document_Pipeline
/Users/joshuadell/Dev/AI_Document_Pipeline/.venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for API to start
sleep 5

# Start frontend server
echo "🌐 Starting frontend server on port 3000..."
cd /Users/joshuadell/Dev/AI_Document_Pipeline/frontend
npm run dev &
FRONTEND_PID=$!

# Wait for both to start
sleep 5

echo "✅ Servers started!"
echo "🔗 API: http://localhost:8000"
echo "🔗 Frontend: http://localhost:3000"
echo ""
echo "Testing connections..."

# Test API
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API server is responding"
else
    echo "❌ API server is not responding"
fi

# Test Frontend
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend server is responding"
else
    echo "❌ Frontend server is not responding"
fi

echo ""
echo "🎯 Ready to test! Open http://localhost:3000 in your browser"
echo ""
echo "To stop servers later, run:"
echo "kill $API_PID $FRONTEND_PID"

# Keep script running
wait