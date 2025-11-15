#!/bin/bash
# filepath: start_all.sh

echo "🚀 Starting Both Servers..."

# Start API server in background
./start_api.sh &
API_PID=$!

# Wait a moment for API to start
sleep 3

# Start frontend server in background
./start_frontend.sh &
FRONTEND_PID=$!

echo "✅ API Server PID: $API_PID"
echo "✅ Frontend Server PID: $FRONTEND_PID"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔗 API: http://localhost:8000"
echo ""
echo "✅ Both servers are now running in the background!"
echo "To stop them, run: pkill -f 'uvicorn\|vite'"