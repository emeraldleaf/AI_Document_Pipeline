"""Unit tests for document extractors."""

import pytest
from pathlib import Path
from src.extractors import (
    PDFExtractor,
    DOCXExtractor,
    ExcelExtractor,
    TextExtractor,
    ExtractionService,
)


class TestPDFExtractor:
    """Test PDF extraction functionality."""

    def test_can_extract_pdf(self):
        """Test PDF file detection."""
        extractor = PDFExtractor()
        assert extractor.can_extract(Path("document.pdf"))
        assert extractor.can_extract(Path("document.PDF"))
        assert not extractor.can_extract(Path("document.docx"))

    def test_extract_pdf(self, tmp_path):
        """Test PDF extraction (requires actual PDF)."""
        # This test requires a sample PDF file
        # In production, you would create a sample PDF or use a fixture
        pass


class TestDOCXExtractor:
    """Test DOCX extraction functionality."""

    def test_can_extract_docx(self):
        """Test DOCX file detection."""
        extractor = DOCXExtractor()
        assert extractor.can_extract(Path("document.docx"))
        assert extractor.can_extract(Path("document.doc"))
        assert extractor.can_extract(Path("document.DOCX"))
        assert not extractor.can_extract(Path("document.pdf"))


class TestExcelExtractor:
    """Test Excel extraction functionality."""

    def test_can_extract_excel(self):
        """Test Excel file detection."""
        extractor = ExcelExtractor()
        assert extractor.can_extract(Path("spreadsheet.xlsx"))
        assert extractor.can_extract(Path("spreadsheet.xls"))
        assert extractor.can_extract(Path("spreadsheet.xlsm"))
        assert not extractor.can_extract(Path("document.pdf"))


class TestTextExtractor:
    """Test text file extraction."""

    def test_can_extract_text(self):
        """Test text file detection."""
        extractor = TextExtractor()
        assert extractor.can_extract(Path("document.txt"))
        assert extractor.can_extract(Path("document.md"))
        assert extractor.can_extract(Path("data.csv"))
        assert extractor.can_extract(Path("config.json"))
        assert not extractor.can_extract(Path("document.pdf"))

    def test_extract_text(self, tmp_path):
        """Test text file extraction."""
        extractor = TextExtractor()

        # Create a test text file
        test_file = tmp_path / "test.txt"
        test_content = "This is a test document.\nWith multiple lines."
        test_file.write_text(test_content)

        # Extract content
        result = extractor.extract(test_file)

        # Verify
        assert result is not None
        assert result.text == test_content
        assert result.metadata.file_name == "test.txt"
        assert result.metadata.page_count == 1


class TestExtractionService:
    """Test extraction service orchestration."""

    def test_service_initialization(self):
        """Test service initializes with all extractors."""
        service = ExtractionService()
        assert len(service.extractors) == 5  # Updated for ImageExtractor

    def test_extract_nonexistent_file(self):
        """Test handling of nonexistent files."""
        service = ExtractionService()
        result = service.extract(Path("nonexistent.pdf"))
        assert result is None

    def test_extract_unsupported_format(self, tmp_path):
        """Test handling of unsupported file formats."""
        service = ExtractionService()

        # Create an unsupported file type
        test_file = tmp_path / "test.unsupported"
        test_file.write_text("test content")

        result = service.extract(test_file)
        assert result is None
