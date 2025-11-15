#!/usr/bin/env python3
"""
Test LLM Metadata Extraction
==============================

Quick test script to see detailed extraction results.
"""

import sys
import json
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import DatabaseService
from llm_metadata_extractor import ConfigurableMetadataExtractor

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")

# Initialize
import os
database_url = os.environ.get('DATABASE_URL', 'postgresql://joshuadell@localhost:5432/documents')
db = DatabaseService(database_url=database_url)

# Get a sample document
from sqlalchemy import text
with db.engine.connect() as conn:
    result = conn.execute(
        text("SELECT file_name, category, full_content FROM documents WHERE category = 'invoices' AND full_content IS NOT NULL LIMIT 1")
    )
    doc = result.fetchone()

if not doc:
    logger.error("No invoice documents found")
    sys.exit(1)

file_name, category, content = doc

logger.info(f"Testing extraction on: {file_name}")
logger.info(f"Category: {category}")
logger.info(f"Content length: {len(content)} characters")
logger.info("=" * 60)

# Extract metadata
extractor = ConfigurableMetadataExtractor(model="llama3.2:3b")

metadata = extractor.extract(
    text=content,
    category=category,
    file_metadata={"file_name": file_name}
)

# Display results
logger.info("\n📋 EXTRACTED METADATA:")
logger.info("=" * 60)
print(json.dumps(metadata, indent=2, default=str))
logger.info("=" * 60)

# Show key fields
logger.info("\n🔍 KEY EXTRACTED FIELDS:")
if category == 'invoices':
    logger.info(f"  Invoice Number: {metadata.get('invoice_number')}")
    logger.info(f"  Date: {metadata.get('invoice_date')}")
    logger.info(f"  Vendor: {metadata.get('vendor_name')}")
    logger.info(f"  Customer: {metadata.get('customer_name')}")
    logger.info(f"  Subtotal: ${metadata.get('subtotal')}")
    logger.info(f"  Tax: ${metadata.get('tax_amount')}")
    logger.info(f"  Total: ${metadata.get('total_amount')}")
    logger.info(f"  Payment Method: {metadata.get('payment_method')}")
    logger.info(f"  Payment Terms: {metadata.get('payment_terms')}")

logger.info("\n📊 EXTRACTION QUALITY:")
logger.info(f"  Method: {metadata.get('extraction_method')}")
logger.info(f"  Model: {metadata.get('extraction_model')}")
logger.info(f"  Confidence: {metadata.get('extraction_confidence')}")
logger.info(f"  Timestamp: {metadata.get('extracted_at')}")
