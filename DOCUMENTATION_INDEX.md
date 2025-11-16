# Documentation Index

Complete guide to all documentation in the AI Document Classification Pipeline.

---

## 🚀 Quick Start

| Document | Purpose | Time | Audience |
|----------|---------|------|----------|
| **[START_HERE.md](START_HERE.md)** | Main entry point | 5 min | Everyone |

---

## 📚 Core Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[README.md](README.md)** | Main project documentation | Everyone |
| **[START_HERE.md](START_HERE.md)** | Getting started guide | New users |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System architecture & design | Developers |
| **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** | Project overview & stats | Stakeholders |

---

## ⚡ Parallel Processing (500K Documents)

| Document | Purpose | Audience |
|----------|---------|----------|
| **[QUICK_START_500K.md](QUICK_START_500K.md)** | Quick start for 500K documents | High-volume users |
| **[PARALLEL_PROCESSING_IMPLEMENTATION.md](PARALLEL_PROCESSING_IMPLEMENTATION.md)** | Complete technical guide | Developers |
| **[PARALLEL_PROCESSING_SUMMARY.md](PARALLEL_PROCESSING_SUMMARY.md)** | Implementation summary | Technical leads |
| **[DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md)** | Production deployment | DevOps |

---

## 🔍 Search & Indexing

| Document | Purpose | Audience |
|----------|---------|----------|
| **[SEARCH_GUIDE.md](SEARCH_GUIDE.md)** | Complete search documentation | Search users |
| **[SETUP_SEARCH.md](SETUP_SEARCH.md)** | Enable advanced search | Users wanting search |
| **[OPENSEARCH_SETUP_GUIDE.md](OPENSEARCH_SETUP_GUIDE.md)** | OpenSearch setup | DevOps |

---

## 📈 High-Throughput Processing

| Document | Purpose | Audience |
|----------|---------|----------|
| **[SCALING_GUIDE.md](SCALING_GUIDE.md)** | Complete scaling documentation | DevOps/Engineers |
| **[HIGH_THROUGHPUT_FEATURES.md](HIGH_THROUGHPUT_FEATURES.md)** | Feature overview & usage | Developers |

---

## 🧪 Testing & Quality

| Document | Purpose | Audience |
|----------|---------|----------|
| **[TESTING_GUIDE.md](TESTING_GUIDE.md)** | Testing strategy & organization | Developers/QA |
| **[END_TO_END_TESTING_GUIDE.md](END_TO_END_TESTING_GUIDE.md)** | Complete testing guide | QA Engineers |
| **[BENCHMARKING_GUIDE.md](BENCHMARKING_GUIDE.md)** | Performance benchmarking | DevOps |

---

## 🎯 Features

| Document | Purpose | Audience |
|----------|---------|----------|
| **[LLM_METADATA_EXTRACTION.md](LLM_METADATA_EXTRACTION.md)** | Metadata extraction with LLMs | Developers |
| **[SCHEMA_MANAGEMENT_GUIDE.md](SCHEMA_MANAGEMENT_GUIDE.md)** | Managing document type schemas | Developers |
| **[SPLITTING_GUIDE.md](SPLITTING_GUIDE.md)** | Document chunking | Advanced users |
| **[TRAINING_GUIDE.md](TRAINING_GUIDE.md)** | Model training & fine-tuning | ML engineers |

---

## 🏗️ Production

| Document | Purpose | Audience |
|----------|---------|----------|
| **[DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md)** | Production deployment guide | DevOps |
| **[PRODUCTION_RESILIENCE_GUIDE.md](PRODUCTION_RESILIENCE_GUIDE.md)** | Production best practices | DevOps/Engineers |
| **[DATABASE_GUIDE.md](DATABASE_GUIDE.md)** | Database management | DB administrators |

---

## 📖 Use Cases

### "I want to process 500K documents"
1. **[PARALLEL_PROCESSING_IMPLEMENTATION.md](PARALLEL_PROCESSING_IMPLEMENTATION.md)** - Complete guide
2. **[DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md)** - Deploy to production

