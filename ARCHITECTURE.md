# System Architecture

## Overview

The AI Document Classification Pipeline follows a layered architecture pattern with clear separation of concerns. Each layer is responsible for a specific aspect of the document processing workflow.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐         ┌──────────────────────┐          │
│  │   CLI Tool  │ ────────▶  Python API          │          │
│  │ (src/cli.py)│         │ (Programmatic Usage) │          │
│  │             │         │                      │          │
│  │ • classify  │         │ • Classification     │          │
│  │ • search    │         │ • Search             │          │
│  │ • reindex   │         │ • Indexing           │          │
│  └─────────────┘         └──────────────────────┘          │
│         │                           │                        │
└─────────┼───────────────────────────┼────────────────────────┘
          │                           │
          ▼                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATION LAYER                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            DocumentClassifier                         │  │
│  │  • classify_document()                                │  │
│  │  • classify_batch()                                   │  │
│  │  • classify_directory()                               │  │
│  │  • get_category_distribution()                        │  │
│  │  • export_results()                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            SearchService (NEW)                        │  │
│  │  • keyword_search()     - PostgreSQL FTS              │  │
│  │  • semantic_search()    - pgvector similarity         │  │
│  │  • hybrid_search()      - Combined ranking            │  │
│  │  • get_statistics()                                   │  │
│  │  • reindex_document()                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            DocumentOrganizer                          │  │
│  │  • organize()                                         │  │
│  │  • _create_manifest()                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                           │                        │
└─────────┼───────────────────────────┼────────────────────────┘
          │                           │
          ▼                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYERS                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────┐    ┌───────────────────────────┐│
│  │  EXTRACTION LAYER     │    │  CLASSIFICATION LAYER     ││
│  │                       │    │                           ││
│  │  ExtractionService    │    │    OllamaService          ││
│  │  ┌─────────────────┐ │    │  ┌─────────────────────┐ ││
│  │  │  PDFExtractor   │ │    │  │  is_available()     │ ││
│  │  │  • extract()    │ │    │  │  list_models()      │ ││
│  │  └─────────────────┘ │    │  │  generate()         │ ││
│  │  ┌─────────────────┐ │    │  │  chat()             │ ││
│  │  │  DOCXExtractor  │ │    │  │  classify_document()│ ││
│  │  │  • extract()    │ │    │  │  classify_with_     │ ││
│  │  └─────────────────┘ │    │  │    confidence()     │ ││
│  │  ┌─────────────────┐ │    │  └─────────────────────┘ ││
│  │  │  ExcelExtractor │ │    │           │               ││
│  │  │  • extract()    │ │    │           ▼               ││
│  │  └─────────────────┘ │    │  ┌─────────────────────┐ ││
│  │  ┌─────────────────┐ │    │  │  Ollama LLM         │ ││
│  │  │  TextExtractor  │ │    │  │  (External Service) │ ││
│  │  │  • extract()    │ │    │  └─────────────────────┘ ││
│  │  └─────────────────┘ │    │                           ││
│  └───────────────────────┘    └───────────────────────────┘│
│                                                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │ Input Docs   │   │ Organized    │   │ PostgreSQL DB  │  │
│  │ documents/   │   │ documents/   │   │ (Optional)     │  │
│  │   input/     │──▶│   output/    │   │                │  │
│  │   • PDF      │   │   • Category1/   │ • Full text    │  │
│  │   • DOCX     │   │   • Category2/   │ • Metadata     │  │
│  │   • XLSX     │   │   • Category3/   │ • FTS index    │  │
│  │   • TXT      │   └──────────────┘   │ • Vectors      │  │
│  └──────────────┘                      └────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Metadata & Search Indexes                            │  │
│  │  • Manifest JSON                                      │  │
│  │  • Classification results                             │  │
│  │  • PostgreSQL FTS (full-text search)                  │  │
│  │  • pgvector embeddings (semantic search)              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  CONFIGURATION LAYER                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Settings (Pydantic)                                  │  │
│  │  • Environment variables (.env)                       │  │
│  │  • Default configurations                             │  │
│  │  • Category definitions                               │  │
│  │  • Ollama connection settings                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Classification Pipeline

```
1. INPUT
   └─▶ User provides document path(s)
       └─▶ CLI or Python API

2. EXTRACTION
   └─▶ ExtractionService selects appropriate extractor
       ├─▶ Extracts text content
       ├─▶ Extracts metadata (author, title, dates, etc.)
       └─▶ Returns ExtractedContent object

3. CLASSIFICATION
   └─▶ OllamaService processes extracted content
       ├─▶ Constructs classification prompt
       ├─▶ Sends to local LLM
       ├─▶ Receives category prediction
       └─▶ Validates against predefined categories

4. ORGANIZATION
   └─▶ DocumentOrganizer handles file management
       ├─▶ Creates category folders
       ├─▶ Moves/copies files
       ├─▶ Handles duplicates
       └─▶ Generates manifest

5. OUTPUT
   └─▶ Results returned to user
       ├─▶ Terminal output (CLI)
       ├─▶ JSON export (optional)
       └─▶ Organized file structure
```

