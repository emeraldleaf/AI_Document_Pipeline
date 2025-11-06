"""
==============================================================================
CONFIGURATION MANAGEMENT - Application Settings
==============================================================================

PURPOSE:
    Centralized configuration for the entire document classification pipeline.
    All settings in one place, loaded from environment variables or .env file.

WHAT IS CONFIGURATION MANAGEMENT?
    - Single source of truth for all settings
    - Environment-based configuration (dev, staging, prod)
    - Type-safe settings with validation
    - Default values with override capability

WHY PYDANTIC SETTINGS?
    Traditional approach (BAD):
    ```python
    import os
    HOST = os.getenv("OLLAMA_HOST", "localhost")  # String (no validation)
    PORT = int(os.getenv("PORT", "11434"))        # Manual conversion
    DEBUG = os.getenv("DEBUG", "false") == "true" # Error-prone
    ```

    Pydantic Settings (GOOD):
    ```python
    class Settings(BaseSettings):
        ollama_host: str = "http://localhost:11434"  # Type-safe
        port: int = 11434                             # Auto-conversion
        debug: bool = False                           # Proper boolean
    ```

    Benefits:
    ✓ Type validation (catches errors early)
    ✓ Auto-conversion (str → int, str → bool, etc.)
    ✓ Default values (fallback if not set)
    ✓ Documentation (types show expected values)
    ✓ IDE autocomplete (knows what settings exist)

CONFIGURATION SOURCES (Priority Order):
    1. Environment variables (highest priority)
       export OLLAMA_MODEL="llama3.2:latest"

    2. .env file
       OLLAMA_MODEL=llama3.2:latest

    3. Default values in this file (lowest priority)
       ollama_model: str = "llama3.2:3b"

EXAMPLE .env FILE:
    ```
    # Ollama Configuration
    OLLAMA_HOST=http://localhost:11434
    OLLAMA_MODEL=llama3.2:3b

    # Paths
    INPUT_FOLDER=./documents/input
    OUTPUT_FOLDER=./documents/output

    # Categories (comma-separated)
    CATEGORIES=invoices,contracts,reports,other

    # Database (optional)
    USE_DATABASE=false
    DATABASE_URL=postgresql://user:pass@localhost:5432/docs
    ```

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │                  Configuration Flow                          │
    │                                                              │
    │  Environment Variables (.env file or shell)                 │
    │           ↓                                                  │
    │  Pydantic Settings (validates, converts types)              │
    │           ↓                                                  │
    │  settings object (globally accessible)                      │
    │           ↓                                                  │
    │  Used by: classifier, services, extractors, etc.            │
    └─────────────────────────────────────────────────────────────┘

KEY CONCEPTS:
    1. **Settings Class**: Defines all configuration
    2. **BaseSettings**: Pydantic base class for env loading
    3. **Type Hints**: Define expected types (validated)
    4. **Default Values**: Fallback if not in environment
    5. **Properties**: Computed values (e.g., list from CSV string)
    6. **Global Instance**: Singleton settings object

USAGE EXAMPLE:
    ```python
    from config import settings

    # Access settings
    print(settings.ollama_model)  # "llama3.2:3b"
    print(settings.category_list)  # ["invoices", "contracts", ...]

    # Settings are type-safe
    if settings.use_database:
        db = DatabaseService(settings.database_url)

    # Create necessary directories
    settings.ensure_directories()
    ```

DEVELOPMENT VS PRODUCTION:
    Development (.env):
        USE_DATABASE=false
        LOG_LEVEL=DEBUG
        OLLAMA_HOST=http://localhost:11434

    Production (.env):
        USE_DATABASE=true
        LOG_LEVEL=INFO
        OLLAMA_HOST=http://ollama.production.com
        DATABASE_URL=postgresql://prod-user:***@prod-db:5432/docs

RELATED FILES:
    - .env - Environment variables (not in git)
    - .env.example - Example configuration (in git)
    - src/classifier.py - Uses settings
    - src/ollama_service.py - Uses settings

AUTHOR: AI Document Pipeline Team
LAST UPDATED: October 2025
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


# ==============================================================================
# SETTINGS CLASS (Application Configuration)
# ==============================================================================

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    WHAT IT IS:
        Central configuration object for the entire application.
        All settings in one place, type-safe, with validation.

    HOW IT WORKS:
        1. Define settings as class attributes with types
        2. Pydantic loads from environment variables
        3. Falls back to default values if not set
        4. Validates types (catches errors early)

    LOADING PRIORITY:
        1. Environment variables (export VAR=value)
        2. .env file (VAR=value)
        3. Default values (defined below)

    TYPE CONVERSION:
        Pydantic automatically converts:
        - "true"/"false" → bool
        - "123" → int
        - "1.5" → float
        - "./path" → Path
        - "a,b,c" → str (use @property for List)

    USAGE:
        >>> from config import settings
        >>> print(settings.ollama_model)
        llama3.2:3b
        >>> print(settings.category_list)
        ['invoices', 'contracts', 'reports', ...]

    Why BaseSettings?
        - Loads from environment automatically
        - Validates types
        - Provides defaults
        - Supports .env files
        - Thread-safe singleton pattern
    """

    # ==========================================================================
    # OLLAMA CONFIGURATION (AI Service)
    # ==========================================================================

    ollama_host: str = "http://localhost:11434"
    """
    Ollama service URL.

    Default: http://localhost:11434 (local installation)

    Examples:
        - Local: http://localhost:11434
        - Docker: http://ollama:11434
        - Remote: http://ollama.mycompany.com:11434

    Why needed?
        - All AI classification goes through Ollama
        - Must be running and accessible
        - Check with: ollama list
    """

    ollama_model: str = "llama3.2:3b"
    """
    Ollama model name for classification.

    Default: llama3.2:3b (small, fast, good accuracy)

    Available models (download with: ollama pull MODEL):
        - llama3.2:3b (3 billion params) - Fast, good for most docs
        - llama3.2:13b (13 billion params) - Slower, better accuracy
        - mistral:latest - Alternative, similar performance
        - llama3.1:latest - Previous version

    Trade-offs:
        Smaller models (3b):
        + Faster classification (2-5 seconds/doc)
        + Lower memory usage (~4GB RAM)
        - Slightly lower accuracy

        Larger models (13b):
        - Slower classification (5-15 seconds/doc)
        - Higher memory usage (~16GB RAM)
        + Better accuracy, especially edge cases

    Recommendation:
        - Development: llama3.2:3b (fast iteration)
        - Production: Test both, choose based on accuracy needs
    """

    # ==========================================================================
    # DOCUMENT PROCESSING PATHS
    # ==========================================================================

    input_folder: Path = Path("./documents/input")
    """
    Where to find documents to classify.

    Default: ./documents/input

    Structure:
        documents/input/
            invoice_001.pdf
            contract_002.pdf
            report_003.docx

    Processing:
        - All files in this folder will be classified
        - Supports subdirectories if process_subdirectories=True
        - Original files preserved (unless moved by organizer)
    """

    output_folder: Path = Path("./documents/output")
    """
    Where to organize classified documents.

    Default: ./documents/output

    Structure after classification:
        documents/output/
            invoices/
                invoice_001.pdf
            contracts/
                contract_002.pdf
            reports/
                report_003.docx

    Behavior:
        - Creates category folders automatically
        - Files moved/copied here by DocumentOrganizer
        - Can be same as input_folder (organize in place)
    """

    temp_folder: Path = Path("./documents/temp")
    """
    Temporary storage for processing.

    Default: ./documents/temp

    Used for:
        - OCR intermediate files
        - Extraction temporary files
        - Can be cleared periodically

    Note: Not heavily used in current implementation
    """

    # ==========================================================================
    # CLASSIFICATION CATEGORIES
    # ==========================================================================

    categories: str = "invoices,contracts,reports,correspondence,research,compliance,other"
    """
    Comma-separated list of document categories.

    Default: invoices,contracts,reports,correspondence,research,compliance,other

    These are the categories the AI can assign to documents.

    Guidelines for choosing categories:
        - Clear and distinct (avoid overlap)
        - Meaningful to your organization
        - Not too many (5-10 is good, 20+ gets confusing)
        - Include "other" for edge cases

    Examples by use case:
        Legal firm:
            "contracts,correspondence,filings,evidence,research,other"

        Accounting:
            "invoices,receipts,statements,reports,tax_documents,other"

        Research:
            "papers,datasets,notes,presentations,reviews,other"

    Why string (not list)?
        - Environment variables are strings
        - Easy to set: export CATEGORIES="cat1,cat2,cat3"
        - Converted to list by category_list property
    """

    # ==========================================================================
    # PROCESSING OPTIONS
    # ==========================================================================

    max_file_size_mb: int = 100
    """
    Maximum file size to process (in megabytes).

    Default: 100 MB

    Files larger than this will be skipped.

    Why limit?
        - Very large files slow down processing
        - Can cause memory issues
        - OCR on 1000-page PDFs takes forever

    Typical file sizes:
        - Invoice PDF: 0.5-2 MB
        - Contract: 1-5 MB
        - Report with images: 5-20 MB
        - Scanned archive: 50-200 MB

    Recommendation:
        - Most documents: 50-100 MB
        - Large archives: 500 MB (warning: slow!)
        - Production: 100 MB is safe
    """

    process_subdirectories: bool = True
    """
    Whether to process subdirectories recursively.

    Default: True (process all subdirectories)

    True:
        input/
            doc1.pdf          ← Processed
            folder1/
                doc2.pdf      ← Processed
                subfolder/
                    doc3.pdf  ← Processed

    False:
        input/
            doc1.pdf          ← Processed
            folder1/
                doc2.pdf      ← Skipped

    When to use False?
        - Flat directory structure
        - Want to control which folders to process
        - Testing specific subset
    """

    preserve_original_structure: bool = False
    """
    Preserve original directory structure in output.

    Default: False (organize by category only)

    False (default):
        output/
            invoices/
                doc1.pdf
                doc2.pdf

    True:
        output/
            invoices/
                2024/
                    Q1/
                        doc1.pdf
                2023/
                    doc2.pdf

    Note: Not fully implemented in current version
    """

    # ==========================================================================
    # LOGGING CONFIGURATION
    # ==========================================================================

    log_level: str = "INFO"
    """
    Logging level for application output.

    Default: INFO

    Levels (least to most verbose):
        - ERROR: Only errors
        - WARNING: Errors + warnings
        - INFO: Errors + warnings + info (recommended)
        - DEBUG: Everything (very verbose, for debugging)

    What you'll see at each level:
        INFO:
            - "Classifying: invoice_001.pdf"
            - "Successfully classified 45/50 documents"
            - "Exported results to results.json"

        DEBUG:
            - Everything from INFO
            - "Extracted 523 characters from invoice_001.pdf"
            - "Ollama response: {...}"
            - "Database query: INSERT INTO..."

    Recommendation:
        - Development: DEBUG (see everything)
        - Production: INFO (enough detail, not overwhelming)
        - Production issues: DEBUG (temporarily, for troubleshooting)
    """

    # ==========================================================================
    # DATABASE CONFIGURATION (Optional)
    # ==========================================================================

    use_database: bool = False
    """
    Enable database storage for documents.

    Default: False (database is optional)

    What database stores:
        - Extracted text content
        - Classification results
        - Metadata (file info, dates)
        - Vector embeddings (for semantic search)
        - Processing history

    Benefits of database:
        ✓ Persistence (results survive across runs)
        ✓ Search (find documents by content)
        ✓ Analytics (query patterns, statistics)
        ✓ Audit trail (track changes)
        ✓ Semantic search (find similar documents)

    Requirements:
        - PostgreSQL 12+ with pgvector extension
        - SQLAlchemy installed
        - Database created and accessible

    Setup:
        1. Install PostgreSQL
        2. Install pgvector extension
        3. Create database
        4. Set DATABASE_URL
        5. Set USE_DATABASE=true

    When to enable:
        - Need document search
        - Want to track history
        - Building document management system
        - Multiple users/systems access docs

    When to skip:
        - Simple batch classification
        - Just organizing files
        - Don't need search
        - Simpler is better
    """

    database_url: str = "postgresql://docuser:devpassword@localhost:5432/documents"
    """
    PostgreSQL database connection URL.

    Default: postgresql://docuser:devpassword@localhost:5432/documents

    Format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE

    Examples:
        Local:
            postgresql://docuser:devpassword@localhost:5432/documents

        Docker:
            postgresql://docuser:devpassword@postgres:5432/documents

        Production:
            postgresql://prod_user:***@db.company.com:5432/prod_docs

    Security:
        - NEVER commit real passwords to git
        - Use .env file (add to .gitignore)
        - Use environment variables in production
        - Consider connection pooling for production
    """

    store_full_content: bool = True
    """
    Store full document content in database.

    Default: True (store everything)

    True:
        - Full text stored in database
        - Enables full-text search
        - Uses more storage
        - Search is faster (no need to read files)

    False:
        - Only store metadata + embeddings
        - Less storage
        - Search returns file paths (must read files)
        - Good if files are on fast storage

    Storage impact:
        - Average document: 10-50 KB text
        - 10,000 documents: 100-500 MB
        - With embeddings: +50% (150-750 MB)

    Recommendation:
        - Most cases: True (convenience > storage cost)
        - Huge archives (millions of docs): False (save storage)
    """

    # ==========================================================================
    # EMBEDDING CONFIGURATION (Semantic Search)
    # ==========================================================================

    embedding_provider: str = "ollama"
    """
    Provider for text embeddings (vector representations).

    Default: ollama (local, free)

    Options:
        - ollama: Local, free, good quality
        - openai: Cloud, paid, excellent quality

    What are embeddings?
        - Vector representation of text (array of numbers)
        - Similar texts have similar vectors
        - Enables semantic search ("find similar documents")

    Comparison:
        Ollama (nomic-embed-text):
        + Free
        + Local (private)
        + Good quality
        - Slower than OpenAI

        OpenAI (text-embedding-3-small):
        + Excellent quality
        + Fast
        - Costs money ($0.02 per 1M tokens)
        - Requires API key
        - Sends data to OpenAI
    """

    embedding_model: str = "nomic-embed-text"
    """
    Model name for generating embeddings.

    Default: nomic-embed-text (Ollama)

    Ollama models:
        - nomic-embed-text: Best for documents (recommended)
        - mxbai-embed-large: Alternative

    OpenAI models:
        - text-embedding-3-small: Good balance
        - text-embedding-3-large: Best quality
        - text-embedding-ada-002: Legacy

    Download (Ollama):
        ollama pull nomic-embed-text
    """

    embedding_dimension: int = 768
    """
    Dimension of embedding vectors.

    Default: 768 (nomic-embed-text)

    Different models have different dimensions:
        - nomic-embed-text: 768
        - text-embedding-3-small: 1536
        - text-embedding-3-large: 3072

    Why it matters:
        - Must match model's output
        - Database vector column must match
        - More dimensions = more precision, more storage

    Note: Don't change unless changing model
    """

    openai_api_key: str = ""
    """
    OpenAI API key (only needed if using OpenAI embeddings).

    Default: "" (not set)

    Get from: https://platform.openai.com/api-keys

    Example:
        export OPENAI_API_KEY="sk-proj-..."

    Security:
        - NEVER commit to git
        - Use environment variables
        - Rotate periodically
        - Limit permissions to embeddings only
    """

    # ==========================================================================
    # DOCUMENT SPLITTING (Advanced)
    # ==========================================================================

    split_documents: str = "none"
    """
    How to split documents for processing.

    Default: none (process entire document)

    Options:
        - none: Whole document (default, recommended)
        - pages: One entry per page
        - sections: Split by headings/sections
        - chunks: Fixed-size chunks
        - smart: Intelligent splitting (paragraphs, etc.)

    Why split?
        - Very long documents (100+ pages)
        - Want page-level search
        - Improve search relevance

    Why not split (default)?
        - Simpler
        - Better for classification (sees full context)
        - Faster processing
        - Most documents are <20 pages

    When to enable:
        - Building search system
        - Long technical documents
        - Want to cite specific pages
    """

    chunk_size: int = 2000
    """
    Characters per chunk (for chunks mode).

    Default: 2000 characters (~400 words)

    Trade-offs:
        Small chunks (500-1000):
        + More precise search results
        + Lower memory per chunk
        - More chunks to process
        - May lose context

        Large chunks (3000-5000):
        + Better context
        + Fewer chunks
        - Less precise results
        - More memory

    Typical documents:
        - 2000 chars = ~1 page of text
        - 10-page doc = ~5 chunks
    """

    chunk_overlap: int = 200
    """
    Character overlap between chunks.

    Default: 200 characters

    Why overlap?
        - Prevents cutting sentences/paragraphs in half
        - Maintains context across chunks
        - Important information near boundaries not lost

    Example with overlap=200:
        Chunk 1: chars 0-2000
        Chunk 2: chars 1800-3800  (200 overlap with chunk 1)
        Chunk 3: chars 3600-5600  (200 overlap with chunk 2)
    """

    min_section_size: int = 100
    """
    Minimum section size (for sections mode).

    Default: 100 characters

    Sections smaller than this are merged with adjacent sections.

    Why?
        - Avoid tiny sections (headers only, single sentences)
        - Each section needs enough context
    """

    # ==========================================================================
    # PYDANTIC CONFIGURATION
    # ==========================================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    """
    Pydantic settings configuration.

    What this does:
        - env_file: Load from .env file
        - env_file_encoding: UTF-8 encoding
        - case_sensitive: False (OLLAMA_HOST = ollama_host)

    This tells Pydantic:
        1. Look for .env file in current directory
        2. Load variables from it
        3. Match environment variables case-insensitively
           (OLLAMA_MODEL matches ollama_model)
    """

    # ==========================================================================
    # COMPUTED PROPERTIES
    # ==========================================================================

    @property
    def category_list(self) -> List[str]:
        """
        Return categories as a list.

        Converts comma-separated string to list:
            "invoices,contracts,reports" → ["invoices", "contracts", "reports"]

        Returns:
            List of category strings

        Why a property?
            - Environment variables are strings
            - Code wants a list
            - Property converts on access
            - Don't need to store both formats

        Usage:
            >>> settings.categories
            "invoices,contracts,reports"
            >>> settings.category_list
            ["invoices", "contracts", "reports"]
        """
        return [cat.strip() for cat in self.categories.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """
        Return max file size in bytes.

        Converts MB to bytes:
            100 MB → 104,857,600 bytes

        Returns:
            Max file size in bytes

        Why?
            - Config is in MB (human-readable)
            - Code needs bytes (for comparisons)
            - Property converts automatically

        Usage:
            >>> settings.max_file_size_mb
            100
            >>> settings.max_file_size_bytes
            104857600
            >>>
            >>> # In code:
            >>> if file_size > settings.max_file_size_bytes:
            ...     skip_file()
        """
        return self.max_file_size_mb * 1024 * 1024

    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================

    def ensure_directories(self):
        """
        Create necessary directories if they don't exist.

        Creates:
            - input_folder/
            - output_folder/
            - temp_folder/
            - output_folder/[category]/ (for each category)

        Why?
            - Prevents "directory not found" errors
            - Safe to call multiple times (mkdir with exist_ok=True)
            - Sets up filesystem structure automatically

        When to call:
            - Application startup
            - Before processing documents
            - After changing configuration

        Usage:
            >>> from config import settings
            >>> settings.ensure_directories()
            >>> # Now all folders exist and are ready
        """
        # Create main folders
        self.input_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.temp_folder.mkdir(parents=True, exist_ok=True)

        # Create category folders in output directory
        # This prepares folders for DocumentOrganizer
        for category in self.category_list:
            (self.output_folder / category).mkdir(parents=True, exist_ok=True)


# ==============================================================================
# GLOBAL SETTINGS INSTANCE
# ==============================================================================

settings = Settings()
"""
Global settings instance (singleton pattern).

This is the main way to access configuration throughout the application.

Why global?
    - Single source of truth
    - Loaded once at startup
    - Accessible everywhere
    - Simplifies code

Usage:
    >>> from config import settings
    >>>
    >>> # Access any setting
    >>> print(settings.ollama_model)
    >>>
    >>> # Use in services
    >>> ollama = OllamaService(host=settings.ollama_host)
    >>>
    >>> # Use in classifiers
    >>> classifier = DocumentClassifier()
    >>> # Automatically uses settings.category_list

Thread Safety:
    - Pydantic settings are immutable after creation
    - Safe to access from multiple threads
    - No locking needed

When is it created?
    - At import time (when you import config)
    - Loads from environment/.env immediately
    - Ready to use

Example:
    ```python
    # In any file:
    from config import settings

    # Settings already loaded and ready
    if settings.use_database:
        db = DatabaseService(settings.database_url)

    for category in settings.category_list:
        print(category)
    ```
"""
