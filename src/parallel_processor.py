"""
==============================================================================
PARALLEL DOCUMENT PROCESSOR - High-Throughput Classification
==============================================================================

PURPOSE:
    Process thousands/millions of documents efficiently using multiple CPU cores.
    This is the solution for scaling from 300 docs/hour to 3000+ docs/hour.

WHAT IS MULTIPROCESSING?
    - Python's way of using multiple CPU cores simultaneously
    - Each "worker" is a separate process (like running multiple programs)
    - Workers process documents in parallel (at the same time)
    - Much faster than processing one document at a time

WHEN TO USE THIS:
    ✓ Processing 1,000+ documents
    ✓ Need to process 500K documents in a week
    ✓ Single-threaded processing is too slow
    ✓ Have a multi-core CPU (most modern computers do)

HOW FAST IS IT?
    - Single-threaded: ~300 documents/hour
    - Parallel (8 cores): ~2,400 documents/hour (8x faster!)
    - For 500K documents: ~9 days → ~1 day

ARCHITECTURE:
    ┌────────────────────────────────────────────────────────────────┐
    │                     Main Process (Coordinator)                  │
    │  - Collects files                                              │
    │  - Divides work into chunks                                    │
    │  - Distributes to workers                                      │
    │  - Aggregates results                                          │
    └─────┬──────────────────────────────────────────────────────────┘
          │
          ├─────> Worker 1 ──> [Doc 1, Doc 2, Doc 3...]
          ├─────> Worker 2 ──> [Doc 4, Doc 5, Doc 6...]
          ├─────> Worker 3 ──> [Doc 7, Doc 8, Doc 9...]
          └─────> Worker N ──> [Doc N, Doc N+1, Doc N+2...]
                    ↓
              Each worker:
              1. Extracts text from document
              2. Classifies with AI
              3. Saves to database (optional)
              4. Returns result

KEY CONCEPTS:
    1. **Worker Pool**: A group of processes that wait for work
    2. **Chunk Size**: How many documents each worker gets at once
    3. **Pickling**: Python's way of sending data between processes
    4. **Process Isolation**: Each worker has its own memory (can't share objects)

USAGE EXAMPLE:
    ```python
    from pathlib import Path
    from src.parallel_processor import ParallelDocumentProcessor

    # Create processor with 8 workers
    processor = ParallelDocumentProcessor(num_workers=8)

    # Process all documents in a directory
    stats = processor.process_directory(Path("documents/input"))

    # Print results
    processor.print_summary()
    # Output: Processed 10,000 documents in 250s (40 docs/sec)
    ```

RELATED FILES:
    - src/classifier.py - Single document classification
    - src/async_batch_processor.py - For I/O-heavy workloads
    - src/celery_tasks.py - For distributed processing across machines

AUTHOR: AI Document Pipeline Team
LAST UPDATED: October 2025
"""

import multiprocessing as mp
from multiprocessing import Pool, Queue, Manager
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import time
import os
import signal
from loguru import logger
from tqdm import tqdm

