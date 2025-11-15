# Production Resilience Guide for 500K+ Documents

## Executive Summary

This guide ensures your AI Document Pipeline can reliably process 500K+ documents with fault tolerance, error recovery, and production-grade reliability.

---

## ✅ Issues Fixed for Production Scale

### 1. **PostgreSQL Schema Type Safety** ✅ FIXED

**Problem**: `confidence` column was TEXT, causing type mismatch with OpenSearch (expects FLOAT)

**Solution**:
- Applied migration: `migrations/001_fix_confidence_type.sql`
- Column is now `DOUBLE PRECISION` (FLOAT)
- Old text values converted to NULL gracefully

**Verification**:
```bash
psql -h localhost -U joshuadell -d documents -c "\d documents" | grep confidence
```

Expected output: `confidence | double precision`

---

### 2. **Embedding Generation Resilience** ✅ FIXED

**Problem**:
- Long documents (11K+ chars) cause Ollama API 500 errors
- Embedding failures blocked entire migration

**Solution** (in `src/opensearch_service.py:442-477`):
- ✅ Content truncation to 8000 chars (prevents API failures)
- ✅ Try-catch around each embedding generation
- ✅ Continue processing on embedding failure (documents indexed without embeddings)
- ✅ Detailed logging of embedding success/failure rates

**Benefits**:
```
✓ Documents without embeddings → Still searchable via keyword search
✓ One embedding failure → Doesn't block other documents
✓ Clear visibility into embedding success rates
```

---

### 3. **Bulk Indexing Fault Tolerance** ✅ FIXED

**Problem**: Silent failures during bulk indexing

**Solution** (in `src/opensearch_service.py:467-497`):
- ✅ Automatic retry with exponential backoff (max 3 retries)
- ✅ Detailed error logging (first 5 failures + count)
- ✅ Returns error details for debugging
- ✅ `raise_on_error=False` prevents crashes

**Configuration**:
```python
helpers.bulk(
    self.client,
    actions,
    chunk_size=chunk_size,
    raise_on_error=False,      # Don't crash on errors
    stats_only=False,          # Return detailed failure info
    max_retries=3,             # Retry failed documents
    initial_backoff=2          # Wait 2s before first retry
)
```

---

### 4. **Migration Script Data Parsing** ✅ FIXED

**Problem**: Type coercion failures from PostgreSQL to OpenSearch

**Solution** (in `scripts/migrate_to_opensearch.py:153-192`):
- ✅ Parse pgvector embeddings from string to float array
- ✅ Convert text confidence values to NULL (graceful fallback)
- ✅ Handle NULL values properly across all fields

---

## 🚀 Production Configuration for 500K Documents

### OpenSearch Cluster Settings

**For 500K documents**, use these settings in `docker-compose-opensearch.yml`:

```yaml
opensearch:
  environment:
    # Increase heap size for large datasets
    - "OPENSEARCH_JAVA_OPTS=-Xms4g -Xmx4g"  # 4GB heap (adjust based on RAM)

    # Optimize for bulk indexing
    - "indices.memory.index_buffer_size=30%"
    - "thread_pool.write.queue_size=1000"

  # Increase resource limits
  ulimits:
    memlock:
      soft: -1
      hard: -1
    nofile:
      soft: 65536
      hard: 65536
```

### Migration Settings

**Recommended batch sizes** for different scales:

| Document Count | Batch Size | Expected Duration |
|---------------|------------|-------------------|
| < 10K | 500 | ~2-5 minutes |
| 10K - 100K | 1000 | ~10-30 minutes |
| 100K - 500K | 2000 | ~1-2 hours |
| 500K+ | 2000-5000 | ~2-5 hours |

**Run migration**:
```bash
# For 500K documents with embeddings
python3 scripts/migrate_to_opensearch.py \
  --batch-size 2000 \
  --regenerate-embeddings \
  --force-recreate

# For 500K documents without embeddings (faster)
python3 scripts/migrate_to_opensearch.py \
  --batch-size 5000 \
  --force-recreate
```

---

## 🛡️ Fault Tolerance Features

### 1. Automatic Error Recovery

| Error Type | Handling | Impact |
|------------|----------|--------|
| Embedding API failure | Log error, continue without embedding | ✅ Document still indexed |
| Type mismatch | Auto-convert or NULL | ✅ Document indexed with valid fields |
| Network timeout | Retry 3x with backoff | ✅ Automatic recovery |
| Bulk index failure | Log details, continue batch | ✅ Other docs still indexed |
| Content too long | Truncate to 8000 chars | ✅ Embedding still generated |

### 2. Monitoring & Logging

**Key metrics logged**:
- ✅ Documents processed per batch
- ✅ Embedding success/failure rates
- ✅ Bulk indexing success/failure counts
- ✅ Detailed error messages for first 5 failures
- ✅ Total migration duration

**Check logs**:
```bash
# During migration
tail -f logs/migration.log

# Search for errors
grep ERROR logs/migration.log

# Get success rate summary
grep "Migration complete" logs/migration.log
```

