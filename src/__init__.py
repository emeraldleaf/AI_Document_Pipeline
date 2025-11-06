"""
AI Document Pipeline - A comprehensive document processing and classification system.

This package follows SOLID principles with a clean architecture:
- Domain layer: Core business logic and protocols
- Services layer: Core service implementations
- Infrastructure layer: External system integrations
"""

__version__ = "1.0.0"
__author__ = "AI Document Pipeline Team"
__description__ = "A comprehensive document processing and classification system"

# Main component exports
from .domain import (
    DocumentMetadata,
    ExtractedContent,
    Result,
    OCRResult,
    ClassificationResult,
    load_configuration,
)

from .services import (
    TesseractOCRService,
    ImageProcessor,
    OllamaClassificationService,
    DocumentProcessingService,
    ProcessingResult,
)

from .infrastructure import (
    ExtractionService,
    create_extraction_service,
)

__all__ = [
    # Domain models
    "DocumentMetadata",
    "ExtractedContent",
    "Result",
    "OCRResult",
    "ClassificationResult",

    # Services
    "TesseractOCRService",
    "ImageProcessor",
    "OllamaClassificationService",
    "DocumentProcessingService",
    "ProcessingResult",

    # Infrastructure
    "ExtractionService",
    "create_extraction_service",

    # Configuration
    "load_configuration",
]
