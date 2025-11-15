#!/usr/bin/env python3
"""Debug why API search doesn't show technical manual."""

from src.search_service import SearchService, SearchMode
from config import settings

search = SearchService(
    database_url=settings.database_url,
    embedding_provider=settings.embedding_provider
)

query = "API"

print(f"\n=== KEYWORD SEARCH for '{query}' ===\n")
keyword_results = search.keyword_search(query=query, limit=10)
for i, r in enumerate(keyword_results, 1):
    print(f"{i}. {r.file_name} - Score: {r.keyword_rank:.4f}")
    if "technical" in r.file_name.lower():
        print(f"   Preview: {r.content_preview[:150]}...")

print(f"\n=== SEMANTIC SEARCH for '{query}' ===\n")
semantic_results = search.semantic_search(query=query, limit=10)
for i, r in enumerate(semantic_results, 1):
    print(f"{i}. {r.file_name} - Score: {r.semantic_rank:.4f}")
    if "technical" in r.file_name.lower():
        print(f"   Preview: {r.content_preview[:150]}...")

print(f"\n=== HYBRID SEARCH for '{query}' ===\n")
hybrid_results = search.hybrid_search(query=query, limit=10)
for i, r in enumerate(hybrid_results, 1):
    print(f"{i}. {r.file_name} - Keyword: {r.keyword_rank:.4f}, Semantic: {r.semantic_rank:.4f}, Combined: {r.combined_score:.4f}")
    if "technical" in r.file_name.lower():
        print(f"   Preview: {r.content_preview[:150]}...")