## Component Details

### 1. Extraction Layer (`src/extractors.py`)

**Purpose:** Convert various document formats into structured text and metadata

**Design Patterns:**
- Strategy Pattern (BaseExtractor with format-specific implementations)
- Factory Pattern (ExtractionService selects appropriate extractor)

**Key Classes:**
- `DocumentMetadata` - Value object for file metadata
- `ExtractedContent` - Container for content and metadata
- `BaseExtractor` - Abstract base class
- Format-specific extractors (PDF, DOCX, Excel, Text)
- `ExtractionService` - Facade for all extractors

**Dependencies:**
- pdfplumber, PyPDF2 - PDF processing
- python-docx - Word documents
- openpyxl, pandas - Excel files

### 2. Classification Layer (`src/ollama_service.py`)

**Purpose:** Interface with Ollama LLM for intelligent document classification

**Design Patterns:**
- Adapter Pattern (wraps Ollama REST API)
- Template Method (different classification modes)

**Key Methods:**
- `is_available()` - Health check
- `classify_document()` - Simple classification
- `classify_with_confidence()` - Classification with reasoning

**Communication:**
- REST API over HTTP
- JSON payload format
- Streaming disabled for reliability

### 3. Orchestration Layer (`src/classifier.py`)

**Purpose:** Coordinate extraction, classification, and organization

**Design Patterns:**
- Facade Pattern (simplifies complex operations)
- Command Pattern (encapsulates classification operations)

**Key Responsibilities:**
- Batch processing coordination
- Progress tracking
- Results aggregation
- Statistics generation

### 4. Interface Layer (`src/cli.py`)

**Purpose:** Provide user-friendly command-line interface

**Design Patterns:**
- Command Pattern (each CLI command is a command)
- Decorator Pattern (Click decorators)

**Features:**
- Rich terminal output
- Progress indicators
- Input validation
- Error handling

### 5. Configuration Layer (`config.py`)

**Purpose:** Centralized configuration management

**Design Patterns:**
- Singleton Pattern (global settings instance)
- Builder Pattern (Pydantic constructs settings)

**Features:**
- Environment variable support
- Type validation
- Default values
- Computed properties

## Error Handling Strategy

### Layers of Error Handling

```
User Action
    │
    ├─▶ CLI Validation
    │   └─▶ Input validation, path checks
    │
    ├─▶ Service Layer Errors
    │   └─▶ Ollama unavailable, model missing
    │
    ├─▶ Processing Errors
    │   └─▶ Extraction failures, classification errors
    │
    └─▶ System Errors
        └─▶ File permissions, disk space
```

### Error Recovery

1. **Graceful Degradation**: Continue processing other files if one fails
2. **Detailed Logging**: Track all errors with context
3. **User Feedback**: Clear error messages with solutions
4. **Retry Logic**: Automatic retries for transient failures

## Scalability Considerations

### Current Implementation

**Storage & Search:**
- **PostgreSQL Database**: Full-text search with FTS indexing
- **pgvector Integration**: Semantic search with 768-dimensional embeddings
- **Hybrid Search**: Combined keyword + semantic ranking (< 150ms latency)
- **File System**: Organized document storage with category folders
- **Indexing**: Automatic FTS triggers and IVFFlat vector indexes

**Processing:**
- **Single-threaded**: Sequential document processing
- **Batch Operations**: Efficient batch classification and organization
- **Streaming**: Large files processed in chunks

**Search Performance:**
- Keyword search: < 50ms (PostgreSQL FTS with BM25 ranking)
- Semantic search: < 100ms (pgvector cosine similarity)
- Hybrid search: < 150ms (weighted combination)
- Scales to thousands of multi-page documents

### Scalability Characteristics

**Current Capacity:**
- ✅ Handles thousands of documents efficiently
- ✅ Multi-page PDF support (100+ page documents indexed fully)
- ✅ All document content searchable (no page limits)
- ✅ PostgreSQL handles concurrent read operations
- ⚠️ Sequential write operations (classification pipeline)

**Production Ready:**
- PostgreSQL supports horizontal scaling (read replicas)
- pgvector indexes optimize vector similarity search
- Full-text search with weighted fields and ranking
- Cloud-ready: Migrates from local to cloud with zero code changes

### Future Enhancements

**Processing Improvements:**
- **Parallel Processing**: Multi-threading for document extraction
- **Queue System**: Async job processing for large batches (Celery/RQ)
- **Distributed Processing**: Scale classification across multiple workers
- **Caching**: Cache LLM responses for similar documents (Redis)

**Database Optimizations:**
- **Connection Pooling**: PgBouncer for high-concurrency scenarios
- **Partitioning**: Time-based partitioning for very large datasets
- **Replication**: Read replicas for search-heavy workloads
- **Sharding**: Horizontal partitioning for massive scale (10M+ documents)

