"""Document splitting and chunking for page-level and section-level classification."""

from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from loguru import logger

from src.extractors import ExtractedContent, DocumentMetadata


class SplitMode(Enum):
    """Document splitting modes."""

    NONE = "none"  # Process entire document as one unit (default)
    PAGES = "pages"  # Split by pages (for PDFs)
    SECTIONS = "sections"  # Split by sections/headings
    CHUNKS = "chunks"  # Split by character/token chunks
    SMART = "smart"  # Intelligent splitting based on content


@dataclass
class DocumentSection:
    """Represents a section or chunk of a document."""

    content: str
    section_number: int
    section_type: str  # 'page', 'section', 'chunk'
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    heading: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __len__(self) -> int:
        """Return content length."""
        return len(self.content)


class DocumentSplitter:
    """Split documents into pages, sections, or chunks for independent classification."""

    def __init__(
        self,
        split_mode: SplitMode = SplitMode.NONE,
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
        min_section_size: int = 100,
    ):
        """Initialize document splitter.

        Args:
            split_mode: How to split documents
            chunk_size: Size of chunks (for CHUNKS mode)
            chunk_overlap: Overlap between chunks
            min_section_size: Minimum size for a section (chars)
        """
        self.split_mode = split_mode
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_section_size = min_section_size

    def split(self, extracted: ExtractedContent) -> List[DocumentSection]:
        """Split extracted content based on split mode.

        Args:
            extracted: Extracted document content

        Returns:
            List of document sections
        """
        if self.split_mode == SplitMode.NONE:
            return self._no_split(extracted)
        elif self.split_mode == SplitMode.PAGES:
            return self._split_by_pages(extracted)
        elif self.split_mode == SplitMode.SECTIONS:
            return self._split_by_sections(extracted)
        elif self.split_mode == SplitMode.CHUNKS:
            return self._split_by_chunks(extracted)
        elif self.split_mode == SplitMode.SMART:
            return self._smart_split(extracted)
        else:
            return self._no_split(extracted)

    def _no_split(self, extracted: ExtractedContent) -> List[DocumentSection]:
        """Return entire document as single section (default behavior)."""
        return [
            DocumentSection(
                content=extracted.text,
                section_number=1,
                section_type="full_document",
                start_page=1,
                end_page=extracted.metadata.page_count,
                metadata=extracted.metadata.to_dict(),
            )
        ]

    def _split_by_pages(self, extracted: ExtractedContent) -> List[DocumentSection]:
        """Split document by pages (PDF page-level classification).

        Useful for multi-format documents where each page is a different type.
        """
        if not extracted.pages:
            logger.warning("No page data available, treating as single document")
            return self._no_split(extracted)

        sections = []

        for page_num, page_content in enumerate(extracted.pages, 1):
            if len(page_content.strip()) < self.min_section_size:
                logger.debug(f"Skipping page {page_num} (too small)")
                continue

            section = DocumentSection(
                content=page_content,
                section_number=page_num,
                section_type="page",
                start_page=page_num,
                end_page=page_num,
                heading=f"Page {page_num}",
                metadata=extracted.metadata.to_dict(),
            )
            sections.append(section)

        logger.info(f"Split into {len(sections)} pages")
        return sections

    def _split_by_sections(self, extracted: ExtractedContent) -> List[DocumentSection]:
        """Split document by sections based on headings.

        Detects section headers and splits accordingly.
        """
        text = extracted.text
        lines = text.split('\n')

        sections = []
        current_section = []
        current_heading = None
        section_num = 0

        # Simple heuristic: Lines that are short, capitalized, or end with ':'
        for line in lines:
            line_stripped = line.strip()

            # Check if this looks like a heading
            is_heading = (
                line_stripped and
                len(line_stripped) < 100 and
                (
                    line_stripped.isupper() or
                    line_stripped.endswith(':') or
                    (line_stripped[0].isupper() and len(line_stripped.split()) <= 10)
                )
            )

            if is_heading and len(current_section) > 0:
                # Save previous section
                section_content = '\n'.join(current_section)
                if len(section_content.strip()) >= self.min_section_size:
                    section_num += 1
                    sections.append(
                        DocumentSection(
                            content=section_content,
                            section_number=section_num,
                            section_type="section",
                            heading=current_heading,
                            metadata=extracted.metadata.to_dict(),
                        )
                    )

                # Start new section
                current_section = []
                current_heading = line_stripped
            else:
                current_section.append(line)

        # Add final section
        if current_section:
            section_content = '\n'.join(current_section)
            if len(section_content.strip()) >= self.min_section_size:
                section_num += 1
                sections.append(
                    DocumentSection(
                        content=section_content,
                        section_number=section_num,
                        section_type="section",
                        heading=current_heading,
                        metadata=extracted.metadata.to_dict(),
                    )
                )

        if not sections:
            # If no sections detected, return whole document
            logger.warning("No sections detected, using full document")
            return self._no_split(extracted)

        logger.info(f"Split into {len(sections)} sections")
        return sections

    def _split_by_chunks(self, extracted: ExtractedContent) -> List[DocumentSection]:
        """Split document into fixed-size chunks with overlap.

        Useful for very large documents or when you want consistent chunk sizes.
        """
        text = extracted.text
        sections = []

        start = 0
        section_num = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at a sentence/paragraph boundary
            if end < len(text):
                # Look for period, newline, or space within last 100 chars
                search_start = max(end - 100, start)
                best_break = text.rfind('.', search_start, end)
                if best_break == -1:
                    best_break = text.rfind('\n', search_start, end)
                if best_break == -1:
                    best_break = text.rfind(' ', search_start, end)
                if best_break != -1:
                    end = best_break + 1

            chunk = text[start:end].strip()

            if len(chunk) >= self.min_section_size:
                section_num += 1
                sections.append(
                    DocumentSection(
                        content=chunk,
                        section_number=section_num,
                        section_type="chunk",
                        heading=f"Chunk {section_num}",
                        metadata=extracted.metadata.to_dict(),
                    )
                )

            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break

        logger.info(f"Split into {len(sections)} chunks")
        return sections

    def _smart_split(self, extracted: ExtractedContent) -> List[DocumentSection]:
        """Intelligent splitting based on content analysis.

        Uses multiple heuristics to determine best split strategy.
        """
        # If we have page data and it's a PDF, try page splitting first
        if extracted.pages and len(extracted.pages) > 1:
            # Check if pages have significantly different content
            avg_page_length = sum(len(p) for p in extracted.pages) / len(extracted.pages)
            variance = sum((len(p) - avg_page_length) ** 2 for p in extracted.pages) / len(extracted.pages)

            # High variance suggests different content types per page
            if variance > 1000:
                logger.info("Smart split: Using page-level (high content variance)")
                return self._split_by_pages(extracted)

        # Check for clear section markers
        text = extracted.text
        section_markers = [
            line for line in text.split('\n')
            if line.strip() and len(line.strip()) < 100 and
            (line.strip().isupper() or line.strip().endswith(':'))
        ]

        if len(section_markers) >= 3:
            logger.info("Smart split: Using section-level (section markers found)")
            return self._split_by_sections(extracted)

        # For very large documents, use chunking
        if len(text) > 10000:
            logger.info("Smart split: Using chunks (large document)")
            return self._split_by_chunks(extracted)

        # Otherwise, process as whole document
        logger.info("Smart split: Using full document (no clear split points)")
        return self._no_split(extracted)


