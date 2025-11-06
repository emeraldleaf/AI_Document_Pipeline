"""
Unit tests for the new Protocol-based architecture.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from uuid import UUID

from src.domain import (
    DocumentMetadata,
    ExtractedContent,
    Result,
    OCRResult,
    ClassificationResult,
    AppConfiguration,
    DefaultConfigurationProvider,
)
from src.services import (
    TesseractOCRService,
    OllamaClassificationService,
    DocumentProcessingService,
)
from src.infrastructure import (
    PDFExtractor,
    ImageExtractor,
    DOCXExtractor,
    ExcelExtractor,
    TextExtractor,
    ExtractionService,
)


class TestDomainModels:
    """Test domain models and data classes."""
    
    def test_document_metadata_creation(self):
        """Test DocumentMetadata creation."""
        metadata = DocumentMetadata.from_file_stats(Path(__file__))
        
        assert isinstance(metadata.id, UUID)
        assert metadata.file_path == Path(__file__)
        assert metadata.file_name == Path(__file__).name
        assert metadata.file_size > 0
        assert metadata.created_date is not None
        assert metadata.modified_date is not None
    
    def test_extracted_content_creation(self):
        """Test ExtractedContent creation."""
        metadata = DocumentMetadata.from_file_stats(Path(__file__))
        content = ExtractedContent(
            text="Sample text content",
            metadata=metadata,
            pages=["Page 1", "Page 2"]
        )
        
        assert content.text == "Sample text content"
        assert content.metadata == metadata
        assert len(content.pages) == 2
        assert content.get_summary(10) == "Sample tex..."
    
    def test_result_type_success(self):
        """Test Result type for successful operations."""
        result = Result.success("test value")
        
        assert result.is_success
        assert result.value == "test value"
        assert result.error is None
        assert result.unwrap() == "test value"
        assert result.unwrap_or("default") == "test value"
    
    def test_result_type_failure(self):
        """Test Result type for failed operations."""
        result = Result.failure("test error")
        
        assert not result.is_success
        assert result.value is None
        assert result.error == "test error"
        assert result.unwrap_or("default") == "default"
        
        with pytest.raises(ValueError, match="Result failed: test error"):
            result.unwrap()
    
    def test_app_configuration(self):
        """Test application configuration."""
        config = AppConfiguration()
        
        assert config.input_directory == Path("documents/input")
        assert config.output_directory == Path("documents/output")
        assert config.temp_directory == Path("documents/temp")
        assert "invoice" in config.categories
        assert config.ocr_language == "eng"
        assert config.ocr_min_confidence == 60.0
    
    def test_configuration_provider(self):
        """Test configuration provider."""
        config = AppConfiguration()
        provider = DefaultConfigurationProvider(config)
        
        assert len(provider.get_categories()) > 0
        assert provider.get_output_directory() == Path("documents/output")
        assert provider.use_database() == False


class TestOCRService:
    """Test OCR service implementation."""
    
    def test_tesseract_service_initialization(self):
        """Test TesseractOCRService initialization."""
        service = TesseractOCRService()
        
        assert service.language == "eng"
        assert len(service.get_supported_formats()) > 0
        assert service.is_supported("test.png")
        assert service.is_supported("test.jpg")
        assert not service.is_supported("test.pdf")
    
    @pytest.mark.asyncio
    async def test_ocr_service_extract_text_unsupported(self):
        """Test OCR service with unsupported format."""
        service = TesseractOCRService()
        
        result = await service.extract_text("test.pdf")
        
        assert not result.is_success
        assert "Unsupported format" in result.error
    
    @pytest.mark.asyncio
    async def test_ocr_service_extract_text_nonexistent(self):
        """Test OCR service with nonexistent file."""
        service = TesseractOCRService()
        
        result = await service.extract_text("nonexistent.png")
        
        assert not result.is_success
        assert "File not found" in result.error


class TestClassificationService:
    """Test classification service implementation."""
    
    def test_ollama_service_initialization(self):
        """Test OllamaClassificationService initialization."""
        service = OllamaClassificationService()
        
        assert service.host == "http://localhost:11434"
        assert service.model == "llama3.2"
        assert service.timeout == 120
        assert service.temperature == 0.1
    
    @pytest.mark.asyncio
    async def test_classification_service_unavailable(self):
        """Test classification when service is unavailable."""
        service = OllamaClassificationService()
        
        # Mock the is_available method to return False
        with patch.object(service, 'is_available', return_value=False):
            metadata = DocumentMetadata.from_file_stats(Path(__file__))
            content = ExtractedContent("test content", metadata)
            
            result = await service.classify_document(content, ["invoice", "other"])
            
            assert not result.is_success
            assert "not available" in result.error


class TestExtractors:
    """Test document extractors."""
    
    def test_pdf_extractor_can_extract(self):
        """Test PDF extractor file detection."""
        extractor = PDFExtractor()
        
        assert extractor.can_extract(Path("test.pdf"))
        assert extractor.can_extract(Path("test.PDF"))
        assert not extractor.can_extract(Path("test.docx"))
    
    def test_image_extractor_initialization(self):
        """Test Image extractor requires OCR service."""
        with pytest.raises(TypeError):
            # Should fail without OCR service
            ImageExtractor()
    
    def test_docx_extractor_can_extract(self):
        """Test DOCX extractor file detection."""
        extractor = DOCXExtractor()
        
        assert extractor.can_extract(Path("test.docx"))
        assert extractor.can_extract(Path("test.DOCX"))
        assert not extractor.can_extract(Path("test.pdf"))
    
    def test_excel_extractor_can_extract(self):
        """Test Excel extractor file detection."""
        extractor = ExcelExtractor()
        
        assert extractor.can_extract(Path("test.xlsx"))
        assert extractor.can_extract(Path("test.xls"))
        assert not extractor.can_extract(Path("test.pdf"))
    
    def test_text_extractor_can_extract(self):
        """Test Text extractor file detection."""
        extractor = TextExtractor()
        
        assert extractor.can_extract(Path("test.txt"))
        assert extractor.can_extract(Path("test.md"))
        assert extractor.can_extract(Path("test.csv"))
        assert not extractor.can_extract(Path("test.pdf"))


class TestInfrastructureIntegration:
    """Test infrastructure layer integration."""
    
    def test_extraction_service_creation(self):
        """Test extraction service creation with factory function."""
        from src.infrastructure import create_extraction_service
        
        service = create_extraction_service()
        
        assert isinstance(service, ExtractionService)
        assert len(service.extractors) >= 4  # At least PDF, DOCX, Excel, Text
    
    @pytest.mark.asyncio
    async def test_extraction_service_nonexistent_file(self):
        """Test extraction service with nonexistent file."""
        service = ExtractionService([])
        
        result = await service.extract_content(Path("nonexistent.pdf"))
        
        assert not result.is_success
        assert "File not found" in result.error


class TestDocumentProcessingService:
    """Test the main document processing service."""
    
    @pytest.mark.asyncio
    async def test_document_processing_service_creation(self):
        """Test creating document processing service."""
        from src.services import create_document_processing_service
        from src.infrastructure import create_extraction_service
        
        # Create mock services
        extraction_service = create_extraction_service()
        classification_service = Mock()
        classification_service.is_available = AsyncMock(return_value=True)
        
        config = DefaultConfigurationProvider(AppConfiguration())
        
        service = await create_document_processing_service(
            extraction_service=extraction_service,
            classification_service=classification_service,
            config=config,
        )
        
        assert isinstance(service, DocumentProcessingService)
        assert service.extraction_service == extraction_service
        assert service.classification_service == classification_service
        assert service.config == config


class TestModuleExports:
    """Test main module exports."""

    def test_main_module_exports(self):
        """Test main module exports are available."""
        import src

        # Test that main exports are available
        assert hasattr(src, 'DocumentMetadata')
        assert hasattr(src, 'ExtractedContent')
        assert hasattr(src, 'Result')
        assert hasattr(src, 'TesseractOCRService')
        assert hasattr(src, 'ExtractionService')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])