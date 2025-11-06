#!/usr/bin/env python3
"""
Example usage of OCR functionality in the AI Document Pipeline.
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def example_image_processing():
    """Example of processing image files with OCR."""
    print("🖼️  Image Processing Example")
    print("=" * 40)
    
    try:
        from image_processor import ImageProcessor
        
        # Initialize the OCR processor
        processor = ImageProcessor()
        print(f"✅ OCR processor initialized")
        print(f"📋 Supported formats: {', '.join(processor.get_supported_formats())}")
        
        # Example: Process a single image
        image_path = "documents/input/sample_document.png"
        
        if Path(image_path).exists():
            print(f"\n📄 Processing image: {image_path}")
            
            result = processor.extract_text(image_path)
            
            print(f"📝 Extracted {result['word_count']} words")
            print(f"🎯 Confidence: {result['confidence']:.1f}%")
            print(f"📏 Image size: {result['image_size']}")
            
            if result['text']:
                print(f"\n📖 Extracted text:")
                print("-" * 40)
                print(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
            
        else:
            print(f"📁 Sample image not found: {image_path}")
            print("💡 Place a sample image in documents/input/ to test")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def example_document_extraction():
    """Example of using the enhanced document extraction service."""
    print("\n📚 Document Extraction Example")
    print("=" * 40)
    
    try:
        from extractors import ExtractionService
        
        # Initialize the extraction service
        service = ExtractionService()
        print(f"✅ Extraction service initialized with {len(service.extractors)} extractors")
        
        # List available extractors
        for i, extractor in enumerate(service.extractors):
            print(f"   {i+1}. {extractor.__class__.__name__}")
        
        # Example: Process documents from input directory
        input_dir = Path("documents/input")
        
        if input_dir.exists():
            # Find all supported files
            supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.gif', '.webp', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md'}
            
            files = []
            for ext in supported_extensions:
                files.extend(input_dir.glob(f'*{ext}'))
                files.extend(input_dir.glob(f'*{ext.upper()}'))
            
            if files:
                print(f"\n🔍 Found {len(files)} supported files:")
                
                for file_path in files[:5]:  # Process first 5 files
                    print(f"\n📄 Processing: {file_path.name}")
                    
                    try:
                        result = service.extract(file_path)
                        
                        if result:
                            print(f"   ✅ Success: {len(result.text)} characters extracted")
                            print(f"   📑 Type: {result.metadata.file_type}")
                            if hasattr(result.metadata, 'page_count') and result.metadata.page_count:
                                print(f"   📄 Pages: {result.metadata.page_count}")
                            
                            # Show preview of extracted text
                            if result.text.strip():
                                preview = result.text[:150] + "..." if len(result.text) > 150 else result.text
                                print(f"   📖 Preview: {preview}")
                        else:
                            print(f"   ❌ Extraction failed")
                    
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
            else:
                print(f"📁 No supported files found in {input_dir}")
        else:
            print(f"📁 Input directory not found: {input_dir}")
            print("💡 Create documents/input/ and add some files to test")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def example_pdf_with_ocr():
    """Example of PDF processing with OCR fallback."""
    print("\n📄 PDF with OCR Example")
    print("=" * 40)
    
    try:
        from extractors import PDFExtractor
        
        # Initialize PDF extractor with OCR support
        extractor = PDFExtractor()
        print("✅ PDF extractor with OCR support initialized")
        
        # Example PDF processing
        pdf_path = Path("documents/input/sample.pdf")
        
        if pdf_path.exists():
            print(f"\n📄 Processing PDF: {pdf_path.name}")
            
            result = extractor.extract(pdf_path)
            
            if result:
                print(f"   ✅ Success: {len(result.text)} characters extracted")
                print(f"   📑 Pages: {result.metadata.page_count}")
                
                # Check if OCR was used
                if "[Image-based PDF]" in result.text or "[No text found]" in result.text:
                    print("   🖼️  OCR was used for this PDF")
                else:
                    print("   📝 Text was extracted directly")
                
                # Show preview
                if result.text.strip():
                    preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
                    print(f"   📖 Preview: {preview}")
        else:
            print(f"📁 Sample PDF not found: {pdf_path}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run all examples."""
    print("🧪 OCR Functionality Examples")
    print("=" * 50)
    
    # Example 1: Direct image processing
    example_image_processing()
    
    # Example 2: Document extraction service
    example_document_extraction()
    
    # Example 3: PDF with OCR
    example_pdf_with_ocr()
    
    print("\n" + "=" * 50)
    print("🎉 Examples completed!")
    print("\n💡 Tips for better OCR results:")
    print("   • Use high-resolution images (>300 DPI)")
    print("   • Ensure good contrast between text and background")
    print("   • Use clean, unrotated images")
    print("   • TIFF format often works best for scanned documents")

if __name__ == "__main__":
    main()