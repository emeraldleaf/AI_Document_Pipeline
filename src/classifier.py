"""
==============================================================================
DOCUMENT CLASSIFIER - Orchestration and Workflow Management
==============================================================================

PURPOSE:
    Orchestrate the complete document classification workflow:
    Extract → Classify → Store → Organize

WHAT THIS FILE DOES:
    - Coordinates between extraction, classification, and storage services
    - Manages batch processing workflows
    - Organizes classified files into folders
    - Tracks results and generates reports

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │                   DocumentClassifier                         │
    │                  (Orchestration Layer)                       │
    │                                                              │
    │  classify_document():                                        │
    │    1. Extract text (ExtractionService)                      │
    │    2. Classify (OllamaService)                              │
    │    3. Store (DatabaseService - optional)                    │
    │    4. Return ClassificationResult                           │
    │                                                              │
    │  classify_batch():                                           │
    │    Loop over documents, call classify_document()            │
    │                                                              │
    │  classify_directory():                                       │
    │    Scan directory → collect files → classify_batch()        │
    └─────────────────────────────────────────────────────────────┘

WORKFLOW:
    User Input (file/directory)
           ↓
    DocumentClassifier.classify_document()
           ↓
    ┌─────────────────────────────────────────────────┐
    │ 1. ExtractionService.extract()                 │
    │    - Read file (PDF, DOCX, Excel, etc.)        │
    │    - Extract text + metadata                    │
    └─────────────────────────────────────────────────┘
           ↓
    ┌─────────────────────────────────────────────────┐
    │ 2. OllamaService.classify_document()           │
    │    - Build prompt with text + metadata          │
    │    - Send to AI (Ollama)                        │
    │    - Get category + confidence                  │
    └─────────────────────────────────────────────────┘
           ↓
    ┌─────────────────────────────────────────────────┐
    │ 3. DatabaseService.add_document() [optional]   │
    │    - Store text, category, metadata             │
    │    - Store embeddings for semantic search      │
    └─────────────────────────────────────────────────┘
           ↓
    ClassificationResult (category, confidence, metadata)
           ↓
    DocumentOrganizer.organize() [optional]
    - Move/copy files to category folders

DESIGN PATTERNS:
    - **Facade Pattern**: Simplifies complex subsystem interactions
    - **Dependency Injection**: Services injected into constructor
    - **Chain of Responsibility**: Extract → Classify → Store pipeline

KEY CONCEPTS:
    1. **Orchestration**: Coordinating multiple services
    2. **Batch Processing**: Process many documents efficiently
    3. **Result Tracking**: Accumulate and export results
    4. **File Organization**: Move classified files to folders

EXAMPLE USAGE:
    ```python
    from pathlib import Path
    from src.classifier import DocumentClassifier, DocumentOrganizer

    # Create classifier
    classifier = DocumentClassifier(use_database=True)

    # Classify a single document
    result = classifier.classify_document(
        Path("documents/invoice.pdf"),
        include_reasoning=True
    )
    print(f"Category: {result.category}")
    print(f"Reasoning: {result.confidence}")

    # Classify entire directory
    results = classifier.classify_directory(
        Path("documents/input"),
        recursive=True
    )

    # Export results to JSON
    classifier.export_results(Path("results.json"))

    # Organize files into folders
    organizer = DocumentOrganizer(output_dir=Path("documents/organized"))
    organizer.organize(results, copy_files=True)
    ```

RELATED FILES:
    - src/extractors.py - Document content extraction
    - src/ollama_service.py - AI classification
    - src/database.py - Database storage (optional)
    - src/parallel_processor.py - For high-throughput batches

AUTHOR: AI Document Pipeline Team
LAST UPDATED: October 2025
"""

import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from loguru import logger
from tqdm import tqdm

from src.extractors import ExtractionService, ExtractedContent
from src.ollama_service import OllamaService
from config import settings

# Optional database support
# Not all installations have PostgreSQL configured
try:
    from src.database import DatabaseService, check_database_available
    DATABASE_AVAILABLE = check_database_available()
except ImportError:
    DATABASE_AVAILABLE = False
    DatabaseService = None


# ==============================================================================
# DATA MODELS
# ==============================================================================

