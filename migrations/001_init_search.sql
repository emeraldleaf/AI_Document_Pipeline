-- Initialize PostgreSQL with pgvector extension and full-text search
-- This migration creates the schema for cloud-ready document search

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table with full-text search and vector support
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,

    -- File information
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    file_hash VARCHAR(64) UNIQUE,  -- SHA256 for deduplication

    -- Timestamps
    created_date TIMESTAMP,
    modified_date TIMESTAMP,
    processed_date TIMESTAMP DEFAULT NOW(),

    -- Document metadata
    author VARCHAR(255),
    title VARCHAR(500),
    page_count INTEGER,

    -- Classification
    category VARCHAR(100) NOT NULL,
    confidence TEXT,
    model_used VARCHAR(100),

    -- Content
    content_preview TEXT,
    full_content TEXT,
    metadata_json JSONB,

    -- Organization
    output_path VARCHAR(500),
    is_organized BOOLEAN DEFAULT FALSE,

    -- Performance tracking
    classification_time FLOAT,

    -- Full-text search vector (automatically updated)
    content_tsv tsvector,

    -- Semantic search embedding (768-dim for nomic-embed-text)
    embedding vector(768)
);

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_documents_file_name ON documents(file_name);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_processed_date ON documents(processed_date DESC);
CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents(file_path);

-- Full-text search index (GIN index for fast text search)
CREATE INDEX IF NOT EXISTS idx_documents_fts ON documents USING GIN(content_tsv);

-- Vector similarity index (IVFFlat for fast nearest neighbor search)
-- This creates an approximate index for semantic search
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Trigger to automatically update full-text search vector
CREATE OR REPLACE FUNCTION documents_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.author, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.file_name, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.full_content, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.content_preview, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE
ON documents FOR EACH ROW EXECUTE FUNCTION documents_tsv_trigger();

-- Classification history table for tracking accuracy
CREATE TABLE IF NOT EXISTS classification_history (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,

    timestamp TIMESTAMP DEFAULT NOW(),

    -- Classification details
    predicted_category VARCHAR(100) NOT NULL,
    correct_category VARCHAR(100),
    was_corrected BOOLEAN DEFAULT FALSE,

    -- Model info
    model_name VARCHAR(100),
    confidence_score TEXT,

    -- Performance
    processing_time FLOAT
);

CREATE INDEX IF NOT EXISTS idx_history_document_id ON classification_history(document_id);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON classification_history(timestamp DESC);

-- View for search statistics
CREATE OR REPLACE VIEW search_statistics AS
SELECT
    COUNT(*) as total_documents,
    COUNT(DISTINCT category) as total_categories,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as documents_with_embeddings,
    COUNT(CASE WHEN content_tsv IS NOT NULL THEN 1 END) as documents_with_fts,
    AVG(file_size) as avg_file_size,
    SUM(file_size) as total_storage
FROM documents;

-- Function for hybrid search (combines FTS + vector similarity)
CREATE OR REPLACE FUNCTION hybrid_search(
    search_query TEXT,
    query_embedding vector(768),
    keyword_weight DOUBLE PRECISION DEFAULT 0.6,
    semantic_weight DOUBLE PRECISION DEFAULT 0.4,
    result_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id INTEGER,
    file_name VARCHAR,
    category VARCHAR,
    title VARCHAR,
    content_preview TEXT,
    keyword_rank DOUBLE PRECISION,
    semantic_rank DOUBLE PRECISION,
    combined_score DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    WITH keyword_results AS (
        SELECT
            d.id,
            ts_rank(d.content_tsv, websearch_to_tsquery('english', search_query)) as rank
        FROM documents d
        WHERE d.content_tsv @@ websearch_to_tsquery('english', search_query)
    ),
    semantic_results AS (
        SELECT
            d.id,
            1 - (d.embedding <=> query_embedding) as similarity
        FROM documents d
        WHERE d.embedding IS NOT NULL
        ORDER BY d.embedding <=> query_embedding
        LIMIT result_limit * 3
    )
    SELECT
        d.id,
        d.file_name,
        d.category,
        d.title,
        d.content_preview,
        COALESCE(kr.rank, 0)::DOUBLE PRECISION as keyword_rank,
        COALESCE(sr.similarity, 0)::DOUBLE PRECISION as semantic_rank,
        (COALESCE(kr.rank, 0) * keyword_weight + COALESCE(sr.similarity, 0) * semantic_weight)::DOUBLE PRECISION as combined_score
    FROM documents d
    LEFT JOIN keyword_results kr ON d.id = kr.id
    LEFT JOIN semantic_results sr ON d.id = sr.id
    WHERE kr.rank IS NOT NULL OR sr.similarity IS NOT NULL
    ORDER BY combined_score DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (for future multi-user support)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO docuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO docuser;

-- Insert a welcome document for testing
INSERT INTO documents (
    file_path, file_name, file_type, file_size, category,
    title, content_preview, full_content
) VALUES (
    '/welcome.txt',
    'welcome.txt',
    'text/plain',
    100,
    'system',
    'Welcome to AI Document Pipeline',
    'Welcome to the AI Document Pipeline with PostgreSQL full-text search and pgvector semantic search.',
    'Welcome to the AI Document Pipeline with PostgreSQL full-text search and pgvector semantic search. This system supports both keyword-based and semantic search capabilities.'
) ON CONFLICT DO NOTHING;
