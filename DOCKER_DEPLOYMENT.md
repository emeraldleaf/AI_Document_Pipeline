# Docker Deployment Guide

Complete Docker containerization for the AI Document Pipeline with separate containers for each component.

## Architecture

The system runs in 5 separate Docker containers:

1. **postgres** - PostgreSQL 16 with pgvector extension
2. **redis** - Redis 7 for Celery task queue
3. **api** - FastAPI application server (Python 3.11)
4. **worker** - Celery workers for parallel processing (Python 3.11)
5. **frontend** - React/TypeScript UI with Nginx

All containers communicate over a dedicated Docker network and include health checks.

## Prerequisites

- Docker Desktop 4.0+ installed
- Ollama running on host machine (for local embeddings)
- 4GB+ RAM available for Docker
- 10GB+ disk space

## Quick Start

### 1. Start All Services

```bash
docker-compose up -d
```

This will:
- Build all Docker images (first time only)
- Start PostgreSQL with pgvector
- Start Redis
- Start API server on port 8000
- Start 1 Celery worker (4 concurrent tasks)
- Start frontend on port 80
- Run database migrations automatically

### 2. Verify Services

```bash
# Check all containers are running
docker-compose ps

# Check logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f frontend
```

### 3. Access the Application

- **Frontend**: http://localhost
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Service Details

### PostgreSQL Container

**Image**: `pgvector/pgvector:pg16`
**Port**: 5432
**Database**: documents
**User**: docuser
**Password**: devpassword (change for production!)

Includes:
- pgvector extension for embeddings
- Automatic schema initialization from migrations
- Persistent data volume

### Redis Container

**Image**: `redis:7-alpine`
**Port**: 6379

Includes:
- AOF persistence enabled
- Persistent data volume
- Health checks

### API Container

**Base Image**: `python:3.11-slim`
**Port**: 8000

Includes:
- All Python dependencies from requirements.txt
- Tesseract OCR for document processing
- Poppler utils for PDF handling
- Health check endpoint
- Auto-restart on failure

### Worker Container

**Base Image**: `python:3.11-slim`
**Concurrency**: 4 tasks per worker

Includes:
- Same dependencies as API container
- Celery worker with autoscaling
- Can be scaled horizontally

### Frontend Container

**Build**: Node 20 → Nginx Alpine
**Port**: 80

Includes:
- Multi-stage build (smaller image)
- Production Nginx configuration
- API proxy to backend
- Static asset caching
- Health checks

## Scaling

### Scale Workers Horizontally

```bash
# Scale to 5 workers
docker-compose up -d --scale worker=5

# Scale to 10 workers for high volume
docker-compose up -d --scale worker=10
```

Each worker runs 4 concurrent tasks, so:
- 5 workers = 20 concurrent tasks
- 10 workers = 40 concurrent tasks

### Adjust Worker Concurrency

Edit `docker-compose.yml`:

```yaml
worker:
  command: celery -A api.tasks worker --loglevel=info --concurrency=8
```

## Configuration

### Environment Variables

Edit environment variables in `docker-compose.yml`:

```yaml
environment:
  - DATABASE_URL=postgresql://docuser:devpassword@postgres:5432/documents
  - REDIS_URL=redis://redis:6379/0
  - USE_DATABASE=true
  - STORE_FULL_CONTENT=true
  - EMBEDDING_PROVIDER=ollama  # or 'openai'
  - EMBEDDING_MODEL=nomic-embed-text
  - OLLAMA_HOST=http://host.docker.internal:11434
  - OPENAI_API_KEY=sk-...  # if using OpenAI
```

### Use OpenAI for Embeddings

```yaml
environment:
  - EMBEDDING_PROVIDER=openai
  - OPENAI_API_KEY=sk-your-key-here
```

### Production Settings

For production, change:

1. **Database credentials**:
```yaml
environment:
  - DATABASE_URL=postgresql://secure_user:strong_password@postgres:5432/documents
postgres:
  environment:
    POSTGRES_USER: secure_user
    POSTGRES_PASSWORD: strong_password
```

