#!/usr/bin/env python3
"""Check embeddings in OpenSearch documents"""
import json
import subprocess

result = subprocess.run(
    ['curl', '-s', 'http://localhost:9200/documents/_search?size=5'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)

print("Checking embeddings in OpenSearch documents:\n")
print("=" * 70)

for i, hit in enumerate(data['hits']['hits'][:5], 1):
    src = hit['_source']
    embedding = src.get('embedding', [])

    has_valid_embedding = False
    if embedding and len(embedding) > 0:
        # Check if any of the first 10 values are non-zero
        has_valid_embedding = any(v != 0 for v in embedding[:10])

    print(f"{i}. {src['file_name']}")
    print(f"   Category: {src.get('category', 'N/A')}")
    print(f"   Content length: {len(src.get('full_content', ''))}")

    if has_valid_embedding:
        print(f"   ✓ Embedding: VALID (dimension: {len(embedding)})")
        print(f"   First 5 values: {embedding[:5]}")
    elif embedding and len(embedding) > 0:
        print(f"   ✗ Embedding: ALL ZEROS (dimension: {len(embedding)})")
    else:
        print(f"   ✗ Embedding: MISSING")
    print()

print("=" * 70)

# Count valid vs invalid
total = len(data['hits']['hits'])
valid_count = sum(
    1 for hit in data['hits']['hits']
    if hit['_source'].get('embedding') and len(hit['_source']['embedding']) > 0
    and any(v != 0 for v in hit['_source']['embedding'][:10])
)

print(f"\nSummary: {valid_count}/{total} documents have valid embeddings")
