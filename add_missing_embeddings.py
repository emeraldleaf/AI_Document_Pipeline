#!/usr/bin/env python3
"""
Generate embeddings for documents that are missing them.

This script processes only the documents without embeddings,
with delays between requests to prevent Ollama API overload.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from opensearchpy import OpenSearch
from src.embedding_service import EmbeddingService
from config import settings

print("=" * 80)
print("ADDING EMBEDDINGS TO DOCUMENTS WITHOUT THEM")
print("=" * 80)
print()

# Initialize services
embedding_service = EmbeddingService.from_config(settings)
client = OpenSearch(
    hosts=["http://localhost:9200"],
    use_ssl=False,
    verify_certs=False
)

# Get all documents
response = client.search(
    index="documents",
    body={"query": {"match_all": {}}, "size": 100}
)

# Find documents without embeddings
docs_to_process = []
for hit in response['hits']['hits']:
    doc_id = hit['_source']['id']
    embedding = hit['_source'].get('embedding', [])

    # Check if embedding is missing or invalid (all zeros)
    has_valid_embedding = False
    if embedding and len(embedding) > 0:
        has_valid_embedding = any(v != 0 for v in embedding[:10])

    if not has_valid_embedding:
        docs_to_process.append({
            'id': doc_id,
            'file_name': hit['_source']['file_name'],
            'full_content': hit['_source'].get('full_content', ''),
            'content_length': len(hit['_source'].get('full_content', ''))
        })

if not docs_to_process:
    print("✅ All documents already have embeddings!")
    sys.exit(0)

print(f"Found {len(docs_to_process)} documents without embeddings:")
print()
for doc in docs_to_process:
    print(f"  • ID {doc['id']:2d}: {doc['file_name']:40s} ({doc['content_length']:,} chars)")
print()

# Process each document with delay
print("-" * 80)
print("Processing documents (with 3-second delay between each)...")
print("-" * 80)
print()

success_count = 0
failed_count = 0
failed_docs = []

for i, doc in enumerate(docs_to_process, 1):
    print(f"[{i}/{len(docs_to_process)}] Processing ID {doc['id']}: {doc['file_name']}")
    print(f"     Content length: {doc['content_length']:,} chars")

    try:
        # Truncate content if too long (nomic-embed-text limit is ~2500 chars)
        content = doc['full_content']
        max_length = 2000  # Safe limit for Ollama nomic-embed-text
        if len(content) > max_length:
            print(f"     Truncating from {len(content):,} to {max_length:,} chars")
            content = content[:max_length]

        # Generate embedding
        print(f"     Generating embedding...")
        embedding = embedding_service.embed_text(content)

        if embedding and len(embedding) > 0:
            # Update document in OpenSearch
            client.update(
                index="documents",
                id=doc['id'],
                body={"doc": {"embedding": embedding}}
            )
            print(f"     ✅ SUCCESS: Generated {len(embedding)}-dim embedding and updated document")
            success_count += 1
        else:
            print(f"     ❌ FAILED: Embedding service returned None")
            failed_count += 1
            failed_docs.append(doc['file_name'])

    except Exception as e:
        print(f"     ❌ ERROR: {e}")
        failed_count += 1
        failed_docs.append(doc['file_name'])

    print()

    # Delay between requests to prevent API overload
    if i < len(docs_to_process):
        print(f"     Waiting 3 seconds before next document...")
        time.sleep(3)
        print()

# Refresh index
print("-" * 80)
print("Refreshing OpenSearch index...")
client.indices.refresh(index="documents")
print("✓ Index refreshed")
print()

# Verify results
print("=" * 80)
print("RESULTS")
print("=" * 80)
print()

response = client.search(
    index="documents",
    body={"query": {"match_all": {}}, "size": 100}
)

total_with_embeddings = 0
total_without_embeddings = 0

for hit in response['hits']['hits']:
    embedding = hit['_source'].get('embedding', [])
    has_valid_embedding = embedding and len(embedding) > 0 and any(v != 0 for v in embedding[:10])

    if has_valid_embedding:
        total_with_embeddings += 1
    else:
        total_without_embeddings += 1

total_docs = total_with_embeddings + total_without_embeddings

print(f"Documents with embeddings:    {total_with_embeddings}/{total_docs} ({total_with_embeddings/total_docs*100:.1f}%)")
print(f"Documents without embeddings: {total_without_embeddings}/{total_docs} ({total_without_embeddings/total_docs*100:.1f}%)")
print()

print("-" * 80)
print(f"Processed: {len(docs_to_process)} documents")
print(f"Succeeded: {success_count}")
print(f"Failed:    {failed_count}")
print()

if failed_count > 0:
    print("Failed documents:")
    for fname in failed_docs:
        print(f"  • {fname}")
    print()
    print("⚠️  Some documents still don't have embeddings.")
    print("   They are still searchable via keyword search.")
    print()
else:
    print("✅ ALL DOCUMENTS NOW HAVE EMBEDDINGS!")
    print()
    print("All documents are now ready for:")
    print("  • Keyword search (BM25)")
    print("  • Semantic search (vector similarity)")
    print("  • Hybrid search (combined)")
    print()

sys.exit(0 if failed_count == 0 else 1)
