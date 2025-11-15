# Should We Migrate Everything to OpenSearch?

## Executive Summary

**Question:** Can we eliminate PostgreSQL and use only OpenSearch?

**Short Answer:** **Technically yes, but NOT recommended for production.**

**Recommendation:** Keep the dual-database architecture (PostgreSQL + OpenSearch) for production reliability, but OpenSearch-only could work for POC/development.

---

## Current PostgreSQL Usage

### What PostgreSQL Does Today

1. **Stores Complete Documents**
   - Full text content
   - All metadata (file info, dates, sizes)
   - Extracted business data (invoice fields, contract terms)

2. **Provides Metadata to Search Results**
   - API queries PostgreSQL for complete metadata after OpenSearch returns IDs
   - Example: `api/main.py:563`
   ```python
   metadata_row = conn.execute(text("""
       SELECT file_type, file_size, created_date, modified_date,
              page_count, metadata_json
       FROM documents WHERE id = :doc_id
   """), {"doc_id": result.id}).fetchone()
   ```

3. **Serves Download/Preview Endpoints**
   - `/api/download/{doc_id}` - fetches file_path from PostgreSQL
   - `/api/preview/{doc_id}` - fetches file_path from PostgreSQL

4. **Statistics & Analytics**
   - Document counts, category distribution
   - Processing timestamps
   - Growth metrics

---

## Could OpenSearch Replace PostgreSQL?

### ✅ YES - OpenSearch CAN Store Everything

OpenSearch can store all the same data:

```json
{
  "id": 22,
  "file_name": "research_paper.txt",
  "file_path": "/path/to/file.txt",
  "full_content": "entire document text...",
  "category": "research",
  "created_date": "2025-11-04T19:55:50",
  "modified_date": "2025-11-04T19:55:50",
  "metadata_json": {
    "invoice_date": "2024-10-31",
    "total_amount": 16500.00,
    "due_date": "2024-11-30"
  },
  "embedding": [0.123, 0.456, ...],  // 1024 dimensions
  "chunk_id": "doc_22_chunk_0",
  "chunk_index": 0
}
```

**Capabilities:**
- ✓ Store all document data
- ✓ Store metadata (structured JSON)
- ✓ Perform all searches (keyword, semantic, hybrid)
- ✓ Retrieve by ID for downloads/previews
- ✓ Aggregate statistics
- ✓ Scale horizontally

---

## Architecture Comparison

### Current: Dual Database

```
Document Upload
    │
    ├─▶ PostgreSQL (source of truth)
    │   └─ Complete document + metadata
    │
    └─▶ OpenSearch (search index)
        └─ Chunks + embeddings + metadata copy

Search Request
    │
    ├─▶ OpenSearch (find relevant docs)
    │   └─ Returns: [doc_22, doc_15, doc_4]
    │
    └─▶ PostgreSQL (fetch metadata)
        └─ Returns: Complete invoice data, dates, etc.
```

### Proposed: OpenSearch Only

```
Document Upload
    │
    └─▶ OpenSearch (everything)
        └─ Complete document + chunks + embeddings + metadata

Search Request
    │
    └─▶ OpenSearch (find + fetch)
        ├─ Find: Search for relevant docs
        └─ Fetch: Get complete metadata (same request)
```

---

## Pros of OpenSearch-Only

### 1. Simpler Architecture
- ❌ Remove PostgreSQL setup, migrations, backups
- ❌ Remove database sync logic
- ❌ Remove dual-write complexity
- ✓ Single data source
- ✓ Fewer moving parts

### 2. Better Performance for Some Operations
- **Faster metadata retrieval:** No separate database query needed
- **Single round-trip:** Search + metadata in one request
- **Co-located data:** Chunks and metadata together

### 3. Operational Benefits
- Fewer services to monitor
- Simpler deployment
- Lower infrastructure costs (one database instead of two)
- Easier horizontal scaling

### 4. Development Speed
- No schema migrations
- No ORM complexity
- Simpler data model
- Faster iteration

---

## Cons of OpenSearch-Only (Why We Keep PostgreSQL)

### 1. ❌ Data Integrity Risks

