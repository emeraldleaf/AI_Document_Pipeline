# AI Document Pipeline - SOLID Architecture

## Overview

The AI Document Pipeline follows SOLID principles with a clean, Protocol-based architecture. This implementation separates concerns, improves testability, and makes the codebase maintainable and extensible.

## Architecture Layers

### 1. Domain Layer (`src/domain/`)

Contains the core business logic and defines contracts (protocols) for the system.

**Key Components:**
- **Protocols**: Interface definitions following Interface Segregation Principle
  - `DocumentExtractor`: Contract for document content extraction
  - `OCRProcessor`: Contract for OCR text extraction
  - `ClassificationService`: Contract for document classification
  - `ConfigurationProvider`: Contract for configuration management
  
- **Domain Models**: Immutable data classes with proper type hints
  - `DocumentMetadata`: Document metadata with UUID-based identity
  - `ExtractedContent`: Container for extracted document content
  - `OCRResult`: OCR processing results with confidence metrics
  - `ClassificationResult`: Classification results with reasoning
  - `Result[T]`: Generic result type for explicit error handling

- **Configuration**: Centralized configuration management
  - `AppConfiguration`: Immutable configuration dataclass
  - `DefaultConfigurationProvider`: Default implementation of config protocol

### 2. Services Layer (`src/services/`)

Contains core service implementations that implement domain protocols.

**Key Components:**
- **TesseractOCRService**: OCR implementation using Tesseract engine
- **OllamaClassificationService**: Classification using Ollama LLM
- **DocumentProcessingService**: Main orchestration service with dependency injection

### 3. Infrastructure Layer (`src/infrastructure/`)

Contains implementations that depend on external systems and frameworks.

**Key Components:**
- **Document Extractors**: Format-specific extraction implementations
  - `PDFExtractor`: PDF processing with OCR fallback
  - `ImageExtractor`: Image processing using OCR
  - `DOCXExtractor`: Word document processing
  - `ExcelExtractor`: Excel file processing
  - `TextExtractor`: Plain text file processing
- **ExtractionService**: Coordinated extraction with dependency injection

## SOLID Principles Implementation

### Single Responsibility Principle (SRP)
- Each class has a single, well-defined responsibility
- Services focus on one aspect (OCR, classification, extraction)
- Clear separation between domain logic and infrastructure concerns

### Open/Closed Principle (OCP)
- System is open for extension through new Protocol implementations
- Core domain logic is closed for modification
- New document formats can be added by implementing DocumentExtractor

### Liskov Substitution Principle (LSP)
- All implementations properly substitute their protocols
- Result types ensure consistent behavior across implementations
- Services can be swapped without breaking the system

### Interface Segregation Principle (ISP)
- Protocols are focused and don't force unnecessary dependencies
- Clients depend only on the methods they actually use
- OCR, extraction, and classification concerns are separated

### Dependency Inversion Principle (DIP)
- High-level modules depend on abstractions (protocols)
- Concrete implementations depend on abstractions
- Dependency injection enables easy testing and configuration

## Key Improvements

### 1. Error Handling with Result Type
```python
# Before: Exception-based error handling
try:
    content = extractor.extract(file_path)
except Exception as e:
    handle_error(e)

# After: Explicit Result type
result = await extractor.extract(file_path)
if result.is_success:
    content = result.value
else:
    handle_error(result.error)
```

### 2. Dependency Injection
```python
# Before: Hard-coded dependencies
class DocumentClassifier:
    def __init__(self):
        self.ollama = OllamaService()  # Hard dependency
        self.extractor = ExtractionService()  # Hard dependency

# After: Protocol-based injection
class DocumentProcessingService:
    def __init__(
        self,
        extraction_service: DocumentExtractor,
        classification_service: ClassificationService,
        config: ConfigurationProvider,
    ):
        self.extraction_service = extraction_service
        self.classification_service = classification_service
        self.config = config
```

### 3. Immutable Domain Models
```python
@dataclass(frozen=True)
class DocumentMetadata:
    """Immutable document metadata."""
    id: UUID
    file_path: Path
    file_name: str
    # ... other fields
    
    @classmethod
    def from_file_stats(cls, file_path: Path) -> "DocumentMetadata":
        """Factory method for creation."""
        # ...
```

### 4. Configuration Management
```python
# Centralized, type-safe configuration
@dataclass(frozen=True)
class AppConfiguration:
    input_directory: Path
    output_directory: Path
    categories: List[str]
    ocr_language: str
    # ... other settings
    
    @classmethod
    def from_env(cls) -> "AppConfiguration":
        """Load from environment variables."""
        # ...
```

## Usage Examples

### Basic Document Processing
```python
from src import load_configuration, create_extraction_service
from src.services import create_ollama_service, create_document_processing_service

# Load configuration
config = load_configuration()

# Create services with dependency injection
ocr_service = TesseractOCRService()
extraction_service = create_extraction_service(ocr_service)
classification_service = create_ollama_service(config)

# Create main processing service
document_service = await create_document_processing_service(
    extraction_service=extraction_service,
    classification_service=classification_service,
    config=config,
)

# Process document
result = await document_service.process_document(Path("document.pdf"))
if result.success:
    print(f"Category: {result.category}")
    print(f"Confidence: {result.confidence}")
```

### Modern CLI Usage
```python
# New CLI with dependency injection
python main.py check  # Check service availability
python main.py process input_dir/ --copy --reasoning
python main.py categories  # List available categories
python main.py info --format json  # System information
```


## Testing Benefits

The architecture greatly improves testability:

1. **Protocol Mocking**: Easy to mock interfaces for unit tests
2. **Dependency Injection**: Services can be tested in isolation
3. **Result Types**: Explicit error handling simplifies test assertions
4. **Immutable Models**: Thread-safe, predictable behavior

## Performance Considerations

- **Async Operations**: OCR and classification are now async for better performance
- **Lazy Loading**: Services are created only when needed
- **Resource Management**: Proper cleanup and resource handling
- **Memory Efficiency**: Immutable models prevent accidental mutations

## Development Guide

### Adding New Features
1. Implement new document formats by creating Protocol implementations
2. Use the Result type for all operations that can fail
3. Follow the dependency injection pattern for service composition
4. Write unit tests using Protocol mocking

## Security Improvements

- **Input Validation**: Proper validation at domain boundaries
- **Type Safety**: Strong typing prevents runtime errors
- **Error Isolation**: Explicit error handling prevents information leakage
- **Configuration Security**: Centralized, validated configuration management

This architecture provides a solid foundation for development with high code quality, testability, and maintainability.

---

## See Also

### Architecture Documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component overview
- **[OCR_IMPLEMENTATION.md](OCR_IMPLEMENTATION.md)** - OCR capabilities and integration

### Code Quality
- **[CODACY_ANALYSIS_REPORT.md](CODACY_ANALYSIS_REPORT.md)** - Code quality analysis report

### Testing
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing strategy and organization
- **[END_TO_END_TESTING_GUIDE.md](END_TO_END_TESTING_GUIDE.md)** - Complete testing guide
- **[TESTING_QUICK_REFERENCE.md](TESTING_QUICK_REFERENCE.md)** - Quick testing commands

---

**Last Updated:** October 2025