### "I want to classify documents"
1. **[START_HERE.md](START_HERE.md)** - Getting started
2. **[README.md](README.md)** - Full documentation

### "I want to search my documents"
1. **[SETUP_SEARCH.md](SETUP_SEARCH.md)** - Enable search
2. **[SEARCH_GUIDE.md](SEARCH_GUIDE.md)** - Complete guide
3. **[OPENSEARCH_SETUP_GUIDE.md](OPENSEARCH_SETUP_GUIDE.md)** - Advanced setup

### "I want to deploy to production"
1. **[DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md)** - Deployment guide
2. **[PRODUCTION_RESILIENCE_GUIDE.md](PRODUCTION_RESILIENCE_GUIDE.md)** - Best practices
3. **[SCALING_GUIDE.md](SCALING_GUIDE.md)** - Scaling guide

### "I want to improve classification accuracy"
1. **[TRAINING_GUIDE.md](TRAINING_GUIDE.md)** - Training guide

---

## 📊 Documentation Statistics

| Category | Documents | Purpose |
|----------|-----------|---------|
| Quick Start | 1 | Fast onboarding |
| Core | 4 | Essential reading |
| Parallel Processing | 4 | 500K document processing |
| Search | 3 | Search functionality |
| High-Throughput | 2 | Scaling |
| Testing | 3 | Quality assurance |
| Features | 4 | Specific features |
| Production | 3 | Deployment |
| **Total** | **22** | **Complete coverage** |

---

## 🎯 By Role

### End Users
- [START_HERE.md](START_HERE.md)
- [SETUP_SEARCH.md](SETUP_SEARCH.md)

### Developers
- [README.md](README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PARALLEL_PROCESSING_IMPLEMENTATION.md](PARALLEL_PROCESSING_IMPLEMENTATION.md)

### DevOps Engineers
- [DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md)
- [SCALING_GUIDE.md](SCALING_GUIDE.md)
- [PRODUCTION_RESILIENCE_GUIDE.md](PRODUCTION_RESILIENCE_GUIDE.md)

### Data Scientists / ML Engineers
- [TRAINING_GUIDE.md](TRAINING_GUIDE.md)
- [LLM_METADATA_EXTRACTION.md](LLM_METADATA_EXTRACTION.md)

### Project Managers
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- [PARALLEL_PROCESSING_SUMMARY.md](PARALLEL_PROCESSING_SUMMARY.md)

---

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| [.env.example](.env.example) | Configuration template |
| [requirements.txt](requirements.txt) | Python dependencies |
| [pyproject.toml](pyproject.toml) | Project metadata |

---

## 📝 Code Documentation

| File | Lines | Purpose |
|------|-------|---------|
| [api/main.py](api/main.py) | ~1,350 | FastAPI application (search + upload) |
| [api/tasks.py](api/tasks.py) | ~350 | Celery tasks (parallel processing) |
| [src/classifier.py](src/classifier.py) | ~400 | Classification logic |
| [src/search_service.py](src/search_service.py) | ~450 | Search functionality |
| [src/metadata_extractor.py](src/metadata_extractor.py) | ~450 | Metadata extraction |

---

## 🗂️ Scripts

| File | Purpose |
|------|---------|
| [scripts/batch_upload_500k.py](scripts/batch_upload_500k.py) | Batch upload 500K documents |
| [scripts/migrate_to_opensearch.py](scripts/migrate_to_opensearch.py) | Migrate to OpenSearch |
| [scripts/start_all.sh](scripts/start_all.sh) | Start all services |

---

## 🆘 Getting Help

1. **Quick questions:** [START_HERE.md](START_HERE.md)
2. **Setup issues:** Relevant guide above
3. **Architecture questions:** [ARCHITECTURE.md](ARCHITECTURE.md)
4. **Deployment:** [DEPLOYMENT_GUIDE_PARALLEL.md](DEPLOYMENT_GUIDE_PARALLEL.md)

---

**Last Updated:** November 2025
**Total Documentation:** 22 files
