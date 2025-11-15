"""
Document Chunking for Efficient Embedding Generation

Implements intelligent document chunking to:
1. Handle documents of any size
2. Preserve context across chunk boundaries
3. Optimize for embedding model limits
4. Enable efficient semantic search
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata."""
    chunk_id: str
    document_id: int
    chunk_index: int
    content: str
    char_start: int
    char_end: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for storage."""
        return {
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'char_start': self.char_start,
            'char_end': self.char_end,
            'file_name': self.metadata.get('file_name'),
            'category': self.metadata.get('category'),
            'title': self.metadata.get('title'),
            'author': self.metadata.get('author'),
        }


class DocumentChunker:
    """
    Intelligent document chunker for embedding generation.

    Features:
    - Configurable chunk size (default: 800 chars for nomic-embed-text)
    - Overlap between chunks to preserve context
    - Smart splitting on sentence/paragraph boundaries
    - Metadata preservation for each chunk
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        min_chunk_size: int = 100,
        split_on_sentences: bool = True
    ):
        """
        Initialize document chunker.

        Args:
            chunk_size: Target size for each chunk (chars)
            chunk_overlap: Overlap between consecutive chunks (chars)
            min_chunk_size: Minimum chunk size to keep (chars)
            split_on_sentences: Try to split on sentence boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.split_on_sentences = split_on_sentences

        # Sentence boundary pattern
        self.sentence_pattern = re.compile(r'[.!?]+[\s\n]+')

    def chunk_document(
        self,
        document_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk a document into manageable pieces.

        Args:
            document_id: Unique document identifier
            content: Full document content
            metadata: Document metadata (file_name, category, etc.)

        Returns:
            List of document chunks
        """
        if not content or len(content.strip()) == 0:
            return []

        metadata = metadata or {}
        chunks = []

        # For short documents, return as single chunk
        if len(content) <= self.chunk_size:
            chunks.append(DocumentChunk(
                chunk_id=f"doc_{document_id}_chunk_0",
                document_id=document_id,
                chunk_index=0,
                content=content,
                char_start=0,
                char_end=len(content),
                metadata=metadata
            ))
            return chunks

        # For longer documents, split intelligently
        if self.split_on_sentences:
            chunks = self._chunk_by_sentences(document_id, content, metadata)
        else:
            chunks = self._chunk_by_size(document_id, content, metadata)

        return chunks

    def _chunk_by_sentences(
        self,
        document_id: int,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Chunk document by sentence boundaries for better context preservation.
        """
        chunks = []

        # Split into sentences
        sentences = self.sentence_pattern.split(content)

        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence exceeds chunk size
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size:
                # Save current chunk if it meets minimum size
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(DocumentChunk(
                        chunk_id=f"doc_{document_id}_chunk_{chunk_index}",
                        document_id=document_id,
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        char_start=current_start,
                        char_end=current_start + len(current_chunk),
                        metadata=metadata
                    ))

                    # Calculate overlap for next chunk
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                    current_start = current_start + len(current_chunk) - len(overlap_text) - len(sentence) - 1
                    chunk_index += 1
                else:
                    # Chunk too small, keep building
                    current_chunk += " " + sentence
            else:
                # Add sentence to current chunk
                current_chunk += " " + sentence if current_chunk else sentence

        # Add final chunk
        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(DocumentChunk(
                chunk_id=f"doc_{document_id}_chunk_{chunk_index}",
                document_id=document_id,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                char_start=current_start,
                char_end=current_start + len(current_chunk),
                metadata=metadata
            ))

        return chunks

    def _chunk_by_size(
        self,
        document_id: int,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Chunk document by fixed size with overlap (fallback method).
        """
        chunks = []
        chunk_index = 0

        start = 0
        while start < len(content):
            # Calculate chunk end
            end = min(start + self.chunk_size, len(content))

            # Extract chunk
            chunk_content = content[start:end].strip()

            if len(chunk_content) >= self.min_chunk_size:
                chunks.append(DocumentChunk(
                    chunk_id=f"doc_{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    char_start=start,
                    char_end=end,
                    metadata=metadata
                ))
                chunk_index += 1

            # Move to next chunk with overlap
            start = end - self.chunk_overlap

        return chunks

    def chunk_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """
        Chunk multiple documents in batch.

        Args:
            documents: List of documents with 'id', 'full_content', and metadata

        Returns:
            List of all chunks from all documents
        """
        all_chunks = []

        for doc in documents:
            doc_id = doc.get('id')
            content = doc.get('full_content', '')

            metadata = {
                'file_name': doc.get('file_name'),
                'category': doc.get('category'),
                'title': doc.get('title'),
                'author': doc.get('author'),
                'file_type': doc.get('file_type'),
            }

            chunks = self.chunk_document(doc_id, content, metadata)
            all_chunks.extend(chunks)

        return all_chunks


# Preset configurations for different use cases
CHUNKING_PRESETS = {
    'ollama_nomic': {
        'chunk_size': 700,      # Safe for nomic-embed-text (~2500 char limit)
        'chunk_overlap': 100,
        'min_chunk_size': 100,
        'split_on_sentences': True
    },
    'ollama_mxbai': {
        'chunk_size': 700,      # Safe for mxbai-embed-large (~2500 char limit, 1024 dims)
        'chunk_overlap': 100,
        'min_chunk_size': 100,
        'split_on_sentences': True
    },
    'openai_small': {
        'chunk_size': 1500,     # OpenAI text-embedding-3-small
        'chunk_overlap': 200,
        'min_chunk_size': 100,
        'split_on_sentences': True
    },
    'openai_large': {
        'chunk_size': 2000,     # OpenAI text-embedding-3-large
        'chunk_overlap': 200,
        'min_chunk_size': 100,
        'split_on_sentences': True
    },
    'aggressive': {
        'chunk_size': 500,      # Small chunks for precise retrieval
        'chunk_overlap': 50,
        'min_chunk_size': 50,
        'split_on_sentences': True
    }
}


def get_chunker(preset: str = 'ollama_mxbai') -> DocumentChunker:
    """
    Get a pre-configured document chunker.

    Args:
        preset: One of 'ollama_mxbai', 'ollama_nomic', 'openai_small', 'openai_large', 'aggressive'

    Returns:
        Configured DocumentChunker instance
    """
    if preset not in CHUNKING_PRESETS:
        raise ValueError(f"Unknown preset: {preset}. Available: {list(CHUNKING_PRESETS.keys())}")

    config = CHUNKING_PRESETS[preset]
    return DocumentChunker(**config)
