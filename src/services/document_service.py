"""
Document processing orchestration service implementing dependency injection.
This is the main entry point that coordinates all document processing operations.
"""

import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..domain import (
    DocumentExtractor,
    OCRProcessor,
    ClassificationService,
    ConfigurationProvider,
    ExtractedContent,
    ClassificationResult as DomainClassificationResult,
    Result,
    DocumentExtractionError,
    ClassificationError,
)


logger = logging.getLogger(__name__)


class ProcessingResult:
    """Container for document processing results."""

    def __init__(
        self,
        file_path: Path,
        category: str,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        extracted_content: Optional[ExtractedContent] = None,
        error: Optional[str] = None,
    ):
        self.file_path = file_path
        self.category = category
        self.confidence = confidence
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        self.extracted_content = extracted_content
        self.error = error
        self.success = error is None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": str(self.file_path),
            "file_name": self.file_path.name,
            "category": self.category,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error": self.error,
        }


class DocumentProcessingService:
    """
    Main service for document processing and classification.
    Uses dependency injection for all core services.
    """

    def __init__(
        self,
        extraction_service: DocumentExtractor,
        classification_service: ClassificationService,
        config: ConfigurationProvider,
    ):
        """
        Initialize document processing service.

        Args:
            extraction_service: Service for document content extraction
            classification_service: Service for document classification
            config: Configuration provider
        """
        self.extraction_service = extraction_service
        self.classification_service = classification_service
        self.config = config
        self.results: List[ProcessingResult] = []

        logger.info("Document processing service initialized")

    async def process_document(
        self,
        file_path: Path,
        copy_files: bool = False,
        include_reasoning: bool = False,
    ) -> ProcessingResult:
        """
        Process a single document: extract content and classify.

        Args:
            file_path: Path to the document to process
            copy_files: Whether to copy files to organized folders
            include_reasoning: Include classification reasoning in metadata

        Returns:
            ProcessingResult with classification and metadata
        """
        try:
            if not file_path.exists():
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                return ProcessingResult(
                    file_path=file_path,
                    category="error",
                    error=error_msg
                )

            # Extract content from document
            logger.info(f"Processing document: {file_path}")
            extraction_result = await self.extraction_service.extract(file_path)

            if not extraction_result.is_success:
                error_msg = f"Failed to extract content: {extraction_result.error}"
                logger.error(error_msg)
                return ProcessingResult(
                    file_path=file_path,
                    category="error",
                    error=error_msg
                )

            extracted_content = extraction_result.value

            # Check if content is meaningful
            if not extracted_content.text.strip():
                logger.warning(f"No extractable text found in: {file_path}")
                return ProcessingResult(
                    file_path=file_path,
                    category="other",
                    confidence=0.0,
                    extracted_content=extracted_content,
                    metadata={"warning": "No extractable text found"}
                )

            # Classify the document
            categories = self.config.get_categories()
            classification_result = await self.classification_service.classify_document(
                extracted_content, categories
            )

            if not classification_result.is_success:
                error_msg = f"Classification failed: {classification_result.error}"
                logger.error(error_msg)
                return ProcessingResult(
                    file_path=file_path,
                    category="other",
                    confidence=0.0,
                    extracted_content=extracted_content,
                    error=error_msg
                )

            classification = classification_result.value

            # Prepare metadata
            metadata = {
                "file_size": extracted_content.metadata.file_size,
                "file_type": extracted_content.metadata.file_type,
                "word_count": len(extracted_content.text.split()),
                "page_count": extracted_content.metadata.page_count,
            }

            if include_reasoning and classification.reasoning:
                metadata["reasoning"] = classification.reasoning

            if classification.metadata:
                metadata.update(classification.metadata)

            # Organize file if requested
            if copy_files:
                try:
                    output_dir = self.config.get_output_directory()
                    organized_path = await self._organize_file(
                        file_path, classification.category, output_dir, copy_files
                    )
                    metadata["organized_path"] = str(organized_path)
                except Exception as e:
                    logger.warning(f"Failed to organize file: {e}")
                    metadata["organization_error"] = str(e)

            result = ProcessingResult(
                file_path=file_path,
                category=classification.category,
                confidence=classification.confidence,
                metadata=metadata,
                extracted_content=extracted_content,
            )

            self.results.append(result)
            logger.info(
                f"Document processed: {file_path.name} -> {classification.category} "
                f"(confidence: {classification.confidence:.2f})"
            )

            return result

        except Exception as e:
            error_msg = f"Unexpected error processing document {file_path}: {e}"
            logger.error(error_msg)
            return ProcessingResult(
                file_path=file_path,
                category="error",
                error=error_msg
            )

    async def process_directory(
        self,
        input_dir: Path,
        copy_files: bool = False,
        include_reasoning: bool = False,
        pattern: str = "*",
    ) -> List[ProcessingResult]:
        """
        Process all documents in a directory.

        Args:
            input_dir: Directory containing documents to process
            copy_files: Whether to copy files to organized folders
            include_reasoning: Include classification reasoning in metadata
            pattern: File pattern to match (default: all files)

        Returns:
            List of ProcessingResult objects
        """
        if not input_dir.exists():
            logger.error(f"Input directory not found: {input_dir}")
            return []

        # Find all files matching pattern
        files = list(input_dir.rglob(pattern))
        document_files = [f for f in files if f.is_file()]

        if not document_files:
            logger.warning(f"No files found in {input_dir} matching pattern '{pattern}'")
            return []

        logger.info(f"Processing {len(document_files)} documents from {input_dir}")

        # Process each document
        results = []
        for file_path in document_files:
            result = await self.process_document(
                file_path, copy_files, include_reasoning
            )
            results.append(result)

        # Log summary
        successful = len([r for r in results if r.success])
        logger.info(
            f"Completed processing: {successful}/{len(results)} documents successful"
        )

        return results

    async def _organize_file(
        self,
        file_path: Path,
        category: str,
        base_output_dir: Path,
        copy_files: bool = False,
    ) -> Path:
        """Organize file into appropriate category folder."""
        category_dir = base_output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        destination = category_dir / file_path.name

        # Handle filename conflicts
        if destination.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            counter = 1
            while destination.exists():
                destination = category_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        if copy_files:
            shutil.copy2(file_path, destination)
            logger.debug(f"Copied file to: {destination}")
        else:
            shutil.move(str(file_path), destination)
            logger.debug(f"Moved file to: {destination}")

        return destination

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of all processing results."""
        if not self.results:
            return {"total": 0, "successful": 0, "failed": 0, "categories": {}}

        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        # Count by category
        categories = {}
        for result in successful:
            category = result.category
            categories[category] = categories.get(category, 0) + 1

        return {
            "total": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "categories": categories,
            "average_confidence": (
                sum(r.confidence or 0 for r in successful) / len(successful)
                if successful else 0
            ),
        }

    def export_results(self, output_path: Path) -> None:
        """Export processing results to JSON file."""
        results_data = {
            "summary": self.get_processing_summary(),
            "results": [result.to_dict() for result in self.results],
            "exported_at": datetime.now().isoformat(),
        }

        with open(output_path, 'w') as f:
            import json
            json.dump(results_data, f, indent=2)

        logger.info(f"Results exported to: {output_path}")


# Factory function for easy service creation
async def create_document_processing_service(
    extraction_service: DocumentExtractor,
    classification_service: ClassificationService,
    config: ConfigurationProvider,
) -> DocumentProcessingService:
    """
    Factory function to create a configured document processing service.

    Args:
        extraction_service: Configured extraction service
        classification_service: Configured classification service
        config: Configuration provider

    Returns:
        Configured DocumentProcessingService
    """
    # Verify services are available
    if not await classification_service.is_available():
        logger.warning("Classification service is not available")

    return DocumentProcessingService(
        extraction_service=extraction_service,
        classification_service=classification_service,
        config=config,
    )