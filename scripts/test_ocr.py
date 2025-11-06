#!/usr/bin/env python3
"""
Test script for OCR image processing functionality.
"""
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_ocr_installation():
    """Test if OCR dependencies are properly installed."""
    print("🔍 Testing OCR Installation...")
    
    # Test PIL/Pillow
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        print("✅ Pillow (PIL) is installed")
    except ImportError as e:
        print(f"❌ Pillow (PIL) not found: {e}")
        return False
    
    # Test pytesseract
    try:
        import pytesseract
        print("✅ pytesseract is installed")
    except ImportError as e:
        print(f"❌ pytesseract not found: {e}")
        return False
    
    # Test tesseract binary
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract binary found (version: {version})")
    except Exception as e:
        print(f"❌ Tesseract binary not found: {e}")
        print("💡 Install tesseract:")
        print("   macOS: brew install tesseract")
        print("   Ubuntu: sudo apt-get install tesseract-ocr")
        return False
    
    # Test pdf2image
    try:
        from pdf2image import convert_from_path
        print("✅ pdf2image is installed")
    except ImportError as e:
        print(f"❌ pdf2image not found: {e}")
        return False
    
    return True

def test_image_processor():
    """Test the ImageProcessor class."""
    print("\n🖼️  Testing ImageProcessor...")
    
    try:
        from image_processor import ImageProcessor
        
        # Initialize processor
        processor = ImageProcessor()
        print(f"✅ ImageProcessor initialized successfully")
        print(f"📋 Supported formats: {', '.join(processor.get_supported_formats())}")
        
        return True
        
    except Exception as e:
        print(f"❌ ImageProcessor test failed: {e}")
        return False

def test_extractors():
    """Test the updated extractors with OCR support."""
    print("\n📄 Testing Extractors...")
    
    try:
        from extractors import ExtractionService, ImageExtractor, PDFExtractor
        
        # Test extraction service initialization
        service = ExtractionService()
        print(f"✅ ExtractionService initialized with {len(service.extractors)} extractors")
        
        # List available extractors
        for i, extractor in enumerate(service.extractors):
            print(f"   {i+1}. {extractor.__class__.__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Extractors test failed: {e}")
        return False

def test_sample_processing():
    """Test processing sample files if available."""
    print("\n📁 Testing Sample Processing...")
    
    # Check for sample files
    samples_dir = Path(__file__).parent.parent / 'documents' / 'input'
    
    if not samples_dir.exists():
        print(f"📁 Sample directory not found: {samples_dir}")
        print("💡 Create sample files in documents/input/ to test processing")
        return True
    
    try:
        from extractors import ExtractionService
        
        service = ExtractionService()
        
        # Find image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.gif', '.webp'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(samples_dir.glob(f'*{ext}'))
            image_files.extend(samples_dir.glob(f'*{ext.upper()}'))
        
        if image_files:
            print(f"🔍 Found {len(image_files)} image files to test")
            
            for image_file in image_files[:3]:  # Test first 3 files
                print(f"\n📄 Testing: {image_file.name}")
                try:
                    result = service.extract(image_file)
                    if result:
                        print(f"   ✅ Extracted {len(result.text)} characters")
                        if result.text.strip():
                            preview = result.text[:100] + "..." if len(result.text) > 100 else result.text
                            print(f"   📖 Preview: {preview}")
                        else:
                            print(f"   ⚠️  No text found")
                    else:
                        print(f"   ❌ Extraction failed")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        else:
            print("📁 No image files found in samples directory")
        
        # Test PDF files for OCR fallback
        pdf_files = list(samples_dir.glob('*.pdf'))
        if pdf_files:
            print(f"\n🔍 Found {len(pdf_files)} PDF files to test")
            
            for pdf_file in pdf_files[:2]:  # Test first 2 PDFs
                print(f"\n📄 Testing PDF: {pdf_file.name}")
                try:
                    result = service.extract(pdf_file)
                    if result:
                        print(f"   ✅ Extracted {len(result.text)} characters from {result.metadata.page_count} pages")
                        if "[No text found]" in result.text or "[Image-based PDF]" in result.text:
                            print(f"   🖼️  PDF processed with OCR")
                    else:
                        print(f"   ❌ PDF extraction failed")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sample processing test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 OCR Functionality Test Suite")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: OCR Installation
    if not test_ocr_installation():
        all_passed = False
        print("\n❌ OCR installation test failed. Please install missing dependencies.")
        return
    
    # Test 2: ImageProcessor
    if not test_image_processor():
        all_passed = False
    
    # Test 3: Extractors
    if not test_extractors():
        all_passed = False
    
    # Test 4: Sample Processing
    if not test_sample_processing():
        all_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! OCR functionality is ready.")
        print("\n💡 Usage tips:")
        print("   - Place images in documents/input/ for processing")
        print("   - Supported formats: PNG, JPG, TIFF, BMP, GIF, WebP")
        print("   - Image-based PDFs will automatically use OCR")
        print("   - For better OCR accuracy, use high-resolution images (>300 DPI)")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()