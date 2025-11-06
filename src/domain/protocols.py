"""
==============================================================================
DOMAIN PROTOCOLS - Foundation Contracts and Interfaces
==============================================================================

PURPOSE:
    Define the core contracts (interfaces) that all implementations must follow.
    This is the "foundation" of the architecture - the rules everyone follows.

WHAT ARE PROTOCOLS?
    - Python's way of defining interfaces (like Java/C# interfaces)
    - Specify WHAT methods must exist, not HOW they work
    - Enable "contract-based" programming
    - Support dependency injection and testing

WHY USE PROTOCOLS?
    Without protocols:
    - Hard to swap implementations (e.g., change from Ollama to OpenAI)
    - Hard to test (can't easily mock services)
    - Tight coupling (code depends on specific implementations)

    With protocols:
    ✓ Easy to swap implementations (just implement the protocol)
    ✓ Easy to test (create mock objects that follow the protocol)
    ✓ Loose coupling (depend on interfaces, not implementations)
    ✓ SOLID principles (especially Dependency Inversion)

SOLID PRINCIPLES IN THIS FILE:
    1. **Single Responsibility**: Each protocol has ONE clear purpose
    2. **Open/Closed**: Open for extension, closed for modification
    3. **Liskov Substitution**: Any implementation can replace another
    4. **Interface Segregation**: Small, focused protocols (not giant interfaces)
    5. **Dependency Inversion**: Depend on abstractions (protocols), not implementations

REAL-WORLD ANALOGY:
    Protocol = Electrical Outlet Standard
    - Outlets define the interface (shape, voltage, frequency)
    - Any device that follows the standard can plug in
    - You can swap devices without changing the outlet
    - China devices, USA devices - different implementations, same interface

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │                      Domain Layer                            │
    │                  (This File - Protocols)                     │
    │                                                              │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
    │  │DocumentExtrac│  │Classification│  │OCRProcessor  │    │
    │  │tor Protocol  │  │Service Proto │  │Protocol      │    │
    │  │              │  │col           │  │              │    │
    │  │Defines:      │  │Defines:      │  │Defines:      │    │
    │  │- can_extract │  │- classify    │  │- extract_text│    │
    │  │- extract     │  │- is_available│  │- is_supported│    │
    │  └──────────────┘  └──────────────┘  └──────────────┘    │
    └─────────────────────────────────────────────────────────────┘
                           ↑         ↑         ↑
                           │         │         │
                    Implementations follow protocols:
                           │         │         │
    ┌──────────────────────┴─────────┴─────────┴───────────────┐
    │              Infrastructure Layer                          │
    │                                                            │
    │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐    │
    │  │PDFExtractor │  │OllamaClassify│  │TesseractOCR │    │
    │  │(implements  │  │Service       │  │Service      │    │
    │  │protocol)    │  │(implements   │  │(implements  │    │
    │  └─────────────┘  │protocol)     │  │protocol)    │    │
    │                   └──────────────┘  └─────────────┘    │
    └────────────────────────────────────────────────────────────┘

KEY CONCEPTS:
    1. **Protocol**: Interface definition (what, not how)
    2. **Dataclass**: Immutable data container
    3. **Result Type**: Explicit error handling (no exceptions)
    4. **Frozen**: Immutable (can't be modified after creation)
    5. **Protocol vs ABC**: Protocol = structural typing, ABC = inheritance

EXAMPLE - Why Protocols Matter:
    # Without protocols (BAD):
    class DocumentClassifier:
        def __init__(self):
            self.ollama = OllamaService()  # Tightly coupled!
            # Can't easily swap for OpenAI, Claude, etc.
            # Hard to test (requires real Ollama service)

    # With protocols (GOOD):
    class DocumentClassifier:
        def __init__(self, service: ClassificationService):
            self.service = service  # Loosely coupled!
            # Can use Ollama, OpenAI, Claude, or Mock
            # Easy to test (pass mock service)

RELATED FILES:
    - src/infrastructure/extractors.py - Implements DocumentExtractor protocol
    - src/services/classification_service.py - Implements ClassificationService protocol
    - src/services/ocr_service.py - Implements OCRProcessor protocol

AUTHOR: AI Document Pipeline Team
LAST UPDATED: October 2025
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Any, Union
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4


# ==============================================================================
# DATA MODELS (Immutable Value Objects)
# ==============================================================================

@dataclass(frozen=True)
class DocumentMetadata:
    """
    Immutable document metadata container.

    WHAT IT IS:
        A value object that holds all metadata about a document.
        "Value object" means it's identified by its values, not by ID.

    WHY FROZEN (IMMUTABLE)?
        - Thread-safe (can't be changed by accident)
        - Hashable (can use as dict keys, in sets)
        - Predictable (once created, never changes)
        - Prevents bugs (no accidental mutations)

    DESIGN PATTERN:
        Value Object pattern from Domain-Driven Design (DDD)

    Attributes:
        id: Unique identifier for this document
        file_path: Path to the file on disk
        file_name: Name of the file (e.g., "invoice.pdf")
        file_type: MIME type (e.g., "application/pdf")
        file_size: Size in bytes
        created_date: When file was created (from filesystem)
        modified_date: When file was last modified
        page_count: Number of pages (for PDFs, DOCX)
        author: Document author (from metadata)
        title: Document title (from metadata)
        ocr_confidence: OCR confidence if extracted from image
        image_size: (width, height) if document is an image
        image_format: Image format if applicable

    Why so many optional fields?
    - Not all documents have all metadata
    - PDFs might not have author/title
    - Images don't have page_count
    - Optional = "may or may not be present"

    Example:
        >>> from pathlib import Path
        >>> metadata = DocumentMetadata.from_file_stats(Path("invoice.pdf"))
        >>> print(metadata.file_name)
        invoice.pdf
        >>> print(metadata.file_size)
        524288  # 512 KB
    """

    # Required fields (must be provided)
    id: UUID                          # Unique identifier
    file_path: Path                   # Where file is located
    file_name: str                    # File name (e.g., "doc.pdf")
    file_type: str                    # MIME type
    file_size: int                    # Size in bytes

    # Optional fields (might not be available)
    created_date: Optional[datetime] = None      # When created
    modified_date: Optional[datetime] = None     # When last modified
    page_count: Optional[int] = None             # Number of pages
    author: Optional[str] = None                 # Document author
    title: Optional[str] = None                  # Document title

    # OCR-specific metadata
    ocr_confidence: Optional[float] = None       # OCR confidence (0-100)
    image_size: Optional[tuple[int, int]] = None # (width, height) in pixels
    image_format: Optional[str] = None           # Image format (PNG, JPEG)

    @classmethod
    def from_file_stats(cls, file_path: Path) -> "DocumentMetadata":
        """
        Factory method to create metadata from file system statistics.

        This is a convenience method that:
        1. Reads file system metadata (size, dates)
        2. Guesses MIME type from extension
        3. Creates DocumentMetadata object

        Args:
            file_path: Path to the file

        Returns:
            DocumentMetadata with filesystem info populated

        Why classmethod?
        - Alternative constructor (different way to create object)
        - More convenient than manually gathering all info
        - Common pattern: "from_X" factory methods

        Example:
            >>> metadata = DocumentMetadata.from_file_stats(Path("doc.pdf"))
            >>> # Automatically fills in file_size, dates, etc.
        """
        import mimetypes

        # Get file system statistics
        # stat() returns size, creation time, modification time, etc.
        stat = file_path.stat()

        # Guess MIME type from file extension
        # e.g., "invoice.pdf" → "application/pdf"
        mime_type, _ = mimetypes.guess_type(file_path)

        return cls(
            id=uuid4(),                                         # Generate unique ID
            file_path=file_path,
            file_name=file_path.name,
            file_type=mime_type or "unknown",                  # Fallback if can't guess
            file_size=stat.st_size,                            # Bytes
            created_date=datetime.fromtimestamp(stat.st_ctime), # Unix timestamp → datetime
            modified_date=datetime.fromtimestamp(stat.st_mtime),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary for serialization.

        Returns:
            Dictionary with all metadata fields

        Why?
        - JSON export (for API responses, storage)
        - Database insertion
        - Logging

        Example:
            >>> metadata.to_dict()
            {'id': '...', 'file_name': 'invoice.pdf', 'file_size': 524288, ...}
        """
        return {
            'id': str(self.id),
            'file_path': str(self.file_path),
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None,
            'page_count': self.page_count,
            'author': self.author,
            'title': self.title,
            'ocr_confidence': self.ocr_confidence,
            'image_size': self.image_size,
            'image_format': self.image_format,
        }


@dataclass(frozen=True)
class ExtractedContent:
    """
    Immutable container for extracted document content.

    WHAT IT IS:
        The result of document extraction - the text we pulled out
        plus metadata about the document.

    WHY THIS EXISTS:
        - Bundles text + metadata together
        - Type-safe (compiler checks we have both)
        - Immutable (can't be accidentally changed)

    Attributes:
        text: The extracted text content
        metadata: Document metadata (file info, dates, etc.)
        pages: Optional list of text per page (for multi-page docs)

    Example:
        >>> from pathlib import Path
        >>> metadata = DocumentMetadata.from_file_stats(Path("doc.pdf"))
        >>> content = ExtractedContent(
        ...     text="Invoice #12345...",
        ...     metadata=metadata,
        ...     pages=["Page 1 text", "Page 2 text"]
        ... )
        >>> print(content.get_summary(50))
        Invoice #12345...
    """

    text: str                              # Extracted text content
    metadata: DocumentMetadata             # File metadata
    pages: Optional[List[str]] = None      # Per-page text (optional)

    def get_summary(self, max_length: int = 500) -> str:
        """
        Get a truncated summary of the content.

        Args:
            max_length: Maximum characters to return (default: 500)

        Returns:
            Full text if short, or truncated with "..." if long

        Why?
        - For logging (don't want to log 100KB of text)
        - For previews (show first N characters)
        - For debugging (quick look at content)

        Example:
            >>> content = ExtractedContent(text="A" * 1000, metadata=...)
            >>> summary = content.get_summary(50)
            >>> len(summary)
            53  # 50 chars + "..."
        """
        if len(self.text) <= max_length:
            return self.text
        return self.text[:max_length] + "..."


# ==============================================================================
# RESULT TYPE (Explicit Error Handling)
# ==============================================================================

from typing import TypeVar, Generic

# TypeVar lets us create generic types
# T can be any type (int, str, DocumentMetadata, etc.)
T = TypeVar('T')

@dataclass(frozen=True)
class Result(Generic[T]):
    """
    Generic result type for explicit error handling without exceptions.

    WHAT IT IS:
        A container that holds EITHER a success value OR an error message.
        Never both, never neither.

    WHY USE THIS INSTEAD OF EXCEPTIONS?
        Exceptions (traditional Python):
        - Hidden control flow (can't see which functions might fail)
        - Forces try/except everywhere
        - Easy to forget to catch exceptions

        Result type (modern approach):
        ✓ Explicit error handling (return type shows it can fail)
        ✓ Compiler helps (type checker warns if you don't check)
        ✓ No hidden control flow (everything is explicit)
        ✓ Composable (easy to chain operations)

    DESIGN PATTERN:
        Result/Either pattern from functional programming
        Used in: Rust (Result<T, E>), Scala (Either), Haskell (Either)

    States:
        Success: value=something, error=None, is_success=True
        Failure: value=None, error="error message", is_success=False

    Example:
        >>> # Success case
        >>> result = Result.success(42)
        >>> if result.is_success:
        ...     print(f"Got value: {result.value}")
        Got value: 42

        >>> # Failure case
        >>> result = Result.failure("File not found")
        >>> if not result.is_success:
        ...     print(f"Error: {result.error}")
        Error: File not found

    Why Generic[T]?
    - Works with any type
    - Result[int], Result[str], Result[DocumentMetadata], etc.
    - Type checker knows what type the value is
    """

    value: Optional[T] = None          # The success value (if successful)
    error: Optional[str] = None        # The error message (if failed)
    is_success: bool = True            # Whether operation succeeded

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        """
        Create a successful result containing a value.

        Args:
            value: The success value

        Returns:
            Result with value set, is_success=True

        Example:
            >>> result = Result.success("Hello")
            >>> result.is_success
            True
            >>> result.value
            'Hello'
        """
        return cls(value=value, is_success=True)

    @classmethod
    def failure(cls, error: str) -> "Result[T]":
        """
        Create a failed result containing an error message.

        Args:
            error: Error message describing what went wrong

        Returns:
            Result with error set, is_success=False

        Example:
            >>> result = Result.failure("File not found")
            >>> result.is_success
            False
            >>> result.error
            'File not found'
        """
        return cls(error=error, is_success=False)

    def unwrap(self) -> T:
        """
        Get the value or raise exception if failed.

        Returns:
            The success value

        Raises:
            ValueError: If result is a failure

        When to use:
        - When failure is truly unexpected
        - In tests (assert result.unwrap() == expected)
        - When you WANT to crash on error

        Example:
            >>> result = Result.success(42)
            >>> result.unwrap()
            42

            >>> result = Result.failure("Error")
            >>> result.unwrap()
            ValueError: Result failed: Error
        """
        if not self.is_success:
            raise ValueError(f"Result failed: {self.error}")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """
        Get the value or return default if failed.

        Args:
            default: Value to return if result is a failure

        Returns:
            Success value if successful, default otherwise

        When to use:
        - When you have a sensible fallback
        - When you want to continue despite errors

        Example:
            >>> result = Result.success(42)
            >>> result.unwrap_or(0)
            42

            >>> result = Result.failure("Error")
            >>> result.unwrap_or(0)
            0
        """
        return self.value if self.is_success else default


# ==============================================================================
# SPECIALIZED RESULT TYPES
# ==============================================================================

@dataclass(frozen=True)
class OCRResult:
    """
    Result of OCR text extraction operation.

    WHAT IT IS:
        Data returned from OCR processing (Tesseract).
        Contains text + quality metrics.

    Attributes:
        text: The extracted text
        confidence: Overall confidence (0-100%)
        word_count: Number of words extracted
        high_confidence_words: Words with confidence > 60%
        image_size: (width, height) in pixels
        format: Image format (PNG, JPEG, etc.)
        mode: Color mode (RGB, L=grayscale, etc.)

    Why separate from ExtractedContent?
    - OCR has unique fields (confidence, word-level data)
    - Different use cases
    - Type safety (can't confuse OCR result with regular extraction)

    Example:
        >>> ocr_result = OCRResult(
        ...     text="Invoice #12345",
        ...     confidence=92.5,
        ...     word_count=3,
        ...     high_confidence_words=[...],
        ...     image_size=(1200, 800),
        ...     format='PNG',
        ...     mode='RGB'
        ... )
    """

    text: str                                    # Extracted text
    confidence: float                            # Overall confidence (0-100)
    word_count: int                              # Number of words
    high_confidence_words: List[Dict[str, Any]]  # High-confidence words with bboxes
    image_size: tuple[int, int]                  # (width, height) pixels
    format: str                                  # Image format (PNG, JPEG, ...)
    mode: str                                    # Color mode (RGB, L, ...)


@dataclass(frozen=True)
class ClassificationResult:
    """
    Result of document classification operation.

    WHAT IT IS:
        The category assigned by AI + confidence + reasoning.

    Attributes:
        category: The assigned category (e.g., "invoices")
        confidence: How confident the AI is (0.0-1.0)
        reasoning: Optional explanation from AI
        metadata: Optional additional data (model used, etc.)

    Why separate from ExtractedContent?
    - Classification is a different operation
    - Has unique fields (reasoning, confidence)
    - Type safety

    Example:
        >>> result = ClassificationResult(
        ...     category="invoices",
        ...     confidence=0.95,
        ...     reasoning="Contains invoice number, amount, vendor",
        ...     metadata={"model": "llama3.2", "temperature": 0.1}
        ... )
    """

    category: str                           # Assigned category
    confidence: float                       # Confidence (0.0-1.0)
    reasoning: Optional[str] = None         # AI's explanation
    metadata: Optional[Dict[str, Any]] = None  # Additional data


# ==============================================================================
# PROTOCOL DEFINITIONS (Interfaces)
# ==============================================================================
#
# Protocols define contracts that implementations must follow.
# Think of them as "interfaces" from Java/C#.
#
# Benefits:
# - Dependency Inversion (depend on abstractions)
# - Easy to swap implementations
# - Easy to test (create mocks)
# - Type-safe (type checker verifies)

class DocumentExtractor(Protocol):
    """
    Protocol for document content extraction.

    WHAT IT IS:
        Contract that all document extractors must follow.

    WHO IMPLEMENTS THIS:
        - PDFExtractor (extract from PDFs)
        - DOCXExtractor (extract from Word documents)
        - ExcelExtractor (extract from Excel spreadsheets)
        - TextExtractor (extract from text files)

    WHY THIS EXISTS:
        - Allows swapping extractors without changing callers
        - Enables testing with mock extractors
        - Enforces consistent interface across all extractors

    Methods:
        can_extract(file_path): Returns True if this extractor handles this file
        extract(file_path): Extracts text + metadata from file

    Example usage:
        >>> def process_document(extractor: DocumentExtractor, path: Path):
        ...     if extractor.can_extract(path):
        ...         result = await extractor.extract(path)
        ...         if result.is_success:
        ...             print(result.value.text)
        >>>
        >>> # Can use ANY extractor that follows the protocol:
        >>> process_document(PDFExtractor(), Path("doc.pdf"))
        >>> process_document(DOCXExtractor(), Path("doc.docx"))
    """

    def can_extract(self, file_path: Path) -> bool:
        """
        Check if this extractor can handle the given file.

        Args:
            file_path: Path to the document file

        Returns:
            True if this extractor can handle it, False otherwise

        Why?
        - Different extractors handle different file types
        - PDFExtractor handles .pdf
        - DOCXExtractor handles .docx
        - This method lets us ask "can you handle this?"
        """
        ...

    async def extract(self, file_path: Path) -> Result[ExtractedContent]:
        """
        Extract content and metadata from the document.

        Args:
            file_path: Path to the document file

        Returns:
            Result containing ExtractedContent or error

        Why async?
        - Extraction can be slow (OCR takes seconds)
        - Allows other work while waiting
        - Essential for batch processing

        Why Result type?
        - Explicit error handling
        - No hidden exceptions
        - Caller must check success
        """
        ...


class OCRProcessor(Protocol):
    """
    Protocol for OCR text extraction from images.

    WHAT IT IS:
        Contract for OCR engines (Tesseract, Google Vision, etc.)

    WHO IMPLEMENTS THIS:
        - TesseractOCRService (uses Tesseract OCR)
        - Could add: GoogleVisionOCR, AmazonTextractOCR, etc.

    WHY THIS EXISTS:
        - Swap OCR engines without changing code
        - Test with mock OCR
        - Compare different OCR providers

    Methods:
        is_supported(file_path): Check if file format is supported
        extract_text(file_path): Extract text from image
        get_supported_formats(): List supported image formats
    """

    def is_supported(self, file_path: str) -> bool:
        """Check if the file format is supported for OCR."""
        ...

    async def extract_text(self, file_path: str, preprocess: bool = True) -> Result[OCRResult]:
        """Extract text from image file using OCR."""
        ...

    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats."""
        ...


class ClassificationService(Protocol):
    """
    Protocol for document classification.

    WHAT IT IS:
        Contract for AI classification services.

    WHO IMPLEMENTS THIS:
        - OllamaClassificationService (uses local Ollama)
        - Could add: OpenAIClassifier, ClaudeClassifier, etc.

    WHY THIS EXISTS:
        - Swap AI providers without changing code
        - Test with mock classifier
        - Compare different AI models

    Methods:
        classify_document(content, categories): Classify document
        is_available(): Check if service is running
    """

    async def classify_document(
        self,
        content: ExtractedContent,
        categories: List[str]
    ) -> Result[ClassificationResult]:
        """Classify document content into predefined categories."""
        ...

    async def is_available(self) -> bool:
        """Check if the classification service is available."""
        ...


class DocumentRepository(Protocol):
    """
    Protocol for document persistence.

    WHAT IT IS:
        Contract for storing/retrieving documents.

    WHO IMPLEMENTS THIS:
        - PostgreSQLRepository (uses PostgreSQL)
        - Could add: MongoDBRepository, ElasticsearchRepository, etc.

    WHY THIS EXISTS:
        - Swap databases without changing code
        - Test with in-memory repository
        - Support multiple storage backends
    """

    async def save(self, content: ExtractedContent) -> Result[UUID]:
        """Save extracted content to repository."""
        ...

    async def get_by_id(self, document_id: UUID) -> Result[ExtractedContent]:
        """Retrieve document by ID."""
        ...

    async def search(self, query: str) -> Result[List[ExtractedContent]]:
        """Search documents by text content."""
        ...


class FileOrganizer(Protocol):
    """
    Protocol for file organization operations.

    WHAT IT IS:
        Contract for organizing files into folders by category.

    WHO IMPLEMENTS THIS:
        - BasicFileOrganizer (moves/copies files to folders)
        - Could add: CloudFileOrganizer, NetworkFileOrganizer, etc.
    """

    async def organize_file(
        self,
        file_path: Path,
        category: str,
        base_output_dir: Path,
        copy_files: bool = False
    ) -> Result[Path]:
        """Organize file into appropriate category folder."""
        ...


class ConfigurationProvider(Protocol):
    """
    Protocol for configuration management.

    WHAT IT IS:
        Contract for accessing configuration settings.

    WHO IMPLEMENTS THIS:
        - Settings class from config.py
        - Could add: RemoteConfigProvider, DatabaseConfigProvider, etc.

    WHY THIS EXISTS:
        - Decouple configuration from code
        - Easy to test (mock config)
        - Support different config sources
    """

    def get_categories(self) -> List[str]:
        """Get list of classification categories."""
        ...

    def get_database_url(self) -> Optional[str]:
        """Get database connection URL."""
        ...

    def get_output_directory(self) -> Path:
        """Get output directory for organized files."""
        ...

    def use_database(self) -> bool:
        """Check if database storage is enabled."""
        ...


# ==============================================================================
# ABSTRACT BASE CLASSES (Shared Functionality)
# ==============================================================================

class BaseDocumentExtractor(ABC):
    """
    Abstract base class for document extractors.

    WHAT IT IS:
        Shared functionality for all extractors.

    PROTOCOL VS ABC:
        Protocol: Defines interface (structural typing)
        ABC: Provides shared implementation (inheritance)

    WHY BOTH?
        - Protocol: For dependency injection (loose coupling)
        - ABC: For code reuse (DRY - Don't Repeat Yourself)

    This provides:
        - _get_basic_metadata(): Get file system metadata (all extractors need this)
    """

    @abstractmethod
    def can_extract(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file."""
        pass

    @abstractmethod
    async def extract(self, file_path: Path) -> Result[ExtractedContent]:
        """Extract content and metadata from the document."""
        pass

    def _get_basic_metadata(self, file_path: Path) -> DocumentMetadata:
        """
        Extract basic file system metadata.

        This is shared by all extractors:
        - All extractors need file size, dates, etc.
        - No need to duplicate this code
        - Just call this helper method

        Returns:
            DocumentMetadata with filesystem info
        """
        return DocumentMetadata.from_file_stats(file_path)


# ==============================================================================
# CUSTOM EXCEPTIONS (Domain-Specific Errors)
# ==============================================================================

class DocumentExtractionError(Exception):
    """
    Raised when document extraction fails.

    Base exception for all extraction errors.

    Example:
        >>> raise DocumentExtractionError("Failed to extract PDF")
    """
    pass


class UnsupportedFormatError(DocumentExtractionError):
    """
    Raised when trying to extract from unsupported format.

    Example:
        >>> if file_path.suffix not in ['.pdf', '.docx']:
        ...     raise UnsupportedFormatError(f"Can't handle {file_path.suffix}")
    """
    pass


class OCRProcessingError(Exception):
    """
    Raised when OCR processing fails.

    Example:
        >>> raise OCRProcessingError("Tesseract not found")
    """
    pass


class ClassificationError(Exception):
    """
    Raised when document classification fails.

    Example:
        >>> raise ClassificationError("Ollama service not available")
    """
    pass


class ConfigurationError(Exception):
    """
    Raised when configuration is invalid or missing.

    Example:
        >>> if not database_url:
        ...     raise ConfigurationError("DATABASE_URL not set")
    """
    pass
