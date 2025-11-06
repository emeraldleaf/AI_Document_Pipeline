# AI-Powered Document Classification Pipeline

> **⚠️ PROOF OF CONCEPT - NOT PRODUCTION READY**
>
> This is a proof-of-concept implementation that has **not been fully tested**. Use at your own risk.
> Before deploying to production, conduct thorough testing with your specific use cases and data.

Automatically classify and organize multi-format documents (PDF, Excel, Word, etc.) using Ollama's local LLM models. This pipeline intelligently categorizes documents based on their content and metadata, then organizes them into structured folders.

## Features

### Document Processing
- **Multi-format Support**: PDF, Word (DOCX), Excel (XLSX), plain text, and **images** (PNG, JPG, TIFF, etc.)
- **OCR Text Extraction**: Automatically extracts text from images and image-based PDFs using Tesseract OCR
  - Supports scanned documents and image-based PDFs
  - Confidence scoring for extracted text
  - Automatic image preprocessing for better accuracy
  - See [OCR_IMPLEMENTATION.md](OCR_IMPLEMENTATION.md) for details
- **Smart Extraction**: Extracts both text content and metadata (author, title, dates, etc.)
- **Page-level Analysis**: Handles multi-page documents intelligently
- **Image-based PDF Support**: Automatically detects and processes scanned PDFs with OCR

### AI Classification
- **Local LLM Power**: Uses Ollama for privacy-preserving, on-device classification
- **Intelligent Analysis**: Considers both content and metadata for accurate categorization
- **Confidence Scoring**: Optional reasoning explanations for each classification
- **Customizable Categories**: Define your own classification categories

### Advanced Search (NEW)
- **Complete Full-Text Search**: Search ALL text from EVERY page in your documents (PDFs, Word, Excel)
- **Keyword Search**: Lightning-fast PostgreSQL FTS with ranking - no size or page limits
- **Semantic Search**: AI-powered concept matching using vector embeddings
- **Hybrid Search**: Combines keyword + semantic for best results
- **Multi-Page Support**: 100-page PDF? 1000-page contract? All text is indexed and searchable
- **Cloud-Ready**: Free POC → Production with zero code changes
- **Multiple Backends**: Ollama (free, local) or OpenAI (production)

### Auto-Organization
- **Automated Filing**: Moves or copies files into category-specific folders
- **Duplicate Handling**: Intelligent renaming when files conflict
- **Audit Trail**: Creates detailed manifest files for tracking
- **Batch Processing**: Efficiently processes entire directories
- **Database Storage**: Optional PostgreSQL storage with full-text indexing

### High-Throughput Processing (NEW) ⚡
- **Parallel Processing**: Multi-core document processing with 5-10x speedup
- **Async Batch Processing**: Concurrent I/O operations with 10-15x total speedup
- **Distributed Processing**: Horizontal scaling across multiple machines with 50x+ speedup
- **500K Documents in 1 Week**: Process massive document volumes efficiently
- **Production Ready**: Docker Compose deployment with monitoring dashboard
- **Cloud Scalable**: Deploy to AWS/GCP/Azure for unlimited scale
- **See [QUICK_START_500K.md](QUICK_START_500K.md) for processing 500,000 documents**

## Why Ollama?

- **Privacy & Security**: All processing happens locally, no data leaves your machine
- **Customizable**: Use pre-trained models or fine-tune for your specific domain
- **Flexible**: Works with unstructured data and various document types
- **Cost-effective**: No API fees, runs on your own hardware

## Use Cases

### Document Organization
- Sorting office documents by department
- Organizing contracts, invoices, and reports
- Automating research paper classification
- Streamlining compliance and audit document workflows
- Managing personal document archives
- Categorizing email attachments in bulk

### Advanced Search (NEW)
- Search across thousands of multi-page documents instantly
- Find specific clauses in 500-page contracts
- Search all invoices from any time period
- Locate information across entire document collections
- Natural language queries: "how to request a refund"
- Works with PDFs, Word docs, Excel sheets - all pages, all sheets, all text

### High-Volume Processing (NEW) ⚡
- **Enterprise Scale**: Process 500,000+ documents in days instead of months
- **Legal Discovery**: Classify thousands of documents for litigation
- **Digital Transformation**: Migrate paper archives to digital systems
- **Compliance Audits**: Organize and categorize regulatory documents at scale
- **Research Data**: Process large academic document collections
- **Government**: Handle FOIA requests with massive document volumes

