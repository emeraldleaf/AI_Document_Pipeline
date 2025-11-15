#!/usr/bin/env python3
"""
Migrate the 5 missing documents (IDs 20-24)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import psycopg2
from opensearchpy import OpenSearch

# Missing IDs
missing_ids = [20, 21, 22, 23, 24]

# Connect to PostgreSQL
conn = psycopg2.connect("postgresql://joshuadell@localhost:5432/documents")
cur = conn.cursor()

# Get missing documents
cur.execute("""
    SELECT id, file_name, file_path, category, title, author,
           page_count, file_type, file_size, created_date, modified_date,
           processed_date, full_content, content_preview, confidence
    FROM documents
    WHERE id IN %s
    ORDER BY id
""", (tuple(missing_ids),))

rows = cur.fetchall()
print(f"Found {len(rows)} missing documents in PostgreSQL\n")

# Connect to OpenSearch
client = OpenSearch(
    hosts=["http://localhost:9200"],
    use_ssl=False,
    verify_certs=False
)

# Try to index each document without embeddings first
success_count = 0
failed_count = 0

for row in rows:
    doc_id = row[0]
    file_name = row[1]
    content_length = len(row[12]) if row[12] else 0

    print(f"Attempting to index ID {doc_id}: {file_name} ({content_length} chars)")

    try:
        # Parse confidence - convert string to None if not a number
        confidence = row[14]
        if confidence and isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except (ValueError, TypeError):
                confidence = None  # Skip non-numeric confidence values

        doc = {
            "id": row[0],
            "file_name": row[1],
            "file_path": row[2],
            "category": row[3],
            "title": row[4],
            "author": row[5],
            "page_count": row[6],
            "file_type": row[7],
            "file_size": row[8],
            "created_date": row[9],
            "modified_date": row[10],
            "processed_date": row[11],
            "full_content": row[12],
            "content_preview": row[13],
            "confidence": confidence
            # Note: No embedding field - will be skipped for semantic search
        }

        response = client.index(
            index="documents",
            id=doc_id,
            body=doc
        )

        if response['result'] in ['created', 'updated']:
            print(f"  ✓ Success: {response['result']}")
            success_count += 1
        else:
            print(f"  ✗ Failed: {response['result']}")
            failed_count += 1

    except Exception as e:
        print(f"  ✗ Error: {e}")
        failed_count += 1

    print()

# Verify final count
client.indices.refresh(index="documents")
count = client.count(index="documents")

print("=" * 60)
print(f"Migration Summary:")
print(f"  Attempted: {len(rows)}")
print(f"  Succeeded: {success_count}")
print(f"  Failed: {failed_count}")
print(f"\nTotal documents in OpenSearch: {count['count']}")

cur.close()
conn.close()
