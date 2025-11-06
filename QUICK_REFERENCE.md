# Quick Reference Card

## Setup (5 Minutes)

```bash
# 1. Start database
docker-compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull embedding model
ollama pull nomic-embed-text

# 4. Configure (copy .env.example to .env)
cp .env.example .env

# 5. Test
doc-classify search-stats
```

---

## Search Commands

```bash
# Hybrid search (default - best results)
doc-classify search "QUERY"

# Keyword search (fast, exact)
doc-classify search "QUERY" --mode keyword

# Semantic search (smart, flexible)
doc-classify search "QUERY" --mode semantic

# Filter by category
doc-classify search "QUERY" --category invoices

# Show more results
doc-classify search "QUERY" --limit 50

# Verbose output
doc-classify search "QUERY" -v

# Custom hybrid weights
doc-classify search "QUERY" \
  --keyword-weight 0.7 \
  --semantic-weight 0.3
```

---

## Indexing Commands

```bash
# View statistics
doc-classify search-stats

# Reindex FTS (automatic usually)
doc-classify reindex

# Generate embeddings for semantic search
doc-classify reindex --include-vectors

# Reindex specific category
doc-classify reindex --category invoices --include-vectors
```

---

## Python API

```python
from src.search_service import SearchService, SearchMode

# Initialize
search = SearchService(
    database_url="postgresql://docuser:devpassword@localhost:5432/documents"
)

# Search
results = search.search(
    query="invoice payment",
    mode=SearchMode.HYBRID,
    limit=20
)

# Display
for r in results:
    print(f"{r.file_name}: {r.combined_score:.4f}")
```

---

## Configuration

### POC (Free)
```ini
DATABASE_URL=postgresql://docuser:devpassword@localhost:5432/documents
USE_DATABASE=true
STORE_FULL_CONTENT=true
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
```

### Production (Cloud)
```ini
DATABASE_URL=postgresql://user:pass@your-rds.amazonaws.com:5432/documents
USE_DATABASE=true
STORE_FULL_CONTENT=true
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

---

## Search Modes Comparison

| Mode | Speed | Accuracy | Best For |
|------|-------|----------|----------|
| **keyword** | ⚡⚡⚡ Fast | Exact matches | Known terms |
| **semantic** | ⚡⚡ Fast | Concept matching | Natural language |
| **hybrid** | ⚡⚡ Fast | Best of both | General use |

---

## Common Queries

```bash
# Find all invoices
doc-classify search "invoice" --category invoices

# Natural language
doc-classify search "how to cancel subscription" --mode semantic

# Exact document
doc-classify search "INV-2024-001" --mode keyword

# Boolean search
doc-classify search "contract AND amendment" --mode keyword

# Phrase search
doc-classify search '"quarterly report"' --mode keyword

# Fuzzy concept
doc-classify search "refund policy" --mode semantic
```

---

## Troubleshooting

```bash
# Database not running
docker-compose up -d

# Check connection
doc-classify search-stats

# View logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres

# Check embeddings
ollama list

# Test search
doc-classify search "test" -v
```

---

## Docker Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f postgres

# Restart
docker-compose restart

# Status
docker-compose ps

# Shell access
docker-compose exec postgres psql -U docuser -d documents
```

---

## Database Commands

```bash
# Connect to database
psql postgresql://docuser:devpassword@localhost:5432/documents

# Check tables
\dt

# Count documents
SELECT COUNT(*) FROM documents;

# Check embeddings
SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL;

# View indexes
\d documents
```

---

## Performance Tips

1. **Use hybrid search** for best results
2. **Generate embeddings** once, search many times
3. **Batch reindex** for large document sets
4. **Monitor stats** regularly
5. **Vacuum database** monthly

---

## Cost Summary

### POC
- **Database:** $0 (Docker)
- **Embeddings:** $0 (Ollama)
- **Total:** **$0/month**

### Production
- **Database:** $50-100/month
- **Compute:** $20-50/month
- **Embeddings:** $0-50/month
- **Total:** **$70-200/month**

---

## File Structure

```
AI_Document_Pipeline/
├── docker-compose.yml          # PostgreSQL setup
├── migrations/
│   └── 001_init_search.sql    # Database schema
├── src/
│   ├── embedding_service.py   # Embeddings (Ollama/OpenAI)
│   ├── search_service.py      # Search functionality
│   └── cli.py                 # CLI commands
├── .env                       # Configuration
├── SETUP_SEARCH.md           # Quick start
├── SEARCH_GUIDE.md           # Complete guide
└── CLOUD_MIGRATION.md        # Production guide
```

---

## Getting Help

- **Quick Start:** [SETUP_SEARCH.md](SETUP_SEARCH.md)
- **Full Guide:** [SEARCH_GUIDE.md](SEARCH_GUIDE.md)
- **Migration:** [CLOUD_MIGRATION.md](CLOUD_MIGRATION.md)
- **Summary:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

---

## Common Patterns

### Search → Classify → Organize
```bash
doc-classify search "unprocessed" --category other
doc-classify classify documents/input
doc-classify search "invoice"
```

### Batch Processing
```bash
doc-classify classify ~/Documents --recursive
doc-classify reindex --include-vectors
doc-classify search-stats
```

### Production Deployment
```bash
# Update .env
DATABASE_URL=postgresql://prod-endpoint/db

# Test
doc-classify search-stats

# Deploy
docker build -t doc-pipeline .
docker push your-registry/doc-pipeline
```

---

**Quick Command Reference:**

| Task | Command |
|------|---------|
| Start DB | `docker-compose up -d` |
| Search | `doc-classify search "query"` |
| Stats | `doc-classify search-stats` |
| Reindex | `doc-classify reindex --include-vectors` |
| Help | `doc-classify search --help` |

---

**One-Line Setup:**
```bash
docker-compose up -d && ollama pull nomic-embed-text && pip install -r requirements.txt && cp .env.example .env
```

🚀 **Ready to go!**
