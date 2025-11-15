"""Advanced search service with PostgreSQL FTS and pgvector semantic search.

Provides:
- Keyword search (PostgreSQL full-text search)
- Semantic search (pgvector cosine similarity)
- Hybrid search (combines both)
- Cloud-ready architecture
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import sqlalchemy as sa
from sqlalchemy import text
from loguru import logger

from src.embedding_service import EmbeddingService, EmbeddingProvider


class SearchMode(str, Enum):
    """Search modes."""
    KEYWORD = "keyword"      # Fast FTS search
    SEMANTIC = "semantic"    # Vector similarity search
    HYBRID = "hybrid"        # Combined (best)


@dataclass
class SearchResult:
    """Search result with ranking."""
    id: int
    file_name: str
    file_path: str
    category: str
    title: Optional[str]
    author: Optional[str]
    content_preview: str
    keyword_rank: float = 0.0
    semantic_rank: float = 0.0
    combined_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "category": self.category,
            "title": self.title,
            "author": self.author,
            "content_preview": self.content_preview[:200] + "..." if len(self.content_preview) > 200 else self.content_preview,
            "keyword_rank": round(self.keyword_rank, 4),
            "semantic_rank": round(self.semantic_rank, 4),
            "combined_score": round(self.combined_score, 4),
        }


class SearchService:
    """Advanced search service with FTS and vector search.

    Features:
    - PostgreSQL full-text search (fast keyword search)
    - pgvector semantic search (meaning-based search)
    - Hybrid search combining both methods
    - Configurable ranking weights
    - Cloud-ready architecture
    """

    def __init__(
        self,
        database_url: str,
        embedding_service=None,
        embedding_provider: str = "ollama"
    ):
        """Initialize search service.

        Args:
            database_url: PostgreSQL connection URL
            embedding_service: Optional pre-configured embedding service
            embedding_provider: "ollama" or "openai"
        """
        self.database_url = database_url
        self.engine = sa.create_engine(database_url)

        # Initialize embedding service
        if embedding_service:
            self.embedding_service = embedding_service
        else:
            self.embedding_service = EmbeddingService.create(
                provider=EmbeddingProvider(embedding_provider)
            )

        logger.info("Search service initialized")

    def _extract_multiple_snippets(
        self,
        full_text: str,
        query: str,
        max_snippets: int = 5,
        snippet_length: int = 200
    ) -> str:
        """Extract multiple relevant snippets from text showing different matches.

        For documents with page markers ([Page N]), this will show which pages
        contain relevant content.

        Args:
            full_text: Full document text
            query: Search query
            max_snippets: Maximum number of snippets to extract (default 5)
            snippet_length: Length of each snippet (default 200)

        Returns:
            Combined text with multiple relevant snippets, preserving page markers
        """
        if not full_text:
            return ""

        # Check if document has page markers
        import re
        has_pages = bool(re.search(r'\[Page \d+\]', full_text))

        if has_pages:
            # Extract snippets per page for better readability
            return self._extract_page_based_snippets(full_text, query, max_snippets, snippet_length)
        else:
            # Use original position-based extraction
            return self._extract_position_based_snippets(full_text, query, max_snippets, snippet_length)

    def _extract_page_based_snippets(
        self,
        full_text: str,
        query: str,
        max_snippets: int,
        snippet_length: int
    ) -> str:
        """Extract snippets organized by page number.

        Args:
            full_text: Full document text with [Page N] markers
            query: Search query
            max_snippets: Maximum number of page snippets to show
            snippet_length: Characters to show per snippet

        Returns:
            Snippets with page numbers, e.g., "[Page 6] REST API provides..."
        """
        import re

        # Split into pages
        page_pattern = r'\[Page (\d+)\](.*?)(?=\[Page \d+\]|$)'
        pages = list(re.finditer(page_pattern, full_text, re.DOTALL))

        # Find query terms in each page
        query_terms = [term.lower() for term in query.split() if len(term) >= 2]
        page_matches = []

        for page_match in pages:
            page_num = page_match.group(1)
            page_content = page_match.group(2)
            page_content_lower = page_content.lower()

            # Count matches for this page
            match_count = 0
            best_match_pos = -1

            for term in query_terms:
                pos = page_content_lower.find(term)
                if pos != -1:
                    match_count += page_content_lower.count(term)
                    if best_match_pos == -1:
                        best_match_pos = pos

            if match_count > 0:
                page_matches.append({
                    'page_num': page_num,
                    'content': page_content,
                    'match_count': match_count,
                    'match_pos': best_match_pos
                })

        # Sort by match count (most relevant first)
        page_matches.sort(key=lambda x: (-x['match_count'], int(x['page_num'])))

        # Extract snippets from top matching pages
        snippets = []
        for page_data in page_matches[:max_snippets]:
            page_num = page_data['page_num']
            content = page_data['content'].strip()
            match_pos = page_data['match_pos']

            # Extract snippet around the match
            if match_pos >= 0:
                # Center snippet around the match
                start = max(0, match_pos - snippet_length // 2)
                end = min(len(content), match_pos + snippet_length // 2)

                # Adjust to word boundaries
                while start > 0 and content[start] not in ' \n':
                    start -= 1
                while end < len(content) and content[end] not in ' \n':
                    end += 1

                snippet_text = content[start:end].strip()

                # Clean up whitespace
                snippet_text = ' '.join(snippet_text.split())

                # Add ellipsis if truncated
                if start > 0:
                    snippet_text = "..." + snippet_text
                if end < len(content):
                    snippet_text = snippet_text + "..."

                snippets.append(f"[Page {page_num}] {snippet_text}")
            else:
                # Fallback: show beginning of page
                snippet_text = ' '.join(content[:snippet_length].split())
                snippets.append(f"[Page {page_num}] {snippet_text}...")

        if snippets:
            return " | ".join(snippets)
        else:
            # No matches found, return beginning of document
            return full_text[:snippet_length * 2].strip() + "..."

    def _extract_position_based_snippets(
        self,
        full_text: str,
        query: str,
        max_snippets: int,
        snippet_length: int
    ) -> str:
        """Extract snippets based on query term positions (original method).

        Args:
            full_text: Full document text
            query: Search query
            max_snippets: Maximum number of snippets
            snippet_length: Length of each snippet

        Returns:
            Combined snippets separated by |
        """
        # Split query into terms
        query_terms = [term.lower() for term in query.split() if len(term) >= 2]
        text_lower = full_text.lower()

        # Find all occurrences of query terms
        matches = []
        for term in query_terms:
            start = 0
            while True:
                pos = text_lower.find(term, start)
                if pos == -1:
                    break
                matches.append((pos, term))
                start = pos + len(term)

        # Sort matches by position and remove duplicates/close matches
        matches.sort(key=lambda x: x[0])
        filtered_matches = []
        for match in matches:
            # Reduce minimum distance to 150 chars (was 200) to get more snippets
            if not filtered_matches or match[0] - filtered_matches[-1][0] > 150:
                filtered_matches.append(match)

        # Extract snippets around matches
        snippets = []
        for pos, term in filtered_matches[:max_snippets]:
            # Get context around the match
            start = max(0, pos - snippet_length // 2)
            end = min(len(full_text), pos + snippet_length // 2)

            # Adjust to word boundaries
            while start > 0 and full_text[start] not in ' \n':
                start -= 1
            while end < len(full_text) and full_text[end] not in ' \n':
                end += 1

            snippet = full_text[start:end].strip()
            # Clean up whitespace
            snippet = ' '.join(snippet.split())

            if snippet:
                # Add ellipsis
                if start > 0:
                    snippet = "..." + snippet
                if end < len(full_text):
                    snippet = snippet + "..."
                snippets.append(snippet)

        # Combine snippets
        if snippets:
            return " | ".join(snippets)
        else:
            # Fallback to beginning of document
            return full_text[:snippet_length * 2] + ("..." if len(full_text) > snippet_length * 2 else "")

    def keyword_search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """Perform keyword-based full-text search.

        Uses PostgreSQL's built-in FTS with ranking.

        Args:
            query: Search query (supports AND, OR, NOT)
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of search results ranked by relevance

        Examples:
            # Simple search
            results = search.keyword_search("invoice payment")

            # Boolean search
            results = search.keyword_search("contract AND amendment")

            # Phrase search
            results = search.keyword_search('"quarterly report"')
        """
        try:
            with self.engine.connect() as conn:
                # Build query - include full_content for snippet extraction
                sql = """
                    SELECT
                        id,
                        file_name,
                        file_path,
                        category,
                        title,
                        author,
                        content_preview,
                        full_content,
                        ts_rank(content_tsv, websearch_to_tsquery('english', :query)) as rank
                    FROM documents
                    WHERE content_tsv @@ websearch_to_tsquery('english', :query)
                """

                params = {"query": query}

                # Add category filter if specified
                if category:
                    sql += " AND category = :category"
                    params["category"] = category

                sql += " ORDER BY rank DESC LIMIT :limit"
                params["limit"] = limit

                result = conn.execute(text(sql), params)
                rows = result.fetchall()

                # Convert to SearchResult objects with snippet extraction
                results = []
                for row in rows:
                    # Extract snippet from full content if available
                    full_content = row[7] or ""
                    if full_content:
                        snippet = self._extract_multiple_snippets(full_content, query)
                    else:
                        snippet = row[6] or ""  # Fall back to content_preview

                    results.append(SearchResult(
                        id=row[0],
                        file_name=row[1],
                        file_path=row[2],
                        category=row[3],
                        title=row[4],
                        author=row[5],
                        content_preview=snippet,
                        keyword_rank=float(row[8]),
                        combined_score=float(row[8])
                    ))

                logger.info(f"Keyword search for '{query}': {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

    def semantic_search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """Perform semantic vector similarity search.

        Uses pgvector for fast native vector similarity search.

        Args:
            query: Search query (natural language)
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of search results ranked by semantic similarity

        Examples:
            # Find documents about a concept
            results = search.semantic_search("how to cancel a subscription")

            # Works across different phrasings
            results = search.semantic_search("refund policy")
            # Also finds: "money back guarantee", "return policy", etc.
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)

            if not query_embedding or len(query_embedding) == 0:
                logger.error("Failed to generate query embedding")
                return []

            with self.engine.connect() as conn:
                # Build query using pgvector's cosine distance operator (<=>)
                # Use CAST instead of :: to avoid SQLAlchemy parameter conflicts
                sql = """
                    SELECT
                        id,
                        file_name,
                        file_path,
                        category,
                        title,
                        author,
                        content_preview,
                        full_content,
                        1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                    FROM documents
                    WHERE embedding IS NOT NULL
                """

                params = {"query_embedding": str(query_embedding)}

                # Add category filter if specified
                if category:
                    sql += " AND category = :category"
                    params["category"] = category

                sql += """
                    ORDER BY embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                """
                params["limit"] = limit

                result = conn.execute(text(sql), params)
                rows = result.fetchall()

                # Convert to SearchResult objects with snippet extraction
                results = []
                for row in rows:
                    # Handle NaN/inf values from similarity calculation
                    similarity = float(row[8]) if row[8] is not None else 0.0
                    if not (0.0 <= similarity <= 1.0):  # Check for valid range
                        similarity = max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

                    # Extract snippet from full content if available
                    full_content = row[7] or ""
                    if full_content:
                        snippet = self._extract_multiple_snippets(full_content, query)
                    else:
                        snippet = row[6] or ""  # Fall back to content_preview

                    results.append(SearchResult(
                        id=row[0],
                        file_name=row[1],
                        file_path=row[2],
                        category=row[3],
                        title=row[4],
                        author=row[5],
                        content_preview=snippet,
                        semantic_rank=similarity,
                        combined_score=similarity
                    ))

                logger.info(f"Semantic search for '{query}': {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        category: Optional[str] = None,
        keyword_weight: float = 0.6,
        semantic_weight: float = 0.4,
        limit: int = 20
    ) -> List[SearchResult]:
        """Perform hybrid search combining keyword and semantic search.

        This provides the best of both worlds:
        - Keyword search finds exact/partial matches (fast, precise)
        - Semantic search finds conceptually similar docs (smart, flexible)

        Args:
            query: Search query
            category: Optional category filter
            keyword_weight: Weight for keyword ranking (0-1)
            semantic_weight: Weight for semantic ranking (0-1)
            limit: Maximum results

        Returns:
            List of search results with combined ranking

        Examples:
            # Balanced hybrid search
            results = search.hybrid_search("contract amendment")

            # Favor keyword precision
            results = search.hybrid_search(
                "invoice #12345",
                keyword_weight=0.8,
                semantic_weight=0.2
            )

            # Favor semantic understanding
            results = search.hybrid_search(
                "how to return a product",
                keyword_weight=0.3,
                semantic_weight=0.7
            )
        """
        try:
            # Perform both searches
            keyword_results = self.keyword_search(query, category, limit * 2)
            semantic_results = self.semantic_search(query, category, limit * 2)

            # If semantic search failed, fall back to keyword only
            if not semantic_results:
                logger.warning("Semantic search failed, falling back to keyword search")
                return keyword_results[:limit]

            # Combine results by document ID
            doc_scores = {}

            # Add keyword results
            for result in keyword_results:
                doc_scores[result.id] = {
                    'result': result,
                    'keyword_rank': result.keyword_rank,
                    'semantic_rank': 0.0
                }

            # Add/update with semantic results
            for result in semantic_results:
                if result.id in doc_scores:
                    doc_scores[result.id]['semantic_rank'] = result.semantic_rank
                else:
                    doc_scores[result.id] = {
                        'result': result,
                        'keyword_rank': 0.0,
                        'semantic_rank': result.semantic_rank
                    }

            # Calculate combined scores
            combined_results = []
            for doc_id, data in doc_scores.items():
                combined_score = (
                    data['keyword_rank'] * keyword_weight +
                    data['semantic_rank'] * semantic_weight
                )

                result = data['result']
                result.keyword_rank = data['keyword_rank']
                result.semantic_rank = data['semantic_rank']
                result.combined_score = combined_score

                combined_results.append(result)

            # Sort by combined score
            combined_results.sort(key=lambda x: x.combined_score, reverse=True)

            # Return top results
            results = combined_results[:limit]
            logger.info(f"Hybrid search for '{query}': {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            logger.warning("Falling back to keyword search")
            return self.keyword_search(query, category, limit)

    def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        category: Optional[str] = None,
        limit: int = 20,
        **kwargs
    ) -> List[SearchResult]:
        """Unified search interface.

        Args:
            query: Search query
            mode: Search mode (keyword, semantic, or hybrid)
            category: Optional category filter
            limit: Maximum results
            **kwargs: Additional arguments for specific search modes

        Returns:
            List of search results
        """
        if mode == SearchMode.KEYWORD:
            return self.keyword_search(query, category, limit)

        elif mode == SearchMode.SEMANTIC:
            return self.semantic_search(query, category, limit)

        elif mode == SearchMode.HYBRID:
            return self.hybrid_search(
                query,
                category,
                keyword_weight=kwargs.get("keyword_weight", 0.6),
                semantic_weight=kwargs.get("semantic_weight", 0.4),
                limit=limit
            )

        else:
            raise ValueError(f"Unknown search mode: {mode}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get search index statistics.

        Returns:
            Dictionary with index statistics
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM search_statistics"))
                row = result.fetchone()

                if row:
                    return {
                        "total_documents": row[0],
                        "total_categories": row[1],
                        "documents_with_embeddings": row[2],
                        "documents_with_fts": row[3],
                        "avg_file_size_bytes": int(row[4]) if row[4] else 0,
                        "total_storage_bytes": int(row[5]) if row[5] else 0,
                        "embedding_coverage": f"{(row[2] / row[0] * 100):.1f}%" if row[0] > 0 else "0%",
                        "fts_coverage": f"{(row[3] / row[0] * 100):.1f}%" if row[0] > 0 else "0%"
                    }

                return {}

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def reindex_document(
        self,
        document_id: int,
        content: str,
        generate_embedding: bool = True
    ) -> bool:
        """Reindex a single document.

        Args:
            document_id: Document ID
            content: Document content
            generate_embedding: Generate new embedding

        Returns:
            True if successful
        """
        try:
            with self.engine.connect() as conn:
                # FTS vector is updated automatically by trigger
                # Only need to update embedding if requested
                if generate_embedding:
                    embedding = self.embedding_service.embed_text(content)

                    if embedding and len(embedding) > 0:
                        # Use CAST to avoid :: syntax conflicts with SQLAlchemy
                        sql = """
                            UPDATE documents
                            SET embedding = CAST(:embedding AS vector),
                                full_content = :content
                            WHERE id = :id
                        """

                        conn.execute(text(sql), {
                            "id": document_id,
                            "embedding": str(embedding),
                            "content": content
                        })
                        conn.commit()

                        logger.debug(f"Reindexed document {document_id}")
                        return True

                return False

        except Exception as e:
            logger.error(f"Error reindexing document {document_id}: {e}")
            return False

    def test_connection(self) -> bool:
        """Test database connection.

        Returns:
            True if connection successful
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"Connected to PostgreSQL: {version[:50]}...")

                # Check for pgvector extension
                result = conn.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                ))
                has_pgvector = result.fetchone()[0]

                if has_pgvector:
                    logger.info("pgvector extension is enabled")
                else:
                    logger.warning("pgvector extension is NOT enabled")

                return True

        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