class ClassificationResult:
    """
    Container for classification results.

    WHAT IT IS:
        Simple data container holding classification output.

    Attributes:
        file_path: Path to the classified document
        category: Assigned category (e.g., "invoices")
        confidence: Confidence or reasoning from AI (optional)
        metadata: Document metadata (file info, dates, etc.)
        timestamp: When classification occurred
        db_id: Database ID if stored (optional)

    Why not use dataclass?
    - Legacy code compatibility
    - Mutable (can update db_id after creation)
    - Simple and explicit

    Example:
        >>> result = ClassificationResult(
        ...     file_path=Path("invoice.pdf"),
        ...     category="invoices",
        ...     confidence="Contains invoice number and amount",
        ...     metadata={"file_size": 52428, "pages": 2}
        ... )
    """

    def __init__(
        self,
        file_path: Path,
        category: str,
        confidence: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        db_id: Optional[int] = None,
    ):
        """
        Initialize classification result.

        Args:
            file_path: Path to the classified document
            category: Assigned category
            confidence: AI reasoning or confidence score
            metadata: Document metadata
            timestamp: When classified (default: now)
            db_id: Database ID if stored
        """
        self.file_path = file_path
        self.category = category
        self.confidence = confidence
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        self.db_id = db_id

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON export.

        Returns:
            Dictionary with all result fields

        Why?
        - JSON export (for reports, APIs)
        - Database insertion
        - Logging

        Example:
            >>> result.to_dict()
            {'file_path': 'invoice.pdf', 'category': 'invoices', ...}
        """
        return {
            "file_path": str(self.file_path),
            "file_name": self.file_path.name,
            "category": self.category,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


# ==============================================================================
# DOCUMENT CLASSIFIER (Main Orchestrator)
# ==============================================================================

class DocumentClassifier:
    """
    Main classifier for document organization.

    WHAT IT DOES:
        Orchestrates the complete classification workflow:
        1. Extract text from documents
        2. Classify using AI
        3. Store in database (optional)
        4. Track and export results

    DESIGN PATTERN:
        Facade Pattern - Provides simple interface to complex subsystems

    KEY FEATURES:
        - **Single Document**: classify_document()
        - **Batch Processing**: classify_batch()
        - **Directory Scanning**: classify_directory()
        - **Result Tracking**: Accumulates all results
        - **Statistics**: Category distribution, export to JSON
        - **Database Integration**: Optional storage

    DEPENDENCY INJECTION:
        Services are injected into constructor for:
        - Testability (can inject mocks)
        - Flexibility (can use different implementations)
        - Loose coupling (doesn't create its own dependencies)

    EXAMPLE:
        >>> # Basic usage
        >>> classifier = DocumentClassifier()
        >>> result = classifier.classify_document(Path("doc.pdf"))
        >>>
        >>> # With database storage
        >>> classifier = DocumentClassifier(use_database=True)
        >>>
        >>> # With custom services (for testing)
        >>> mock_ollama = MockOllamaService()
        >>> classifier = DocumentClassifier(ollama_service=mock_ollama)
    """

    def __init__(
        self,
        ollama_service: Optional[OllamaService] = None,
        extraction_service: Optional[ExtractionService] = None,
        use_database: Optional[bool] = None,
    ):
        """
        Initialize document classifier.

        Args:
            ollama_service: Ollama AI service (default: create new)
            extraction_service: Document extraction service (default: create new)
            use_database: Enable database storage (default: from config)

        What happens during initialization:
        1. Set up services (Ollama, Extractor)
        2. Load categories from config
        3. Initialize result storage
        4. Set up database connection (if enabled)

        Why dependency injection?
        - Testing: Can inject mock services
        - Flexibility: Can use different implementations
        - Configuration: Can customize behavior per instance

        Example:
            >>> # Default (creates own services)
            >>> classifier = DocumentClassifier()
            >>>
            >>> # Custom services (e.g., for testing)
            >>> mock_ollama = MockOllamaService()
            >>> classifier = DocumentClassifier(ollama_service=mock_ollama)
            >>>
            >>> # With database
            >>> classifier = DocumentClassifier(use_database=True)
        """
        # Step 1: Initialize services (or use provided ones)
        #
        # Why allow injection?
        # - Testing: Pass mock services
        # - Reuse: Share service instances across classifiers
        # - Configuration: Different configs per classifier
        self.ollama = ollama_service or OllamaService()
        self.extractor = extraction_service or ExtractionService()

        # Step 2: Load categories from configuration
        #
        # Categories are the possible document types:
        # ["invoices", "contracts", "reports", "receipts", "other"]
        self.categories = settings.category_list

        # Step 3: Initialize result storage
        #
        # We accumulate results as we process documents.
        # This allows us to generate statistics and exports.
        self.results: List[ClassificationResult] = []

        # Step 4: Set up database storage (optional)
        #
        # Database storage is optional because:
        # - Not all users have PostgreSQL
        # - Simple use cases don't need persistence
        # - Can process without database
        self.use_database = use_database if use_database is not None else settings.use_database
        self.db = None

        if self.use_database:
            if DATABASE_AVAILABLE:
                try:
                    self.db = DatabaseService(database_url=settings.database_url)
                    logger.info("Database storage enabled")
                except Exception as e:
                    logger.warning(f"Failed to initialize database: {e}")
                    self.use_database = False
            else:
                logger.warning("Database requested but SQLAlchemy not installed")
                self.use_database = False

    # ==========================================================================
    # CLASSIFICATION METHODS
    # ==========================================================================

    def classify_document(
        self,
        file_path: Path,
        include_reasoning: bool = False,
    ) -> Optional[ClassificationResult]:
        """
        Classify a single document.

        This is the core classification method. It orchestrates:
        1. Text extraction
        2. AI classification
        3. Database storage (optional)

        Args:
            file_path: Path to the document
            include_reasoning: Include AI reasoning in result (slower)

        Returns:
            ClassificationResult with category, or None if failed

        Flow:
            file_path
               ↓
            Extract text (ExtractionService)
               ↓
            Classify (OllamaService)
               ↓
            Store (DatabaseService - optional)
               ↓
            Return ClassificationResult

        Example:
            >>> result = classifier.classify_document(
            ...     Path("invoice.pdf"),
            ...     include_reasoning=True
            ... )
            >>> if result:
            ...     print(f"Category: {result.category}")
            ...     print(f"Reasoning: {result.confidence}")

        Why might it return None?
        - Extraction failed (corrupted file, unsupported format)
        - Classification failed (Ollama not running, AI error)
        - File doesn't exist
        """
        logger.info(f"Classifying: {file_path.name}")

        # Step 1: Extract content from document
        #
        # This reads the file and extracts:
        # - Text content
        # - Metadata (file size, pages, dates, etc.)
        #
        # Why separate extraction from classification?
        # - Different concerns (file I/O vs AI)
        # - Can extract once, classify multiple times
        # - Can cache extracted content
        extracted = self.extractor.extract(file_path)

        if not extracted:
            logger.error(f"Failed to extract content from {file_path.name}")
            return None

        # Step 2: Classify using AI
        #
        # Two modes:
        # A) With reasoning: Get category + AI's explanation (slower)
        # B) Without reasoning: Just get category (faster)
        #
        # Why two modes?
        # - Reasoning is useful for debugging/auditing
        # - But it's slower (AI generates more text)
        # - Choose based on use case
        if include_reasoning:
            # Mode A: Get category + reasoning
            classification = self.ollama.classify_with_confidence(
                content=extracted.text,
                metadata=extracted.metadata.to_dict(),
                categories=self.categories,
            )

            if classification:
                result = ClassificationResult(
                    file_path=file_path,
                    category=classification["category"],
                    confidence=classification.get("reasoning"),  # AI's explanation
                    metadata=extracted.metadata.to_dict(),
                )
            else:
                return None

        else:
            # Mode B: Just get category (faster)
            category = self.ollama.classify_document(
                content=extracted.text,
                metadata=extracted.metadata.to_dict(),
                categories=self.categories,
            )

            if category:
                result = ClassificationResult(
                    file_path=file_path,
                    category=category,
                    metadata=extracted.metadata.to_dict(),
                )
            else:
                return None

        # Step 3: Store result for later (statistics, export)
        self.results.append(result)

        # Step 4: Store in database if enabled
        #
        # Database storage is optional but useful for:
        # - Persistence (results survive across runs)
        # - Search (find documents by content)
        # - Analytics (query patterns, statistics)
        # - Audit trail (who classified what when)
        if self.use_database and self.db:
            try:
                doc_id = self.db.add_document(
                    file_path=file_path,
                    category=result.category,
                    content=extracted.text,
                    metadata=result.metadata,
                    confidence=result.confidence,
                    model_used=self.ollama.model,
                    store_full_content=settings.store_full_content,
                )

                # Store database ID in result for reference
                result.db_id = doc_id

            except Exception as e:
                # Database error doesn't fail classification
                # We log it and continue
                logger.error(f"Failed to store in database: {e}")

        return result

    def classify_batch(
        self,
        file_paths: List[Path],
        include_reasoning: bool = False,
        show_progress: bool = True,
    ) -> List[ClassificationResult]:
        """
        Classify multiple documents.

        This is a convenience wrapper around classify_document().
        It processes documents sequentially with a progress bar.

        Args:
            file_paths: List of document paths
            include_reasoning: Include AI reasoning
            show_progress: Show progress bar (default: True)

        Returns:
            List of classification results (successful only)

        Why sequential (not parallel)?
        - This is the simple/basic batch method
        - For parallel processing, use parallel_processor.py
        - For async processing, use async_batch_processor.py
        - For distributed processing, use celery_tasks.py

        Flow:
            for each file:
                classify_document(file)
                add to results list
            return results

        Example:
            >>> files = [Path("doc1.pdf"), Path("doc2.pdf"), ...]
            >>> results = classifier.classify_batch(files)
            >>> print(f"Classified {len(results)} documents")

        When to use this vs parallel_processor?
        - Small batches (<100 documents): Use this (simple)
        - Large batches (1000+ documents): Use parallel_processor (fast)
        - Production workloads: Use celery_tasks (scalable)
        """
        results = []

        # Create progress bar if requested
        #
        # tqdm shows real-time progress:
        # Classifying documents: 45%|████      | 450/1000 [01:23<01:42, 5.38doc/s]
        #
        # Why optional?
        # - CLI: Show progress (user-friendly)
        # - Scripts: Hide progress (cleaner logs)
        iterator = tqdm(file_paths, desc="Classifying documents") if show_progress else file_paths

        # Process each document
        for file_path in iterator:
            result = self.classify_document(file_path, include_reasoning)
            if result:
                results.append(result)
            # If result is None, we skip it (already logged error)

        logger.info(f"Successfully classified {len(results)}/{len(file_paths)} documents")
        return results

    def classify_directory(
        self,
        input_dir: Path,
        recursive: bool = True,
        include_reasoning: bool = False,
    ) -> List[ClassificationResult]:
        """
        Classify all documents in a directory.

        Convenience method that:
        1. Scans directory for supported files
        2. Calls classify_batch() to process them

        Args:
            input_dir: Directory containing documents
            recursive: Also process subdirectories (default: True)
            include_reasoning: Include AI reasoning

        Returns:
            List of classification results

        Supported file types:
        - PDF (.pdf)
        - Word (.docx, .doc)
        - Excel (.xlsx, .xls)
        - Text (.txt, .md)

        Flow:
            Scan directory → Collect files → classify_batch()

        Example:
            >>> results = classifier.classify_directory(
            ...     Path("documents/input"),
            ...     recursive=True
            ... )
            >>> # Processes all documents in input/ and subdirectories

        When to use recursive=True vs False?
        - True: Process all subdirectories (good for organized archives)
        - False: Only process top level (good for flat directories)
        """
        logger.info(f"Scanning directory: {input_dir}")

        # Step 1: Define supported file extensions
        supported_extensions = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md"}

        # Step 2: Collect all matching files
        file_paths = []

        if recursive:
            # rglob searches recursively (all subdirectories)
            for ext in supported_extensions:
                file_paths.extend(input_dir.rglob(f"*{ext}"))
        else:
            # glob searches only specified directory
            for ext in supported_extensions:
                file_paths.extend(input_dir.glob(f"*{ext}"))

        logger.info(f"Found {len(file_paths)} documents to classify")

        # Step 3: Handle edge case - no files found
        if not file_paths:
            logger.warning("No documents found to classify")
            return []

        # Step 4: Process all files
        return self.classify_batch(file_paths, include_reasoning)

    # ==========================================================================
    # STATISTICS AND EXPORT
    # ==========================================================================

    def get_category_distribution(self) -> Dict[str, int]:
        """
        Get distribution of documents across categories.

        Returns:
            Dictionary mapping category → count

        Example:
            >>> distribution = classifier.get_category_distribution()
            >>> print(distribution)
            {'invoices': 45, 'contracts': 23, 'reports': 12, 'other': 5}

        Useful for:
        - Understanding document composition
        - Generating reports
        - Validating classification quality
        """
        # Initialize with all categories at 0
        distribution = {cat: 0 for cat in self.categories}

        # Count results per category
        for result in self.results:
            if result.category in distribution:
                distribution[result.category] += 1

        return distribution

    def export_results(self, output_path: Path):
        """
        Export classification results to JSON.

        Creates a JSON file with:
        - Summary statistics
        - Category distribution
        - Individual results for each document

        Args:
            output_path: Where to save JSON file

        Example:
            >>> classifier.export_results(Path("results.json"))

            # Results file contains:
            {
              "timestamp": "2025-10-30T12:34:56",
              "total_documents": 85,
              "categories": ["invoices", "contracts", ...],
              "distribution": {
                "invoices": 45,
                "contracts": 23,
                ...
              },
              "results": [
                {
                  "file_path": "invoice_001.pdf",
                  "category": "invoices",
                  "confidence": "Contains invoice number...",
                  ...
                },
                ...
              ]
            }

        Why export to JSON?
        - Human-readable format
        - Easy to parse with other tools
        - Can import into spreadsheets
        - Version control friendly
        """
        # Build export data structure
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_documents": len(self.results),
            "categories": self.categories,
            "distribution": self.get_category_distribution(),
            "results": [result.to_dict() for result in self.results],
        }

        # Write to file with nice formatting
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.success(f"Exported results to {output_path}")

    def clear_results(self):
        """
        Clear stored results.

        Use this to reset the classifier between batches:
        - Free memory
        - Start fresh statistics
        - Process new batch independently

        Example:
            >>> classifier.classify_directory(Path("batch1"))
            >>> classifier.export_results(Path("batch1_results.json"))
            >>> classifier.clear_results()  # Reset for next batch
            >>> classifier.classify_directory(Path("batch2"))
        """
        self.results.clear()


# ==============================================================================
# DOCUMENT ORGANIZER (File Management)
# ==============================================================================

class DocumentOrganizer:
    """
    Organizes documents into folders based on classification.

    WHAT IT DOES:
        Takes classification results and organizes files:
        - Creates category folders
        - Moves/copies files to appropriate folders
        - Handles duplicate filenames
        - Creates manifest (record of moves)

    WORKFLOW:
        Classification Results
               ↓
        Create category folders (invoices/, contracts/, ...)
               ↓
        For each document:
            Move/copy to category folder
            Handle duplicates (append _1, _2, etc.)
               ↓
        Create manifest.json (record of all moves)

    EXAMPLE:
        Before:
        documents/
            invoice_001.pdf
            contract_002.pdf
            report_003.pdf

        After organize():
        documents/organized/
            invoices/
                invoice_001.pdf
            contracts/
                contract_002.pdf
            reports/
                report_003.pdf
            organization_manifest.json

    USAGE:
        >>> from src.classifier import DocumentClassifier, DocumentOrganizer
        >>>
        >>> # Classify documents
        >>> classifier = DocumentClassifier()
        >>> results = classifier.classify_directory(Path("documents"))
        >>>
        >>> # Organize files
        >>> organizer = DocumentOrganizer(output_dir=Path("documents/organized"))
        >>> summary = organizer.organize(results, copy_files=True)
        >>> print(f"Organized {summary['successful']} files")
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize document organizer.

        Args:
            output_dir: Base output directory (default: from config)

        Example:
            >>> organizer = DocumentOrganizer()  # Uses config output dir
            >>> organizer = DocumentOrganizer(Path("/data/organized"))  # Custom
        """
        # Use provided directory or fall back to config
        self.output_dir = output_dir or settings.output_folder

        # Track moved files for manifest
        self.moved_files: List[Dict[str, str]] = []

    def organize(
        self,
        results: List[ClassificationResult],
        copy_files: bool = False,
        create_manifest: bool = True,
    ) -> Dict[str, Any]:
        """
        Organize documents into category folders.

        This moves or copies files to folders based on classification.

        Args:
            results: Classification results (from classifier)
            copy_files: Copy instead of move (default: False = move)
            create_manifest: Create manifest.json (default: True)

        Returns:
            Summary dictionary with statistics:
                - total_files: How many processed
                - successful: How many organized successfully
                - failed: How many failed
                - operation: "moved" or "copied"

        Flow:
            1. Create category folders (if they don't exist)
            2. For each result:
                - Determine destination folder
                - Handle duplicate filenames
                - Move or copy file
                - Track in moved_files list
            3. Create manifest (optional)
            4. Return summary

        Why copy vs move?
        - Copy: Keep originals (safer, uses more disk space)
        - Move: Save disk space (can't undo easily)

        Duplicate handling:
        - invoice.pdf exists → save as invoice_1.pdf
        - invoice_1.pdf exists → save as invoice_2.pdf
        - etc.

        Example:
            >>> results = classifier.classify_directory(Path("docs"))
            >>> summary = organizer.organize(
            ...     results,
            ...     copy_files=True,  # Keep originals
            ...     create_manifest=True  # Create record
            ... )
            >>> print(f"{summary['successful']} files organized")
            85 files organized
        """
        logger.info(f"Organizing {len(results)} documents")

        # Step 1: Ensure output directories exist
        #
        # Create a folder for each category:
        # output_dir/
        #     invoices/
        #     contracts/
        #     reports/
        #     ...
        for result in results:
            category_dir = self.output_dir / result.category
            category_dir.mkdir(parents=True, exist_ok=True)

        # Step 2: Move/copy files
        success_count = 0
        error_count = 0

        # Process each result with progress bar
        for result in tqdm(results, desc="Organizing files"):
            try:
                # Determine source and destination
                source = result.file_path
                destination_dir = self.output_dir / result.category
                destination = destination_dir / source.name

                # Step 3: Handle duplicate filenames
                #
                # If destination already exists, append counter:
                # invoice.pdf → invoice_1.pdf → invoice_2.pdf
                #
                # Why?
                # - Multiple documents might have same name
                # - Don't want to overwrite existing files
                # - Keep all documents
                if destination.exists():
                    stem = source.stem  # "invoice" from "invoice.pdf"
                    suffix = source.suffix  # ".pdf" from "invoice.pdf"
                    counter = 1

                    # Find available filename
                    while destination.exists():
                        destination = destination_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                # Step 4: Move or copy file
                if copy_files:
                    # Copy: Keep original
                    shutil.copy2(source, destination)
                    logger.debug(f"Copied {source.name} to {result.category}/")
                else:
                    # Move: Remove original
                    shutil.move(str(source), str(destination))
                    logger.debug(f"Moved {source.name} to {result.category}/")

                # Step 5: Track the move for manifest
                self.moved_files.append({
                    "source": str(source),
                    "destination": str(destination),
                    "category": result.category,
                })

                success_count += 1

            except Exception as e:
                # File operation failed (permissions, disk full, etc.)
                logger.error(f"Failed to organize {result.file_path.name}: {e}")
                error_count += 1

        # Step 6: Build summary
        summary = {
            "total_files": len(results),
            "successful": success_count,
            "failed": error_count,
            "operation": "copied" if copy_files else "moved",
        }

        # Step 7: Create manifest (record of all moves)
        if create_manifest:
            manifest_path = self.output_dir / "organization_manifest.json"
            self._create_manifest(results, manifest_path)

        logger.success(f"Organization complete: {success_count} files organized, {error_count} failed")
        return summary

    def _create_manifest(self, results: List[ClassificationResult], output_path: Path):
        """
        Create a manifest file with organization details.

        The manifest is a JSON file that records:
        - When organization happened
        - Which files were moved where
        - Category summary

        Args:
            results: Classification results
            output_path: Where to save manifest

        Manifest format:
        {
          "timestamp": "2025-10-30T12:34:56",
          "total_files": 85,
          "moved_files": [
            {
              "source": "/docs/invoice.pdf",
              "destination": "/organized/invoices/invoice.pdf",
              "category": "invoices"
            },
            ...
          ],
          "category_summary": {
            "invoices": [
              {"filename": "invoice_001.pdf", "confidence": "..."},
              ...
            ],
            ...
          }
        }

        Why create a manifest?
        - Audit trail (what was moved where)
        - Can undo moves if needed
        - Record for compliance/documentation
        - Helps troubleshoot issues
        """
        # Build manifest data structure
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(results),
            "moved_files": self.moved_files,
            "category_summary": {},
        }

        # Count files per category and list them
        for result in results:
            category = result.category
            if category not in manifest["category_summary"]:
                manifest["category_summary"][category] = []

            manifest["category_summary"][category].append({
                "filename": result.file_path.name,
                "confidence": result.confidence,
            })

        # Write to JSON file
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Created manifest: {output_path}")