from src.classifier import DocumentClassifier, ClassificationResult
from src.ollama_service import OllamaService
from src.extractors import ExtractionService


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class ProcessingStats:
    """
    Performance statistics for a parallel processing run.

    This tracks:
    - How many documents we processed
    - How many succeeded vs failed
    - How long it took
    - How fast we processed (documents per second)

    Why track stats?
    - Monitor performance and identify bottlenecks
    - Calculate if we can meet deadlines (500K in 1 week)
    - Compare different processing strategies
    - Report progress to users

    Example:
        >>> stats = ProcessingStats(
        ...     total_documents=10000,
        ...     successful=9850,
        ...     failed=150,
        ...     start_time=datetime.now(),
        ...     worker_count=8
        ... )
        >>> stats.end_time = datetime.now()
        >>> stats.update_final()
        >>> print(f"Processed {stats.documents_per_second:.1f} docs/sec")
        Processed 42.5 docs/sec
    """
    # Input metrics
    total_documents: int              # Total number of documents to process
    successful: int                    # Successfully processed documents
    failed: int                        # Failed documents
    start_time: datetime              # When processing started

    # Calculated metrics (filled in after processing)
    end_time: Optional[datetime] = None              # When processing finished
    processing_time_seconds: float = 0.0            # Total time taken
    documents_per_second: float = 0.0               # Throughput (speed)
    worker_count: int = 0                           # Number of parallel workers

    def update_final(self):
        """
        Calculate final statistics after processing completes.

        This computes:
        - Total processing time (end_time - start_time)
        - Documents per second (throughput)

        Call this AFTER setting end_time.

        Why separate this from __init__?
        - We create the stats object before processing starts
        - We update it incrementally as documents finish
        - We calculate final stats only at the end
        """
        if self.end_time:
            # Calculate total time in seconds
            self.processing_time_seconds = (self.end_time - self.start_time).total_seconds()

            # Calculate throughput (avoid division by zero)
            if self.processing_time_seconds > 0:
                self.documents_per_second = self.successful / self.processing_time_seconds

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert statistics to a dictionary for JSON export.

        Returns:
            Dictionary with all statistics

        Why?
        - JSON export for reporting
        - Easy to save to file or database
        - Can be loaded and analyzed later
        """
        return {
            "total_documents": self.total_documents,
            "successful": self.successful,
            "failed": self.failed,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "processing_time_seconds": self.processing_time_seconds,
            "documents_per_second": self.documents_per_second,
            "worker_count": self.worker_count,
        }


# ==============================================================================
# WORKER FUNCTIONS
# ==============================================================================

def _worker_process_document(args):
    """
    Worker function that processes a single document in a separate process.

    This is the function that runs in each worker process. Each worker:
    1. Creates its own classifier instance (can't share between processes)
    2. Extracts text from the document
    3. Classifies it with AI
    4. Optionally saves to database
    5. Returns the result

    IMPORTANT - Why this is a module-level function:
    Python's multiprocessing can only send simple data between processes
    (strings, numbers, lists, dicts). It does this using "pickling".

    Functions defined at the module level CAN be pickled.
    Functions defined inside classes CANNOT be pickled.

    That's why this worker function is outside the class!

    Args:
        args: Tuple containing:
            - file_path: Path to document file
            - categories: List of classification categories
            - include_reasoning: Whether to include AI reasoning in result
            - use_database: Whether to save results to database
            - database_url: Database connection string (if using database)

    Returns:
        Tuple of (file_path_string, result_dictionary) where result contains:
            If successful:
                - success: True
                - category: Classified category
                - confidence: Confidence score (0-100)
                - metadata: Document metadata
                - timestamp: When classified
                - db_id: Database ID (if saved to DB)

            If failed:
                - success: False
                - error: Error message

    Why return tuple instead of object?
    - Tuples and dicts can be pickled easily
    - Complex objects (like ClassificationResult) are harder to send between processes
    - Simple data structures = reliable multiprocessing

    Example flow:
        Worker 3 receives: ("documents/invoice.pdf", ["invoices", "receipts"], False, True, "postgresql://...")
        Worker 3 processes invoice.pdf
        Worker 3 returns: ("documents/invoice.pdf", {"success": True, "category": "invoices", ...})
    """
    # Unpack arguments
    # (Each worker gets a tuple with all the info it needs)
    file_path, categories, include_reasoning, use_database, database_url = args

    try:
        # Step 1: Create service instances for THIS worker
        #
        # Why create new instances instead of reusing?
        # Each worker is a SEPARATE PROCESS with its own memory.
        # We can't share objects between processes.
        # Each worker needs its own copy of the services.
        ollama = OllamaService()
        extractor = ExtractionService()
        classifier = DocumentClassifier(
            ollama_service=ollama,
            extraction_service=extractor,
            use_database=use_database
        )

        # Step 2: Configure database connection if needed
        #
        # If database is enabled, give this worker its own database connection.
        # Each worker needs its own connection (can't share connections between processes).
        if use_database and classifier.db:
            from src.database import DatabaseService
            classifier.db = DatabaseService(database_url=database_url)

        # Step 3: Classify the document
        #
        # This is where the actual work happens:
        # - Extract text from document
        # - Send to AI for classification
        # - Save to database (if enabled)
        result = classifier.classify_document(file_path, include_reasoning)

        # Step 4: Convert result to dictionary for return
        #
        # Why convert to dict?
        # Dicts can be easily pickled and sent back to the main process.
        # ClassificationResult objects are more complex to pickle.
        if result:
            return (str(file_path), {
                "success": True,
                "category": result.category,
                "confidence": result.confidence,
                "metadata": result.metadata,
                "timestamp": result.timestamp.isoformat(),
                "db_id": result.db_id
            })
        else:
            # Classification returned None (shouldn't happen, but handle it)
            return (str(file_path), {
                "success": False,
                "error": "Classification failed - returned None"
            })

    except Exception as e:
        # Something went wrong (file not found, OCR failed, AI error, etc.)
        # Log it and return error result
        logger.error(f"Worker error processing {file_path}: {e}")
        return (str(file_path), {
            "success": False,
            "error": str(e)
        })


# ==============================================================================
# PARALLEL PROCESSOR CLASS
# ==============================================================================

class ParallelDocumentProcessor:
    """
    High-throughput parallel document processor using multiprocessing.

    WHAT IT DOES:
        Takes a large batch of documents and processes them across multiple
        CPU cores simultaneously for maximum speed.

    HOW IT WORKS:
        1. Main process: Collects all document files
        2. Main process: Creates a pool of worker processes
        3. Main process: Divides documents into chunks
        4. Workers: Each processes its chunk of documents
        5. Main process: Collects all results from workers
        6. Main process: Aggregates statistics

    PERFORMANCE:
        Single-threaded: ~300 documents/hour
        Parallel (8 cores): ~2,400 documents/hour (8x faster!)

        For 500K documents:
        - Single-threaded: ~69 days
        - Parallel (8 cores): ~8.7 days
        - Parallel (16 cores): ~4.3 days

    KEY PARAMETERS:
        - num_workers: Number of parallel processes (default: CPU count)
        - chunk_size: Documents per worker chunk (default: 10)
        - use_database: Save results to database (default: False)

    TUNING GUIDE:
        num_workers:
            - Default (CPU count) is usually optimal
            - More workers = faster processing (up to CPU core limit)
            - Too many workers = overhead from process management
            - Rule of thumb: workers = CPU cores or CPU cores - 1

        chunk_size:
            - Small chunks (1-5): Better load balancing, more overhead
            - Large chunks (50-100): Less overhead, worse load balancing
            - Default (10): Good balance for most workloads
            - Adjust based on document processing time variance

    EXAMPLE USAGE:
        ```python
        # Process a directory with 8 workers
        processor = ParallelDocumentProcessor(num_workers=8)
        stats = processor.process_directory(Path("documents/input"))
        processor.print_summary()

        # Process specific files with database storage
        processor = ParallelDocumentProcessor(
            num_workers=16,
            use_database=True
        )
        files = [Path("doc1.pdf"), Path("doc2.pdf")]
        stats = processor.process_batch(files)

        # Export results to JSON
        processor.export_results(Path("results.json"))
        ```

    COMPARISON WITH OTHER PROCESSORS:
        - parallel_processor.py (this file): Best for CPU-heavy work
        - async_batch_processor.py: Best for I/O-heavy work
        - celery_tasks.py: Best for distributed across machines

        Use parallel processing when:
        ✓ Processing locally on one machine
        ✓ Extraction/OCR is the bottleneck
        ✓ Want simplicity (no external dependencies)
    """

    def __init__(
        self,
        categories: Optional[List[str]] = None,
        num_workers: Optional[int] = None,
        use_database: bool = False,
        database_url: Optional[str] = None,
        chunk_size: int = 10,
    ):
        """
        Initialize the parallel document processor.

        Args:
            categories: List of classification categories (default: from config)
            num_workers: Number of worker processes (default: CPU count)
            use_database: Enable database storage for results
            database_url: Database connection URL (default: from config)
            chunk_size: Number of documents per worker chunk

        What happens during initialization:
        1. Load configuration settings
        2. Set number of workers (default to CPU count)
        3. Configure database connection if needed
        4. Initialize result storage

        Why default to CPU count for workers?
        - Most computers have 4-16 cores
        - Each core can run one worker efficiently
        - More workers than cores = diminishing returns
        - Python multiprocessing automatically detects CPU count

        Common configurations:
        - Laptop (4 cores): num_workers=4
        - Desktop (8 cores): num_workers=8
        - Server (32 cores): num_workers=32
        """
        from config import settings

        # Step 1: Set classification categories
        # Use provided categories, or fall back to config
        self.categories = categories or settings.category_list

        # Step 2: Set number of worker processes
        # Default to CPU count (optimal for most systems)
        self.num_workers = num_workers or mp.cpu_count()

        # Step 3: Configure database storage
        self.use_database = use_database
        self.database_url = database_url or settings.database_url

        # Step 4: Set chunk size (how many docs each worker gets at once)
        # Smaller = better load balancing, more overhead
        # Larger = less overhead, worse load balancing
        self.chunk_size = chunk_size

        # Step 5: Initialize storage for results
        # These will be populated as documents are processed
        self.results: Dict[str, Dict] = {}          # All results (file_path -> result)
        self.stats: Optional[ProcessingStats] = None  # Performance statistics

        logger.info(f"Initialized ParallelDocumentProcessor with {self.num_workers} workers")

    def process_batch(
        self,
        file_paths: List[Path],
        include_reasoning: bool = False,
        show_progress: bool = True,
    ) -> ProcessingStats:
        """
        Process a batch of documents in parallel across multiple CPU cores.

        This is the main processing function. It:
        1. Creates a pool of worker processes
        2. Divides documents among workers
        3. Processes all documents in parallel
        4. Collects and aggregates results
        5. Returns performance statistics

        Args:
            file_paths: List of document paths to process
            include_reasoning: Include AI reasoning in classification results
            show_progress: Display a progress bar during processing

        Returns:
            ProcessingStats object with:
                - total_documents: How many we tried to process
                - successful: How many succeeded
                - failed: How many failed
                - processing_time_seconds: How long it took
                - documents_per_second: Throughput (speed)

        Flow:
            1. Initialize statistics tracker
            2. Prepare arguments for workers
            3. Create worker pool
            4. Distribute work to workers
            5. Collect results as workers finish
            6. Calculate final statistics
            7. Return stats

        Example:
            >>> processor = ParallelDocumentProcessor(num_workers=8)
            >>> files = [Path("doc1.pdf"), Path("doc2.pdf"), ...]
            >>> stats = processor.process_batch(files)
            >>> print(f"Processed {stats.successful} documents in {stats.processing_time_seconds:.1f}s")
            Processed 9,850 documents in 245.3s

        Performance tips:
        - More workers = faster (up to CPU core count)
        - Disable progress bar for maximum speed (show_progress=False)
        - Process in larger batches (less startup overhead)
        - Use SSD for better file I/O performance
        """
        start_time = datetime.now()

        # Step 1: Initialize performance statistics
        #
        # We create the stats object now with what we know:
        # - How many documents we're processing
        # - When we started
        # - How many workers we're using
        #
        # We'll update it as processing progresses.
        self.stats = ProcessingStats(
            total_documents=len(file_paths),
            successful=0,      # Will increment as documents succeed
            failed=0,          # Will increment as documents fail
            start_time=start_time,
            worker_count=self.num_workers
        )

        logger.info(f"Starting parallel processing of {len(file_paths)} documents")
        logger.info(f"Workers: {self.num_workers}, Chunk size: {self.chunk_size}")

        # Step 2: Prepare arguments for workers
        #
        # Each worker needs:
        # - The file path to process
        # - Configuration (categories, reasoning, database settings)
        #
        # We create a list of tuples, one for each document.
        # The worker function will unpack these tuples.
        worker_args = [
            (fp, self.categories, include_reasoning, self.use_database, self.database_url)
            for fp in file_paths
        ]

        # Step 3: Process documents using multiprocessing pool
        #
        # The Pool class manages worker processes:
        # - Creates num_workers processes
        # - Distributes work among them
        # - Collects results as they finish
        # - Cleans up when done
        #
        # The "with" statement ensures workers are cleaned up properly.
        try:
            with Pool(processes=self.num_workers) as pool:
                if show_progress:
                    # Option A: Show progress bar (slower but user-friendly)
                    #
                    # imap_unordered returns results as they finish (not in order).
                    # This is faster than waiting for all workers to finish.
                    #
                    # chunksize=self.chunk_size means each worker gets
                    # chunk_size documents at a time.
                    results_iter = pool.imap_unordered(
                        _worker_process_document,  # Function to run in each worker
                        worker_args,                # List of arguments (one per document)
                        chunksize=self.chunk_size  # Documents per worker chunk
                    )

                    # Show progress bar using tqdm
                    # Updates in real-time as workers finish documents
                    for file_path, result in tqdm(
                        results_iter,
                        total=len(file_paths),
                        desc="Processing documents",
                        unit="doc"
                    ):
                        self._process_result(file_path, result)

                else:
                    # Option B: No progress bar (fastest)
                    #
                    # pool.map waits for all workers to finish,
                    # then returns all results at once.
                    #
                    # Slightly faster than imap_unordered because
                    # no progress updates.
                    results = pool.map(
                        _worker_process_document,
                        worker_args,
                        chunksize=self.chunk_size
                    )

                    # Process all results after completion
                    for file_path, result in results:
                        self._process_result(file_path, result)

        except KeyboardInterrupt:
            # User pressed Ctrl+C - stop gracefully
            logger.warning("Processing interrupted by user")
            pool.terminate()  # Stop all workers immediately
            pool.join()       # Wait for workers to finish cleanup

        except Exception as e:
            # Something unexpected went wrong
            logger.error(f"Parallel processing error: {e}")

        # Step 4: Calculate final statistics
        #
        # Now that processing is complete:
        # - Record end time
        # - Calculate total processing time
        # - Calculate throughput (documents per second)
        self.stats.end_time = datetime.now()
        self.stats.update_final()

        # Step 5: Log summary
        logger.success(
            f"Parallel processing complete: {self.stats.successful}/{self.stats.total_documents} "
            f"documents in {self.stats.processing_time_seconds:.2f}s "
            f"({self.stats.documents_per_second:.2f} docs/sec)"
        )

        return self.stats

    def _process_result(self, file_path: str, result: Dict):
        """
        Process a single result from a worker.

        This is called for each document as workers finish processing.
        It:
        1. Stores the result
        2. Updates success/failure counters
        3. Logs any failures

        Args:
            file_path: Path to the processed document
            result: Result dictionary from worker

        Why separate this into its own method?
        - Called from two places (with/without progress bar)
        - Keeps the main process_batch method cleaner
        - Easy to add custom result handling later
        """
        # Store the result for this document
        self.results[file_path] = result

        # Update statistics counters
        if result.get("success"):
            self.stats.successful += 1
        else:
            self.stats.failed += 1
            # Log failure details for debugging
            logger.warning(f"Failed to process {Path(file_path).name}: {result.get('error')}")

    def process_directory(
        self,
        input_dir: Path,
        recursive: bool = True,
        include_reasoning: bool = False,
        file_extensions: Optional[List[str]] = None,
    ) -> ProcessingStats:
        """
        Process all documents in a directory (convenience wrapper).

        This is a convenience method that:
        1. Scans a directory for documents
        2. Filters by file extension
        3. Calls process_batch() to process them

        It's essentially: "find all files, then process them"

        Args:
            input_dir: Directory containing documents
            recursive: Also process subdirectories (default: True)
            include_reasoning: Include AI reasoning in results
            file_extensions: List of extensions to process (default: all supported)

        Returns:
            ProcessingStats with performance metrics

        Example:
            >>> processor = ParallelDocumentProcessor(num_workers=8)
            >>> stats = processor.process_directory(
            ...     Path("documents/input"),
            ...     recursive=True  # Also process subdirectories
            ... )
            >>> print(f"Found and processed {stats.total_documents} documents")

        When to use recursive=True vs False:
        - True: Process all subdirectories (good for organized archives)
        - False: Only process top-level files (good for flat directories)
        """
        logger.info(f"Scanning directory: {input_dir}")

        # Step 1: Determine which file types to process
        #
        # Default to all supported document types.
        # User can override to process only specific types.
        if file_extensions is None:
            file_extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md"]

        # Step 2: Collect all matching files
        #
        # Two modes:
        # - Recursive (rglob): Search all subdirectories
        # - Non-recursive (glob): Only search top level
        file_paths = []
        if recursive:
            # rglob searches recursively (all subdirectories)
            for ext in file_extensions:
                file_paths.extend(input_dir.rglob(f"*{ext}"))
        else:
            # glob searches only the specified directory
            for ext in file_extensions:
                file_paths.extend(input_dir.glob(f"*{ext}"))

        # Step 3: Filter to only files (exclude directories)
        #
        # Sometimes glob returns directories that match the pattern.
        # We only want actual files.
        file_paths = [f for f in file_paths if f.is_file()]

        logger.info(f"Found {len(file_paths)} documents to process")

        # Step 4: Handle edge case - no files found
        if not file_paths:
            logger.warning("No documents found to process")
            return ProcessingStats(
                total_documents=0,
                successful=0,
                failed=0,
                start_time=datetime.now(),
                end_time=datetime.now(),
                worker_count=self.num_workers
            )

        # Step 5: Process all found documents
        return self.process_batch(file_paths, include_reasoning)

    # ==========================================================================
    # RESULT ACCESS METHODS
    # ==========================================================================

    def get_results(self) -> Dict[str, Dict]:
        """
        Get all processing results (successful and failed).

        Returns:
            Dictionary mapping file paths to result dictionaries

        Example:
            >>> processor.get_results()
            {
                "doc1.pdf": {"success": True, "category": "invoices", ...},
                "doc2.pdf": {"success": False, "error": "File not found"},
                ...
            }
        """
        return self.results

    def get_successful_results(self) -> Dict[str, Dict]:
        """
        Get only successful results (filter out failures).

        Returns:
            Dictionary of only successful classifications

        Use this when you want to:
        - Export only successful classifications
        - Count success rate
        - Ignore errors for now
        """
        return {
            path: result
            for path, result in self.results.items()
            if result.get("success")
        }

    def get_failed_results(self) -> Dict[str, Dict]:
        """
        Get only failed results (filter out successes).

        Returns:
            Dictionary of only failed documents

        Use this when you want to:
        - Investigate failures
        - Retry failed documents
        - Generate error report
        """
        return {
            path: result
            for path, result in self.results.items()
            if not result.get("success")
        }

    # ==========================================================================
    # EXPORT AND REPORTING
    # ==========================================================================

    def export_results(self, output_path: Path):
        """
        Export all processing results to a JSON file.

        The exported JSON includes:
        - Processing statistics (time, throughput, etc.)
        - All individual results (successful and failed)
        - Summary counts

        Args:
            output_path: Where to save the JSON file

        Example:
            >>> processor.export_results(Path("results.json"))

            # Results file contains:
            {
                "stats": {
                    "total_documents": 10000,
                    "successful": 9850,
                    "failed": 150,
                    "processing_time_seconds": 245.3,
                    "documents_per_second": 40.1,
                    ...
                },
                "results": {
                    "doc1.pdf": {"success": True, "category": "invoices", ...},
                    "doc2.pdf": {"success": True, "category": "reports", ...},
                    ...
                }
            }

        Why export to JSON?
        - Can be loaded and analyzed later
        - Easy to parse with other tools
        - Human-readable format
        - Can be imported into databases or spreadsheets
        """
        import json

        # Build export data structure
        export_data = {
            "stats": self.stats.to_dict() if self.stats else {},
            "results": self.results,
            "successful_count": len(self.get_successful_results()),
            "failed_count": len(self.get_failed_results()),
        }

        # Write to file with nice formatting (indent=2)
        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.success(f"Exported results to {output_path}")

    def print_summary(self):
        """
        Print a formatted summary of processing results to console.

        Displays:
        - Total documents processed
        - Success/failure counts
        - Success rate percentage
        - Number of workers used
        - Total processing time
        - Throughput (documents per second)
        - Estimated time for 500K documents

        Example output:
            ================================================================================
            PARALLEL PROCESSING SUMMARY
            ================================================================================
            Total Documents:      10,000
            Successful:           9,850
            Failed:               150
            Success Rate:         98.5%
            Worker Processes:     8
            Processing Time:      245.32s
            Throughput:           40.15 documents/second
            Estimated for 500K:   3.5 hours
            ================================================================================

        Why estimate time for 500K?
        - That's the original requirement (500K docs in 1 week)
        - Helps users understand if current speed is sufficient
        - Shows whether they need more workers or better hardware
        """
        if not self.stats:
            logger.warning("No stats available - run processing first")
            return

        print("\n" + "=" * 80)
        print("PARALLEL PROCESSING SUMMARY")
        print("=" * 80)
        print(f"Total Documents:      {self.stats.total_documents:,}")
        print(f"Successful:           {self.stats.successful:,}")
        print(f"Failed:               {self.stats.failed:,}")
        print(f"Success Rate:         {self.stats.successful/self.stats.total_documents:.1%}")
        print(f"Worker Processes:     {self.stats.worker_count}")
        print(f"Processing Time:      {self.stats.processing_time_seconds:.2f}s")
        print(f"Throughput:           {self.stats.documents_per_second:.2f} documents/second")

        # Calculate estimated time for 500K documents
        if self.stats.documents_per_second > 0:
            hours_for_500k = 500000 / self.stats.documents_per_second / 3600
            print(f"Estimated for 500K:   {hours_for_500k:.1f} hours")

        print("=" * 80)


# ==============================================================================
# CONVENIENCE FUNCTIONS FOR CLI
# ==============================================================================

def parallel_classify_directory(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    categories: Optional[List[str]] = None,
    num_workers: Optional[int] = None,
    include_reasoning: bool = False,
    use_database: bool = False,
    export_results: bool = True,
) -> ProcessingStats:
    """
    Convenience function to classify a directory with parallel processing.

    This is a simple "do everything" function that:
    1. Creates a processor
    2. Processes the directory
    3. Prints summary
    4. Exports results

    Perfect for CLI usage or simple scripts.

    Args:
        input_dir: Directory containing documents to process
        output_dir: Where to save results (optional)
        categories: Classification categories (default: from config)
        num_workers: Number of worker processes (default: CPU count)
        include_reasoning: Include AI reasoning in results
        use_database: Save results to database
        export_results: Export results to JSON file

    Returns:
        ProcessingStats with performance metrics

    Example:
        >>> from pathlib import Path
        >>> stats = parallel_classify_directory(
        ...     input_dir=Path("documents/input"),
        ...     num_workers=8,
        ...     export_results=True
        ... )
        >>> # Automatically processes all documents and shows summary

    Used by:
        - CLI command: doc-classify classify-parallel
        - Quick scripts
        - Testing
    """
    # Step 1: Create processor
    processor = ParallelDocumentProcessor(
        categories=categories,
        num_workers=num_workers,
        use_database=use_database
    )

    # Step 2: Process all documents in directory
    stats = processor.process_directory(
        input_dir,
        recursive=True,
        include_reasoning=include_reasoning
    )

    # Step 3: Print summary to console
    processor.print_summary()

    # Step 4: Export results if requested
    if export_results and output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"parallel_results_{timestamp}.json"
        processor.export_results(results_file)

    return stats
