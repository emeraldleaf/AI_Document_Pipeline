# Parallel Processing for 500K Documents

## Goal: Process 500K documents efficiently with a monolith architecture

**Solution: Monolith API + Distributed Celery Workers**

This gives you the scalability of microservices with the simplicity of a monolith.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Monolith                          │
│                  (api/main.py - Port 8000)                   │
│                                                              │
│  POST /api/upload        → Save file, queue task            │
│  POST /api/batch-upload  → Queue 1000s of tasks             │
│  GET  /api/status/{id}   → Check processing status          │
│  GET  /api/search        → Search processed docs            │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Publishes tasks to
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Redis Queue                             │
│            (Task broker + Result backend)                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                   ↓                   ↓
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Celery Worker │  │ Celery Worker │  │ Celery Worker │
│   (Pod 1)     │  │   (Pod 2)     │  │   (Pod 3)     │
│  - Classify   │  │  - Classify   │  │  - Classify   │
│  - Extract    │  │  - Extract    │  │  - Extract    │
│  - Index      │  │  - Index      │  │  - Index      │
└───────────────┘  └───────────────┘  └───────────────┘
        ... scale to 20-50 workers ...
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌──────────────────┐                  ┌──────────────────┐
│   PostgreSQL     │                  │   OpenSearch     │
│   (SQLModel)     │                  │  (Vector Search) │
└──────────────────┘                  └──────────────────┘
```

**Key Insight:**
- 1 API server (simple)
- 50 workers (massive parallelism)
- All share same code (easy deployment)

---

## Performance Math

### Single Worker Performance

**Processing times (per document):**
- Classification: 2-5 seconds (Ollama vision)
- Extraction: 3-8 seconds (Docling + LLM)
- Indexing: 0.5-1 second (Database + OpenSearch)
- **Total: ~10 seconds per document**

**Throughput:**
- 1 worker = 6 docs/min = 360 docs/hour = 8,640 docs/day

### Parallel Workers

| Workers | Docs/Day | 500K in Days |
|---------|----------|--------------|
| 10      | 86,400   | 5.8 days     |
| 20      | 172,800  | 2.9 days     |
| 30      | 259,200  | 1.9 days     |
| **50**  | **432,000** | **1.2 days** |
| 100     | 864,000  | 0.6 days     |

**✅ With 50 workers: 500K documents in ~28 hours**

---

## Implementation

### 1. Enhanced Monolith with Celery

**File: `api/main.py`**

```python
"""
Enhanced Monolith with Parallel Processing
Handles 500K documents with distributed Celery workers
"""

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, create_engine
from celery import Celery, group, chord
from celery.result import AsyncResult
from typing import List, Optional
import uuid
from pathlib import Path
import shutil

from models.document import Document, DocumentCreate, DocumentRead
from src.classifier import DocumentClassifier
from src.metadata_extractor import MetadataExtractor
from src.search_service import SearchService

# ============================================================================
# CONFIGURATION
# ============================================================================

app = FastAPI(title="AI Document Pipeline - Parallel Processing")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database with SQLModel
DATABASE_URL = "postgresql://postgres:devpassword@localhost:5432/documents"
engine = create_engine(DATABASE_URL)

# Celery for parallel processing
celery = Celery(
    'document_pipeline',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
)

