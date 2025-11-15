#!/usr/bin/env python3
"""
Indexing Worker Service

Listens for 'document.extracted' events, generates embeddings,
indexes to OpenSearch, updates PostgreSQL, and publishes 'document.indexed' events.
"""

import os
import sys
import json
import requests
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

# Add shared library to path
sys.path.insert(0, '/app/shared')

from events import EventConsumer, EventPublisher
from models.document import Document as DocumentModel

try:
    from opensearchpy import OpenSearch, helpers
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    logger.warning("OpenSearch not available")

try:
    from sqlmodel import Session, create_engine, select, SQLModel
    from datetime import datetime
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("PostgreSQL/SQLModel not available")


class IndexingWorker:
    """Worker that indexes documents to OpenSearch and PostgreSQL."""

    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')

        # Initialize OpenSearch
        if OPENSEARCH_AVAILABLE:
            opensearch_url = os.getenv('OPENSEARCH_URL', 'http://localhost:9200')
            self.opensearch_client = OpenSearch(
                hosts=[opensearch_url],
                http_compress=True,
                use_ssl=False,
                verify_certs=False
            )
            self.index_name = os.getenv('OPENSEARCH_INDEX', 'documents')
            self._ensure_index_exists()
            logger.info("OpenSearch client initialized")
        else:
            self.opensearch_client = None

        # Initialize PostgreSQL
        if POSTGRES_AVAILABLE:
            postgres_url = os.getenv('POSTGRES_URL', 'postgresql://postgres:password@localhost:5432/documents')
            self.db_engine = create_engine(postgres_url)
            logger.info("PostgreSQL connection initialized")
        else:
            self.db_engine = None

        # Initialize event bus
        backend = os.getenv('EVENT_BACKEND', 'rabbitmq')
        self.publisher = EventPublisher(backend=backend)
        self.consumer = EventConsumer(
            queue_name='indexing-workers',
            event_patterns=['document.extracted'],
            backend=backend
        )

        # Register event handler
        self.consumer.register_handler('document.extracted', self.handle_document_extracted)

        logger.info("Indexing worker initialized")

    def _ensure_index_exists(self):
        """Create OpenSearch index if it doesn't exist."""
        if not self.opensearch_client:
            return

        if self.opensearch_client.indices.exists(index=self.index_name):
            logger.info(f"Index '{self.index_name}' already exists")
            return

        # Create index with mapping
        mapping = {
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "file_path": {"type": "keyword"},
                    "metadata": {"type": "object", "enabled": True},
                    "text": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 768,  # nomic-embed-text dimension
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    "confidence": {"type": "float"},
                    "extraction_method": {"type": "keyword"},
                    "indexed_at": {"type": "date"},
                }
            }
        }

        self.opensearch_client.indices.create(index=self.index_name, body=mapping)
        logger.info(f"Created index '{self.index_name}'")

    def handle_document_extracted(self, payload: Dict[str, Any]):
        """
        Handle document.extracted event.

        Args:
            payload: Event payload with document_id, metadata, category
        """
        document_id = payload['document_id']
        file_path = payload['file_path']
        category = payload['category']
        metadata = payload['metadata']
        confidence = payload.get('confidence', 0.0)
        extraction_method = payload.get('extraction_method', 'unknown')
        correlation_id = payload.get('correlation_id', document_id)

        logger.info(
            f"Indexing document {document_id} "
            f"(category: {category}, confidence: {confidence:.2f})"
        )

        try:
            # Generate embedding
            text = self._prepare_text_for_embedding(metadata)
            embedding = self._generate_embedding(text)

            # Index to OpenSearch
            opensearch_success = self._index_to_opensearch(
                document_id=document_id,
                category=category,
                file_path=file_path,
                metadata=metadata,
                text=text,
                embedding=embedding,
                confidence=confidence,
                extraction_method=extraction_method
            )

            # Update PostgreSQL
            postgres_success = self._update_postgres(
                document_id=document_id,
                category=category,
                metadata=metadata,
                confidence=confidence,
                indexed=opensearch_success
            )

            # Publish completion event
            self.publisher.publish(
                event_type='document.indexed',
                payload={
                    'document_id': document_id,
                    'file_path': file_path,
                    'category': category,
                    'confidence': confidence,
                    'opensearch_indexed': opensearch_success,
                    'postgres_updated': postgres_success,
                    'indexed_at': datetime.utcnow().isoformat()
                },
                correlation_id=correlation_id
            )

            logger.success(
                f"Document {document_id} indexed successfully "
                f"(OpenSearch: {opensearch_success}, PostgreSQL: {postgres_success})"
            )

        except Exception as e:
            logger.error(f"Failed to index document {document_id}: {e}")
            raise

    def _prepare_text_for_embedding(self, metadata: Dict[str, Any]) -> str:
        """
        Prepare text from metadata for embedding generation.

        Args:
            metadata: Extracted metadata

        Returns:
            Combined text for embedding
        """
        # Combine relevant text fields
        text_parts = []

        # Add raw text if available
        if 'text' in metadata:
            text_parts.append(str(metadata['text']))

        # Add structured fields
        for key, value in metadata.items():
            if key == 'text':
                continue
            if value and isinstance(value, (str, int, float)):
                text_parts.append(f"{key}: {value}")

        combined_text = '\n'.join(text_parts)

        # Truncate if too long (max ~8000 chars for embedding)
        max_length = 8000
        if len(combined_text) > max_length:
            combined_text = combined_text[:max_length]

        return combined_text

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using Ollama.

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            embedding = result['embedding']

            logger.debug(f"Generated embedding of dimension {len(embedding)}")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 768

    def _index_to_opensearch(
        self,
        document_id: str,
        category: str,
        file_path: str,
        metadata: Dict[str, Any],
        text: str,
        embedding: List[float],
        confidence: float,
        extraction_method: str
    ) -> bool:
        """
        Index document to OpenSearch.

        Returns:
            True if successful, False otherwise
        """
        if not self.opensearch_client:
            logger.warning("OpenSearch not available, skipping indexing")
            return False

        try:
            doc = {
                "document_id": document_id,
                "category": category,
                "file_path": file_path,
                "metadata": metadata,
                "text": text[:10000],  # Limit text size
                "embedding": embedding,
                "confidence": confidence,
                "extraction_method": extraction_method,
                "indexed_at": datetime.utcnow().isoformat()
            }

            self.opensearch_client.index(
                index=self.index_name,
                id=document_id,
                body=doc
            )

            logger.debug(f"Indexed document {document_id} to OpenSearch")

            return True

        except Exception as e:
            logger.error(f"Failed to index to OpenSearch: {e}")
            return False

    def _update_postgres(
        self,
        document_id: str,
        category: str,
        metadata: Dict[str, Any],
        confidence: float,
        indexed: bool
    ) -> bool:
        """
        Update document status in PostgreSQL using SQLModel.

        Returns:
            True if successful, False otherwise
        """
        if not self.db_engine:
            logger.warning("PostgreSQL not available, skipping update")
            return False

        try:
            # Ensure table exists
            SQLModel.metadata.create_all(self.db_engine)

            with Session(self.db_engine) as session:
                # Try to find existing document
                statement = select(DocumentModel).where(
                    DocumentModel.document_id == document_id
                )
                existing_doc = session.exec(statement).first()

                if existing_doc:
                    # Update existing
                    existing_doc.category = category
                    existing_doc.metadata_ = metadata
                    existing_doc.confidence = confidence
                    existing_doc.indexed = indexed
                    existing_doc.extraction_method = existing_doc.extraction_method or "unknown"
                    existing_doc.processing_status = "indexed" if indexed else "processing"
                    existing_doc.updated_at = datetime.utcnow()
                    existing_doc.indexed_at = datetime.utcnow() if indexed else None
                else:
                    # Create new document
                    doc = DocumentModel(
                        document_id=document_id,
                        category=category,
                        metadata_=metadata,
                        confidence=confidence,
                        indexed=indexed,
                        extraction_method="unknown",
                        processing_status="indexed" if indexed else "processing",
                        indexed_at=datetime.utcnow() if indexed else None
                    )
                    session.add(doc)

                session.commit()
                logger.debug(f"Updated document {document_id} in PostgreSQL")

                return True

        except Exception as e:
            logger.error(f"Failed to update PostgreSQL: {e}")
            return False

    def start(self):
        """Start the worker."""
        logger.info("Starting indexing worker...")
        self.consumer.start()


def main():
    """Main entry point."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=os.getenv('LOG_LEVEL', 'INFO')
    )

    # Create and start worker
    worker = IndexingWorker()
    worker.start()


if __name__ == '__main__':
    main()
