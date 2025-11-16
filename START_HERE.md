# AI Document Pipeline - Start Here

AI-powered document classification and processing pipeline with parallel processing capabilities.

---

## Quick Start

### 1. Prerequisites

```bash
# Install Docker Desktop
brew install --cask docker

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Services

```bash
# Start PostgreSQL
docker-compose up -d

# Start Redis (for parallel processing)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Pull embedding model
ollama pull nomic-embed-text
```

### 3. Configure

```bash
cp .env.example .env
```

### 4. Start API

```bash
uvicorn api.main:app --port 8000
```

Visit: http://localhost:8000

---

## What Can You Do?

### Process Documents
- Single document upload via web UI
- Batch upload for high-volume processing
- Automatic classification and metadata extraction

### Search Documents
- Full-text search
- Semantic search with embeddings
- Hybrid search combining both approaches

### Scale Processing
- Process up to 500K documents
- Parallel processing with Celery workers
- Real-time monitoring and progress tracking

---

## Documentation

### Essential Reading
- [README.md](README.md) - Complete project documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Project overview

### High-Volume Processing
- [PARALLEL_PROCESSING_IMPLEMENTATION.md](PARALLEL_PROCESSING_IMPLEMENTATION.md) - Process 500K documents
- [DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md) - Production deployment
- [SCALING_GUIDE.md](SCALING_GUIDE.md) - Scaling strategies

### Search & Indexing
- [SEARCH_GUIDE.md](SEARCH_GUIDE.md) - Search documentation
- [SETUP_SEARCH.md](SETUP_SEARCH.md) - Search setup
- [OPENSEARCH_SETUP_GUIDE.md](OPENSEARCH_SETUP_GUIDE.md) - OpenSearch integration

### Testing & Development
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing strategy
- [END_TO_END_TESTING_GUIDE.md](END_TO_END_TESTING_GUIDE.md) - E2E testing
- [BENCHMARKING_GUIDE.md](BENCHMARKING_GUIDE.md) - Performance testing

### All Documentation
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Complete index

---

## Common Tasks

### Classify Documents
```bash
# Via API
curl -X POST http://localhost:8000/api/upload \
  -F "file=@document.pdf"
```

### Batch Upload
```bash
python scripts/batch_upload_500k.py /path/to/documents
```

### Search Documents
```bash
# Full-text search
doc-classify search "invoice"

# Semantic search
doc-classify search "payment terms" --mode semantic

# Hybrid search
doc-classify search "contract" --mode hybrid
```

### Monitor Workers
```bash
# Start workers
celery -A api.tasks worker --loglevel=info

# Monitor status
curl http://localhost:8000/api/workers
```

---

## Architecture

**Monolith + Parallel Workers**
- FastAPI application serving web UI and API
- PostgreSQL for document storage
- Redis for task queuing
- Celery workers for parallel processing
- Ollama for local embeddings

**Processing Capacity**
- Single worker: ~10 documents/minute
- 50 workers: 432,000 documents/day
- Scales horizontally with worker count

---

## Next Steps

1. **Process your first document** - Upload via http://localhost:8000
2. **Scale up** - Read [PARALLEL_PROCESSING_IMPLEMENTATION.md](PARALLEL_PROCESSING_IMPLEMENTATION.md)
3. **Deploy to production** - Read [DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md)

---

Questions? Check [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for complete documentation.
