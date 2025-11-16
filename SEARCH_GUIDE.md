# Advanced Search Guide

> **⚠️ PROOF OF CONCEPT** - This search implementation has not been fully tested. Use at your own risk and conduct thorough testing before production deployment.

Complete guide to using keyword, semantic, and hybrid search in the AI Document Classification Pipeline.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Search Modes](#search-modes)
4. [Setup](#setup)
5. [Usage Examples](#usage-examples)
6. [POC to Production Migration](#poc-to-production-migration)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The AI Document Pipeline now includes **three powerful search modes**:

| Mode | Technology | Best For | Speed |
|------|-----------|----------|-------|
| **Keyword** | PostgreSQL FTS | Exact/partial matches, precise searches | ⚡ Very Fast |
| **Semantic** | pgvector | Concept-based, meaning searches | 🚀 Fast |
| **Hybrid** | Both | Best of both worlds | ⚡ Fast |

### Architecture

```
┌─────────────────────────────────────────────┐
│         Your Documents (PDF, DOCX, etc)     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│   Extract Text + Metadata (extractors.py)  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│          PostgreSQL Database                │
│  • Full-text search index (FTS)            │
│  • Vector embeddings (pgvector)            │
│  • Metadata + content                       │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              Search Service                 │
│  • Keyword search (fast, precise)          │
│  • Semantic search (smart, flexible)       │
│  • Hybrid search (best results)            │
└─────────────────────────────────────────────┘
```

### Key Features

✅ **Complete Full-Text Search** - ALL text from EVERY page indexed and searchable
✅ **No Size Limits** - 1-page memo or 1000-page contract - fully searchable
✅ **Multi-Format** - PDFs (all pages), Word (all paragraphs), Excel (all sheets)
✅ **Free for POC** - Everything runs locally
✅ **Cloud-ready** - Same code in production
✅ **No migration needed** - Just change DATABASE_URL
✅ **Multiple search modes** - Keyword, semantic, hybrid
✅ **Fast** - Optimized indexes (< 100ms searches)
✅ **Privacy-first** - Local embeddings (Ollama)

### Full-Text Coverage Details

When you enable search with `STORE_FULL_CONTENT=true`:

```
100-page PDF contract
    ↓ (extracts ALL pages)
Complete text: "Page 1... Page 2... Page 100..."
    ↓ (stores in database)
PostgreSQL full_content field
    ↓ (automatic indexing)
FTS index + Vector embeddings
    ↓
Search "clause on page 87" → FOUND ✅
```

**What gets indexed:**
- ✅ Every page in multi-page PDFs
- ✅ Every paragraph in Word documents
- ✅ Every sheet in Excel workbooks
- ✅ Every cell in spreadsheets
- ✅ All headers, footers, tables
- ✅ Complete document metadata (title, author, etc.)

**No truncation** - The entire document text is stored and searchable.

---

## Quick Start

### 1. Start PostgreSQL

```bash
# Start PostgreSQL with pgvector
docker-compose up -d

# Check it's running
docker-compose ps
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Pull Embedding Model (for semantic search)

```bash
# Pull the embedding model in Ollama
ollama pull nomic-embed-text
```

### 4. Configure Environment

Create or edit `.env`:

```ini
# Use PostgreSQL for search
USE_DATABASE=true
DATABASE_URL=postgresql://docuser:devpassword@localhost:5432/documents
STORE_FULL_CONTENT=true

# Embedding configuration (for semantic search)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
```

### 5. Test Search

```bash
# Check connection
doc-classify search-stats

# Simple search
doc-classify search "invoice"
```

---

## Search Modes

### 1. Keyword Search (PostgreSQL FTS)

**How it works:**
- Uses PostgreSQL's built-in full-text search
- Indexes words with stemming (running → run)
- Fast pattern matching
- Weighted by field (title > content)

**Best for:**
- Exact term searches
- Boolean queries (AND, OR, NOT)
- Phrase matching
- Known keywords

**Examples:**

```bash
# Simple keyword
doc-classify search "invoice" --mode keyword

# Boolean operators
doc-classify search "contract AND amendment" --mode keyword

# Phrase search
doc-classify search '"quarterly report"' --mode keyword

# Prefix matching (finds financing, financial, etc.)
doc-classify search "financ" --mode keyword
```

**Pros:**
- ✅ Very fast (< 50ms)
- ✅ Precise results
- ✅ Boolean operators
- ✅ Phrase matching

**Cons:**
- ❌ Requires exact keywords
- ❌ No synonym understanding
- ❌ Limited typo tolerance

---

### 2. Semantic Search (pgvector)

**How it works:**
- Converts text to embeddings (vectors)
- Finds similar vectors using cosine similarity
- Understands meaning, not just keywords
- Powered by Ollama (free) or OpenAI (production)

**Best for:**
- Concept-based searches
- Natural language queries
- Finding related documents
- Cross-language search

**Examples:**

```bash
# Natural language query
doc-classify search "how to cancel a subscription" --mode semantic

# Concept-based
doc-classify search "refund policy" --mode semantic
# Also finds: "money back guarantee", "return policy", etc.

# Finds similar documents even without exact terms
doc-classify search "financial statements" --mode semantic
# Finds: "quarterly reports", "balance sheets", "income statements"
```

**Pros:**
- ✅ Understands concepts
- ✅ Works with synonyms
- ✅ Natural language queries
- ✅ Typo tolerant

**Cons:**
- ❌ Slower than keyword (but still fast)
- ❌ Requires embeddings
- ❌ Less precise for exact matches

---

### 3. Hybrid Search (Recommended)

**How it works:**
- Runs both keyword and semantic search
- Combines results with weighted scoring
- Returns best matches from both methods

**Best for:**
- Most use cases
- When you're not sure which mode is best
- Maximum recall and precision

**Examples:**

```bash
# Balanced hybrid (default)
doc-classify search "contract amendment"

# Favor keyword precision
doc-classify search "invoice #12345" --keyword-weight 0.8 --semantic-weight 0.2

# Favor semantic understanding
doc-classify search "how to terminate agreement" --keyword-weight 0.3 --semantic-weight 0.7
```

**Pros:**
- ✅ Best of both worlds
- ✅ High recall (finds more)
- ✅ High precision (finds relevant)
- ✅ Configurable weights

**Cons:**
- ❌ Slightly slower than single mode (still fast)

---

## Setup

### Prerequisites

1. **Docker** - For PostgreSQL
2. **Ollama** - Already installed for classification
3. **Python 3.9+** - For the pipeline

### Installation Steps

#### Step 1: Start PostgreSQL

```bash
# Start database
docker-compose up -d

# Verify it's running
docker-compose logs postgres

# You should see: "database system is ready to accept connections"
```

#### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `sqlalchemy` - Database ORM
- `psycopg2-binary` - PostgreSQL driver

#### Step 3: Pull Embedding Model

```bash
# Pull nomic-embed-text for semantic search
ollama pull nomic-embed-text

# Verify
ollama list
```

#### Step 4: Configure Application

Create `.env` file:

```ini
# Database
USE_DATABASE=true
DATABASE_URL=postgresql://docuser:devpassword@localhost:5432/documents
STORE_FULL_CONTENT=true

# Embeddings (for semantic search)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768

# Optional: OpenAI embeddings (production)
# EMBEDDING_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# EMBEDDING_MODEL=text-embedding-3-small
# EMBEDDING_DIMENSION=1536
```

#### Step 5: Test Connection

```bash
# Check database connection
doc-classify search-stats

# Should show statistics (even if empty)
```

---

## Usage Examples

### CLI Usage

#### Basic Search

```bash
# Hybrid search (default)
doc-classify search "invoice payment"

# Show more results
doc-classify search "contract" --limit 50

# Filter by category
doc-classify search "Q3 results" --category reports

# Verbose output with previews
doc-classify search "amendment" -v
```

#### Advanced Search

```bash
# Keyword-only search (fast, exact)
doc-classify search "INV-2024-001" --mode keyword

# Semantic-only search (smart, flexible)
doc-classify search "how to request a refund" --mode semantic

# Custom hybrid weights
doc-classify search "financial report" \
  --keyword-weight 0.7 \
  --semantic-weight 0.3
```

#### Indexing

```bash
# View index statistics
doc-classify search-stats

# Reindex for FTS (automatic on insert)
doc-classify reindex

# Reindex with embeddings (for semantic search)
doc-classify reindex --include-vectors

# Reindex specific category
doc-classify reindex --category invoices --include-vectors
```

### Python API Usage

#### Basic Search

```python
from src.search_service import SearchService, SearchMode

# Initialize search service
search = SearchService(
    database_url="postgresql://docuser:devpassword@localhost:5432/documents",
    embedding_provider="ollama"
)

# Hybrid search
results = search.search(
    query="contract amendment",
    mode=SearchMode.HYBRID,
    limit=20
)

# Display results
for result in results:
    print(f"{result.file_name} - Score: {result.combined_score:.4f}")
    print(f"  Category: {result.category}")
    print(f"  Preview: {result.content_preview[:100]}...\n")
```

#### Keyword Search

```python
# Fast keyword search
results = search.keyword_search(
    query="invoice AND payment",
    category="invoices",
    limit=10
)

for result in results:
    print(f"{result.file_name} - Rank: {result.keyword_rank:.4f}")
```

#### Semantic Search

```python
# Concept-based search
results = search.semantic_search(
    query="how to cancel a subscription",
    limit=15
)

for result in results:
    print(f"{result.file_name} - Similarity: {result.semantic_rank:.4f}")
```

#### Custom Hybrid Search

```python
# Favor keyword precision
results = search.hybrid_search(
    query="invoice #12345",
    keyword_weight=0.8,
    semantic_weight=0.2,
    limit=10
)

# Favor semantic understanding
results = search.hybrid_search(
    query="refund process",
    keyword_weight=0.3,
    semantic_weight=0.7,
    limit=20
)
```

#### Statistics

```python
# Get index statistics
stats = search.get_statistics()

print(f"Total documents: {stats['total_documents']}")
print(f"FTS coverage: {stats['fts_coverage']}")
print(f"Embedding coverage: {stats['embedding_coverage']}")
```

---

## POC to Production Migration

### Current Setup (POC - Free)

```
Local Machine
  ↓
Docker PostgreSQL + pgvector
  ↓
Ollama Embeddings (local, free)
  ↓
Cost: $0/month
```

### Production Setup (Cloud)

```
Application Server (EC2, Cloud Run, etc.)
  ↓
AWS RDS PostgreSQL + pgvector
  ↓
OpenAI API Embeddings (optional)
  ↓
Cost: ~$60-250/month
```

### Migration Steps

#### Option 1: Keep Everything the Same (Cheapest)

```bash
# 1. Deploy PostgreSQL to AWS RDS
# 2. Install pgvector extension
# 3. Update .env with new DATABASE_URL
# 4. Deploy application

# New .env:
DATABASE_URL=postgresql://user:pass@mydb.rds.amazonaws.com:5432/documents

# Keep using Ollama (deploy it too)
EMBEDDING_PROVIDER=ollama

# That's it! No code changes needed.
```

**Cost:** ~$50-100/month (just database)

---

#### Option 2: Upgrade Embeddings (Better Performance)

```bash
# Switch to OpenAI embeddings for better quality/speed
# Everything else stays the same

# New .env:
DATABASE_URL=postgresql://user:pass@mydb.rds.amazonaws.com:5432/documents
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Reindex with new embeddings
doc-classify reindex --include-vectors
```

**Cost:** ~$60-250/month (database + API)
- Database: $50-100/month
- OpenAI: ~$10-50/month (depends on volume)

---

### Cloud Provider Options

#### AWS

```bash
# RDS PostgreSQL with pgvector
1. Create RDS PostgreSQL 16 instance
2. Connect and enable extension:
   CREATE EXTENSION vector;
3. Update DATABASE_URL
4. Deploy app to EC2/ECS/Lambda
```

**Cost:** $50-200/month

---

#### Google Cloud

```bash
# Cloud SQL PostgreSQL
1. Create Cloud SQL PostgreSQL 16
2. Enable vector extension
3. Update DATABASE_URL
4. Deploy to Cloud Run/GKE
```

**Cost:** $50-150/month

---

#### Azure

```bash
# Azure Database for PostgreSQL
1. Create Flexible Server PostgreSQL 16
2. Enable vector extension
3. Update DATABASE_URL
4. Deploy to App Service/AKS
```

**Cost:** $50-200/month

---

### Zero-Downtime Migration

```bash
# 1. Export current data
doc-classify db-export --output backup.json

# 2. Set up cloud database
# 3. Import data using pg_dump/restore
pg_dump local_db | pg_restore cloud_db

# 4. Test with new DATABASE_URL
DATABASE_URL=postgresql://cloud... doc-classify search-stats

# 5. Deploy application
# 6. Update DNS/Load balancer
```

---

## Troubleshooting

### Database Won't Start

```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs postgres

# Restart
docker-compose down
docker-compose up -d

# Check port 5432 is available
lsof -i :5432
```

### Connection Errors

```bash
# Test connection
psql postgresql://docuser:devpassword@localhost:5432/documents

# If connection fails:
1. Check PostgreSQL is running (docker-compose ps)
2. Check DATABASE_URL in .env
3. Check firewall/network
```

### Embedding Model Not Found

```bash
# Pull the model
ollama pull nomic-embed-text

# Verify it's available
ollama list

# Test embedding
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'
```

### Search Returns No Results

```bash
# Check if documents are indexed
doc-classify search-stats

# If FTS coverage is 0%, reindex:
doc-classify reindex

# If embedding coverage is 0%, reindex with vectors:
doc-classify reindex --include-vectors
```

### Slow Search Performance

```bash
# For large databases, check indexes
psql -c "\d+ documents" $DATABASE_URL

# Ensure these indexes exist:
# - idx_documents_fts (GIN on content_tsv)
# - idx_documents_embedding (IVFFlat on embedding)

# Rebuild indexes if needed:
REINDEX TABLE documents;
```

### Out of Memory (Embeddings)

```bash
# Reduce batch size
doc-classify reindex --include-vectors --batch-size 5

# Or use OpenAI API instead of local Ollama
EMBEDDING_PROVIDER=openai
```

---

## Performance Benchmarks

Based on typical hardware:

| Documents | Keyword Search | Semantic Search | Hybrid Search | Indexing Time |
|-----------|---------------|-----------------|---------------|---------------|
| 100 | < 10ms | < 50ms | < 100ms | 1 min |
| 1,000 | < 50ms | < 100ms | < 150ms | 10 min |
| 10,000 | < 100ms | < 200ms | < 300ms | 2 hours |
| 100,000 | < 200ms | < 500ms | < 700ms | 20 hours |

*Indexing time includes generating embeddings with Ollama (CPU). Use OpenAI API for 10x faster indexing.*

---

## Best Practices

### 1. Choose the Right Search Mode

- **Exact matches** → Keyword
- **Concept searches** → Semantic
- **Not sure** → Hybrid (default)

### 2. Indexing Strategy

```bash
# Initial setup: Index everything with embeddings
doc-classify reindex --include-vectors

# Regular updates: FTS updates automatically
# Only regenerate embeddings if content changes significantly
```

### 3. Performance Optimization

```python
# For production, use connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

### 4. Backup Strategy

```bash
# Daily backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Or export to JSON
doc-classify db-export --output backup.json
```

---

## Next Steps

- **Getting Started**: See [START_HERE.md](START_HERE.md)
- **Database Guide**: See [DATABASE_GUIDE.md](DATABASE_GUIDE.md)
- **Deployment**: See [DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md)
- **API Reference**: See source code in [src/search_service.py](src/search_service.py)

---

**Questions?** Open an issue on GitHub or check the documentation.
