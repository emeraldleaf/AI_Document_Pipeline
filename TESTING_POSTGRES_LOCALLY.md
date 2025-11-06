# Testing PostgreSQL Locally

Quick guide to test your PostgreSQL database and search functionality in your local development environment.

## Prerequisites

1. **Docker** - For running PostgreSQL
2. **Ollama** - For AI classification and embeddings
3. **Python 3.9+** - With dependencies installed

## Quick Start (5 minutes)

### Option 1: Automated Test Script

```bash
# Run the comprehensive test script
./test_postgres.sh
```

This script will:
- ✅ Check all prerequisites
- ✅ Start PostgreSQL with pgvector
- ✅ Create test documents
- ✅ Test classification
- ✅ Test keyword search
- ✅ Generate embeddings
- ✅ Test semantic search
- ✅ Test hybrid search

### Option 2: Manual Testing

If you prefer to test step-by-step:

#### 1. Install Docker Desktop

```bash
brew install --cask docker
# Then open Docker Desktop from Applications
```

#### 2. Start PostgreSQL

```bash
# Start PostgreSQL with pgvector extension
docker-compose up -d

# Verify it's running
docker-compose ps

# Should show: doc_pipeline_postgres ... Up
```

#### 3. Check Ollama

```bash
# Start Ollama if not running
brew services start ollama

# Pull required models
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Verify
ollama list
```

#### 4. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Key settings for PostgreSQL:
# USE_DATABASE=true
# DATABASE_URL=postgresql://docuser:devpassword@localhost:5432/documents
# STORE_FULL_CONTENT=true
# EMBEDDING_PROVIDER=ollama
# EMBEDDING_MODEL=nomic-embed-text
```

#### 5. Create Test Documents

```bash
mkdir -p documents/input

# Create a test invoice
cat > documents/input/test_invoice.txt << 'EOF'
INVOICE #2024-001
Date: October 27, 2024
Customer: Acme Corp
Amount: $5,000.00
Payment terms: Net 30
EOF

# Create a test contract
cat > documents/input/test_contract.txt << 'EOF'
SOFTWARE LICENSE AGREEMENT
This Agreement is entered into as of October 27, 2024.
License Fee: $10,000 annually
Term: One year
EOF

# Create a test report
cat > documents/input/test_report.txt << 'EOF'
Q3 2024 QUARTERLY REPORT
Revenue: $2.5M (up 15% YoY)
Net Profit: 18%
Key achievements and future outlook.
EOF
```

#### 6. Classify Documents (Stores in PostgreSQL)

```bash
# Classify and store in database
doc-classify classify documents/input

# You should see each document being classified
# and stored in PostgreSQL
```

#### 7. Test Database Connection

```bash
# View database statistics
doc-classify search-stats

# Should show:
# - Total Documents: 3
# - Documents with FTS: 3
# - FTS Coverage: 100%
```

#### 8. Test Keyword Search

```bash
# Search for "invoice"
doc-classify search "invoice" --mode keyword

# Search for specific amount
doc-classify search "5000" --mode keyword

# Search with verbose output
doc-classify search "agreement" --mode keyword -v
```

#### 9. Generate Embeddings for Semantic Search

```bash
# Generate vector embeddings (takes ~1 sec per document)
doc-classify reindex --include-vectors

# Check embedding coverage
doc-classify search-stats
# Should now show: Embedding Coverage: 100%
```

#### 10. Test Semantic Search

```bash
# Semantic search understands concepts
doc-classify search "payment document" --mode semantic
# Finds invoices even without exact keyword match

# Natural language query
doc-classify search "financial agreement" --mode semantic
# Finds contracts and invoices

# Try a question
doc-classify search "how much revenue" --mode semantic
# Finds reports with revenue information
```

#### 11. Test Hybrid Search (Best Results)

```bash
# Hybrid combines keyword + semantic
doc-classify search "quarterly revenue" --mode hybrid

# Custom weights (70% keyword, 30% semantic)
doc-classify search "license fee" \
  --keyword-weight 0.7 \
  --semantic-weight 0.3
```

## Testing Database Directly

### Connect to PostgreSQL

```bash
# Using psql (if installed)
psql postgresql://docuser:devpassword@localhost:5432/documents

# Or via Docker
docker-compose exec postgres psql -U docuser -d documents
```

### Run SQL Queries

```sql
-- See all documents
SELECT id, file_name, category, processed_date
FROM documents
ORDER BY processed_date DESC;

-- Search using PostgreSQL FTS
SELECT file_name,
       ts_rank(content_tsv, to_tsquery('invoice')) as rank
FROM documents
WHERE content_tsv @@ to_tsquery('invoice')
ORDER BY rank DESC;

-- Check embedding coverage
SELECT
  COUNT(*) as total_docs,
  COUNT(embedding) as docs_with_embeddings,
  ROUND(100.0 * COUNT(embedding) / COUNT(*), 2) as coverage_percent
FROM documents;

-- View pgvector extension
\dx pgvector
```

## Verifying Search Performance

### Test Search Speed

```bash
# Keyword search (should be < 50ms)
time doc-classify search "invoice" --mode keyword

# Semantic search (should be < 100ms)
time doc-classify search "payment" --mode semantic