**Search Enhancements:**
- **Advanced Ranking**: Custom ranking algorithms (BM25F, learning-to-rank)
- **Faceted Search**: Category, date, author filters
- **Autocomplete**: Suggest-as-you-type functionality
- **Search Analytics**: Query performance monitoring and optimization

## Security Architecture

### Data Protection

1. **Local Processing**: All data stays on local machine
2. **No External Calls**: Ollama runs locally
3. **File Permissions**: Respects OS permissions
4. **No Logging of Content**: Sensitive data not logged

### Access Control

- Read access to input directory
- Write access to output directory
- Configurable temporary directory

## Performance Optimization

### Extraction Layer

- **Lazy Loading**: Load documents only when needed
- **Streaming**: Process large files in chunks
- **Caching**: Cache extracted content temporarily

### Classification Layer

- **Batch Requests**: Send multiple documents if supported
- **Model Selection**: Choose appropriate model size
- **Content Truncation**: Limit content length for speed

### Organization Layer

- **Atomic Operations**: Ensure file operations are atomic
- **Batch Moves**: Group file operations
- **Progress Tracking**: Real-time progress updates

## Testing Strategy

### Unit Tests

- Extractor functionality
- Ollama service methods
- Classifier logic

### Integration Tests

- End-to-end workflow
- Multi-format processing
- Error scenarios

### Performance Tests

- Large file handling
- Batch processing
- Memory usage

## Monitoring and Observability

### Logging

- **Loguru**: Structured logging
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Context**: Rich context in log messages

### Metrics

- Processing time per document
- Classification accuracy
- Error rates
- Category distribution

## Search Architecture (NEW)

### Search Service Layer (`src/search_service.py`)

**Purpose:** Provide advanced search capabilities with PostgreSQL FTS and pgvector

**Design Patterns:**
- Strategy Pattern (different search modes)
- Factory Pattern (embedding service selection)

**Search Modes:**
1. **Keyword Search** - PostgreSQL full-text search
   - Uses `ts_vector` and `ts_query`
   - Weighted fields (title > content)
   - BM25 ranking
   - < 50ms latency

2. **Semantic Search** - pgvector similarity
   - Cosine similarity on embeddings
   - 768-dimensional vectors (Ollama)
   - IVFFlat indexing
   - < 100ms latency

3. **Hybrid Search** - Combined ranking
   - Configurable weights
   - Best precision + recall
   - < 150ms latency

### Embedding Service Layer (`src/embedding_service.py`)

**Purpose:** Abstract embedding generation for POC → Production migration

**Design Patterns:**
- Strategy Pattern (provider-specific implementations)
- Factory Pattern (provider selection)

**Providers:**
- **OllamaEmbeddingService** - Free, local (POC)
- **OpenAIEmbeddingService** - Production quality

### Database Schema

**documents table:**
- Full document content + metadata
- `content_tsv` - Full-text search vector (auto-updated)
- `embedding` - 768-dim vector for semantic search
- Indexes: GIN (FTS), IVFFlat (vectors)

**Migrations:**
- `migrations/001_init_search.sql` - Initial schema
- Automatic FTS trigger
- Vector indexing
- Hybrid search function

## Extension Points

### Adding New Document Formats

1. Create new extractor class extending `BaseExtractor`
2. Implement `can_extract()` and `extract()` methods
3. Add to `ExtractionService.extractors` list

### Adding New Models

1. Update Ollama model in configuration
2. Pull model: `ollama pull model_name`
3. Test classification accuracy

### Custom Categories

1. Update `.env` file with new categories
2. Create corresponding output folders
3. Test classification with new categories

### Adding New Search Modes

1. Extend `SearchService` with new method
2. Add to `SearchMode` enum
3. Update CLI and API interfaces
4. Test performance

## Deployment Options

### Local Installation

```bash
pip install -e .
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["doc-classify", "classify", "documents/input"]
```

### Cloud Deployment

- Package as Lambda function
- Deploy with Ollama in container
- Use S3 for document storage

---

## See Also

### Architecture Documentation
- **[SOLID_ARCHITECTURE.md](SOLID_ARCHITECTURE.md)** - SOLID principles implementation and Protocol-based design
- **[OCR_IMPLEMENTATION.md](OCR_IMPLEMENTATION.md)** - OCR capabilities and integration

### Search & Database
- **[SEARCH_GUIDE.md](SEARCH_GUIDE.md)** - Complete search documentation
- **[SETUP_SEARCH.md](SETUP_SEARCH.md)** - Search setup guide
- **[CLOUD_MIGRATION.md](CLOUD_MIGRATION.md)** - POC → Production migration
- **[DATABASE_GUIDE.md](DATABASE_GUIDE.md)** - Database management

### Testing
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing strategy and organization
- **[END_TO_END_TESTING_GUIDE.md](END_TO_END_TESTING_GUIDE.md)** - Complete testing guide

---

**Architecture Version:** 2.0.0 (with Search)
**Last Updated:** October 2025
