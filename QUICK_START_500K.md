# Quick Start: Process 500K Documents

**Goal:** Process 500,000 documents in 28 hours using parallel workers.

---

## 1. Install & Start (5 minutes)

```bash
# Install
pip install -r requirements.txt

# Start Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Start API
uvicorn api.main:app --port 8000

# Start Workers (10 workers)
celery -A api.tasks worker --loglevel=info --autoscale=10,1
```

## 2. Upload 500K Documents

```bash
python scripts/batch_upload_500k.py /path/to/docs --batch-size 1000 --monitor
```

## 3. Scale to 50 Workers (for 28-hour processing)

Deploy 5 servers with 10 workers each, or use Kubernetes.

**Done!** See [PARALLEL_PROCESSING_SUMMARY.md](PARALLEL_PROCESSING_SUMMARY.md) for full details.
