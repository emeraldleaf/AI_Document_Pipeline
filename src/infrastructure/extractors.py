"""
Document extractors implementing Protocol-based architecture.

This module contains extractors for different document formats (PDF, Word, Excel, Images, Text).
Each extractor knows how to read a specific file type and extract its text content.

Architecture Pattern: Strategy Pattern
- Each extractor implements the DocumentExtractor protocol
- The ExtractionService selects the right extractor based on file type
- This makes it easy to add new document formats without changing existing code

For Junior Developers:
- Start by reading the ExtractionService class to understand the flow
- Then look at individual extractors (TextExtractor is the simplest)
- Notice how each extractor follows the same pattern: can_extract() then extract()
"""

import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Third-party libraries for document processing
import pdfplumber  # For reading PDF files
from docx import Document as DocxDocument  # For reading Word documents
import openpyxl  # For reading Excel files
import pandas as pd  # For processing Excel data
from pdf2image import convert_from_path  # For converting PDF pages to images

# Import our domain models and protocols
# These define the "contracts" that extractors must follow
from ..domain import (
    DocumentExtractor,  # Protocol (interface) that all extractors implement
    OCRProcessor,  # Protocol for Optical Character Recognition (reading text from images)
    BaseDocumentExtractor,  # Base class with common functionality
    DocumentMetadata,  # Data about the document (author, title, dates, etc.)
    ExtractedContent,  # The extracted text and metadata
    Result,  # Wrapper for success/failure results
    DocumentExtractionError,  # Custom error for extraction failures
    UnsupportedFormatError,  # Custom error for unsupported file types
)


# Set up logging to help us debug issues
logger = logging.getLogger(__name__)


