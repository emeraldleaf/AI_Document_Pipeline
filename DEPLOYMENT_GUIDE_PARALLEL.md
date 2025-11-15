# Deployment Guide: Parallel Processing for 500K Documents

Complete guide to deploying the enhanced monolith with Celery workers for processing 500K documents.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI API Server                        │
│                   (api/main.py - Port 8000)                  │
│  - Upload endpoints                                          │
│  - Search endpoints                                          │
│  - Monitoring endpoints                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Publishes to Redis
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Redis (Port 6379)                       │
│  - Task queue (broker)                                       │
│  - Result backend                                            │
│  - Caching                                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                   ↓                   ↓
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Celery Worker │  │ Celery Worker │  │ Celery Worker │
│    Pod 1-10   │  │   Pod 11-25   │  │   Pod 26-50   │
└───────────────┘  └───────────────┘  └───────────────┘
        ... 50 workers total for 500K documents ...
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌──────────────────┐                  ┌──────────────────┐
│   PostgreSQL     │                  │   OpenSearch     │
│    (Port 5432)   │                  │    (Port 9200)   │
│  - Metadata      │                  │  - Full-text     │
│  - Status        │                  │  - Vectors       │
└──────────────────┘                  └──────────────────┘
```

---

## Quick Start (Local Development)

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start Redis (using Docker)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Start PostgreSQL (if not already running)
docker run -d --name postgres \
  -e POSTGRES_DB=documents \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=devpassword \
  -p 5432:5432 \
  postgres:15-alpine
```

### 2. Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
DATABASE_URL=postgresql://postgres:devpassword@localhost:5432/documents
```

### 3. Start Services

```bash
# Terminal 1: Start API
uvicorn api.main:app --reload --port 8000

# Terminal 2: Start Celery workers (10 workers, 4 concurrent tasks each = 40 parallel tasks)
celery -A api.tasks worker --loglevel=info --concurrency=4 --autoscale=10,1

# Terminal 3 (Optional): Start Flower (monitoring dashboard)
celery -A api.tasks flower --port=5555
```

### 4. Test Upload

```bash
# Upload single document
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test.pdf"

# Upload batch
python scripts/batch_upload_500k.py /path/to/documents --batch-size 100
```

---

## Production Deployment

### Option 1: Single Server (Small Scale)

**For:** Up to 50K documents, limited budget

**Resources:**
- 1 server (16 vCPU, 32GB RAM)
- 1 API process
- 20 Celery workers

```bash
# Install supervisor for process management
sudo apt install supervisor

# /etc/supervisor/conf.d/api.conf
[program:api]
command=/path/to/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/path/to/app
autostart=true
autorestart=true
stderr_logfile=/var/log/api.err.log
stdout_logfile=/var/log/api.out.log

# /etc/supervisor/conf.d/celery.conf
[program:celery]
command=/path/to/venv/bin/celery -A api.tasks worker --loglevel=info --concurrency=4 --autoscale=20,5
directory=/path/to/app
autostart=true
autorestart=true
stderr_logfile=/var/log/celery.err.log
stdout_logfile=/var/log/celery.out.log

# Start services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

---

### Option 2: Multi-Server (500K Documents)

**For:** 500K documents in 24-48 hours

**Infrastructure:**

```
1x API Server (4 vCPU, 8GB RAM)
  - FastAPI API
  - Nginx reverse proxy
  - $50/month

1x Redis Server (2 vCPU, 4GB RAM)
  - Redis 7
  - $25/month

5x Worker Servers (4 vCPU, 8GB RAM each)
  - 10 Celery workers each = 50 total
  - $50/month × 5 = $250/month

1x PostgreSQL Server (8 vCPU, 16GB RAM)
  - Database
  - $100/month

1x OpenSearch Server (8 vCPU, 16GB RAM)
  - Search index
  - $100/month

Total: ~$525/month (scale down to $200/month after processing)
```

**Deployment:**

```bash
# API Server
scp -r . user@api-server:/app
ssh user@api-server
cd /app
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Worker Servers (repeat on worker-1 through worker-5)
scp -r . user@worker-1:/app
ssh user@worker-1
cd /app
pip install -r requirements.txt
celery -A api.tasks worker --loglevel=info --concurrency=4 --autoscale=10,2 --hostname=worker1@%h
```

---

### Option 3: Kubernetes (Cloud Native)

**For:** Enterprise scale, auto-scaling, high availability

**Files:**

`k8s/api-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: your-registry/document-pipeline:latest
        command: ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: CELERY_BROKER_URL
          value: redis://redis-service:6379/0
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

`k8s/worker-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-workers
spec:
  replicas: 50  # For 500K documents
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
        image: your-registry/document-pipeline:latest
        command:
          - celery
          - -A
          - api.tasks
          - worker
          - --loglevel=info
          - --concurrency=4
          - --max-tasks-per-child=100
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: CELERY_BROKER_URL
          value: redis://redis-service:6379/0
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

