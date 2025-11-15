# OpenSearch Setup Guide

> **Enterprise-Scale Document Search for 500K+ Documents**

This guide will help you migrate from PostgreSQL to OpenSearch for dramatically improved search performance at scale.

---

## 📊 When to Use OpenSearch

### Use OpenSearch if you have:
- ✅ **100K+ documents** (500K+ recommended)
- ✅ **High query volume** (1000s of searches/day)
- ✅ **Need advanced features** (facets, aggregations, highlighting)
- ✅ **Analytics requirements** (search patterns, statistics)
- ✅ **Planning to scale** horizontally

### Stick with PostgreSQL if you have:
- ⭕ **<50K documents** (PostgreSQL works fine)
- ⭕ **Simple use case** (just file organization)
- ⭕ **Resource constrained** (limited RAM/CPU)
- ⭕ **Want simplicity** (fewer moving parts)

---

## 🏗️ Architecture Comparison

### Current (PostgreSQL):
```
FastAPI → PostgreSQL (with pgvector)
          ├─ Document metadata
          ├─ Full-text search (FTS)
          └─ Vector embeddings
```

### With OpenSearch (Recommended for 500K+ docs):
```
FastAPI → SearchService (Abstraction)
          ├─ PostgreSQL (metadata, relationships)
          └─ OpenSearch (search index)
              ├─ Full-text search (BM25)
              ├─ Vector search (k-NN)
              ├─ Facets & aggregations
              └─ Dashboards
```

---

## 🚀 Quick Start (Development)

### Step 1: Install Dependencies

```bash
# Install OpenSearch Python client
pip install opensearch-py

# Or update requirements
pip install -r requirements.txt
```

### Step 2: Start OpenSearch

```bash
# Start OpenSearch + Dashboards + PostgreSQL
docker-compose -f docker-compose-opensearch.yml up -d

# Check status
docker-compose -f docker-compose-opensearch.yml ps

# View logs
docker-compose -f docker-compose-opensearch.yml logs -f opensearch
```

**Wait 30-60 seconds** for OpenSearch to fully start.

### Step 3: Verify OpenSearch is Running

```bash
# Test API
curl http://localhost:9200

# Check cluster health
curl http://localhost:9200/_cluster/health

# Expected output:
# {
#   "cluster_name": "doc-search-cluster",
#   "status": "green",
#   ...
# }
```

### Step 4: Migrate Existing Data

```bash
# Migrate all documents from PostgreSQL to OpenSearch
python scripts/migrate_to_opensearch.py

# Expected output:
# 📊 Found 50,000 documents in PostgreSQL
# ✓ Created OpenSearch index: documents
# ⏳ Migrating documents...
# ✓ Migrated 50,000/50,000 documents (100%)
# 🎉 Migration complete!
```

**Migration Performance:**
- ~1,000 docs/second (with embeddings)
- ~5,000 docs/second (without embeddings)
- **500K documents in ~8-10 minutes**

### Step 5: Update Configuration

Edit your `.env` file:

```bash
# Switch to OpenSearch backend
SEARCH_BACKEND=opensearch

# OpenSearch settings (defaults work for local development)
OPENSEARCH_HOSTS=http://localhost:9200
OPENSEARCH_INDEX=documents
```

### Step 6: Test Search

```bash
# Test search with new backend
doc-classify search "invoice payment terms"

# You should see results with highlighting
```

### Step 7: Access OpenSearch Dashboards

Open http://localhost:5601 in your browser to:
- Explore your documents
- Visualize search patterns
- Monitor cluster health
- Create custom dashboards

---

## 📈 Performance Comparison

### PostgreSQL (pgvector)
| Document Count | Search Time | Scalability |
|----------------|-------------|-------------|
| 10K docs       | ~50ms       | ✅ Good     |
| 50K docs       | ~200ms      | ⚠️ OK       |
| 100K docs      | ~500ms      | ❌ Slow     |
| 500K+ docs     | 2-5 seconds | ❌ Too slow |

### OpenSearch
| Document Count | Search Time | Scalability |
|----------------|-------------|-------------|
| 10K docs       | ~20ms       | ✅ Excellent |
| 50K docs       | ~30ms       | ✅ Excellent |
| 100K docs      | ~50ms       | ✅ Excellent |
| 500K docs      | ~100ms      | ✅ Excellent |
| 10M docs       | ~200ms      | ✅ Excellent |

**At 500K documents, OpenSearch is ~20-50x faster** than PostgreSQL.

---

## 🔧 Advanced Configuration

