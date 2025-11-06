# Quick Start: Process 500K Documents in 1 Week

**Goal:** Process 500,000 documents (5 million pages) within 7 days.

---

## TL;DR - Fastest Path

### Option 1: Single Machine (Simplest)

```bash
# 1. Install dependencies
pip install -e .

# 2. Run parallel classification
doc-classify classify-parallel documents/input -w 8 --use-database --export -o results/

# Time: 5-7 days on decent machine (16+ cores)
# Cost: $0
```

### Option 2: Distributed Cloud (Fastest)

```bash
# 1. Start infrastructure
docker-compose -f docker-compose-workers.yml up -d

# 2. Submit batch
python scripts/submit_distributed_batch.py documents/input --wait

# 3. Monitor
open http://localhost:5555  # Flower dashboard

# Time: 1-3 days with 10 workers
# Cost: ~$1,500
```

---

## Step-by-Step Guide

### Prerequisites

```bash
# 1. Install Python dependencies
pip install -e .

# 2. Start Ollama (if not running)
ollama serve

# 3. Pull model (if needed)
ollama pull llama3.2:3b

# 4. Start PostgreSQL (optional, for database storage)
docker-compose up -d postgres
```

---

## Method 1: Local Parallel Processing

**Best for:** Small-medium datasets (< 50K docs), no cloud setup

```bash
# Simple command
doc-classify classify-parallel documents/input

# With all options
doc-classify classify-parallel documents/input \
  -w 8 \
  --chunk-size 10 \
  --use-database \
  --export \
  -o results/ \
  -v
```

**Expected Performance:**
- **8-core machine**: 1,500-2,000 docs/hour
- **16-core machine**: 3,000-4,000 docs/hour
- **Time for 500K**: 5-14 days depending on hardware

**Pros:**
- Simple setup
- Free
- No cloud dependencies

**Cons:**
- Slower
- Ties up your machine
- Limited by single machine resources

---

## Method 2: Distributed Processing (RECOMMENDED)

**Best for:** Large datasets (50K+ docs), production deployments

### Setup (One-Time)

```bash
# 1. Install distributed processing dependencies
pip install celery redis flower

# 2. Start infrastructure with Docker Compose
docker-compose -f docker-compose-workers.yml up -d

# This starts:
# - Redis (message broker)
# - PostgreSQL (database)
# - Ollama (LLM service)
# - 4 Celery workers (8 processes each = 32 total)
# - Flower (monitoring dashboard)

# 3. Verify workers are running
docker-compose -f docker-compose-workers.yml ps

# 4. Check Flower dashboard
open http://localhost:5555
```

### Process Documents

```bash
# Submit all documents in a directory
python scripts/submit_distributed_batch.py documents/input --wait

# Or submit without waiting
python scripts/submit_distributed_batch.py documents/input

# Save the batch ID that's printed!
```

### Monitor Progress

```bash
# Check progress once
python scripts/check_batch_progress.py <batch_id>

# Watch continuously (refreshes every 5s)
python scripts/check_batch_progress.py <batch_id> --watch

# Get final results (blocks until complete)
python scripts/check_batch_progress.py <batch_id> --get-results

# Or use Flower dashboard
open http://localhost:5555
```

### Scale Workers

```bash
# Add more workers dynamically
docker-compose -f docker-compose-workers.yml up -d --scale worker1=8

# Or start workers on separate machines
# Machine 1:
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=machine1

# Machine 2:
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=machine2
```

**Expected Performance:**
- **4 workers (32 processes)**: 6,000-8,000 docs/hour
- **10 workers (80 processes)**: 15,000-20,000 docs/hour
- **Time for 500K**: 1-3 days depending on worker count

**Pros:**
- Very fast
- Scales horizontally
- Production-ready
- Monitoring included

**Cons:**
- More complex setup
- Requires Redis
- May require cloud infrastructure for best performance

---

## Cloud Deployment (For Maximum Speed)

### AWS Quick Deploy

```bash
# 1. Launch EC2 instances
# 10x c6i.4xlarge (16 cores, 32GB RAM each)
# Use Spot instances for 70% cost savings

# 2. Deploy PostgreSQL RDS
# db.r6g.xlarge (16GB RAM)

# 3. Deploy ElastiCache Redis
# r6g.large

# 4. On each EC2 instance:
git clone <your-repo>
cd AI_Document_Pipeline
pip install -r requirements.txt

# Set environment variables
export REDIS_URL=redis://<elasticache-endpoint>:6379/0
export DATABASE_URL=postgresql://<rds-endpoint>:5432/documents
export OLLAMA_HOST=http://<ollama-instance>:11434

# Start worker
celery -A src.celery_tasks worker --loglevel=info --concurrency=8

# 5. Submit from your local machine
python scripts/submit_distributed_batch.py documents/input
```

