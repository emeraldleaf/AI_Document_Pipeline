# SQLModel Integration Guide

## Overview

This document describes the SQLModel integration in the AI Document Pipeline microservices architecture. SQLModel combines Pydantic validation with SQLAlchemy ORM for type-safe database operations.

## Why SQLModel?

**Benefits over raw SQL:**
- ✅ Type safety with Pydantic validation
- ✅ Auto-completion in IDEs
- ✅ Compile-time error detection
- ✅ Cleaner, more maintainable code
- ✅ Built-in data validation
- ✅ Seamless JSON field handling
- ✅ Automatic schema migrations

**Comparison:**

```python
# Before (Raw SQL)
conn.execute(text("""
    INSERT INTO documents (document_id, category, metadata, confidence, indexed)
    VALUES (:document_id, :category, :metadata, :confidence, :indexed)
    ON CONFLICT (document_id) DO UPDATE SET...
"""), {'document_id': doc_id, 'category': cat, ...})

# After (SQLModel)
doc = Document(
    document_id=doc_id,
    category=cat,
    metadata_=metadata,
    confidence=0.95,
    indexed=True
)
session.add(doc)
session.commit()
```

## Architecture

### Database Models

Location: `shared/models/document.py`

```
DocumentBase (SQLModel)
    ├── Document (table=True)
    │   - Full database model with all fields
    │   - Includes processing status, timestamps, errors
    │
    ├── DocumentCreate
    │   - For creating new documents
    │
    ├── DocumentRead
    │   - For API responses
    │
    └── DocumentUpdate
        - For partial updates

BatchJob (SQLModel, table=True)
    - Tracks batch upload jobs
    - Progress monitoring
    - Correlation IDs
```

### Model Fields

**Document Model:**
```python
class Document(DocumentBase, table=True):
    id: Optional[int]                           # Primary key
    document_id: str                            # Unique identifier (indexed)
    category: Optional[str]                     # Document category
    file_path: Optional[str]                    # Storage path
    confidence: Optional[float]                 # Extraction confidence (0.0-1.0)
    indexed: bool                               # OpenSearch indexing status

    # Processing metadata
    extraction_method: Optional[str]            # docling, llm, etc.
    processing_status: str                      # pending, processing, indexed, failed

    # Extracted metadata (JSON field)
    metadata_: Optional[Dict[str, Any]]

    # Error tracking
    error_message: Optional[str]
    retry_count: int

    # Timestamps
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime]
```

**BatchJob Model:**
```python
class BatchJob(SQLModel, table=True):
    id: Optional[int]
    batch_id: str                               # Unique batch identifier
    correlation_id: str                         # For event correlation

    # Progress tracking
    total_documents: int
    completed_documents: int
    failed_documents: int

    # Status
    status: str                                 # pending, processing, completed, failed

    # Metadata
    batch_metadata: Optional[Dict[str, Any]]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
```

### Indexes

Automatic indexes for query optimization:
```python
Index('idx_document_id', Document.document_id, unique=True)
Index('idx_category', Document.category)
Index('idx_processing_status', Document.processing_status)
Index('idx_created_at', Document.created_at)

Index('idx_batch_id', BatchJob.batch_id, unique=True)
Index('idx_correlation_id', BatchJob.correlation_id)
Index('idx_batch_status', BatchJob.status)
```

## Implementation

### 1. Indexing Worker

**File:** `services/indexing-worker/worker.py`

The indexing worker has been updated to use SQLModel for all PostgreSQL operations.

**Before (Raw SQL):**
```python
def _update_postgres(self, document_id, category, metadata, confidence, indexed):
    with self.db_engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'documents'
            )
        """))

        # Create table if needed
        if not result.scalar():
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS documents (...)
            """))

        # Upsert document
        conn.execute(text("""
            INSERT INTO documents (...)
            VALUES (...)
            ON CONFLICT (document_id) DO UPDATE SET...
        """), {...})
        conn.commit()
```

**After (SQLModel):**
```python
def _update_postgres(self, document_id, category, metadata, confidence, indexed):
    # Ensure table exists
    SQLModel.metadata.create_all(self.db_engine)

    with Session(self.db_engine) as session:
        # Try to find existing document
        statement = select(DocumentModel).where(
            DocumentModel.document_id == document_id
        )
        existing_doc = session.exec(statement).first()

        if existing_doc:
            # Update existing
            existing_doc.category = category
            existing_doc.metadata_ = metadata
            existing_doc.confidence = confidence
            existing_doc.indexed = indexed
            existing_doc.updated_at = datetime.utcnow()
            existing_doc.indexed_at = datetime.utcnow() if indexed else None
        else:
            # Create new
            doc = DocumentModel(
                document_id=document_id,
                category=category,
                metadata_=metadata,
                confidence=confidence,
                indexed=indexed,
                processing_status="indexed" if indexed else "processing",
                indexed_at=datetime.utcnow() if indexed else None
            )
            session.add(doc)

        session.commit()
```