### Production Settings

Edit your `.env` for production:

```bash
# Search backend
SEARCH_BACKEND=opensearch

# OpenSearch cluster (multiple nodes for HA)
OPENSEARCH_HOSTS=http://node1:9200,http://node2:9200,http://node3:9200
OPENSEARCH_INDEX=documents

# Security (IMPORTANT for production!)
OPENSEARCH_USE_SSL=true
OPENSEARCH_VERIFY_CERTS=true
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=your_secure_password

# Embedding service
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
```

### Docker Compose Production Setup

For production, create `docker-compose-opensearch-prod.yml`:

```yaml
version: '3.8'

services:
  opensearch-node1:
    image: opensearchproject/opensearch:2.11.0
    environment:
      - cluster.name=prod-search-cluster
      - node.name=opensearch-node1
      - discovery.seed_hosts=opensearch-node2,opensearch-node3
      - cluster.initial_master_nodes=opensearch-node1,opensearch-node2,opensearch-node3
      - OPENSEARCH_JAVA_OPTS=-Xms4g -Xmx4g  # 4GB heap
      - plugins.security.ssl.http.enabled=true
      - plugins.security.ssl.transport.enabled=true
    volumes:
      - opensearch-data1:/usr/share/opensearch/data
      - ./certs:/usr/share/opensearch/config/certs:ro
    networks:
      - opensearch-net

  opensearch-node2:
    # ... similar config

  opensearch-node3:
    # ... similar config

volumes:
  opensearch-data1:
  opensearch-data2:
  opensearch-data3:

networks:
  opensearch-net:
```

---

## 🔍 Search Features

### Keyword Search (BM25)

```python
from src.opensearch_service import OpenSearchService
from config import settings

search = OpenSearchService(hosts=settings.opensearch_hosts_list)

# BM25 keyword search with highlighting
results = search.keyword_search(
    query="invoice payment terms",
    limit=20,
    highlight=True
)

for result in results:
    print(f"{result.file_name} - Score: {result.keyword_rank}")
    if result.highlights:
        print(f"Highlights: {result.highlights['full_content']}")
```

### Semantic Search (k-NN)

```python
# Vector similarity search
results = search.semantic_search(
    query="how to request a refund",
    limit=20
)
```

### Hybrid Search (Best Results)

```python
# Combines keyword + semantic using Reciprocal Rank Fusion
results = search.hybrid_search(
    query="contract amendment terms",
    keyword_weight=0.5,
    semantic_weight=0.5,
    limit=20
)
```

### Faceted Search

```python
# Get category distribution
aggregations = search.get_aggregations(
    query="invoice"
)

print(aggregations["categories"])
# Output: {"invoices": 1234, "receipts": 456, ...}
```

---

## 📊 Monitoring and Analytics

### OpenSearch Dashboards

Access http://localhost:5601 to:

1. **Dev Tools** - Run queries directly
   ```json
   GET /documents/_search
   {
     "query": {
       "match": {
         "full_content": "invoice"
       }
     }
   }
   ```

2. **Index Management** - View indices, mappings, settings

3. **Discover** - Browse documents

4. **Visualize** - Create charts and dashboards

### Cluster Health

```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# Check index stats
curl http://localhost:9200/documents/_stats?pretty

# Check node information
curl http://localhost:9200/_cat/nodes?v
```

### Python API

```python
# Get cluster health
health = search.health_check()
print(health)
# Output: {"status": "green", "number_of_nodes": 1, ...}

# Get index statistics
stats = search.get_index_stats("documents")
print(f"Document count: {stats['document_count']:,}")
print(f"Index size: {stats['store_size_mb']} MB")
```

---

## 🔄 Migration Options

### Option 1: Full Migration (Recommended)

Migrate all data from PostgreSQL to OpenSearch:

```bash
python scripts/migrate_to_opensearch.py
```

### Option 2: Selective Migration

Migrate only specific categories:

```python
from scripts.migrate_to_opensearch import fetch_documents_from_postgres
from src.opensearch_service import OpenSearchService

# Fetch only invoices
documents = fetch_documents_from_postgres(settings.database_url)
invoices = [doc for doc in documents if doc['category'] == 'invoices']

# Index to OpenSearch
search = OpenSearchService(hosts=settings.opensearch_hosts_list)
search.bulk_index_documents("documents", invoices)
```

### Option 3: Regenerate Embeddings

Regenerate all embeddings during migration:

```bash
python scripts/migrate_to_opensearch.py --regenerate-embeddings
```