# Hybrid search (should be < 150ms)
time doc-classify search "quarterly" --mode hybrid
```

### Test with Many Documents

```bash
# Add more test documents
for i in {1..50}; do
  cat > "documents/input/doc_$i.txt" << EOF
Document $i
Created: $(date)
Random content: $(uuidgen)
Category: Test
Amount: $$(( RANDOM % 10000 ))
EOF
done

# Classify all
doc-classify classify documents/input

# Generate embeddings
doc-classify reindex --include-vectors

# Test search performance with 50+ documents
doc-classify search "document" --mode hybrid --limit 10
```

## Database Management

### View Statistics

```bash
# Search statistics
doc-classify search-stats

# Database statistics
doc-classify db-stats
```

### Export Data

```bash
# Export all documents to JSON
doc-classify db-export --output backup.json

# Export specific category
doc-classify db-search --category invoices --limit 100
```

### Clear Database

```bash
# Stop PostgreSQL
docker-compose down

# Remove data volume (WARNING: deletes all data!)
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Troubleshooting

### PostgreSQL won't start

```bash
# Check if port 5432 is in use
lsof -i :5432

# If another postgres is running:
brew services stop postgresql@14  # or your version

# Restart
docker-compose down
docker-compose up -d
```

### Connection refused errors

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Check if container is running
docker ps | grep postgres

# Restart if needed
docker-compose restart postgres
```

### No search results

```bash
# Check if documents are in database
doc-classify search-stats

# If 0 documents, classify some
doc-classify classify documents/input

# Reindex if needed
doc-classify reindex --include-vectors
```

### Slow embedding generation

```bash
# Normal: ~1 second per document on CPU
# For 100 documents: ~2 minutes

# Speed up options:
# 1. Use GPU if available (requires CUDA setup)
# 2. Use OpenAI API (faster but costs money)
#    Edit .env:
#      EMBEDDING_PROVIDER=openai
#      OPENAI_API_KEY=sk-your-key
```

### pgvector extension not found

```bash
# The docker-compose.yml uses pgvector/pgvector:pg16
# which includes the extension

# Verify extension is installed
docker-compose exec postgres psql -U docuser -d documents \
  -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# If not installed, recreate container
docker-compose down -v
docker-compose up -d
```

## Performance Expectations

With local PostgreSQL on a typical development machine:

| Documents | Indexing Time | Keyword Search | Semantic Search | Hybrid Search |
|-----------|---------------|----------------|-----------------|---------------|
| 10        | 10 sec        | < 10ms         | < 20ms          | < 30ms        |
| 100       | 2 min         | < 20ms         | < 50ms          | < 70ms        |
| 1,000     | 20 min        | < 50ms         | < 100ms         | < 150ms       |

*Indexing time includes embedding generation with Ollama on CPU*

## What You're Testing

This local setup tests all the scalability features mentioned in ARCHITECTURE.md:

### Storage & Search
- ✅ PostgreSQL Database with FTS indexing
- ✅ pgvector integration (768-dimensional embeddings)
- ✅ Hybrid search (keyword + semantic ranking)
- ✅ Automatic FTS triggers and IVFFlat vector indexes

### Search Modes
- ✅ Keyword search (PostgreSQL FTS with BM25 ranking)
- ✅ Semantic search (pgvector cosine similarity)
- ✅ Hybrid search (weighted combination)

### Production Features
- ✅ Multi-page document support (all pages indexed)
- ✅ No content limits (1-page to 1000-page documents)
- ✅ Concurrent read operations
- ✅ Cloud-ready architecture (same code works in production)

## Next Steps

### 1. Add Real Documents

```bash
# Copy your documents
cp ~/Documents/invoices/* documents/input/
cp ~/Documents/contracts/* documents/input/

# Process them
doc-classify classify documents/input

# Generate embeddings
doc-classify reindex --include-vectors
```

### 2. Integrate into Your Application

```python
from src.search_service import SearchService, SearchMode

# Initialize
search = SearchService(
    database_url="postgresql://docuser:devpassword@localhost:5432/documents",
    embedding_provider="ollama"
)

# Search
results = search.search(
    query="your query",
    mode=SearchMode.HYBRID,
    limit=20
)
```

### 3. Deploy to Cloud

When ready for production:
1. Create cloud PostgreSQL database (AWS RDS, GCP Cloud SQL, etc.)
2. Enable pgvector extension
3. Update DATABASE_URL in .env
4. Deploy your application

See [CLOUD_MIGRATION.md](CLOUD_MIGRATION.md) for details.

## Cleanup

When done testing:

```bash
# Stop PostgreSQL
docker-compose down

# Remove data volume (optional)
docker-compose down -v

# Remove test documents
rm -rf documents/input/*
rm -rf documents/output/*
```

## References

- **Setup Guide**: [SETUP_SEARCH.md](SETUP_SEARCH.md)
- **Search Documentation**: [SEARCH_GUIDE.md](SEARCH_GUIDE.md)
- **Database Guide**: [DATABASE_GUIDE.md](DATABASE_GUIDE.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Cloud Migration**: [CLOUD_MIGRATION.md](CLOUD_MIGRATION.md)

---

**Ready to test!** Run `./test_postgres.sh` to get started.
