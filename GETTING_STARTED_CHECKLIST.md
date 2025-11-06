# Getting Started Checklist - Document Search UI

Use this checklist to get the search UI up and running.

---

## Prerequisites

### Software Installation

- [ ] **Python 3.11+** installed
  ```bash
  python3 --version  # Should be 3.11 or higher
  ```

- [ ] **Node.js 18+** installed
  ```bash
  node --version  # Should be v18 or higher
  ```

- [ ] **PostgreSQL 15+** installed and running
  ```bash
  psql --version
  pg_isready
  ```

- [ ] **pgvector extension** installed
  ```bash
  psql -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
  ```

- [ ] **Git** installed
  ```bash
  git --version
  ```

---

## Database Setup

- [ ] Create `documents` database
  ```bash
  createdb documents
  ```

- [ ] Enable pgvector extension
  ```bash
  psql -d documents -c "CREATE EXTENSION IF NOT EXISTS vector;"
  ```

- [ ] Verify database is accessible
  ```bash
  psql -h localhost -U your_user -d documents -c "SELECT version();"
  ```

---

## Backend Setup (FastAPI)

- [ ] Navigate to project directory
  ```bash
  cd /Users/joshuadell/Dev/AI_Document_Pipeline
  ```

- [ ] Install Python dependencies
  ```bash
  pip install -r requirements.txt
  ```

- [ ] Set environment variables
  ```bash
  export DATABASE_URL="postgresql://user:pass@localhost:5432/documents"
  export POSTGRES_HOST="localhost"
  export POSTGRES_USER="your_user"
  export POSTGRES_PASSWORD="your_password"
  export POSTGRES_DB="documents"
  ```

- [ ] Test backend startup
  ```bash
  cd api
  uvicorn main:app --reload
  # Should start without errors
  # Press Ctrl+C to stop
  ```

- [ ] Verify API is accessible
  ```bash
  curl http://localhost:8000/health
  # Should return: {"status":"healthy"}
  ```

- [ ] Check API documentation
  - Open: http://localhost:8000/docs
  - Should see interactive API docs

---

## Frontend Setup (React)

- [ ] Navigate to frontend directory
  ```bash
  cd frontend
  ```

- [ ] **⭐ CRITICAL:** Install Node dependencies
  ```bash
  npm install
  ```

  **This step is REQUIRED!**
  - Without it, TypeScript will show JSX errors in your IDE
  - IDE autocomplete won't work
  - Type checking will fail
  - The app won't run

  **What it does:**
  - Installs 379 packages including React, TypeScript, TanStack Query
  - Creates `node_modules/` directory (~200MB)
  - Takes 1-2 minutes

  **Already installed?** Skip this step if `node_modules/` exists

- [ ] Create `.env.local` file
  ```bash
  cp .env.example .env.local
  # Edit .env.local:
  # VITE_API_URL=http://localhost:8000
  ```

- [ ] Test frontend startup
  ```bash
  npm run dev
  # Should start Vite dev server
  # Press Ctrl+C to stop
  ```

- [ ] Verify frontend is accessible
  - Open: http://localhost:3000
  - Should see "Document Search" page

---

## Verify Integration

- [ ] Start both backend and frontend
  ```bash
  # Option 1: Use quick start script
  ./start_search_ui.sh

  # Option 2: Manual (two terminals)
  # Terminal 1:
  cd api && uvicorn main:app --reload

  # Terminal 2:
  cd frontend && npm run dev
  ```

- [ ] Test search functionality
  1. Open: http://localhost:3000
  2. Enter search query: "test"
  3. Select search mode (hybrid)
  4. Verify results appear (if any documents exist)

- [ ] Test API endpoints
  ```bash
  # Health check
  curl http://localhost:8000/health

  # Stats
  curl http://localhost:8000/api/stats

  # Search
  curl "http://localhost:8000/api/search?q=test&mode=keyword"
  ```

---

## Populate Test Data (Optional)

If no documents exist yet, process some test files:

- [ ] Run document processing pipeline
  ```bash
  # Process a single file
  python3 -m src.main --input-file path/to/document.pdf

  # Or process a directory
  python3 -m src.main --input-dir path/to/documents/
  ```

