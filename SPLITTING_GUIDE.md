# Document Splitting Guide

The AI Document Classification Pipeline supports **optional document splitting** for classifying pages, sections, or chunks independently. This is perfect for multi-format documents where different parts belong to different categories.

## Table of Contents

1. [Overview](#overview)
2. [When to Use Splitting](#when-to-use-splitting)
3. [Split Modes](#split-modes)
4. [Quick Start](#quick-start)
5. [CLI Usage](#cli-usage)
6. [Python API](#python-api)
7. [Use Cases](#use-cases)
8. [Best Practices](#best-practices)

---

## Overview

### Default Behavior (No Splitting)

By default, the system treats each document as a single unit:

```
document.pdf → Extract → Classify → Organize
```

**Result**: Entire document gets one category.

### With Splitting

When enabled, documents are split into sections, each classified independently:

```
document.pdf → Extract → Split → Classify Each Section → Organize
```

**Result**: Each section can have a different category.

---

## When to Use Splitting

### ✅ Use Splitting When:

1. **Mixed-Format Documents**
   - PDF with different page types (invoices + contracts)
   - Scanned documents with multiple originals
   - Reports with varied sections

2. **Large Documents**
   - Multi-page reports with different topics
   - Compiled documents (multiple docs in one file)
   - Books or manuals with chapters

3. **Page-Level Classification**
   - Need to extract specific pages
   - Want to separate document types within one file
   - Compliance requirements for page-level tracking

### ❌ Don't Use Splitting When:

1. **Uniform Documents**
   - Single-topic documents
   - Consistent format throughout
   - Already pre-separated files

2. **Small Documents**
   - 1-2 page documents
   - Simple memos or letters
   - Single invoices/forms

---

## Split Modes

### 1. `none` (Default)

**No splitting** - process entire document as one unit.

```bash
doc-classify classify documents/input
# or explicitly
doc-classify classify documents/input --split none
```

**Use when**: Documents are already single-purpose.

---

### 2. `pages`

**Page-by-page classification** - each PDF page classified independently.

```bash
doc-classify classify documents/input --split pages
```

**How it works**:
- Extracts each page as separate content
- Classifies each page individually
- Perfect for mixed PDFs

**Example**:
```
multi_doc.pdf (10 pages)
  Page 1-3: invoices
  Page 4-6: contracts
  Page 7-10: reports

Result: 3 separate classifications
```

**Use when**:
- Scanned multi-document PDFs
- Each page is a different document type
- Need page-level granularity

---

### 3. `sections`

**Section-based classification** - splits by headings/sections.

```bash
doc-classify classify documents/input --split sections
```

**How it works**:
- Detects section headers (UPPERCASE, ends with :, etc.)
- Splits document at section boundaries
- Classifies each section

**Example**:
```
report.pdf
  EXECUTIVE SUMMARY → reports
  FINANCIAL STATEMENTS → invoices
  LEGAL DISCLAIMER → contracts

Result: 3 classifications per section
```

**Use when**:
- Documents with clear section headers
- Reports with mixed content types
- Structured documents

---

### 4. `chunks`

**Fixed-size chunks** - splits into consistent chunks with overlap.

```bash
doc-classify classify documents/input --split chunks
```

**How it works**:
- Splits by character count (default: 2000 chars)
- Overlaps between chunks (default: 200 chars)
- Tries to break at sentence boundaries

**Configuration**:
```ini
# .env
CHUNK_SIZE=2000
CHUNK_OVERLAP=200
```

**Use when**:
- Very large documents
- Need consistent chunk sizes
- Processing for embeddings/search

---

### 5. `smart`

**Intelligent splitting** - automatically chooses best method.

```bash
doc-classify classify documents/input --split smart
```

**How it works**:
1. Analyzes document structure
2. Checks for page variance (PDF)
3. Looks for section markers
4. Falls back to appropriate mode

**Decision logic**:
- High page variance → `pages` mode
- Clear section markers → `sections` mode
- Very large document → `chunks` mode
- Otherwise → `none` (full document)

**Use when**:
- Unsure which mode to use
- Processing diverse document types
- Want automatic optimization

---

## Quick Start

### Enable Splitting in Config

Edit `.env`:

```ini
# Document Splitting Options
SPLIT_DOCUMENTS=pages      # or: none, sections, chunks, smart
CHUNK_SIZE=2000           # For chunk mode
CHUNK_OVERLAP=200         # Overlap between chunks
MIN_SECTION_SIZE=100      # Minimum section size (chars)
```

### Use from CLI

```bash
# Page-level classification
doc-classify classify mixed_docs.pdf --split pages

# Section-based classification
doc-classify classify report.pdf --split sections

# Smart mode (automatic)
doc-classify classify documents/input --split smart
```

---

## CLI Usage

### Basic Commands

```bash
# No splitting (default)
doc-classify classify documents/input

# Page-level
doc-classify classify scanned.pdf --split pages

# Section-based
doc-classify classify report.docx --split sections

# Fixed chunks
doc-classify classify large_doc.pdf --split chunks

# Smart mode
doc-classify classify documents/input --split smart
```

### With Other Options

```bash
# Splitting + reasoning
doc-classify classify docs.pdf --split pages --reasoning

# Splitting + custom categories
doc-classify classify docs.pdf --split pages -c "type1,type2,type3"

# Splitting + export results
doc-classify classify docs.pdf --split pages --export results.json

# Splitting + copy (don't move)
doc-classify classify docs.pdf --split pages --copy
```

---

## Python API

### Basic Usage

```python
from pathlib import Path
from src.classifier import DocumentClassifier
from src.splitter import DocumentSplitter, SplitMode

# Initialize splitter
splitter = DocumentSplitter(
    split_mode=SplitMode.PAGES,
    chunk_size=2000,
    chunk_overlap=200
)

# Classify with splitting
classifier = DocumentClassifier()

# The classifier will use splitter if configured
# (Split mode from config.py settings.split_documents)
results = classifier.classify_directory(Path("documents/input"))
```

### Advanced Usage

```python
from src.splitter import (
    DocumentSplitter,
    SplitMode,
    SectionClassificationResult,
    merge_section_results
)
from src.extractors import ExtractionService
from src.ollama_service import OllamaService

# Extract document
extractor = ExtractionService()
extracted = extractor.extract(Path("mixed_doc.pdf"))

# Split into sections
splitter = DocumentSplitter(split_mode=SplitMode.PAGES)
sections = splitter.split(extracted)

print(f"Split into {len(sections)} sections")

# Classify each section
ollama = OllamaService()
section_results = []

for section in sections:
    category = ollama.classify_document(
        content=section.content,
        metadata=section.metadata,
        categories=["invoices", "contracts", "reports"]
    )
    section_results.append((section, category, None))

# Analyze results
result = SectionClassificationResult(
    file_path=Path("mixed_doc.pdf"),
    sections=section_results
)

print(f"Is mixed document: {result.is_mixed}")
print(f"Category distribution: {result.get_category_distribution()}")
print(f"Dominant category: {result.dominant_category}")

# Get sections by category
invoices = result.get_sections_by_category("invoices")
print(f"Found {len(invoices)} invoice sections")
```

### Custom Splitting Logic

```python
from src.splitter import DocumentSplitter, DocumentSection

class CustomSplitter(DocumentSplitter):
    """Custom splitting logic."""

    def custom_split(self, extracted):
        """Split by your custom logic."""
        sections = []

        # Example: Split by a specific pattern
        text = extracted.text
        parts = text.split("--- NEW DOCUMENT ---")

        for i, part in enumerate(parts):
            if part.strip():
                section = DocumentSection(
                    content=part.strip(),
                    section_number=i + 1,
                    section_type="custom",
                    metadata=extracted.metadata.to_dict()
                )
                sections.append(section)

        return sections

# Use custom splitter
splitter = CustomSplitter()
sections = splitter.custom_split(extracted)
```

---

## Use Cases

### 1. Mixed Scanned Documents

**Problem**: Scanned PDF with invoices, contracts, and reports.

**Solution**:
```bash
doc-classify classify scanned_batch.pdf --split pages
```

**Result**:
- Pages 1-5 → invoices/
- Pages 6-10 → contracts/
- Pages 11-15 → reports/

---

### 2. Multi-Section Reports

**Problem**: Report with financial, legal, and operational sections.

**Solution**:
```bash
doc-classify classify annual_report.pdf --split sections
```

**Result**:
- Executive Summary → reports/summary/
- Financial Statements → reports/financial/
- Legal Notices → contracts/legal/

---

### 3. Compiled Document Archives

**Problem**: Single PDF containing multiple historical documents.

**Solution**:
```bash
doc-classify classify archive_2024.pdf --split smart
```

**Result**: Automatically detects best split method and organizes.

---

### 4. Large Research Papers

**Problem**: 100-page research paper needs to be indexed.

**Solution**:
```bash
doc-classify classify thesis.pdf --split chunks
```

**Result**: Split into 50 chunks for easier processing/indexing.

---

## Best Practices

### 1. Choose the Right Mode

| Document Type | Recommended Mode |
|---------------|------------------|
| Mixed scans | `pages` |
| Structured reports | `sections` |
| Very large docs | `chunks` |
| Unknown/varied | `smart` |
| Uniform docs | `none` (default) |

### 2. Configure Chunk Sizes

```ini
# For detailed analysis
CHUNK_SIZE=1000
CHUNK_OVERLAP=100

# For efficient processing
CHUNK_SIZE=3000
CHUNK_OVERLAP=300
```

### 3. Handle Mixed Results

```python
# Check if document is mixed
if result.is_mixed:
    print("Mixed document detected!")
    print(f"Distribution: {result.get_category_distribution()}")

    # Organize by dominant category
    print(f"Primary category: {result.dominant_category}")

    # Or organize sections separately
    for category in result.get_category_distribution():
        sections = result.get_sections_by_category(category)
        # Save sections to category folder
```

### 4. Minimum Section Size

Set minimum size to avoid tiny sections:

```ini
# Ignore sections smaller than 100 characters
MIN_SECTION_SIZE=100
```

### 5. Database Integration

When using splitting with database:

```python
# Each section can be stored separately
for section, category, confidence in section_results:
    db.add_document(
        file_path=Path(f"{original_file}_section_{section.section_number}"),
        category=category,
        content=section.content,
        metadata=section.metadata,
        confidence=confidence
    )
```

---

## Performance Considerations

### Processing Time

- **No splitting**: ~2-5 seconds per document
- **Page splitting**: ~2-5 seconds × number of pages
- **Section splitting**: ~2-5 seconds × number of sections
- **Chunk splitting**: ~2-5 seconds × number of chunks

### Memory Usage

- **No splitting**: Minimal (single document in memory)
- **With splitting**: Higher (multiple sections in memory)
- **Recommendation**: Process large batches sequentially

### Optimization Tips

```python
# Process sections in batches
batch_size = 10

for i in range(0, len(sections), batch_size):
    batch = sections[i:i + batch_size]
    # Process batch
    # Clear memory if needed
```

---

## Troubleshooting

### No Sections Detected

**Problem**: Section mode returns single document.

**Solution**:
- Check if document has clear section markers
- Try `pages` mode instead
- Use `smart` mode to auto-detect

### Too Many Small Sections

**Problem**: Hundreds of tiny sections created.

**Solution**:
```ini
# Increase minimum section size
MIN_SECTION_SIZE=500
```

### Wrong Split Points

**Problem**: Document split at wrong locations.

**Solution**:
- Try different split mode
- Implement custom splitter
- Pre-process document to add markers

---

## Examples

### Example 1: Process Mixed PDF

```bash
# Input: mixed_documents.pdf (20 pages)
# - Pages 1-10: Invoices
# - Pages 11-15: Contracts
# - Pages 16-20: Reports

doc-classify classify mixed_documents.pdf --split pages --reasoning

# Output:
# invoices/mixed_documents_page_1.pdf
# invoices/mixed_documents_page_2.pdf
# ...
# contracts/mixed_documents_page_11.pdf
# ...
# reports/mixed_documents_page_16.pdf
```

### Example 2: Structured Report

```python
from pathlib import Path
from src.classifier import DocumentClassifier
from src.splitter import SplitMode

# Configure
classifier = DocumentClassifier()
classifier.split_mode = SplitMode.SECTIONS

# Classify
result = classifier.classify_document(
    Path("structured_report.pdf"),
    include_reasoning=True
)

# Analyze
if result.is_mixed:
    print("Sections found:")
    for section, category, confidence in result.sections:
        print(f"  {section.heading}: {category}")
```

---

## Next Steps

- **Getting Started**: See [GETTING_STARTED.md](GETTING_STARTED.md)
- **Full Documentation**: See [README.md](README.md)
- **Database Guide**: See [DATABASE_GUIDE.md](DATABASE_GUIDE.md)
- **API Reference**: See [src/splitter.py](src/splitter.py)

---

**Questions?** Check the main documentation or open an issue on GitHub.
