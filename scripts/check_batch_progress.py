#!/usr/bin/env python3
"""
Check progress of a distributed batch processing job.
"""

import sys
import argparse
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.celery_tasks import CeleryDistributedProcessor, CELERY_AVAILABLE
from loguru import logger


def format_time(seconds):
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def main():
    parser = argparse.ArgumentParser(
        description="Check progress of distributed batch processing"
    )
    parser.add_argument(
        "batch_id",
        help="Batch ID from submission"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously watch progress (refresh every 5s)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Refresh interval in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--get-results",
        action="store_true",
        help="Get and display results (blocks until complete)"
    )

    args = parser.parse_args()

    # Check Celery is available
    if not CELERY_AVAILABLE:
        logger.error("Celery is not installed. Install with: pip install celery redis")
        sys.exit(1)

    # Create processor
    processor = CeleryDistributedProcessor()

    if args.get_results:
        # Get results (blocking)
        logger.info(f"Fetching results for batch {args.batch_id}...")
        logger.info("This will block until all tasks are complete...")

        try:
            results = processor.get_results(args.batch_id, timeout=3600)  # 1 hour timeout

            # Count successes and failures
            successful = sum(1 for r in results if r.get('success'))
            failed = len(results) - successful

            logger.success("Results retrieved!")
            logger.info(f"Total: {len(results)}")
            logger.info(f"Successful: {successful}")
            logger.info(f"Failed: {failed}")

            # Show sample results
            if successful > 0:
                print("\nSample successful results:")
                for r in results[:5]:
                    if r.get('success'):
                        print(f"  {Path(r['file_path']).name} -> {r['category']}")

            if failed > 0:
                print("\nSample failed results:")
                for r in results[:5]:
                    if not r.get('success'):
                        print(f"  {Path(r['file_path']).name} -> {r.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to get results: {e}")
            sys.exit(1)

    elif args.watch:
        # Watch progress continuously
        logger.info(f"Watching batch {args.batch_id}...")
        logger.info(f"Refresh interval: {args.interval}s")
        logger.info("Press Ctrl+C to stop\n")

        try:
            start_time = time.time()
            last_completed = 0

            while True:
                progress = processor.check_progress(args.batch_id)

                # Clear screen (Unix/Mac)
                print("\033[H\033[J", end="")

                # Display header
                print("="*80)
                print(f"Batch Progress: {args.batch_id}")
                print("="*80)

                # Display stats
                total = progress.get('total_tasks', 0)
                completed = progress.get('completed', 0)
                successful = progress.get('successful', 0)
                failed = progress.get('failed', 0)
                pending = progress.get('pending', 0)
                progress_pct = progress.get('progress_percent', 0)
                status = progress.get('status', 'unknown')

                print(f"Status: {status}")
                print(f"Progress: {progress_pct:.1f}% ({completed}/{total})")
                print(f"Successful: {successful}")
                print(f"Failed: {failed}")
                print(f"Pending: {pending}")

                # Calculate throughput
                elapsed = time.time() - start_time
                if elapsed > 0 and completed > 0:
                    docs_per_sec = completed / elapsed
                    print(f"\nThroughput: {docs_per_sec:.2f} docs/sec")
                    print(f"Elapsed time: {format_time(elapsed)}")

                    if pending > 0:
                        eta_seconds = pending / docs_per_sec
                        print(f"ETA: {format_time(eta_seconds)}")

                # Progress bar
                if total > 0:
                    bar_width = 60
                    filled = int(bar_width * completed / total)
                    bar = "█" * filled + "░" * (bar_width - filled)
                    print(f"\n[{bar}]")

                # Check if complete
                if status == 'completed' or completed >= total:
                    print("\n" + "="*80)
                    print("BATCH COMPLETE!")
                    print("="*80)
                    break

                # Calculate new docs since last check
                new_docs = completed - last_completed
                if new_docs > 0:
                    print(f"\n+{new_docs} documents completed in last {args.interval}s")

                last_completed = completed

                # Wait
                time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n\nStopped by user")
            sys.exit(0)

    else:
        # Single progress check
        progress = processor.check_progress(args.batch_id)

        print("\n" + "="*80)
        print(f"Batch Progress: {args.batch_id}")
        print("="*80)

        total = progress.get('total_tasks', 0)
        completed = progress.get('completed', 0)
        successful = progress.get('successful', 0)
        failed = progress.get('failed', 0)
        pending = progress.get('pending', 0)
        progress_pct = progress.get('progress_percent', 0)
        status = progress.get('status', 'unknown')

        print(f"Status: {status}")
        print(f"Progress: {progress_pct:.1f}% ({completed}/{total})")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Pending: {pending}")

        if status != 'completed' and completed < total:
            print(f"\nTo watch continuously:")
            print(f"  python scripts/check_batch_progress.py {args.batch_id} --watch")
        else:
            print(f"\nTo get results:")
            print(f"  python scripts/check_batch_progress.py {args.batch_id} --get-results")

        print("="*80)


if __name__ == "__main__":
    main()
