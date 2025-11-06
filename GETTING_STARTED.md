# Getting Started Guide

Welcome to the AI Document Classification Pipeline! This guide will walk you through installation, setup, and your first document classification.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Quick Setup](#quick-setup)
4. [Your First Classification](#your-first-classification)
5. [Understanding the Results](#understanding-the-results)
6. [Next Steps](#next-steps)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

1. **Python 3.9 or later**
   ```bash
   python3 --version
   # Should show 3.9.x or higher
   ```

2. **Ollama** (for local LLM)
   ```bash
   # macOS
   brew install ollama

   # Linux
   curl -fsSL https://ollama.com/install.sh | sh

   # Windows
   # Download from https://ollama.com/download
   ```

3. **Git** (to clone the repository)
   ```bash
   git --version
   ```

### System Requirements

- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 5GB for models and dependencies
- **OS**: macOS, Linux, or Windows (with WSL)

## Installation

### Automated Installation (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd AI_Document_Pipeline

# Run the setup script
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Check Python version
- Verify Ollama installation
- Install Python dependencies
- Set up the directory structure
- Download AI model (optional)

### Manual Installation

If you prefer manual installation:

```bash
# Clone the repository
git clone <repository-url>
cd AI_Document_Pipeline

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .

# Copy environment file
cp .env.example .env
```

## Quick Setup

### 1. Start Ollama Service

In a separate terminal:

```bash
ollama serve
```

Keep this running in the background.

### 2. Download an AI Model

```bash
# Fast model (recommended for most use cases)
ollama pull llama3.2:3b

# More powerful model (better accuracy, slower)
ollama pull llama3.1:8b

# List installed models
ollama list
```

### 3. Verify Installation

```bash
# Check if Ollama is available
doc-classify check

# Expected output:
# ✓ Ollama service is available
# Host: http://localhost:11434
# Model: llama3.2:3b
# Available models:
#   • llama3.2:3b
```

### 4. Initialize Project Structure

```bash
doc-classify init

# This creates:
# documents/input/    - Place documents here
# documents/output/   - Classified documents appear here
# documents/temp/     - Temporary files
```

## Your First Classification

### Step 1: Prepare Sample Documents

Create some test documents or copy existing ones:

```bash
# Example: Create a sample invoice
echo "Invoice #12345
Date: 2025-10-13
Amount: $1,500.00
Service: Consulting Services" > documents/input/invoice.txt

# Example: Create a sample contract
echo "SERVICE AGREEMENT
This agreement is made on October 13, 2025
Between Company A and Company B
Terms and conditions..." > documents/input/contract.txt

# Or copy your existing documents
cp /path/to/your/pdfs/*.pdf documents/input/
```

### Step 2: Run Classification

```bash
# Basic classification
doc-classify classify documents/input
```

You'll see output like:

```
AI Document Classification Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Using model: llama3.2:3b
✓ Categories: invoices, contracts, reports, correspondence, research, compliance, other

Classifying directory: documents/input

Classifying documents: 100%|████████████████| 2/2

Successfully classified 2 documents

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ File             ┃ Category  ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ invoice.txt      │ invoices  │
│ contract.txt     │ contracts │
└──────────────────┴───────────┘

Category Distribution:
  • invoices: 1
  • contracts: 1

Organizing files into: documents/output

✓ Organization complete!
  • 2 files moved
  • Manifest created: documents/output/organization_manifest.json
```

### Step 3: Check Results

```bash
# View organized structure
ls -R documents/output/

# Output:
# documents/output/:
# contracts  invoices  organization_manifest.json
#
# documents/output/contracts:
# contract.txt
#
# documents/output/invoices:
# invoice.txt
```

## Understanding the Results

### Organized Files

Your documents are now organized into category folders:

```
documents/output/
├── invoices/
│   └── invoice.txt
├── contracts/
│   └── contract.txt
└── organization_manifest.json
```

### Manifest File

The manifest contains detailed information:

```json
{
  "timestamp": "2025-10-13T10:30:00",
  "total_files": 2,
  "moved_files": [
    {
      "source": "documents/input/invoice.txt",
      "destination": "documents/output/invoices/invoice.txt",
      "category": "invoices"
    }
  ],
  "category_summary": {
    "invoices": [{"filename": "invoice.txt", "confidence": null}]
  }
}
```

## Next Steps

### Advanced Classification

#### 1. Include AI Reasoning

See why documents were classified:

```bash
doc-classify classify documents/input --reasoning
```

#### 2. Copy Instead of Move

Preserve original files:

```bash
doc-classify classify documents/input --copy
```

#### 3. Custom Categories

Define your own categories:

```bash
doc-classify classify documents/input -c "urgent,normal,archive"
```

#### 4. Export Results

Save results to JSON:

```bash
doc-classify classify documents/input --export results.json
```

#### 5. Process Single File

Classify one document:

```bash
doc-classify classify path/to/document.pdf --no-organize
```

### Using Python API

For programmatic access:

```python
from pathlib import Path
from src.classifier import DocumentClassifier, DocumentOrganizer
from src.ollama_service import OllamaService

# Initialize
ollama = OllamaService()
classifier = DocumentClassifier(ollama_service=ollama)

# Classify
results = classifier.classify_directory(Path("documents/input"))

# Organize
organizer = DocumentOrganizer()
summary = organizer.organize(results)

print(f"Organized {summary['successful']} documents")
```

### Customization

#### Edit Configuration

```bash
# Edit .env file
nano .env

# Modify settings:
OLLAMA_MODEL=llama3.1:8b
CATEGORIES=legal,financial,hr,marketing
MAX_FILE_SIZE_MB=200
```

#### View Current Config

```bash
doc-classify config
```

## Troubleshooting

### Problem: "Ollama service not available"

**Solution:**
```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Problem: "No model found"

**Solution:**
```bash
# Pull a model
ollama pull llama3.2:3b

# Verify installation
ollama list
```

### Problem: "Command 'doc-classify' not found"

**Solution:**
```bash
# Add to PATH or use directly
python -m src.cli classify documents/input

# Or reinstall
pip install -e .
```

### Problem: "Permission denied"

**Solution:**
```bash
# Check file permissions
ls -la documents/input/

# Fix permissions if needed
chmod 644 documents/input/*

# Or use copy mode
doc-classify classify documents/input --copy
```

### Problem: Classification seems inaccurate

**Solutions:**
1. Use a larger model:
   ```bash
   ollama pull llama3.1:8b
   ```
   Then update `.env`: `OLLAMA_MODEL=llama3.1:8b`

2. Check document content:
   ```bash
   # View what was extracted
   doc-classify classify document.pdf --reasoning -v
   ```

3. Refine categories:
   ```bash
   # More specific categories work better
   doc-classify classify docs/ -c "sales_invoices,purchase_orders,receipts"
   ```

### Problem: Processing very slow

**Solutions:**
1. Use smaller model:
   ```bash
   ollama pull llama3.2:1b
   ```

2. Limit file size in `.env`:
   ```
   MAX_FILE_SIZE_MB=50
   ```

3. Process in smaller batches:
   ```bash
   # Process 10 files at a time
   ls documents/input/*.pdf | head -10 | xargs -I {} doc-classify classify {}
   ```

## Learning Resources

### Documentation

- **[README.md](README.md)** - Comprehensive documentation
- **[QUICKSTART.md](QUICKSTART.md)** - Quick reference guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture details
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Project overview

### Examples

- **[examples/sample_usage.py](examples/sample_usage.py)** - Python API examples

### Commands Reference

```bash
# Initialize
doc-classify init [--categories TEXT]

# Check setup
doc-classify check [--host TEXT] [--model TEXT]

# Classify documents
doc-classify classify INPUT_PATH [OPTIONS]
  -o, --output PATH       Output directory
  -c, --categories TEXT   Categories list
  --copy                  Copy instead of move
  --reasoning             Include AI reasoning
  --no-organize           Only classify, don't organize
  --export PATH           Export to JSON
  -v, --verbose           Verbose output

# View configuration
doc-classify config
```

## Getting Help

### Built-in Help

```bash
# General help
doc-classify --help

# Command-specific help
doc-classify classify --help
```

### Community Support

- Open an issue on GitHub
- Check existing issues for solutions
- Consult Ollama documentation: https://ollama.com/docs

## What's Next?

Now that you're set up, explore these use cases:

1. **Office Documents**: Sort emails, memos, and reports
2. **Financial Records**: Organize invoices, receipts, and statements
3. **Legal Documents**: Classify contracts, agreements, and filings
4. **Research Papers**: Categorize academic papers and articles
5. **Personal Archives**: Organize personal documents and files

### Experiment with:

- Different Ollama models
- Custom category schemes
- Batch processing workflows
- Integration with existing systems

---

**Ready to classify?** Start with: `doc-classify classify documents/input`

**Questions?** Check the [README.md](README.md) or open an issue.

**Happy Classifying! 🚀**
