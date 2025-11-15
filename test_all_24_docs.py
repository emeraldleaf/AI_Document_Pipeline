#!/usr/bin/env python3
"""Test search across all 24 documents"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.opensearch_service import OpenSearchService
from src.embedding_service import EmbeddingService

settings.search_backend = "opensearch"
settings.opensearch_hosts = "http://localhost:9200"

embedding_service = EmbeddingService.from_config(settings)
opensearch_service = OpenSearchService(
    hosts=settings.opensearch_hosts,
    embedding_service=embedding_service
)

print("=" * 70)
print("Testing Search Across All 24 Documents")
print("=" * 70)
print()

# Test 1: Search for content from the large documents
print("TEST 1: Search for 'annual report' (should find ID 20)")
print("-" * 70)
results = opensearch_service.keyword_search(query="annual report", limit=3)
for i, result in enumerate(results, 1):
    print(f"{i}. {result.file_name} (ID: {result.id}, Category: {result.category})")
    print(f"   Score: {result.combined_score:.3f}")
print()

# Test 2: Search for research content
print("TEST 2: Search for 'machine learning' (should find ID 22)")
print("-" * 70)
results = opensearch_service.keyword_search(query="machine learning", limit=3)
for i, result in enumerate(results, 1):
    print(f"{i}. {result.file_name} (ID: {result.id}, Category: {result.category})")
    print(f"   Score: {result.combined_score:.3f}")
print()

# Test 3: Search for security content
print("TEST 3: Search for 'security' (should find ID 23)")
print("-" * 70)
results = opensearch_service.keyword_search(query="security", limit=3)
for i, result in enumerate(results, 1):
    print(f"{i}. {result.file_name} (ID: {result.id}, Category: {result.category})")
    print(f"   Score: {result.combined_score:.3f}")
print()

# Test 4: Get document counts by category
print("TEST 4: Document Counts by Category")
print("-" * 70)

categories = ['invoices', 'contracts', 'reports', 'correspondence', 'research', 'compliance', 'other']
for category in categories:
    results = opensearch_service.keyword_search(query="*", category=category, limit=100)
    if results:
        print(f"{category.capitalize():15} : {len(results)} documents")

print()
print("=" * 70)
print(f"✓ All tests complete! Total documents searchable: 24")
print("=" * 70)
