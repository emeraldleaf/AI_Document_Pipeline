#!/bin/bash

# AI Document Classification Pipeline - Setup Script
# This script automates the installation and setup process

set -e  # Exit on error

echo "=========================================="
echo "AI Document Classification Pipeline Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}[1/6] Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.9 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Found Python $PYTHON_VERSION${NC}"

# Check if Ollama is installed
echo ""
echo -e "${BLUE}[2/6] Checking Ollama installation...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Warning: Ollama is not installed${NC}"
    echo ""
    echo "Please install Ollama:"
    echo "  macOS:  brew install ollama"
    echo "  Linux:  curl -fsSL https://ollama.com/install.sh | sh"
    echo "  Windows: Download from https://ollama.com/download"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Ollama is installed${NC}"
fi

# Check if Ollama is running
echo ""
echo -e "${BLUE}[3/6] Checking Ollama service...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama service is running${NC}"

    # List available models
    echo "Available models:"
    ollama list | tail -n +2 || echo "  (none)"
else
    echo -e "${YELLOW}Warning: Ollama service is not running${NC}"
    echo "Start it with: ollama serve"
    echo ""
    read -p "Do you want to start Ollama now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Starting Ollama in background..."
        nohup ollama serve > /dev/null 2>&1 &
        sleep 2
        echo -e "${GREEN}✓ Ollama service started${NC}"
    fi
fi

# Install Python dependencies
echo ""
echo -e "${BLUE}[4/6] Installing Python dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    python3 -m pip install --upgrade pip > /dev/null
    python3 -m pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}Error: requirements.txt not found${NC}"
    exit 1
fi

# Install package
echo ""
echo -e "${BLUE}[5/6] Installing AI Document Pipeline...${NC}"
python3 -m pip install -e . > /dev/null
echo -e "${GREEN}✓ Package installed${NC}"

# Setup environment
echo ""
echo -e "${BLUE}[6/6] Setting up environment...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${YELLOW}⚠ .env file already exists, skipping${NC}"
fi

# Initialize directories
echo ""
echo "Initializing directory structure..."
doc-classify init > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Directories created${NC}"

# Download a model if needed
echo ""
echo -e "${BLUE}Checking for AI models...${NC}"
if command -v ollama &> /dev/null; then
    if ! ollama list | grep -q "llama3.2"; then
        echo -e "${YELLOW}No llama3.2 model found${NC}"
        read -p "Do you want to download llama3.2:3b (~2GB)? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Downloading model (this may take a few minutes)..."
            ollama pull llama3.2:3b
            echo -e "${GREEN}✓ Model downloaded${NC}"
        fi
    else
        echo -e "${GREEN}✓ llama3.2 model is available${NC}"
    fi
fi

# Final checks
echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Place documents in: documents/input/"
echo "  2. Run classification: doc-classify classify documents/input"
echo ""
echo "Commands:"
echo "  doc-classify check      # Verify setup"
echo "  doc-classify config     # View configuration"
echo "  doc-classify classify   # Classify documents"
echo ""
echo "Documentation:"
echo "  README.md               # Full documentation"
echo "  QUICKSTART.md          # Quick start guide"
echo "  examples/sample_usage.py  # Python examples"
echo ""

# Verify installation
if command -v doc-classify &> /dev/null; then
    echo -e "${GREEN}✓ Installation verified successfully${NC}"
    echo ""
    echo "Test the installation:"
    echo "  doc-classify check"
else
    echo -e "${YELLOW}⚠ Command 'doc-classify' not found in PATH${NC}"
    echo "You may need to add it to your PATH or use: python -m src.cli"
fi

echo ""
echo "Happy classifying! 🚀"
