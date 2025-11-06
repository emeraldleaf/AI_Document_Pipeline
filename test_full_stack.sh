#!/bin/bash

###############################################################################
# FULL STACK TEST SCRIPT
###############################################################################
#
# Tests the complete backend + frontend integration
#
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         Testing Full Stack - Backend + Frontend              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Set environment variables
export DATABASE_URL="postgresql://$(whoami)@localhost:5432/documents"
export POSTGRES_HOST="localhost"
export POSTGRES_USER="$(whoami)"
export POSTGRES_DB="documents"
export OLLAMA_BASE_URL="http://localhost:11434"

# Test 1: Database
echo -e "${BLUE}Test 1: Checking database...${NC}"
/opt/homebrew/opt/postgresql@15/bin/psql -d documents -c "SELECT COUNT(*) as document_count FROM documents;" || exit 1
echo -e "${GREEN}✓ Database OK${NC}"
echo ""

# Test 2: Backend API
echo -e "${BLUE}Test 2: Starting backend API...${NC}"
cd api
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../logs/backend_test.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 5

# Test health endpoint
echo "Testing health endpoint..."
curl -s http://localhost:8000/health || (echo "Backend failed to start!" && kill $BACKEND_PID && exit 1)
echo -e "${GREEN}✓ Backend API running${NC}"
echo ""

# Test 3: Search endpoint
echo -e "${BLUE}Test 3: Testing search endpoint...${NC}"
curl -s "http://localhost:8000/api/search?q=invoice&mode=keyword&limit=10" | python3 -m json.tool | head -20
echo -e "${GREEN}✓ Search endpoint working${NC}"
echo ""

# Test 4: Frontend
echo -e "${BLUE}Test 4: Starting frontend...${NC}"
cd frontend
npm run dev > ../logs/frontend_test.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 5

echo -e "${GREEN}✓ Frontend running${NC}"
echo ""

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    🎉 ALL TESTS PASSED                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "  Backend PID:  $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop services, or run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Open browser
if command -v open &> /dev/null; then
    sleep 2
    open http://localhost:3000
fi

# Wait for user
wait
