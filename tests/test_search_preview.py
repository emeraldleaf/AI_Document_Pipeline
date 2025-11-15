#!/usr/bin/env python3
"""Test search preview to demonstrate the improvement."""

from src.search_service import SearchService, SearchMode
from config import settings

def test_search(query: str):
    """Test search with the given query."""
    search = SearchService(
        database_url=settings.database_url,
        embedding_provider=settings.embedding_provider
    )

    print(f"\n{'='*80}")
    print(f"SEARCHING FOR: '{query}'")
    print(f"{'='*80}\n")

    # Perform hybrid search
    results = search.search(query=query, mode=SearchMode.HYBRID, limit=3)

    for i, result in enumerate(results, 1):
        if "technical_manual" in result.file_name.lower():
            print(f"\nResult {i}: {result.file_name}")
            print(f"Category: {result.category}")
            print(f"Scores - Keyword: {result.keyword_rank:.4f}, Semantic: {result.semantic_rank:.4f}, Combined: {result.combined_score:.4f}")
            print(f"\nContent Preview (showing relevant pages):")
            print(f"{'-'*80}")

            # Split by | to show each page snippet on a new line for readability
            snippets = result.content_preview.split(" | ")
            for snippet in snippets:
                print(f"  • {snippet}")

            print(f"{'-'*80}")

if __name__ == "__main__":
    # Test with queries that should find content on specific pages
    test_queries = [
        "API",
        "authentication",
        "backup procedures",
        "performance tuning"
    ]

    for query in test_queries:
        test_search(query)

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print("The improved snippet extraction now:")
    print("  1. Shows page numbers clearly: [Page 6], [Page 12], etc.")
    print("  2. Displays up to 5 relevant pages (was 3)")
    print("  3. Sorts pages by relevance (most matches first)")
    print("  4. Provides better context around each match")
    print("  5. Makes it easy to see which pages contain your search terms")
    print(f"{'='*80}\n")
