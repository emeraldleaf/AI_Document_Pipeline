# Metadata Service (Not Yet Implemented)

## Status: 🔜 Future Enhancement

This service is **designed but not yet implemented**. It's part of the optional enhancement roadmap.

---

## Purpose

Provide CRUD operations for document metadata with:
- **Create** - Add new metadata records
- **Read** - Retrieve document metadata
- **Update** - Modify existing metadata
- **Delete** - Remove documents
- **Validation** - Ensure data quality
- **Statistics** - Aggregate metadata insights

---

## Planned Technology

- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Metadata storage
- **SQLAlchemy** - ORM for database operations
- **Redis** - Cache frequently accessed metadata
- **Pydantic** - Data validation

---

## When to Implement

Implement this service when:
- You need to manually edit metadata
- You want to expose metadata to frontend
- You need bulk update operations
- You're building admin interfaces

---

## Current Workaround

For now, metadata is managed by the indexing worker:
- **Created** - When document is uploaded
- **Updated** - During indexing process
- **Stored** - In PostgreSQL automatically

Query directly if needed:
```bash
# Connect to PostgreSQL
docker exec -it doc-pipeline-postgres psql -U postgres -d documents

# Query metadata
SELECT * FROM documents WHERE document_id = 'abc123';
```

This works fine for automated processing.

---

## Implementation Guide

See [EVENT_DRIVEN_ARCHITECTURE.md](../../EVENT_DRIVEN_ARCHITECTURE.md) for:
- Complete API specification
- Database schema
- Endpoint definitions
- Validation rules
- Caching strategy

---

## Planned Endpoints

```
POST   /api/documents              # Create metadata
GET    /api/documents/{id}         # Get document metadata
PUT    /api/documents/{id}         # Update metadata
DELETE /api/documents/{id}         # Delete document
GET    /api/documents              # List all documents
GET    /api/stats                  # Get statistics
POST   /api/documents/bulk-update  # Batch operations
```

---

## Planned Events

This service would also listen to events:
- **document.indexed** - Update status to "indexed"
- **document.failed** - Update status to "failed"

And publish events:
- **document.metadata.updated** - When admin edits metadata
- **document.deleted** - When document is removed

---

## Quick Implementation (When Needed)

1. Create FastAPI service
2. Add PostgreSQL client
3. Implement CRUD endpoints
4. Add event listeners
5. Add Redis caching
6. Create Dockerfile
7. Add to docker-compose

**Estimated time:** 2-3 days

---

**Status:** Optional - Indexing worker handles this automatically
**Priority:** Low (implement when building admin UI)
**Documentation:** Complete design available in architecture docs
