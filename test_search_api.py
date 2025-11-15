#!/usr/bin/env python3
"""
Test the search API with OpenSearch backend
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.opensearch_service import OpenSearchService
from src.embedding_service import EmbeddingService, EmbeddingProvider

# Override settings to use OpenSearch
settings.search_backend = "opensearch"
settings.opensearch_hosts = "http://localhost:9200"

# Initialize embedding service
embedding_service = EmbeddingService.from_config(settings)

# Initialize OpenSearch service with embedding service
print(f"Search backend: {settings.search_backend}")
print(f"OpenSearch hosts: {settings.opensearch_hosts}")
print(f"Embedding service: {type(embedding_service).__name__}")
print()

opensearch_service = OpenSearchService(
    hosts=settings.opensearch_hosts,
    embedding_service=embedding_service
)

# Test 1: Keyword search
print("=" * 60)
print("TEST 1: Keyword Search for 'invoice'")
print("=" * 60)

results = opensearch_service.keyword_search(
    query="invoice",
    limit=5
)

print(f"Found {len(results)} results:\n")
for i, result in enumerate(results, 1):
    print(f"{i}. {result.file_name} (Category: {result.category})")
    print(f"   Score: {result.combined_score:.3f}")
    if result.content_preview:
        snippet_preview = result.content_preview[:100].replace('\n', ' ')
        print(f"   Preview: {snippet_preview}...")
    print()

# Test 2: Semantic search
print("=" * 60)
print("TEST 2: Semantic Search for 'contract agreement'")
print("=" * 60)

results = opensearch_service.semantic_search(
    query="contract agreement",
    limit=3
)

print(f"Found {len(results)} results:\n")
for i, result in enumerate(results, 1):
    print(f"{i}. {result.file_name} (Category: {result.category})")
    print(f"   Score: {result.combined_score:.3f}")
    print()

# Test 3: Hybrid search (keyword + semantic)
print("=" * 60)
print("TEST 3: Hybrid Search for 'financial report'")
print("=" * 60)

results = opensearch_service.hybrid_search(
    query="financial report",
    limit=5
)

print(f"Found {len(results)} results:\n")
for i, result in enumerate(results, 1):
    print(f"{i}. {result.file_name} (Category: {result.category})")
    print(f"   Score: {result.combined_score:.3f}")
    print()

# Test 4: Get index stats
print("=" * 60)
print("TEST 4: Index Statistics")
print("=" * 60)

stats = opensearch_service.get_index_stats()
print(f"Index: {stats.get('index_name', 'N/A')}")
print(f"Documents: {stats.get('document_count', 0):,}")
print(f"Size: {stats.get('size_bytes', 0):,} bytes")
print()

print("✓ All tests completed!")