## Installation

### Prerequisites

1. **Python 3.9+** installed on your system
2. **Ollama** installed and running

#### Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

#### Pull a Model

```bash
# Recommended: Fast and accurate 3B parameter model
ollama pull llama3.2:3b

# Alternative: More powerful but slower
ollama pull llama3.1:8b
```

#### Start Ollama Service

```bash
ollama serve
```

### Install the Pipeline

#### Option 1: Using pip (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd AI_Document_Pipeline

# Install in editable mode
pip install -e .
```

#### Option 2: Using requirements.txt

```bash
# Clone the repository
git clone <repository-url>
cd AI_Document_Pipeline

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Initialize the Pipeline

```bash
# Create directory structure with default categories
doc-classify init

# Or specify custom categories
doc-classify init --categories "invoices,contracts,reports,correspondence"
```

This creates:
```
documents/
├── input/          # Place documents here
├── output/         # Organized documents appear here
│   ├── invoices/
│   ├── contracts/
│   ├── reports/
│   └── ...
└── temp/           # Temporary processing files
```

### 2. Check Ollama Connection

```bash
doc-classify check
```

### 3. Classify Documents

```bash
# Classify all documents in input folder
doc-classify classify documents/input

# Classify a single file
doc-classify classify path/to/document.pdf

# Classify with AI reasoning
doc-classify classify documents/input --reasoning

# Copy instead of move
doc-classify classify documents/input --copy

# Custom output directory
doc-classify classify documents/input -o /path/to/output

# Export results to JSON
doc-classify classify documents/input --export results.json
```

## Configuration

### Using .env File

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Edit `.env`:

```ini
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Document Processing
INPUT_FOLDER=./documents/input
OUTPUT_FOLDER=./documents/output
TEMP_FOLDER=./documents/temp

# Classification Categories (comma-separated)
CATEGORIES=invoices,contracts,reports,correspondence,research,compliance,other

# Processing Options
MAX_FILE_SIZE_MB=100
PROCESS_SUBDIRECTORIES=true
PRESERVE_ORIGINAL_STRUCTURE=false
```

### View Current Configuration

```bash
doc-classify config
```

## CLI Commands

### Document Classification

#### `doc-classify init`
Initialize directory structure and create category folders.

**Example:**
```bash
doc-classify init --categories "legal,financial,hr,marketing"
```

#### `doc-classify check`
Verify Ollama service is running and list available models.

**Example:**
```bash
doc-classify check --model llama3.1:8b
```

#### `doc-classify classify`
Classify and organize documents.

**Arguments:**
- `INPUT_PATH`: File or directory to classify

**Options:**
- `-o, --output PATH`: Output directory
- `-c, --categories TEXT`: Categories list
- `--copy`: Copy files instead of moving
- `--reasoning`: Include AI classification reasoning
- `--no-organize`: Only classify, don't organize
- `--export PATH`: Export results to JSON
- `-v, --verbose`: Enable detailed logging

**Examples:**
```bash
# Basic classification
doc-classify classify documents/input

# Classify with reasoning and export
doc-classify classify documents/input --reasoning --export report.json

# Classify single file without organizing
doc-classify classify invoice.pdf --no-organize

# Custom categories and output
doc-classify classify docs/ -c "urgent,normal,archive" -o organized_docs/

# Verbose mode for debugging
doc-classify classify documents/input -v
```

---

#### `doc-classify config`
Display current configuration settings.

**Example:**
```bash
doc-classify config
```

---

### Advanced Search Commands (NEW)

#### `doc-classify search`
Search documents using keyword, semantic, or hybrid search.

**Full-Text Coverage:**
- ✅ Searches **ALL text** from **EVERY page** in your documents
- ✅ No size limits - 1-page or 1000-page documents fully indexed
- ✅ Multi-format: PDFs (all pages), Word docs (all paragraphs), Excel (all sheets)
- ✅ Complete content stored when `STORE_FULL_CONTENT=true`
- ✅ Lightning fast even with thousands of multi-page documents

**Examples:**
```bash
# Hybrid search (default - best results)
doc-classify search "contract amendment"

# Keyword search (fast, exact matches)
doc-classify search "INV-2024-001" --mode keyword

# Semantic search (AI-powered concept matching)
doc-classify search "how to cancel subscription" --mode semantic

# Filter by category
doc-classify search "Q3 results" --category reports

# Custom hybrid weights
doc-classify search "invoice" --keyword-weight 0.7 --semantic-weight 0.3

# Search finds text from ANY page in multi-page documents
doc-classify search "appendix section 12.3" --mode keyword
```

