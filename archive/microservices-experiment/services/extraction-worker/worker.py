#!/usr/bin/env python3
"""
Extraction Worker Service

Listens for 'document.classified' events, extracts structured metadata
using Docling + LLM, and publishes 'document.extracted' events.
"""

import os
import sys
import json
import requests
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

# Add shared library to path
sys.path.insert(0, '/app/shared')

from events import EventConsumer, EventPublisher

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning("Docling not available, using basic extraction")


class ExtractionWorker:
    """Worker that extracts structured metadata from documents."""

    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        self.use_llm = os.getenv('USE_LLM', 'true').lower() == 'true'

        # Initialize Docling converter if available
        if DOCLING_AVAILABLE:
            self.converter = DocumentConverter()
            logger.info("Docling converter initialized")
        else:
            self.converter = None

        # Initialize event bus
        backend = os.getenv('EVENT_BACKEND', 'rabbitmq')
        self.publisher = EventPublisher(backend=backend)
        self.consumer = EventConsumer(
            queue_name='extraction-workers',
            event_patterns=['document.classified'],
            backend=backend
        )

        # Register event handler
        self.consumer.register_handler('document.classified', self.handle_document_classified)

        logger.info(f"Extraction worker initialized (LLM: {self.use_llm})")

    def handle_document_classified(self, payload: Dict[str, Any]):
        """
        Handle document.classified event.

        Args:
            payload: Event payload with document_id, category, file_path
        """
        document_id = payload['document_id']
        file_path = payload['file_path']
        category = payload['category']
        correlation_id = payload.get('correlation_id', document_id)

        logger.info(
            f"Extracting metadata from document {document_id} "
            f"(category: {category})"
        )

        try:
            # Download file
            file_content = self._download_file(file_path)

            # Extract metadata
            metadata, confidence = self._extract_metadata(
                file_content,
                category
            )

            # Publish result
            self.publisher.publish(
                event_type='document.extracted',
                payload={
                    'document_id': document_id,
                    'file_path': file_path,
                    'category': category,
                    'metadata': metadata,
                    'confidence': confidence,
                    'extraction_method': 'docling+llm' if self.use_llm else 'docling'
                },
                correlation_id=correlation_id
            )

            logger.success(
                f"Document {document_id} metadata extracted "
                f"(confidence: {confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to extract metadata from document {document_id}: {e}")
            raise

    def _download_file(self, file_path: str) -> bytes:
        """Download file from storage."""
        if file_path.startswith('s3://') or file_path.startswith('minio://'):
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
            response = requests.get(file_path)
            response.raise_for_status()
            return response.content

        else:
            return Path(file_path).read_bytes()

    def _extract_metadata(
        self,
        file_content: bytes,
        category: str
    ) -> tuple[Dict[str, Any], float]:
        """
        Extract structured metadata from document.

        Args:
            file_content: Document file content
            category: Document category

        Returns:
            Tuple of (metadata dict, confidence score)
        """
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name

        try:
            # Step 1: Extract text and structure with Docling
            text, structure = self._extract_with_docling(tmp_path)

            # Step 2: Extract structured metadata with LLM
            if self.use_llm and text:
                metadata = self._extract_with_llm(text, category)
                confidence = 0.85  # Base confidence for LLM extraction
            else:
                metadata = {
                    'text': text,
                    'structure': structure,
                    'category': category
                }
                confidence = 0.70  # Lower confidence without LLM

            return metadata, confidence

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _extract_with_docling(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """
        Extract text and structure using Docling.

        Returns:
            Tuple of (text, structure dict)
        """
        if not self.converter:
            logger.warning("Docling not available, using basic extraction")
            return self._basic_text_extraction(file_path), {}

        try:
            result = self.converter.convert(file_path)

            # Extract text
            text = result.document.export_to_markdown()

            # Extract structure
            structure = {
                'num_pages': len(result.document.pages) if hasattr(result.document, 'pages') else 0,
                'has_tables': False,
                'has_images': False,
                'layout': 'document'
            }

            # Check for tables
            if hasattr(result.document, 'tables') and result.document.tables:
                structure['has_tables'] = True
                structure['num_tables'] = len(result.document.tables)

            # Check for images
            if hasattr(result.document, 'pictures') and result.document.pictures:
                structure['has_images'] = True
                structure['num_images'] = len(result.document.pictures)

            logger.debug(f"Docling extracted {len(text)} chars, structure: {structure}")

            return text, structure

        except Exception as e:
            logger.error(f"Docling extraction failed: {e}")
            return self._basic_text_extraction(file_path), {}

    def _basic_text_extraction(self, file_path: str) -> str:
        """Basic text extraction using pypdf or pdfplumber."""
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = '\n\n'.join(page.extract_text() or '' for page in pdf.pages)
            return text
        except ImportError:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                text = '\n\n'.join(page.extract_text() for page in reader.pages)
                return text
            except Exception as e:
                logger.error(f"Basic text extraction failed: {e}")
                return ""

    def _extract_with_llm(
        self,
        text: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Extract structured metadata using LLM.

        Args:
            text: Document text from Docling
            category: Document category

        Returns:
            Structured metadata dict
        """
        # Get schema for category
        schema = self._get_schema_for_category(category)

        # Build extraction prompt
        prompt = self._build_extraction_prompt(text, category, schema)

        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            metadata_str = result['response'].strip()

            # Parse JSON response
            metadata = json.loads(metadata_str)

            logger.debug(f"LLM extracted {len(metadata)} fields")

            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return {'text': text, 'category': category, 'error': 'json_parse_failed'}
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {'text': text, 'category': category, 'error': str(e)}

    def _get_schema_for_category(self, category: str) -> Dict[str, Any]:
        """Get extraction schema for document category."""
        schemas = {
            'invoice': {
                'invoice_number': 'Invoice number',
                'invoice_date': 'Invoice date',
                'due_date': 'Due date',
                'vendor_name': 'Vendor/seller name',
                'vendor_address': 'Vendor address',
                'customer_name': 'Customer/buyer name',
                'customer_address': 'Customer address',
                'subtotal': 'Subtotal amount',
                'tax_amount': 'Tax amount',
                'total_amount': 'Total amount',
                'currency': 'Currency code',
                'payment_terms': 'Payment terms',
            },
            'receipt': {
                'receipt_number': 'Receipt number',
                'date': 'Transaction date',
                'merchant_name': 'Merchant name',
                'merchant_address': 'Merchant address',
                'total_amount': 'Total amount',
                'payment_method': 'Payment method',
                'items': 'List of purchased items',
            },
            'contract': {
                'contract_number': 'Contract number',
                'contract_date': 'Contract date',
                'effective_date': 'Effective date',
                'expiration_date': 'Expiration date',
                'party_a': 'First party name',
                'party_b': 'Second party name',
                'contract_type': 'Type of contract',
                'contract_value': 'Contract value',
            },
            'report': {
                'report_title': 'Report title',
                'report_date': 'Report date',
                'author': 'Author name',
                'organization': 'Organization',
                'report_type': 'Type of report',
                'key_findings': 'Key findings or summary',
            }
        }

        return schemas.get(category, {
            'title': 'Document title',
            'date': 'Document date',
            'summary': 'Brief summary'
        })

    def _build_extraction_prompt(
        self,
        text: str,
        category: str,
        schema: Dict[str, str]
    ) -> str:
        """Build LLM prompt for metadata extraction."""
        # Truncate text if too long
        max_text_length = 4000
        if len(text) > max_text_length:
            text = text[:max_text_length] + "...[truncated]"

        schema_description = '\n'.join(
            f'- "{field}": {description}'
            for field, description in schema.items()
        )

        prompt = f"""Extract structured information from this {category} document.

Document text:
```
{text}
```

Extract these fields:
{schema_description}

Return a JSON object with the extracted fields. Use null for fields you cannot find.
Only return the JSON object, no other text.

Example format:
{{"invoice_number": "INV-001", "vendor_name": "ACME Corp", "total_amount": 1500.00}}

JSON:"""

        return prompt

    def start(self):
        """Start the worker."""
        logger.info("Starting extraction worker...")
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
    worker = ExtractionWorker()
    worker.start()


if __name__ == '__main__':
    main()
