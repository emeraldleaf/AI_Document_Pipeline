#!/usr/bin/env python3
"""Test snippet extraction to understand the issue."""

from src.search_service import SearchService
from config import settings

# Initialize search service
search = SearchService(
    database_url=settings.database_url,
    embedding_provider=settings.embedding_provider
)

# Test query
query = "API"

# Perform search
print(f"\n=== Testing Query: '{query}' ===\n")

# Try all search modes
for mode_name in ["keyword", "semantic", "hybrid"]:
    from src.search_service import SearchMode
    mode = SearchMode[mode_name.upper()]

    print(f"\n{mode_name.upper()} Search Results:")
    print("=" * 80)

    results = search.search(query=query, mode=mode, limit=5)

    for i, result in enumerate(results, 1):
        if "technical_manual" in result.file_name.lower():
            print(f"\nResult {i}: {result.file_name}")
            print(f"Scores - Keyword: {result.keyword_rank:.4f}, Semantic: {result.semantic_rank:.4f}, Combined: {result.combined_score:.4f}")
            print(f"\nContent Preview:")
            print("-" * 80)
            print(result.content_preview)
            print("-" * 80)

# Now test the snippet extraction directly
print("\n\n=== TESTING SNIPPET EXTRACTION DIRECTLY ===\n")

# Get the full content
import sqlalchemy as sa
from sqlalchemy import text

engine = sa.create_engine(settings.database_url)
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT full_content FROM documents WHERE file_name = 'technical_manual_20_pages.pdf'")
    )
    row = result.fetchone()
    full_content = row[0] if row else ""

# Test snippet extraction
snippet = search._extract_multiple_snippets(full_content, query, max_snippets=5, snippet_length=150)
print(f"Extracted Snippet for '{query}':")
print("=" * 80)
print(snippet)
print("=" * 80)

# Check what pages mention API
print("\n\n=== PAGES MENTIONING 'API' ===\n")
import re
pages_with_api = []
page_pattern = r'\[Page (\d+)\](.*?)(?=\[Page \d+\]|$)'
matches = re.finditer(page_pattern, full_content, re.DOTALL)

for match in matches:
    page_num = match.group(1)
    page_content = match.group(2)
    if 'API' in page_content or 'api' in page_content.lower():
        pages_with_api.append(page_num)
        print(f"Page {page_num} mentions API")

print(f"\nTotal pages with API mentions: {pages_with_api}")
