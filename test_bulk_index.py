#!/usr/bin/env python3
"""
Test bulk indexing to understand the return format
"""
import psycopg2
from opensearchpy import OpenSearch, helpers

# Connect to PostgreSQL
conn = psycopg2.connect("postgresql://joshuadell@localhost:5432/documents")
cur = conn.cursor()

# Get a few documents
cur.execute("""
    SELECT id, file_name, file_path, category, full_content, title, author
    FROM documents
    LIMIT 3
""")

rows = cur.fetchall()
print(f"Found {len(rows)} documents in PostgreSQL\n")

# Connect to OpenSearch
client = OpenSearch(
    hosts=["http://localhost:9200"],
    use_ssl=False,
    verify_certs=False
)

# Prepare bulk actions
actions = []
for row in rows:
    doc_id, file_name, file_path, category, full_content, title, author = row

    actions.append({
        "_index": "documents",
        "_id": doc_id,
        "_source": {
            "id": doc_id,
            "file_name": file_name,
            "file_path": file_path,
            "category": category,
            "full_content": full_content,
            "title": title,
            "author": author
        }
    })
    print(f"Prepared: {file_name} (ID: {doc_id})")

print(f"\nBulk indexing {len(actions)} documents...")

try:
    # Try bulk indexing
    result = helpers.bulk(
        client,
        actions,
        chunk_size=500,
        raise_on_error=False,
        stats_only=False
    )

    print(f"\nBulk result type: {type(result)}")
    print(f"Bulk result: {result}")

    if isinstance(result, tuple):
        success_count = result[0]
        failed_items = result[1]
        print(f"\n✓ Success count: {success_count}")
        print(f"✗ Failed count: {len(failed_items)}")
        if failed_items:
            print(f"\nFailed items:")
            for item in failed_items[:3]:  # Show first 3 failures
                print(f"  {item}")

    # Verify count
    client.indices.refresh(index="documents")
    count = client.count(index="documents")
    print(f"\n✓ Total documents in index: {count['count']}")

except Exception as e:
    print(f"✗ Bulk indexing failed: {e}")
    import traceback
    traceback.print_exc()

cur.close()
conn.close()
