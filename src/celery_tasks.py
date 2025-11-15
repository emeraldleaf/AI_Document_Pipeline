"""
==============================================================================
CELERY DISTRIBUTED TASKS - Horizontal Scaling Across Machines
==============================================================================

PURPOSE:
    Scale document processing across multiple machines using Celery.
    This is the solution for processing millions of documents by adding more workers.

WHAT IS CELERY?
    - Distributed task queue system
    - Like having a "job board" where workers pick up tasks
    - Workers can run on different machines (horizontal scaling)
    - Built for production workloads (retry, monitoring, reliability)

HOW CELERY WORKS:
    ┌─────────────────────────────────────────────────────────────┐
    │                    Celery Architecture                       │
    │                                                             │
    │  ┌─────────────┐                                           │
    │  │   Client    │  1. Submit tasks                          │
    │  │  (Your App) │────────────┐                              │
    │  └─────────────┘            ↓                              │
    │                    ┌──────────────┐                        │
    │                    │    Redis     │  (Message Broker)      │
    │                    │   (Queue)    │  Holds pending tasks   │
    │                    └──────────────┘                        │
    │                            │                                │
    │         ┌──────────────────┼──────────────────┐           │
    │         ↓                  ↓                  ↓            │
    │    ┌─────────┐       ┌─────────┐       ┌─────────┐       │
    │    │Worker 1 │       │Worker 2 │       │Worker N │       │
    │    │Machine A│       │Machine B│       │Machine C│       │
    │    └─────────┘       └─────────┘       └─────────┘       │
    │         │                  │                  │            │
    │         └──────────────────┼──────────────────┘           │
    │                            ↓                                │
    │                    ┌──────────────┐                        │
    │                    │   Results    │  Stored in Redis       │
    │                    │   Backend    │  Client retrieves      │
    │                    └──────────────┘                        │
    └─────────────────────────────────────────────────────────────┘

WORKFLOW:
    1. Client submits 10,000 tasks to Redis queue
    2. Workers (on different machines) pick up tasks from queue
    3. Each worker processes its task independently
    4. Workers store results in Redis
    5. Client can check progress or retrieve results

WHY USE CELERY?
    ✓ Horizontal Scaling: Add more machines = more throughput
    ✓ Reliability: Automatic retries, failure handling
    ✓ Monitoring: Flower dashboard shows real-time progress
    ✓ Production-Ready: Used by Instagram, Reddit, Mozilla
    ✓ Language Agnostic: Workers can run anywhere

WHEN TO USE CELERY:
    ✓ Processing millions of documents
    ✓ Need to scale beyond one machine
    ✓ Want fault tolerance (retries, failure recovery)
    ✓ Have multiple machines available
    ✓ Production workloads

    ✗ Small batches (<10K documents)
    ✗ Single machine is enough
    ✗ Want simplicity (use parallel_processor.py instead)

PERFORMANCE COMPARISON:
    Single-threaded:        ~300 docs/hour
    Parallel (8 cores):     ~2,400 docs/hour
    Async (50 concurrent):  ~3,000 docs/hour
    Distributed (10 workers × 8 cores): ~24,000 docs/hour (80x faster!)

    For 500K documents:
    - Single-threaded: ~69 days
    - Distributed (10 workers): ~21 hours (✓ Meets 1 week deadline!)

SETUP GUIDE:
    1. Install dependencies:
        pip install celery redis

    2. Start Redis (message broker):
        docker run -d -p 6379:6379 redis

    3. Start workers (on each machine):
        celery -A src.celery_tasks worker --loglevel=info --concurrency=8

    4. Optional: Start monitoring dashboard:
        celery -A src.celery_tasks flower
        # Opens http://localhost:5555

    5. Submit tasks from your app:
        processor = CeleryDistributedProcessor()
        batch_id = processor.submit_directory(Path("documents"))

SCALING EXAMPLE:
    1 worker (8 cores):     ~2,400 docs/hour
    5 workers (40 cores):   ~12,000 docs/hour
    10 workers (80 cores):  ~24,000 docs/hour
    20 workers (160 cores): ~48,000 docs/hour

    Just add more machines running: celery -A src.celery_tasks worker

KEY CONCEPTS:
    1. **Task**: A unit of work (classify one document)
    2. **Broker**: Redis, holds the task queue
    3. **Worker**: Process that executes tasks
    4. **Result Backend**: Redis, stores task results
    5. **Group**: Collection of tasks submitted together
    6. **Retry**: Automatic retry on failure (with backoff)
    7. **Prefetch**: How many tasks worker grabs at once

RELATED FILES:
    - src/parallel_processor.py - For single-machine parallelism
    - src/async_batch_processor.py - For async I/O optimization
    - docker-compose-workers.yml - Docker setup for workers
    - scripts/submit_distributed_batch.py - CLI for submitting batches

AUTHOR: AI Document Pipeline Team
LAST UPDATED: October 2025
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

# Try to import Celery (it's optional)
try:
    from celery import Celery, group
    from celery.result import GroupResult
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None

from loguru import logger
from config import settings


# ==============================================================================
# CELERY APP INITIALIZATION
# ==============================================================================

# Only initialize if Celery is installed
if CELERY_AVAILABLE:
    # Get Redis URL from environment or use default
    # Redis is the message broker (task queue) and result backend
    #
    # Why Redis?
    # - Fast (in-memory database)
    # - Simple setup
    # - Reliable
    # - Industry standard for Celery
    #
    # Can also use: RabbitMQ, Amazon SQS, etc.
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Create Celery app
    #
    # 'document_pipeline': App name (shown in logs, monitoring)
    # broker: Where tasks are queued (Redis)
    # backend: Where results are stored (Redis)
    app = Celery(
        'document_pipeline',
        broker=REDIS_URL,
        backend=REDIS_URL
    )

    # ===========================================================================
    # CELERY CONFIGURATION
    # ===========================================================================
    #
    # These settings optimize for document processing workload:
    # - JSON serialization (simple, debuggable)
    # - Time limits (prevent hung tasks)
    # - Prefetching (balance between efficiency and fairness)
    # - Worker restarts (prevent memory leaks)

    app.conf.update(
        # Serialization format for tasks and results
        # JSON is simple, human-readable, and universal
        # Alternative: pickle (faster but less safe)
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',

        # Timezone settings
        # All tasks use UTC for consistency across machines
        timezone='UTC',
        enable_utc=True,

        # Task tracking
        # track_started=True lets us see tasks in "STARTED" state
        # (not just PENDING → SUCCESS/FAILURE)
        task_track_started=True,

        # Time limits
        # task_time_limit: Hard limit (task is killed after this)
        # task_soft_time_limit: Soft limit (raises exception, task can clean up)
        #
        # Why 5 minutes?
        # - Most documents process in <10 seconds
        # - Large documents might take 60-120 seconds
        # - 5 minutes catches truly stuck tasks
        # - Prevents workers from being blocked forever
        task_time_limit=300,        # 5 minutes hard limit
        task_soft_time_limit=240,   # 4 minutes soft limit (allows cleanup)

        # Worker prefetching
        # How many tasks a worker grabs from queue at once
        #
        # worker_prefetch_multiplier=4:
        # - Worker with concurrency=8 will prefetch 32 tasks (8 * 4)
        # - Trade-off: Efficiency (less queue polling) vs Fairness (task distribution)
        #
        # Why 4?
        # - Good balance for document processing
        # - Not too high (would hoard tasks unfairly)
        # - Not too low (would poll queue too often)
        worker_prefetch_multiplier=4,

        # Worker restart policy
        # Restart worker after 1000 tasks
        #
        # Why restart?
        # - Prevents memory leaks from accumulating
        # - Fresh worker = consistent performance
        # - 1000 tasks is ~30-60 minutes of work
        #
        # Trade-off:
        # + Prevents slow memory leaks
        # - Brief downtime during restart (milliseconds)
        worker_max_tasks_per_child=1000,
    )

    # ==========================================================================
    # TASK DEFINITIONS
    # ==========================================================================

    @app.task(bind=True, name='classify_document', max_retries=3)
    def classify_document_task(
        self,
        file_path_str: str,
        categories: List[str],
        include_reasoning: bool = False,
        use_database: bool = False,
        database_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Celery task to classify a single document.

        This is the core task that runs on worker machines.
        Each worker executes this function for each document.

        Args:
            self: Task instance (because bind=True)
            file_path_str: String path to document file
            categories: List of classification categories
            include_reasoning: Include AI reasoning in result
            use_database: Enable database storage
            database_url: Database connection URL

        Returns:
            Dictionary with classification result:
                - success: True/False
                - category: Classified category
                - confidence: Confidence score
                - processing_time: How long it took
                - worker: Which worker processed it
                - task_id: Celery task ID

        Decorator parameters:
            @app.task: Registers this as a Celery task
            bind=True: Gives access to task instance (self)
            name='classify_document': Task name in queue
            max_retries=3: Retry up to 3 times on failure

        Why bind=True?
        - Access to self.request.id (task ID)
        - Access to self.request.hostname (worker name)
        - Access to self.retry() (for retrying)
        - Useful for debugging and monitoring

        Why max_retries=3?
        - Transient errors (network glitch, temporary API failure)
        - Exponential backoff: 2s, 4s, 8s
        - After 3 retries, give up (permanent failure)

        Task lifecycle:
        1. Client submits task to Redis queue
        2. Worker picks up task from queue
        3. Worker executes this function
        4. Worker stores result in Redis
        5. Client can retrieve result using task ID

        Example:
            # Submit task (returns immediately)
            result = classify_document_task.delay(
                "/path/to/doc.pdf",
                ["invoices", "contracts"]
            )

            # Check status
            print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE

            # Get result (blocks until complete)
            data = result.get(timeout=300)
            print(data['category'])
        """
        # Import inside task (important for worker process)
        #
        # Why import inside?
        # - Workers run in separate processes
        # - Each worker needs its own service instances
        # - Can't share objects across processes
        # - Imports are cheap (Python caches them)
        from src.classifier import DocumentClassifier
        from src.ollama_service import OllamaService
        from src.extractors import ExtractionService

        try:
            # Step 1: Convert string path to Path object
            file_path = Path(file_path_str)

            # Step 2: Create service instances
            #
            # Each task creates fresh service instances.
            # Why?
            # - Tasks run in worker processes
            # - Can't share service objects between processes
            # - Each task needs isolated services
            #
            # This might seem inefficient, but:
            # - Python imports are cached
            # - Service creation is fast (<10ms)
            # - Ensures clean state per task
            ollama = OllamaService()
            extractor = ExtractionService()
            classifier = DocumentClassifier(
                ollama_service=ollama,
                extraction_service=extractor,
                use_database=use_database
            )

            # Step 3: Update database connection if provided
            #
            # Workers might have different database URLs
            # (e.g., different machines, connection pooling)
            if use_database and database_url and classifier.db:
                from src.database import DatabaseService
                classifier.db = DatabaseService(database_url=database_url)

            # Step 4: Classify the document
            #
            # This is the actual work:
            # - Extract text from document
            # - Send to AI for classification
            # - Save to database (if enabled)
            #
            # Timing it for monitoring/debugging
            start_time = datetime.now()
            result = classifier.classify_document(file_path, include_reasoning)
            processing_time = (datetime.now() - start_time).total_seconds()

            # Step 5: Build result dictionary
            #
            # Return simple dictionary (not objects)
            # because results are serialized to JSON
            if result:
                return {
                    'success': True,
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'category': result.category,
                    'confidence': result.confidence,
                    'metadata': result.metadata,
                    'timestamp': result.timestamp.isoformat(),
                    'processing_time': processing_time,
                    'worker': self.request.hostname,  # Which worker processed this
                    'task_id': self.request.id,        # Celery task ID
                }
            else:
                # Classification failed (returned None)
                return {
                    'success': False,
                    'file_path': str(file_path),
                    'error': 'Classification failed - no result',
                    'processing_time': processing_time,
                }

        except Exception as e:
            # Task failed with exception
            #
            # Options:
            # 1. Retry (for transient errors)
            # 2. Give up (for permanent errors)
            #
            # We retry with exponential backoff
            logger.error(f"Task failed for {file_path_str}: {e}")

            # Retry with exponential backoff
            #
            # Retries: 0, 1, 2, 3
            # Countdown: 2^0=1s, 2^1=2s, 2^2=4s, 2^3=8s
            #
            # Why exponential backoff?
            # - Give transient errors time to resolve
            # - Don't hammer failing service
            # - Industry standard retry pattern
            try:
                raise self.retry(
                    exc=e,
                    countdown=2 ** self.request.retries  # Exponential: 1s, 2s, 4s, 8s
                )
            except self.MaxRetriesExceededError:
                # All retries exhausted, give up
                return {
                    'success': False,
                    'file_path': file_path_str,
                    'error': f'Max retries exceeded: {str(e)}',
                }

    @app.task(name='classify_batch')
    def classify_batch_task(
        file_paths: List[str],
        categories: List[str],
        include_reasoning: bool = False,
        use_database: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a batch of documents for distributed classification.

        This task creates a "group" of classify_document_task tasks.
        Think of it as: "create 1000 tasks and submit them all at once"

        Args:
            file_paths: List of file paths to classify
            categories: Classification categories
            include_reasoning: Include AI reasoning
            use_database: Enable database storage

        Returns:
            Dictionary with batch info:
                - batch_id: ID to track this batch
                - total_tasks: How many documents
                - status: 'submitted'

        What is a Celery group?
        - Collection of tasks submitted together
        - All tasks execute in parallel
        - Can track progress as a group
        - Can wait for all to complete

        Example:
            # Submit 1000 documents
            result = classify_batch_task.delay(
                ["/doc1.pdf", "/doc2.pdf", ..., "/doc1000.pdf"],
                ["invoices", "contracts"]
            )

            # Track progress
            batch_id = result.id
            # Check how many completed: check_progress(batch_id)
            # Wait for all: wait_for_completion(batch_id)

        Flow:
        1. Client calls this task
        2. This task creates 1000 individual tasks
        3. All 1000 tasks are queued in Redis
        4. Workers pick up and process tasks
        5. Client can track progress using batch_id
        """
        # Create a group of tasks
        #
        # group() creates a collection of tasks
        # .s() creates a "signature" (task template)
        #
        # This doesn't execute yet, just prepares the tasks
        job = group(
            classify_document_task.s(  # .s() = signature (task template)
                fp,
                categories,
                include_reasoning,
                use_database,
                settings.database_url
            )
            for fp in file_paths  # One task per file
        )

        # Execute the group
        #
        # apply_async() submits all tasks to queue
        # Returns a GroupResult object for tracking
        result = job.apply_async()

        return {
            'batch_id': result.id,           # Use this to track progress
            'total_tasks': len(file_paths),  # How many documents
            'status': 'submitted'            # Initial status
        }


    # ==============================================================================
    # DISTRIBUTED PROCESSOR CLASS
    # ==============================================================================

    class CeleryDistributedProcessor:
        """
        Distributed document processor using Celery.

        WHAT IT DOES:
            Manages distributed document processing across multiple worker machines.
            Submits tasks, tracks progress, retrieves results.

        HOW IT WORKS:
            1. Client creates CeleryDistributedProcessor
            2. Client calls submit_batch() or submit_directory()
            3. Processor submits tasks to Redis queue
            4. Workers pick up tasks and process documents
            5. Client can check_progress() to monitor
            6. Client can wait_for_completion() to wait
            7. Client can get_results() to retrieve all results

        KEY FEATURES:
            - **Batch Submission**: Submit thousands of tasks at once
            - **Progress Tracking**: Real-time progress monitoring
            - **Chunk Management**: Automatically splits huge batches
            - **Result Retrieval**: Get all results when done
            - **Wait with Progress**: Block until complete with progress bar

        SCALING EXAMPLE:
            Machine 1: celery worker --concurrency=8
            Machine 2: celery worker --concurrency=8
            Machine 3: celery worker --concurrency=8
            Total: 24 concurrent documents

            Add Machine 4, 5, 6... for more throughput!

        EXAMPLE USAGE:
            ```python
            # Create processor
            processor = CeleryDistributedProcessor(
                categories=["invoices", "contracts", "reports"],
                use_database=True
            )

            # Submit directory for processing
            batch_id = processor.submit_directory(Path("documents"))
            print(f"Submitted batch: {batch_id}")

            # Check progress periodically
            progress = processor.check_progress(batch_id)
            print(f"Progress: {progress['completed']}/{progress['total_tasks']}")

            # Or wait until complete (with progress bar)
            stats = processor.wait_for_completion(batch_id)
            print(f"Complete: {stats['successful']} successful, {stats['failed']} failed")

            # Get all results
            results = processor.get_results(batch_id)
            for result in results:
                if result['success']:
                    print(f"{result['file_name']}: {result['category']}")
            ```

        COMPARISON WITH OTHER PROCESSORS:
            parallel_processor.py:
            - Single machine
            - Multiprocessing
            - ~2,400 docs/hour (8 cores)

            async_batch_processor.py:
            - Single machine
            - Async I/O
            - ~3,000 docs/hour

            celery_tasks.py (this file):
            - Multiple machines
            - Distributed
            - ~24,000 docs/hour (10 machines × 8 cores)
            - Scales linearly: 20 machines = ~48,000 docs/hour!
        """

        def __init__(
            self,
            categories: Optional[List[str]] = None,
            use_database: bool = False,
            batch_size: int = 1000,
        ):
            """
            Initialize distributed processor.

            Args:
                categories: Classification categories (default: from config)
                use_database: Enable database storage
                batch_size: Max documents per batch chunk (default: 1000)

            What happens during initialization:
            1. Check Celery is installed
            2. Load configuration
            3. Set batch size for chunking

            Why batch_size=1000?
            - Celery groups have practical limits
            - 1000 tasks per group is efficient
            - Larger batches are split into multiple groups
            - Can be tuned based on your setup

            Example:
                >>> # Basic setup
                >>> processor = CeleryDistributedProcessor()

                >>> # With database and custom categories
                >>> processor = CeleryDistributedProcessor(
                ...     categories=["invoices", "contracts", "reports", "other"],
                ...     use_database=True,
                ...     batch_size=500  # Smaller chunks
                ... )
            """
            # Check if Celery is available
            if not CELERY_AVAILABLE:
                raise ImportError(
                    "Celery is required for distributed processing. "
                    "Install with: pip install celery redis"
                )

            # Load configuration
            self.categories = categories or settings.category_list
            self.use_database = use_database
            self.batch_size = batch_size

            logger.info("Initialized CeleryDistributedProcessor")

        # ==========================================================================
        # BATCH SUBMISSION
        # ==========================================================================

        def submit_batch(
            self,
            file_paths: List[Path],
            include_reasoning: bool = False
        ) -> str:
            """
            Submit a batch of documents for processing.

            This queues tasks for all documents in the batch.
            Workers will pick them up and process them.

            Args:
                file_paths: List of document paths
                include_reasoning: Include AI reasoning in results

            Returns:
                Batch ID string for tracking progress

            How it works:
            1. Convert Path objects to strings (for JSON serialization)
            2. Check if batch is too large (>batch_size)
            3. If too large, split into chunks
            4. Submit each chunk as a separate group
            5. Return combined batch ID

            Why split large batches?
            - Celery groups have practical limits
            - Smaller groups = better load distribution
            - Can track progress per chunk
            - More resilient to failures

            Example:
                >>> processor = CeleryDistributedProcessor()
                >>> files = [Path(f"doc{i}.pdf") for i in range(10000)]
                >>> batch_id = processor.submit_batch(files)
                >>> print(f"Submitted {len(files)} documents: {batch_id}")
            """
            # Convert Path objects to strings for JSON serialization
            file_path_strs = [str(fp) for fp in file_paths]

            # Check if batch needs chunking
            if len(file_paths) > self.batch_size:
                # Large batch: split into chunks
                logger.info(f"Splitting batch of {len(file_paths)} into chunks of {self.batch_size}")

                batch_ids = []

                # Submit chunks
                for i in range(0, len(file_path_strs), self.batch_size):
                    chunk = file_path_strs[i:i + self.batch_size]

                    # Submit this chunk
                    result = classify_batch_task.delay(
                        chunk,
                        self.categories,
                        include_reasoning,
                        self.use_database
                    )
                    batch_ids.append(result.id)

                logger.info(f"Submitted {len(batch_ids)} batch chunks")

                # Return comma-separated IDs
                # (check_progress and get_results handle this format)
                return ",".join(batch_ids)

            else:
                # Small batch: submit as single group
                result = classify_batch_task.delay(
                    file_path_strs,
                    self.categories,
                    include_reasoning,
                    self.use_database
                )

                logger.info(f"Submitted batch: {result.id}")
                return result.id

        def submit_directory(
            self,
            input_dir: Path,
            recursive: bool = True,
            include_reasoning: bool = False,
            file_extensions: Optional[List[str]] = None
        ) -> str:
            """
            Submit all documents in a directory for processing.

            Convenience method that:
            1. Scans directory for documents
            2. Filters by extension
            3. Submits as batch

            Args:
                input_dir: Directory containing documents
                recursive: Also process subdirectories (default: True)
                include_reasoning: Include AI reasoning
                file_extensions: File types to process (default: all supported)

            Returns:
                Batch ID for tracking

            Example:
                >>> processor = CeleryDistributedProcessor()
                >>> batch_id = processor.submit_directory(
                ...     Path("documents/invoices"),
                ...     recursive=True
                ... )
                >>> print(f"Submitted directory: {batch_id}")
            """
            logger.info(f"Scanning directory: {input_dir}")

            # Default extensions
            if file_extensions is None:
                file_extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md"]

            # Collect files
            file_paths = []
            if recursive:
                # Search all subdirectories
                for ext in file_extensions:
                    file_paths.extend(input_dir.rglob(f"*{ext}"))
            else:
                # Search only top level
                for ext in file_extensions:
                    file_paths.extend(input_dir.glob(f"*{ext}"))

            # Filter to only files (not directories)
            file_paths = [f for f in file_paths if f.is_file()]

            logger.info(f"Found {len(file_paths)} documents to submit")

            if not file_paths:
                logger.warning("No documents found")
                return ""

            # Submit as batch
            return self.submit_batch(file_paths, include_reasoning)

        # ==========================================================================
        # PROGRESS TRACKING
        # ==========================================================================

        def check_progress(self, batch_id: str) -> Dict[str, Any]:
            """
            Check progress of a batch (non-blocking).

            Queries Celery to see how many tasks are complete.

            Args:
                batch_id: Batch ID from submission

            Returns:
                Dictionary with progress information:
                    - batch_id: The batch ID
                    - total_tasks: Total number of tasks
                    - completed: How many finished
                    - successful: How many succeeded
                    - failed: How many failed
                    - pending: How many still waiting
                    - progress_percent: Completion percentage
                    - status: Overall status

            This is non-blocking - returns immediately with current status.

            Example:
                >>> progress = processor.check_progress(batch_id)
                >>> print(f"Progress: {progress['progress_percent']:.1f}%")
                >>> print(f"Status: {progress['completed']}/{progress['total_tasks']}")
            """
            from celery.result import AsyncResult

            # Handle multiple batch IDs (from chunked batches)
            if ',' in batch_id:
                batch_ids = batch_id.split(',')
                all_results = []

                # Get result objects for each chunk
                for bid in batch_ids:
                    result = AsyncResult(bid, app=app)
                    all_results.append(result)

                # Aggregate stats across all chunks
                total = sum(len(r.children) if hasattr(r, 'children') else 0 for r in all_results)
                completed = sum(
                    sum(1 for c in r.children if c.ready()) if hasattr(r, 'children') else 0
                    for r in all_results
                )
                successful = sum(
                    sum(1 for c in r.children if c.successful()) if hasattr(r, 'children') else 0
                    for r in all_results
                )
                failed = sum(
                    sum(1 for c in r.children if c.failed()) if hasattr(r, 'children') else 0
                    for r in all_results
                )

                return {
                    'batch_id': batch_id,
                    'total_tasks': total,
                    'completed': completed,
                    'successful': successful,
                    'failed': failed,
                    'pending': total - completed,
                    'progress_percent': (completed / total * 100) if total > 0 else 0,
                    'status': 'completed' if completed == total else 'processing'
                }

            else:
                # Single batch ID
                result = AsyncResult(batch_id, app=app)

                if hasattr(result, 'children'):
                    # This is a group result
                    children = result.children
                    total = len(children)
                    completed = sum(1 for c in children if c.ready())
                    successful = sum(1 for c in children if c.successful())
                    failed = sum(1 for c in children if c.failed())

                    return {
                        'batch_id': batch_id,
                        'total_tasks': total,
                        'completed': completed,
                        'successful': successful,
                        'failed': failed,
                        'pending': total - completed,
                        'progress_percent': (completed / total * 100) if total > 0 else 0,
                        'status': result.state
                    }
                else:
                    # Single task result
                    return {
                        'batch_id': batch_id,
                        'status': result.state,
                        'info': str(result.info)
                    }

        def get_results(self, batch_id: str, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
            """
            Get results from a batch (BLOCKING - waits until complete).

            This retrieves all classification results.
            Blocks until all tasks are finished.

            Args:
                batch_id: Batch ID from submission
                timeout: Optional timeout in seconds (None = wait forever)

            Returns:
                List of result dictionaries, one per document

            WARNING: This blocks until all tasks complete!
            For non-blocking progress, use check_progress() instead.

            Example:
                >>> # Submit batch
                >>> batch_id = processor.submit_directory(Path("documents"))
                >>>
                >>> # Wait and get results (blocks)
                >>> results = processor.get_results(batch_id, timeout=3600)  # 1 hour max
                >>>
                >>> # Process results
                >>> for result in results:
                ...     if result['success']:
                ...         print(f"{result['file_name']}: {result['category']}")
                ...     else:
                ...         print(f"{result['file_name']}: FAILED - {result['error']}")
            """
            from celery.result import AsyncResult

            # Handle multiple batch IDs (from chunked batches)
            if ',' in batch_id:
                batch_ids = batch_id.split(',')
                all_results = []

                # Get results from each chunk
                for bid in batch_ids:
                    result = AsyncResult(bid, app=app)
                    if hasattr(result, 'children'):
                        # Get result from each child task (blocks)
                        all_results.extend([c.get(timeout=timeout) for c in result.children])

                return all_results

            else:
                # Single batch ID
                result = AsyncResult(batch_id, app=app)

                if hasattr(result, 'children'):
                    # Group result: get from all children (blocks)
                    return [child.get(timeout=timeout) for child in result.children]
                else:
                    # Single task result
                    return [result.get(timeout=timeout)]

        def wait_for_completion(
            self,
            batch_id: str,
            poll_interval: float = 5.0,
            show_progress: bool = True
        ) -> Dict[str, Any]:
            """
            Wait for batch completion with progress tracking (BLOCKING).

            This polls for progress and displays a progress bar.
            Blocks until all tasks complete.

            Args:
                batch_id: Batch ID from submission
                poll_interval: Seconds between progress checks (default: 5.0)
                show_progress: Show progress bar (default: True)

            Returns:
                Final statistics dictionary with completion stats

            This is useful for:
            - CLI scripts that should wait for completion
            - Batch jobs that need to know when done
            - Monitoring progress in real-time

            Example:
                >>> # Submit batch
                >>> batch_id = processor.submit_directory(Path("documents"))
                >>>
                >>> # Wait with progress bar
                >>> stats = processor.wait_for_completion(batch_id)
                >>> # Shows: Processing documents: 100%|████████| 10000/10000
                >>>
                >>> print(f"Complete! {stats['successful']} successful, {stats['failed']} failed")
            """
            import time
            from tqdm import tqdm

            logger.info(f"Waiting for batch {batch_id} to complete...")

            # Get initial progress to know total
            progress_info = self.check_progress(batch_id)
            total = progress_info.get('total_tasks', 0)

            # Create progress bar if requested
            if show_progress and total > 0:
                pbar = tqdm(total=total, desc="Processing documents", unit="doc")

            last_completed = 0

            # Poll loop
            while True:
                # Check current progress
                progress_info = self.check_progress(batch_id)
                completed = progress_info.get('completed', 0)

                # Update progress bar
                if show_progress and total > 0:
                    pbar.update(completed - last_completed)

                last_completed = completed

                # Check if done
                if progress_info.get('status') == 'completed' or completed >= total:
                    if show_progress and total > 0:
                        pbar.close()
                    break

                # Wait before checking again
                time.sleep(poll_interval)

            logger.success(
                f"Batch complete: {progress_info.get('successful', 0)} successful, "
                f"{progress_info.get('failed', 0)} failed"
            )

            return progress_info

# End of CELERY_AVAILABLE block

else:
    # ===========================================================================
    # CELERY NOT AVAILABLE - PROVIDE HELPFUL ERROR
    # ===========================================================================

    logger.warning("Celery not installed. Distributed processing unavailable.")

    class CeleryDistributedProcessor:
        """Placeholder class when Celery is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Celery is required for distributed processing. "
                "Install with: pip install celery redis\n"
                "\n"
                "Setup:\n"
                "1. pip install celery redis\n"
                "2. docker run -d -p 6379:6379 redis\n"
                "3. celery -A src.celery_tasks worker --loglevel=info\n"
            )
