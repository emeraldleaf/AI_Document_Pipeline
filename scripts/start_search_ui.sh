#!/bin/bash

###############################################################################
# START SEARCH UI - Quick Start Script
###############################################################################
#
# PURPOSE:
#   One-command script to start both backend and frontend for development.
#
# USAGE:
#   chmod +x start_search_ui.sh
#   ./start_search_ui.sh
#
# WHAT IT DOES:
#   1. Checks if dependencies are installed
#   2. Starts FastAPI backend (port 8000)
#   3. Starts React frontend (port 3000)
#   4. Opens browser to http://localhost:3000
#
# REQUIREMENTS:
#   - Python 3.11+ with dependencies installed
#   - Node.js 18+ with frontend dependencies installed
#   - PostgreSQL running with documents database
#
# AUTHOR: AI Document Pipeline Team
# LAST UPDATED: October 2025
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

# Header
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         AI Document Pipeline - Search UI Quick Start         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if running from project root
if [ ! -d "api" ] || [ ! -d "frontend" ]; then
    print_error "Error: Must run from project root directory"
    echo "  Current directory: $(pwd)"
    echo "  Expected: /path/to/AI_Document_Pipeline"
    exit 1
fi

# Check Python
print_step "Checking Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.11+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_success "Python $PYTHON_VERSION found"

# Check Node.js
print_step "Checking Node.js..."
if ! command -v node &> /dev/null; then
    print_error "Node.js not found. Please install Node.js 18+"
    exit 1
fi
NODE_VERSION=$(node --version)
print_success "Node.js $NODE_VERSION found"

# Check if FastAPI is installed
print_step "Checking backend dependencies..."
if ! python3 -c "import fastapi" &> /dev/null; then
    print_warning "FastAPI not installed. Installing dependencies..."
    pip install -r requirements.txt
    print_success "Backend dependencies installed"
else
    print_success "Backend dependencies OK"
fi

# Check if frontend dependencies are installed
print_step "Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    print_warning "Frontend dependencies not installed. Installing..."
    cd frontend
    npm install
    cd ..
    print_success "Frontend dependencies installed"
else
    print_success "Frontend dependencies OK"
fi

# Check PostgreSQL connection (optional)
print_step "Checking database connection..."
if [ -n "$DATABASE_URL" ]; then
    print_success "DATABASE_URL environment variable set"
else
    print_warning "DATABASE_URL not set. Backend may fail to start."
    echo "  Set it with: export DATABASE_URL='postgresql://user:pass@localhost:5432/documents'"
fi

echo ""
print_step "Starting services..."
echo ""

# Create log directory
mkdir -p logs

# Function to cleanup on exit
cleanup() {
    echo ""
    print_warning "Shutting down services..."

    # Kill background processes
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        print_success "Backend stopped"
    fi

    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_success "Frontend stopped"
    fi

    echo ""
    print_success "Services stopped. Logs saved in logs/ directory"
    exit 0
}

# Register cleanup function
trap cleanup SIGINT SIGTERM

# Start Backend (FastAPI)
print_step "Starting FastAPI backend on http://localhost:8000..."
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Check if backend is running
if kill -0 $BACKEND_PID 2>/dev/null; then
    print_success "Backend started (PID: $BACKEND_PID)"
    print_success "API Docs: http://localhost:8000/docs"
else
    print_error "Backend failed to start. Check logs/backend.log"
    cat logs/backend.log
    exit 1
fi

# Start Frontend (React + Vite)
print_step "Starting React frontend on http://localhost:3000..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 5

# Check if frontend is running
if kill -0 $FRONTEND_PID 2>/dev/null; then
    print_success "Frontend started (PID: $FRONTEND_PID)"
else
    print_error "Frontend failed to start. Check logs/frontend.log"
    cat logs/frontend.log
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    🎉 ALL SERVICES RUNNING                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Frontend UI:      http://localhost:3000"
echo "  Backend API:      http://localhost:8000"
echo "  API Docs:         http://localhost:8000/docs"
echo ""
echo "  Backend Logs:     logs/backend.log"
echo "  Frontend Logs:    logs/frontend.log"
echo ""
print_warning "Press Ctrl+C to stop all services"
echo ""

# Try to open browser (macOS)
if command -v open &> /dev/null; then
    sleep 2
    open http://localhost:3000
# Try to open browser (Linux)
elif command -v xdg-open &> /dev/null; then
    sleep 2
    xdg-open http://localhost:3000
fi

# Wait for user to press Ctrl+C
wait
