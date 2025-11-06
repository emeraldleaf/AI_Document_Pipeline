"""
Domain layer of the AI Document Pipeline.

This module contains the core business logic, protocols (interfaces),
and domain models following SOLID principles.
"""

from .protocols import (
    # Data classes
    DocumentMetadata,
    ExtractedContent,
    Result,
    OCRResult,
    ClassificationResult,
    
    # Protocols
    DocumentExtractor,
    OCRProcessor,
    ClassificationService,
    DocumentRepository,
    FileOrganizer,
    ConfigurationProvider,
    
    # Abstract base classes
    BaseDocumentExtractor,
    
    # Exceptions
    DocumentExtractionError,
    UnsupportedFormatError,
    OCRProcessingError,
    ClassificationError,
    ConfigurationError,
)

from .configuration import (
    AppConfiguration,
    DefaultConfigurationProvider,
    setup_logging,
    load_configuration,
)

__all__ = [
    # Data classes
    "DocumentMetadata",
    "ExtractedContent", 
    "Result",
    "OCRResult",
    "ClassificationResult",
    
    # Protocols
    "DocumentExtractor",
    "OCRProcessor", 
    "ClassificationService",
    "DocumentRepository",
    "FileOrganizer",
    "ConfigurationProvider",
    
    # Abstract base classes
    "BaseDocumentExtractor",
    
    # Exceptions
    "DocumentExtractionError",
    "UnsupportedFormatError",
    "OCRProcessingError", 
    "ClassificationError",
    "ConfigurationError",
    
    # Configuration
    "AppConfiguration",
    "DefaultConfigurationProvider",
    "setup_logging",
    "load_configuration",
]