This is useful if:
- You changed embedding models
- You want to ensure consistency
- Embeddings were generated with different settings

---

## 🚨 Troubleshooting

### OpenSearch won't start

```bash
# Check logs
docker-compose -f docker-compose-opensearch.yml logs opensearch

# Common issues:
# 1. Port 9200 already in use
docker ps | grep 9200
# Solution: Stop other services or change port

# 2. Not enough memory
# Solution: Increase Docker memory limit (4GB minimum)

# 3. vm.max_map_count too low (Linux)
sudo sysctl -w vm.max_map_count=262144
```

### Migration fails

```bash
# Test with dry run
python scripts/migrate_to_opensearch.py --dry-run

# Check PostgreSQL connection
psql -h localhost -U docuser -d documents -c "SELECT COUNT(*) FROM documents;"

# Check OpenSearch connection
curl http://localhost:9200/_cluster/health
```

### Search returns no results

```bash
# Verify documents are indexed
curl http://localhost:9200/documents/_count

# Refresh index (make documents searchable)
curl -X POST http://localhost:9200/documents/_refresh

# Check mapping
curl http://localhost:9200/documents/_mapping?pretty
```

### Slow search performance

1. **Check cluster health:**
   ```bash
   curl http://localhost:9200/_cluster/health
   ```
   Should be "green" or "yellow"

2. **Check shard allocation:**
   ```bash
   curl http://localhost:9200/_cat/shards?v
   ```

3. **Increase heap size** (if you have RAM):
   Edit `docker-compose-opensearch.yml`:
   ```yaml
   environment:
     - "OPENSEARCH_JAVA_OPTS=-Xms4g -Xmx4g"  # 4GB heap
   ```

4. **Add more nodes** for horizontal scaling

---

## 📚 Additional Resources

### Official Documentation
- [OpenSearch Documentation](https://opensearch.org/docs/latest/)
- [OpenSearch Python Client](https://opensearch.org/docs/latest/clients/python/)
- [OpenSearch Dashboards](https://opensearch.org/docs/latest/dashboards/index/)

### Performance Tuning
- [Index Settings](https://opensearch.org/docs/latest/api-reference/index-apis/create-index/)
- [Search Performance](https://opensearch.org/docs/latest/tuning-your-cluster/)
- [Cluster Sizing](https://opensearch.org/docs/latest/install-and-configure/install-opensearch/cluster/)

### Production Deployment
- [AWS OpenSearch Service](https://aws.amazon.com/opensearch-service/)
- [Security Plugin](https://opensearch.org/docs/latest/security-plugin/index/)
- [Backup and Restore](https://opensearch.org/docs/latest/tuning-your-cluster/availability-and-recovery/snapshots/)

---

## 🎯 Next Steps

After setting up OpenSearch:

1. **Update your application:**
   - Set `SEARCH_BACKEND=opensearch` in `.env`
   - Test all search endpoints
   - Update documentation

2. **Set up monitoring:**
   - Create dashboards in OpenSearch Dashboards
   - Set up alerts for cluster health
   - Monitor query performance

3. **Plan for production:**
   - Enable security (SSL/TLS, authentication)
   - Set up multi-node cluster (3+ nodes)
   - Configure backups (snapshots)
   - Tune for your workload

4. **Optimize indexing:**
   - Batch document ingestion (500-1000 docs/batch)
   - Generate embeddings in parallel
   - Consider async processing for large volumes

---

## 💡 Tips for 500K+ Documents

### Indexing Strategy
```python
# Use bulk indexing with appropriate chunk size
search.bulk_index_documents(
    documents=documents,
    chunk_size=500,  # Balance speed vs memory
    generate_embeddings=True
)
```

### Search Best Practices
```python
# Use pagination
results = search.search(
    query="invoice",
    limit=20,    # Results per page
    offset=0     # Start from beginning
)

# Filter by category for faster searches
results = search.search(
    query="payment",
    category="invoices",  # Reduces search scope
    limit=20
)

# Use appropriate search mode
# - keyword: Fast, exact matches (IDs, names)
# - semantic: Smart, concept-based (questions)
# - hybrid: Best of both (recommended)
```

### Scaling Tips
1. **Start with 1 node** for development
2. **Use 3 nodes** for production (high availability)
3. **Add more nodes** as document volume grows
4. **Monitor heap usage** (should be <70%)
5. **Use SSD storage** for best performance

---

**Questions or issues?** Open an issue on GitHub or check the [troubleshooting](#-troubleshooting) section above.
