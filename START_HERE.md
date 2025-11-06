# 🚀 Start Here

Welcome to the AI Document Classification Pipeline!

## What Do You Want To Do?

### 📄 Classify Documents (Basic)
→ **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes

### ⚡ Process 500K Documents (High-Volume)
→ **[QUICK_START_500K.md](QUICK_START_500K.md)** - Process massive volumes fast

### 🔍 Search Documents
→ **[SETUP_SEARCH.md](SETUP_SEARCH.md)** - Enable search in 10 minutes

### 🚀 Deploy to Production
→ **[CLOUD_MIGRATION.md](CLOUD_MIGRATION.md)** - Scale to cloud

---

## Quick Test (PostgreSQL + Search)

### Step 1: Install Docker Desktop (if not installed)

```bash
brew install --cask docker
```

Then open **Docker Desktop** from Applications and wait for it to start.

### Step 2: Run the Test

```bash
./test_postgres.sh
```

That's it! The script will:
- ✅ Start PostgreSQL with pgvector
- ✅ Create test documents
- ✅ Test full-text search
- ✅ Test semantic search
- ✅ Test hybrid search

## What This Tests

This validates your **ARCHITECTURE.md** scalability section:

### Current Implementation ✅
- PostgreSQL database with FTS indexing
- pgvector integration (768-dimensional embeddings)
- Hybrid search (keyword + semantic ranking < 150ms)
- Automatic FTS triggers and IVFFlat vector indexes

### Search Performance ✅
- Keyword search: < 50ms (PostgreSQL FTS with BM25 ranking)
- Semantic search: < 100ms (pgvector cosine similarity)
- Hybrid search: < 150ms (weighted combination)

## After Testing

### Try Search Commands

```bash
# Basic search
doc-classify search "invoice"

# Semantic search
doc-classify search "payment document" --mode semantic

# View statistics
doc-classify search-stats
```

### Stop PostgreSQL

```bash
docker-compose down
```

## Documentation

### Quick Start Guides
- **[QUICKSTART.md](QUICKSTART.md)** - Basic classification
- **[QUICK_START_500K.md](QUICK_START_500K.md)** - High-volume processing ⚡
- **[SETUP_SEARCH.md](SETUP_SEARCH.md)** - Search setup
- **[QUICK_TEST_GUIDE.md](QUICK_TEST_GUIDE.md)** - Testing

### Complete Guides
- **[SCALING_GUIDE.md](SCALING_GUIDE.md)** - Scale to 500K documents ⚡
- **[SEARCH_GUIDE.md](SEARCH_GUIDE.md)** - Search documentation
- **[CLOUD_MIGRATION.md](CLOUD_MIGRATION.md)** - Production deployment
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture

### All Documentation
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation index

---

**Questions?** Check [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for all guides.
