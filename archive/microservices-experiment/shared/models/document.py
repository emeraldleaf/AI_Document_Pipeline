"""
SQLModel models for document metadata.

Combines Pydantic validation with SQLAlchemy ORM for type-safe database operations.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import Index


class DocumentBase(SQLModel):
    """Base model with common fields."""
    document_id: str = Field(unique=True, index=True, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    file_path: Optional[str] = Field(default=None, max_length=500)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    indexed: bool = Field(default=False)


class Document(DocumentBase, table=True):
    """
    Document metadata table.

    Stores processing status, category, confidence scores,
    and extracted metadata for each document.
    """
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Processing metadata
    extraction_method: Optional[str] = Field(default=None, max_length=50)
    processing_status: str = Field(default="pending", max_length=50)

    # Extracted metadata (JSON field)
    metadata_: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, name="metadata")
    )

    # Error tracking
    error_message: Optional[str] = Field(default=None, max_length=1000)
    retry_count: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: Optional[datetime] = Field(default=None)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


# Create indexes for common queries
Index('idx_document_id', Document.document_id, unique=True)
Index('idx_category', Document.category)
Index('idx_processing_status', Document.processing_status)
Index('idx_created_at', Document.created_at)


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""
    pass


class DocumentRead(DocumentBase):
    """Model for reading document data (includes all fields)."""
    id: int
    extraction_method: Optional[str] = None
    processing_status: str
    metadata_: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime] = None


class DocumentUpdate(SQLModel):
    """Model for updating document data (all fields optional)."""
    category: Optional[str] = None
    file_path: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    indexed: Optional[bool] = None
    extraction_method: Optional[str] = None
    processing_status: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    indexed_at: Optional[datetime] = None


class BatchJob(SQLModel, table=True):
    """
    Batch job tracking.

    Stores state for batch uploads with correlation IDs.
    """
    __tablename__ = "batch_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: str = Field(unique=True, index=True, max_length=255)
    correlation_id: str = Field(index=True, max_length=255)

    # Progress tracking
    total_documents: int = Field(default=0)
    completed_documents: int = Field(default=0)
    failed_documents: int = Field(default=0)

    # Status
    status: str = Field(default="pending", max_length=50)  # pending, processing, completed, failed

    # Metadata
    batch_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, name="metadata")
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)


Index('idx_batch_id', BatchJob.batch_id, unique=True)
Index('idx_correlation_id', BatchJob.correlation_id)
Index('idx_batch_status', BatchJob.status)
