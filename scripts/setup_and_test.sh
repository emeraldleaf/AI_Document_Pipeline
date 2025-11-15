#!/bin/bash

# AI Document Pipeline - Local Setup and Test Script
# This script will help you get everything running

set -e  # Exit on error

echo "🚀 AI Document Pipeline - Local Setup"
echo "======================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found: Python $PYTHON_VERSION"

if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "   ✅ Python version is compatible (>=3.11)"
else
    echo "   ❌ Python 3.11+ is required"
    exit 1
fi
echo ""

# Check Tesseract
echo "📋 Checking Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n 1)
    echo "   ✅ $TESSERACT_VERSION"
else
    echo "   ❌ Tesseract not found. Install with: brew install tesseract"
    exit 1
fi
echo ""

# Check Ollama
echo "📋 Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "   ✅ Ollama is installed"
    if pgrep -x "ollama" > /dev/null; then
        echo "   ✅ Ollama service is running"
    else
        echo "   ⚠️  Ollama is installed but not running"
        echo "   💡 Start it in another terminal: ollama serve"
    fi
else
    echo "   ❌ Ollama not found"
    echo "   💡 Install with: brew install ollama"
    echo "   💡 Then run: ollama serve"
    echo "   💡 And pull model: ollama pull llama3.2:3b"
    exit 1
fi
echo ""

# Check Docker (optional)
echo "📋 Checking Docker (optional for search)..."
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        echo "   ✅ Docker is installed and running"
    else
        echo "   ⚠️  Docker is installed but not running"
        echo "   💡 Start Docker Desktop if you want search features"
    fi
else
    echo "   ℹ️  Docker not found (only needed for search features)"
fi
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if pip3 install -e . > /dev/null 2>&1; then
    echo "   ✅ Dependencies installed successfully"
else
    echo "   ⚠️  Installation had warnings, trying requirements.txt..."
    pip3 install -r requirements.txt
    echo "   ✅ Dependencies installed"
fi
echo ""

# Set up environment
echo "⚙️  Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   ✅ Created .env file from template"
else
    echo "   ℹ️  .env file already exists"
fi
echo ""

# Initialize directories
echo "📁 Initializing directory structure..."
mkdir -p documents/input documents/output documents/temp
echo "   ✅ Created directories"
echo ""

# Create test document
echo "📄 Creating test document..."
cat > documents/input/test-invoice.txt << 'EOF'
INVOICE

Invoice Number: INV-2024-001
Date: December 20, 2024

Bill To:
Acme Corporation
123 Business St
San Francisco, CA 94102

Description: Consulting Services - Q4 2024
Amount: $2,500.00

Payment Terms: Net 30
Due Date: January 19, 2025

Thank you for your business!
EOF
echo "   ✅ Created test-invoice.txt"
echo ""

# Test configuration
echo "🧪 Testing configuration..."
python3 << 'PYEOF'
try:
    from src.domain import load_configuration
    config = load_configuration()
    print("   ✅ Configuration loaded")
    print(f"   📂 Input: {config.input_directory}")
    print(f"   📂 Output: {config.output_directory}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)
PYEOF
echo ""

# Summary
echo "✨ Setup Complete!"
echo ""
echo "Next Steps:"
echo "==========="
echo ""
echo "1. Make sure Ollama is running:"
echo "   $ ollama serve"
echo ""
echo "2. Pull the AI model (in another terminal):"
echo "   $ ollama pull llama3.2:3b"
echo ""
echo "3. Test classification:"
echo "   $ python3 -m src.cli classify documents/input/"
echo ""
echo "   OR if installed with pip:"
echo "   $ doc-classify classify documents/input/"
echo ""
echo "4. Check results:"
echo "   $ ls -R documents/output/"
echo ""
echo "📚 Documentation: LOCAL_SETUP_GUIDE.md"
echo ""
