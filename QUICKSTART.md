# Quick Start Guide

> **⚠️ PROOF OF CONCEPT** - This implementation has not been fully tested. Use at your own risk and test thoroughly before production use.

Get started with the AI Document Classification Pipeline in 5 minutes!

## Prerequisites

1. Install Ollama:
   ```bash
   # macOS
   brew install ollama

   # Linux
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Pull a model:
   ```bash
   ollama pull llama3.2:3b
   ```

3. Start Ollama:
   ```bash
   ollama serve
   ```

## Installation

```bash
# Clone and install
git clone <repo-url>
cd AI_Document_Pipeline
pip install -e .
```

## Basic Usage

### 1. Initialize

```bash
doc-classify init
```

This creates the folder structure:
- `documents/input/` - Place your documents here
- `documents/output/` - Organized documents appear here

### 2. Add Documents

```bash
cp /path/to/your/files/* documents/input/
```

### 3. Classify & Organize

```bash
doc-classify classify documents/input
```

That's it! Your documents are now classified and organized by category.

## Example Output

```
✓ Using model: llama3.2:3b
✓ Categories: invoices, contracts, reports, correspondence, research, compliance, other

Classifying directory: documents/input
Classifying documents: 100%|████████████| 15/15

Successfully classified 15 documents

┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ File                  ┃ Category       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ invoice_001.pdf       │ invoices       │
│ service_contract.docx │ contracts      │
│ q4_report.xlsx        │ reports        │
│ client_email.pdf      │ correspondence │
└───────────────────────┴────────────────┘

Category Distribution:
  • invoices: 5
  • contracts: 3
  • reports: 4
  • correspondence: 3

Organizing files into: documents/output

✓ Organization complete!
  • 15 files moved
  • Manifest created: documents/output/organization_manifest.json
```

## Advanced Usage

### Classify with AI Reasoning

```bash
doc-classify classify documents/input --reasoning
```

### Copy Instead of Move

```bash
doc-classify classify documents/input --copy
```

### Custom Categories

```bash
doc-classify classify documents/input -c "urgent,normal,archive"
```

### Export Results

```bash
doc-classify classify documents/input --export results.json
```

## Advanced Features

### Enable Search (Optional)

For advanced search capabilities:

```bash
# 1. Start PostgreSQL
docker-compose up -d

# 2. Install search dependencies
pip install -r requirements.txt

# 3. Pull embedding model
ollama pull nomic-embed-text

# 4. Configure search in .env
USE_DATABASE=true
DATABASE_URL=postgresql://docuser:devpassword@localhost:5432/documents

# 5. Search documents
doc-classify search "invoice payment"
```

See [SETUP_SEARCH.md](SETUP_SEARCH.md) for complete search setup.

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- **NEW:** [SETUP_SEARCH.md](SETUP_SEARCH.md) - Enable advanced search
- Check [examples/sample_usage.py](examples/sample_usage.py) for Python API examples
- Customize settings in `.env` file
- Try different Ollama models for better accuracy

## Need Help?

- Check service: `doc-classify check`
- View config: `doc-classify config`
- See available models: `ollama list`
- Full docs: [README.md](README.md)

## Common Issues

**Ollama not available?**
```bash
# Start the service
ollama serve
```

**Wrong model?**
```bash
# Check installed models
ollama list

# Pull a model if needed
ollama pull llama3.2:3b
```

**Permission errors?**
```bash
# Use copy mode to preserve originals
doc-classify classify documents/input --copy
```

---

Happy classifying!
