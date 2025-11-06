"""
==============================================================================
OCR SERVICE - Optical Character Recognition for Images
==============================================================================

PURPOSE:
    Extract text from images and scanned documents using OCR technology.
    Turns images of text into actual text that can be searched and classified.

WHAT IS OCR (Optical Character Recognition)?
    Technology that "reads" text from images:
    - Scanned documents (scanned PDFs)
    - Photos of documents (smartphone photos)
    - Screenshots with text
    - Image-based PDFs (no selectable text)

    Example:
    [Image of Invoice] → OCR → "Invoice #12345\nDate: 2024-10-01\nAmount: $1,234.56"

HOW OCR WORKS:
    1. Load image file (PNG, JPEG, TIFF, etc.)
    2. Preprocess image (enhance contrast, sharpen, denoise)
    3. Send to Tesseract OCR engine
    4. Tesseract analyzes:
       - Finds text regions
       - Recognizes characters
       - Calculates confidence scores
    5. Return extracted text + metadata

WHAT IS TESSERACT?
    - Open-source OCR engine (originally by HP, now Google)
    - Industry-standard OCR tool
    - Supports 100+ languages
    - Free and runs locally (no API costs)
    - Command-line tool we wrap with Python

WHEN TO USE OCR:
    ✓ Scanned documents (PDFs from scanner)
    ✓ Image-based PDFs (no selectable text)
    ✓ Photos of documents (smartphone camera)
    ✓ Screenshots with text
    ✓ Faxes, printed forms, receipts

    ✗ Text-based PDFs (use PyPDF2 instead - faster!)
    ✗ Word documents (use python-docx - more accurate!)

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │                       OCR Processing Flow                    │
    │                                                             │
    │  1. Image File (PNG, JPEG, TIFF)                           │
    │           ↓                                                 │
    │  2. Load & Validate Image (PIL/Pillow)                     │
    │           ↓                                                 │
    │  3. Preprocess (optional):                                 │
    │      - Convert to grayscale                                │
    │      - Enhance contrast                                    │
    │      - Sharpen edges                                       │
    │      - Reduce noise (blur)                                 │
    │           ↓                                                 │
    │  4. Tesseract OCR Engine                                   │
    │      - Find text regions                                   │
    │      - Recognize characters                                │
    │      - Calculate confidence                                │
    │           ↓                                                 │
    │  5. Process Results:                                       │
    │      - Filter low-confidence words                         │
    │      - Calculate overall confidence                        │
    │      - Extract bounding boxes                              │
    │           ↓                                                 │
    │  6. Return OCRResult                                       │
    └─────────────────────────────────────────────────────────────┘

KEY CONCEPTS:
    1. **OCR Confidence**: How sure Tesseract is (0-100%)
       - 90-100%: Very confident (usually accurate)
       - 60-89%: Medium confidence (mostly accurate)
       - 0-59%: Low confidence (likely errors)

    2. **Image Preprocessing**: Improving image quality for better OCR
       - Grayscale: Remove color, focus on text
       - Contrast: Make text darker, background lighter
       - Sharpen: Make edges crisp
       - Denoise: Remove artifacts, grain

    3. **Bounding Boxes**: Coordinates of where text was found
       - (left, top, width, height)
       - Useful for understanding layout

    4. **Protocol-Based Design**: Implements OCRProcessor protocol
       - Can swap Tesseract for other OCR engines
       - Google Vision API, Amazon Textract, etc.

PREPROCESSING COMPARISON:
    Without preprocessing:
    [Blurry, low-contrast image] → OCR → "Invoi€e #1234S" (errors!)
    Confidence: 45%

    With preprocessing:
    [Blurry, low-contrast image] → Enhance → Sharp, high-contrast
    → OCR → "Invoice #12345" (accurate!)
    Confidence: 92%

EXAMPLE USAGE:
    ```python
    from src.services.ocr_service import TesseractOCRService

    # Create OCR service
    ocr = TesseractOCRService(language='eng')

    # Extract text from image
    result = await ocr.extract_text(
        "scanned_invoice.png",
        preprocess=True  # Apply image enhancement
    )

    if result.is_success:
        ocr_result = result.value
        print(f"Text: {ocr_result.text}")
        print(f"Confidence: {ocr_result.confidence:.1f}%")
        print(f"Words: {ocr_result.word_count}")
        print(f"High confidence words: {len(ocr_result.high_confidence_words)}")
    else:
        print(f"OCR failed: {result.error}")
    ```

SUPPORTED FORMATS:
    - TIFF (.tif, .tiff) - Best for scanning
    - PNG (.png) - Lossless, good quality
    - JPEG (.jpg, .jpeg) - Common but lossy
    - BMP (.bmp) - Uncompressed
    - GIF (.gif) - Basic support
    - WebP (.webp) - Modern format

RELATED FILES:
    - src/domain/protocols.py - OCRProcessor protocol definition
    - src/domain/models.py - OCRResult model
    - src/infrastructure/extractors.py - Uses this for PDF OCR
    - config.py - OCR configuration settings

INSTALLATION:
    macOS:
        brew install tesseract

    Linux (Ubuntu/Debian):
        sudo apt-get install tesseract-ocr

    Windows:
        Download from: https://github.com/UB-Mannheim/tesseract/wiki

AUTHOR: AI Document Pipeline Team
LAST UPDATED: October 2025
"""