2. **Expose only frontend**:
```yaml
# Remove port mappings for api, postgres, redis
# Only expose frontend:
frontend:
  ports:
    - "80:80"
```

3. **Enable SSL/TLS** (see nginx.conf)

## Volume Mounts

The following directories are mounted as volumes:

```yaml
volumes:
  - ./documents:/app/documents  # Document storage
  - ./logs:/app/logs            # Application logs
  - ./config:/app/config        # Configuration files
```

**Persistent data volumes:**
- `postgres_data` - PostgreSQL database
- `redis_data` - Redis persistence

## Common Commands

### Start Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d api

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (DELETE ALL DATA)
docker-compose down -v
```

### Rebuild Images

```bash
# Rebuild all images
docker-compose build

# Rebuild specific service
docker-compose build api

# Rebuild and start
docker-compose up -d --build
```

### Shell Access

```bash
# Access API container
docker-compose exec api bash

# Access worker container
docker-compose exec worker bash

# Access PostgreSQL
docker-compose exec postgres psql -U docuser -d documents
```

### Monitor Resources

```bash
# View resource usage
docker stats

# View container details
docker-compose ps -a
```

## Health Checks

All services include health checks:

```bash
# Check service health
docker-compose ps

# healthy - Service is running correctly
# unhealthy - Service failed health check
# starting - Service is still starting up
```

## Troubleshooting

### API container fails to start

Check Ollama connectivity:
```bash
# From your host
curl http://localhost:11434/api/tags

# From API container
docker-compose exec api curl http://host.docker.internal:11434/api/tags
```

### Worker not processing tasks

Check Redis connection:
```bash
docker-compose exec worker redis-cli -h redis ping
```

Check Celery status:
```bash
docker-compose logs worker
```

### Database migration issues

Manually run migrations:
```bash
docker-compose exec postgres psql -U docuser -d documents -f /docker-entrypoint-initdb.d/001_init_search.sql
```

### Frontend can't connect to API

Check API health:
```bash
curl http://localhost:8000/api/health
```

Check nginx configuration:
```bash
docker-compose exec frontend nginx -t
```

### Out of disk space

Clean up Docker:
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything (DANGEROUS)
docker system prune -a --volumes
```

## Production Deployment

For production deployment:

1. Use external PostgreSQL (AWS RDS, Google Cloud SQL)
2. Use external Redis (AWS ElastiCache, Google Memorystore)
3. Deploy to Kubernetes or ECS
4. Use environment variables for secrets
5. Enable HTTPS with Let's Encrypt
6. Set up monitoring (Prometheus, Grafana)
7. Configure log aggregation (ELK, CloudWatch)
8. Set up backups for PostgreSQL

See [DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md) for cloud deployment details.

## Performance Tips

1. **Scale workers based on load**:
   - Low volume: 1-2 workers
   - Medium volume: 5-10 workers
   - High volume: 20+ workers

2. **Adjust worker concurrency**:
   - CPU-bound tasks: concurrency = CPU cores
   - I/O-bound tasks: concurrency = 2-4x CPU cores

3. **Monitor memory usage**:
   - Each worker uses ~500MB-1GB RAM
   - API container uses ~1-2GB RAM
   - PostgreSQL uses based on data size

4. **Database tuning**:
   - Increase `shared_buffers` for large datasets
   - Enable query caching
   - Regular VACUUM operations

## Security Considerations

1. **Change default passwords**
2. **Use secrets management** (Docker secrets, Kubernetes secrets)
3. **Limit container privileges**
4. **Scan images for vulnerabilities**
5. **Keep images updated**
6. **Use private registry** for production
7. **Enable network policies**
8. **Implement rate limiting**

## Next Steps

- Test with sample documents: Upload via http://localhost
- Monitor worker performance: Check logs
- Scale workers: `docker-compose up --scale worker=5`
- Deploy to production: See deployment guide

---

**Questions?** See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for complete documentation.