class PDFExtractor(BaseDocumentExtractor):
    """
    Extract content from PDF files with OCR fallback for image-based PDFs.

    PDF files come in two types:
    1. Text-based PDFs: Have selectable text (can copy/paste)
    2. Image-based PDFs: Scanned documents (need OCR to extract text)

    This extractor tries text extraction first, then falls back to OCR if needed.

    Example:
        >>> extractor = PDFExtractor(ocr_service)
        >>> result = await extractor.extract(Path("invoice.pdf"))
        >>> if result.is_success:
        ...     print(result.value.text)
    """

    def __init__(self, ocr_service: Optional[OCRProcessor] = None):
        """
        Initialize PDF extractor.

        Args:
            ocr_service: Optional OCR service for reading scanned PDFs
                        If None, image-based PDFs will return empty text

        Why Optional?
        - OCR requires Tesseract to be installed
        - Some users may not need image-based PDF support
        - Allows the system to work without OCR for text-based PDFs
        """
        self.ocr_service = ocr_service

    def can_extract(self, file_path: Path) -> bool:
        """
        Check if this extractor can handle the given file.

        This is the "Strategy Pattern" check - each extractor says what it can handle.

        Args:
            file_path: Path to the file we want to extract from

        Returns:
            True if this extractor can handle .pdf files

        Example:
            >>> extractor = PDFExtractor()
            >>> extractor.can_extract(Path("document.pdf"))  # Returns True
            >>> extractor.can_extract(Path("document.docx"))  # Returns False
        """
        return file_path.suffix.lower() == '.pdf'

    async def extract(self, file_path: Path) -> Result[ExtractedContent]:
        """
        Extract content from PDF with OCR fallback for image-based PDFs.

        Flow:
        1. Check if we can handle this file type
        2. Get basic file information (size, dates, etc.)
        3. Try text extraction first (fast)
        4. If no text found, try OCR (slower but works on scanned docs)
        5. Return extracted content or error

        Args:
            file_path: Path to the PDF file

        Returns:
            Result object containing:
            - Success: ExtractedContent with text and metadata
            - Failure: Error message explaining what went wrong

        Why async?
        - OCR processing can take a while (seconds per page)
        - Using async allows other tasks to run while waiting
        - Better for batch processing many documents
        """
        try:
            # Step 1: Validate file type
            if not self.can_extract(file_path):
                return Result.failure(f"Unsupported file type: {file_path.suffix}")

            # Step 2: Get basic metadata (file size, dates, etc.)
            # This is quick and doesn't require reading the PDF content
            metadata = self._get_basic_metadata(file_path)

            # Step 3: Try text extraction first (works for most PDFs)
            text_result = await self._extract_text_based(file_path, metadata)

            # Check if we got any text
            if text_result.is_success and text_result.value and text_result.value.text.strip():
                logger.info(f"Successfully extracted text from PDF: {file_path.name}")
                return text_result

            # Step 4: Fallback to OCR for image-based PDFs (scanned documents)
            if self.ocr_service:
                logger.info(f"No text found, attempting OCR for: {file_path.name}")
                return await self._extract_image_based(file_path, metadata)

            # Step 5: If no OCR available, return empty content
            # This is better than failing - we at least return the metadata
            logger.warning(f"No text extracted and no OCR service available: {file_path.name}")
            content = ExtractedContent(
                text="",  # Empty text
                metadata=metadata,
                pages=[]
            )
            return Result.success(content)

        except Exception as e:
            # Catch any unexpected errors and return as a failure
            # This prevents the whole program from crashing
            error_msg = f"PDF extraction failed for {file_path}: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)

    async def _extract_text_based(self, file_path: Path, metadata: DocumentMetadata) -> Result[ExtractedContent]:
        """
        Extract text using pdfplumber library.

        This works for PDFs that have selectable text (most PDFs).
        It's fast because it just reads the text data from the PDF file.

        Process:
        1. Open PDF with pdfplumber
        2. Loop through each page
        3. Extract text from each page
        4. Combine all pages into one big text string
        5. Also keep individual pages for later analysis

        Args:
            file_path: Path to PDF file
            metadata: Basic metadata we already collected

        Returns:
            Result with extracted text or error
        """
        try:
            pages = []  # Store text from each page separately
            all_text = []  # Store all text combined

            # Open the PDF file using a context manager
            # "with" ensures the file is properly closed even if there's an error
            with pdfplumber.open(file_path) as pdf:
                # Get additional metadata from the PDF itself
                page_count = len(pdf.pages)

                # Create updated metadata with PDF-specific info
                # Why recreate? DocumentMetadata is immutable (frozen=True)
                # This is good for thread safety but means we need a new object
                metadata = DocumentMetadata(
                    id=metadata.id,
                    file_path=metadata.file_path,
                    file_name=metadata.file_name,
                    file_type=metadata.file_type,
                    file_size=metadata.file_size,
                    created_date=metadata.created_date,
                    modified_date=metadata.modified_date,
                    page_count=page_count,  # NEW: from PDF
                    author=pdf.metadata.get('Author') if pdf.metadata else None,  # NEW: from PDF
                    title=pdf.metadata.get('Title') if pdf.metadata else None,  # NEW: from PDF
                )

                # Process each page
                for i, page in enumerate(pdf.pages):
                    # Extract text from this page
                    # "or ''" means: if extract_text() returns None, use empty string instead
                    page_text = page.extract_text() or ""

                    pages.append(page_text)  # Store individually
                    all_text.append(page_text)  # Add to combined text

                    # Log progress for large documents
                    if (i + 1) % 10 == 0:  # Every 10 pages
                        logger.debug(f"Processed {i + 1}/{page_count} pages")

            # Create the final ExtractedContent object
            content = ExtractedContent(
                text="\n".join(all_text),  # Join all pages with newlines
                metadata=metadata,
                pages=pages  # Keep individual pages for later
            )

            logger.info(f"Extracted {len(all_text)} pages from PDF: {file_path.name}")
            return Result.success(content)

        except Exception as e:
            # If anything goes wrong, return an error instead of crashing
            error_msg = f"Text-based PDF extraction failed: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)

    async def _extract_image_based(self, file_path: Path, metadata: DocumentMetadata) -> Result[ExtractedContent]:
        """
        Extract text from image-based PDF using OCR (Optical Character Recognition).

        This is for scanned documents where the PDF is basically just images of pages.
        OCR "reads" the images and converts them to text, like a human reading a page.

        Process:
        1. Convert each PDF page to an image
        2. Run OCR on each image to extract text
        3. Combine all the text
        4. Clean up temporary files

        Why slower?
        - Converting PDF to images takes time
        - OCR has to analyze each image pixel-by-pixel
        - Can take 1-5 seconds per page depending on complexity

        Args:
            file_path: Path to PDF file
            metadata: Basic metadata

        Returns:
            Result with OCR-extracted text or error
        """
        # Ensure we have an OCR service
        if not self.ocr_service:
            return Result.failure("OCR service not available for image-based PDF")

        try:
            # Step 1: Convert PDF pages to images
            # This creates a list of PIL Image objects, one per page
            logger.info(f"Converting PDF to images: {file_path.name}")
            images = convert_from_path(file_path)

            pages = []  # Store OCR text from each page
            all_text = []  # Store all text combined

            # Step 2: Process each image with OCR
            for i, image in enumerate(images):
                logger.debug(f"Processing page {i + 1}/{len(images)} with OCR")

                # Save image temporarily
                # OCR tools often need a file path rather than an image object
                temp_image_path = f"/tmp/pdf_page_{i}.png"
                image.save(temp_image_path, 'PNG')

                try:
                    # Step 3: Run OCR on this image
                    ocr_result = await self.ocr_service.extract_text(temp_image_path)

                    if ocr_result.is_success and ocr_result.value:
                        page_text = ocr_result.value.text
                        pages.append(page_text)
                        all_text.append(page_text)
                        logger.debug(f"OCR extracted {len(page_text)} characters from page {i + 1}")
                    else:
                        # OCR failed for this page, add empty text
                        logger.warning(f"OCR failed for page {i}: {ocr_result.error}")
                        pages.append("")

                finally:
                    # Step 4: Clean up temporary file
                    # This happens even if OCR fails (that's why it's in "finally")
                    Path(temp_image_path).unlink(missing_ok=True)

            # Update metadata with page count from images
            updated_metadata = DocumentMetadata(
                id=metadata.id,
                file_path=metadata.file_path,
                file_name=metadata.file_name,
                file_type=metadata.file_type,
                file_size=metadata.file_size,
                created_date=metadata.created_date,
                modified_date=metadata.modified_date,
                page_count=len(images),
                author=metadata.author,
                title=metadata.title,
            )

            # Create final content object
            content = ExtractedContent(
                text="\n".join(all_text),
                metadata=updated_metadata,
                pages=pages
            )

            logger.info(f"OCR extracted {len(pages)} pages from image-based PDF: {file_path.name}")
            return Result.success(content)

        except Exception as e:
            error_msg = f"Image-based PDF extraction failed: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)


