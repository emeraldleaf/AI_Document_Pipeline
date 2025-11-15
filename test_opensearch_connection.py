#!/usr/bin/env python3
"""
Quick test script to check OpenSearch indexing
"""
import sys
import psycopg2
from opensearchpy import OpenSearch, helpers

# Connect to PostgreSQL
conn = psycopg2.connect("postgresql://joshuadell@localhost:5432/documents")
cur = conn.cursor()

# Get one document
cur.execute("""
    SELECT id, file_name, file_path, category, full_content, title
    FROM documents
    LIMIT 1
""")

row = cur.fetchone()
if not row:
    print("No documents found in PostgreSQL")
    sys.exit(1)

doc_id, file_name, file_path, category, full_content, title = row
print(f"Found document: {file_name}")
print(f"  ID: {doc_id}")
print(f"  Category: {category}")
print(f"  Content length: {len(full_content) if full_content else 0}")

# Connect to OpenSearch
client = OpenSearch(
    hosts=["http://localhost:9200"],
    use_ssl=False,
    verify_certs=False
)

# Test connection
info = client.info()
print(f"\nOpenSearch cluster: {info['cluster_name']}")

# Try to index the document
test_doc = {
    "id": doc_id,
    "file_name": file_name,
    "file_path": file_path,
    "category": category,
    "full_content": full_content,
    "title": title
}

print(f"\nAttempting to index document...")

try:
    # Try simple index first
    response = client.index(
        index="documents",
        id=doc_id,
        body=test_doc
    )
    print(f"✓ Successfully indexed: {response['result']}")

    # Verify it's there
    client.indices.refresh(index="documents")
    count = client.count(index="documents")
    print(f"✓ Document count in index: {count['count']}")

except Exception as e:
    print(f"✗ Failed to index: {e}")
    import traceback
    traceback.print_exc()

cur.close()
conn.close()