- [ ] Verify documents in database
  ```bash
  psql -d documents -c "SELECT COUNT(*) FROM documents;"
  ```

- [ ] Test search with processed documents
  - Open: http://localhost:3000
  - Search for keywords from processed documents
  - Verify results appear

---

## Production Readiness (Optional)

For deploying to production:

- [ ] Configure environment for production
  ```bash
  # Backend
  export DATABASE_URL="postgresql://prod-user:prod-pass@prod-db:5432/documents"
  export ENVIRONMENT="production"

  # Frontend
  # Edit .env.production:
  VITE_API_URL=https://api.yourdomain.com
  ```

- [ ] Build frontend for production
  ```bash
  cd frontend
  npm run build
  # Output in dist/ directory
  ```

- [ ] Set up production server
  - [ ] Install Nginx or Apache
  - [ ] Configure SSL certificates
  - [ ] Set up reverse proxy
  - [ ] Configure firewall rules

- [ ] Deploy backend with Gunicorn
  ```bash
  gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
  ```

- [ ] Deploy frontend
  - [ ] Upload dist/ to web server
  - [ ] Or deploy to Vercel/Netlify
  - [ ] Configure CDN (optional)

- [ ] Set up monitoring
  - [ ] Application monitoring (Sentry, DataDog)
  - [ ] Server monitoring (Prometheus, Grafana)
  - [ ] Database monitoring
  - [ ] Log aggregation

- [ ] Performance optimization
  - [ ] Database indexes created
  - [ ] Connection pooling configured
  - [ ] Rate limiting enabled
  - [ ] Caching configured

---

## Troubleshooting

### Backend won't start

**Problem:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
pip install -r requirements.txt
```

---

**Problem:** Database connection errors

**Solution:**
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection details
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

---

### Frontend won't start

**Problem:** `Cannot find module 'react'`

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

**Problem:** API requests fail (CORS errors)

**Solution:**
- Check backend has CORS middleware (already configured in `api/main.py`)
- Verify `VITE_API_URL` in `.env.local` is correct
- Check backend is running on expected port

---

### No search results

**Problem:** Search returns 0 results

**Solution:**
1. Check if documents exist in database:
   ```bash
   psql -d documents -c "SELECT COUNT(*) FROM documents;"
   ```
2. If 0, process some documents first
3. If >0, check search query matches document content

---

## Success Checklist

You're ready to use the search UI when:

- [✓] Backend starts without errors
- [✓] Frontend starts without errors
- [✓] http://localhost:8000/health returns healthy
- [✓] http://localhost:8000/docs shows API documentation
- [✓] http://localhost:3000 shows search interface
- [✓] Search returns results (if documents exist)
- [✓] Can preview documents
- [✓] Can download documents
- [✓] Statistics panel shows correct counts

---

## Quick Commands Reference

```bash
# Start both services (recommended)
./start_search_ui.sh

# Or start individually:

# Backend only
cd api && uvicorn main:app --reload

# Frontend only
cd frontend && npm run dev

# Type checking
cd frontend && npm run typecheck

# Build for production
cd frontend && npm run build

# Run tests (if any)
pytest  # Backend
npm test  # Frontend

# Check logs
tail -f logs/backend.log
tail -f logs/frontend.log
```

---

## Next Steps

Once everything is working:

1. **Read the documentation:**
   - [SEARCH_UI_DEPLOYMENT.md](SEARCH_UI_DEPLOYMENT.md) - Full deployment guide
   - [SEARCH_UI_SUMMARY.md](SEARCH_UI_SUMMARY.md) - What was built
   - [frontend/README.md](frontend/README.md) - Frontend docs

2. **Process your documents:**
   - Run the document processing pipeline
   - Verify documents appear in search

3. **Customize the UI:**
   - Update colors in `tailwind.config.js`
   - Modify components in `frontend/src/components/`
   - Add your logo and branding

4. **Deploy to production:**
   - Follow deployment guide
   - Set up monitoring
   - Configure backups

---

**Questions or issues?** Check the [Troubleshooting](#troubleshooting) section or review [SEARCH_UI_DEPLOYMENT.md](SEARCH_UI_DEPLOYMENT.md).

**Happy searching! 🔍**