class SectionClassificationResult:
    """Result of classifying document sections."""

    def __init__(
        self,
        file_path: Path,
        sections: List[Tuple[DocumentSection, str, Optional[str]]],
        dominant_category: Optional[str] = None,
    ):
        """Initialize section classification result.

        Args:
            file_path: Original file path
            sections: List of (section, category, confidence) tuples
            dominant_category: Most common category across sections
        """
        self.file_path = file_path
        self.sections = sections
        self.dominant_category = dominant_category

    @property
    def is_mixed(self) -> bool:
        """Check if document has mixed categories."""
        categories = set(cat for _, cat, _ in self.sections)
        return len(categories) > 1

    def get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of categories across sections."""
        distribution = {}
        for _, category, _ in self.sections:
            distribution[category] = distribution.get(category, 0) + 1
        return distribution

    def get_sections_by_category(self, category: str) -> List[DocumentSection]:
        """Get all sections classified as a specific category."""
        return [section for section, cat, _ in self.sections if cat == category]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": str(self.file_path),
            "file_name": self.file_path.name,
            "is_mixed": self.is_mixed,
            "dominant_category": self.dominant_category,
            "category_distribution": self.get_category_distribution(),
            "sections": [
                {
                    "section_number": section.section_number,
                    "section_type": section.section_type,
                    "category": category,
                    "confidence": confidence,
                    "heading": section.heading,
                    "content_length": len(section.content),
                    "start_page": section.start_page,
                    "end_page": section.end_page,
                }
                for section, category, confidence in self.sections
            ],
        }


def merge_section_results(
    section_results: List[Tuple[DocumentSection, str, Optional[str]]]
) -> str:
    """Determine dominant category from section classifications.

    Args:
        section_results: List of (section, category, confidence) tuples

    Returns:
        Dominant category (most frequent)
    """
    if not section_results:
        return "other"

    # Count categories
    category_counts = {}
    for _, category, _ in section_results:
        category_counts[category] = category_counts.get(category, 0) + 1

    # Return most common
    return max(category_counts.items(), key=lambda x: x[1])[0]


def should_split_document(
    extracted: ExtractedContent,
    split_mode: SplitMode,
) -> bool:
    """Determine if document should be split.

    Args:
        extracted: Extracted content
        split_mode: Requested split mode

    Returns:
        True if document should be split
    """
    if split_mode == SplitMode.NONE:
        return False

    if split_mode == SplitMode.PAGES:
        return bool(extracted.pages and len(extracted.pages) > 1)

    if split_mode == SplitMode.SECTIONS:
        # Check if document has section markers
        text = extracted.text
        markers = [
            line for line in text.split('\n')[:100]  # Check first 100 lines
            if line.strip() and len(line.strip()) < 100 and line.strip().isupper()
        ]
        return len(markers) >= 2

    if split_mode == SplitMode.CHUNKS:
        return len(extracted.text) > 2000

    if split_mode == SplitMode.SMART:
        return True  # Smart mode decides internally

    return False