class ImageExtractor(BaseDocumentExtractor):
    """
    Extract text from image files using OCR.

    Supports: PNG, JPG, JPEG, TIFF, BMP, etc.

    This is for standalone images (not PDFs with images).
    For example: photos of receipts, screenshots of documents, scanned images.

    Example:
        >>> ocr = TesseractOCRService()
        >>> extractor = ImageExtractor(ocr)
        >>> result = await extractor.extract(Path("receipt.jpg"))
    """

    def __init__(self, ocr_service: OCRProcessor):
        """
        Initialize image extractor.

        Args:
            ocr_service: OCR service for text extraction (REQUIRED)
                        Unlike PDFExtractor, this is required because
                        there's no other way to get text from images
        """
        self.ocr_service = ocr_service

    def can_extract(self, file_path: Path) -> bool:
        """
        Check if this extractor can handle image files.

        We delegate to the OCR service to check supported formats
        because different OCR services support different image types.

        Args:
            file_path: Path to file

        Returns:
            True if OCR service supports this image format
        """
        return self.ocr_service.is_supported(str(file_path))

    async def extract(self, file_path: Path) -> Result[ExtractedContent]:
        """
        Extract text from image file using OCR.

        This is simpler than PDF extraction because:
        - Images are always single-page
        - No need to check for text-based content first
        - Just run OCR directly

        Args:
            file_path: Path to image file

        Returns:
            Result with extracted text or error
        """
        try:
            # Step 1: Validate file type
            if not self.can_extract(file_path):
                return Result.failure(f"Unsupported image format: {file_path.suffix}")

            # Step 2: Get basic file metadata
            metadata = self._get_basic_metadata(file_path)

            # Step 3: Run OCR
            logger.info(f"Running OCR on image: {file_path.name}")
            ocr_result = await self.ocr_service.extract_text(str(file_path))

            if not ocr_result.is_success:
                return Result.failure(f"OCR extraction failed: {ocr_result.error}")

            # Step 4: Update metadata with OCR-specific information
            ocr_data = ocr_result.value
            updated_metadata = DocumentMetadata(
                id=metadata.id,
                file_path=metadata.file_path,
                file_name=metadata.file_name,
                file_type=metadata.file_type,
                file_size=metadata.file_size,
                created_date=metadata.created_date,
                modified_date=metadata.modified_date,
                page_count=1,  # Images are always single page
                ocr_confidence=ocr_data.confidence,  # How confident the OCR is (0-100)
                image_size=ocr_data.image_size,  # Width x Height
                image_format=ocr_data.format,  # PNG, JPEG, etc.
            )

            # Step 5: Create final content
            content = ExtractedContent(
                text=ocr_data.text,
                metadata=updated_metadata,
                pages=[ocr_data.text]  # Single page
            )

            logger.info(f"OCR extracted {ocr_data.word_count} words from image: {file_path.name}")
            return Result.success(content)

        except Exception as e:
            error_msg = f"Image extraction failed for {file_path}: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)


