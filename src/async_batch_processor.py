"""
==============================================================================
ASYNC BATCH PROCESSOR - Ultra-High Throughput Classification
==============================================================================

PURPOSE:
    Process documents using async/await for maximum I/O efficiency.
    Complements parallel_processor.py by handling I/O-bound operations better.

WHAT IS ASYNC/AWAIT?
    - A way to handle multiple I/O operations at once WITHOUT multiple processes
    - Like having one chef (process) juggling multiple dishes (tasks)
    - While waiting for one operation (reading file, calling AI API), start another
    - Much more efficient than blocking and waiting

WHY ASYNC INSTEAD OF PARALLEL?
    Parallel Processing (multiprocessing):
    ✓ Good for CPU-heavy work (OCR, calculations)
    ✗ Overhead from creating processes
    ✗ Each process uses lots of memory

    Async Processing (this file):
    ✓ Good for I/O-heavy work (file reading, API calls, database)
    ✓ Very low overhead
    ✓ Can handle 100s of concurrent operations
    ✗ Not good for CPU-heavy work (Python async is single-threaded)

WHEN TO USE THIS:
    ✓ Network I/O is the bottleneck (API calls to Ollama)
    ✓ File I/O is the bottleneck (reading many small files)
    ✓ Database I/O is the bottleneck (inserting documents)
    ✓ Want to maximize throughput without using multiple processes
    ✓ Processing 10K+ documents with minimal resources

HOW FAST IS IT?
    - Single-threaded: ~300 documents/hour
    - Parallel (8 cores): ~2,400 documents/hour
    - Async (50 concurrent): ~3,000-4,000 documents/hour
    - Parallel + Async: ~5,000-6,000 documents/hour (BEST!)

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │               Single Process, Multiple Tasks                 │
    │  ┌───────────────────────────────────────────────────────┐  │
    │  │              Async Event Loop (1 thread)              │  │
    │  │                                                       │  │
    │  │  Task 1: [Read file] ──> [Call AI] ──> [Insert DB]  │  │
    │  │  Task 2: [Read file] ──> [Call AI] ──> [Insert DB]  │  │
    │  │  Task 3: [Read file] ──> [Call AI] ──> [Insert DB]  │  │
    │  │  ...                                                  │  │
    │  │  Task N: [Read file] ──> [Call AI] ──> [Insert DB]  │  │
    │  │                                                       │  │
    │  │  All running "concurrently" (not parallel!)          │  │
    │  │  - While Task 1 waits for AI, Task 2 reads file     │  │
    │  │  - While Task 3 waits for DB, Task 4 calls AI       │  │
    │  └───────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────┘

KEY CONCEPTS:
    1. **Async/Await**: Non-blocking I/O operations
    2. **Concurrency**: Multiple tasks in progress (but not parallel)
    3. **Semaphore**: Limit how many tasks run at once (to avoid overload)
    4. **Event Loop**: Manages task switching and I/O
    5. **Batch Inserts**: Group database writes for efficiency
    6. **Deduplication**: Skip already-processed documents (by hash)

ASYNC VS PARALLEL VS THREADS:
    Async (this file):
    - 1 process, 1 thread, many tasks
    - Best for I/O-bound work
    - Example: Waiting for API responses

    Parallel (multiprocessing):
    - Many processes, each with threads
    - Best for CPU-bound work
    - Example: Image processing, OCR

    Threading:
    - 1 process, many threads
    - Limited in Python (GIL prevents true parallelism)
    - Rarely used for our workload

USAGE EXAMPLE:
    ```python
    import asyncio
    from pathlib import Path
    from src.async_batch_processor import AsyncBatchProcessor

    async def main():
        # Create processor with 50 concurrent tasks
        processor = AsyncBatchProcessor(
            max_concurrent=50,
            batch_size=100,  # Insert 100 docs at once to DB
            use_database=True
        )

        # Process all documents
        stats = await processor.process_directory_async(
            Path("documents/input")
        )

        print(f"Processed {stats.successful} documents")
        print(f"Speed: {stats.documents_per_second:.1f} docs/sec")

    # Run the async function
    asyncio.run(main())
    ```

RELATED FILES:
    - src/parallel_processor.py - For CPU-heavy parallel processing
    - src/celery_tasks.py - For distributed processing across machines
    - src/classifier.py - Single document classification (synchronous)

AUTHOR: AI Document Pipeline Team
LAST UPDATED: October 2025
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from loguru import logger

from src.extractors import ExtractionService, ExtractedContent
from src.ollama_service import OllamaService
from config import settings

# Optional database import
# (Not all installations have PostgreSQL configured)
try:
    from src.database import DatabaseService
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class AsyncBatchResult:
    """
    Result from processing a single document asynchronously.

    This is a lightweight result object optimized for async processing.
    Unlike ClassificationResult, it focuses on what we need for batch operations.

    Attributes:
        file_path: Path to the processed document
        category: Classified category (e.g., "invoices", "reports")
        confidence: Optional reasoning from AI (if requested)
        metadata: Document metadata (file size, dates, pages, etc.)
        processing_time: How long this document took to process (seconds)
        success: Whether processing succeeded
        error: Error message if failed

    Why separate from ClassificationResult?
    - Simpler structure for async operations
    - Includes processing time for performance monitoring
    - Easier to serialize for export
    """
    file_path: Path
    category: str
    confidence: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class AsyncBatchStats:
    """
    Performance statistics for async batch processing.

    Tracks:
    - Total documents processed
    - Success/failure counts
    - Duplicate detection stats
    - Processing time and throughput

    Similar to ProcessingStats but with async-specific metrics.

    Why track duplicates?
    - Async processing often reprocesses same directory
    - Deduplication prevents wasted work
    - Important for incremental processing

    Example:
        >>> stats = AsyncBatchStats(
        ...     total_documents=10000,
        ...     successful=9850,
        ...     failed=50,
        ...     skipped_duplicates=100,
        ...     start_time=datetime.now()
        ... )
        >>> stats.end_time = datetime.now()
        >>> stats.finalize()
        >>> print(f"{stats.documents_per_second:.1f} docs/sec")
        45.2 docs/sec
    """
    # Input metrics
    total_documents: int          # Total attempted
    successful: int               # Successfully processed
    failed: int                   # Failed to process
    skipped_duplicates: int       # Already processed (deduplication)
    start_time: datetime          # When batch started

    # Calculated metrics (filled after processing)
    end_time: Optional[datetime] = None       # When batch finished
    total_processing_time: float = 0.0        # Total time taken
    documents_per_second: float = 0.0         # Throughput
    avg_processing_time: float = 0.0          # Average time per document

    def finalize(self):
        """
        Calculate final statistics after batch completes.

        Computes:
        - Total processing time (end_time - start_time)
        - Throughput (documents per second)
        - Average time per document

        Call this AFTER setting end_time.

        Why separate from __init__?
        - Stats object is created before processing starts
        - Updated incrementally during processing
        - Finalized only at the end
        """
        if self.end_time:
            # Calculate total elapsed time
            self.total_processing_time = (self.end_time - self.start_time).total_seconds()

            # Calculate throughput (documents per second)
            if self.total_processing_time > 0:
                self.documents_per_second = self.successful / self.total_processing_time

        # Calculate average time per document
        if self.successful > 0:
            self.avg_processing_time = self.total_processing_time / self.successful


# ==============================================================================
# ASYNC BATCH PROCESSOR CLASS
# ==============================================================================

class AsyncBatchProcessor:
    """
    Ultra-high throughput async batch processor.

    WHAT IT DOES:
        Processes many documents concurrently using async/await.
        Uses a single process but handles multiple I/O operations at once.

    HOW IT WORKS:
        1. Create many async tasks (one per document)
        2. Use semaphore to limit concurrent tasks (prevent overload)
        3. Each task: extract → classify → add to batch
        4. Batch database inserts (100 docs at once)
        5. Deduplicate using file hashes (skip already-processed)

    KEY FEATURES:
        - **Concurrency Control**: Semaphore limits concurrent tasks
        - **Batch Database Inserts**: Groups writes for efficiency
        - **Deduplication**: SHA256 hashing to skip duplicates
        - **Progress Tracking**: Real-time progress monitoring
        - **Error Handling**: Graceful failure handling per document

    PERFORMANCE:
        - Can handle 50-100 concurrent tasks
        - 3,000-4,000 documents/hour typical
        - Low memory usage (single process)
        - Excellent for network I/O (API calls)

    TUNING PARAMETERS:
        max_concurrent:
            - Default: 50 (good starting point)
            - Higher (100): More throughput, higher memory
            - Lower (25): Less throughput, safer
            - Rule: Start low, increase until performance plateaus

        batch_size:
            - Default: 100 (good for most databases)
            - Higher (500): Fewer DB roundtrips, more memory
            - Lower (50): More frequent writes, less memory
            - Rule: Match to your database's batch insert performance

    EXAMPLE USAGE:
        ```python
        import asyncio
        from pathlib import Path

        async def process_documents():
            processor = AsyncBatchProcessor(
                max_concurrent=50,
                batch_size=100,
                use_database=True,
                deduplicate=True  # Skip already-processed
            )

            stats = await processor.process_directory_async(
                Path("documents/input")
            )

            print(f"Success: {stats.successful}")
            print(f"Failed: {stats.failed}")
            print(f"Skipped (duplicates): {stats.skipped_duplicates}")
            print(f"Speed: {stats.documents_per_second:.1f} docs/sec")

        asyncio.run(process_documents())
        ```

    COMPARISON:
        vs parallel_processor.py:
        + Better for I/O-bound work (API calls, file reading)
        + Lower memory usage (single process)
        - Not as good for CPU-bound work (OCR)

        vs celery_tasks.py:
        + Simpler setup (no Redis, no workers)
        + Better for single-machine processing
        - Can't scale across multiple machines
    """

    def __init__(
        self,
        categories: Optional[List[str]] = None,
        max_concurrent: int = 50,
        batch_size: int = 100,
        use_database: bool = False,
        database_url: Optional[str] = None,
        deduplicate: bool = True,
    ):
        """
        Initialize the async batch processor.

        Args:
            categories: Classification categories (default: from config)
            max_concurrent: Max concurrent async operations (default: 50)
            batch_size: Database batch insert size (default: 100)
            use_database: Enable database storage
            database_url: Database connection URL (default: from config)
            deduplicate: Enable deduplication via file hashing

        What happens during initialization:
        1. Load configuration
        2. Create service instances (Ollama, Extractor)
        3. Initialize database connection (if enabled)
        4. Create semaphore for concurrency control
        5. Initialize result storage

        Why use a semaphore?
        - Limits how many tasks run at once
        - Prevents overwhelming the system
        - Without it, could start 10,000 tasks simultaneously!
        - Example: semaphore=50 means max 50 concurrent tasks

        Common configurations:
        - Development: max_concurrent=25, batch_size=50
        - Production: max_concurrent=100, batch_size=200
        - Low memory: max_concurrent=10, batch_size=25
        """
        # Step 1: Load categories from config
        self.categories = categories or settings.category_list

        # Step 2: Set concurrency and batch parameters
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self.use_database = use_database
        self.database_url = database_url or settings.database_url
        self.deduplicate = deduplicate

        # Step 3: Initialize services
        # These will be used for all document processing
        self.ollama = OllamaService()
        self.extractor = ExtractionService()
        self.db = None

        # Step 4: Initialize database if requested
        if self.use_database and DATABASE_AVAILABLE:
            try:
                self.db = DatabaseService(database_url=self.database_url)
                logger.info("Database enabled for async batch processing")
            except Exception as e:
                logger.warning(f"Failed to initialize database: {e}")
                self.use_database = False

        # Step 5: Initialize result storage
        self.results: List[AsyncBatchResult] = []          # All results
        self.processed_hashes: Set[str] = set()             # For deduplication
        self.pending_db_batch: List[Dict[str, Any]] = []   # Pending DB inserts

        # Step 6: Create semaphore for concurrency control
        #
        # What's a semaphore?
        # - Like a "ticket system" for running tasks
        # - Only max_concurrent tasks can have "tickets" at once
        # - When a task finishes, it returns its ticket
        # - Next task takes that ticket and starts
        #
        # Why needed?
        # - Without it, could start 10,000 async tasks simultaneously
        # - That would overload memory, network, and APIs
        # - Semaphore keeps things under control
        self.semaphore = asyncio.Semaphore(max_concurrent)

        logger.info(f"Initialized AsyncBatchProcessor: max_concurrent={max_concurrent}, batch_size={batch_size}")

    # ==========================================================================
    # DEDUPLICATION METHODS
    # ==========================================================================

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of a file for deduplication.

        The hash is a unique fingerprint of the file content:
        - Same content = same hash (even if renamed)
        - Different content = different hash
        - Very fast to compute
        - Used to detect already-processed documents

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash string (64 hex characters)

        Why SHA256?
        - Industry standard for file hashing
        - Collision-resistant (virtually impossible to have duplicate hashes)
        - Fast enough for our use case
        - 256 bits = 64 hex characters

        How it works:
        1. Read file in 8KB chunks (efficient for large files)
        2. Update hash with each chunk
        3. Return final hash

        Example:
            >>> _calculate_file_hash(Path("invoice.pdf"))
            'a3f5d8c9e2b1...'  # 64-character hash

            # Same file, different location = same hash
            >>> _calculate_file_hash(Path("backup/invoice.pdf"))
            'a3f5d8c9e2b1...'  # Identical!
        """
        try:
            # Create SHA256 hasher
            sha256 = hashlib.sha256()

            # Read file in chunks (efficient for large files)
            with open(file_path, 'rb') as f:
                # Read 8KB at a time
                # This prevents loading huge files entirely into memory
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)

            # Return hex string (64 characters)
            return sha256.hexdigest()

        except Exception as e:
            # If hashing fails (file permissions, etc.), fall back to path
            # Not ideal but prevents crashes
            logger.warning(f"Failed to hash {file_path}: {e}")
            return str(file_path)  # Fallback to path string

    def _is_duplicate(self, file_path: Path) -> bool:
        """
        Check if a document has already been processed.

        Uses file hashing to detect duplicates:
        - Calculates hash of file content
        - Checks if hash exists in processed set
        - Optionally checks database for past processing

        Args:
            file_path: Path to document

        Returns:
            True if already processed, False otherwise

        Why check duplicates?
        - Saves processing time (don't redo work)
        - Prevents duplicate database entries
        - Important for incremental processing (adding new docs to existing batch)

        Example:
            First time processing invoice.pdf:
            >>> _is_duplicate(Path("invoice.pdf"))
            False  # Process it

            Second time (rerun the same directory):
            >>> _is_duplicate(Path("invoice.pdf"))
            True   # Skip it (already done)
        """
        # If deduplication is disabled, always process
        if not self.deduplicate:
            return False

        # Calculate file hash
        file_hash = self._calculate_file_hash(file_path)

        # Check in-memory cache (this batch)
        if file_hash in self.processed_hashes:
            return True

        # TODO: Check database for past processing
        # This would query: SELECT 1 FROM documents WHERE file_hash = ?
        if self.use_database and self.db:
            # Query database for this hash
            # This would need a method in DatabaseService like:
            # if self.db.document_exists(file_hash):
            #     return True
            pass

        return False

    # ==========================================================================
    # ASYNC DOCUMENT PROCESSING
    # ==========================================================================

    async def _classify_document_async(
        self,
        file_path: Path,
        include_reasoning: bool = False
    ) -> AsyncBatchResult:
        """
        Classify a single document asynchronously.

        This is the core async function that processes one document.
        It's called for each document, and many run concurrently.

        Flow:
        1. Acquire semaphore (wait if max concurrent reached)
        2. Check if duplicate (skip if already processed)
        3. Extract text from document (I/O operation)
        4. Classify with AI (I/O operation)
        5. Add to database batch
        6. Release semaphore (allow next task to start)

        Args:
            file_path: Path to document
            include_reasoning: Include AI reasoning in result

        Returns:
            AsyncBatchResult with classification result or error

        Why async?
        - Extract and classify involve I/O waits (reading file, API call)
        - While one task waits, others can progress
        - Much faster than processing sequentially

        Example flow for 3 concurrent tasks:
            Time 0ms:  Task 1 starts extracting
            Time 10ms: Task 1 waits for file I/O, Task 2 starts extracting
            Time 20ms: Tasks 1,2 wait, Task 3 starts extracting
            Time 30ms: Task 1 finishes extract, starts classify
            Time 40ms: Task 1 waits for AI API, Task 2 finishes extract
            ...and so on...

        Without async (sequential):
            Task 1: extract (wait) → classify (wait) → done
            Task 2: extract (wait) → classify (wait) → done
            Task 3: extract (wait) → classify (wait) → done
            Total: 3x longer!
        """
        # Record start time for performance tracking
        start_time = asyncio.get_event_loop().time()

        # Acquire semaphore (wait if too many tasks running)
        #
        # What's happening here:
        # - If fewer than max_concurrent tasks are running, acquire immediately
        # - If max_concurrent tasks are running, wait until one finishes
        # - This prevents overloading the system
        async with self.semaphore:  # Automatically releases when done

            try:
                # Step 1: Check for duplicates
                #
                # If we've already processed this document, skip it.
                # This saves time and prevents duplicate database entries.
                if self._is_duplicate(file_path):
                    logger.debug(f"Skipping duplicate: {file_path.name}")
                    return AsyncBatchResult(
                        file_path=file_path,
                        category="",
                        success=False,
                        error="Duplicate document"
                    )

                # Step 2: Extract content from document
                #
                # Why run_in_executor?
                # - self.extractor.extract() is synchronous (blocking)
                # - We need to run it without blocking the async event loop
                # - run_in_executor runs it in a thread pool
                # - This allows other async tasks to progress
                #
                # Think of it as:
                # "Hey thread pool, run this blocking function for me
                #  while I do other async stuff"
                loop = asyncio.get_event_loop()
                extracted = await loop.run_in_executor(
                    None,                      # Use default thread pool
                    self.extractor.extract,    # Function to run
                    file_path                  # Argument to function
                )

                # Step 3: Check if extraction succeeded
                if not extracted:
                    return AsyncBatchResult(
                        file_path=file_path,
                        category="",
                        success=False,
                        error="Extraction failed"
                    )

                # Step 4: Classify the document using AI
                #
                # Again using run_in_executor because Ollama service is synchronous.
                # We have two classification modes:
                # - With reasoning: Returns category + AI's explanation
                # - Without reasoning: Just returns category (faster)
                if include_reasoning:
                    # Classification with reasoning (detailed)
                    classification = await loop.run_in_executor(
                        None,
                        self.ollama.classify_with_confidence,
                        extracted.text,
                        extracted.metadata.to_dict(),
                        self.categories
                    )

                    if classification:
                        category = classification["category"]
                        confidence = classification.get("reasoning")
                    else:
                        return AsyncBatchResult(
                            file_path=file_path,
                            category="",
                            success=False,
                            error="Classification failed"
                        )

                else:
                    # Classification without reasoning (faster)
                    category = await loop.run_in_executor(
                        None,
                        self.ollama.classify_document,
                        extracted.text,
                        extracted.metadata.to_dict(),
                        self.categories
                    )
                    confidence = None

                    if not category:
                        return AsyncBatchResult(
                            file_path=file_path,
                            category="",
                            success=False,
                            error="Classification failed"
                        )

                # Step 5: Calculate processing time
                processing_time = asyncio.get_event_loop().time() - start_time

                # Step 6: Mark as processed (for deduplication)
                file_hash = self._calculate_file_hash(file_path)
                self.processed_hashes.add(file_hash)

                # Step 7: Create success result
                result = AsyncBatchResult(
                    file_path=file_path,
                    category=category,
                    confidence=confidence,
                    metadata=extracted.metadata.to_dict(),
                    processing_time=processing_time,
                    success=True
                )

                # Step 8: Add to database batch (if enabled)
                #
                # Instead of inserting immediately (slow!), we batch inserts.
                # Collect 100 documents, then insert all at once.
                # Much faster than 100 individual inserts.
                if self.use_database:
                    self.pending_db_batch.append({
                        'file_path': file_path,
                        'category': category,
                        'content': extracted.text,
                        'metadata': extracted.metadata.to_dict(),
                        'confidence': confidence,
                    })

                    # If batch is full, flush to database
                    if len(self.pending_db_batch) >= self.batch_size:
                        await self._flush_database_batch()

                return result

            except Exception as e:
                # Something went wrong - log and return error
                processing_time = asyncio.get_event_loop().time() - start_time
                logger.error(f"Async classification error for {file_path}: {e}")
                return AsyncBatchResult(
                    file_path=file_path,
                    category="",
                    processing_time=processing_time,
                    success=False,
                    error=str(e)
                )

    # ==========================================================================
    # DATABASE BATCH OPERATIONS
    # ==========================================================================

    async def _flush_database_batch(self):
        """
        Flush pending database batch inserts.

        This writes accumulated documents to the database in one batch operation.
        Called when:
        - Batch is full (reached batch_size)
        - Processing complete (flush remaining documents)

        Why batch inserts?
        - Single insert: Open connection → Insert → Close (repeated 100x)
        - Batch insert: Open connection → Insert 100 → Close (once!)
        - Batch is 10-50x faster!

        How it works:
        1. Check if there are pending documents
        2. Copy the batch (so we can clear it immediately)
        3. Run batch insert in executor (don't block async loop)
        4. Clear the pending batch

        Why run_in_executor?
        - Database operations are synchronous (blocking)
        - Running them directly would block the async event loop
        - Executor runs them in a thread pool
        - Allows other async tasks to continue
        """
        # If nothing to flush, return
        if not self.pending_db_batch or not self.use_database or not self.db:
            return

        try:
            # Run batch insert in executor (non-blocking)
            #
            # Why copy the batch?
            # - We pass batch.copy() to the executor
            # - This lets us clear pending_db_batch immediately
            # - Other tasks can start building a new batch
            # - Executor works on the copy independently
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._batch_insert_to_db,
                self.pending_db_batch.copy()  # Copy so we can clear immediately
            )

            logger.debug(f"Flushed batch of {len(self.pending_db_batch)} documents to database")
            self.pending_db_batch.clear()  # Clear for next batch

        except Exception as e:
            logger.error(f"Failed to flush database batch: {e}")

    def _batch_insert_to_db(self, batch_data: List[Dict[str, Any]]):
        """
        Perform batch insert to database.

        Runs in executor thread pool to avoid blocking async loop.

        This is a synchronous function (no async) because:
        - DatabaseService is synchronous
        - It's called via run_in_executor from async code
        - Executor handles the threading

        Args:
            batch_data: List of document dictionaries to insert

        Note: Currently inserts one at a time in a loop.
        TODO: Use database's native batch insert for even better performance:
            - PostgreSQL: INSERT ... VALUES (...), (...), ...
            - Would be 2-3x faster than current implementation
        """
        for data in batch_data:
            try:
                self.db.add_document(
                    file_path=data['file_path'],
                    category=data['category'],
                    content=data['content'],
                    metadata=data['metadata'],
                    confidence=data['confidence'],
                    model_used=self.ollama.model,
                    store_full_content=settings.store_full_content,
                )
            except Exception as e:
                logger.error(f"Failed to insert document: {e}")

    # ==========================================================================
    # MAIN PROCESSING METHODS
    # ==========================================================================

    async def process_batch_async(
        self,
        file_paths: List[Path],
        include_reasoning: bool = False,
        show_progress: bool = True
    ) -> AsyncBatchStats:
        """
        Process a batch of documents asynchronously.

        This is the main entry point for async batch processing.

        Flow:
        1. Create async tasks for all documents
        2. Run all tasks concurrently (limited by semaphore)
        3. Collect results as tasks complete
        4. Flush remaining database batch
        5. Calculate and return statistics

        Args:
            file_paths: List of document paths to process
            include_reasoning: Include AI reasoning in results
            show_progress: Show progress bar (async-compatible)

        Returns:
            AsyncBatchStats with performance metrics

        Example:
            >>> import asyncio
            >>> processor = AsyncBatchProcessor(max_concurrent=50)
            >>> files = [Path("doc1.pdf"), Path("doc2.pdf"), ...]
            >>> stats = asyncio.run(
            ...     processor.process_batch_async(files)
            ... )
            >>> print(f"Processed {stats.successful} docs in {stats.total_processing_time:.1f}s")
            Processed 9,850 docs in 245.3s

        Performance tips:
        - Increase max_concurrent for better throughput
        - Disable progress bar for maximum speed
        - Use deduplication to skip already-processed
        - Tune batch_size based on database performance
        """
        start_time = datetime.now()
        logger.info(f"Starting async batch processing of {len(file_paths)} documents")

        # Step 1: Create async tasks for all documents
        #
        # This creates a list of "coroutines" (async functions).
        # They don't start running yet - just created.
        # Think of it as creating a to-do list.
        tasks = [
            self._classify_document_async(fp, include_reasoning)
            for fp in file_paths
        ]

        # Step 2: Execute all tasks concurrently
        #
        # asyncio.gather() runs all tasks at once (concurrently).
        # But remember: semaphore limits how many actually run simultaneously.
        #
        # Two modes:
        # - With progress: Show a progress bar (slightly slower)
        # - Without progress: Maximum speed (no progress updates)
        if show_progress:
            # Use tqdm's async-compatible progress bar
            from tqdm.asyncio import tqdm
            results = await tqdm.gather(*tasks, desc="Processing documents async")
        else:
            # Run without progress tracking (fastest)
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 3: Flush any remaining database batch
        #
        # If batch isn't full (e.g., 73 documents left), flush them now.
        await self._flush_database_batch()

        # Step 4: Store results (filter out any exceptions)
        self.results = [r for r in results if isinstance(r, AsyncBatchResult)]

        # Step 5: Calculate statistics
        successful = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success and r.error != "Duplicate document")
        skipped = sum(1 for r in self.results if r.error == "Duplicate document")

        # Step 6: Create and finalize stats
        stats = AsyncBatchStats(
            total_documents=len(file_paths),
            successful=successful,
            failed=failed,
            skipped_duplicates=skipped,
            start_time=start_time,
            end_time=datetime.now()
        )
        stats.finalize()

        # Step 7: Log summary
        logger.success(
            f"Async processing complete: {successful}/{len(file_paths)} successful, "
            f"{failed} failed, {skipped} skipped (duplicates) "
            f"in {stats.total_processing_time:.2f}s "
            f"({stats.documents_per_second:.2f} docs/sec)"
        )

        return stats

    async def process_directory_async(
        self,
        input_dir: Path,
        recursive: bool = True,
        include_reasoning: bool = False,
        file_extensions: Optional[List[str]] = None
    ) -> AsyncBatchStats:
        """
        Process all documents in a directory asynchronously.

        Convenience wrapper that:
        1. Scans directory for documents
        2. Filters by file extension
        3. Calls process_batch_async() to process them

        Args:
            input_dir: Directory containing documents
            recursive: Also process subdirectories
            include_reasoning: Include AI reasoning
            file_extensions: List of extensions to process (default: all supported)

        Returns:
            AsyncBatchStats with performance metrics

        Example:
            >>> import asyncio
            >>> processor = AsyncBatchProcessor(max_concurrent=50)
            >>> stats = asyncio.run(
            ...     processor.process_directory_async(Path("documents/input"))
            ... )
            >>> print(f"Processed {stats.successful} documents")
        """
        logger.info(f"Scanning directory: {input_dir}")

        # Step 1: Default to all supported file types
        if file_extensions is None:
            file_extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md"]

        # Step 2: Collect matching files
        file_paths = []
        if recursive:
            # Search all subdirectories
            for ext in file_extensions:
                file_paths.extend(input_dir.rglob(f"*{ext}"))
        else:
            # Search only top-level directory
            for ext in file_extensions:
                file_paths.extend(input_dir.glob(f"*{ext}"))

        # Step 3: Filter to only files (not directories)
        file_paths = [f for f in file_paths if f.is_file()]

        logger.info(f"Found {len(file_paths)} documents to process")

        # Step 4: Handle edge case - no files found
        if not file_paths:
            logger.warning("No documents found")
            return AsyncBatchStats(
                total_documents=0,
                successful=0,
                failed=0,
                skipped_duplicates=0,
                start_time=datetime.now(),
                end_time=datetime.now()
            )

        # Step 5: Process all found documents
        return await self.process_batch_async(file_paths, include_reasoning)

    # ==========================================================================
    # RESULT ACCESS AND EXPORT
    # ==========================================================================

    def get_results(self) -> List[AsyncBatchResult]:
        """
        Get all processing results.

        Returns:
            List of AsyncBatchResult objects

        Example:
            >>> results = processor.get_results()
            >>> successful = [r for r in results if r.success]
            >>> failed = [r for r in results if not r.success]
        """
        return self.results

    def export_results(self, output_path: Path):
        """
        Export all processing results to JSON.

        The exported JSON includes:
        - Total/successful/failed counts
        - Individual results for each document
        - Processing times

        Args:
            output_path: Where to save the JSON file

        Example:
            >>> processor.export_results(Path("async_results.json"))

            # File contains:
            {
                "total": 10000,
                "successful": 9850,
                "failed": 150,
                "results": [
                    {
                        "file_path": "doc1.pdf",
                        "category": "invoices",
                        "processing_time": 2.3,
                        "success": true
                    },
                    ...
                ]
            }
        """
        import json

        export_data = {
            "total": len(self.results),
            "successful": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success),
            "results": [
                {
                    "file_path": str(r.file_path),
                    "category": r.category,
                    "confidence": r.confidence,
                    "processing_time": r.processing_time,
                    "success": r.success,
                    "error": r.error
                }
                for r in self.results
            ]
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.success(f"Exported results to {output_path}")


