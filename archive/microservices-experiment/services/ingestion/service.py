#!/usr/bin/env python3
"""
Ingestion Service

Handles document uploads, validates files, stores to MinIO,
and publishes 'document.uploaded' events to trigger processing.
"""

import os
import sys
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import List
from loguru import logger

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add shared library to path
sys.path.insert(0, '/app/shared')

from events import EventPublisher

try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    logger.warning("boto3 not available")


# Pydantic models
class UploadResponse(BaseModel):
    """Response for single file upload."""
    document_id: str
    filename: str
    size: int
    file_path: str
    message: str


class BatchUploadResponse(BaseModel):
    """Response for batch upload."""
    batch_id: str
    correlation_id: str
    total_files: int
    uploaded_files: List[UploadResponse]
    message: str


# Create FastAPI app
app = FastAPI(title="Ingestion Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize event publisher
event_publisher = None

# Initialize S3/MinIO client
s3_client = None


def get_event_publisher():
    """Get or create event publisher."""
    global event_publisher
    if event_publisher is None:
        backend = os.getenv('EVENT_BACKEND', 'rabbitmq')
        event_publisher = EventPublisher(backend=backend)
    return event_publisher


def get_s3_client():
    """Get or create S3/MinIO client."""
    global s3_client
    if s3_client is None and S3_AVAILABLE:
        s3_client = boto3.client(
            's3',
            endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'localhost:9000')}",
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        )
    return s3_client


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "s3_available": S3_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a single document.

    This endpoint:
    1. Validates the file
    2. Uploads to MinIO/S3
    3. Publishes 'document.uploaded' event
    """
    logger.info(f"Receiving upload: {file.filename}")

    try:
        # Validate file
        _validate_file(file)

        # Generate document ID
        document_id = str(uuid.uuid4())

        # Upload to storage
        file_path = await _upload_to_storage(file, document_id)

        # Get file metadata
        file_size = 0
        if hasattr(file, 'size'):
            file_size = file.size
        else:
            # Read file to get size
            content = await file.read()
            file_size = len(content)
            await file.seek(0)  # Reset for upload

        # Publish event in background
        if background_tasks:
            background_tasks.add_task(
                _publish_upload_event,
                document_id=document_id,
                file_path=file_path,
                filename=file.filename,
                size=file_size,
                mime_type=file.content_type
            )
        else:
            # Publish synchronously if no background tasks
            _publish_upload_event(
                document_id=document_id,
                file_path=file_path,
                filename=file.filename,
                size=file_size,
                mime_type=file.content_type
            )

        logger.success(f"Document {document_id} uploaded successfully")

        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            size=file_size,
            file_path=file_path,
            message="Document uploaded successfully"
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/batch-upload", response_model=BatchUploadResponse)
async def batch_upload(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload multiple documents as a batch.

    This endpoint:
    1. Validates all files
    2. Uploads to MinIO/S3
    3. Publishes 'document.uploaded' events with correlation_id for tracking
    """
    logger.info(f"Receiving batch upload: {len(files)} files")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per batch")

    batch_id = str(uuid.uuid4())
    correlation_id = batch_id  # Use batch_id as correlation_id
    uploaded_files = []

    try:
        for file in files:
            try:
                # Validate file
                _validate_file(file)

                # Generate document ID
                document_id = str(uuid.uuid4())

                # Upload to storage
                file_path = await _upload_to_storage(file, document_id)

                # Get file size
                file_size = 0
                if hasattr(file, 'size'):
                    file_size = file.size
                else:
                    content = await file.read()
                    file_size = len(content)
                    await file.seek(0)

                # Publish event with correlation_id
                if background_tasks:
                    background_tasks.add_task(
                        _publish_upload_event,
                        document_id=document_id,
                        file_path=file_path,
                        filename=file.filename,
                        size=file_size,
                        mime_type=file.content_type,
                        correlation_id=correlation_id
                    )
                else:
                    _publish_upload_event(
                        document_id=document_id,
                        file_path=file_path,
                        filename=file.filename,
                        size=file_size,
                        mime_type=file.content_type,
                        correlation_id=correlation_id
                    )

                uploaded_files.append(UploadResponse(
                    document_id=document_id,
                    filename=file.filename,
                    size=file_size,
                    file_path=file_path,
                    message="Uploaded successfully"
                ))

                logger.info(f"Uploaded {file.filename} ({document_id})")

            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {e}")
                # Continue with other files

        logger.success(
            f"Batch {batch_id} uploaded: {len(uploaded_files)}/{len(files)} successful"
        )

        return BatchUploadResponse(
            batch_id=batch_id,
            correlation_id=correlation_id,
            total_files=len(files),
            uploaded_files=uploaded_files,
            message=f"Uploaded {len(uploaded_files)}/{len(files)} files successfully"
        )

    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")


