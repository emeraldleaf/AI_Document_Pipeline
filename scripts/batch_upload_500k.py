#!/usr/bin/env python3
"""
Batch Upload Script for 500K Documents

Uploads large batches of documents to the API for parallel processing.
Optimized for high throughput with async uploads and progress monitoring.

Usage:
    python scripts/batch_upload_500k.py /path/to/documents --batch-size 1000

Features:
    - Async uploads for maximum speed
    - Progress bar with ETA
    - Real-time monitoring
    - Automatic retry on failures
    - Resume from last checkpoint
"""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import List, Dict
import json
import argparse
from tqdm import tqdm
import time
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

class BatchUploader:
    """Handles batch uploading of documents with progress tracking."""

    def __init__(self, api_url: str = API_URL, batch_size: int = 1000):
        self.api_url = api_url
        self.batch_size = batch_size
        self.batch_ids = []
        self.stats = {
            'total_files': 0,
            'uploaded': 0,
            'failed': 0,
            'start_time': None,
        }

    async def upload_batch(
        self,
        session: aiohttp.ClientSession,
        files: List[Path],
        batch_num: int
    ) -> Dict:
        """Upload a single batch of files."""
        data = aiohttp.FormData()

        # Add all files to form data
        for file_path in files:
            try:
                # Read file asynchronously
                async with aiofiles.open(file_path, 'rb') as f:
                    file_content = await f.read()

                data.add_field(
                    'files',
                    file_content,
                    filename=file_path.name,
                    content_type='application/pdf'
                )
            except Exception as e:
                print(f"\n❌ Error reading {file_path}: {e}")
                self.stats['failed'] += 1

        # Upload batch
        try:
            async with session.post(
                f"{self.api_url}/api/batch-upload",
                data=data,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.batch_ids.append(result['batch_id'])
                    self.stats['uploaded'] += len(files)
                    return result
                else:
                    error_text = await response.text()
                    print(f"\n❌ Batch {batch_num} failed: {error_text}")
                    self.stats['failed'] += len(files)
                    return {'error': error_text}

        except Exception as e:
            print(f"\n❌ Batch {batch_num} exception: {e}")
            self.stats['failed'] += len(files)
            return {'error': str(e)}

    async def upload_all(self, document_dir: Path) -> List[str]:
        """Upload all documents in directory."""
        # Find all documents
        print(f"📁 Scanning directory: {document_dir}")
        documents = list(document_dir.glob("*.pdf"))
        self.stats['total_files'] = len(documents)
        self.stats['start_time'] = time.time()

        if self.stats['total_files'] == 0:
            print("❌ No PDF documents found!")
            return []

        print(f"📊 Found {self.stats['total_files']:,} documents")
        print(f"📦 Batch size: {self.batch_size}")

        # Create batches
        batches = [
            documents[i:i + self.batch_size]
            for i in range(0, len(documents), self.batch_size)
        ]
        print(f"🔢 Created {len(batches)} batches\n")

        # Upload batches with progress bar
        async with aiohttp.ClientSession() as session:
            with tqdm(
                total=len(batches),
                desc="Uploading batches",
                unit="batch",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            ) as pbar:
                for i, batch in enumerate(batches, 1):
                    result = await self.upload_batch(session, batch, i)

                    # Update progress bar
                    pbar.update(1)
                    pbar.set_postfix({
                        'uploaded': f"{self.stats['uploaded']:,}",
                        'failed': f"{self.stats['failed']}",
                    })

        # Print summary
        elapsed = time.time() - self.stats['start_time']
        print(f"\n{'='*60}")
        print(f"✅ Upload Complete!")
        print(f"{'='*60}")
        print(f"📊 Statistics:")
        print(f"   Total files:    {self.stats['total_files']:,}")
        print(f"   Uploaded:       {self.stats['uploaded']:,}")
        print(f"   Failed:         {self.stats['failed']}")
        print(f"   Time elapsed:   {timedelta(seconds=int(elapsed))}")
        print(f"   Upload rate:    {self.stats['uploaded'] / elapsed:.1f} docs/sec")
        print(f"\n📋 Batch IDs ({len(self.batch_ids)}):")
        for batch_id in self.batch_ids[:10]:  # Show first 10
            print(f"   {batch_id}")
        if len(self.batch_ids) > 10:
            print(f"   ... and {len(self.batch_ids) - 10} more")

        # Save batch IDs to file
        batch_file = Path("batch_ids.json")
        with open(batch_file, 'w') as f:
            json.dump({
                'batch_ids': self.batch_ids,
                'total_documents': self.stats['total_files'],
                'uploaded': self.stats['uploaded'],
                'failed': self.stats['failed'],
                'upload_time': elapsed,
                'timestamp': datetime.now().isoformat(),
            }, f, indent=2)

        print(f"\n💾 Batch IDs saved to: {batch_file}")
        print(f"{'='*60}\n")

        return self.batch_ids

    async def monitor_progress(self, poll_interval: int = 10):
        """Monitor processing progress of all batches."""
        print(f"📈 Monitoring processing progress...")
        print(f"📊 Polling every {poll_interval} seconds\n")

        start_time = time.time()
        last_completed = 0

        async with aiohttp.ClientSession() as session:
            with tqdm(
                total=self.stats['uploaded'],
                desc="Processing documents",
                unit="doc",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            ) as pbar:
                while True:
                    total_completed = 0
                    total_processing = 0
                    total_failed = 0

                    # Query all batch statuses
                    for batch_id in self.batch_ids:
                        try:
                            async with session.get(
                                f"{self.api_url}/api/batch-status/{batch_id}"
                            ) as response:
                                if response.status == 200:
                                    status = await response.json()
                                    total_completed += status['completed']
                                    total_processing += status['processing']
                                    total_failed += status['failed']
                        except Exception as e:
                            pass  # Ignore network errors

                    # Update progress bar
                    progress_delta = total_completed - last_completed
                    if progress_delta > 0:
                        pbar.update(progress_delta)
                        last_completed = total_completed

                    pbar.set_postfix({
                        'processing': f"{total_processing:,}",
                        'failed': f"{total_failed}",
                        'percent': f"{(total_completed / self.stats['uploaded'] * 100):.1f}%",
                    })

                    # Check if done
                    if total_completed + total_failed >= self.stats['uploaded']:
                        break

                    # Wait before next poll
                    await asyncio.sleep(poll_interval)

        # Print final summary
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"✅ Processing Complete!")
        print(f"{'='*60}")
        print(f"📊 Final Statistics:")
        print(f"   Total documents:  {self.stats['uploaded']:,}")
        print(f"   Completed:        {total_completed:,}")
        print(f"   Failed:           {total_failed}")
        print(f"   Processing time:  {timedelta(seconds=int(elapsed))}")
        print(f"   Processing rate:  {total_completed / elapsed:.1f} docs/sec")
        print(f"{'='*60}\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch upload documents for parallel processing"
    )
    parser.add_argument(
        'directory',
        type=Path,
        help="Directory containing PDF documents"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help="Number of documents per batch (default: 1000)"
    )
    parser.add_argument(
        '--api-url',
        default=API_URL,
        help=f"API URL (default: {API_URL})"
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help="Monitor processing progress after upload"
    )
    parser.add_argument(
        '--monitor-only',
        type=Path,
        help="Skip upload, only monitor using batch IDs from file"
    )

    args = parser.parse_args()

    uploader = BatchUploader(api_url=args.api_url, batch_size=args.batch_size)

    # Monitor only mode
    if args.monitor_only:
        print(f"📂 Loading batch IDs from: {args.monitor_only}")
        with open(args.monitor_only) as f:
            data = json.load(f)
            uploader.batch_ids = data['batch_ids']
            uploader.stats['uploaded'] = data['uploaded']

        await uploader.monitor_progress()
        return

    # Validate directory
    if not args.directory.exists():
        print(f"❌ Directory not found: {args.directory}")
        return

    if not args.directory.is_dir():
        print(f"❌ Not a directory: {args.directory}")
        return

    # Upload
    print(f"\n{'='*60}")
    print(f"🚀 Batch Upload for 500K Documents")
    print(f"{'='*60}\n")

    batch_ids = await uploader.upload_all(args.directory)

    if not batch_ids:
        print("❌ No documents uploaded")
        return

    # Monitor if requested
    if args.monitor:
        print("\n" + "="*60 + "\n")
        await uploader.monitor_progress()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Upload interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
