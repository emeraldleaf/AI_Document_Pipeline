# Document Search UI - Deployment Guide

**AI Document Classification Pipeline**
**Last Updated:** October 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Quick Start](#quick-start)
5. [Backend Setup (FastAPI)](#backend-setup-fastapi)
6. [Frontend Setup (React)](#frontend-setup-react)
7. [Development Workflow](#development-workflow)
8. [Production Deployment](#production-deployment)
9. [Troubleshooting](#troubleshooting)
10. [Performance Tuning](#performance-tuning)

---

## Overview

The Document Search UI is a modern, high-performance web application for searching and managing documents in the AI Document Pipeline.

### Key Features

- **Multiple Search Modes:** Keyword, semantic, and hybrid search
- **Real-time Results:** <300ms search latency with caching
- **Document Management:** Preview, download, and organize documents
- **Responsive Design:** Works on desktop, tablet, and mobile
- **Production-Ready:** Rate limiting, error handling, monitoring

### Technology Stack

**Backend:**
- FastAPI (async Python web framework)
- PostgreSQL with pgvector (vector database)
- SQLAlchemy (ORM)
- Pydantic (data validation)

**Frontend:**
- React 18 (UI framework)
- TypeScript (type safety)
- TanStack Query (data fetching & caching)
- Tailwind CSS (styling)
- Vite (build tool)

---

## Architecture

```
┌─────────────────┐      HTTP/REST API       ┌─────────────────┐
│                 │ ←────────────────────────→ │                 │
│  React Frontend │                            │  FastAPI Backend│
│  (Port 3000)    │                            │   (Port 8000)   │
│                 │                            │                 │
└─────────────────┘                            └────────┬────────┘
                                                        │
                                                        │ SQL
                                                        ↓
                                               ┌─────────────────┐
                                               │   PostgreSQL    │
                                               │  + pgvector     │
                                               │  (Port 5432)    │
                                               └─────────────────┘
```

**Request Flow:**

1. User enters search query in React UI
2. Request debounced (300ms delay to avoid spam)
3. React Query sends HTTP request to FastAPI
4. FastAPI performs keyword/semantic/hybrid search
5. Results returned with download URLs
6. React Query caches results (5 min)
7. User can preview/download documents

---

## Prerequisites

### Required Software

- **Python 3.11+** - For backend
- **Node.js 18+** - For frontend
- **PostgreSQL 15+** - With pgvector extension
- **Redis** (optional) - For caching
- **Git** - Version control

### System Requirements

**Development:**
- 8GB RAM minimum
- 4 CPU cores
- 10GB disk space

**Production:**
- 16GB+ RAM recommended
- 8+ CPU cores
- 50GB+ disk space

---

## Quick Start

### 1. Clone Repository

```bash
cd /path/to/your/workspace
git clone <your-repo-url>
cd AI_Document_Pipeline
```

### 2. Start Backend (FastAPI)

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
export DATABASE_URL="postgresql://user:pass@localhost:5432/documents"
export POSTGRES_HOST="localhost"
export POSTGRES_USER="your_user"
export POSTGRES_PASSWORD="your_password"
export POSTGRES_DB="documents"

# Run database migrations (if any)
# alembic upgrade head

# Start FastAPI server
cd api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### 3. Start Frontend (React)

```bash
# Open new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:3000`

### 4. Test the Application

1. Open browser to `http://localhost:3000`
2. Enter a search query (e.g., "invoice payment terms")
3. Select search mode (keyword/semantic/hybrid)
4. View results, preview, and download documents

---

## Backend Setup (FastAPI)

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/documents
POSTGRES_HOST=localhost
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=documents

# Ollama (for semantic search)
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text:latest

# Performance
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

### Database Setup

```bash
# Create PostgreSQL database
createdb documents

# Install pgvector extension
psql -d documents -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations (if using Alembic)
alembic upgrade head
```

### Running Backend

**Development:**
```bash
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
# With Gunicorn (production ASGI server)
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | GET | Search documents |
| `/api/documents/{id}` | GET | Get document details |
| `/api/preview/{id}` | GET | Preview document text |
| `/api/download/{id}` | GET | Download original file |
| `/api/stats` | GET | System statistics |
| `/health` | GET | Health check |
| `/docs` | GET | Interactive API docs |

---

## Frontend Setup (React)

### Installation

```bash
cd frontend

# Install dependencies
npm install

# Or with Yarn
yarn install

# Or with pnpm
pnpm install
```

### Configuration

Create `.env.local` file in `frontend/` directory:

```bash
# API URL
VITE_API_URL=http://localhost:8000

# Optional: Enable debug mode
VITE_DEBUG=true
```

### Running Frontend

**Development:**
```bash
npm run dev
# Opens browser at http://localhost:3000
```

**Build for Production:**
```bash
npm run build
# Output in dist/ directory
```

**Preview Production Build:**
```bash
npm run preview
# Serves dist/ at http://localhost:4173
```

### File Structure

```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── SearchResultCard.tsx
│   │   ├── SearchFilters.tsx
│   │   └── StatsPanel.tsx
│   ├── App.tsx               # Main app component
│   ├── main.tsx              # Entry point
│   ├── types.ts              # TypeScript types
│   ├── api.ts                # API client functions
│   ├── utils.ts              # Utility functions
│   └── index.css             # Global styles
├── package.json              # Dependencies
├── vite.config.ts            # Vite configuration
├── tsconfig.json             # TypeScript config
├── tailwind.config.js        # Tailwind CSS config
└── index.html                # HTML template
```

---

## Development Workflow

### 1. Start Development Servers

**Terminal 1 - Backend:**
```bash
cd api
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 2. Making Changes

**Backend Changes:**
- Edit files in `api/`
- FastAPI auto-reloads on file changes
- Test at `http://localhost:8000/docs`

**Frontend Changes:**
- Edit files in `frontend/src/`
- Vite HMR updates browser instantly (no refresh needed)
- Components, styles update in real-time

### 3. Type Checking

**Frontend:**
```bash
cd frontend
npm run typecheck
```

**Backend:**
```bash
# Using mypy (add to dev dependencies)
mypy api/
```

### 4. Linting

**Frontend:**
```bash
cd frontend
npm run lint
```

### 5. Testing the Search

**Test Keyword Search:**
```bash
curl "http://localhost:8000/api/search?q=invoice&mode=keyword"
```

**Test Semantic Search:**
```bash
curl "http://localhost:8000/api/search?q=payment%20terms&mode=semantic"
```

**Test Stats:**
```bash
curl http://localhost:8000/api/stats
```

---

## Production Deployment

### Option 1: Docker Deployment (Recommended)

**1. Create Dockerfile for Backend:**

```dockerfile
# api/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY api/ .

# Expose port
EXPOSE 8000

# Run with Gunicorn
CMD ["gunicorn", "main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

**2. Create Dockerfile for Frontend:**

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production image with Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**3. Create docker-compose.yml:**

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: documents
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: documents
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # FastAPI Backend
  backend:
    build:
      context: .
      dockerfile: api/Dockerfile
    environment:
      DATABASE_URL: postgresql://documents:secure_password@db:5432/documents
      POSTGRES_HOST: db
      POSTGRES_USER: documents
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: documents
      OLLAMA_BASE_URL: http://ollama:11434
    depends_on:
      - db
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data

  # React Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

  # Ollama (for embeddings)
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  postgres_data:
  ollama_data:
```

**4. Deploy:**

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: Manual Deployment

**Backend (on server):**

```bash
# Install dependencies
pip install -r requirements.txt gunicorn

# Set environment variables
export DATABASE_URL="postgresql://user:pass@db-host:5432/documents"

# Run with Gunicorn + systemd
sudo systemctl enable document-api
sudo systemctl start document-api
```

**Frontend (build + deploy):**

```bash
# Build production bundle
cd frontend
npm run build

# Deploy dist/ to web server (Nginx, Apache, S3, etc.)
rsync -avz dist/ user@server:/var/www/search-ui/

# Or upload to S3
aws s3 sync dist/ s3://your-bucket/
```

### Option 3: Platform as a Service

**Backend (Railway, Render, Fly.io):**
1. Connect GitHub repo
2. Set environment variables
3. Deploy automatically on push

**Frontend (Vercel, Netlify, Cloudflare Pages):**
1. Connect GitHub repo
2. Set build command: `npm run build`
3. Set output directory: `dist`
4. Set environment variable: `VITE_API_URL=<backend-url>`
5. Deploy

---

## Troubleshooting

### Backend Issues

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
pg_isready -h localhost

# Test connection
psql -h localhost -U your_user -d documents

# Check environment variables
echo $DATABASE_URL
```

---

**Problem:** Slow search queries

**Solution:**
```sql
-- Create indexes for better performance
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_filename ON documents(filename);
CREATE INDEX idx_documents_processed_at ON documents(processed_at DESC);

-- For semantic search (pgvector)
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

### Frontend Issues

**Problem:** `Cannot find module 'react'`

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

**Problem:** API requests failing (CORS errors)

**Solution:**

Backend (FastAPI) must have CORS middleware:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

**Problem:** Build errors with Tailwind CSS

**Solution:**
```bash
# Reinstall Tailwind dependencies
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

---

**Problem:** Slow page loads in production

**Solution:**
```bash
# Enable compression in Nginx
gzip on;
gzip_types text/css application/javascript application/json;

# Enable browser caching
location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## Performance Tuning

### Backend Optimization

**1. Connection Pooling:**

```python
# In config.py
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 40
DB_POOL_TIMEOUT = 30
```

**2. Query Optimization:**

```python
# Use select_in loading for relationships
from sqlalchemy.orm import selectinload

results = session.execute(
    select(Document).options(selectinload(Document.embeddings))
).scalars().all()
```

**3. Response Caching:**

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

# Cache search results for 5 minutes
@app.get("/api/search")
@cache(expire=300)
async def search(...):
    ...
```

**4. Rate Limiting:**

```python
from slowapi import Limiter

limiter = Limiter(key_func=lambda: "global")

@app.get("/api/search")
@limiter.limit("100/minute")
async def search(...):
    ...
```

### Frontend Optimization

**1. Code Splitting:**

Already configured in vite.config.ts. Vendor chunks are split automatically.

**2. Image Optimization:**

```bash
# Optimize images before deployment
npm install -D vite-plugin-imagemin
```

**3. React Query Caching:**

```typescript
// Increase stale time for static data
const { data: stats } = useQuery({
  queryKey: ['stats'],
  queryFn: getStats,
  staleTime: 5 * 60 * 1000,  // 5 minutes
  cacheTime: 30 * 60 * 1000, // 30 minutes
});
```

**4. Debouncing:**

Already implemented. Search is debounced by 300ms.

**5. Lazy Loading Components:**

```typescript
import { lazy, Suspense } from 'react';

const SearchResultCard = lazy(() => import('./components/SearchResultCard'));

<Suspense fallback={<div>Loading...</div>}>
  <SearchResultCard {...props} />
</Suspense>
```

### Database Optimization

**1. Vector Index (pgvector):**

```sql
-- Create IVFFlat index for faster semantic search
CREATE INDEX idx_embeddings_vector
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Analyze table for better query planning
ANALYZE embeddings;
```

**2. Regular Maintenance:**

```sql
-- Vacuum database weekly
VACUUM ANALYZE documents;

-- Update statistics
ANALYZE;
```

**3. Monitoring:**

```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Monitoring and Logging

### Backend Logging

FastAPI logs are configured in `api/main.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**View logs:**
```bash
# Development
tail -f api.log

# Production (systemd)
journalctl -u document-api -f
```

### Frontend Monitoring

Use browser DevTools:
- **Network Tab:** Check API requests
- **Console:** Check for errors
- **Performance Tab:** Measure load times

**Production Monitoring:**
```typescript
// Add error tracking (e.g., Sentry)
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "your-sentry-dsn",
  environment: import.meta.env.MODE,
});
```

---

## Security Best Practices

### Backend Security

1. **Environment Variables:** Never commit secrets
2. **HTTPS:** Use SSL certificates in production
3. **Rate Limiting:** Prevent abuse
4. **Input Validation:** Pydantic models validate all inputs
5. **SQL Injection:** SQLAlchemy ORM prevents this
6. **CORS:** Restrict to specific origins

### Frontend Security

1. **XSS Protection:** React escapes user input by default
2. **HTTPS Only:** Serve over HTTPS
3. **Content Security Policy:** Add CSP headers
4. **Dependency Scanning:** Run `npm audit`

```bash
# Check for vulnerabilities
npm audit

# Fix automatically
npm audit fix
```

---

## Next Steps

1. **Set up monitoring:** Add application monitoring (e.g., Prometheus, Grafana)
2. **Add authentication:** Implement user login (OAuth, JWT)
3. **Add file upload:** Allow users to upload documents
4. **Add analytics:** Track search queries and user behavior
5. **Improve search:** Fine-tune semantic search with better embeddings
6. **Add tests:** Write unit and integration tests

---

## Support

For issues or questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review API docs at `http://localhost:8000/docs`
- Check browser console for frontend errors
- Review backend logs for API errors

---

**Happy Searching! 🔍**
