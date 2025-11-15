# Quick Reference - AI Document Pipeline

## 🚀 One-Command Start

```bash
./start_microservices.sh
```

## 🛑 Stop Everything

```bash
./stop_microservices.sh
```

---

## 📤 Upload Document

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@your-document.pdf"
```

## 📊 Monitor Progress

- **RabbitMQ UI:** http://localhost:15672 (admin/password)
- **MinIO Console:** http://localhost:9001 (minioadmin/minioadmin123)
- **Logs:** `docker-compose -f docker-compose-microservices.yml logs -f`

---

## 🔧 Common Commands

### Scale Workers
```bash
docker-compose -f docker-compose-microservices.yml up -d \
  --scale classification-worker=10
```

### Check Status
```bash
docker-compose -f docker-compose-microservices.yml ps
```

### View Logs
```bash
# All services
docker-compose -f docker-compose-microservices.yml logs -f

# Specific service
docker-compose -f docker-compose-microservices.yml logs -f ingestion-service
```

### Restart Service
```bash
docker-compose -f docker-compose-microservices.yml restart classification-worker
```

---

## 📡 Service Ports

| Service | Port | URL |
|---------|------|-----|
| Ingestion API | 8000 | http://localhost:8000 |
| Notification WebSocket | 8001 | ws://localhost:8001 |
| RabbitMQ UI | 15672 | http://localhost:15672 |
| MinIO Console | 9001 | http://localhost:9001 |
| OpenSearch | 9200 | http://localhost:9200 |
| PostgreSQL | 5432 | localhost:5432 |

---

## 🐛 Quick Troubleshooting

### Services Won't Start
```bash
# Check Docker is running
docker info

# Check logs for errors
docker-compose -f docker-compose-microservices.yml logs
```

### Worker Not Processing
```bash
# Check RabbitMQ queues
open http://localhost:15672

# Restart worker
docker-compose -f docker-compose-microservices.yml restart classification-worker
```

### Out of Memory
```bash
# Check container resources
docker stats

# Restart with less memory (edit docker-compose-microservices.yml)
# Change: OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
```

---

## 📚 Documentation

- **[README](README_MICROSERVICES.md)** - Main documentation
- **[Quick Start](MICROSERVICES_QUICK_START.md)** - Detailed setup guide
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment
- **[Architecture](EVENT_DRIVEN_ARCHITECTURE.md)** - Technical design

---

## 🎯 Performance

| Workers | Throughput |
|---------|-----------|
| 2-2-2 | 10-15 docs/min |
| 5-5-3 | 25-35 docs/min |
| 10-10-5 | 45-60 docs/min |
| 20-20-10 | 80-120 docs/min |

---

## 💾 Data Locations

- **Documents:** MinIO (docker volume `minio_data`)
- **Metadata:** PostgreSQL (docker volume `postgres_data`)
- **Search Index:** OpenSearch (docker volume `opensearch_data`)
- **Messages:** RabbitMQ (docker volume `rabbitmq_data`)

---

## 🧪 Test

```bash
python test_microservices_e2e.py test_documents/sample.pdf
```

---

**For more details, see [README_MICROSERVICES.md](README_MICROSERVICES.md)**