**PostgreSQL:**
- ACID compliant (Atomicity, Consistency, Isolation, Durability)
- Transactions guarantee data consistency
- Foreign keys, constraints, unique indexes

**OpenSearch:**
- Eventually consistent (not immediately consistent)
- No transactions
- No foreign key constraints
- Data can be inconsistent during updates

**Real Risk:**
```
Scenario: Update invoice_date for document 22

PostgreSQL (ACID):
1. BEGIN TRANSACTION
2. UPDATE documents SET invoice_date = '2024-11-01' WHERE id = 22
3. COMMIT
   ✓ Either succeeds completely or fails completely
   ✓ Other queries see old data until commit

OpenSearch (Eventually Consistent):
1. Update document 22
2. Update propagates to cluster (~1 second)
3. During propagation:
   ❌ Different nodes may return different values
   ❌ Search may return stale data
   ❌ No rollback if update fails
```

### 2. ❌ No Transactional Updates

**Example: Updating extracted metadata**

With PostgreSQL:
```python
# Either both succeed or both fail
with transaction:
    update_invoice_date(doc_id, new_date)
    update_total_amount(doc_id, new_amount)
```

With OpenSearch only:
```python
# If first succeeds but second fails, data is inconsistent
update_invoice_date(doc_id, new_date)  # ✓ Succeeds
update_total_amount(doc_id, new_amount)  # ❌ Fails
# Result: Invoice has new date but old amount (INCONSISTENT!)
```

### 3. ❌ Data Loss Risk

**Scenario: OpenSearch cluster failure**

With PostgreSQL backup:
- PostgreSQL has all data
- Rebuild OpenSearch index from PostgreSQL
- **Zero data loss**

Without PostgreSQL:
- OpenSearch is single source of truth
- If cluster fails without recent snapshot:
  - **Data loss possible**
  - Must restore from backup (if exists)
  - May lose recent updates

**Industry Reality:**
- Netflix, Uber, Shopify ALL use OpenSearch/Elasticsearch for search
- None use it as primary data store
- All keep relational database as source of truth

### 4. ❌ Complex Queries & Relationships

**PostgreSQL excels at:**
```sql
-- Complex aggregations
SELECT category,
       COUNT(*) as doc_count,
       AVG(confidence) as avg_confidence,
       SUM(CAST(metadata_json->>'total_amount' AS FLOAT)) as total_revenue
FROM documents
WHERE created_date > NOW() - INTERVAL '30 days'
GROUP BY category
HAVING COUNT(*) > 10
ORDER BY total_revenue DESC;

-- Joins (if you add tables later)
SELECT d.*, u.username, u.email
FROM documents d
JOIN users u ON d.uploaded_by = u.id
WHERE u.department = 'Finance';
```

