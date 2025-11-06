#!/usr/bin/env python3
"""Direct embedding generation using psycopg2."""

import requests
import psycopg2

def generate_ollama_embedding(text: str) -> list:
    """Generate embedding using Ollama API."""
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text}
    )
    response.raise_for_status()
    return response.json()["embedding"]

def add_embedding_to_document(doc_id: int):
    """Add embedding to a specific document."""

    # Connect to database
    conn = psycopg2.connect("postgresql://joshuadell@localhost:5432/documents")
    cur = conn.cursor()

    try:
        # Get document content
        cur.execute("SELECT file_name, full_content FROM documents WHERE id = %s", (doc_id,))
        row = cur.fetchone()

        if not row:
            print(f"Document {doc_id} not found")
            return

        file_name, content = row
        print(f"Processing: {file_name}")
        print(f"Content length: {len(content)} characters")

        # Generate embedding (truncate to first 2000 chars to avoid errors)
        content_truncated = content[:2000] if len(content) > 2000 else content
        print(f"Generating embedding for {len(content_truncated)} characters...")
        embedding = generate_ollama_embedding(content_truncated)
        print(f"Generated embedding: {len(embedding)} dimensions")

        # Update document
        cur.execute(
            "UPDATE documents SET embedding = %s WHERE id = %s",
            (embedding, doc_id)
        )
        conn.commit()

        print(f"✓ Embedding saved for {file_name}")

        # Verify
        cur.execute("SELECT embedding IS NOT NULL, pg_column_size(embedding) FROM documents WHERE id = %s", (doc_id,))
        has_emb, size = cur.fetchone()
        print(f"  Verified: has_embedding={has_emb}, size={size} bytes")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Process document ID 22 (research paper)
    add_embedding_to_document(22)
