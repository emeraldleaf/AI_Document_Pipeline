#!/bin/bash

###############################################################################
# FRONTEND SETUP SCRIPT - Document Search UI
###############################################################################
#
# PURPOSE:
#   Quick setup script to install all dependencies and verify configuration.
#
# USAGE:
#   chmod +x setup.sh
#   ./setup.sh
#
# WHAT IT DOES:
#   1. Checks if Node.js is installed
#   2. Installs npm dependencies
#   3. Verifies TypeScript configuration
#   4. Shows next steps
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
echo "║         Document Search UI - Frontend Setup                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check Node.js
print_step "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    print_error "Node.js not found!"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
print_success "Node.js $NODE_VERSION found"

# Check npm
print_step "Checking npm..."
if ! command -v npm &> /dev/null; then
    print_error "npm not found!"
    exit 1
fi

NPM_VERSION=$(npm --version)
print_success "npm $NPM_VERSION found"

# Install dependencies
print_step "Installing dependencies..."
echo "This may take a few minutes..."
npm install

if [ $? -eq 0 ]; then
    print_success "Dependencies installed successfully"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Verify TypeScript
print_step "Verifying TypeScript configuration..."
if [ -f "node_modules/.bin/tsc" ]; then
    print_success "TypeScript installed"
else
    print_warning "TypeScript not found in node_modules"
fi

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    print_step "Creating .env.local from template..."
    cp .env.example .env.local
    print_success ".env.local created"
    print_warning "Please edit .env.local and set VITE_API_URL if needed"
else
    print_success ".env.local already exists"
fi

# Success message
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    ✅ SETUP COMPLETE                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "  1. Make sure the backend is running:"
echo "     cd ../api && uvicorn main:app --reload"
echo ""
echo "  2. Start the development server:"
echo "     npm run dev"
echo ""
echo "  3. Open your browser to:"
echo "     http://localhost:3000"
echo ""
print_success "Happy coding! 🚀"
echo ""