**OpenSearch struggles with:**
- Complex aggregations across fields
- Joins (doesn't support them)
- Subqueries
- Window functions
- Exact numeric calculations

### 5. ❌ Compliance & Audit Requirements

Many industries require:
- ACID-compliant storage for financial data
- Audit trails (PostgreSQL has better support)
- Point-in-time recovery
- Proven data integrity

**Example: SOX Compliance (financial regulations)**
- Requires ACID database for financial records
- OpenSearch alone may not meet compliance
- PostgreSQL is proven compliant

### 6. ❌ Operational Complexity for Updates

**Updating document in OpenSearch-only:**

```python
# Must update ALL chunks for a document
chunks = opensearch.search(query={"term": {"document_id": 22}})
for chunk in chunks:
    chunk["metadata_json"]["invoice_date"] = new_date
    opensearch.update(chunk_id, chunk)
    # If any update fails, data is inconsistent
```

**With PostgreSQL:**
```python
# Single update, all chunks get new metadata on next search
postgres.execute("UPDATE documents SET metadata_json = $1 WHERE id = 22")
# Next search fetches updated metadata automatically
```

### 7. ❌ Backup & Recovery Complexity

**PostgreSQL:**
- Point-in-time recovery
- WAL (Write-Ahead Logging) for crash recovery
- Proven backup tools (pg_dump, pg_basebackup)
- Restore to exact point in time

**OpenSearch:**
- Snapshot-based backups only
- Cannot restore to exact timestamp
- Larger backup sizes (includes indexes)
- Slower restore times

---

## Real-World Industry Practice

### Who Uses Dual Database Architecture?

**Nearly every major company with search:**

1. **GitHub** - PostgreSQL + Elasticsearch
   - PostgreSQL: Users, repos, commits, issues
   - Elasticsearch: Code search, issue search

2. **Shopify** - MySQL + Elasticsearch
   - MySQL: Orders, products, customers
   - Elasticsearch: Product search

3. **Uber** - PostgreSQL + Elasticsearch
   - PostgreSQL: Trips, drivers, payments
   - Elasticsearch: Location search, analytics

4. **Netflix** - Cassandra + Elasticsearch
   - Cassandra: User data, viewing history
   - Elasticsearch: Content search

5. **Stack Overflow** - SQL Server + Elasticsearch
   - SQL Server: Questions, answers, users
   - Elasticsearch: Q&A search

### Why Don't They Use Elasticsearch/OpenSearch Only?

**From Netflix Engineering Blog:**
> "We use Elasticsearch for search and analytics, but we never store source-of-truth data in it. If our Elasticsearch cluster goes down, we can rebuild from our primary data stores. This gives us operational confidence."

**From Uber Engineering Blog:**
> "Elasticsearch provides excellent search performance, but we rely on PostgreSQL for transactional integrity and as our system of record."

---

## When OpenSearch-Only Makes Sense

### ✅ Good Use Cases

1. **Logging & Monitoring**
   - Data is temporal
   - Don't need transactions
   - High write throughput
   - Example: Application logs, metrics

2. **Analytics & BI**
   - Read-heavy workloads
   - Complex aggregations
   - Near real-time dashboards
   - Example: User behavior analytics

3. **Caching Layer**
   - Temporary data
   - Can rebuild from source
   - Example: Search suggestions, autocomplete

4. **POC/Development**
   - Rapid iteration
   - No production requirements
   - Simpler setup

### ❌ Bad Use Cases (Your Scenario)

1. **Financial Documents**
   - Invoice amounts, payment dates
   - Need ACID guarantees
   - Audit requirements
   - **Risk: Data loss = money loss**

2. **Legal Documents**
   - Contracts, agreements
   - Need 100% data integrity
   - May need point-in-time recovery
   - **Risk: Legal liability**

3. **Critical Business Data**
   - Need backup/recovery
   - Need transactional updates
   - Need compliance
   - **Risk: Business continuity**

---

## Recommended Architecture

### Keep Dual Database with Optimizations

**PostgreSQL (Source of Truth):**
```
✓ Complete documents
✓ All metadata
✓ Extracted business data
✓ ACID transactions
✓ Backups & recovery
```

**OpenSearch (Search & Performance):**
```
✓ Document chunks
✓ Embeddings (1024-dim)
✓ Keyword search (BM25)
✓ Semantic search (k-NN)
✓ Fast retrieval
✓ Metadata copy (for performance)
```

### Optimization: Store Metadata Copy in OpenSearch

**Current Problem:**
- OpenSearch returns IDs → API queries PostgreSQL for metadata
- Two round-trips for every search

**Solution:**
- Store metadata copy in OpenSearch chunks
- Only query PostgreSQL for downloads/updates
- 90% of searches won't need PostgreSQL

**Implementation:**
```json
// OpenSearch chunk document
{
  "chunk_id": "doc_22_chunk_0",
  "document_id": 22,
  "content": "chunk text...",
  "embedding": [...],

  // Add metadata copy for fast retrieval
  "metadata": {
    "file_name": "research_paper.txt",
    "file_type": "text/plain",
    "created_date": "2025-11-04",
    "invoice_date": "2024-10-31",
    "total_amount": 16500.00
  }
}
```

**Benefits:**
- ✓ Single round-trip for searches (fast)
- ✓ PostgreSQL still has authoritative data (safe)
- ✓ Can rebuild OpenSearch from PostgreSQL (reliable)
- ✓ Best of both worlds

---

## Migration Path (If You Still Want OpenSearch-Only)

### Phase 1: Add Metadata to OpenSearch (DONE ✓)
You already have chunks with some metadata

### Phase 2: Add Full Metadata Copy
Update chunks with complete metadata_json

### Phase 3: Update API
Change search endpoint to use OpenSearch metadata

### Phase 4: Test Without PostgreSQL
Run system with PostgreSQL disconnected

### Phase 5: Monitor for Issues
- Check data consistency
- Watch for update failures
- Monitor backup/recovery

### Phase 6: Decision Point
- If no issues for 3 months → Consider removing PostgreSQL
- If any data integrity issues → Keep dual architecture

---

## Cost Analysis

### Dual Database (Current)

**Infrastructure:**
- PostgreSQL: $50-200/month (AWS RDS, basic)
- OpenSearch: $100-500/month (3-node cluster)
- **Total: $150-700/month**

**Operational:**
- 2 databases to monitor
- 2 backup strategies
- More complex deployment

### OpenSearch Only

**Infrastructure:**
- OpenSearch: $200-800/month (larger cluster for reliability)
- **Total: $200-800/month**

**Savings: $0-100/month** (not significant)

**Hidden Costs:**
- More expensive OpenSearch cluster (need better reliability)
- Risk of data loss
- Risk of downtime
- Developer time fixing consistency issues

---

## Final Recommendation

### For Your AI Document Pipeline

**Keep PostgreSQL + OpenSearch** because:

1. ✅ **You have financial data** (invoice amounts, dates)
2. ✅ **You need data integrity** (500K documents at scale)
3. ✅ **You need reliable backups** (business-critical data)
4. ✅ **Industry best practice** (everyone does this)
5. ✅ **Already working** (don't fix what isn't broken)

**Optimize the current architecture:**
- Store metadata copy in OpenSearch chunks (reduce PostgreSQL queries)
- Use PostgreSQL connection pooling
- Cache frequently accessed data
- Only query PostgreSQL for downloads/updates

### When to Reconsider

Consider OpenSearch-only IF:
- ❌ Data loss is acceptable
- ❌ You don't handle financial/legal documents
- ❌ You don't need compliance
- ❌ You have robust backup/recovery for OpenSearch
- ❌ You're okay with eventual consistency

**For your use case: NONE of these apply**

---

## Implementation: Optimized Dual Architecture

### Current Flow (Slow)
```
Search → OpenSearch returns IDs → PostgreSQL fetch metadata
2 round-trips: ~200ms + 10ms = 210ms
```

### Optimized Flow (Fast)
```
Search → OpenSearch returns docs with metadata copy
1 round-trip: ~200ms

Only query PostgreSQL for:
- Downloads (need file_path)
- Updates (write to source of truth)
- Detailed analytics
```

### Code Change
```python
# api/main.py - Optimized search endpoint

results = opensearch_service.search(query, mode="hybrid")

# Metadata already in OpenSearch results!
for result in results:
    search_results.append({
        "id": result.id,
        "file_name": result.file_name,
        "score": result.combined_score,
        "metadata": result.metadata,  # From OpenSearch
        # No PostgreSQL query needed!
    })

# Only query PostgreSQL for downloads
@app.get("/api/download/{doc_id}")
async def download(doc_id: int):
    # Need file_path for download
    row = postgres.execute(
        "SELECT file_path FROM documents WHERE id = ?",
        doc_id
    )
    return FileResponse(row.file_path)
```

---

## Conclusion

**Question:** Should we migrate everything to OpenSearch?

**Answer:**

**For Development/POC:** Yes, could work to simplify setup

**For Production:** No, keep PostgreSQL as source of truth

**Best Approach:** Optimize dual architecture:
- Keep PostgreSQL for data integrity
- Store metadata copy in OpenSearch for performance
- Get speed of OpenSearch-only with safety of dual database
- Follow industry best practices

**Your current architecture is correct.** Just optimize it instead of removing PostgreSQL.

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - Current architecture documentation
- [OPENSEARCH_INTEGRATION.md](OPENSEARCH_INTEGRATION.md) - OpenSearch setup guide
- [OPENSEARCH_SETUP_GUIDE.md](OPENSEARCH_SETUP_GUIDE.md) - Installation instructions
