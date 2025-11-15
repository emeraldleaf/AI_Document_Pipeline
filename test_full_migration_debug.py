#!/usr/bin/env python3
"""
Debug the full migration process
"""
import psycopg2
from opensearchpy import OpenSearch, helpers
from sqlalchemy import create_engine, text

# Database URL
db_url = "postgresql://joshuadell@localhost:5432/documents"

# Connect with SQLAlchemy (like the migration script does)
engine = create_engine(db_url)

with engine.connect() as conn:
    sql = text("""
        SELECT
            id, file_name, file_path, category,
            title, author, page_count, file_type, file_size,
            created_date, modified_date, processed_date,
            full_content, content_preview,
            confidence,
            embedding, metadata_json
        FROM documents
        ORDER BY id
        LIMIT 2
    """)

    result = conn.execute(sql)
    rows = result.fetchall()

    print(f"Found {len(rows)} documents\n")

    documents = []
    for row in rows:
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
            "confidence": row[14],
            "embedding": row[15],
            "metadata_json": row[16]
        }

        print(f"Document {doc['id']}: {doc['file_name']}")
        print(f"  Dates: created={type(doc['created_date'])}, modified={type(doc['modified_date'])}")
        print(f"  Embedding: {type(doc['embedding'])}, is None: {doc['embedding'] is None}")
        print(f"  Metadata: {type(doc['metadata_json'])}")
        print()

        documents.append(doc)

# Now try to bulk index
client = OpenSearch(
    hosts=["http://localhost:9200"],
    use_ssl=False,
    verify_certs=False
)

# Prepare bulk actions
actions = []
for doc in documents:
    doc_id = doc.get("id")
    if not doc_id:
        print("Skipping document without ID")
        continue

    actions.append({
        "_index": "documents",
        "_id": doc_id,
        "_source": doc
    })

print(f"Attempting to bulk index {len(actions)} documents...")

try:
    result = helpers.bulk(
        client,
        actions,
        chunk_size=500,
        raise_on_error=False,
        stats_only=False
    )

    success_count = result[0]
    failed_items = result[1]

    print(f"\n✓ Success: {success_count}")
    print(f"✗ Failed: {len(failed_items)}")

    if failed_items:
        print(f"\nFailed items:")
        for item in failed_items:
            print(f"  {item}")

except Exception as e:
    print(f"✗ Bulk indexing failed: {e}")
    import traceback
    traceback.print_exc()
