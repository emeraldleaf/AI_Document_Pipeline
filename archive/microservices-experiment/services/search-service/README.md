# Search Service (Not Yet Implemented)

## Status: 🔜 Future Enhancement

This service is **designed but not yet implemented**. It's part of the optional enhancement roadmap.

---

## Purpose

Provide a dedicated REST API for searching documents with:
- **Keyword Search** - Traditional full-text search
- **Semantic Search** - AI-powered meaning-based search
- **Hybrid Search** - Combine both for best results
- **Faceted Search** - Filter by category, date, etc.
- **Search History** - Track user searches
- **Search Suggestions** - Auto-complete queries

---

## Planned Technology

- **FastAPI** - Modern Python web framework
- **OpenSearch Client** - Query the search index
- **Redis** - Cache frequent queries
- **Pydantic** - Request/response validation

---

## When to Implement

Implement this service when:
- You need a frontend to search documents
- You want advanced search features
- You need search analytics
- You're building a user-facing application

---

## Current Workaround

For now, query OpenSearch directly:

```bash
# Keyword search
curl "http://localhost:9200/documents/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match": {"text": "invoice"}}}'

# Semantic search with embeddings
# (generate embedding first, then search by vector similarity)
```

This works fine for development and simple queries.

---

## Implementation Guide

See [EVENT_DRIVEN_ARCHITECTURE.md](../../EVENT_DRIVEN_ARCHITECTURE.md) for:
- Complete API specification
- Endpoint definitions
- Query examples
- Response formats
- Caching strategies

---

## Planned Endpoints

```
GET  /api/search?q=query&mode=hybrid&limit=20
GET  /api/search/suggestions?q=query
GET  /api/documents/{id}
GET  /api/categories
GET  /api/stats
```

---

## Quick Implementation (When Needed)

1. Create FastAPI service
2. Add OpenSearch query logic
3. Implement search endpoints
4. Add Redis caching
5. Create Dockerfile
6. Add to docker-compose

**Estimated time:** 2-3 days

---

**Status:** Optional - Can query OpenSearch directly
**Priority:** Medium (implement when building frontend)
**Documentation:** Complete design available in architecture docs
