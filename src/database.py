"""Optional database support for storing document metadata and classifications."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json

from loguru import logger

# Import embedding service for automatic embedding generation
try:
    from src.embedding_service import EmbeddingService
    EMBEDDING_SERVICE_AVAILABLE = True
except ImportError:
    EMBEDDING_SERVICE_AVAILABLE = False
    logger.warning("Embedding service not available")

try:
    import sqlalchemy as sa
    from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, JSON
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("SQLAlchemy not installed. Database features disabled.")


if DATABASE_AVAILABLE:
    Base = declarative_base()

    class Document(Base):
        """Document metadata and classification results."""

        __tablename__ = "documents"

        id = Column(Integer, primary_key=True, autoincrement=True)

        # File information
        file_path = Column(String(500), nullable=False, index=True)
        file_name = Column(String(255), nullable=False, index=True)
        file_type = Column(String(50))
        file_size = Column(Integer)
        file_hash = Column(String(64), index=True)  # SHA256 hash

        # Timestamps
        created_date = Column(DateTime)
        modified_date = Column(DateTime)
        processed_date = Column(DateTime, default=datetime.now, index=True)

        # Document metadata
        author = Column(String(255))
        title = Column(String(500))
        page_count = Column(Integer)

        # Classification
        category = Column(String(100), nullable=False, index=True)
        confidence = Column(Text)
        model_used = Column(String(100))

        # Content
        content_preview = Column(Text)  # First 1000 chars
        full_content = Column(Text)  # Optional: store full text
        metadata_json = Column(JSON)  # Additional metadata

        # Organization
        output_path = Column(String(500))
        is_organized = Column(Boolean, default=False)

        # Auditing
        classification_time = Column(Float)  # Time in seconds

        # Vector embedding for semantic search (pgvector type)
        # Note: This uses the existing 'embedding' column in the database
        # The column was created by migrations, not by SQLAlchemy
        embedding = Column(Text)  # Stored as array, actual type is vector(768) in PostgreSQL

        def __repr__(self):
            return f"<Document(id={self.id}, name='{self.file_name}', category='{self.category}')>"

        def to_dict(self) -> Dict[str, Any]:
            """Convert to dictionary."""
            return {
                "id": self.id,
                "file_path": self.file_path,
                "file_name": self.file_name,
                "file_type": self.file_type,
                "file_size": self.file_size,
                "category": self.category,
                "confidence": self.confidence,
                "author": self.author,
                "title": self.title,
                "page_count": self.page_count,
                "processed_date": self.processed_date.isoformat() if self.processed_date else None,
                "output_path": self.output_path,
                "is_organized": self.is_organized,
                "full_content": self.full_content,  # Include full content for modal view
                "content_preview": self.content_preview,
            }


    class ClassificationHistory(Base):
        """Track classification history for model improvement."""

        __tablename__ = "classification_history"

        id = Column(Integer, primary_key=True, autoincrement=True)
        document_id = Column(Integer, index=True)

        timestamp = Column(DateTime, default=datetime.now, index=True)

        # Classification details
        predicted_category = Column(String(100), nullable=False)
        correct_category = Column(String(100))
        was_corrected = Column(Boolean, default=False)

        # Model info
        model_name = Column(String(100))
        confidence_score = Column(Text)

        # Performance
        processing_time = Column(Float)

        def __repr__(self):
            return f"<ClassificationHistory(id={self.id}, doc_id={self.document_id}, category='{self.predicted_category}')>"


class DatabaseService:
    """Service for interacting with the document database."""

    def __init__(self, database_url: str = "sqlite:///documents.db", echo: bool = False, auto_generate_embeddings: bool = True):
        """Initialize database service.

        Args:
            database_url: SQLAlchemy database URL
            echo: Echo SQL statements (for debugging)
            auto_generate_embeddings: Automatically generate embeddings when adding documents (default: True)
        """
        if not DATABASE_AVAILABLE:
            raise ImportError(
                "SQLAlchemy is required for database features. "
                "Install with: pip install sqlalchemy"
            )

        self.engine = create_engine(database_url, echo=echo)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.auto_generate_embeddings = auto_generate_embeddings

        # Initialize embedding service if auto-generation is enabled
        self.embedding_service = None
        if auto_generate_embeddings and EMBEDDING_SERVICE_AVAILABLE:
            try:
                from config import settings
                # Use the factory to create the embedding service
                if settings.embedding_provider == "ollama":
                    from src.embedding_service import OllamaEmbeddingService
                    self.embedding_service = OllamaEmbeddingService(
                        host=settings.ollama_host,
                        model=settings.embedding_model,
                        dimension=settings.embedding_dimension
                    )
                elif settings.embedding_provider == "openai":
                    from src.embedding_service import OpenAIEmbeddingService
                    self.embedding_service = OpenAIEmbeddingService(
                        api_key=settings.openai_api_key,
                        model=settings.embedding_model,
                        dimension=settings.embedding_dimension
                    )
                logger.info(f"Embedding service initialized ({settings.embedding_provider}) for automatic embedding generation")
            except Exception as e:
                logger.warning(f"Could not initialize embedding service: {e}")
                logger.warning("Embeddings will not be generated automatically")

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        logger.info(f"Database initialized: {database_url}")

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def add_document(
        self,
        file_path: Path,
        category: str,
        content: str,
        metadata: Dict[str, Any],
        confidence: Optional[str] = None,
        model_used: Optional[str] = None,
        classification_time: Optional[float] = None,
        store_full_content: bool = False,
    ) -> int:
        """Add a classified document to the database.

        Args:
            file_path: Path to document
            category: Classification category
            content: Document content
            metadata: Document metadata
            confidence: Classification confidence/reasoning
            model_used: Name of model used
            classification_time: Time taken to classify
            store_full_content: Store full content (can be large)

        Returns:
            Document ID
        """
        session = self.get_session()

        try:
            # Calculate file hash for deduplication
            import hashlib
            file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

            # Generate embedding if enabled and service is available
            embedding = None
            if self.auto_generate_embeddings and self.embedding_service and content:
                try:
                    # Truncate content to avoid Ollama errors (max 2000 chars)
                    content_for_embedding = content[:2000] if len(content) > 2000 else content
                    embedding = self.embedding_service.embed_text(content_for_embedding)
                    logger.info(f"✓ Generated embedding for {file_path.name} ({len(embedding)} dimensions)")
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for {file_path.name}: {e}")
                    logger.warning("Document will be added without embedding")

            doc = Document(
                file_path=str(file_path),
                file_name=file_path.name,
                file_type=metadata.get("file_type"),
                file_size=metadata.get("file_size"),
                file_hash=file_hash,
                created_date=metadata.get("created_date"),
                modified_date=metadata.get("modified_date"),
                author=metadata.get("author"),
                title=metadata.get("title"),
                page_count=metadata.get("page_count"),
                category=category,
                confidence=confidence,
                model_used=model_used,
                content_preview=content[:1000] if content else None,
                full_content=content if store_full_content else None,
                metadata_json=metadata,
                classification_time=classification_time,
                embedding=embedding,  # Add the generated embedding
            )

            session.add(doc)
            session.commit()

            doc_id = doc.id
            embedding_status = "with embedding" if embedding else "without embedding"
            logger.debug(f"Added document to database: {file_path.name} (ID: {doc_id}) {embedding_status}")

            return doc_id

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add document to database: {e}")
            raise
        finally:
            session.close()

    def update_document_path(self, doc_id: int, output_path: Path):
        """Update document output path after organization.

        Args:
            doc_id: Document ID
            output_path: New output path
        """
        session = self.get_session()

        try:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.output_path = str(output_path)
                doc.is_organized = True
                session.commit()
                logger.debug(f"Updated document path: {doc_id} -> {output_path}")
        finally:
            session.close()

    def get_document_by_id(self, doc_id: int) -> Optional[Dict]:
        """Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document dict or None
        """
        session = self.get_session()

        try:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            return doc.to_dict() if doc else None
        finally:
            session.close()

    def get_documents_by_category(self, category: str, limit: int = 100) -> List[Dict]:
        """Get documents by category.

        Args:
            category: Category name
            limit: Maximum results

        Returns:
            List of document dicts
        """
        session = self.get_session()

        try:
            docs = (
                session.query(Document)
                .filter(Document.category == category)
                .order_by(Document.processed_date.desc())
                .limit(limit)
                .all()
            )
            return [doc.to_dict() for doc in docs]
        finally:
            session.close()

    def search_documents(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Search documents by content or metadata.

        Args:
            query: Search query
            category: Filter by category
            limit: Maximum results

        Returns:
            List of matching documents
        """
        session = self.get_session()

        try:
            q = session.query(Document)

            # Search in multiple fields
            search_filter = sa.or_(
                Document.file_name.ilike(f"%{query}%"),
                Document.title.ilike(f"%{query}%"),
                Document.author.ilike(f"%{query}%"),
                Document.content_preview.ilike(f"%{query}%"),
            )

            q = q.filter(search_filter)

            if category:
                q = q.filter(Document.category == category)

            docs = q.order_by(Document.processed_date.desc()).limit(limit).all()

            return [doc.to_dict() for doc in docs]
        finally:
            session.close()

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Statistics dict
        """
        session = self.get_session()

        try:
            total_docs = session.query(Document).count()

            # Count by category
            category_counts = {}
            categories = session.query(Document.category).distinct().all()
            for (cat,) in categories:
                count = session.query(Document).filter(Document.category == cat).count()
                category_counts[cat] = count

            # Recent documents
            recent_count = (
                session.query(Document)
                .filter(Document.processed_date >= datetime.now().replace(hour=0, minute=0, second=0))
                .count()
            )

            # Organized vs unorganized
            organized_count = session.query(Document).filter(Document.is_organized == True).count()

            return {
                "total_documents": total_docs,
                "by_category": category_counts,
                "processed_today": recent_count,
                "organized": organized_count,
                "unorganized": total_docs - organized_count,
            }
        finally:
            session.close()

    def add_classification_history(
        self,
        document_id: int,
        predicted_category: str,
        correct_category: Optional[str] = None,
        model_name: Optional[str] = None,
        confidence: Optional[str] = None,
        processing_time: Optional[float] = None,
    ):
        """Record classification in history for tracking.

        Args:
            document_id: Document ID
            predicted_category: Predicted category
            correct_category: Correct category (if different)
            model_name: Model used
            confidence: Confidence score
            processing_time: Processing time
        """
        session = self.get_session()

        try:
            history = ClassificationHistory(
                document_id=document_id,
                predicted_category=predicted_category,
                correct_category=correct_category or predicted_category,
                was_corrected=correct_category is not None and correct_category != predicted_category,
                model_name=model_name,
                confidence_score=confidence,
                processing_time=processing_time,
            )

            session.add(history)
            session.commit()
        finally:
            session.close()

    def get_accuracy_over_time(self, days: int = 30) -> Dict[str, List]:
        """Get classification accuracy over time.

        Args:
            days: Number of days to analyze

        Returns:
            Accuracy data by date
        """
        session = self.get_session()

        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)

            history = (
                session.query(ClassificationHistory)
                .filter(ClassificationHistory.timestamp >= start_date)
                .all()
            )

            # Group by date
            by_date = {}
            for h in history:
                date_key = h.timestamp.date().isoformat()
                if date_key not in by_date:
                    by_date[date_key] = {"correct": 0, "total": 0}

                by_date[date_key]["total"] += 1
                if not h.was_corrected:
                    by_date[date_key]["correct"] += 1

            # Calculate accuracy
            accuracy_data = {
                "dates": [],
                "accuracy": [],
                "total": [],
            }

            for date in sorted(by_date.keys()):
                stats = by_date[date]
                accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0

                accuracy_data["dates"].append(date)
                accuracy_data["accuracy"].append(accuracy)
                accuracy_data["total"].append(stats["total"])

            return accuracy_data
        finally:
            session.close()

    def export_to_json(self, output_file: Path, limit: Optional[int] = None):
        """Export database to JSON.

        Args:
            output_file: Output file path
            limit: Limit number of records (None = all)
        """
        session = self.get_session()

        try:
            q = session.query(Document).order_by(Document.processed_date.desc())
            if limit:
                q = q.limit(limit)

            docs = q.all()
            data = [doc.to_dict() for doc in docs]

            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.success(f"Exported {len(data)} documents to {output_file}")
        finally:
            session.close()

    def clear_database(self):
        """Clear all data from database (use with caution!)."""
        session = self.get_session()

        try:
            session.query(ClassificationHistory).delete()
            session.query(Document).delete()
            session.commit()
            logger.warning("Database cleared!")
        finally:
            session.close()


def check_database_available() -> bool:
    """Check if database features are available."""
    return DATABASE_AVAILABLE