def _validate_file(file: UploadFile):
    """
    Validate uploaded file.

    Raises:
        ValueError: If file is invalid
    """
    # Check filename
    if not file.filename:
        raise ValueError("Filename is required")

    # Check file extension
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg']
    ext = Path(file.filename).suffix.lower()

    if ext not in allowed_extensions:
        raise ValueError(
            f"File type '{ext}' not allowed. "
            f"Allowed types: {', '.join(allowed_extensions)}"
        )

    # Check content type
    if file.content_type:
        allowed_mimetypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/png',
            'image/jpeg'
        ]

        if file.content_type not in allowed_mimetypes:
            logger.warning(f"Unexpected MIME type: {file.content_type}")


async def _upload_to_storage(file: UploadFile, document_id: str) -> str:
    """
    Upload file to MinIO/S3.

    Args:
        file: Uploaded file
        document_id: Unique document ID

    Returns:
        S3/MinIO file path (e.g., s3://documents/path/to/file.pdf)
    """
    client = get_s3_client()

    if not client:
        raise RuntimeError("S3/MinIO client not available")

    # Generate object key
    ext = Path(file.filename).suffix
    object_key = f"uploads/{datetime.utcnow().strftime('%Y/%m/%d')}/{document_id}{ext}"

    bucket_name = os.getenv('MINIO_BUCKET', 'documents')

    try:
        # Ensure bucket exists
        try:
            client.head_bucket(Bucket=bucket_name)
        except ClientError:
            client.create_bucket(Bucket=bucket_name)
            logger.info(f"Created bucket: {bucket_name}")

        # Upload file
        file_content = await file.read()

        client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_content,
            ContentType=file.content_type or 'application/octet-stream'
        )

        logger.debug(f"Uploaded to s3://{bucket_name}/{object_key}")

        return f"s3://{bucket_name}/{object_key}"

    except Exception as e:
        logger.error(f"Failed to upload to storage: {e}")
        raise


def _publish_upload_event(
    document_id: str,
    file_path: str,
    filename: str,
    size: int,
    mime_type: str,
    correlation_id: str = None
):
    """
    Publish 'document.uploaded' event.

    Args:
        document_id: Unique document ID
        file_path: S3/MinIO file path
        filename: Original filename
        size: File size in bytes
        mime_type: MIME type
        correlation_id: Optional correlation ID for batch tracking
    """
    publisher = get_event_publisher()

    payload = {
        'document_id': document_id,
        'file_path': file_path,
        'metadata': {
            'filename': filename,
            'size_bytes': size,
            'mime_type': mime_type,
            'uploaded_at': datetime.utcnow().isoformat()
        }
    }

    publisher.publish(
        event_type='document.uploaded',
        payload=payload,
        correlation_id=correlation_id or document_id
    )

    logger.info(
        f"Published document.uploaded event for {document_id} "
        f"(correlation_id: {correlation_id or document_id})"
    )


def main():
    """Main entry point."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=os.getenv('LOG_LEVEL', 'INFO')
    )

    # Run FastAPI server
    port = int(os.getenv('PORT', '8000'))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


if __name__ == '__main__':
    main()
