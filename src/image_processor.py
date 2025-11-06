"""
Image processing module for OCR text extraction from various image formats.
"""

import os
from typing import Dict, Any, Optional, List
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from loguru import logger
from pathlib import Path

class ImageProcessor:
    """
    Processes image files (TIF, TIFF, PNG, JPG, JPEG, etc.) to extract text using OCR.
    """
    
    SUPPORTED_FORMATS = {'.tif', '.tiff', '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
    
    def __init__(self, tesseract_path: Optional[str] = None, language: str = 'eng'):
        """
        Initialize the ImageProcessor.
        
        Args:
            tesseract_path: Path to tesseract executable (optional)
            language: Language for OCR (default: 'eng')
        """
        self.language = language
        
        # Set tesseract path if provided
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Try to find tesseract automatically on macOS
        if not tesseract_path and not hasattr(pytesseract.pytesseract, 'tesseract_cmd'):
            possible_paths = [
                '/usr/local/bin/tesseract',
                '/opt/homebrew/bin/tesseract',
                '/usr/bin/tesseract'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
        
        # Verify tesseract installation
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR initialized successfully (version: {version})")
        except Exception as e:
            logger.error(f"Tesseract OCR initialization failed: {e}")
            raise RuntimeError(f"Tesseract OCR not found. Please install tesseract: {e}")
    
    def is_supported(self, file_path: str) -> bool:
        """
        Check if the file format is supported for image processing.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if supported, False otherwise
        """
        return Path(file_path).suffix.lower() in self.SUPPORTED_FORMATS
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image object
        """
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to grayscale for better OCR
        image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Apply slight blur to reduce noise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Resize if image is too small (minimum 300 DPI equivalent)
        width, height = image.size
        if width < 1000 or height < 1000:
            scale_factor = max(1000 / width, 1000 / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def extract_text(self, file_path: str, preprocess: bool = True) -> Dict[str, Any]:
        """
        Extract text from image file using OCR.
        
        Args:
            file_path: Path to the image file
            preprocess: Whether to preprocess the image for better OCR
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        self._validate_file_path(file_path)
        
        try:
            # Open and load the image
            image = Image.open(file_path)
            
            # Preprocess if requested
            if preprocess:
                image = self.preprocess_image(image)
            
            # Extract text and metadata
            text = pytesseract.image_to_string(image, lang=self.language)
            ocr_data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
            
            # Build result dictionary
            result = self._build_extraction_result(text, ocr_data, image, file_path)
            
            logger.info(f"Successfully extracted text from {file_path} (confidence: {result['confidence']:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            raise

    def _validate_file_path(self, file_path: str) -> None:
        """Validate file path and format support."""
        if not self.is_supported(file_path):
            raise ValueError(f"Unsupported file format: {Path(file_path).suffix}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

    def _build_extraction_result(self, text: str, data: Dict, image: Image.Image, file_path: str) -> Dict[str, Any]:
        """Build the extraction result dictionary."""
        # Calculate average confidence
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Extract words with high confidence
        high_confidence_words = self._extract_high_confidence_words(data)
        
        return {
            'text': text.strip(),
            'confidence': avg_confidence,
            'word_count': len(text.split()),
            'high_confidence_words': high_confidence_words,
            'image_size': image.size,
            'file_size': os.path.getsize(file_path),
            'format': image.format,
            'mode': image.mode
        }

    def _extract_high_confidence_words(self, data: Dict) -> List[Dict[str, Any]]:
        """Extract words with high confidence scores."""
        high_confidence_words = []
        for i, conf in enumerate(data['conf']):
            if int(conf) > 60:  # Only include words with >60% confidence
                word = data['text'][i].strip()
                if word:
                    high_confidence_words.append({
                        'word': word,
                        'confidence': int(conf),
                        'bbox': {
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i]
                        }
                    })
        return high_confidence_words
    
    def extract_text_from_multiple_images(self, file_paths: List[str], preprocess: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Extract text from multiple image files.
        
        Args:
            file_paths: List of image file paths
            preprocess: Whether to preprocess images for better OCR
            
        Returns:
            Dictionary mapping file paths to extraction results
        """
        results = {}
        
        for file_path in file_paths:
            try:
                if self.is_supported(file_path):
                    results[file_path] = self.extract_text(file_path, preprocess)
                else:
                    logger.warning(f"Skipping unsupported file: {file_path}")
                    results[file_path] = {'error': f'Unsupported format: {Path(file_path).suffix}'}
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results[file_path] = {'error': str(e)}
        
        return results
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported image formats.
        
        Returns:
            List of supported file extensions
        """
        return list(self.SUPPORTED_FORMATS)

    def extract_text_from_pdf_image(self, pdf_page_image: Image.Image, preprocess: bool = True) -> Dict[str, Any]:
        """
        Extract text from a PDF page rendered as an image.
        
        Args:
            pdf_page_image: PIL Image object of a PDF page
            preprocess: Whether to preprocess the image for better OCR
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            # Preprocess if requested
            if preprocess:
                pdf_page_image = self.preprocess_image(pdf_page_image)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(pdf_page_image, lang=self.language)
            
            # Get confidence scores
            data = pytesseract.image_to_data(pdf_page_image, lang=self.language, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            result = {
                'text': text.strip(),
                'confidence': avg_confidence,
                'word_count': len(text.split()),
                'image_size': pdf_page_image.size,
                'mode': pdf_page_image.mode
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF page image: {e}")
            raise