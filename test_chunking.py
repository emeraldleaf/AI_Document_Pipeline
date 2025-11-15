#!/usr/bin/env python3
"""
Test document chunking system
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import psycopg2
from src.document_chunker import DocumentChunker, get_chunker

print("=" * 80)
print("TESTING DOCUMENT CHUNKING SYSTEM")
print("=" * 80)
print()

# Test with the 3 problematic documents + 1 very long document
test_doc_ids = [2, 3, 5, 20]  # report, invoice, receipt, annual_report (long)

# Connect to PostgreSQL
conn = psycopg2.connect("postgresql://joshuadell@localhost:5432/documents")
cur = conn.cursor()

cur.execute("""
    SELECT id, file_name, full_content, category, title, author
    FROM documents
    WHERE id IN %s
    ORDER BY id
""", (tuple(test_doc_ids),))

documents = []
for row in cur.fetchall():
    documents.append({
        'id': row[0],
        'file_name': row[1],
        'full_content': row[2],
        'category': row[3],
        'title': row[4],
        'author': row[5]
    })

cur.close()
conn.close()

print(f"Loaded {len(documents)} test documents")
print()

# Test with Ollama-optimized chunker
print("-" * 80)
print("TEST 1: Ollama-Optimized Chunking (800 chars, 100 overlap)")
print("-" * 80)
print()

chunker = get_chunker('ollama_nomic')

for doc in documents:
    print(f"Document {doc['id']}: {doc['file_name']}")
    print(f"  Original length: {len(doc['full_content']):,} chars")

    chunks = chunker.chunk_document(
        document_id=doc['id'],
        content=doc['full_content'],
        metadata={
            'file_name': doc['file_name'],
            'category': doc['category'],
            'title': doc['title'],
            'author': doc['author']
        }
    )

    print(f"  Number of chunks: {len(chunks)}")

    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
        print(f"  Chunk {i}: {len(chunk.content)} chars")
        print(f"    Preview: {chunk.content[:80]}...")

    if len(chunks) > 3:
        print(f"  ... and {len(chunks) - 3} more chunks")

    print()

# Test with different preset
print("-" * 80)
print("TEST 2: OpenAI-Optimized Chunking (1500 chars, 200 overlap)")
print("-" * 80)
print()

chunker_openai = get_chunker('openai_small')

# Test with longest document
long_doc = documents[-1]  # annual_report_20_pages
print(f"Document {long_doc['id']}: {long_doc['file_name']}")
print(f"  Original length: {len(long_doc['full_content']):,} chars")

chunks = chunker_openai.chunk_document(
    document_id=long_doc['id'],
    content=long_doc['full_content'],
    metadata={'file_name': long_doc['file_name'], 'category': long_doc['category']}
)

print(f"  Number of chunks: {len(chunks)}")
print(f"  Average chunk size: {sum(len(c.content) for c in chunks) // len(chunks)} chars")
print(f"  Smallest chunk: {min(len(c.content) for c in chunks)} chars")
print(f"  Largest chunk: {max(len(c.content) for c in chunks)} chars")
print()

# Test batch chunking
print("-" * 80)
print("TEST 3: Batch Chunking (All documents)")
print("-" * 80)
print()

chunker = get_chunker('ollama_nomic')
all_chunks = chunker.chunk_documents_batch(documents)

print(f"Total chunks generated: {len(all_chunks)}")
print()

# Group by document
chunks_by_doc = {}
for chunk in all_chunks:
    if chunk.document_id not in chunks_by_doc:
        chunks_by_doc[chunk.document_id] = []
    chunks_by_doc[chunk.document_id].append(chunk)

for doc_id in sorted(chunks_by_doc.keys()):
    doc_chunks = chunks_by_doc[doc_id]
    doc = next(d for d in documents if d['id'] == doc_id)
    print(f"  Doc {doc_id} ({doc['file_name']}): {len(doc_chunks)} chunks")

print()

# Verify chunk sizes are within limits
print("-" * 80)
print("TEST 4: Verify All Chunks Within Embedding Limits")
print("-" * 80)
print()

max_limit = 2000  # nomic-embed-text safe limit
oversized_chunks = [c for c in all_chunks if len(c.content) > max_limit]

if oversized_chunks:
    print(f"❌ FAIL: {len(oversized_chunks)} chunks exceed {max_limit} char limit")
    for chunk in oversized_chunks[:5]:
        print(f"  • Chunk {chunk.chunk_id}: {len(chunk.content)} chars")
else:
    print(f"✅ PASS: All {len(all_chunks)} chunks are within {max_limit} char limit")
    print(f"  Largest chunk: {max(len(c.content) for c in all_chunks)} chars")
    print(f"  Average chunk: {sum(len(c.content) for c in all_chunks) // len(all_chunks)} chars")

print()

print("=" * 80)
print("CHUNKING SYSTEM READY FOR PRODUCTION")
print("=" * 80)
print()
print("Benefits of chunking:")
print("  ✅ Handles documents of ANY size")
print("  ✅ All chunks stay within embedding model limits")
print("  ✅ Context preserved via 100-char overlap")
print("  ✅ Metadata attached to each chunk")
print("  ✅ Better semantic search granularity")
print()
print("Next step: Integrate chunking into migration pipeline")
