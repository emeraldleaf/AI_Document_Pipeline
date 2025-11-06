# Local Testing Guide - Full Stack

**AI Document Pipeline - Backend + Frontend Testing**
**Last Updated:** October 2025

---

## Quick Answer: YES! ✅

You can test the **entire backend and frontend locally** on your machine.

**What you need:**
- PostgreSQL database (local)
- Python 3.11+ with dependencies
- Node.js 18+ with dependencies
- Ollama (for semantic search)
- Sample documents to test with

**Time to set up:** 15-30 minutes

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step-by-Step Setup](#step-by-step-setup)
3. [Testing Backend Only](#testing-backend-only)
4. [Testing Frontend Only](#testing-frontend-only)
5. [Testing Full Stack](#testing-full-stack)
6. [Sample Test Workflow](#sample-test-workflow)
7. [Troubleshooting](#troubleshooting)
8. [What You Can Test](#what-you-can-test)

---

## Prerequisites

### Required Software

✅ **PostgreSQL 15+** (local database)
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Verify
psql --version
```

✅ **Python 3.11+** (backend)
```bash
python3 --version
# Should show 3.11 or higher
```

✅ **Node.js 18+** (frontend)
```bash
node --version
# Should show v18 or higher
```

✅ **Ollama** (for semantic search - optional but recommended)
```bash
# macOS
brew install ollama

# Start Ollama service
brew services start ollama

# Pull embedding model
ollama pull nomic-embed-text:latest

# Verify
ollama list
```

### Optional (For Advanced Testing)

- **Redis** (for caching - optional)
- **Celery** (for distributed processing - optional)

---

## Step-by-Step Setup

### 1. Database Setup

```bash
# Create database
createdb documents

# Connect and verify
psql -d documents

# In psql:
CREATE EXTENSION IF NOT EXISTS vector;  -- For semantic search
\q  # Exit psql
```

**Verify database:**
```bash
psql -d documents -c "SELECT version();"
psql -d documents -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

### 2. Backend Setup

```bash
cd /Users/joshuadell/Dev/AI_Document_Pipeline

# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://$(whoami)@localhost:5432/documents"
export POSTGRES_HOST="localhost"
export POSTGRES_USER="$(whoami)"
export POSTGRES_PASSWORD=""
export POSTGRES_DB="documents"
export OLLAMA_BASE_URL="http://localhost:11434"

# Or create .env file
cat > .env << EOF
DATABASE_URL=postgresql://$(whoami)@localhost:5432/documents
POSTGRES_HOST=localhost
POSTGRES_USER=$(whoami)
POSTGRES_PASSWORD=
POSTGRES_DB=documents
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text:latest
EOF
```

**Verify backend setup:**
```bash
# Test database connection
python3 -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://$(whoami)@localhost:5432/documents'); print('✓ Database connected')"

# Check imports
python3 -c "import fastapi, sqlalchemy; print('✓ Backend dependencies OK')"
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies (if not already done)
npm install

# Create .env.local
cat > .env.local << EOF
VITE_API_URL=http://localhost:8000
EOF
```

**Verify frontend setup:**
```bash
# Check TypeScript
npx tsc --noEmit
# Should have no output (no errors)

# Check node_modules
ls node_modules | wc -l
# Should show ~379 directories
```

### 4. Add Sample Documents

**Option A: Use Example Documents**

```bash
cd /Users/joshuadell/Dev/AI_Document_Pipeline

# Create test documents directory
mkdir -p test_documents

# Create sample text files
cat > test_documents/invoice_001.txt << EOF
INVOICE #001
Date: 2024-10-31
From: Acme Corporation
To: Widget Company
Amount: $1,250.00
Payment terms: Net 30 days
Description: Software consulting services
EOF

cat > test_documents/contract_001.txt << EOF
SERVICE AGREEMENT
Date: 2024-10-31
Between: Tech Solutions Inc. and Enterprise Corp
Term: 12 months
Services: Cloud infrastructure management
Monthly fee: $5,000
Payment terms: Net 15 days
EOF

cat > test_documents/receipt_001.txt << EOF
RECEIPT
Date: 2024-10-31
Merchant: Office Supplies Plus
Amount: $234.56
Items:
- Paper (10 reams): $80.00
- Pens (50 pack): $24.56
- Stapler: $30.00
Payment method: Credit card
EOF
```

**Option B: Use Your Own Documents**

```bash
# Copy your PDFs/DOCX/TXT files to test_documents/
cp /path/to/your/documents/* test_documents/
```

### 5. Process Documents

```bash
# Process all documents in test_documents/
python3 -m src.main --input-dir test_documents/

# Or process single file
python3 -m src.main --input-file test_documents/invoice_001.txt

# This will:
# - Extract text from documents
# - Classify them (invoice, contract, receipt, etc.)
# - Generate embeddings for semantic search
# - Store everything in PostgreSQL
```

**Verify documents are in database:**
```bash
psql -d documents -c "SELECT id, filename, category, created_at FROM documents LIMIT 5;"
```

---

## Testing Backend Only

### Start Backend Server

```bash
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**You should see:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Test Backend Endpoints

**Open another terminal and run these tests:**

#### 1. Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

#### 2. API Documentation
```bash
# Open in browser
open http://localhost:8000/docs
```
You'll see interactive API documentation where you can test all endpoints!

#### 3. Search (Keyword)
```bash
curl "http://localhost:8000/api/search?q=invoice&mode=keyword&limit=10"
```

Expected response:
```json
{
  "results": [
    {
      "id": "...",
      "filename": "invoice_001.txt",
      "category": "invoice",
      "score": 0.95,
      "highlights": ["...invoice..."],
      "download_url": "/api/download/...",
      "preview_url": "/api/preview/..."
    }
  ],
  "total_results": 1,
  "execution_time_ms": 45
}
```

#### 4. Search (Semantic)
```bash
curl "http://localhost:8000/api/search?q=payment%20terms&mode=semantic&limit=10"
```

#### 5. Statistics
```bash
curl http://localhost:8000/api/stats
```

Expected response:
```json
{
  "total_documents": 3,
  "categories": {
    "invoice": 1,
    "contract": 1,
    "receipt": 1
  },
  "avg_processing_time_ms": 1250,
  "total_storage_bytes": 1234,
  "last_updated": "2024-10-31T...",
  "status": "healthy"
}
```

#### 6. Preview Document
```bash
# Get document ID from search results, then:
curl "http://localhost:8000/api/preview/{document-id}"
```

#### 7. Download Document
```bash
# In browser, open:
open "http://localhost:8000/api/download/{document-id}"
```

### Backend Testing Checklist

- [ ] ✅ Health check returns `{"status":"healthy"}`
- [ ] ✅ `/docs` shows interactive API documentation
- [ ] ✅ Keyword search returns results
- [ ] ✅ Semantic search returns results
- [ ] ✅ Stats endpoint shows correct counts
- [ ] ✅ Preview endpoint returns document text
- [ ] ✅ Download endpoint serves files
- [ ] ✅ No errors in terminal logs

---

## Testing Frontend Only

### Start Frontend Server

```bash
cd frontend
npm run dev
```

**You should see:**
```
  VITE v5.0.11  ready in 1234 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### Test Frontend (Without Backend)

**Note:** Frontend will show errors if backend isn't running. Start backend first for full testing.

#### Frontend-Only Tests:

1. **Page loads:**
   - Open http://localhost:3000
   - Should see "Document Search" page
   - No JavaScript errors in browser console

2. **UI Components visible:**
   - Search bar
   - Search mode tabs (Keyword, Semantic, Hybrid)
   - Empty state message

3. **TypeScript compilation:**
   ```bash
   npm run typecheck
   # Should complete with no errors
   ```

4. **Build test:**
   ```bash
   npm run build
   # Should complete successfully
   # Output in dist/ directory
   ```

### Frontend Testing Checklist (UI Only)

- [ ] ✅ Page loads at http://localhost:3000
- [ ] ✅ No console errors
- [ ] ✅ Search bar visible and functional
- [ ] ✅ Search mode tabs render correctly
- [ ] ✅ TypeScript compiles without errors
- [ ] ✅ Production build succeeds

---

## Testing Full Stack

### Start Both Services

**Option 1: Quick Start Script (Recommended)**

```bash
cd /Users/joshuadell/Dev/AI_Document_Pipeline
./start_search_ui.sh
```

This automatically:
- Checks dependencies
- Starts backend on port 8000
- Starts frontend on port 3000
- Opens browser to http://localhost:3000

**Option 2: Manual Start (Two Terminals)**

**Terminal 1 - Backend:**
```bash
cd /Users/joshuadell/Dev/AI_Document_Pipeline/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /Users/joshuadell/Dev/AI_Document_Pipeline/frontend
npm run dev
```

**Then open browser:** http://localhost:3000

### Full Stack Testing Checklist

#### 1. Page Load
- [ ] ✅ Frontend loads at http://localhost:3000
- [ ] ✅ No errors in browser console
- [ ] ✅ Stats panel shows correct document counts

#### 2. Keyword Search
- [ ] ✅ Type "invoice" in search box
- [ ] ✅ Click "Keyword" search mode
- [ ] ✅ Results appear within 1 second
- [ ] ✅ Results show filename, category, score
- [ ] ✅ Highlights show matching text

#### 3. Semantic Search
- [ ] ✅ Type "payment terms" in search box
- [ ] ✅ Click "Semantic" search mode
- [ ] ✅ Results appear (may be slower, 1-3 seconds)
- [ ] ✅ Results are relevant (not just exact matches)

#### 4. Hybrid Search
- [ ] ✅ Type "contract services" in search box
- [ ] ✅ Click "Hybrid" search mode (default)
- [ ] ✅ Results combine keyword + semantic

#### 5. Document Preview
- [ ] ✅ Click "Preview" button on a search result
- [ ] ✅ Loading spinner shows briefly
- [ ] ✅ Document text displays in modal
- [ ] ✅ Can close preview

#### 6. Document Download
- [ ] ✅ Click "Download" button on a search result
- [ ] ✅ Browser downloads the original file
- [ ] ✅ File opens correctly

#### 7. Category Filtering
- [ ] ✅ Click "Show Filters" button
- [ ] ✅ Category pills display
- [ ] ✅ Click a category (e.g., "invoice")
- [ ] ✅ Results filter to that category only
- [ ] ✅ Click "All" or same category to clear filter

#### 8. Pagination
- [ ] ✅ Search returns >20 results (add more docs if needed)
- [ ] ✅ Pagination controls appear
- [ ] ✅ Click "Next" page
- [ ] ✅ New results load
- [ ] ✅ Click "Previous" page
- [ ] ✅ Previous results load

#### 9. Loading States
- [ ] ✅ Spinner shows while searching
- [ ] ✅ "Updating..." indicator shows during background fetch
- [ ] ✅ No flickering or jumping content

#### 10. Error Handling
- [ ] ✅ Stop backend (Ctrl+C in backend terminal)
- [ ] ✅ Try searching in frontend
- [ ] ✅ Error message displays (not blank screen)
- [ ] ✅ Restart backend
- [ ] ✅ Search works again

#### 11. Caching
- [ ] ✅ Search "invoice" (first time: ~300ms)
- [ ] ✅ Search "contract" (new search: ~300ms)
- [ ] ✅ Search "invoice" again (cached: <10ms - instant!)
- [ ] ✅ Check Network tab in browser DevTools
- [ ] ✅ Second "invoice" search: no API call (cached by React Query)

#### 12. Debouncing
- [ ] ✅ Open Network tab in browser DevTools
- [ ] ✅ Type "i" "n" "v" "o" "i" "c" "e" quickly
- [ ] ✅ Only ONE API call made (after you stop typing)
- [ ] ✅ Not 7 API calls (one per keystroke)

#### 13. Stats Auto-Refresh
- [ ] ✅ Note current document count in stats panel
- [ ] ✅ Process a new document in another terminal:
       ```bash
       echo "Test document" > test.txt
       python3 -m src.main --input-file test.txt
       ```
- [ ] ✅ Wait 60 seconds
- [ ] ✅ Stats panel updates automatically (document count increases)
- [ ] ✅ No page refresh needed

#### 14. Responsive Design
- [ ] ✅ Resize browser window to mobile size (< 768px)
- [ ] ✅ UI adapts to mobile layout
- [ ] ✅ All features still work

---

## Sample Test Workflow

Here's a complete test workflow you can follow:

### Setup (One-Time)

```bash
# 1. Create database
createdb documents
psql -d documents -c "CREATE EXTENSION vector;"

# 2. Set environment variables
export DATABASE_URL="postgresql://$(whoami)@localhost:5432/documents"

# 3. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 4. Create test documents
mkdir -p test_documents
# (Create 3 test files as shown in Step 4 above)

# 5. Process documents
python3 -m src.main --input-dir test_documents/
```

### Daily Testing

```bash
# 1. Start both services
./start_search_ui.sh

# 2. Browser opens automatically to http://localhost:3000

# 3. Test search:
   - Type "invoice" → See results
   - Click "Preview" → See document content
   - Click "Download" → File downloads
   - Type "payment" → See semantic results

# 4. Test caching:
   - Search "invoice" again → Instant results (cached)

# 5. Stop services:
   - Press Ctrl+C in terminal
```

### Testing New Features

```bash
# 1. Make code changes

# 2. Backend changes:
   # - Save file
   # - FastAPI auto-reloads (no restart needed)
   # - Test immediately

# 3. Frontend changes:
   # - Save file
   # - Vite HMR updates browser instantly (no refresh)
   # - See changes immediately

# 4. Type checking:
   cd frontend && npm run typecheck
```

---

## Troubleshooting

### Backend Won't Start

**Problem:** `Database connection failed`

**Solution:**
```bash
# Check PostgreSQL is running
pg_isready -h localhost

# If not running:
brew services start postgresql@15

# Check connection
psql -d documents -c "SELECT 1;"
```

---

**Problem:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
pip install -r requirements.txt
```

---

**Problem:** `No documents found in database`

**Solution:**
```bash
# Process documents first
python3 -m src.main --input-dir test_documents/

# Verify
psql -d documents -c "SELECT COUNT(*) FROM documents;"
```

---

### Frontend Won't Start

**Problem:** `Cannot find module 'react'`

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

**Problem:** `JSX element implicitly has type 'any'`

**Solution:**
```bash
# Install dependencies (they're missing!)
cd frontend
npm install

# Restart VS Code or run:
# Cmd+Shift+P → "TypeScript: Restart TS Server"
```

---

**Problem:** `Connection refused to http://localhost:8000`

**Solution:**
```bash
# Backend isn't running! Start it:
cd api
uvicorn main:app --reload
```

---

### Search Not Working

**Problem:** Search returns 0 results

**Check 1:** Documents in database?
```bash
psql -d documents -c "SELECT filename, category FROM documents;"
```

**Check 2:** Ollama running? (for semantic search)
```bash
ollama list
# Should show: nomic-embed-text:latest

# If not:
ollama pull nomic-embed-text:latest
```

**Check 3:** Check backend logs
```bash
# Look for errors in the terminal running uvicorn
```

---

### Performance Issues

**Problem:** Search is slow (>3 seconds)

**Solution 1:** Create database indexes
```sql
-- Connect to database
psql -d documents

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- Analyze tables
ANALYZE documents;
ANALYZE embeddings;
```

**Solution 2:** Check Ollama is running
```bash
# Semantic search needs Ollama
brew services list | grep ollama
```

---

## What You Can Test

### ✅ Backend Testing

- [x] API endpoints (all 6)
- [x] Database operations (CRUD)
- [x] Search algorithms (keyword, semantic, hybrid)
- [x] File serving (preview, download)
- [x] Error handling
- [x] Performance (<300ms search)
- [x] Concurrent requests
- [x] Rate limiting (if enabled)

### ✅ Frontend Testing

- [x] UI rendering
- [x] Search functionality
- [x] TanStack Query caching
- [x] Debouncing (300ms delay)
- [x] Loading states
- [x] Error states
- [x] Preview modal
- [x] Download functionality
- [x] Category filtering
- [x] Pagination
- [x] Responsive design
- [x] TypeScript compilation

### ✅ Integration Testing

- [x] Backend ↔ Database
- [x] Frontend ↔ Backend API
- [x] Search → Preview → Download flow
- [x] Caching end-to-end
- [x] Stats auto-refresh
- [x] Error propagation

### ✅ Performance Testing

- [x] Search latency
- [x] Cache hit rate
- [x] Page load time
- [x] Bundle size
- [x] Network requests (count)
- [x] Memory usage

---

## Advanced Testing

### Load Testing (Optional)

```bash
# Install Apache Bench
brew install apache-bench

# Test search endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 "http://localhost:8000/api/search?q=invoice&mode=keyword"

# Check results:
# - Requests per second
# - Average response time
# - Failed requests (should be 0)
```

### Automated Testing (Optional)

**Backend tests:**
```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Create tests/test_api.py
# Run tests
pytest tests/
```

**Frontend tests:**
```bash
# Install Vitest
npm install -D vitest @testing-library/react

# Create tests
# Run tests
npm test
```

---

## Summary

### ✅ YES! You Can Test Everything Locally

**What works locally:**
- ✅ Full backend API (all endpoints)
- ✅ Full frontend UI (all features)
- ✅ Database operations
- ✅ Semantic search (with Ollama)
- ✅ Document preview/download
- ✅ Caching and performance
- ✅ All integration flows

**What you need:**
- PostgreSQL (local database)
- Python + dependencies
- Node.js + dependencies
- Ollama (for semantic search)
- Sample documents

**Time investment:**
- First setup: 15-30 minutes
- Daily testing: 30 seconds (just run `./start_search_ui.sh`)

**No cloud/remote services needed!** Everything runs on your Mac.

---

## Quick Start (Copy-Paste)

```bash
# 1. Database
createdb documents
psql -d documents -c "CREATE EXTENSION vector;"

# 2. Environment
export DATABASE_URL="postgresql://$(whoami)@localhost:5432/documents"

# 3. Dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 4. Test documents
mkdir -p test_documents
echo "INVOICE #001 - Payment due" > test_documents/invoice.txt

# 5. Process
python3 -m src.main --input-dir test_documents/

# 6. Start everything
./start_search_ui.sh

# 7. Test in browser: http://localhost:3000
```

**That's it! You're testing locally! 🚀**

---

## Need Help?

- **Setup issues:** See [GETTING_STARTED_CHECKLIST.md](GETTING_STARTED_CHECKLIST.md)
- **Backend errors:** Check [api/main.py](api/main.py) comments
- **Frontend errors:** See [TYPESCRIPT_SETUP.md](TYPESCRIPT_SETUP.md)
- **TanStack Query:** Read [TANSTACK_QUERY_GUIDE.md](frontend/TANSTACK_QUERY_GUIDE.md)

**Happy testing! 🎉**