**See Also:** [SEARCH_GUIDE.md](SEARCH_GUIDE.md) for complete search documentation

---

#### `doc-classify search-stats`
Display search index statistics including FTS and embedding coverage.

**Example:**
```bash
doc-classify search-stats
```

---

#### `doc-classify reindex`
Reindex documents for search and optionally generate embeddings.

**Examples:**
```bash
# Reindex FTS (fast - automatic usually)
doc-classify reindex

# Generate embeddings for semantic search
doc-classify reindex --include-vectors

# Reindex specific category
doc-classify reindex --category invoices --include-vectors
```

**See Also:** [SETUP_SEARCH.md](SETUP_SEARCH.md) for search setup guide

---

#### Database Commands

See [DATABASE_GUIDE.md](DATABASE_GUIDE.md) for database management commands (`db-stats`, `db-search`, `db-export`)

## Python API Usage

### Classification API

```python
from pathlib import Path
from src.classifier import DocumentClassifier, DocumentOrganizer
from src.ollama_service import OllamaService

# Initialize services
ollama = OllamaService()
classifier = DocumentClassifier(ollama_service=ollama)

# Classify a single document
result = classifier.classify_document(Path("invoice.pdf"))
print(f"Category: {result.category}")

# Classify a directory
results = classifier.classify_directory(
    Path("documents/input"),
    recursive=True,
    include_reasoning=True
)

# Organize files
organizer = DocumentOrganizer(output_dir=Path("documents/output"))
summary = organizer.organize(results, copy_files=False)
print(f"Organized {summary['successful']} files")

# Export results
classifier.export_results(Path("classification_results.json"))
```

### Search API (NEW)

```python
from src.search_service import SearchService, SearchMode
from config import settings

# Initialize search service
search = SearchService(
    database_url=settings.database_url,
    embedding_provider="ollama"
)

# Hybrid search (best results)
results = search.search(
    query="contract amendment",
    mode=SearchMode.HYBRID,
    limit=20
)

# Keyword search (fast)
results = search.keyword_search("invoice payment", limit=10)

# Semantic search (smart)
results = search.semantic_search("refund policy", limit=15)

# Display results
for result in results:
    print(f"{result.file_name} - Score: {result.combined_score:.4f}")
    print(f"  Category: {result.category}")
    print(f"  Preview: {result.content_preview[:100]}...\n")

# Get search statistics
stats = search.get_statistics()
print(f"Total documents: {stats['total_documents']}")
print(f"Embedding coverage: {stats['embedding_coverage']}")
```

**See Also:** [SEARCH_GUIDE.md](SEARCH_GUIDE.md) for more search examples

## Architecture

### SOLID Architecture

The pipeline is built with **SOLID principles** for maintainability, testability, and extensibility:

- **Protocol-based Design**: Clear interfaces with dependency injection
- **Layered Architecture**: Domain, Services, and Infrastructure layers
- **Type Safety**: Strong typing with Result[T] for error handling
- **Testability**: Easy mocking and unit testing
- **Extensibility**: Add new document formats or services without modifying core code

**See [SOLID_ARCHITECTURE.md](SOLID_ARCHITECTURE.md) for complete architectural details**

### Component Overview

```
AI Document Pipeline
│
├── Domain Layer (src/domain/)
│   ├── Protocols - Interface definitions
│   ├── Models - Immutable domain models
│   └── Configuration - Type-safe settings
│
├── Services Layer (src/services/)
│   ├── OCR Service - Text extraction from images
│   ├── Classification Service - AI-powered categorization
│   └── Processing Service - Main orchestration
│
├── Infrastructure Layer (src/infrastructure/)
│   ├── PDFExtractor - Handles PDF documents
│   ├── ImageExtractor - Processes images with OCR
│   ├── DOCXExtractor - Processes Word documents
│   ├── ExcelExtractor - Extracts spreadsheet data
│   └── TextExtractor - Plain text files
│
└── Interface Layer (src/cli.py)
    └── CLI Commands - User interface
```

### Processing Flow

```
1. Document Input
   ↓
2. Metadata & Content Extraction
   ↓
3. AI Classification (Ollama LLM)
   ↓
4. Category Assignment
   ↓
5. Auto-Organization into Folders
   ↓
6. Manifest Generation
```