**Expected Performance:**
- **10 EC2 workers**: 20,000-30,000 docs/hour
- **Time for 500K**: 17-25 hours (~1 day)
- **Cost**: ~$1,500 for 1 week (Spot instances)

See [SCALING_GUIDE.md](SCALING_GUIDE.md) for detailed cloud deployment instructions.

---

## Performance Testing

Before processing 500K documents, test with a small batch:

```bash
# 1. Create test dataset (100 docs)
python scripts/create_test_dataset.py --count 100 --output test_docs/

# 2. Run benchmark
python tests/test_performance_benchmark.py test_docs/ \
  --operations end_to_end \
  --output-dir benchmark_results/

# 3. Check results
cat benchmark_results/benchmark_results_*.json

# 4. Calculate time for 500K
# If you get 10 docs/sec, then 500K docs = 50,000 seconds = ~14 hours
```

---

## Optimization Tips

### 1. Use Faster Model

```bash
# Default model (balanced)
export OLLAMA_MODEL=llama3.2:3b

# Faster model (slightly lower accuracy)
export OLLAMA_MODEL=llama3.2:1b

# Slower but more accurate
export OLLAMA_MODEL=llama3.1:8b
```

### 2. Optimize Database

```bash
# Increase PostgreSQL max connections
# In postgresql.conf:
max_connections = 200

# Use connection pooling
pip install pgbouncer
```

### 3. Tune Concurrency

```python
# More concurrent operations (if Ollama can handle it)
processor = AsyncBatchProcessor(
    max_concurrent=100,  # Default: 50
    batch_size=200       # Default: 100
)

# More worker processes
doc-classify classify-parallel documents/input -w 16  # Default: CPU count
```

### 4. Enable Deduplication

```python
# Skip already processed documents
processor = AsyncBatchProcessor(
    deduplicate=True  # Checks database for existing docs
)
```

---

## Common Issues

### 1. "Ollama service not available"

```bash
# Start Ollama
ollama serve

# Check it's running
curl http://localhost:11434/api/tags
```

### 2. "Celery workers not picking up tasks"

```bash
# Check Redis is running
redis-cli ping

# Restart workers
docker-compose -f docker-compose-workers.yml restart worker1 worker2

# Check Flower dashboard
open http://localhost:5555
```

### 3. "Out of memory"

```bash
# Reduce concurrency
doc-classify classify-parallel documents/input -w 4  # Instead of 8

# Or increase Docker memory limit
# In Docker Desktop: Settings → Resources → Memory → 8GB+
```

### 4. Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Increase max connections
docker-compose exec postgres psql -U docuser -c "ALTER SYSTEM SET max_connections = 200;"
docker-compose restart postgres
```

---

## Monitoring

### Real-Time Monitoring

```bash
# Flower dashboard (for Celery)
open http://localhost:5555

# Watch batch progress
python scripts/check_batch_progress.py <batch_id> --watch

# Docker logs
docker-compose -f docker-compose-workers.yml logs -f worker1
```

### Check Results

```bash
# Via database
psql -U docuser -d documents -c "SELECT category, COUNT(*) FROM documents GROUP BY category;"

# Via export
doc-classify db-export --output results.json
```

---

## Estimated Costs

| Configuration | Hardware | Time | Cost |
|--------------|----------|------|------|
| **Local (8-core)** | Laptop/Desktop | 10-14 days | $0 |
| **Local (16-core)** | Workstation | 5-7 days | $0 |
| **Cloud Minimal (5 workers)** | EC2 Spot | 2-3 days | $700 |
| **Cloud Recommended (10 workers)** | EC2 Spot | 1-2 days | $1,400 |
| **Cloud Premium (20 workers)** | EC2 On-Demand | < 1 day | $3,900 |

---

## Decision Matrix

### Choose Local Parallel Processing if:
- ✅ You have a powerful machine (16+ cores)
- ✅ Budget is $0
- ✅ You can wait 5-7 days
- ✅ You want simple setup

### Choose Distributed Processing if:
- ✅ You need it done in 1-3 days
- ✅ You have access to multiple machines or cloud
- ✅ Budget is $500-2,000
- ✅ You want production-grade solution

---

## Next Steps

1. **Choose your method** (local vs distributed)
2. **Run performance test** with 100 documents
3. **Calculate estimated time** based on test results
4. **Provision infrastructure** if needed
5. **Process full dataset**
6. **Monitor progress** via dashboard or scripts
7. **Verify results** in database/exports

---

## Support

- **Full Documentation**: [SCALING_GUIDE.md](SCALING_GUIDE.md)
- **Architecture Details**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Cloud Migration**: [CLOUD_MIGRATION.md](CLOUD_MIGRATION.md)
- **Feature Overview**: [HIGH_THROUGHPUT_FEATURES.md](HIGH_THROUGHPUT_FEATURES.md)

---

**Ready to process half a million documents? You've got this! 🚀**
