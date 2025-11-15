"""
Docling-Enhanced Metadata Extraction
======================================

Uses IBM's Docling library for superior document parsing before LLM extraction.

Improvements over basic text extraction:
- Preserves document structure (headings, tables, lists)
- Better handling of multi-column layouts
- OCR support for scanned documents
- Table extraction and formatting
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning("Docling not available - install with: pip install docling")

from llm_metadata_extractor import ConfigurableMetadataExtractor


class DoclingMetadataExtractor(ConfigurableMetadataExtractor):
    """
    Enhanced metadata extractor using Docling for document parsing.

    Combines Docling's advanced PDF/document parsing with LLM-based
    metadata extraction for superior results.
    """

    def __init__(
        self,
        schema_path: str = None,
        model: str = "llama3.2:3b",
        max_text_length: int = 6000,  # Increased for better structure preservation
        use_ocr: bool = True
    ):
        """
        Initialize enhanced extractor.

        Args:
            schema_path: Path to metadata schema YAML
            model: Ollama model for extraction
            max_text_length: Max text length (increased for structured content)
            use_ocr: Whether to use OCR for scanned documents
        """
        super().__init__(schema_path, model, max_text_length)

        if not DOCLING_AVAILABLE:
            raise ImportError(
                "Docling is required for DoclingMetadataExtractor. "
                "Install with: pip install docling"
            )

        # Initialize Docling converter
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = use_ocr
        pipeline_options.do_table_structure = True  # Extract table structure

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        self.use_ocr = use_ocr
        logger.info(f"Docling extractor initialized (OCR: {use_ocr})")

    def extract_from_file(
        self,
        file_path: str,
        category: str,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract metadata from a document file using Docling + LLM.

        Args:
            file_path: Path to document file (PDF, DOCX, etc.)
            category: Document category
            file_metadata: Additional metadata

        Returns:
            Extracted metadata dictionary
        """
        path = Path(file_path)

        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return file_metadata or {}

        logger.info(f"Processing with Docling: {path.name}")

        try:
            # Convert document using Docling
            result = self.doc_converter.convert(str(path))

            # Export to structured markdown
            markdown_text = result.document.export_to_markdown()

            logger.info(f"Docling extracted {len(markdown_text)} characters of structured text")

            # Extract metadata using LLM (parent class method)
            metadata = self.extract(
                text=markdown_text,
                category=category,
                file_metadata=file_metadata or {"file_name": path.name}
            )

            # Add Docling-specific metadata
            metadata['document_parser'] = 'docling'
            metadata['has_tables'] = self._check_for_tables(markdown_text)

            return metadata

        except Exception as e:
            logger.error(f"Docling processing failed: {e}")
            logger.exception(e)

            # Fallback to basic text extraction
            logger.warning("Falling back to basic text extraction")
            if path.suffix.lower() == '.txt':
                text = path.read_text()
                return self.extract(text, category, file_metadata or {"file_name": path.name})
            else:
                return file_metadata or {}

    def _check_for_tables(self, markdown_text: str) -> bool:
        """Check if document contains tables (markdown table syntax)."""
        # Look for markdown table indicators
        lines = markdown_text.split('\n')
        for line in lines:
            if '|' in line and '-' in line:
                return True
        return False

    def extract_from_text(
        self,
        text: str,
        category: str,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract from plain text (bypass Docling).

        For text-only content, use the parent LLM extraction directly.
        """
        return self.extract(text, category, file_metadata)


# Convenience function
def extract_metadata_from_file(
    file_path: str,
    category: str,
    model: str = "llama3.2:3b",
    use_ocr: bool = True
) -> Dict[str, Any]:
    """
    Extract metadata from a document file.

    Args:
        file_path: Path to document
        category: Document category
        model: Ollama model
        use_ocr: Use OCR for scanned docs

    Returns:
        Extracted metadata
    """
    extractor = DoclingMetadataExtractor(model=model, use_ocr=use_ocr)
    return extractor.extract_from_file(file_path, category)
