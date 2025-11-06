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

    def _extract_snippet(
        self,
        full_text: str,
        query: str,
        context_sentences: int = 2,
        max_snippet_length: int = 500
    ) -> str:
        """Extract relevant snippet from text showing matches with context.

        Args:
            full_text: Full document text
            query: Search query
            context_sentences: Number of sentences before/after match to include
            max_snippet_length: Maximum length of snippet

        Returns:
            Text snippet with matching context
        """
        if not full_text:
            return ""

        # Split query into terms
        query_terms = query.lower().split()
        text_lower = full_text.lower()

        # Find first occurrence of any query term
        first_match_pos = -1
        matched_term = ""
        for term in query_terms:
            if len(term) < 3:  # Skip very short terms
                continue
            pos = text_lower.find(term)
            if pos != -1 and (first_match_pos == -1 or pos < first_match_pos):
                first_match_pos = pos
                matched_term = term

        # If no match found, return beginning of document
        if first_match_pos == -1:
            return full_text[:max_snippet_length] + ("..." if len(full_text) > max_snippet_length else "")

        # Split text into sentences (simple approach)
        import re
        sentences = re.split(r'(?<=[.!?])\s+', full_text)

        # Find which sentence contains the match
        char_count = 0
        match_sentence_idx = 0
        for i, sentence in enumerate(sentences):
            char_count += len(sentence) + 1  # +1 for space
            if char_count > first_match_pos:
                match_sentence_idx = i
                break

        # Get context sentences before and after
        start_idx = max(0, match_sentence_idx - context_sentences)
        end_idx = min(len(sentences), match_sentence_idx + context_sentences + 1)

        # Build snippet
        snippet_sentences = sentences[start_idx:end_idx]
        snippet = " ".join(snippet_sentences)

        # Truncate if too long
        if len(snippet) > max_snippet_length:
            snippet = snippet[:max_snippet_length] + "..."

        # Add ellipsis at start if not beginning of document
        if start_idx > 0:
            snippet = "..." + snippet

        return snippet

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
                        snippet = self._extract_snippet(full_content, query)
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
                        snippet = self._extract_snippet(full_content, query)
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