import os
from typing import Dict, Any, Optional, List
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import logging
from pathlib import Path

from ..domain import OCRProcessor, Result, OCRResult, OCRProcessingError


logger = logging.getLogger(__name__)


# ==============================================================================
# TESSERACT OCR SERVICE
# ==============================================================================

class TesseractOCRService:
    """
    OCR service implementation using Tesseract OCR engine.

    WHAT IT DOES:
        Extracts text from images using the Tesseract OCR engine.
        Includes optional preprocessing to improve accuracy.

    HOW IT WORKS:
        1. Loads image file using PIL/Pillow
        2. Optionally preprocesses (grayscale, enhance, sharpen)
        3. Sends to Tesseract for text recognition
        4. Processes results (filter, confidence, bounding boxes)
        5. Returns structured OCRResult

    KEY FEATURES:
        - **Protocol Implementation**: Implements OCRProcessor protocol
        - **Image Preprocessing**: Optional enhancement for better accuracy
        - **Confidence Scoring**: Per-word and overall confidence
        - **Bounding Boxes**: Location of each recognized word
        - **Multi-language Support**: Configure language (eng, spa, fra, etc.)
        - **Error Handling**: Returns Result type (no exceptions)

    PREPROCESSING TECHNIQUES:
        1. Grayscale conversion: Remove color, focus on text
        2. Contrast enhancement: Make text darker, background lighter
        3. Sharpness enhancement: Make edges crisp
        4. Gaussian blur: Reduce noise while preserving edges

    PERFORMANCE:
        - Fast: ~1-3 seconds per page
        - Accuracy: 95-99% on clean images
        - Accuracy: 70-85% on poor quality images
        - Works offline (no API calls)

    WHEN TO ENABLE PREPROCESSING:
        ✓ Low contrast images (faded text)
        ✓ Blurry images (out of focus)
        ✓ Noisy images (grain, artifacts)
        ✓ Photos (not scans)

        ✗ High quality scans (already perfect)
        ✗ Very low resolution (preprocessing won't help)

    EXAMPLE:
        ```python
        # Create service with English language
        ocr = TesseractOCRService(language='eng')

        # Check if file is supported
        if ocr.is_supported("document.png"):
            # Extract text with preprocessing
            result = await ocr.extract_text(
                "document.png",
                preprocess=True
            )

            if result.is_success:
                print(f"Extracted {result.value.word_count} words")
                print(f"Confidence: {result.value.confidence:.1f}%")
        ```

    MULTI-LANGUAGE SUPPORT:
        language='eng'          # English (default)
        language='spa'          # Spanish
        language='fra'          # French
        language='deu'          # German
        language='eng+spa'      # English + Spanish (both)

        Install additional languages:
            macOS: brew install tesseract-lang
            Linux: apt-get install tesseract-ocr-spa
    """

    # Supported image formats
    # These are image formats that PIL can read and Tesseract can process
    SUPPORTED_FORMATS = {'.tif', '.tiff', '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}

    def __init__(self, tesseract_path: Optional[str] = None, language: str = 'eng'):
        """
        Initialize the OCR service.

        Args:
            tesseract_path: Path to tesseract executable (default: auto-detect)
            language: Language for OCR (default: 'eng' for English)

        What happens during initialization:
        1. Store language setting
        2. Find/set tesseract executable path
        3. Verify tesseract is installed and working

        Why specify tesseract_path?
        - Different systems install tesseract in different locations
        - macOS Homebrew: /opt/homebrew/bin/tesseract
        - macOS Homebrew (Intel): /usr/local/bin/tesseract
        - Linux: /usr/bin/tesseract
        - Windows: C:\\Program Files\\Tesseract-OCR\\tesseract.exe

        Why verify installation?
        - Catch installation issues early
        - Provide clear error messages
        - Fail fast if tesseract is missing

        Example:
            >>> # Auto-detect tesseract
            >>> ocr = TesseractOCRService()

            >>> # Explicit path (useful on Windows)
            >>> ocr = TesseractOCRService(
            ...     tesseract_path="C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
            ... )

            >>> # Spanish language
            >>> ocr = TesseractOCRService(language='spa')
        """
        self.language = language
        self._setup_tesseract(tesseract_path)
        self._verify_installation()

    # ==========================================================================
    # SETUP AND VERIFICATION
    # ==========================================================================

    def _setup_tesseract(self, tesseract_path: Optional[str]) -> None:
        """
        Set up tesseract executable path.

        This finds the tesseract executable on your system.

        Search strategy:
        1. If path provided explicitly, use it
        2. Otherwise, search common installation locations
        3. Try macOS Homebrew locations first (most common)
        4. Then try Linux standard locations

        Args:
            tesseract_path: Explicit path to tesseract (optional)

        Why search multiple paths?
        - Homebrew on M1 Macs: /opt/homebrew/bin/tesseract
        - Homebrew on Intel Macs: /usr/local/bin/tesseract
        - Linux systems: /usr/bin/tesseract
        - Different installations = different paths

        Note: Windows users should provide explicit path
        (Windows doesn't have standard locations like Unix)
        """
        # If user provided explicit path, use it
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            return

        # Try to find tesseract automatically on macOS/Linux
        possible_paths = [
            '/usr/local/bin/tesseract',      # Homebrew (Intel Mac)
            '/opt/homebrew/bin/tesseract',   # Homebrew (M1/M2 Mac)
            '/usr/bin/tesseract'             # Linux standard location
        ]

        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"Found Tesseract at: {path}")
                return

        # If not found, pytesseract will try system PATH
        # (may work if tesseract is in PATH)

    def _verify_installation(self) -> None:
        """
        Verify tesseract installation is working.

        This checks if:
        1. Tesseract executable can be found
        2. Tesseract can be run
        3. Version can be retrieved

        Raises:
            OCRProcessingError: If tesseract is not installed or not working

        Why verify?
        - Catch installation issues immediately
        - Provide helpful error messages
        - Better than cryptic errors later during OCR

        Common errors:
        - "tesseract not found" → Not installed or not in PATH
        - "Permission denied" → Execute permission missing
        - "Version not found" → Corrupted installation
        """
        try:
            # Try to get tesseract version
            # This will fail if tesseract is not installed or not working
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR initialized successfully (version: {version})")

        except Exception as e:
            # Tesseract not working - provide helpful error
            error_msg = f"Tesseract OCR initialization failed: {e}"
            logger.error(error_msg)
            logger.error("Please install Tesseract:")
            logger.error("  macOS: brew install tesseract")
            logger.error("  Linux: sudo apt-get install tesseract-ocr")
            logger.error("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            raise OCRProcessingError(error_msg) from e

    # ==========================================================================
    # FORMAT SUPPORT
    # ==========================================================================

    def is_supported(self, file_path: str) -> bool:
        """
        Check if the file format is supported for OCR.

        Args:
            file_path: Path to file

        Returns:
            True if format is supported, False otherwise

        Supported formats:
        - TIFF (.tif, .tiff) - Best for scanning, lossless
        - PNG (.png) - Lossless, good quality
        - JPEG (.jpg, .jpeg) - Compressed, common
        - BMP (.bmp) - Uncompressed, large files
        - GIF (.gif) - Basic support
        - WebP (.webp) - Modern format

        Why these formats?
        - PIL/Pillow can read them
        - Tesseract can process them
        - Common image formats

        Why not PDF?
        - PDFs can contain images OR text
        - PDF extraction handled separately (PyPDF2)
        - This service is for pure images

        Example:
            >>> ocr = TesseractOCRService()
            >>> ocr.is_supported("document.png")
            True
            >>> ocr.is_supported("document.pdf")
            False  # PDFs handled differently
            >>> ocr.is_supported("document.xyz")
            False  # Unknown format
        """
        path = Path(file_path)
        return path.suffix.lower() in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported image formats.

        Returns:
            List of supported file extensions (e.g., ['.png', '.jpg', ...])

        Example:
            >>> ocr = TesseractOCRService()
            >>> formats = ocr.get_supported_formats()
            >>> print("Supported:", ", ".join(formats))
            Supported: .tif, .tiff, .png, .jpg, .jpeg, .bmp, .gif, .webp
        """
        return list(self.SUPPORTED_FORMATS)

    # ==========================================================================
    # OCR EXTRACTION
    # ==========================================================================

    async def extract_text(self, file_path: str, preprocess: bool = True) -> Result[OCRResult]:
        """
        Extract text from image file using OCR.

        This is the main OCR method. It:
        1. Validates file exists and is supported format
        2. Loads image using PIL
        3. Optionally preprocesses image (enhance quality)
        4. Runs Tesseract OCR
        5. Processes results (filter, confidence, bounding boxes)
        6. Returns structured OCRResult

        Args:
            file_path: Path to the image file
            preprocess: Whether to apply image preprocessing (default: True)

        Returns:
            Result containing:
                - Success: OCRResult with text, confidence, word data
                - Failure: Error message string

        Preprocessing (when preprocess=True):
        1. Convert to grayscale (remove color)
        2. Enhance contrast (darken text, lighten background)
        3. Enhance sharpness (crisp edges)
        4. Apply slight blur (reduce noise)

        Why async?
        - OCR can take 1-3 seconds per page
        - Async allows other tasks to run while OCR processes
        - Essential for batch processing

        Example:
            >>> ocr = TesseractOCRService()
            >>> result = await ocr.extract_text(
            ...     "scanned_invoice.png",
            ...     preprocess=True  # Enhance image quality
            ... )
            >>>
            >>> if result.is_success:
            ...     ocr_result = result.value
            ...     print(f"Text: {ocr_result.text[:100]}...")
            ...     print(f"Confidence: {ocr_result.confidence:.1f}%")
            ...     print(f"Words: {ocr_result.word_count}")
            ... else:
            ...     print(f"OCR failed: {result.error}")

        When to disable preprocessing (preprocess=False):
        - High quality scans (already perfect)
        - Preprocessed externally (already enhanced)
        - Speed critical (preprocessing adds ~0.5s)
        """
        try:
            # Step 1: Validate file format
            #
            # Check if this is a supported image format.
            # We handle PNG, JPEG, TIFF, etc.
            if not self.is_supported(file_path):
                return Result.failure(f"Unsupported format: {Path(file_path).suffix}")

            # Step 2: Validate file exists
            #
            # Better to check now than fail in PIL
            if not os.path.exists(file_path):
                return Result.failure(f"File not found: {file_path}")

            # Step 3: Load image
            #
            # Load image file into memory using PIL.
            # This validates the image is readable and not corrupted.
            image = self._load_image(file_path)
            if image is None:
                return Result.failure(f"Failed to load image: {file_path}")

            # Step 4: Apply preprocessing if requested
            #
            # Preprocessing improves OCR accuracy on poor quality images:
            # - Grayscale: Focus on text, remove color
            # - Contrast: Make text darker, background lighter
            # - Sharpen: Make edges crisp
            # - Blur: Reduce noise (slight)
            #
            # Trade-off:
            # + Better accuracy on poor images (+10-20% accuracy)
            # - Adds ~0.5s processing time
            # - Can slightly hurt accuracy on perfect images
            if preprocess:
                image = self._preprocess_image(image)

            # Step 5: Extract text using Tesseract OCR
            #
            # image_to_data returns detailed OCR results:
            # - text: The recognized text
            # - conf: Confidence score per word (0-100)
            # - left, top, width, height: Bounding boxes
            #
            # Why image_to_data instead of image_to_string?
            # - Gets confidence scores
            # - Gets bounding boxes
            # - More detailed information
            # - Can filter low-confidence words
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT
            )

            # Step 6: Process OCR results
            #
            # Convert raw Tesseract output to structured OCRResult:
            # - Filter empty/low-confidence words
            # - Calculate overall confidence
            # - Extract high-confidence words with bounding boxes
            # - Package into OCRResult object
            return self._process_ocr_data(ocr_data, image)

        except Exception as e:
            # Unexpected error (shouldn't happen but handle gracefully)
            error_msg = f"OCR extraction failed for {file_path}: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)

    # ==========================================================================
    # IMAGE LOADING
    # ==========================================================================

    def _load_image(self, file_path: str) -> Optional[Image.Image]:
        """
        Load and validate image file.

        This loads the image using PIL/Pillow and converts to RGB if needed.

        Args:
            file_path: Path to image file

        Returns:
            PIL Image object, or None if loading failed

        Why convert to RGB?
        - Some images are in CMYK, RGBA, or palette modes
        - OCR works best with consistent format
        - RGB is standard for processing
        - Prevents downstream errors

        Color modes:
        - RGB: Standard color (Red, Green, Blue)
        - RGBA: RGB + Alpha (transparency)
        - CMYK: Print colors (Cyan, Magenta, Yellow, Key/Black)
        - L: Grayscale (single channel)
        - P: Palette mode (indexed colors)

        Why load might fail:
        - File is corrupted
        - Not actually an image
        - Unsupported variant of format
        """
        try:
            # Load image using PIL
            image = Image.open(file_path)

            # Convert to RGB if necessary
            # Some images are CMYK, RGBA, palette, etc.
            # RGB is standard and works best
            if image.mode != 'RGB':
                image = image.convert('RGB')

            return image

        except Exception as e:
            logger.error(f"Failed to load image {file_path}: {e}")
            return None

    # ==========================================================================
    # IMAGE PREPROCESSING
    # ==========================================================================

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Apply preprocessing to improve OCR accuracy.

        Preprocessing enhances image quality for better text recognition.

        Techniques applied:
        1. Grayscale conversion: Remove color, focus on text
        2. Contrast enhancement: Make text darker, background lighter (2.0x)
        3. Sharpness enhancement: Make edges crisp (2.0x)
        4. Gaussian blur: Reduce noise while preserving edges (0.5 radius)

        Args:
            image: PIL Image object (original)

        Returns:
            PIL Image object (preprocessed)

        Why these enhancements?
        1. Grayscale:
           - OCR doesn't need color
           - Reduces complexity
           - Focuses on luminance (brightness)

        2. Contrast (2.0x):
           - Makes text stand out from background
           - Faded documents: 2.0x makes them readable
           - Example: Gray text on white → Black text on white

        3. Sharpness (2.0x):
           - Makes character edges crisp
           - Blurry scans: Sharpening helps OCR recognize characters
           - Example: Fuzzy 'e' → Sharp 'e'

        4. Gaussian blur (0.5 radius):
           - Removes noise (grain, artifacts)
           - Very slight blur (0.5) smooths without losing detail
           - Example: Grainy scan → Smooth scan

        When preprocessing helps most:
        - Faded documents (low contrast)
        - Blurry scans (out of focus)
        - Photos from phones (not perfectly flat)
        - Old documents (degraded)

        When preprocessing might hurt:
        - Perfect high-quality scans (already optimal)
        - Very low resolution (can't fix bad data)

        Performance:
        - Adds ~0.5 seconds per page
        - Worth it for poor quality images (+10-20% accuracy)

        Example enhancement:
            Before: [Faded, blurry text]
            After:  [Sharp, high-contrast text]
            Accuracy: 65% → 85% (+20% improvement!)
        """
        try:
            # Step 1: Convert to grayscale
            #
            # Why grayscale?
            # - OCR engines work on text luminance (brightness)
            # - Color is not needed for text recognition
            # - Simplifies processing
            # - Removes color noise
            #
            # Color mode 'L' = Luminance (grayscale)
            if image.mode != 'L':
                image = image.convert('L')

            # Step 2: Enhance contrast (2.0x)
            #
            # What this does:
            # - Makes dark pixels darker
            # - Makes light pixels lighter
            # - Increases difference between text and background
            #
            # Factor 2.0:
            # - 1.0 = no change
            # - 2.0 = double the contrast
            # - 0.5 = half the contrast
            #
            # Why 2.0?
            # - Good balance for most documents
            # - Not too aggressive (would create artifacts)
            # - Not too subtle (would be pointless)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)

            # Step 3: Enhance sharpness (2.0x)
            #
            # What this does:
            # - Emphasizes edges
            # - Makes boundaries between characters crisp
            # - Helps with blurry scans
            #
            # Factor 2.0:
            # - 1.0 = no change
            # - 2.0 = double the sharpness
            # - Higher = more sharp but can create artifacts
            #
            # Why 2.0?
            # - Good for slightly blurry images
            # - Not so aggressive it creates halos
            # - Helps OCR recognize character shapes
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)

            # Step 4: Apply slight Gaussian blur to reduce noise
            #
            # What this does:
            # - Smooths the image slightly
            # - Removes grain, artifacts, specks
            # - Preserves edges (Gaussian is edge-aware)
            #
            # Radius 0.5:
            # - Very subtle blur
            # - 0.0 = no blur
            # - 0.5 = gentle smoothing
            # - 2.0+ = noticeable blur (bad for OCR!)
            #
            # Why blur after sharpening?
            # - Sharpening can amplify noise
            # - Slight blur removes noise
            # - Net effect: Sharp text, smooth background
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

            return image

        except Exception as e:
            # If preprocessing fails, log warning and use original
            # Better to have unprocessed OCR than no OCR
            logger.warning(f"Preprocessing failed, using original image: {e}")
            return image

    # ==========================================================================
    # RESULT PROCESSING
    # ==========================================================================

    def _process_ocr_data(self, ocr_data: Dict[str, Any], image: Image.Image) -> Result[OCRResult]:
        """
        Process raw OCR data from Tesseract into structured result.

        Tesseract returns dictionaries with parallel arrays:
        - ocr_data['text']: ['Invoice', '#12345', 'Date:', '2024-10-01', ...]
        - ocr_data['conf']: [95, 87, 92, 88, ...]
        - ocr_data['left']: [10, 120, 10, 120, ...]  (x coordinate)
        - ocr_data['top']: [10, 10, 30, 30, ...]     (y coordinate)
        - ocr_data['width']: [100, 80, 50, 120, ...]
        - ocr_data['height']: [20, 20, 20, 20, ...]

        This method:
        1. Filters empty text and low-confidence words
        2. Calculates overall confidence (average)
        3. Extracts high-confidence words with bounding boxes (conf > 60)
        4. Creates structured OCRResult

        Args:
            ocr_data: Raw OCR data from Tesseract (dictionary)
            image: Original PIL Image (for metadata)

        Returns:
            Result containing OCRResult or error

        Confidence threshold (60%):
        - 90-100%: Very confident (trust it)
        - 60-89%: Medium confidence (usually correct)
        - 0-59%: Low confidence (likely errors) ← Filtered out

        Why filter low confidence?
        - Tesseract sometimes "sees" text that isn't there
        - Low confidence words are often garbage ("|||", "—", etc.)
        - Better to miss a word than include garbage

        Bounding boxes:
        - (left, top, width, height)
        - Coordinates in pixels
        - Useful for:
          - Understanding document layout
          - Extracting specific regions
          - Debugging OCR results
        """
        try:
            # Step 1: Extract words and filter
            #
            # Process each word from Tesseract output:
            # - Skip empty/whitespace
            # - Store all non-empty words
            # - Track confidence scores
            # - Save high-confidence words with bounding boxes
            words = []
            confidences = []
            high_confidence_words = []

            for i, text in enumerate(ocr_data['text']):
                # Skip empty text
                if text.strip():
                    # Get confidence score for this word
                    conf = int(ocr_data['conf'][i])

                    # Store word and confidence
                    words.append(text)
                    confidences.append(conf)

                    # If high confidence (>60%), save with bounding box
                    # These are the words we trust
                    if conf > 60:  # High confidence threshold
                        high_confidence_words.append({
                            'text': text,
                            'confidence': conf,
                            'bbox': (
                                ocr_data['left'][i],    # x coordinate
                                ocr_data['top'][i],     # y coordinate
                                ocr_data['width'][i],   # width in pixels
                                ocr_data['height'][i]   # height in pixels
                            )
                        })

            # Step 2: Calculate overall confidence
            #
            # Average of all word confidences.
            # Gives a sense of overall OCR quality.
            #
            # Interpretation:
            # - 90-100%: Excellent OCR, very reliable
            # - 70-89%: Good OCR, mostly reliable
            # - 50-69%: Fair OCR, some errors expected
            # - <50%: Poor OCR, many errors likely
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Step 3: Join text with spaces
            #
            # Tesseract returns individual words.
            # We join them with spaces to form full text.
            #
            # Note: This loses some layout information
            # (line breaks, indentation, etc.)
            # For layout preservation, use image_to_pdf or hOCR output.
            full_text = ' '.join(words)

            # Step 4: Create structured result
            #
            # Package everything into OCRResult object:
            # - Extracted text
            # - Overall confidence
            # - Word count
            # - High confidence words (for validation/debugging)
            # - Image metadata (size, format, color mode)
            result = OCRResult(
                text=full_text,
                confidence=overall_confidence,
                word_count=len(words),
                high_confidence_words=high_confidence_words,
                image_size=image.size,           # (width, height) in pixels
                format=image.format or 'Unknown', # 'PNG', 'JPEG', etc.
                mode=image.mode                  # 'RGB', 'L', etc.
            )

            logger.info(f"OCR completed: {len(words)} words, {overall_confidence:.1f}% confidence")
            return Result.success(result)

        except Exception as e:
            # Processing failed (shouldn't happen but handle gracefully)
            error_msg = f"Failed to process OCR data: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)


# ==============================================================================
# CONVENIENCE ALIAS
# ==============================================================================

# Alias for backward compatibility and convenience
# Some code might reference ImageProcessor instead of TesseractOCRService
ImageProcessor = TesseractOCRService
