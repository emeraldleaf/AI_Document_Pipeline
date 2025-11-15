#!/bin/bash
# filepath: stop_servers.sh

echo "🛑 Stopping all servers..."

# Kill API server
pkill -f "uvicorn.*api.main" 2>/dev/null && echo "✅ API server stopped" || echo "❌ API server not running"

# Kill frontend server
pkill -f "vite" 2>/dev/null && echo "✅ Frontend server stopped" || echo "❌ Frontend server not running"

echo "🧹 Cleanup complete"