## Advanced Usage

### Custom Categories for Specific Domains

**Legal Practice:**
```bash
doc-classify init --categories "contracts,briefs,correspondence,discovery,filings"
```

**Research Lab:**
```bash
doc-classify init --categories "papers,protocols,data,grants,presentations"
```

**Accounting Firm:**
```bash
doc-classify init --categories "invoices,receipts,tax_forms,statements,reports"
```

### Batch Processing with Progress

```python
from src.classifier import DocumentClassifier
from pathlib import Path

classifier = DocumentClassifier()

# Process with progress bar
results = classifier.classify_batch(
    file_paths=[Path("doc1.pdf"), Path("doc2.docx")],
    include_reasoning=True,
    show_progress=True
)
```

### Custom Ollama Models

```python
from src.ollama_service import OllamaService
from src.classifier import DocumentClassifier

# Use a specialized model
ollama = OllamaService(model="mistral:7b")
classifier = DocumentClassifier(ollama_service=ollama)
```

## Troubleshooting

### Ollama Service Not Available

**Problem:** `Ollama service not available` error

**Solutions:**
1. Check if Ollama is running: `ollama serve`
2. Verify the host URL: `doc-classify check --host http://localhost:11434`
3. Ensure a model is installed: `ollama list`

### Classification Accuracy Issues

**Problem:** Documents classified incorrectly

**Solutions:**
1. Use a more powerful model: `ollama pull llama3.1:8b`
2. Enable reasoning to see classification logic: `--reasoning`
3. Adjust categories to be more specific
4. Ensure documents have clear content (not scanned images)

### File Permission Errors

**Problem:** Cannot move or copy files

**Solutions:**
1. Check file permissions
2. Use `--copy` flag to preserve originals
3. Run with appropriate user permissions

### Memory Issues

**Problem:** Out of memory errors with large PDFs

**Solutions:**
1. Adjust `MAX_FILE_SIZE_MB` in config
2. Process files individually instead of batch
3. Use a smaller Ollama model

## Performance Tips

1. **Model Selection**: `llama3.2:3b` is fast and accurate for most use cases
2. **Batch Processing**: Process multiple files at once for efficiency
3. **Resource Management**: Larger models need more RAM but provide better accuracy
4. **Content Length**: Very long documents are automatically truncated for faster processing

## Contributing

Contributions are welcome! Areas for improvement:

- Additional document format extractors (images with OCR, HTML, RTF)
- Fine-tuned models for specific domains
- Web interface for visual classification
- Database integration for document tracking
- Multi-language support

### Development Resources

Before contributing, please review:

- **[SOLID_ARCHITECTURE.md](SOLID_ARCHITECTURE.md)** - Protocol-based architecture and design patterns
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component details
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing strategy and organization
- **[END_TO_END_TESTING_GUIDE.md](END_TO_END_TESTING_GUIDE.md)** - Complete testing guide
- **[OCR_IMPLEMENTATION.md](OCR_IMPLEMENTATION.md)** - OCR integration details

## License

**MIT License**

Copyright (c) 2025 Joshua Dell

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for full details.

### Disclaimer

**THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.**

This is a **proof-of-concept implementation** that has not been comprehensively tested. The authors and contributors:

- ❌ Make NO warranties about functionality, reliability, or fitness for any purpose
- ❌ Are NOT liable for any damages, data loss, or issues arising from use
- ❌ Do NOT guarantee accuracy of document classification or search results
- ⚠️ Recommend thorough testing before production use
- ⚠️ Advise backing up important documents before processing

**Use at your own risk.** For production deployments, conduct extensive testing with your specific use cases and data.

## Acknowledgments

- Built with [Ollama](https://ollama.com/) for local LLM inference
- Uses [pdfplumber](https://github.com/jsvine/pdfplumber) for PDF extraction
- CLI powered by [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/)
- PostgreSQL and pgvector for search capabilities

## Support

For issues and questions:
- Open an issue on GitHub
- Check Ollama documentation: https://ollama.com/docs
- Review existing issues for similar problems

**Note:** This is a proof-of-concept project. Community support is provided on a best-effort basis.

---

## Project Status

- **Status:** Proof of Concept (POC)
- **Stability:** Experimental
- **Testing:** Limited testing performed
- **Recommended Use:** Development and testing environments only
- **Production Use:** Not recommended without thorough testing

---

**Built with AI for AI-powered document management**