# Celery configuration for high throughput
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Performance settings
    task_acks_late=True,  # Don't lose tasks if worker crashes
    worker_prefetch_multiplier=4,  # Fetch 4 tasks at a time
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # 9 minute soft limit

    # Concurrency
    worker_concurrency=4,  # 4 threads per worker
    worker_pool='prefork',  # Use multiprocessing
)

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/api/upload", response_model=dict)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a single document and process it asynchronously.

    Returns immediately with task_id for tracking.
    """
    # Generate document ID
    doc_id = str(uuid.uuid4())

    # Save file
    file_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create database record
    with Session(engine) as session:
        doc = Document(
            document_id=doc_id,
            file_path=str(file_path),
            filename=file.filename,
            processing_status="queued",
        )
        session.add(doc)
        session.commit()

    # Queue task for processing (runs on worker)
    task = process_document_task.delay(doc_id, str(file_path))

    return {
        "document_id": doc_id,
        "task_id": task.id,
        "status": "queued",
        "message": "Document queued for processing"
    }


@app.post("/api/batch-upload", response_model=dict)
async def batch_upload(files: List[UploadFile] = File(...)):
    """
    Upload multiple documents and process them in parallel.

    Returns immediately with batch_id for tracking.
    """
    batch_id = str(uuid.uuid4())
    document_ids = []
    tasks = []

    # Save all files and create database records
    with Session(engine) as session:
        for file in files:
            doc_id = str(uuid.uuid4())
            file_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"

            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Create database record
            doc = Document(
                document_id=doc_id,
                file_path=str(file_path),
                filename=file.filename,
                processing_status="queued",
                batch_id=batch_id,
            )
            session.add(doc)
            document_ids.append(doc_id)

        session.commit()

    # Queue all tasks in parallel (Celery distributes to workers)
    task_group = group([
        process_document_task.s(doc_id, str(UPLOAD_DIR / f"{doc_id}_*"))
        for doc_id in document_ids
    ])
    result = task_group.apply_async()

    return {
        "batch_id": batch_id,
        "document_count": len(files),
        "document_ids": document_ids,
        "status": "queued",
        "message": f"{len(files)} documents queued for parallel processing"
    }


@app.get("/api/status/{document_id}", response_model=dict)
async def get_status(document_id: str):
    """
    Get processing status of a document.
    """
    with Session(engine) as session:
        doc = session.exec(
            select(Document).where(Document.document_id == document_id)
        ).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "document_id": doc.document_id,
            "filename": doc.filename,
            "status": doc.processing_status,
            "category": doc.category,
            "confidence": doc.confidence,
            "indexed": doc.indexed,
            "error_message": doc.error_message,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }


@app.get("/api/batch-status/{batch_id}", response_model=dict)
async def get_batch_status(batch_id: str):
    """
    Get status of all documents in a batch.
    """
    with Session(engine) as session:
        docs = session.exec(
            select(Document).where(Document.batch_id == batch_id)
        ).all()

        if not docs:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Aggregate statistics
        total = len(docs)
        completed = sum(1 for d in docs if d.processing_status == "completed")
        failed = sum(1 for d in docs if d.processing_status == "failed")
        processing = total - completed - failed

        return {
            "batch_id": batch_id,
            "total": total,
            "completed": completed,
            "processing": processing,
            "failed": failed,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "documents": [
                {
                    "document_id": d.document_id,
                    "filename": d.filename,
                    "status": d.processing_status,
                    "category": d.category,
                }
                for d in docs
            ]
        }


@app.get("/api/search")
async def search_documents(
    q: str,
    limit: int = 10,
    offset: int = 0,
    category: Optional[str] = None,
):
    """
    Search processed documents.
    """
    search_service = SearchService()
    results = await search_service.search(
        query=q,
        limit=limit,
        offset=offset,
        category=category,
    )
    return results


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    # Check database
    try:
        with Session(engine) as session:
            session.exec(select(Document).limit(1)).first()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Celery
    try:
        celery.control.inspect().active()
        celery_status = "healthy"
    except Exception as e:
        celery_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" and celery_status == "healthy" else "degraded",
        "database": db_status,
        "celery": celery_status,
    }


# ============================================================================
# CELERY TASKS (Run on distributed workers)
# ============================================================================

@celery.task(bind=True, max_retries=3)
def process_document_task(self, document_id: str, file_path: str):
    """
    Process a single document (runs on worker).

    This task is distributed across all available Celery workers.
    """
    try:
        # Update status to processing
        with Session(engine) as session:
            doc = session.exec(
                select(Document).where(Document.document_id == document_id)
            ).first()
            doc.processing_status = "processing"
            session.commit()

        # Step 1: Classify document
        classifier = DocumentClassifier()
        category, confidence = classifier.classify(file_path)

        # Update database
        with Session(engine) as session:
            doc = session.exec(
                select(Document).where(Document.document_id == document_id)
            ).first()
            doc.category = category
            doc.confidence = confidence
            session.commit()

        # Step 2: Extract metadata
        extractor = MetadataExtractor()
        metadata = extractor.extract(file_path, category)

        # Step 3: Generate embeddings and index
        search_service = SearchService()
        search_service.index_document(
            document_id=document_id,
            category=category,
            metadata=metadata,
        )

        # Update status to completed
        with Session(engine) as session:
            doc = session.exec(
                select(Document).where(Document.document_id == document_id)
            ).first()
            doc.processing_status = "completed"
            doc.metadata_ = metadata
            doc.indexed = True
            doc.indexed_at = datetime.utcnow()
            session.commit()

        return {
            "document_id": document_id,
            "status": "completed",
            "category": category,
            "confidence": confidence,
        }

    except Exception as e:
        # Update status to failed
        with Session(engine) as session:
            doc = session.exec(
                select(Document).where(Document.document_id == document_id)
            ).first()
            doc.processing_status = "failed"
            doc.error_message = str(e)
            doc.retry_count += 1
            session.commit()

        # Retry task
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

        raise


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables created")
    print("✅ API server ready")
    print("🚀 Start workers with: celery -A api.main worker --loglevel=info --concurrency=4")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 2. Start Workers for Parallel Processing

### Single Machine (Development)

```bash
# Terminal 1: Start API
uvicorn api.main:app --reload --port 8000

# Terminal 2: Start 10 workers (40 concurrent tasks)
celery -A api.main worker --loglevel=info --concurrency=4 --autoscale=10,1

# Terminal 3: Monitor (optional)
celery -A api.main flower
```

### Multiple Machines (Production)

```bash
# Machine 1: API Server
uvicorn api.main:app --workers 4 --port 8000

# Machine 2-6: Celery Workers (10 workers each = 50 total)
# Each machine runs:
celery -A api.main worker \
    --loglevel=info \
    --concurrency=4 \
    --autoscale=10,1 \
    --hostname=worker@%h
```

### Kubernetes (Cloud)

```yaml
# deployment-workers.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-workers
spec:
  replicas: 50  # 50 worker pods
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: worker
        image: your-app:latest
        command:
          - celery
          - -A
          - api.main
          - worker
          - --loglevel=info
          - --concurrency=4
        env:
          - name: REDIS_URL
            value: redis://redis-service:6379/0
          - name: DATABASE_URL
            value: postgresql://postgres:password@postgres:5432/documents
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

```bash
# Deploy
kubectl apply -f deployment-workers.yaml

# Scale up for 500K job
kubectl scale deployment celery-workers --replicas=100

# Scale down after
kubectl scale deployment celery-workers --replicas=10
```

---

## 3. Batch Upload Script

**File: `scripts/batch_upload.py`**

```python
"""
Batch upload 500K documents to the API for parallel processing.
"""

import requests
import asyncio
import aiohttp
from pathlib import Path
from typing import List
import json
from tqdm import tqdm

API_URL = "http://localhost:8000"

async def upload_batch(session: aiohttp.ClientSession, files: List[Path]) -> dict:
    """Upload a batch of files."""
    data = aiohttp.FormData()

    for file_path in files:
        data.add_field(
            'files',
            open(file_path, 'rb'),
            filename=file_path.name,
            content_type='application/pdf'
        )

    async with session.post(f"{API_URL}/api/batch-upload", data=data) as response:
        return await response.json()


async def upload_all_documents(document_dir: Path, batch_size: int = 100):
    """
    Upload all documents in directory in batches.

    Args:
        document_dir: Directory containing documents
        batch_size: Number of documents per batch (100-1000)
    """
    # Get all documents
    documents = list(document_dir.glob("*.pdf"))
    total = len(documents)

    print(f"📁 Found {total} documents")
    print(f"📦 Uploading in batches of {batch_size}")

    # Create batches
    batches = [
        documents[i:i + batch_size]
        for i in range(0, total, batch_size)
    ]

    print(f"🔢 Created {len(batches)} batches")

    # Upload batches concurrently
    async with aiohttp.ClientSession() as session:
        batch_ids = []

        with tqdm(total=len(batches), desc="Uploading batches") as pbar:
            for batch in batches:
                result = await upload_batch(session, batch)
                batch_ids.append(result['batch_id'])
                pbar.update(1)

    print(f"\n✅ All {total} documents uploaded!")
    print(f"📋 Batch IDs: {json.dumps(batch_ids, indent=2)}")

    return batch_ids


async def monitor_progress(batch_ids: List[str]):
    """Monitor processing progress of all batches."""
    async with aiohttp.ClientSession() as session:
        while True:
            total_docs = 0
            completed_docs = 0

            for batch_id in batch_ids:
                async with session.get(f"{API_URL}/api/batch-status/{batch_id}") as response:
                    status = await response.json()
                    total_docs += status['total']
                    completed_docs += status['completed']

            progress = (completed_docs / total_docs * 100) if total_docs > 0 else 0

            print(f"\r📊 Progress: {completed_docs}/{total_docs} ({progress:.1f}%)", end="")

            if completed_docs == total_docs:
                print("\n✅ All documents processed!")
                break

            await asyncio.sleep(10)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python batch_upload.py /path/to/documents")
        sys.exit(1)

    document_dir = Path(sys.argv[1])

    if not document_dir.exists():
        print(f"❌ Directory not found: {document_dir}")
        sys.exit(1)

    # Upload
    batch_ids = asyncio.run(upload_all_documents(document_dir, batch_size=100))

    # Monitor
    print("\n📈 Monitoring progress...")
    asyncio.run(monitor_progress(batch_ids))
```

**Usage:**
```bash
# Upload 500K documents
python scripts/batch_upload.py /path/to/500k_documents/
```

---

## 4. Performance Tuning

### Redis Configuration

```bash
# redis.conf - Optimize for Celery

# Memory
maxmemory 8gb
maxmemory-policy allkeys-lru

# Performance
save ""  # Disable disk persistence (use for speed)
appendonly no

# Network
tcp-backlog 511
timeout 0
tcp-keepalive 300

# Limits
maxclients 10000
```

### PostgreSQL Configuration

```sql
-- postgresql.conf

-- Connections
max_connections = 200

-- Memory
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB

-- Parallel queries
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

-- Write performance
checkpoint_completion_target = 0.9
wal_buffers = 16MB

-- Vacuum
autovacuum = on
autovacuum_max_workers = 4
```

### Celery Autoscaling

```bash
# Auto-scale workers based on queue length

# Min 10 workers, max 50 workers
celery -A api.main worker \
    --loglevel=info \
    --autoscale=50,10 \
    --max-tasks-per-child=100

# This will:
# - Start with 10 workers
# - Scale up to 50 when queue is full
# - Scale down when idle
# - Restart workers after 100 tasks (prevent memory leaks)
```

---

## 5. Monitoring

### Flower (Celery Dashboard)

```bash
# Install
pip install flower

# Run
celery -A api.main flower --port=5555

# Access at http://localhost:5555
```

**Metrics:**
- Active workers
- Tasks per second
- Queue length
- Task success/failure rates
- Average processing time

### Prometheus + Grafana

```python
# Add metrics endpoint
from prometheus_client import Counter, Histogram, generate_latest

tasks_total = Counter('tasks_total', 'Total tasks processed')
task_duration = Histogram('task_duration_seconds', 'Task processing time')

@celery.task
def process_document_task(doc_id, file_path):
    with task_duration.time():
        # ... process document ...
        tasks_total.inc()

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## 6. Cost Estimation

### Cloud Infrastructure (AWS example)

**For 500K documents:**

```
API Server:
- 1x t3.medium (2 vCPU, 4GB RAM)
- $0.0416/hour × 24 hours = $1.00/day

Celery Workers (50 workers):
- 50x t3.medium (2 vCPU, 4GB RAM each)
- $0.0416/hour × 50 × 24 hours = $49.92/day

Redis:
- 1x cache.r6g.large (2 vCPU, 13GB RAM)
- $0.126/hour × 24 hours = $3.02/day

PostgreSQL:
- 1x db.r6g.xlarge (4 vCPU, 32GB RAM)
- $0.42/hour × 24 hours = $10.08/day

OpenSearch:
- 1x r6g.xlarge.search (4 vCPU, 32GB RAM)
- $0.305/hour × 24 hours = $7.32/day

Total: ~$71/day for processing
```

**For 500K documents in 28 hours:** ~$83 total

**Scale down after:** $15/day (API + 5 workers)

---

## 7. Comparison

### Microservices vs Parallel Monolith

| Aspect | Microservices | Parallel Monolith |
|--------|---------------|-------------------|
| **Services** | 8+ | 1 + workers |
| **Infrastructure** | 11+ | 4 (API, Redis, DB, Search) |
| **Deployment complexity** | High | Low |
| **Code complexity** | High | Medium |
| **Debug difficulty** | Hard | Easy |
| **Throughput (50 workers)** | 432K docs/day | 432K docs/day ✅ |
| **Cost** | $140/day | $71/day |
| **Development speed** | Slow | Fast |
| **Ops complexity** | High | Medium |

**Winner for 500K documents: Parallel Monolith** 🏆

---

## Summary

**You can process 500K documents with:**

✅ **1 FastAPI application** (simple)
✅ **50 Celery workers** (parallel processing)
✅ **Redis** (task queue)
✅ **PostgreSQL + OpenSearch** (storage)

**Performance:**
- 50 workers = 432,000 docs/day
- 500K docs in ~28 hours
- Scale to 100 workers for 500K in 14 hours

**Benefits over microservices:**
- 2x cheaper
- 50% less infrastructure
- 5x faster development
- Easier debugging
- Same throughput!

**Next steps:**
1. Implement enhanced api/main.py with Celery
2. Set up Redis
3. Deploy 50 Celery workers
4. Run batch upload script
5. Process 500K documents! 🚀