`k8s/redis-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

**Deploy:**

```bash
# Create namespace
kubectl create namespace document-pipeline

# Create secrets
kubectl create secret generic app-secrets \
  --from-literal=database-url=postgresql://... \
  -n document-pipeline

# Deploy
kubectl apply -f k8s/ -n document-pipeline

# Scale workers for 500K job
kubectl scale deployment celery-workers --replicas=50 -n document-pipeline

# Monitor
kubectl get pods -n document-pipeline
kubectl logs -f deployment/celery-workers -n document-pipeline

# Scale down after processing
kubectl scale deployment celery-workers --replicas=10 -n document-pipeline
```

---

## Monitoring

### Flower Dashboard

```bash
# Start Flower
celery -A api.tasks flower --port=5555

# Access at http://localhost:5555
```

**Metrics:**
- Active workers
- Task success/failure rates
- Processing speed
- Queue length
- Worker utilization

### API Monitoring

```bash
# Worker stats
curl http://localhost:8000/api/workers

# Batch status
curl http://localhost:8000/api/batch-status/{batch_id}

# Task status
curl http://localhost:8000/api/task-status/{task_id}
```

### Prometheus + Grafana

`prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'celery'
    static_configs:
      - targets: ['localhost:5555']  # Flower metrics

  - job_name: 'api'
    static_configs:
      - targets: ['localhost:8000']  # API metrics
```

---

## Performance Tuning

### Redis Optimization

```bash
# redis.conf
maxmemory 8gb
maxmemory-policy allkeys-lru
save ""  # Disable persistence for speed
appendonly no
tcp-backlog 511
```

### PostgreSQL Optimization

```sql
-- postgresql.conf
max_connections = 200
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 64MB
checkpoint_completion_target = 0.9
```

### Celery Worker Optimization

```bash
# For CPU-bound tasks (Ollama classification/extraction)
celery -A api.tasks worker \
  --pool=prefork \
  --concurrency=4 \
  --max-tasks-per-child=50

# For I/O-bound tasks
celery -A api.tasks worker \
  --pool=gevent \
  --concurrency=100
```

---

## Scaling Guide

### Calculate Workers Needed

```python
# Formula:
workers_needed = (total_documents × seconds_per_document) / (target_hours × 3600)

# Example for 500K documents:
# - 10 seconds per document
# - Target: 28 hours
workers_needed = (500000 × 10) / (28 × 3600) = 49.6 ≈ 50 workers
```

### Cost Optimization

```bash
# Development (10K docs/day): 5-10 workers
# - Cost: $100-150/month

# Production (100K docs/day): 20-30 workers
# - Cost: $300-400/month

# Burst (500K in 1 day): 100 workers
# - Spin up for 1 day, then scale down
# - Cost: $50 for 1 day burst
```

---

## Troubleshooting

### Workers Not Processing

```bash
# Check Redis connection
redis-cli ping

# Check worker status
celery -A api.tasks inspect active
celery -A api.tasks inspect stats

# Check logs
tail -f /var/log/celery.err.log
```

### Slow Processing

```bash
# Check worker concurrency
celery -A api.tasks inspect stats

# Increase workers
celery -A api.tasks worker --autoscale=20,5

# Check database performance
EXPLAIN ANALYZE SELECT * FROM documents WHERE processing_status = 'queued';
```

### Out of Memory

```bash
# Reduce worker concurrency
celery -A api.tasks worker --concurrency=2

# Restart workers after N tasks
celery -A api.tasks worker --max-tasks-per-child=50

# Monitor memory
watch -n 1 free -h
```

---

## Backup & Recovery

### Backup Strategy

```bash
# PostgreSQL backup
pg_dump -h localhost -U postgres documents > backup.sql

# Redis backup (if persistence enabled)
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb backup/

# Upload files backup
tar -czf uploads-backup.tar.gz uploads/
```

### Recovery

```bash
# Restore PostgreSQL
psql -h localhost -U postgres documents < backup.sql

# Reprocess failed documents
python scripts/reprocess_failed.py
```

---

## Summary

**For 500K documents:**

1. **Deploy 50 Celery workers** (5 servers × 10 workers each)
2. **Upload in batches** of 1000 using `batch_upload_500k.py`
3. **Monitor progress** with Flower dashboard
4. **Process in ~28 hours** (432K docs/day throughput)
5. **Scale down** to 10 workers after completion

**Total cost:** ~$525/month (or ~$50 for 2-day burst)

**Much simpler than microservices, same performance!** 🚀
