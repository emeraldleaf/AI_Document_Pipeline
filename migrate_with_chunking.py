#!/usr/bin/env python3
"""
Migrate documents to OpenSearch with intelligent chunking.

This approach:
1. Chunks large documents into embedding-friendly sizes
2. Generates embeddings for each chunk
3. Stores chunks in OpenSearch for granular semantic search
4. Preserves document-level metadata on all chunks
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import psycopg2
from opensearchpy import OpenSearch
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from src.document_chunker import get_chunker
from src.embedding_service import EmbeddingService
from config import settings

console = Console()

def main():
    console.print("[bold cyan]Document Migration with Chunking[/bold cyan]")
    console.print("=" * 80)
    console.print()

    # Initialize services
    console.print("Initializing services...")
    embedding_service = EmbeddingService.from_config(settings)
    client = OpenSearch(
        hosts=[settings.opensearch_hosts],
        use_ssl=False,
        verify_certs=False
    )
    chunker = get_chunker('ollama_mxbai')  # 700 char chunks, 100 overlap, optimized for mxbai-embed-large
    console.print("✓ Services initialized")
    console.print()

    # Connect to PostgreSQL
    console.print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM documents")
    total_docs = cur.fetchone()[0]
    console.print(f"✓ Found {total_docs} documents in PostgreSQL")
    console.print()

    # Fetch all documents
    console.print("Fetching documents...")
    cur.execute("""
        SELECT id, file_name, file_path, category, title, author,
               page_count, file_type, file_size, created_date,
               modified_date, processed_date, full_content,
               content_preview, confidence, metadata_json
        FROM documents
        ORDER BY id
    """)

    documents = []
    for row in cur.fetchall():
        documents.append({
            'id': row[0],
            'file_name': row[1],
            'file_path': row[2],
            'category': row[3],
            'title': row[4],
            'author': row[5],
            'page_count': row[6],
            'file_type': row[7],
            'file_size': row[8],
            'created_date': row[9],
            'modified_date': row[10],
            'processed_date': row[11],
            'full_content': row[12],
            'content_preview': row[13],
            'confidence': row[14],
            'metadata_json': row[15]
        })

    cur.close()
    conn.close()

    console.print(f"✓ Fetched {len(documents)} documents")
    console.print()

    # Ensure index exists
    console.print("Setting up OpenSearch index...")
    index_name = "document_chunks"

    # Delete existing index if it exists
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)

    # Create index with proper mapping
    client.indices.create(
        index=index_name,
        body={
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "integer"},
                    "chunk_index": {"type": "integer"},
                    "content": {"type": "text"},
                    "char_start": {"type": "integer"},
                    "char_end": {"type": "integer"},
                    "file_name": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "title": {"type": "text"},
                    "author": {"type": "keyword"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,  # mxbai-embed-large uses 1024 dimensions
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    }
                }
            }
        }
    )
    console.print(f"✓ Created index: {index_name}")
    console.print()

    # Process documents
    console.print("[bold]Processing documents with chunking...[/bold]")
    console.print()

    total_chunks = 0
    total_embeddings_success = 0
    total_embeddings_failed = 0
    chunks_indexed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:

        task = progress.add_task("Processing documents...", total=len(documents))

        for doc in documents:
            # Chunk the document
            chunks = chunker.chunk_document(
                document_id=doc['id'],
                content=doc['full_content'],
                metadata={
                    'file_name': doc['file_name'],
                    'category': doc['category'],
                    'title': doc['title'],
                    'author': doc['author']
                }
            )

            total_chunks += len(chunks)

            # Generate embeddings and index chunks
            for chunk in chunks:
                try:
                    # Generate embedding for chunk
                    embedding = embedding_service.embed_text(chunk.content)

                    if embedding:
                        # Index chunk with embedding
                        chunk_doc = chunk.to_dict()
                        chunk_doc['embedding'] = embedding

                        client.index(
                            index=index_name,
                            id=chunk.chunk_id,
                            body=chunk_doc
                        )

                        chunks_indexed += 1
                        total_embeddings_success += 1
                    else:
                        # Index without embedding (fallback)
                        client.index(
                            index=index_name,
                            id=chunk.chunk_id,
                            body=chunk.to_dict()
                        )
                        chunks_indexed += 1
                        total_embeddings_failed += 1

                    # Small delay to prevent API overload
                    time.sleep(0.5)

                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to process chunk {chunk.chunk_id}: {e}[/yellow]")
                    total_embeddings_failed += 1

            progress.update(task, advance=1)

    # Refresh index
    client.indices.refresh(index=index_name)

    # Results
    console.print()
    console.print("[bold green]Migration Complete![/bold green]")
    console.print()
    console.print(f"Documents processed:     {len(documents)}")
    console.print(f"Total chunks created:    {total_chunks}")
    console.print(f"Chunks indexed:          {chunks_indexed}")
    console.print(f"Embeddings generated:    {total_embeddings_success} ({total_embeddings_success/total_chunks*100:.1f}%)")
    console.print(f"Embedding failures:      {total_embeddings_failed}")
    console.print()

    # Verify
    count = client.count(index=index_name)['count']
    console.print(f"✓ Verified: {count} chunks in OpenSearch")
    console.print()

    console.print("[dim]Benefits of chunking approach:[/dim]")
    console.print("[dim]  • All documents processed (no size limits)[/dim]")
    console.print("[dim]  • Granular semantic search (chunk-level)[/dim]")
    console.print("[dim]  • Better context preservation (overlap)[/dim]")
    console.print("[dim]  • Higher embedding success rate[/dim]")
    console.print()

if __name__ == "__main__":
    main()
