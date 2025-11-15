# Architecture Migration Guide

## Current State: Hybrid Architecture

You currently have **TWO architectures** running side-by-side:

### 1. **Monolithic API** (Original - Fully Functional)
```
api/
└── main.py          # FastAPI monolith for search
    ├── /api/search          - Search documents
    ├── /api/documents/{id}  - Get document details
    ├── /api/download/{id}   - Download files
    ├── /api/preview/{id}    - Preview documents
    └── /api/stats           - Statistics

frontend/
└── src/
    └── App.tsx      # React frontend that calls api/main.py
```

**Status:** ✅ **Production-ready and working**
**Port:** 8000
**Purpose:** Document search and retrieval

---

### 2. **Microservices Architecture** (New - Partially Implemented)
```
services/
├── ingestion/                    # ✅ IMPLEMENTED - Document upload
├── classification-worker/        # ✅ IMPLEMENTED - AI classification
├── extraction-worker/            # ✅ IMPLEMENTED - Metadata extraction
├── indexing-worker/              # ✅ IMPLEMENTED - OpenSearch + PostgreSQL
├── notification-service/         # ✅ IMPLEMENTED - WebSocket updates
├── api-gateway/                  # 📝 PLANNED - Not yet implemented
├── search-service/               # 📝 PLANNED - Not yet implemented
└── metadata-service/             # 📝 PLANNED - Not yet implemented

shared/
├── events/          # ✅ Event publisher/consumer library
└── models/          # ✅ SQLModel database models
```

**Status:** 🚧 **Partially implemented**
**Ports:** 8000 (ingestion), 8001 (notifications)
**Purpose:** Event-driven document processing pipeline

---

## Architecture Comparison

### Monolithic API (`api/main.py`)

**What it does:**
- Receives search queries from React frontend
- Searches PostgreSQL/pgvector database
- Returns document results
- Serves file downloads
- Provides document previews

**Request Flow:**
```
User → React Frontend → api/main.py → PostgreSQL → React Frontend → User
```

**Advantages:**
- ✅ Simple deployment (one service)
- ✅ Fast development
- ✅ Easy debugging
- ✅ Working right now

**Limitations:**
- ❌ Everything in one process
- ❌ Hard to scale individual features
- ❌ Single point of failure
- ❌ Difficult to add new processing steps

---

### Microservices Architecture (`services/`)

**What it does:**
- Splits document processing into independent services
- Uses RabbitMQ for event-driven communication
- Each service can scale independently
- WebSocket for real-time progress updates

**Request Flow:**
```
User → Ingestion Service → RabbitMQ Event
                                ↓
                    Classification Worker (2+ replicas)
                                ↓
                    Extraction Worker (2+ replicas)
                                ↓
                    Indexing Worker → PostgreSQL + OpenSearch
                                ↓
                    Notification Service → WebSocket → User
```

