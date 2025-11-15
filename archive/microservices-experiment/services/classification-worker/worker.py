#!/usr/bin/env python3
"""
Classification Worker Service

Listens for 'document.uploaded' events, classifies documents using Ollama,
and publishes 'document.classified' events.
"""

import os
import sys
import requests
import tempfile
from pathlib import Path
from loguru import logger

# Add shared library to path
sys.path.insert(0, '/app/shared')

from events import EventConsumer, EventPublisher


class ClassificationWorker:
    """Worker that classifies documents using Ollama."""

    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.2-vision')
        self.categories = os.getenv(
            'CATEGORIES',
            'invoice,receipt,contract,report,other'
        ).split(',')

        # Initialize event bus
        backend = os.getenv('EVENT_BACKEND', 'rabbitmq')
        self.publisher = EventPublisher(backend=backend)
        self.consumer = EventConsumer(
            queue_name='classification-workers',
            event_patterns=['document.uploaded'],
            backend=backend
        )

        # Register event handler
        self.consumer.register_handler('document.uploaded', self.handle_document_uploaded)

        logger.info(f"Classification worker initialized (model: {self.model})")

    def handle_document_uploaded(self, payload: dict):
        """
        Handle document.uploaded event.

        Args:
            payload: Event payload with document_id, file_path, metadata
        """
        document_id = payload['document_id']
        file_path = payload['file_path']
        correlation_id = payload.get('correlation_id', document_id)

        logger.info(f"Classifying document {document_id} from {file_path}")

        try:
            # Download file from MinIO/S3
            file_content = self._download_file(file_path)

            # Classify document
            category, confidence = self._classify(file_content)

            # Publish result
            self.publisher.publish(
                event_type='document.classified',
                payload={
                    'document_id': document_id,
                    'file_path': file_path,
                    'category': category,
                    'confidence': confidence,
                    'metadata': payload.get('metadata', {})
                },
                correlation_id=correlation_id
            )

            logger.success(
                f"Document {document_id} classified as '{category}' "
                f"(confidence: {confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to classify document {document_id}: {e}")
            raise

    def _download_file(self, file_path: str) -> bytes:
        """Download file from storage."""
        if file_path.startswith('s3://') or file_path.startswith('minio://'):
            # Use boto3 to download from MinIO/S3
            import boto3
            from urllib.parse import urlparse

            parsed = urlparse(file_path)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')

            s3_client = boto3.client(
                's3',
                endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'localhost:9000')}",
                aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin')
            )

            response = s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()

        elif file_path.startswith('http://') or file_path.startswith('https://'):
            # Download from HTTP URL
            response = requests.get(file_path)
            response.raise_for_status()
            return response.content

        else:
            # Local file system
            return Path(file_path).read_bytes()

    def _classify(self, file_content: bytes) -> tuple[str, float]:
        """
        Classify document using Ollama.

        Args:
            file_content: Document file content

        Returns:
            Tuple of (category, confidence)
        """
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name

        try:
            # Prepare prompt
            prompt = f"""Classify this document into one of these categories:
{', '.join(self.categories)}

Respond with ONLY the category name, nothing else."""

            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [self._encode_image(tmp_path)],
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            category = result['response'].strip().lower()

            # Validate category
            if category not in self.categories:
                logger.warning(f"Unknown category '{category}', defaulting to 'other'")
                category = 'other'

            # Mock confidence score (Ollama doesn't provide this directly)
            # In production, you'd calculate this from logprobs or use a separate confidence model
            confidence = 0.85

            return category, confidence

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for Ollama API."""
        import base64
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def start(self):
        """Start the worker."""
        logger.info("Starting classification worker...")
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
    worker = ClassificationWorker()
    worker.start()


if __name__ == '__main__':
    main()