**Key improvements:**
- ✅ No raw SQL strings
- ✅ Type-safe field assignments
- ✅ Automatic schema creation
- ✅ Cleaner upsert logic
- ✅ Built-in validation
- ✅ Better error messages

### 2. Future Services

When implementing the API Gateway and Search Service, use the same pattern:

```python
from shared.models.document import Document, DocumentRead
from sqlmodel import Session, select

# Read operation
def get_document(document_id: str) -> DocumentRead:
    with Session(engine) as session:
        statement = select(Document).where(Document.document_id == document_id)
        doc = session.exec(statement).first()
        return DocumentRead.from_orm(doc)

# Search operation
def search_documents(category: str) -> List[DocumentRead]:
    with Session(engine) as session:
        statement = select(Document).where(Document.category == category)
        docs = session.exec(statement).all()
        return [DocumentRead.from_orm(doc) for doc in docs]

# Update operation
def update_document(document_id: str, update: DocumentUpdate) -> Document:
    with Session(engine) as session:
        statement = select(Document).where(Document.document_id == document_id)
        doc = session.exec(statement).first()

        # Update only provided fields
        for key, value in update.dict(exclude_unset=True).items():
            setattr(doc, key, value)

        doc.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(doc)
        return doc
```

## Dependencies

### Indexing Worker

**File:** `services/indexing-worker/requirements.txt`

```
sqlmodel==0.0.14
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
```

### Shared Models

**File:** `shared/models/requirements.txt` (if needed)

```
sqlmodel==0.0.14
sqlalchemy==2.0.23
```

## Database Initialization

### Automatic Schema Creation

SQLModel automatically creates tables on first connection:

```python
from sqlmodel import SQLModel, create_engine

# Create engine
engine = create_engine(database_url)

# Create all tables
SQLModel.metadata.create_all(engine)
```

This replaces manual `CREATE TABLE` SQL statements.

### Migration Support

For production, use Alembic for migrations:

```bash
# Install
pip install alembic

# Initialize
alembic init migrations

# Configure alembic/env.py
from shared.models.document import Document, BatchJob
target_metadata = SQLModel.metadata

# Create migration
alembic revision --autogenerate -m "Add document tables"

# Apply migration
alembic upgrade head
```

## Testing

### Unit Tests

```python
import pytest
from sqlmodel import Session, create_engine, SQLModel
from shared.models.document import Document

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_create_document(session):
    doc = Document(
        document_id="test-123",
        category="invoice",
        confidence=0.95,
        indexed=True
    )
    session.add(doc)
    session.commit()

    # Verify
    saved_doc = session.get(Document, doc.id)
    assert saved_doc.document_id == "test-123"
    assert saved_doc.confidence == 0.95

def test_update_document(session):
    # Create
    doc = Document(document_id="test-456", category="receipt")
    session.add(doc)
    session.commit()

    # Update
    doc.category = "invoice"
    doc.confidence = 0.88
    session.commit()

    # Verify
    session.refresh(doc)
    assert doc.category == "invoice"
    assert doc.confidence == 0.88

def test_validation():
    # Should raise validation error
    with pytest.raises(ValidationError):
        doc = Document(
            document_id="test",
            confidence=1.5  # Invalid: must be 0.0-1.0
        )
```

### Integration Tests

```python
async def test_indexing_worker_postgres():
    worker = IndexingWorker()

    # Test document indexing
    success = worker._update_postgres(
        document_id="doc-123",
        category="invoice",
        metadata={"amount": 100.00},
        confidence=0.95,
        indexed=True
    )

    assert success

    # Verify in database
    with Session(worker.db_engine) as session:
        doc = session.exec(
            select(Document).where(Document.document_id == "doc-123")
        ).first()

        assert doc is not None
        assert doc.category == "invoice"
        assert doc.confidence == 0.95
        assert doc.indexed is True
```

## Performance

### Query Optimization

SQLModel generates optimized queries:

```python
# Efficient queries with indexes
statement = (
    select(Document)
    .where(Document.category == "invoice")
    .where(Document.confidence >= 0.8)
    .order_by(Document.created_at.desc())
    .limit(100)
)
```