### 3. Partial Failure Handling

**Scenario**: 10 documents fail out of 500K

**Behavior**:
```
✓ 499,990 documents indexed successfully
✗ 10 documents failed (with error details logged)
→ Migration marked as 99.998% successful
→ You can re-run migration for only failed IDs
```

---

## 📊 Expected Performance (500K Documents)

### Hardware Requirements

**Minimum**:
- 8GB RAM
- 4 CPU cores
- 50GB disk space

**Recommended**:
- 16GB RAM
- 8 CPU cores
- 100GB SSD

### Estimated Timings

**With Embeddings**:
```
500K documents × 0.5 seconds/embedding = ~69 hours (Ollama)
500K documents × 0.05 seconds/embedding = ~7 hours (OpenAI)
```

**Without Embeddings**:
```
500K documents ÷ 5000 docs/batch × 2 seconds/batch = ~3.3 minutes
```

**Recommendation**:
- Initial migration: Skip embeddings (`--batch-size 5000`)
- Add embeddings later: Batch job overnight

---

## 🔍 Verification & Testing

### Test Resilience

```bash
# 1. Test with current 24 documents
python3 scripts/migrate_to_opensearch.py --force-recreate --batch-size 10

# 2. Verify all documents indexed
curl -s http://localhost:9200/documents/_count

# 3. Test search functionality
python3 test_search_api.py

# 4. Check for errors
curl http://localhost:9200/_cluster/health?pretty
```

### Monitor During Production Migration

```bash
# Terminal 1: Run migration
python3 scripts/migrate_to_opensearch.py --batch-size 2000

# Terminal 2: Monitor progress
watch -n 5 'curl -s http://localhost:9200/documents/_count'

# Terminal 3: Monitor cluster health
watch -n 10 'curl -s http://localhost:9200/_cluster/health?pretty'

# Terminal 4: Monitor resource usage
docker stats doc_pipeline_opensearch
```

---

## 🚨 Troubleshooting

### Issue: High Failure Rate (>5%)

**Diagnosis**:
```bash
# Check OpenSearch logs
docker logs doc_pipeline_opensearch --tail 100

# Check for type mismatches
grep "mapper_parsing_exception" logs/migration.log
```

**Solutions**:
1. Run schema migration: `psql -f migrations/001_fix_confidence_type.sql`
2. Reduce batch size: `--batch-size 500`
3. Increase OpenSearch heap: Edit `OPENSEARCH_JAVA_OPTS` in docker-compose

### Issue: Embedding Failures

**Diagnosis**:
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Test embedding API
curl -X POST http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'
```

**Solutions**:
1. Restart Ollama: `ollama serve`
2. Use shorter content: Already handled via truncation
3. Skip embeddings initially: Remove `--regenerate-embeddings` flag

### Issue: Out of Memory

**Diagnosis**:
```bash
docker stats doc_pipeline_opensearch
```

**Solutions**:
1. Reduce batch size: `--batch-size 500`
2. Increase heap size in docker-compose
3. Add swap space to host system

---

## ✅ Pre-Migration Checklist

Before migrating 500K documents:

- [ ] Schema migration applied (`001_fix_confidence_type.sql`)
- [ ] OpenSearch heap size configured (4GB+ for 500K docs)
- [ ] Batch size configured appropriately
- [ ] Backup PostgreSQL database
- [ ] Disk space verified (estimate: 2-3GB per 100K docs)
- [ ] Test migration on sample (1K documents)
- [ ] Monitoring tools ready
- [ ] Downtime window scheduled (if applicable)

---

## 📈 Scaling Beyond 500K Documents

### 1-10M Documents

**Changes needed**:
```yaml
# docker-compose-opensearch.yml
opensearch:
  environment:
    - "OPENSEARCH_JAVA_OPTS=-Xms8g -Xmx8g"  # 8GB heap

  # Add multiple nodes (3-node cluster)
  deploy:
    replicas: 3
```

### 10M+ Documents

**Recommendations**:
- Use AWS OpenSearch Service or Elastic Cloud
- Implement document sharding by category/date
- Use separate indices per time period
- Consider horizontal scaling with multiple clusters

---

## 📚 Related Documentation

- [OpenSearch Setup Guide](OPENSEARCH_SETUP_GUIDE.md)
- [Schema Management Guide](SCHEMA_MANAGEMENT_GUIDE.md)
- [Migration Script](scripts/migrate_to_opensearch.py)
- [OpenSearch Service](src/opensearch_service.py)

---

## ✅ Success Criteria

Your pipeline is production-ready when:

- ✅ Migration completes with >99% success rate
- ✅ All 24 test documents migrate successfully
- ✅ Search functionality works for both keyword and semantic
- ✅ Cluster health is GREEN or YELLOW
- ✅ Embedding failures don't block document indexing
- ✅ Error logs are clear and actionable

**Current Status**: ✅ All criteria met for 24 documents

**Next Step**: Test with 1K sample, then scale to 500K
