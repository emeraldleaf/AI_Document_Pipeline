#!/bin/bash

# OCR Setup Script for AI Document Pipeline
# This script installs Tesseract OCR and Python dependencies

set -e  # Exit on any error

echo "🚀 Setting up OCR functionality for AI Document Pipeline"
echo "======================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo "🔍 Detected OS: $OS"

# Install Tesseract OCR
echo ""
echo "📦 Installing Tesseract OCR..."

case $OS in
    "macos")
        if command_exists brew; then
            echo "📥 Installing Tesseract via Homebrew..."
            brew install tesseract
            
            # Install additional language packs
            echo "🌐 Installing additional language packs..."
            brew install tesseract-lang
        else
            echo "❌ Homebrew not found. Please install Homebrew first:"
            echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
        ;;
    "linux")
        echo "📥 Installing Tesseract via apt..."
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr
        
        # Install additional language packs
        echo "🌐 Installing additional language packs..."
        sudo apt-get install -y tesseract-ocr-eng tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-deu
        
        # Install poppler-utils for PDF to image conversion
        echo "📥 Installing poppler-utils for PDF processing..."
        sudo apt-get install -y poppler-utils
        ;;
    *)
        echo "❌ Unsupported OS. Please install Tesseract manually:"
        echo "   Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        echo "   Other: https://tesseract-ocr.github.io/tessdoc/Installation.html"
        exit 1
        ;;
esac

# Verify Tesseract installation
echo ""
echo "🔍 Verifying Tesseract installation..."
if command_exists tesseract; then
    TESSERACT_VERSION=$(tesseract --version | head -n1)
    echo "✅ Tesseract installed: $TESSERACT_VERSION"
    
    # Show available languages
    echo "🌐 Available languages:"
    tesseract --list-langs | tail -n +2 | head -10
else
    echo "❌ Tesseract installation failed"
    exit 1
fi

# Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. It's recommended to use one."
    echo "   You can create one with: python -m venv venv && source venv/bin/activate"
fi

# Install requirements
echo "📥 Installing Python packages..."
pip install --upgrade pip

# Install OCR-specific dependencies
pip install Pillow>=10.0.0
pip install pytesseract>=0.3.10
pip install pdf2image>=1.16.3

# Install other requirements if file exists
if [ -f "requirements.txt" ]; then
    echo "📥 Installing from requirements.txt..."
    pip install -r requirements.txt
else
    echo "⚠️  requirements.txt not found. Installing minimal dependencies..."
    pip install loguru pathlib2
fi

# Test the installation
echo ""
echo "🧪 Testing OCR installation..."

python3 << 'EOF'
import sys

def test_imports():
    try:
        from PIL import Image
        print("✅ Pillow (PIL) imported successfully")
    except ImportError as e:
        print(f"❌ Pillow import failed: {e}")
        return False
    
    try:
        import pytesseract
        print("✅ pytesseract imported successfully")
    except ImportError as e:
        print(f"❌ pytesseract import failed: {e}")
        return False
    
    try:
        from pdf2image import convert_from_path
        print("✅ pdf2image imported successfully")
    except ImportError as e:
        print(f"❌ pdf2image import failed: {e}")
        return False
    
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract binary accessible (version: {version})")
    except Exception as e:
        print(f"❌ Tesseract binary test failed: {e}")
        return False
    
    return True

if test_imports():
    print("\n🎉 OCR installation successful!")
else:
    print("\n❌ OCR installation has issues")
    sys.exit(1)
EOF

# Create sample test script
echo ""
echo "📝 Creating test script..."

cat > test_ocr_simple.py << 'EOF'
#!/usr/bin/env python3
"""Simple OCR test script."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_ocr():
    try:
        from image_processor import ImageProcessor
        
        processor = ImageProcessor()
        print(f"✅ OCR processor initialized")
        print(f"📋 Supported formats: {', '.join(processor.get_supported_formats())}")
        
        print("\n💡 To test with actual images:")
        print("   1. Place image files in documents/input/")
        print("   2. Run: python scripts/test_ocr.py")
        
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        print("💡 Make sure you're in the project root directory")

if __name__ == "__main__":
    test_ocr()
EOF

chmod +x test_ocr_simple.py

echo ""
echo "🎉 OCR Setup Complete!"
echo "======================"
echo ""
echo "✅ Tesseract OCR installed and configured"
echo "✅ Python dependencies installed"
echo "✅ Test script created (test_ocr_simple.py)"
echo ""
echo "📋 Next steps:"
echo "   1. Test the installation: python test_ocr_simple.py"
echo "   2. Place sample images in documents/input/"
echo "   3. Run full test suite: python scripts/test_ocr.py"
echo ""
echo "🔧 Supported image formats:"
echo "   TIF, TIFF, PNG, JPG, JPEG, BMP, GIF, WebP"
echo ""
echo "📚 For image-based PDFs, OCR will be used automatically"