class DOCXExtractor(BaseDocumentExtractor):
    """
    Extract content from DOCX files (Microsoft Word documents).

    DOCX is actually a ZIP file containing XML files with the document content.
    The python-docx library handles all this complexity for us.

    What we extract:
    - All paragraph text
    - Document properties (author, title, dates)
    - Note: We don't extract images, headers/footers, or complex formatting

    Example:
        >>> extractor = DOCXExtractor()
        >>> result = await extractor.extract(Path("report.docx"))
    """

    def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle DOCX files."""
        return file_path.suffix.lower() == '.docx'

    async def extract(self, file_path: Path) -> Result[ExtractedContent]:
        """
        Extract content from DOCX file.

        Process:
        1. Open DOCX file
        2. Extract text from all paragraphs
        3. Get document properties (author, title, etc.)
        4. Combine everything into ExtractedContent

        Args:
            file_path: Path to DOCX file

        Returns:
            Result with extracted text or error
        """
        try:
            # Step 1: Validate file type
            if not self.can_extract(file_path):
                return Result.failure(f"Unsupported file type: {file_path.suffix}")

            # Step 2: Get basic metadata
            metadata = self._get_basic_metadata(file_path)

            # Step 3: Open and read the DOCX file
            doc = DocxDocument(file_path)

            # Step 4: Extract text from all paragraphs
            # List comprehension: for each paragraph, if it has text, add it to the list
            # "if p.text.strip()" means: skip empty paragraphs
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            # Join all paragraphs with newlines
            text = "\n".join(paragraphs)

            # Step 5: Get document properties
            # Word documents have built-in properties like author and title
            core_props = doc.core_properties

            # Update metadata with document properties
            updated_metadata = DocumentMetadata(
                id=metadata.id,
                file_path=metadata.file_path,
                file_name=metadata.file_name,
                file_type=metadata.file_type,
                file_size=metadata.file_size,
                created_date=core_props.created or metadata.created_date,  # Use doc date if available
                modified_date=core_props.modified or metadata.modified_date,
                page_count=len(paragraphs),  # Not real pages, but number of paragraphs
                author=core_props.author,
                title=core_props.title,
            )

            # Step 6: Create final content
            content = ExtractedContent(
                text=text,
                metadata=updated_metadata,
                pages=paragraphs  # Each paragraph as a "page"
            )

            logger.info(f"Extracted {len(paragraphs)} paragraphs from DOCX: {file_path.name}")
            return Result.success(content)

        except Exception as e:
            error_msg = f"DOCX extraction failed for {file_path}: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)


class ExcelExtractor(BaseDocumentExtractor):
    """
    Extract content from Excel files (.xlsx, .xls).

    Excel files can have multiple sheets with tables of data.
    We convert all sheets to text format so they can be classified.

    Example output:
        Sheet: Sales
        Product  Price  Quantity
        Widget   10.00  5
        Gadget   20.00  3

        Sheet: Expenses
        Category  Amount
        Rent      1000
        Utilities 200

    Example:
        >>> extractor = ExcelExtractor()
        >>> result = await extractor.extract(Path("sales.xlsx"))
    """

    def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle Excel files."""
        return file_path.suffix.lower() in {'.xlsx', '.xls'}

    async def extract(self, file_path: Path) -> Result[ExtractedContent]:
        """
        Extract content from Excel file.

        Process:
        1. Read all sheets from Excel file
        2. Convert each sheet to text format
        3. Combine all sheets with labels

        Args:
            file_path: Path to Excel file

        Returns:
            Result with extracted text or error
        """
        try:
            # Step 1: Validate file type
            if not self.can_extract(file_path):
                return Result.failure(f"Unsupported file type: {file_path.suffix}")

            # Step 2: Get basic metadata
            metadata = self._get_basic_metadata(file_path)

            # Step 3: Read Excel file
            # sheet_name=None means: read ALL sheets
            # Returns a dictionary: {sheet_name: DataFrame}
            df = pd.read_excel(file_path, sheet_name=None)

            all_text = []  # Combined text from all sheets
            sheet_texts = []  # Text from each sheet separately

            # Step 4: Process each sheet
            for sheet_name, sheet_df in df.items():
                # Convert DataFrame to text format
                # This creates a nicely formatted table
                sheet_text = f"Sheet: {sheet_name}\n"
                sheet_text += sheet_df.to_string(
                    index=False,  # Don't include row numbers
                    na_rep=''  # Empty cells show as blank, not "NaN"
                )

                sheet_texts.append(sheet_text)
                all_text.append(sheet_text)

            # Step 5: Update metadata
            updated_metadata = DocumentMetadata(
                id=metadata.id,
                file_path=metadata.file_path,
                file_name=metadata.file_name,
                file_type=metadata.file_type,
                file_size=metadata.file_size,
                created_date=metadata.created_date,
                modified_date=metadata.modified_date,
                page_count=len(df),  # Number of sheets = "pages"
            )

            # Step 6: Create final content
            content = ExtractedContent(
                text="\n\n".join(all_text),  # Double newline between sheets
                metadata=updated_metadata,
                pages=sheet_texts  # Each sheet as a "page"
            )

            logger.info(f"Extracted {len(df)} sheets from Excel: {file_path.name}")
            return Result.success(content)

        except Exception as e:
            error_msg = f"Excel extraction failed for {file_path}: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)


