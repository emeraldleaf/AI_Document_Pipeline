#!/usr/bin/env python3
"""Generate embedding for a single document."""

import os
os.environ["DATABASE_URL"] = "postgresql://joshuadell@localhost:5432/documents"

from src.embedding_service import EmbeddingService
from src.database import DatabaseService
from sqlalchemy import text

def generate_embedding_for_document(doc_id: int):
    """Generate embedding for a specific document."""

    # Initialize services
    embedding_service = EmbeddingService(provider="ollama", model="nomic-embed-text")
    db_service = DatabaseService()

    session = db_service.get_session()

    try:
        # Get document
        result = session.execute(
            text("SELECT id, file_name, full_content FROM documents WHERE id = :doc_id"),
            {"doc_id": doc_id}
        )
        row = result.fetchone()

        if not row:
            print(f"Document {doc_id} not found")
            return

        doc_id, file_name, content = row
        print(f"Generating embedding for: {file_name}")

        if not content:
            print(f"No content found for {file_name}")
            return

        # Generate embedding
        print(f"Content length: {len(content)} characters")
        embedding = embedding_service.generate_embedding(content)
        print(f"Embedding generated: {len(embedding)} dimensions")

        # Update document with embedding
        session.execute(
            text("UPDATE documents SET embedding = :embedding WHERE id = :doc_id"),
            {"embedding": embedding, "doc_id": doc_id}
        )
        session.commit()

        print(f"✓ Embedding saved for {file_name}")

        # Verify
        result = session.execute(
            text("SELECT embedding IS NOT NULL, pg_column_size(embedding) FROM documents WHERE id = :doc_id"),
            {"doc_id": doc_id}
        )
        has_emb, size = result.fetchone()
        print(f"  Has embedding: {has_emb}, Size: {size} bytes")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    # Get the research paper document ID
    db_service = DatabaseService()
    session = db_service.get_session()

    result = session.execute(
        text("SELECT id FROM documents WHERE file_name LIKE '%research_paper%'")
    )
    row = result.fetchone()

    if row:
        doc_id = row[0]
        print(f"Found research paper document with ID: {doc_id}\n")
        generate_embedding_for_document(doc_id)
    else:
        print("Research paper document not found")

    session.close()
