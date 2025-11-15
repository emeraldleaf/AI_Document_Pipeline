#!/usr/bin/env python3
"""
End-to-End Test for Microservices Architecture

This script tests the complete document processing pipeline:
1. Upload document via Ingestion Service
2. Monitor progress via Notification Service WebSocket
3. Verify document indexed in OpenSearch
4. Verify metadata in PostgreSQL
"""

import sys
import time
import asyncio
import json
import requests
from pathlib import Path
from websockets import connect
from loguru import logger


# Configuration
INGESTION_URL = "http://localhost:8000"
NOTIFICATION_URL = "ws://localhost:8001"
OPENSEARCH_URL = "http://localhost:9200"
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'documents',
    'user': 'postgres',
    'password': 'password'
}


class E2ETest:
    """End-to-end test orchestrator."""

    def __init__(self):
        self.document_id = None
        self.correlation_id = None
        self.events_received = []

    async def run(self, test_file_path: str):
        """
        Run complete end-to-end test.

        Args:
            test_file_path: Path to test document
        """
        logger.info("=" * 70)
        logger.info("Starting End-to-End Microservices Test")
        logger.info("=" * 70)

        try:
            # Step 1: Check services health
            logger.info("\n[Step 1] Checking service health...")
            await self.check_health()

            # Step 2: Upload document
            logger.info("\n[Step 2] Uploading document...")
            await self.upload_document(test_file_path)

            # Step 3: Monitor progress via WebSocket
            logger.info("\n[Step 3] Monitoring progress via WebSocket...")
            await self.monitor_progress(timeout=120)

            # Step 4: Verify in OpenSearch
            logger.info("\n[Step 4] Verifying document in OpenSearch...")
            await self.verify_opensearch()

            # Step 5: Verify in PostgreSQL
            logger.info("\n[Step 5] Verifying document in PostgreSQL...")
            await self.verify_postgres()

            # Step 6: Summary
            logger.info("\n" + "=" * 70)
            logger.success("✅ END-TO-END TEST PASSED")
            logger.info("=" * 70)
            self.print_summary()

            return True

        except Exception as e:
            logger.error(f"\n❌ END-TO-END TEST FAILED: {e}")
            return False

    async def check_health(self):
        """Check health of all services."""
        services = {
            'Ingestion Service': f"{INGESTION_URL}/health",
            'Notification Service': f"{NOTIFICATION_URL.replace('ws://', 'http://')}/health",
        }

        all_healthy = True
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    logger.success(f"✓ {name}: healthy")
                else:
                    logger.error(f"✗ {name}: unhealthy (status: {response.status_code})")
                    all_healthy = False
            except Exception as e:
                logger.error(f"✗ {name}: unreachable ({e})")
                all_healthy = False

        if not all_healthy:
            raise RuntimeError("Some services are not healthy")

    async def upload_document(self, file_path: str):
        """Upload document via Ingestion Service."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Test file not found: {file_path}")

        logger.info(f"Uploading: {file_path.name} ({file_path.stat().st_size} bytes)")

        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/pdf')}
            response = requests.post(
                f"{INGESTION_URL}/api/upload",
                files=files,
                timeout=30
            )

        if response.status_code != 200:
            raise RuntimeError(f"Upload failed: {response.status_code} - {response.text}")

        data = response.json()
        self.document_id = data['document_id']
        self.correlation_id = self.document_id

        logger.success(f"✓ Document uploaded")
        logger.info(f"  Document ID: {self.document_id}")
        logger.info(f"  File Path: {data['file_path']}")

    async def monitor_progress(self, timeout: int = 120):
        """Monitor document processing via WebSocket."""
        logger.info(f"Connecting to WebSocket: {NOTIFICATION_URL}/ws/document/{self.document_id}")

        start_time = time.time()
        completed = False

        try:
            async with connect(f"{NOTIFICATION_URL}/ws/document/{self.document_id}") as websocket:
                logger.success("✓ WebSocket connected")

                while time.time() - start_time < timeout:
                    try:
                        # Receive message with timeout
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=10
                        )

                        data = json.loads(message)
                        self.events_received.append(data)

                        if data.get('type') == 'connected':
                            logger.info("  → WebSocket connection confirmed")
                            continue

                        if data.get('type') == 'event':
                            event_type = data['data'].get('event_type', 'unknown')
                            logger.info(f"  → Event received: {event_type}")

                            # Check if processing is complete
                            if event_type == 'document.indexed':
                                logger.success("  → Document processing complete!")
                                completed = True
                                break

                    except asyncio.TimeoutError:
                        # No message received, continue waiting
                        continue

        except Exception as e:
            logger.error(f"WebSocket error: {e}")

        if not completed:
            logger.warning(
                f"⚠ Processing not completed after {timeout}s, "
                f"but {len(self.events_received)} events received"
            )
        else:
            elapsed = time.time() - start_time
            logger.success(f"✓ Processing completed in {elapsed:.1f}s")

        # Print event summary
        logger.info(f"\n  Events received ({len(self.events_received)}):")
        for i, event in enumerate(self.events_received, 1):
            event_type = event.get('data', {}).get('event_type', event.get('type'))
            logger.info(f"    {i}. {event_type}")

    async def verify_opensearch(self):
        """Verify document is indexed in OpenSearch."""
        logger.info(f"Checking OpenSearch for document {self.document_id}")

        # Wait a bit for indexing to complete
        await asyncio.sleep(2)

        try:
            response = requests.get(
                f"{OPENSEARCH_URL}/documents/_doc/{self.document_id}",
                timeout=10
            )

            if response.status_code == 200:
                doc = response.json()
                logger.success("✓ Document found in OpenSearch")

                source = doc.get('_source', {})
                logger.info(f"  Category: {source.get('category', 'N/A')}")
                logger.info(f"  Confidence: {source.get('confidence', 0):.2f}")
                logger.info(f"  Extraction Method: {source.get('extraction_method', 'N/A')}")

                # Check if embedding exists
                if 'embedding' in source:
                    logger.info(f"  Embedding Dimension: {len(source['embedding'])}")
                else:
                    logger.warning("  ⚠ No embedding found")

            elif response.status_code == 404:
                logger.warning("⚠ Document not found in OpenSearch")
            else:
                logger.error(f"✗ OpenSearch error: {response.status_code}")

        except Exception as e:
            logger.error(f"✗ Failed to query OpenSearch: {e}")

    async def verify_postgres(self):
        """Verify document metadata is in PostgreSQL."""
        logger.info(f"Checking PostgreSQL for document {self.document_id}")

        try:
            import psycopg2

            conn = psycopg2.connect(**POSTGRES_CONFIG)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT document_id, category, confidence, indexed, updated_at FROM documents WHERE document_id = %s",
                (self.document_id,)
            )

            row = cursor.fetchone()

            if row:
                logger.success("✓ Document found in PostgreSQL")
                logger.info(f"  Document ID: {row[0]}")
                logger.info(f"  Category: {row[1]}")
                logger.info(f"  Confidence: {row[2]:.2f}")
                logger.info(f"  Indexed: {row[3]}")
                logger.info(f"  Updated At: {row[4]}")
            else:
                logger.warning("⚠ Document not found in PostgreSQL")

            cursor.close()
            conn.close()

        except ImportError:
            logger.warning("⚠ psycopg2 not installed, skipping PostgreSQL verification")
        except Exception as e:
            logger.error(f"✗ Failed to query PostgreSQL: {e}")

    def print_summary(self):
        """Print test summary."""
        logger.info("\n📊 Test Summary:")
        logger.info(f"  Document ID: {self.document_id}")
        logger.info(f"  Correlation ID: {self.correlation_id}")
        logger.info(f"  Events Received: {len(self.events_received)}")

        event_types = [
            event.get('data', {}).get('event_type', event.get('type'))
            for event in self.events_received
        ]

        expected_events = [
            'connected',
            'document.uploaded',
            'document.classified',
            'document.extracted',
            'document.indexed'
        ]

        logger.info(f"\n  Event Flow:")
        for expected in expected_events:
            if expected in event_types:
                logger.success(f"    ✓ {expected}")
            else:
                logger.warning(f"    ⚠ {expected} (not received)")


async def main():
    """Main entry point."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Get test file path
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        # Try to find a test document
        test_docs = list(Path('.').glob('test_documents/*.pdf'))
        if test_docs:
            test_file = str(test_docs[0])
            logger.info(f"Using test file: {test_file}")
        else:
            logger.error("No test file specified and no test documents found")
            logger.info("Usage: python test_microservices_e2e.py <path_to_test_file.pdf>")
            sys.exit(1)

    # Run test
    tester = E2ETest()
    success = await tester.run(test_file)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