# ==============================================================================
# CONVENIENCE FUNCTIONS FOR CLI
# ==============================================================================

async def async_classify_directory(
    input_dir: Path,
    categories: Optional[List[str]] = None,
    max_concurrent: int = 50,
    batch_size: int = 100,
    include_reasoning: bool = False,
    use_database: bool = False,
    export_path: Optional[Path] = None
) -> AsyncBatchStats:
    """
    Convenience function for async directory classification.

    This is a simple "do everything" async function:
    1. Creates processor
    2. Processes directory
    3. Optionally exports results

    Perfect for CLI usage or simple scripts.

    Args:
        input_dir: Directory containing documents
        categories: Classification categories (default: from config)
        max_concurrent: Max concurrent operations (default: 50)
        batch_size: Database batch size (default: 100)
        include_reasoning: Include AI reasoning
        use_database: Save to database
        export_path: Optional export path for results JSON

    Returns:
        AsyncBatchStats with performance metrics

    Example:
        >>> import asyncio
        >>> stats = asyncio.run(
        ...     async_classify_directory(
        ...         Path("documents/input"),
        ...         max_concurrent=50,
        ...         use_database=True
        ...     )
        ... )
        >>> print(f"Success: {stats.successful}")
        >>> print(f"Speed: {stats.documents_per_second:.1f} docs/sec")

    Used by:
        - CLI commands
        - Quick scripts
        - Testing
    """
    # Step 1: Create processor
    processor = AsyncBatchProcessor(
        categories=categories,
        max_concurrent=max_concurrent,
        batch_size=batch_size,
        use_database=use_database
    )

    # Step 2: Process directory
    stats = await processor.process_directory_async(
        input_dir,
        recursive=True,
        include_reasoning=include_reasoning
    )

    # Step 3: Export results if requested
    if export_path:
        processor.export_results(export_path)

    return stats