class TextExtractor(BaseDocumentExtractor):
    """
    Extract content from plain text files.

    Supports: .txt, .md (Markdown), .csv

    This is the simplest extractor - just read the file!
    The only complexity is handling different text encodings.

    Example:
        >>> extractor = TextExtractor()
        >>> result = await extractor.extract(Path("notes.txt"))
    """

    def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle text files."""
        return file_path.suffix.lower() in {'.txt', '.md', '.csv'}

    async def extract(self, file_path: Path) -> Result[ExtractedContent]:
        """
        Extract content from text file.

        Process:
        1. Try different text encodings (UTF-8, Latin-1, etc.)
        2. Read the file with the first encoding that works
        3. Split into lines for "pages"

        Why try multiple encodings?
        - Different systems use different text encodings
        - Windows often uses cp1252, Mac/Linux use UTF-8
        - Old files might use Latin-1
        - We try each one until something works

        Args:
            file_path: Path to text file

        Returns:
            Result with extracted text or error
        """
        try:
            # Step 1: Validate file type
            if not self.can_extract(file_path):
                return Result.failure(f"Unsupported file type: {file_path.suffix}")

            # Step 2: Get basic metadata
            metadata = self._get_basic_metadata(file_path)

            # Step 3: Try different encodings
            # These are the most common text encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            text = ""

            for encoding in encodings:
                try:
                    # Try to open the file with this encoding
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    # If we get here without error, this encoding worked!
                    logger.debug(f"Successfully read file with {encoding} encoding")
                    break  # Stop trying other encodings
                except UnicodeDecodeError:
                    # This encoding didn't work, try the next one
                    continue

            # Check if we successfully read the file
            if not text:
                return Result.failure("Failed to decode text file with any encoding")

            # Step 4: Split into lines for "pages"
            lines = text.split('\n')

            # Step 5: Create final content
            content = ExtractedContent(
                text=text,
                metadata=metadata,
                pages=lines  # Each line as a "page" (not ideal but works)
            )

            logger.info(f"Extracted {len(lines)} lines from text file: {file_path.name}")
            return Result.success(content)

        except Exception as e:
            error_msg = f"Text extraction failed for {file_path}: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)


class ExtractionService:
    """
    Service for extracting content from various document formats.

    This is the main entry point for document extraction.
    It uses the Strategy Pattern to select the right extractor.

    How it works:
    1. You give it a file path
    2. It tries each extractor to see who can handle it
    3. It uses the first extractor that says "yes"
    4. It returns the extracted content

    Why this design?
    - Easy to add new document formats (just add a new extractor)
    - Each extractor is independent (can test separately)
    - Follows Single Responsibility Principle (each extractor does one thing)

    Example:
        >>> service = ExtractionService([
        ...     TextExtractor(),
        ...     PDFExtractor(),
        ...     DOCXExtractor()
        ... ])
        >>> result = await service.extract_content(Path("document.pdf"))
    """

    def __init__(self, extractors: List[DocumentExtractor]):
        """
        Initialize extraction service with list of extractors.

        Args:
            extractors: List of document extractors
                       Order matters! First match wins.
                       Put more specific extractors first.

        Example:
            >>> extractors = [
            ...     TextExtractor(),      # Handles .txt, .md, .csv
            ...     DOCXExtractor(),      # Handles .docx
            ...     ExcelExtractor(),     # Handles .xlsx, .xls
            ...     PDFExtractor(ocr),    # Handles .pdf
            ... ]
        """
        self.extractors = extractors
        logger.info(f"Initialized ExtractionService with {len(extractors)} extractors")

    async def extract_content(self, file_path: Path) -> Result[ExtractedContent]:
        """
        Extract content from a document using appropriate extractor.

        This is the main method you call to extract from any document.
        It automatically picks the right extractor based on file type.

        Flow:
        1. Check if file exists
        2. Loop through extractors
        3. Ask each: "Can you handle this file?"
        4. Use the first one that says yes
        5. Return the result

        Args:
            file_path: Path to the document file

        Returns:
            Result containing ExtractedContent or error

        Example:
            >>> result = await service.extract_content(Path("invoice.pdf"))
            >>> if result.is_success:
            ...     print(f"Extracted {len(result.value.text)} characters")
            >>> else:
            ...     print(f"Error: {result.error}")
        """
        try:
            # Step 1: Validate file exists
            if not file_path.exists():
                return Result.failure(f"File not found: {file_path}")

            # Step 2: Find suitable extractor
            # This is the Strategy Pattern in action!
            for extractor in self.extractors:
                # Ask this extractor: "Can you handle this file?"
                if extractor.can_extract(file_path):
                    # Found one! Use it.
                    logger.info(f"Using {extractor.__class__.__name__} for {file_path.name}")
                    return await extractor.extract(file_path)

            # Step 3: No extractor found
            # This means we don't support this file type
            return Result.failure(f"No suitable extractor found for {file_path}")

        except Exception as e:
            # Catch any unexpected errors
            error_msg = f"Extraction service failed for {file_path}: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)

    def get_supported_extensions(self) -> List[str]:
        """
        Get list of all supported file extensions.

        This is useful for:
        - Showing users what file types we support
        - Filtering files before processing
        - Generating documentation

        Returns:
            Sorted list of file extensions (e.g., ['.pdf', '.docx', '.txt'])
        """
        extensions = set()

        # Check if extractors declare their supported formats
        for extractor in self.extractors:
            if hasattr(extractor, 'SUPPORTED_FORMATS'):
                extensions.update(extractor.SUPPORTED_FORMATS)

        return sorted(list(extensions))


def create_extraction_service(ocr_service: Optional[OCRProcessor] = None) -> ExtractionService:
    """
    Factory function to create a configured extraction service.

    This is a "Factory" pattern - a function that creates and configures objects.

    Why use a factory?
    - Centralizes creation logic
    - Ensures consistent configuration
    - Makes testing easier (can create with test doubles)
    - Hides complexity from users

    Args:
        ocr_service: Optional OCR service for image processing
                    If provided, enables image and scanned PDF support

    Returns:
        Fully configured ExtractionService ready to use

    Example:
        >>> # Without OCR (text-based documents only)
        >>> service = create_extraction_service()

        >>> # With OCR (includes images and scanned PDFs)
        >>> ocr = TesseractOCRService()
        >>> service = create_extraction_service(ocr)
    """
    # Create extractors in order
    # Order matters! More specific formats first
    extractors = [
        TextExtractor(),      # .txt, .md, .csv - simplest, try first
        DOCXExtractor(),      # .docx - Microsoft Word
        ExcelExtractor(),     # .xlsx, .xls - Microsoft Excel
    ]

    # Add PDF extractor with optional OCR support
    extractors.append(PDFExtractor(ocr_service))

    # Add image extractor if OCR service is available
    # Images REQUIRE OCR, so only add if we have it
    if ocr_service:
        extractors.append(ImageExtractor(ocr_service))
        logger.info("OCR service provided - image extraction enabled")
    else:
        logger.info("No OCR service - image extraction disabled")

    return ExtractionService(extractors)
