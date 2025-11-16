# High-Throughput Scaling Guide

## Processing 500,000 Documents in 1 Week

This guide explains how to scale the AI Document Pipeline to process 500,000 documents (5 million pages) within one week.

---

## Table of Contents

1. [Performance Requirements](#performance-requirements)
2. [Scaling Strategies](#scaling-strategies)
3. [Quick Start](#quick-start)
4. [Parallel Processing](#parallel-processing)
5. [Async Batch Processing](#async-batch-processing)
6. [Distributed Processing with Celery](#distributed-processing-with-celery)
7. [Performance Benchmarking](#performance-benchmarking)
8. [Cloud Deployment](#cloud-deployment)
9. [Cost Estimates](#cost-estimates)
10. [Troubleshooting](#troubleshooting)

---

## Performance Requirements

### Target Metrics
- **Total Documents**: 500,000
- **Total Pages**: 5,000,000 (avg 10 pages per document)
- **Timeframe**: 7 days = 168 hours
- **Required Throughput**: **826 documents/hour** (13.8/min, 0.23/sec)

### Current Performance (Single-Threaded)
- **Throughput**: ~180-360 documents/hour
- **Time for 500K**: 58-116 days
- **Bottleneck**: Sequential processing, Ollama inference time

### Performance Gap
- **Multiplier Needed**: 3x minimum, **10-20x recommended** for buffer

---

## Scaling Strategies

### 1. Parallel Processing (5-10x speedup)
Use multiprocessing to leverage all CPU cores on a single machine.

**Best for:**
- Single machine deployment
- 5,000-50,000 documents
- Quick wins without infrastructure changes

### 2. Async Batch Processing (2-3x additional speedup)
Use asyncio for concurrent I/O operations and batch database inserts.

**Best for:**
- Combined with parallel processing
- I/O-heavy workloads
- Reducing database bottlenecks

### 3. Distributed Processing (10-50x speedup)
Use Celery + Redis to distribute work across multiple machines.

**Best for:**
- 100,000+ documents
- Horizontal scaling
- Production deployments

---

## Quick Start

### Option 1: Parallel Processing (Easiest)

```bash
# Install the pipeline
pip install -e .

# Process documents with all CPU cores
doc-classify classify-parallel documents/input

# Specify number of workers
doc-classify classify-parallel documents/input -w 8

# With database and export
doc-classify classify-parallel documents/input \
  --use-database \
  --export \
  -o results/
```

### Option 2: Distributed Processing (Production)

```bash
# Start all services (Redis, PostgreSQL, Ollama, 4 workers)
docker-compose -f docker-compose-workers.yml up -d

# Scale workers dynamically
docker-compose -f docker-compose-workers.yml up -d --scale worker1=8

# Monitor with Flower dashboard
open http://localhost:5555

# Submit documents for processing
python scripts/submit_distributed_batch.py documents/input
```

---

## Parallel Processing

### Architecture
- Uses Python `multiprocessing` module
- Worker processes = CPU cores
- Shared-nothing architecture
- Each worker: extract → classify → store

### Implementation

```python
from src.parallel_processor import ParallelDocumentProcessor
from pathlib import Path

# Create processor
processor = ParallelDocumentProcessor(
    num_workers=8,  # Number of CPU cores
    use_database=True,
    chunk_size=10  # Documents per worker chunk
)

# Process directory
stats = processor.process_directory(
    Path("documents/input"),
    recursive=True,
    include_reasoning=False
)

# Print performance
processor.print_summary()

# Export results
processor.export_results(Path("results/parallel_results.json"))
```

### Performance Characteristics
- **Speedup**: 5-10x (limited by CPU cores and Ollama throughput)
- **Memory**: ~500MB per worker
- **Ideal for**: Up to 50,000 documents on single machine

### Configuration Tips

```python
# CPU-bound workloads
num_workers = os.cpu_count()  # Use all cores

# Memory-constrained
num_workers = os.cpu_count() // 2  # Use half the cores

# I/O-bound (Ollama bottleneck)
num_workers = os.cpu_count() * 2  # Oversubscribe slightly
```

---

## Async Batch Processing

### Architecture
- Uses Python `asyncio` for concurrency
- Non-blocking I/O operations
- Batch database inserts (100 docs at a time)
- Semaphore for concurrency control

### Implementation

```python
import asyncio
from src.async_batch_processor import AsyncBatchProcessor
from pathlib import Path

async def main():
    # Create processor
    processor = AsyncBatchProcessor(
        max_concurrent=50,  # Concurrent async operations
        batch_size=100,  # Database batch size
        use_database=True,
        deduplicate=True  # Skip already processed docs
    )

    # Process directory
    stats = await processor.process_directory_async(
        Path("documents/input"),
        recursive=True,
        include_reasoning=False
    )

    # Export results
    processor.export_results(Path("results/async_results.json"))

    print(f"Processed {stats.successful} documents in {stats.total_processing_time:.2f}s")
    print(f"Throughput: {stats.documents_per_second:.2f} docs/sec")

# Run
asyncio.run(main())
```

### Performance Characteristics
- **Speedup**: 2-3x on top of parallel processing
- **Memory**: Lower than parallel (shared memory)
- **Ideal for**: I/O-heavy workloads, database bottlenecks

### Configuration Tips

```python
# High concurrency (Ollama can handle it)
max_concurrent = 100
batch_size = 200

# Conservative (limited resources)
max_concurrent = 20
batch_size = 50

# Balance (recommended)
max_concurrent = 50
batch_size = 100
```

---

## Distributed Processing with Celery

### Architecture
```
┌─────────────┐
│   Client    │  Submit 500K documents
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Redis     │  Message queue
└──────┬──────┘
       │
       ├──────────┬──────────┬──────────┐
       ▼          ▼          ▼          ▼
   Worker 1   Worker 2   Worker 3   Worker 4  (Each with 8 processes)
       │          │          │          │
       └──────────┴──────────┴──────────┘
                    │
                    ▼
             ┌─────────────┐
             │ PostgreSQL  │
             └─────────────┘
```

### Setup

#### 1. Install Dependencies

```bash
pip install celery redis flower
```

#### 2. Start Infrastructure

```bash
# Option A: Docker Compose (Recommended)
docker-compose -f docker-compose-workers.yml up -d

# Option B: Manual
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Start PostgreSQL (if not running)
docker-compose up -d postgres

# Start Ollama (if not running)
ollama serve
```

#### 3. Start Celery Workers

```bash
# Terminal 1: Worker 1
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=worker1@%h

# Terminal 2: Worker 2
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=worker2@%h

# Terminal 3: Worker 3
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=worker3@%h

# Terminal 4: Worker 4
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=worker4@%h
```

#### 4. Monitor with Flower

```bash
celery -A src.celery_tasks flower --port=5555
```

Open http://localhost:5555 to view the dashboard.

### Submit Documents for Processing

```python
from src.celery_tasks import CeleryDistributedProcessor
from pathlib import Path

# Create processor
processor = CeleryDistributedProcessor(
    use_database=True,
    batch_size=1000  # Submit 1000 docs at a time
)

# Submit directory for processing
batch_id = processor.submit_directory(
    Path("documents/input"),
    recursive=True,
    include_reasoning=False
)

print(f"Submitted batch: {batch_id}")

# Wait for completion with progress tracking
stats = processor.wait_for_completion(
    batch_id,
    poll_interval=5.0,
    show_progress=True
)

print(f"Processing complete!")
print(f"Successful: {stats['successful']}")
print(f"Failed: {stats['failed']}")
```

### Check Progress

```python
# Check progress without blocking
progress = processor.check_progress(batch_id)
print(f"Progress: {progress['progress_percent']:.1f}%")
print(f"Completed: {progress['completed']}/{progress['total_tasks']}")

# Get results (blocks until complete)
results = processor.get_results(batch_id)
```

### Performance Characteristics
- **Speedup**: 10-50x (scales linearly with workers)
- **Throughput**: 3,000-6,000 documents/hour with 4 worker machines
- **Scalability**: Add more workers to scale further

### Scaling Workers

```bash
# Docker Compose: Scale to 8 workers
docker-compose -f docker-compose-workers.yml up -d --scale worker1=8

# Or start workers on separate machines
# Machine 1:
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=worker1@%h

# Machine 2:
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=worker2@%h

# Machine 3:
celery -A src.celery_tasks worker --loglevel=info --concurrency=8 --hostname=worker3@%h
```

---

## Performance Benchmarking

### Run Benchmarks

```bash
# Create test dataset (100 sample documents)
python scripts/create_test_dataset.py --count 100 --output test_docs/

# Run performance benchmark
python tests/test_performance_benchmark.py test_docs/ \
  --operations end_to_end \
  --output-dir benchmark_results/

# View results
cat benchmark_results/benchmark_results_*.json
```

### Interpret Results

```
PERFORMANCE BENCHMARK RESULTS
================================================================================

END_TO_END OPERATION:
  Total Files: 100
  Success Rate: 98/100 (98.0%)
  Average Processing Time: 12.34s
  Median Processing Time: 11.89s
  Operations per Second: 8.11
  Total Throughput: 16.22 MB/s
  Peak Memory Usage: 2048.5 MB
  Average CPU Usage: 85.3%

Estimated time for 500K documents: 17.1 hours
```

### Performance Targets

| Configuration | Docs/Hour | Time for 500K | Cost (1 week) |
|--------------|-----------|---------------|---------------|
| Single-threaded | 180-360 | 58-116 days | $0 |
| Parallel (8 cores) | 1,500-2,000 | 10-14 days | $0 |
| Async + Parallel | 3,000-4,000 | 5-7 days | $0 |
| Distributed (4 workers) | 6,000-8,000 | 2.5-3.5 days | $500-1,000 |
| Distributed (10 workers) | 15,000-20,000 | 1-1.5 days | $1,500-2,500 |

---

## Cloud Deployment

### AWS Deployment (Recommended)

```bash
# 1. Launch EC2 instances (c6i.4xlarge recommended)
# 5-10 instances for workers

# 2. Deploy PostgreSQL RDS
aws rds create-db-instance \
  --db-instance-identifier doc-pipeline-db \
  --db-instance-class db.r6g.xlarge \
  --engine postgres \
  --engine-version 16.1 \
  --allocated-storage 100

# 3. Deploy Redis ElastiCache
aws elasticache create-cache-cluster \
  --cache-cluster-id doc-pipeline-redis \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-nodes 1

# 4. Deploy workers via Docker/ECS
# See DEPLOYMENT_GUIDE_PARALLEL.md for details
```

### Cost Estimate (7 days)

| Service | Configuration | Cost |
|---------|--------------|------|
| EC2 Workers (10x c6i.4xlarge) | On-demand | $1,400 |
| RDS PostgreSQL (db.r6g.xlarge) | 7 days | $400 |
| ElastiCache Redis (r6g.large) | 7 days | $150 |
| S3 Storage | 100GB | $2 |
| Data Transfer | 500GB | $45 |
| **Total** | | **~$2,000** |

**Cost Optimization:**
- Use Spot Instances: Save 70% (~$600 total)
- Use smaller workers: Save 50% (~$1,000 total)
- Turn off nights/weekends: Save 40% (~$1,200 total)

---

## Cost Estimates

### Single Machine (High-Spec Laptop/Workstation)

```
Hardware: $0 (using existing machine)
Processing Time: 5-7 days (async + parallel)
Total Cost: $0
```

**Pros:** Free, simple setup
**Cons:** Slow, ties up machine for a week

---

### Cloud Deployment (Minimal)

```
5x c6i.4xlarge EC2 Spot Instances: $50/day × 7 = $350
RDS db.t3.large: $35/day × 7 = $245
ElastiCache t3.medium: $10/day × 7 = $70
Storage & Transfer: $50
Total: ~$715 for 1 week
Throughput: 10,000-15,000 docs/hour
Time to Complete: 2-3 days
```

**Pros:** Fast, cost-effective
**Cons:** Requires AWS setup

---

### Cloud Deployment (Recommended)

```
10x c6i.4xlarge EC2 Spot Instances: $100/day × 7 = $700
RDS db.r6g.xlarge: $60/day × 7 = $420
ElastiCache r6g.large: $20/day × 7 = $140
Storage & Transfer: $100
Total: ~$1,360 for 1 week
Throughput: 20,000-30,000 docs/hour
Time to Complete: 1-2 days
```

**Pros:** Fast, reliable, buffer for issues
**Cons:** Higher cost

---

### Cloud Deployment (Premium)

```
20x c6i.8xlarge EC2 Instances: $300/day × 7 = $2,100
RDS db.r6g.2xlarge: $120/day × 7 = $840
ElastiCache r6g.xlarge: $40/day × 7 = $280
OpenAI API (instead of Ollama): $500
Storage & Transfer: $200
Total: ~$3,920 for 1 week
Throughput: 50,000-70,000 docs/hour
Time to Complete: < 1 day
```

**Pros:** Extremely fast, enterprise-grade
**Cons:** Expensive

---

## Troubleshooting

### Problem: Slow Processing (< 500 docs/hour)

**Solutions:**
1. Check Ollama is using GPU: `ollama ps`
2. Use smaller/faster model: `llama3.2:1b` instead of `llama3.2:3b`
3. Increase worker count
4. Check database connection pooling
5. Profile with performance benchmark tool

---

### Problem: Out of Memory

**Solutions:**
1. Reduce `num_workers` or `max_concurrent`
2. Reduce `chunk_size` or `batch_size`
3. Use smaller Ollama model
4. Increase machine RAM
5. Enable swap space

---

### Problem: Database Connection Errors

**Solutions:**
1. Increase PostgreSQL `max_connections` (default: 100)
2. Use connection pooling (PgBouncer)
3. Reduce concurrent database operations
4. Check database URL is correct
5. Verify network connectivity

---

### Problem: Celery Workers Not Picking Up Tasks

**Solutions:**
1. Check Redis is running: `redis-cli ping`
2. Verify workers are connected: Check Flower dashboard
3. Check `CELERY_BROKER_URL` environment variable
4. Restart workers: `docker-compose restart worker1`
5. Check task serialization (JSON only)

---

### Problem: Ollama Service Unavailable

**Solutions:**
1. Check Ollama is running: `ollama list`
2. Verify `OLLAMA_HOST` environment variable
3. Check model is pulled: `ollama pull llama3.2:3b`
4. Restart Ollama service
5. Check network connectivity between workers and Ollama

---

## Performance Tuning Checklist

- [ ] Use parallel or distributed processing (not single-threaded)
- [ ] Enable database connection pooling
- [ ] Use batch database inserts (100-200 at a time)
- [ ] Enable deduplication to skip already processed docs
- [ ] Use smaller/faster Ollama model if acceptable
- [ ] Deploy Ollama with GPU acceleration
- [ ] Scale workers horizontally (5-10 machines)
- [ ] Monitor with Flower dashboard
- [ ] Use Spot/Preemptible instances for cost savings
- [ ] Benchmark performance before full run

---

## Next Steps

1. **Test with small batch** (100 documents) to verify setup
2. **Run performance benchmark** to measure throughput
3. **Calculate required workers** based on benchmark results
4. **Deploy infrastructure** (local or cloud)
5. **Process full dataset** with monitoring
6. **Verify results** in database/export files

---

## Support

For issues or questions:
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review [ARCHITECTURE.md](ARCHITECTURE.md)
- Open a GitHub issue
- Check Celery/Redis documentation

---

**Built for scale. Optimized for throughput. Ready for production.**
