# Cloud Migration Guide

> **⚠️ PROOF OF CONCEPT** - This system has not been fully tested. Before deploying to production:
> - Conduct extensive testing with your specific use cases
> - Perform security audits
> - Test data backup and recovery procedures
> - Validate search accuracy and performance at scale
> - Use at your own risk

Complete guide for migrating from local POC to cloud production deployment.

## Overview

This guide covers migrating your AI Document Pipeline with search capabilities from a local proof-of-concept to a production cloud environment with **zero code changes**.

### Migration Strategy

```
┌─────────────────────────────────────┐
│  POC (Local - Free)                 │
│  • Docker PostgreSQL + pgvector     │
│  • Ollama embeddings (local)        │
│  • Your laptop/workstation          │
│  • Cost: $0/month                   │
└─────────────────────────────────────┘
              ↓
         Change 1 line
              ↓
┌─────────────────────────────────────┐
│  Production (Cloud)                 │
│  • AWS RDS / GCP Cloud SQL          │
│  • Same pgvector extension          │
│  • OpenAI API (optional)            │
│  • Cost: $60-250/month              │
└─────────────────────────────────────┘
```

**Key Benefit:** Same Python code, same database schema, same SQL queries.

---

## Table of Contents

1. [Pre-Migration Checklist](#pre-migration-checklist)
2. [AWS Deployment](#aws-deployment)
3. [Google Cloud Deployment](#google-cloud-deployment)
4. [Azure Deployment](#azure-deployment)
5. [Data Migration](#data-migration)
6. [Embedding Strategy](#embedding-strategy)
7. [Cost Optimization](#cost-optimization)
8. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Pre-Migration Checklist

### 1. Export Your Data

```bash
# Export current database
docker-compose exec postgres pg_dump -U docuser documents > backup.sql

# Or use JSON export
doc-classify db-export --output pre_migration_backup.json

# Store securely (S3, Google Drive, etc.)
```

### 2. Document Your Configuration

```bash
# Save current .env
cp .env .env.local.backup

# Document custom settings
cat .env
```

### 3. Test Locally

```bash
# Ensure everything works
doc-classify search-stats
doc-classify search "test"
doc-classify reindex --include-vectors
```

### 4. Calculate Costs

| Component | POC | Production (Min) | Production (Recommended) |
|-----------|-----|------------------|--------------------------|
| Database | $0 | $50/month | $100/month |
| Compute | $0 | $20/month | $50/month |
| Embeddings | $0 | $0 (Ollama) | $10-50/month (OpenAI) |
| Storage | $0 | $5/month | $10/month |
| **Total** | **$0** | **~$75/month** | **~$200/month** |

---

## AWS Deployment

### Step 1: Create RDS PostgreSQL Instance

```bash
# Via AWS CLI
aws rds create-db-instance \
  --db-instance-identifier doc-pipeline-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.1 \
  --master-username docadmin \
  --master-user-password YOUR_SECURE_PASSWORD \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxx \
  --publicly-accessible
```

**Or via AWS Console:**
1. Go to RDS → Create database
2. Engine: PostgreSQL 16.x
3. Template: Free tier (for testing) or Production
4. DB instance: `db.t3.small` (recommended min)
5. Storage: 20 GB (auto-scaling enabled)
6. Public access: Yes (for initial setup)

**Cost:** $15-50/month (Free tier for 12 months)

### Step 2: Enable pgvector Extension

```bash
# Connect to your RDS instance
psql -h doc-pipeline-db.xxxxx.us-east-1.rds.amazonaws.com \
     -U docadmin \
     -d postgres

# Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

# Verify
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Step 3: Run Migration SQL

```bash
# Upload migration script
psql -h YOUR_RDS_ENDPOINT \
     -U docadmin \
     -d postgres \
     -f migrations/001_init_search.sql
```

### Step 4: Migrate Data

```bash
# Import from local backup
psql -h YOUR_RDS_ENDPOINT \
     -U docadmin \
     -d postgres \
     < backup.sql

# Or restore using pg_restore
pg_restore -h YOUR_RDS_ENDPOINT \
           -U docadmin \
           -d postgres \
           backup.dump
```

### Step 5: Deploy Application

#### Option A: EC2

```bash
# Launch EC2 instance (t3.small recommended)
# Install dependencies
sudo apt update
sudo apt install python3.11 python3-pip git

# Clone your repo
git clone YOUR_REPO
cd AI_Document_Pipeline

# Install requirements
pip install -r requirements.txt

# Configure
cat > .env << EOF
DATABASE_URL=postgresql://docadmin:PASSWORD@YOUR_RDS_ENDPOINT:5432/postgres
USE_DATABASE=true
STORE_FULL_CONTENT=true
EMBEDDING_PROVIDER=ollama
EOF

# Test
doc-classify search-stats

# Run as service (systemd)
sudo nano /etc/systemd/system/doc-pipeline.service
```

**Cost:** $10-30/month

#### Option B: ECS (Docker)

```dockerfile
# Dockerfile already provided
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["doc-classify", "classify", "/input"]
```

```bash
# Build and push
docker build -t doc-pipeline .
docker tag doc-pipeline:latest YOUR_ECR_REPO:latest
docker push YOUR_ECR_REPO:latest

# Deploy to ECS
# Use Fargate for serverless
```

**Cost:** $20-100/month

#### Option C: Lambda (for API)

```python
# lambda_handler.py
from src.search_service import SearchService
import json

def lambda_handler(event, context):
    search = SearchService(
        database_url=os.environ['DATABASE_URL']
    )

    query = event.get('query', '')
    results = search.search(query, limit=10)

    return {
        'statusCode': 200,
        'body': json.dumps([r.to_dict() for r in results])
    }
```

**Cost:** $5-20/month

### Step 6: Update Environment Variables

```bash
# Production .env
DATABASE_URL=postgresql://docadmin:PASSWORD@doc-pipeline-db.xxxxx.rds.amazonaws.com:5432/postgres
USE_DATABASE=true
STORE_FULL_CONTENT=true

# Optional: Use OpenAI for better performance
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

### Step 7: Test Production

```bash
# Test connection
doc-classify search-stats

# Test search
doc-classify search "invoice"

# Reindex if needed
doc-classify reindex --include-vectors
```

---

## Google Cloud Deployment

### Step 1: Create Cloud SQL PostgreSQL

```bash
# Via gcloud CLI
gcloud sql instances create doc-pipeline-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_SECURE_PASSWORD

# Create database
gcloud sql databases create documents --instance=doc-pipeline-db

# Get connection string
gcloud sql instances describe doc-pipeline-db
```

**Cost:** $10-50/month

### Step 2: Enable pgvector

```bash
# Connect via Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432

# In another terminal
psql -h localhost -U postgres

# Enable extension
CREATE EXTENSION IF NOT EXISTS vector;
```

### Step 3: Deploy to Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/doc-pipeline

# Deploy
gcloud run deploy doc-pipeline \
  --image gcr.io/PROJECT_ID/doc-pipeline \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=postgresql://...

# Enable Cloud SQL connection
gcloud run services update doc-pipeline \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE
```

**Cost:** $20-80/month

---

## Azure Deployment

### Step 1: Create Azure Database for PostgreSQL

```bash
# Via Azure CLI
az postgres flexible-server create \
  --name doc-pipeline-db \
  --resource-group myResourceGroup \
  --location eastus \
  --admin-user docadmin \
  --admin-password YOUR_SECURE_PASSWORD \
  --sku-name Standard_B1ms \
  --version 16
```

**Cost:** $15-60/month

### Step 2: Enable pgvector

```bash
# Connect to database
psql -h doc-pipeline-db.postgres.database.azure.com \
     -U docadmin \
     -d postgres

# Enable extension
CREATE EXTENSION IF NOT EXISTS vector;
```

### Step 3: Deploy to App Service

```bash
# Create App Service
az appservice plan create \
  --name doc-pipeline-plan \
  --resource-group myResourceGroup \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --name doc-pipeline \
  --resource-group myResourceGroup \
  --plan doc-pipeline-plan \
  --runtime "PYTHON:3.11"

# Configure
az webapp config appsettings set \
  --name doc-pipeline \
  --resource-group myResourceGroup \
  --settings DATABASE_URL="postgresql://..."
```

**Cost:** $20-100/month

---

## Data Migration

### Option 1: Direct Dump/Restore (Recommended)

```bash
# From local
pg_dump -h localhost -U docuser documents > local_backup.sql

# To cloud
psql -h CLOUD_ENDPOINT -U admin postgres < local_backup.sql
```

### Option 2: CSV Export/Import

```bash
# Export from local
psql -h localhost -U docuser documents \
  -c "COPY documents TO STDOUT CSV HEADER" > documents.csv

# Import to cloud
psql -h CLOUD_ENDPOINT -U admin postgres \
  -c "COPY documents FROM STDIN CSV HEADER" < documents.csv
```

### Option 3: JSON Export (Fallback)

```bash
# Export via CLI
doc-classify db-export --output backup.json

# Then manually import or write custom script
python import_from_json.py backup.json
```

### Migration Verification

```bash
# Check row counts match
# Local:
psql -h localhost -U docuser -c "SELECT COUNT(*) FROM documents"

# Cloud:
psql -h CLOUD_ENDPOINT -U admin -c "SELECT COUNT(*) FROM documents"

# Verify embeddings
psql -h CLOUD_ENDPOINT -U admin -c \
  "SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL"
```

---

## Embedding Strategy

### Option 1: Keep Ollama (Free)

**Pros:**
- $0 additional cost
- Privacy (no external API)
- Same quality as POC

**Cons:**
- Need to deploy Ollama server
- Slower embedding generation
- Requires more compute resources

**Setup:**
```bash
# Deploy Ollama alongside your app
docker run -d -v ollama:/root/.ollama -p 11434:11434 ollama/ollama
ollama pull nomic-embed-text

# Keep same config
EMBEDDING_PROVIDER=ollama
OLLAMA_HOST=http://ollama-service:11434
```

**Best for:** Small-medium workloads, budget-conscious

---

### Option 2: Switch to OpenAI (Recommended)

**Pros:**
- 10x faster embedding generation
- Better quality
- No deployment overhead
- Scalable

**Cons:**
- ~$0.13 per 1M tokens
- External dependency
- Requires API key

**Setup:**
```bash
# Update .env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Reindex (one-time)
doc-classify reindex --include-vectors
```

**Cost:** ~$10-50/month depending on volume

**Best for:** Production, high-volume, better quality

---

### Option 3: Hybrid (Smart)

```python
# Use OpenAI for new documents (fast)
# Keep existing Ollama embeddings (no reindexing needed)

def get_embedding_service():
    if os.getenv('FORCE_REINDEX'):
        return OpenAIEmbeddingService()
    else:
        # Check if document has embedding
        # If yes, skip
        # If no, use OpenAI
        return OpenAIEmbeddingService()
```

**Best for:** Gradual migration

---

## Cost Optimization

### 1. Right-Size Database

```bash
# Start small
db.t3.micro  # $15/month - 100-1000 docs
db.t3.small  # $30/month - 1000-10000 docs
db.t3.medium # $60/month - 10000-100000 docs

# Use Reserved Instances for 40% savings
# 1-year: 40% off
# 3-year: 60% off
```

### 2. Optimize Storage

```bash
# Enable auto-scaling
MinStorageSize=20GB
MaxStorageSize=100GB

# Regular VACUUM
psql -c "VACUUM ANALYZE documents"

# Archive old documents
DELETE FROM documents WHERE processed_date < NOW() - INTERVAL '2 years';
```

### 3. Use Spot/Preemptible Instances

```bash
# AWS Spot: 70% savings
# GCP Preemptible: 80% savings
# Azure Spot: 70% savings

# Good for non-critical workloads
```

### 4. Optimize Embeddings

```bash
# Batch processing
doc-classify reindex --include-vectors --batch-size 100

# Only reindex when needed
# FTS updates automatically, embeddings don't change unless content changes

# Use smaller embeddings (trade quality for cost)
EMBEDDING_MODEL=text-embedding-3-small  # 1536 dim, cheaper
# vs
EMBEDDING_MODEL=text-embedding-3-large  # 3072 dim, expensive
```

### 5. Implement Caching

```python
# Add Redis for search caching
from redis import Redis
cache = Redis()

def cached_search(query):
    cached = cache.get(f"search:{query}")
    if cached:
        return json.loads(cached)

    results = search_service.search(query)
    cache.setex(f"search:{query}", 3600, json.dumps(results))
    return results
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Endpoint for health monitoring
@app.route('/health')
def health():
    try:
        search = SearchService(database_url=DB_URL)
        search.test_connection()
        return {'status': 'healthy'}, 200
    except:
        return {'status': 'unhealthy'}, 500
```

### Logging

```python
# Configure structured logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)

# Send to CloudWatch / Stackdriver / App Insights
```

### Metrics to Monitor

```bash
# Database
- Connection count
- Query latency
- Storage usage
- CPU/Memory usage

# Search
- Search latency (p50, p95, p99)
- Search volume
- Error rate
- Cache hit rate

# Embeddings
- Embedding generation time
- API costs
- Queue depth
```

### Alerts

```yaml
# Example CloudWatch alarm
SearchLatencyHigh:
  Metric: SearchLatency
  Threshold: 1000ms
  Period: 5 minutes
  Action: SNS notification

DatabaseCPUHigh:
  Metric: CPUUtilization
  Threshold: 80%
  Period: 5 minutes
  Action: Auto-scale

EmbeddingCostHigh:
  Metric: OpenAICost
  Threshold: $100/day
  Period: 1 day
  Action: Email admin
```

### Backup Strategy

```bash
# Automated daily backups
0 2 * * * pg_dump $DATABASE_URL | gzip > backup_$(date +\%Y\%m\%d).sql.gz

# Retention
- Daily: 7 days
- Weekly: 4 weeks
- Monthly: 12 months

# Test restores monthly
```

### Updates & Maintenance

```bash
# Database maintenance window
# Sunday 2-4 AM UTC

# Tasks:
1. VACUUM ANALYZE
2. Reindex if needed
3. Update statistics
4. Check slow queries
5. Review storage usage

# Automated script
#!/bin/bash
psql $DATABASE_URL << EOF
VACUUM ANALYZE documents;
REINDEX TABLE documents;
ANALYZE documents;
EOF
```

---

## Rollback Plan

If something goes wrong:

```bash
# 1. Keep old environment running during migration

# 2. Test thoroughly before DNS switch

# 3. If issues, revert DNS
# Point DATABASE_URL back to old instance

# 4. Investigate and fix

# 5. Retry migration when ready
```

---

## Success Checklist

- [ ] Database created and accessible
- [ ] pgvector extension enabled
- [ ] Migration SQL executed successfully
- [ ] Data migrated and verified
- [ ] Application deployed and running
- [ ] Search working (keyword, semantic, hybrid)
- [ ] Embeddings generated (if using semantic search)
- [ ] Environment variables configured
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backups automated
- [ ] Costs within budget
- [ ] Documentation updated

---

## Support Resources

- **AWS:** https://docs.aws.amazon.com/rds/
- **GCP:** https://cloud.google.com/sql/docs
- **Azure:** https://docs.microsoft.com/azure/postgresql/
- **pgvector:** https://github.com/pgvector/pgvector
- **SQLAlchemy:** https://docs.sqlalchemy.org/

---

## Estimated Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Setup cloud database | 1-2 hours | Provision + configure |
| Enable pgvector | 30 mins | Simple SQL |
| Migrate data | 1-4 hours | Depends on size |
| Deploy application | 2-4 hours | First time |
| Test & verify | 2-4 hours | Thorough testing |
| Reindex with embeddings | 1-8 hours | Depends on volume |
| Monitoring setup | 1-2 hours | CloudWatch/etc |
| **Total** | **1-2 days** | For first deployment |

**Subsequent deploys:** < 1 hour with automation

---

## Next Steps

1. Choose cloud provider
2. Estimate costs
3. Create accounts/credentials
4. Follow provider-specific guide above
5. Test thoroughly
6. Monitor and optimize

**Questions?** Check [SEARCH_GUIDE.md](SEARCH_GUIDE.md) or open an issue.
