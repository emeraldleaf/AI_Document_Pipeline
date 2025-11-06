# Database Guide

The AI Document Classification Pipeline includes **optional database support** for storing document metadata, classifications, and tracking performance over time.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Database Schema](#database-schema)
5. [CLI Commands](#cli-commands)
6. [Python API](#python-api)
7. [Use Cases](#use-cases)
8. [Supported Databases](#supported-databases)

---

## Overview

### Why Use a Database?

**Without Database** (Default):
- ✅ Simple, no setup required
- ✅ Results stored in JSON files
- ❌ Limited search capabilities
- ❌ No historical tracking
- ❌ Manual data management

**With Database** (Optional):
- ✅ Fast search and filtering
- ✅ Historical tracking and analytics
- ✅ Query by category, date, author, etc.
- ✅ Accuracy tracking over time
- ✅ Centralized metadata storage
- ⚠️ Requires SQLAlchemy installation
- ⚠️ Additional setup step

### What Gets Stored?

When database is enabled, the following data is automatically stored:

1. **Document Metadata**
   - File path, name, type, size
   - Author, title, dates
   - Page count
   - File hash (for deduplication)

2. **Classification Results**
   - Predicted category
   - Confidence/reasoning
   - Model used
   - Processing time

3. **Content** (Optional)
   - Content preview (first 1000 chars)
   - Full content (if enabled)

4. **Organization Info**
   - Output path after organization
   - Organization status

5. **Classification History**
   - All classification attempts
   - Corrections (for training)
   - Accuracy tracking

---

## Quick Start

### 1. Install SQLAlchemy

```bash
pip install sqlalchemy
```

### 2. Enable Database

Edit your `.env` file:

```ini
# Enable database
USE_DATABASE=true

# Database URL (default: SQLite)
DATABASE_URL=sqlite:///documents.db

# Store full document content (optional, can be large)
STORE_FULL_CONTENT=false
```

### 3. Use Normally

That's it! Now when you classify documents, they're automatically stored in the database:

```bash
doc-classify classify documents/input
```

### 4. Query the Database

```bash
# View statistics
doc-classify db-stats

# Search documents
doc-classify db-search --search "invoice"

# Filter by category
doc-classify db-search --category invoices

# Export to JSON
doc-classify db-export --output my_docs.json
```

---

## Configuration

### Environment Variables

```ini
# .env file

# Enable/disable database (default: false)
USE_DATABASE=true

# Database connection URL
# SQLite (default):
DATABASE_URL=sqlite:///documents.db

# PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/documents

# MySQL:
# DATABASE_URL=mysql://user:password@localhost/documents

# Store full document text (default: false)
# Warning: Can significantly increase database size
STORE_FULL_CONTENT=false
```

### Python Configuration

```python
from src.classifier import DocumentClassifier

# Enable database for this session
classifier = DocumentClassifier(use_database=True)

# Disable database (use default from config)
classifier = DocumentClassifier(use_database=False)
```

---

## Database Schema

### Documents Table

Stores document metadata and classification results.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key (auto-increment) |
| file_path | String(500) | Full file path |
| file_name | String(255) | File name only |
| file_type | String(50) | MIME type |
| file_size | Integer | Size in bytes |
| file_hash | String(64) | SHA256 hash for deduplication |
| created_date | DateTime | File creation date |
| modified_date | DateTime | File modification date |
| processed_date | DateTime | When classified (indexed) |
| author | String(255) | Document author |
| title | String(500) | Document title |
| page_count | Integer | Number of pages |
| category | String(100) | Classification category (indexed) |
| confidence | Text | Classification reasoning |
| model_used | String(100) | Ollama model used |
| content_preview | Text | First 1000 characters |
| full_content | Text | Full document text (optional) |
| metadata_json | JSON | Additional metadata |
| output_path | String(500) | Path after organization |
| is_organized | Boolean | Organization status |
| classification_time | Float | Processing time (seconds) |

### Classification History Table

Tracks classification history for training and accuracy analysis.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| document_id | Integer | Reference to document |
| timestamp | DateTime | When classified (indexed) |
| predicted_category | String(100) | AI prediction |
| correct_category | String(100) | Correct category (if corrected) |
| was_corrected | Boolean | If prediction was wrong |
| model_name | String(100) | Model used |
| confidence_score | Text | Confidence/reasoning |
| processing_time | Float | Time taken (seconds) |

---

## CLI Commands

### View Statistics

```bash
doc-classify db-stats
```

Output:
```
Total Documents: 150
Processed Today: 12
Organized: 140
Unorganized: 10

By Category:
  • invoices: 45
  • contracts: 32
  • reports: 28
  • correspondence: 25
  • other: 20
```

### Search Documents

```bash
# Text search (searches file name, title, author, content)
doc-classify db-search --search "invoice"

# Filter by category
doc-classify db-search --category invoices

# Combined search
doc-classify db-search --search "quarterly" --category reports

# Limit results
doc-classify db-search --search "contract" --limit 10
```

### Export Database

```bash
# Export all documents
doc-classify db-export

# Export with limit
doc-classify db-export --limit 100 --output recent.json

# Output location
doc-classify db-export --output /path/to/export.json
```

---

## Python API

### Basic Usage

```python
from pathlib import Path
from src.database import DatabaseService

# Initialize database
db = DatabaseService(database_url="sqlite:///documents.db")

# Add a document
doc_id = db.add_document(
    file_path=Path("invoice.pdf"),
    category="invoices",
    content="Invoice content...",
    metadata={"author": "John Doe", "title": "Invoice #123"},
    confidence="High confidence classification",
    model_used="llama3.2:3b",
)

# Get document by ID
doc = db.get_document_by_id(doc_id)
print(doc)

# Search documents
results = db.search_documents(query="invoice", category="invoices")
for doc in results:
    print(f"{doc['file_name']} - {doc['category']}")

# Get statistics
stats = db.get_statistics()
print(f"Total documents: {stats['total_documents']}")
```

### With Classifier

```python
from src.classifier import DocumentClassifier

# Database is automatically used if enabled in config
classifier = DocumentClassifier()

# Or explicitly enable/disable
classifier = DocumentClassifier(use_database=True)

# Classify - results automatically stored in database
results = classifier.classify_directory(Path("documents/input"))

# Each result includes database ID
for result in results:
    print(f"Doc ID: {result.db_id}, Category: {result.category}")
```

### Advanced Queries

```python
from src.database import DatabaseService

db = DatabaseService()

# Get documents by category
invoices = db.get_documents_by_category("invoices", limit=50)

# Search with filter
contracts = db.search_documents(
    query="agreement",
    category="contracts",
    limit=100
)

# Get accuracy over time
accuracy_data = db.get_accuracy_over_time(days=30)
print(accuracy_data["dates"])  # ['2025-10-01', '2025-10-02', ...]
print(accuracy_data["accuracy"])  # [0.85, 0.87, 0.90, ...]

# Export to JSON
db.export_to_json(Path("backup.json"))

# Statistics
stats = db.get_statistics()
print(stats["by_category"])  # {'invoices': 45, 'contracts': 32, ...}
```

### Classification History

```python
# Add classification to history
db.add_classification_history(
    document_id=123,
    predicted_category="reports",
    correct_category="invoices",  # If corrected
    model_name="llama3.2:3b",
    confidence="Medium confidence",
    processing_time=2.5,
)

# Get accuracy trends
accuracy = db.get_accuracy_over_time(days=30)

# Visualize (requires matplotlib)
import matplotlib.pyplot as plt

plt.plot(accuracy["dates"], accuracy["accuracy"])
plt.title("Classification Accuracy Over Time")
plt.ylabel("Accuracy")
plt.xlabel("Date")
plt.show()
```

---

## Use Cases

### 1. Document Management System

Store all classified documents in a searchable database:

```bash
# Enable database
echo "USE_DATABASE=true" >> .env

# Classify and store
doc-classify classify documents/archive

# Search later
doc-classify db-search --search "contract 2024"
doc-classify db-search --category contracts
```

### 2. Compliance & Auditing

Track all document processing for compliance:

```python
from src.database import DatabaseService

db = DatabaseService()

# Generate audit report
stats = db.get_statistics()
print(f"Total processed: {stats['total_documents']}")
print(f"Organized: {stats['organized']}")

# Export for audit
db.export_to_json(Path("audit_report.json"))
```

### 3. Performance Monitoring

Track classification accuracy over time:

```python
# Get accuracy trends
accuracy = db.get_accuracy_over_time(days=90)

# Calculate average
avg_accuracy = sum(accuracy["accuracy"]) / len(accuracy["accuracy"])
print(f"90-day average accuracy: {avg_accuracy:.2%}")

# Identify trends
if accuracy["accuracy"][-1] < accuracy["accuracy"][0]:
    print("Warning: Accuracy declining")
```

### 4. Content Search

Full-text search across all documents:

```python
# Find all documents mentioning "Q4 results"
results = db.search_documents("Q4 results")

# Filter by category and date
from datetime import datetime, timedelta
recent_contracts = db.search_documents(
    query="amendment",
    category="contracts"
)
```

### 5. Deduplication

Automatically detect duplicate documents:

```python
# Database stores SHA256 hash of each file
# Query by hash to find duplicates

from src.database import DatabaseService
import hashlib

def find_duplicates(db):
    """Find duplicate documents by hash."""
    session = db.get_session()

    # Get all hashes
    from sqlalchemy import func
    from src.database import Document

    duplicates = (
        session.query(Document.file_hash, func.count(Document.id))
        .group_by(Document.file_hash)
        .having(func.count(Document.id) > 1)
        .all()
    )

    return duplicates
```

---

## Supported Databases

### SQLite (Default)

**Pros:**
- No setup required
- Single file database
- Perfect for local use
- Fast for small to medium datasets

**Configuration:**
```ini
DATABASE_URL=sqlite:///documents.db
```

### PostgreSQL

**Pros:**
- Best for production
- Excellent performance
- Advanced features
- Concurrent access

**Setup:**
```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/documents
```

### MySQL/MariaDB

**Pros:**
- Wide compatibility
- Good performance
- Popular choice

**Setup:**
```bash
# Install MySQL driver
pip install pymysql

# Configuration
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/documents
```

### Remote Databases

Connect to cloud databases:

```ini
# AWS RDS PostgreSQL
DATABASE_URL=postgresql://user:pass@mydb.xyz.rds.amazonaws.com:5432/documents

# Google Cloud SQL
DATABASE_URL=postgresql://user:pass@/documents?host=/cloudsql/project:region:instance

# Azure Database
DATABASE_URL=postgresql://user@server:pass@server.postgres.database.azure.com:5432/documents
```

---

## Best Practices

### 1. Storage Considerations

```ini
# For large document collections, don't store full content
STORE_FULL_CONTENT=false

# Only preview (1000 chars) is stored by default
# This keeps database size manageable
```

### 2. Regular Backups

```bash
# SQLite - just copy the file
cp documents.db documents_backup_$(date +%Y%m%d).db

# Or use export command
doc-classify db-export --output backup_$(date +%Y%m%d).json
```

### 3. Performance Optimization

```python
# Add indexes for frequently queried fields
from sqlalchemy import Index
from src.database import Base, Document

# Custom indexes (advanced)
Index('idx_category_date', Document.category, Document.processed_date)
```

### 4. Privacy & Security

```python
# Don't store sensitive content
settings.store_full_content = False

# Use encrypted database URL in production
# DATABASE_URL should be in .env, not committed to git

# Consider encryption at rest for sensitive documents
```

---

## Troubleshooting

### Database Not Created

```bash
# Ensure SQLAlchemy is installed
pip install sqlalchemy

# Check configuration
doc-classify config

# Verify database URL
echo $DATABASE_URL
```

### Connection Errors

```python
# Test connection
from src.database import DatabaseService

try:
    db = DatabaseService("sqlite:///test.db")
    print("Connection successful")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Performance Issues

```sql
-- For large databases, add indexes
CREATE INDEX idx_doc_category ON documents(category);
CREATE INDEX idx_doc_date ON documents(processed_date);
CREATE INDEX idx_doc_hash ON documents(file_hash);
```

---

## Migration & Maintenance

### Export Existing Data

```bash
# Before making changes, export data
doc-classify db-export --output pre_migration_backup.json
```

### Clear Database

```python
from src.database import DatabaseService

db = DatabaseService()
# WARNING: This deletes all data!
db.clear_database()
```

### Schema Updates

If you update the schema in `src/database.py`, recreate tables:

```python
from src.database import Base, DatabaseService

# Drop and recreate (WARNING: loses data!)
db = DatabaseService()
Base.metadata.drop_all(db.engine)
Base.metadata.create_all(db.engine)
```

---

## Next Steps

- **Getting Started**: See [GETTING_STARTED.md](GETTING_STARTED.md)
- **Training**: See [TRAINING_GUIDE.md](TRAINING_GUIDE.md)
- **API Reference**: See [src/database.py](src/database.py)

---

**Questions?** Check [README.md](README.md) or open an issue on GitHub.
