"""
Celery tasks for parallel document processing.

This module contains all background tasks that run on distributed Celery workers.
Supports processing 500K+ documents with horizontal scaling.
"""

from celery import Celery, Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, Any
import json

from config import settings
from src.classifier import DocumentClassifier
from src.metadata_extractor import MetadataExtractor
from src.search_service import SearchService
from src.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================

celery_app = Celery(
    'document_pipeline',
    broker=settings.CELERY_BROKER_URL,  # Redis
    backend=settings.CELERY_RESULT_BACKEND,  # Redis
)

# Celery settings optimized for high throughput
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_expires=3600,  # Results expire after 1 hour

    # Time zone
    timezone='UTC',
    enable_utc=True,

    # Performance
    task_acks_late=True,  # Don't lose tasks if worker crashes
    worker_prefetch_multiplier=4,  # Fetch 4 tasks at a time per worker
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit

    # Retries
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=True,

    # Worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (prevent memory leaks)
    worker_disable_rate_limits=True,  # Max performance

    # Results
    result_backend_transport_options={
        'master_name': 'mymaster'
    },
)

# ============================================================================
# DATABASE SESSION
# ============================================================================

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# ============================================================================
# CELERY TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(self, document_id: int, file_path: str) -> Dict[str, Any]:
    """
    Process a single document: classify → extract → index.

    This task runs on distributed Celery workers for parallel processing.

    Args:
        document_id: Database document ID
        file_path: Path to uploaded file

    Returns:
        dict: Processing result with status, category, metadata

    Raises:
        Retry if processing fails (max 3 retries)
    """
    logger.info(f"[Task {self.request.id}] Processing document {document_id}: {file_path}")

    db = Database()

    try:
        # Update status to processing
        db.update_document_status(document_id, 'processing')
        logger.info(f"[{document_id}] Status: processing")

        # Step 1: Classify document
        logger.info(f"[{document_id}] Step 1/3: Classifying...")
        classifier = DocumentClassifier()
        classification_result = classifier.classify(file_path)

        category = classification_result['category']
        confidence = classification_result['confidence']

        logger.info(f"[{document_id}] Classified as '{category}' (confidence: {confidence:.2f})")

        # Update database with classification
        db.execute_query(
            """
            UPDATE documents
            SET category = %s,
                confidence = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (category, confidence, document_id)
        )

        # Step 2: Extract metadata
        logger.info(f"[{document_id}] Step 2/3: Extracting metadata...")
        extractor = MetadataExtractor()
        metadata = extractor.extract(file_path, category)

        logger.info(f"[{document_id}] Extracted {len(metadata)} metadata fields")

        # Update database with metadata
        db.execute_query(
            """
            UPDATE documents
            SET metadata = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (json.dumps(metadata), document_id)
        )

        # Step 3: Index to search (OpenSearch + vector embeddings)
        logger.info(f"[{document_id}] Step 3/3: Indexing...")
        search_service = SearchService()

        # Get document content for indexing
        doc_data = db.fetch_one(
            "SELECT * FROM documents WHERE id = %s",
            (document_id,)
        )

        # Index to OpenSearch
        search_service.index_document(
            document_id=document_id,
            file_name=doc_data['file_name'],
            category=category,
            content=metadata.get('text_content', ''),
            metadata=metadata
        )

        logger.info(f"[{document_id}] Indexed to search")

        # Update final status
        db.execute_query(
            """
            UPDATE documents
            SET processing_status = 'completed',
                indexed = TRUE,
                indexed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            """,
            (document_id,)
        )

        logger.info(f"[{document_id}] ✅ Processing completed successfully")

        return {
            'document_id': document_id,
            'status': 'completed',
            'category': category,
            'confidence': confidence,
            'metadata_fields': len(metadata),
        }

    except Exception as e:
        logger.error(f"[{document_id}] ❌ Processing failed: {str(e)}")

        # Update error status in database
        db.execute_query(
            """
            UPDATE documents
            SET processing_status = 'failed',
                error_message = %s,
                retry_count = retry_count + 1,
                updated_at = NOW()
            WHERE id = %s
            """,
            (str(e), document_id)
        )

        # Retry task if not exceeded max retries
        if self.request.retries < self.max_retries:
            logger.warning(f"[{document_id}] Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        # Max retries exceeded
        logger.error(f"[{document_id}] Max retries exceeded. Marking as permanently failed.")
        raise


@celery_app.task
def process_batch_task(batch_id: str, document_ids: list) -> Dict[str, Any]:
    """
    Process a batch of documents in parallel.

    Creates individual tasks for each document and monitors completion.

    Args:
        batch_id: Batch identifier
        document_ids: List of document IDs to process

    Returns:
        dict: Batch processing summary
    """
    logger.info(f"[Batch {batch_id}] Starting batch processing of {len(document_ids)} documents")

    from celery import group

    # Create a group of tasks (runs in parallel)
    job = group([
        process_document_task.s(doc_id, f"uploads/{doc_id}_*.pdf")
        for doc_id in document_ids
    ])

    # Execute all tasks in parallel
    result = job.apply_async()

    logger.info(f"[Batch {batch_id}] Dispatched {len(document_ids)} tasks to workers")

    return {
        'batch_id': batch_id,
        'document_count': len(document_ids),
        'group_id': result.id,
        'status': 'processing'
    }


@celery_app.task
def cleanup_old_results_task():
    """
    Periodic task to clean up old task results from Redis.

    Run this hourly to prevent Redis from filling up.
    """
    logger.info("Running cleanup of old task results...")

    # Celery automatically expires results based on result_expires setting
    # This is just a placeholder for additional cleanup logic if needed

    logger.info("Cleanup completed")
    return {'status': 'completed'}


# ============================================================================
# TASK MONITORING
# ============================================================================

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a Celery task.

    Args:
        task_id: Celery task ID

    Returns:
        dict: Task status, result, progress
    """
    from celery.result import AsyncResult

    task = AsyncResult(task_id, app=celery_app)

    return {
        'task_id': task_id,
        'state': task.state,  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
        'status': task.status,
        'result': task.result if task.ready() else None,
        'info': task.info,
    }


def get_worker_stats() -> Dict[str, Any]:
    """
    Get statistics about active Celery workers.

    Returns:
        dict: Worker count, active tasks, queue length
    """
    inspect = celery_app.control.inspect()

    stats = inspect.stats()
    active = inspect.active()

    worker_count = len(stats) if stats else 0
    active_tasks = sum(len(tasks) for tasks in active.values()) if active else 0

    return {
        'worker_count': worker_count,
        'active_tasks': active_tasks,
        'workers': list(stats.keys()) if stats else [],
    }


# ============================================================================
# PERIODIC TASKS (Optional)
# ============================================================================

# Uncomment to enable periodic cleanup
# from celery.schedules import crontab
#
# celery_app.conf.beat_schedule = {
#     'cleanup-every-hour': {
#         'task': 'api.tasks.cleanup_old_results_task',
#         'schedule': crontab(minute=0),  # Every hour
#     },
# }