**Advantages:**
- ✅ Independent scaling (scale classification separately from extraction)
- ✅ Fault isolation (one service crash doesn't kill everything)
- ✅ Technology flexibility (use different languages/frameworks)
- ✅ Parallel processing (multiple workers process simultaneously)

**Limitations:**
- ❌ More complex deployment
- ❌ Requires message broker (RabbitMQ)
- ❌ Distributed debugging harder
- ❌ Network latency between services

---

## Current Reality

### ✅ What Works Today

**Monolithic API:**
```bash
# Start the monolith
uvicorn api.main:app --reload --port 8000

# Start React frontend
cd frontend && npm start

# Use the application
http://localhost:3000
```

**Microservices (Upload & Processing):**
```bash
# Start microservices
./start_microservices.sh

# Upload document
curl -X POST http://localhost:8000/api/upload -F "file=@doc.pdf"

# Get real-time updates
wscat -c ws://localhost:8001/ws/document/{document_id}
```

### 🚧 What's Missing

**Search in Microservices:**
- The microservices don't have a search endpoint yet
- The monolithic `api/main.py` still handles all search queries
- React frontend still points to monolith for search

**API Gateway:**
- No unified entry point for microservices
- Services exposed on different ports
- No centralized authentication/rate limiting

---

## Migration Paths

You have **three options**:

### Option 1: Keep Both (Recommended for Now) ✅

**Use monolith for search, microservices for processing:**

```
React Frontend
    │
    ├─→ api/main.py (search, download, preview)
    │
    └─→ services/ingestion (upload new documents)
            ↓
        Microservices pipeline (classify, extract, index)
```

**Benefits:**
- Don't break existing search functionality
- Gradually migrate features
- Test microservices in production alongside monolith

**Implementation:**
1. Keep `api/main.py` running for search
2. Add upload endpoint to React that calls `services/ingestion`
3. Both architectures write to same PostgreSQL database
4. Microservices handle NEW uploads, monolith handles search

---

### Option 2: Complete Microservices Migration 🚀

**Implement missing services and fully migrate:**

**What needs to be built:**

1. **Search Service** (`services/search-service/`)
   ```python
   @app.get("/api/search")
   async def search(q: str, limit: int = 10):
       # Same logic as api/main.py search
       # But as a microservice
       results = await search_postgres(q, limit)
       return results
   ```

2. **API Gateway** (`services/api-gateway/`)
   ```python
   # Kong or custom gateway
   # Routes:
   #   /api/upload → services/ingestion
   #   /api/search → services/search-service
   #   /api/documents → services/metadata-service
   ```

3. **Update Frontend**
   ```typescript
   // Change from:
   const API_URL = 'http://localhost:8000'

   // To:
   const API_URL = 'http://localhost:8080' // API Gateway
   ```

**Timeline:** 2-3 weeks

**Benefits:**
- Full microservices architecture
- Independent scaling
- Better fault isolation

**Risks:**
- More complex deployment
- Potential downtime during migration
- Need to test thoroughly

---

### Option 3: Monolith with Async Processing (Hybrid) 🔄

**Keep monolith but use microservices for background processing:**

```python
# api/main.py

@app.post("/api/upload")
async def upload_document(file: UploadFile):
    # Save file
    file_path = save_file(file)

    # Publish event to RabbitMQ (microservices process it)
    publisher.publish('document.uploaded', {
        'file_path': file_path,
        'document_id': doc_id
    })

    # Return immediately
    return {"status": "processing", "document_id": doc_id}

@app.get("/api/search")
async def search(q: str):
    # Same as before
    return search_results
```

**Benefits:**
- Simple API surface (one monolith)
- Scalable background processing (microservices)
- Easy to deploy

**When to use:**
- Small to medium scale
- Want simplicity with some scalability
- Don't need to scale search independently

---

## Recommended Path Forward

### Phase 1: Current State (Keep Both) ✅
```
✅ Monolith handles: Search, download, preview
✅ Microservices handle: Upload, classification, extraction, indexing
✅ Both write to same PostgreSQL database
```

**What you have now:**
- Working search interface
- Working upload pipeline
- SQLModel integration ✅
- DevContainer setup ✅

---

### Phase 2: Add Missing Microservices (Optional)

**Priority 1: Search Service**
```bash
# Create service
mkdir services/search-service
cp api/main.py services/search-service/service.py

# Adapt to microservice pattern
# Add event-driven search capabilities
```

**Priority 2: API Gateway**
```bash
# Use Kong or custom gateway
# Route all traffic through single entry point
```

**Priority 3: Migrate Frontend**
```bash
# Update React to call API gateway
# Add WebSocket for real-time search updates
```

---

### Phase 3: Full Microservices (Future)

**Decommission monolith:**
```bash
# Move all functionality to microservices
# Remove api/main.py
# Full event-driven architecture
```

---

## Quick Decision Matrix

| Question | Monolith | Hybrid | Full Microservices |
|----------|----------|--------|-------------------|
| **Team size** | 1-3 devs | 3-5 devs | 5+ devs |
| **Scale needed** | < 1K docs/day | 1K-100K docs/day | 100K+ docs/day |
| **Complexity tolerance** | Low | Medium | High |
| **Current status** | ✅ Works | ✅ Works | 🚧 Needs work |
| **Time to production** | Now | Now | 2-3 weeks |

---

## What You Should Do Right Now

**Recommendation: Stay with hybrid (Option 1)**

### Keep Using:
1. **Monolithic API** (`api/main.py`) for:
   - Search queries
   - Document downloads
   - Previews
   - Stats

2. **Microservices** (`services/`) for:
   - New document uploads
   - Classification
   - Metadata extraction
   - Indexing

### Your Current Stack:
```
┌─────────────────────────────────────────┐
│         React Frontend (Port 3000)      │
└─────────────────────────────────────────┘
            ↓                    ↓
    ┌───────────┐        ┌──────────────┐
    │ Monolith  │        │ Microservices│
    │ (search)  │        │  (upload)    │
    │ Port 8000 │        │  Port 8000   │
    └───────────┘        └──────────────┘
            ↓                    ↓
    ┌─────────────────────────────────────┐
    │     PostgreSQL + OpenSearch         │
    └─────────────────────────────────────┘
```

### Next Steps:
1. ✅ **Keep what works** - Don't break existing search
2. ✅ **Use SQLModel** - Already implemented
3. ✅ **Use DevContainer** - Already implemented
4. 📝 **Test upload pipeline** - Verify microservices work
5. 📝 **Monitor both** - Track which is used more
6. 📝 **Decide later** - Migrate to full microservices only if needed

---

## Commands Quick Reference

### Run Monolith (Search)
```bash
# API
uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend && npm start
```

### Run Microservices (Upload/Processing)
```bash
./start_microservices.sh
```

### Run Both (Recommended)
```bash
# Terminal 1: Monolith
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm start

# Terminal 3: Microservices (if you want upload processing)
./start_microservices.sh
```

---

## Summary

**You don't have to choose one or the other!**

- ✅ Monolith works great for search
- ✅ Microservices work great for processing
- ✅ Both can coexist happily
- ✅ SQLModel and DevContainer work with both

**The best architecture is the one that meets your needs today.**

If search is working well, keep it. If you need scalable processing, use microservices for that. Migrate to full microservices only when you actually need it.

**Current recommendation: Keep both, use what works.** 🎯
