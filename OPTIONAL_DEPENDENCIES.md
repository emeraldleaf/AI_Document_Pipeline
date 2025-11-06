# Optional Dependencies

This document explains the optional dependencies in the AI Document Pipeline and why they are structured this way.

## Philosophy

The pipeline is designed with a **POC → Production** migration path:

1. **POC (Proof of Concept)**: Use free, local tools (Ollama)
2. **Production**: Upgrade to cloud services (OpenAI, AWS, etc.)

This means some dependencies are **optional** and only required for production deployments.

## Core Dependencies (Required)

These are installed with `pip install -r requirements.txt`:

```
✅ Document processing: PyPDF2, python-docx, openpyxl, etc.
✅ OCR: Pillow, pytesseract, pdf2image
✅ Ollama: ollama, requests
✅ Database: sqlalchemy, psycopg2-binary
✅ CLI: click, rich
```

## Optional Dependencies

### OpenAI SDK (`openai`)

**When needed:**
- Production deployments using OpenAI embeddings
- When `EMBEDDING_PROVIDER=openai` in `.env`

**When NOT needed:**
- Local/POC development with Ollama embeddings (default)
- When `EMBEDDING_PROVIDER=ollama` in `.env`

**Install:**
```bash
pip install openai
```

**Why optional:**
- Most users start with free Ollama embeddings
- OpenAI requires API key and costs money
- POC shouldn't require paid services
- Easy to add later when migrating to production

### How It Works

The code uses **lazy imports** to handle optional dependencies:

```python
# src/embedding_service.py

class OpenAIEmbeddingService:
    def __init__(self, api_key: str, ...):
        # Only import when this class is instantiated
        try:
            import openai  # type: ignore[import-not-found]
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            raise
```

Benefits:
- ✅ No import errors if using Ollama only
- ✅ Clear error message if OpenAI is needed but not installed
- ✅ Type checkers know this is intentional (`type: ignore`)
- ✅ Minimal dependencies for POC users

## IDE Warnings

### Pylance: "Import 'openai' could not be resolved"

**This is expected!** The import only happens at runtime when needed.

**Fix the warning:**
1. Suppress with `# type: ignore[import-not-found]` (already done)
2. Or install openai: `pip install openai` (if you plan to use it)
3. Or ignore (the code works correctly)

### Codacy: "OpenAI SDK imported without Guardrails"

**This is a security suggestion**, not an error.

[Guardrails](https://www.guardrailsai.com/) is a library that adds security checks to LLM interactions.

**For this project:**
- ❌ Not needed for POC
- ⚠️ Consider for production with sensitive data
- 📚 Optional security enhancement

**To use Guardrails (optional):**
```bash
pip install guardrails-ai
```

Then change the import:
```python
from guardrails import GuardrailsOpenAI
client = GuardrailsOpenAI(api_key=api_key)
```

## Requirements.txt Structure

```ini
# requirements.txt

# Core dependencies (always required)
python-dotenv==1.0.0
pydantic==2.5.0
# ... etc

# Database (Required for search)
sqlalchemy==2.0.23
psycopg2-binary==2.9.9

# Optional dependencies (commented out)
# openai==1.12.0  # Uncomment for OpenAI embeddings
```

## Development Workflow

### Local Development (Default)

```bash
# Install core dependencies
pip install -r requirements.txt

# Use Ollama embeddings (free)
EMBEDDING_PROVIDER=ollama
```

No additional packages needed!

### Production Deployment

```bash
# Install core dependencies
pip install -r requirements.txt

# Install OpenAI for production embeddings
pip install openai

# Configure for OpenAI
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
```

### Testing Both Providers

```bash
# Install both
pip install -r requirements.txt
pip install openai

# Switch via config
# POC: EMBEDDING_PROVIDER=ollama
# Prod: EMBEDDING_PROVIDER=openai
```

## Adding More Optional Dependencies

When adding new optional features:

1. **Keep them optional** in requirements.txt (commented)
2. **Use lazy imports** in the code
3. **Handle ImportError** with clear messages
4. **Document** in this file

Example:
```python
class MyOptionalService:
    def __init__(self):
        try:
            import optional_package  # type: ignore[import-not-found]
            self.client = optional_package.Client()
        except ImportError:
            logger.error(
                "optional_package not installed. "
                "Install with: pip install optional_package"
            )
            raise
```

## Configuration Matrix

| Feature | Required Packages | Config |
|---------|------------------|---------|
| **Classification** | ollama, requests | OLLAMA_MODEL=llama3.2:3b |
| **Database/Search** | sqlalchemy, psycopg2-binary | DATABASE_URL=postgresql://... |
| **Ollama Embeddings** | (built-in) | EMBEDDING_PROVIDER=ollama |
| **OpenAI Embeddings** | openai | EMBEDDING_PROVIDER=openai |
| **OCR** | pytesseract, Pillow | (automatic) |

## Summary

✅ **Core dependencies**: Required for basic functionality
⚠️ **Optional dependencies**: Only needed for specific features
🔧 **Lazy imports**: Load only when needed
📝 **Clear errors**: Tell users what to install

This design allows:
- Fast setup for POC users
- Easy migration to production
- Minimal dependencies by default
- Clear upgrade path

## References

- **Embedding Service**: [src/embedding_service.py](src/embedding_service.py)
- **Configuration**: [.env.example](.env.example)
- **Setup Guide**: [SETUP_SEARCH.md](SETUP_SEARCH.md)
- **Cloud Migration**: [CLOUD_MIGRATION.md](CLOUD_MIGRATION.md)

---

**Questions about dependencies?** Check if the feature you need is POC (free, local) or Production (paid, cloud).
