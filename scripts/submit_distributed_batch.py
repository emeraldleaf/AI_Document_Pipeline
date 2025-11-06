#!/usr/bin/env python3
"""
Submit a large batch of documents for distributed processing with Celery.
"""

import sys
import argparse
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.celery_tasks import CeleryDistributedProcessor, CELERY_AVAILABLE
from config import settings
from loguru import logger


def main():
    parser = argparse.ArgumentParser(
        description="Submit documents for distributed processing with Celery"
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to document or directory"
    )
    parser.add_argument(
        "-c", "--categories",
        help="Comma-separated categories (default: from config)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for submission (default: 1000)"
    )
    parser.add_argument(
        "--reasoning",
        action="store_true",
        help="Include AI reasoning in classification"
    )
    parser.add_argument(
        "--no-database",
        action="store_true",
        help="Disable database storage"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for completion before exiting"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Seconds between progress checks (default: 5.0)"
    )

    args = parser.parse_args()

    # Check Celery is available
    if not CELERY_AVAILABLE:
        logger.error("Celery is not installed. Install with: pip install celery redis")
        sys.exit(1)

    # Parse categories
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]

    # Create processor
    logger.info("Initializing distributed processor...")
    processor = CeleryDistributedProcessor(
        categories=categories,
        use_database=not args.no_database,
        batch_size=args.batch_size
    )

    # Submit documents
    logger.info(f"Submitting documents from: {args.input_path}")

    if args.input_path.is_file():
        # Single file
        batch_id = processor.submit_batch(
            [args.input_path],
            include_reasoning=args.reasoning
        )
    else:
        # Directory
        batch_id = processor.submit_directory(
            args.input_path,
            recursive=True,
            include_reasoning=args.reasoning
        )

    if not batch_id:
        logger.error("No documents found to submit")
        sys.exit(1)

    logger.success(f"Batch submitted successfully!")
    logger.info(f"Batch ID: {batch_id}")

    # Check initial progress
    time.sleep(1)  # Give workers a moment to pick up tasks
    progress = processor.check_progress(batch_id)

    logger.info(f"Total tasks: {progress.get('total_tasks', 0)}")
    logger.info(f"Monitor progress at: http://localhost:5555 (Flower dashboard)")

    # Wait for completion if requested
    if args.wait:
        logger.info("Waiting for batch to complete...")
        final_stats = processor.wait_for_completion(
            batch_id,
            poll_interval=args.poll_interval,
            show_progress=True
        )

        # Print final stats
        logger.success("Processing complete!")
        logger.info(f"Successful: {final_stats['successful']}")
        logger.info(f"Failed: {final_stats['failed']}")
        logger.info(f"Total time: {final_stats.get('total_time', 'N/A')}s")
    else:
        # Print instructions for checking progress
        print("\n" + "="*80)
        print("Batch submitted to distributed workers!")
        print("="*80)
        print(f"Batch ID: {batch_id}")
        print(f"\nTo check progress:")
        print(f"  python scripts/check_batch_progress.py {batch_id}")
        print(f"\nTo monitor in real-time:")
        print(f"  Open http://localhost:5555 (Flower dashboard)")
        print("="*80)


if __name__ == "__main__":
    main()