### Batch Operations

For bulk inserts:

```python
def bulk_insert_documents(documents: List[DocumentCreate]):
    with Session(engine) as session:
        db_docs = [Document(**doc.dict()) for doc in documents]
        session.add_all(db_docs)
        session.commit()
```

### Connection Pooling

SQLAlchemy handles connection pooling automatically:

```python
engine = create_engine(
    database_url,
    pool_size=10,          # Number of connections to maintain
    max_overflow=20,       # Additional connections when pool is full
    pool_timeout=30,       # Timeout waiting for connection
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

## Best Practices

### 1. Use Context Managers

Always use `Session` as a context manager:

```python
# Good
with Session(engine) as session:
    doc = session.get(Document, doc_id)
    # session.commit() is called automatically
    # session.close() is called on exit

# Bad
session = Session(engine)
doc = session.get(Document, doc_id)
session.commit()
session.close()  # Easy to forget!
```

### 2. Handle Exceptions

Wrap database operations in try-except:

```python
try:
    with Session(engine) as session:
        doc = Document(...)
        session.add(doc)
        session.commit()
except IntegrityError:
    logger.error("Duplicate document_id")
    return False
except Exception as e:
    logger.error(f"Database error: {e}")
    return False
```

### 3. Use Type Hints

SQLModel provides full type safety:

```python
def get_document(document_id: str) -> Optional[Document]:
    with Session(engine) as session:
        return session.get(Document, document_id)

def list_documents(category: str) -> List[Document]:
    with Session(engine) as session:
        statement = select(Document).where(Document.category == category)
        return list(session.exec(statement))
```

### 4. Separate Read/Write Models

Use different models for input/output:

```python
# API endpoint
@app.post("/documents", response_model=DocumentRead)
def create_document(doc: DocumentCreate):
    db_doc = Document(**doc.dict())
    with Session(engine) as session:
        session.add(db_doc)
        session.commit()
        session.refresh(db_doc)
    return db_doc
```

## Migration from Raw SQL

### Step-by-Step Process

1. **Install SQLModel**
   ```bash
   pip install sqlmodel
   ```

2. **Import Models**
   ```python
   from shared.models.document import Document, DocumentCreate, DocumentRead
   from sqlmodel import Session, select
   ```

3. **Replace Raw SQL Queries**

   **Before:**
   ```python
   result = conn.execute(text("SELECT * FROM documents WHERE category = :cat"), {"cat": category})
   rows = result.fetchall()
   ```

   **After:**
   ```python
   with Session(engine) as session:
       docs = session.exec(select(Document).where(Document.category == category)).all()
   ```

4. **Replace Inserts**

   **Before:**
   ```python
   conn.execute(text("INSERT INTO documents (document_id, category) VALUES (:id, :cat)"),
                {"id": doc_id, "cat": category})
   ```

   **After:**
   ```python
   with Session(engine) as session:
       doc = Document(document_id=doc_id, category=category)
       session.add(doc)
       session.commit()
   ```

5. **Replace Updates**

   **Before:**
   ```python
   conn.execute(text("UPDATE documents SET category = :cat WHERE document_id = :id"),
                {"cat": new_category, "id": doc_id})
   ```

   **After:**
   ```python
   with Session(engine) as session:
       doc = session.get(Document, doc_id)
       doc.category = new_category
       session.commit()
   ```

## Status

### Completed ✅
- Created SQLModel models in `shared/models/document.py`
- Updated indexing worker to use SQLModel
- Added sqlmodel to indexing worker requirements
- Verified syntax and imports

### Next Steps
- [ ] Add DevContainer configuration with SQLModel
- [ ] Create migration scripts with Alembic
- [ ] Add comprehensive tests for SQLModel operations
- [ ] Update API Gateway to use SQLModel (when implemented)
- [ ] Update Search Service to use SQLModel (when implemented)
- [ ] Add monitoring for database queries

## Resources

- **SQLModel Documentation:** https://sqlmodel.tiangolo.com/
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org/
- **Pydantic Documentation:** https://docs.pydantic.dev/

## Summary

SQLModel integration provides:
- ✅ Type-safe database operations
- ✅ Built-in validation
- ✅ Cleaner, more maintainable code
- ✅ Better error detection
- ✅ Seamless FastAPI integration
- ✅ Production-ready ORM

The indexing worker now uses SQLModel for all PostgreSQL operations, eliminating raw SQL and providing type safety throughout the pipeline.
