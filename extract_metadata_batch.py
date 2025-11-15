#!/usr/bin/env python3
"""
Batch Metadata Extraction Tool
================================

Re-processes existing documents in the database to extract structured metadata
using configurable LLM-based extraction.

Usage:
    python extract_metadata_batch.py                      # Process all documents
    python extract_metadata_batch.py --category invoices  # Process only invoices
    python extract_metadata_batch.py --limit 10           # Process only 10 documents
    python extract_metadata_batch.py --model llama3.2     # Use specific model
    python extract_metadata_batch.py --dry-run            # Preview without saving
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
from loguru import logger
from sqlalchemy import text
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import DatabaseService
from llm_metadata_extractor import ConfigurableMetadataExtractor


def extract_and_update_metadata(
    db_service: DatabaseService,
    category_filter: Optional[str] = None,
    limit: Optional[int] = None,
    model: str = "llama3.2:3b",
    dry_run: bool = False,
):
    """
    Extract metadata from documents and update database.

    Args:
        db_service: Database service instance
        category_filter: Only process documents in this category
        limit: Maximum number of documents to process
        model: Ollama model to use for extraction
        dry_run: Don't actually update the database
    """
    # Build query
    query = "SELECT id, file_name, category, full_content, metadata_json FROM documents WHERE full_content IS NOT NULL"

    if category_filter:
        query += f" AND category = '{category_filter}'"

    if limit:
        query += f" LIMIT {limit}"

    # Fetch documents
    with db_service.engine.connect() as conn:
        result = conn.execute(text(query))
        documents = result.fetchall()

    if not documents:
        logger.warning("No documents found to process")
        return

    logger.info(f"Processing {len(documents)} documents...")
    logger.info(f"LLM model: {model}")
    logger.info(f"Dry run: {'yes' if dry_run else 'no'}")

    # Initialize the LLM extractor
    extractor = ConfigurableMetadataExtractor(model=model)

    success_count = 0
    error_count = 0

    # Process each document
    for doc in tqdm(documents, desc="Extracting metadata"):
        doc_id, file_name, category, full_content, existing_metadata = doc

        try:
            # Parse existing metadata to get file metadata
            import json
            if existing_metadata:
                if isinstance(existing_metadata, str):
                    file_metadata = json.loads(existing_metadata)
                else:
                    file_metadata = existing_metadata
            else:
                file_metadata = {
                    'file_name': file_name,
                }

            # Extract structured metadata using LLM
            metadata_dict = extractor.extract(
                text=full_content,
                category=category,
                file_metadata=file_metadata
            )

            # Log extraction result
            logger.info(f"✓ {file_name} ({category})")
            logger.info(f"  Extraction method: {metadata_dict.get('extraction_method')}")
            logger.info(f"  Confidence: {metadata_dict.get('extraction_confidence', 0):.2f}")

            # Show key extracted fields
            if category == 'invoices':
                logger.info(f"  Invoice #: {metadata_dict.get('invoice_number')}")
                logger.info(f"  Total: ${metadata_dict.get('total_amount')}")
                logger.info(f"  Vendor: {metadata_dict.get('vendor_name')}")
            elif category == 'contracts':
                logger.info(f"  Contract #: {metadata_dict.get('contract_number')}")
                logger.info(f"  Parties: {metadata_dict.get('party_a')} & {metadata_dict.get('party_b')}")
            elif category == 'reports':
                logger.info(f"  Type: {metadata_dict.get('report_type')}")
                logger.info(f"  Period: {metadata_dict.get('fiscal_quarter')} {metadata_dict.get('fiscal_year')}")

            # Update database
            if not dry_run:
                with db_service.engine.connect() as conn:
                    conn.execute(
                        text("UPDATE documents SET metadata_json = :metadata WHERE id = :doc_id"),
                        {"metadata": json.dumps(metadata_dict), "doc_id": doc_id}
                    )
                    conn.commit()

            success_count += 1

        except Exception as e:
            logger.error(f"✗ Failed to process {file_name}: {e}")
            error_count += 1
            continue

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✓ Successfully processed: {success_count}")
    logger.info(f"✗ Errors: {error_count}")
    logger.info(f"Total: {len(documents)}")

    if dry_run:
        logger.info("\n⚠️  DRY RUN MODE - No changes were made to the database")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract structured metadata from documents using configurable LLM-based extraction"
    )
    parser.add_argument(
        '--category',
        help='Only process documents in this category (e.g., invoices, contracts)',
        default=None
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of documents to process',
        default=None
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Ollama model to use for extraction',
        default='llama3.2:3b'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Don\'t update database, just show what would be extracted'
    )

    args = parser.parse_args()

    # Configure logger
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

    # Initialize database
    import os
    database_url = os.environ.get('DATABASE_URL', 'postgresql://joshuadell@localhost:5432/documents')
    logger.info(f"Initializing database connection... ({database_url})")
    db_service = DatabaseService(database_url=database_url)

    # Run extraction
    extract_and_update_metadata(
        db_service=db_service,
        category_filter=args.category,
        limit=args.limit,
        model=args.model,
        dry_run=args.dry_run
    )

    logger.info("✓ Metadata extraction complete!")


if __name__ == "__main__":
    main()
