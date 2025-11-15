# Event-Driven Microservices Architecture

## Overview
Transform the AI Document Pipeline into a modular, event-driven architecture using Docker containers, message queues, and microservices patterns.

---

## Current Architecture (Monolithic)

```
┌─────────────────────────────────────────────────┐
│              FastAPI Application                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Upload   │  │ Search   │  │ Extract  │      │
│  │ Handler  │  │ Handler  │  │ Handler  │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│         │            │            │              │
│         └────────────┴────────────┘              │
└─────────────────────────────────────────────────┘
         │                   │
         ▼                   ▼
   PostgreSQL          OpenSearch
```

**Issues:**
- ❌ Tight coupling between services
- ❌ Single point of failure
- ❌ Difficult to scale individual components
- ❌ Can't deploy services independently

---

## Proposed Event-Driven Architecture

```
                        ┌─────────────────┐
                        │   API Gateway   │
                        │   (Kong/Nginx)  │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
         ┌──────────▼──┐  ┌─────▼─────┐  ┌──▼──────────┐
         │  Ingestion  │  │  Search   │  │  Metadata   │
         │  Service    │  │  Service  │  │  Service    │
         └──────┬──────┘  └─────┬─────┘  └──────┬──────┘
                │                │                │
                └────────────────┼────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Event Bus (RabbitMQ)  │
                    │   or Redis Streams      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
         ┌──────────▼──┐  ┌─────▼─────┐  ┌──▼──────────┐
         │Classification│  │Extraction │  │ Indexing   │
         │  Worker     │  │  Worker   │  │  Worker    │
         └──────┬──────┘  └─────┬─────┘  └──────┬──────┘
                │                │                │
                └────────────────┼────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Storage Layer         │
                    ├─────────────────────────┤
                    │ PostgreSQL │ OpenSearch │
                    │ S3/MinIO   │ Redis      │
                    └─────────────────────────┘
```

---

## Microservices Breakdown

### 1. **API Gateway Service** 🌐
**Responsibility:** Single entry point, routing, authentication, rate limiting

**Tech Stack:**
- Kong or Nginx
- JWT authentication
- Rate limiting per client

**Container:** `api-gateway`

**Events Consumed:** None (HTTP only)
**Events Published:** None

---

### 2. **Ingestion Service** 📤
**Responsibility:** Handle file uploads, validate, store, trigger processing

**Tech Stack:**
- FastAPI
- S3 client (MinIO/AWS SDK)
- File validation

**Container:** `ingestion-service`

**API Endpoints:**
- `POST /upload` - Single file upload
- `POST /batch-upload` - Multiple files upload
- `GET /upload-status/{id}` - Check upload status

**Events Published:**
- `document.uploaded` - When file is stored
- `batch.uploaded` - When batch is ready

**Example Event:**
```json
{
  "event_type": "document.uploaded",
  "timestamp": "2025-11-12T10:30:00Z",
  "document_id": "uuid",
  "file_path": "s3://bucket/path/file.pdf",
  "metadata": {
    "filename": "invoice.pdf",
    "size_bytes": 102400,
    "mime_type": "application/pdf"
  }
}
```

---

### 3. **Classification Worker** 🏷️
**Responsibility:** Classify documents into categories

**Tech Stack:**
- Python worker process
- Ollama client
- Celery (optional)

**Container:** `classification-worker`

**Events Consumed:**
- `document.uploaded`

**Events Published:**
- `document.classified`

**Processing Logic:**
```python
def classify_document(event):
    document_id = event['document_id']
    file_path = event['file_path']

    # Download from S3
    file_data = s3_client.download(file_path)

    # Classify using LLM
    category = ollama_classifier.classify(file_data)

    # Publish result
    publish_event('document.classified', {
        'document_id': document_id,
        'category': category,
        'confidence': 0.95
    })
```

---

### 4. **Extraction Worker** 📝
**Responsibility:** Extract structured metadata from documents

**Tech Stack:**
- Python worker
- Docling
- LLM metadata extractor

**Container:** `extraction-worker`

**Events Consumed:**
- `document.classified`

**Events Published:**
- `document.extracted`

**Processing Logic:**
```python
def extract_metadata(event):
    document_id = event['document_id']
    category = event['category']

    # Get schema for category
    schema = schema_registry.get(category)

    # Extract using Docling + LLM
    metadata = extractor.extract(file_path, schema)

    # Publish result
    publish_event('document.extracted', {
        'document_id': document_id,
        'metadata': metadata,
        'confidence': 0.87
    })
```

---

### 5. **Indexing Worker** 🔍
**Responsibility:** Generate embeddings and index to OpenSearch

**Tech Stack:**
- Python worker
- Ollama embeddings
- OpenSearch client

**Container:** `indexing-worker`

**Events Consumed:**
- `document.extracted`

**Events Published:**
- `document.indexed`

**Processing Logic:**
```python
def index_document(event):
    document_id = event['document_id']
    metadata = event['metadata']

    # Generate embeddings
    embeddings = ollama.embed(metadata['text'])

    # Index to OpenSearch
    opensearch_client.index(
        index='documents',
        id=document_id,
        body={
            'metadata': metadata,
            'embedding': embeddings
        }
    )

    # Publish completion
    publish_event('document.indexed', {
        'document_id': document_id
    })
```

---

### 6. **Search Service** 🔎
**Responsibility:** Provide search API

**Tech Stack:**
- FastAPI
- OpenSearch client
- PostgreSQL client

**Container:** `search-service`

**API Endpoints:**
- `GET /search?q=...&mode=...`
- `GET /documents/{id}`

**Events Consumed:** None
**Events Published:** None

---

### 7. **Metadata Service** 📊
**Responsibility:** Store and retrieve document metadata

**Tech Stack:**
- FastAPI
- PostgreSQL
- Redis cache

**Container:** `metadata-service`

**API Endpoints:**
- `GET /documents/{id}/metadata`
- `PUT /documents/{id}/metadata`
- `GET /stats`

**Events Consumed:**
- `document.indexed` (to update status)

**Events Published:** None

---

### 8. **Notification Service** 📬
**Responsibility:** Send notifications via WebSocket, email, webhooks

**Tech Stack:**
- FastAPI WebSocket
- Redis pub/sub
- Email client (optional)

**Container:** `notification-service`

**Events Consumed:**
- `document.classified`
- `document.extracted`
- `document.indexed`
- `batch.completed`

**Events Published:** None (sends notifications)

**WebSocket Example:**
```python
@app.websocket("/ws/progress/{batch_id}")
async def progress_websocket(websocket: WebSocket, batch_id: str):
    await websocket.accept()

    # Subscribe to Redis channel
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f'batch:{batch_id}')

    # Stream progress updates
    async for message in pubsub.listen():
        await websocket.send_json(message['data'])
```

---

## Event Bus Implementation

### Option 1: RabbitMQ (Recommended)
**Pros:**
- ✅ Mature, battle-tested
- ✅ Rich routing capabilities (topics, fanout, direct)
- ✅ Built-in dead-letter queues
- ✅ Message persistence
- ✅ Management UI

**Cons:**
- ❌ Additional complexity
- ❌ Higher memory usage

**Docker Compose:**
```yaml
rabbitmq:
  image: rabbitmq:3-management
  ports:
    - "5672:5672"    # AMQP
    - "15672:15672"  # Management UI
  environment:
    RABBITMQ_DEFAULT_USER: admin
    RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
  volumes:
    - rabbitmq_data:/var/lib/rabbitmq
```

**Python Client:**
```python
import pika

# Publisher
connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
channel = connection.channel()
channel.queue_declare(queue='document.uploaded', durable=True)

channel.basic_publish(
    exchange='',
    routing_key='document.uploaded',
    body=json.dumps(event_data),
    properties=pika.BasicProperties(delivery_mode=2)  # Persistent
)

# Consumer
def callback(ch, method, properties, body):
    event = json.loads(body)
    process_event(event)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='document.uploaded', on_message_callback=callback)
channel.start_consuming()
```

### Option 2: Redis Streams
**Pros:**
- ✅ Simple, familiar (already using Redis)
- ✅ Lower resource usage
- ✅ Built-in persistence
- ✅ Consumer groups

**Cons:**
- ❌ Less mature for message queuing
- ❌ Simpler routing

**Python Client:**
```python
import redis

r = redis.Redis(host='redis', port=6379)

# Publisher
r.xadd('document.uploaded', {'data': json.dumps(event_data)})

# Consumer
while True:
    events = r.xreadgroup(
        groupname='classification-workers',
        consumername='worker-1',
        streams={'document.uploaded': '>'},
        count=10,
        block=5000
    )
    for stream, messages in events:
        for message_id, data in messages:
            process_event(json.loads(data[b'data']))
            r.xack('document.uploaded', 'classification-workers', message_id)
```

---

## Docker Container Setup

### Directory Structure
```
AI_Document_Pipeline/
├── docker-compose.yml
├── docker-compose.prod.yml
├── services/
│   ├── api-gateway/
│   │   ├── Dockerfile
│   │   └── nginx.conf
│   ├── ingestion/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── main.py
│   ├── classification-worker/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── worker.py
│   ├── extraction-worker/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── worker.py
│   ├── indexing-worker/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── worker.py
│   ├── search-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── main.py
│   ├── metadata-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── main.py
│   └── notification-service/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── main.py
├── shared/
│   ├── events/
│   │   ├── __init__.py
│   │   ├── publisher.py
│   │   └── consumer.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── utils/
│       ├── __init__.py
│       └── s3_client.py
└── frontend/
    ├── Dockerfile
    └── ...
```

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  # Infrastructure Services
  rabbitmq:
    image: rabbitmq:3-management
    container_name: rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-password}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - doc-pipeline
    healthcheck:
      test: rabbitmq-diagnostics -q ping
      interval: 30s
      timeout: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - doc-pipeline
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5

  postgres:
    image: postgres:15-alpine
    container_name: postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-documents}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - doc-pipeline
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 5

  opensearch:
    image: opensearchproject/opensearch:2
    container_name: opensearch
    environment:
      - discovery.type=single-node
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
      - DISABLE_SECURITY_PLUGIN=true
    ports:
      - "9200:9200"
    volumes:
      - opensearch_data:/usr/share/opensearch/data
    networks:
      - doc-pipeline
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
    volumes:
      - minio_data:/data
    networks:
      - doc-pipeline
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - doc-pipeline

  # Application Services
  api-gateway:
    build: ./services/api-gateway
    container_name: api-gateway
    ports:
      - "80:80"
    depends_on:
      - ingestion-service
      - search-service
      - metadata-service
    networks:
      - doc-pipeline
    volumes:
      - ./services/api-gateway/nginx.conf:/etc/nginx/nginx.conf:ro

  ingestion-service:
    build: ./services/ingestion
    container_name: ingestion-service
    environment:
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD:-password}@rabbitmq:5672/
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-minioadmin}
      POSTGRES_URL: postgresql://postgres:${POSTGRES_PASSWORD:-password}@postgres:5432/documents
    depends_on:
      rabbitmq:
        condition: service_healthy
      minio:
        condition: service_healthy
      postgres:
        condition: service_healthy
    networks:
      - doc-pipeline
    volumes:
      - ./shared:/app/shared:ro

  classification-worker:
    build: ./services/classification-worker
    container_name: classification-worker
    deploy:
      replicas: 3  # Scale as needed
    environment:
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD:-password}@rabbitmq:5672/
      OLLAMA_URL: http://ollama:11434
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-minioadmin}
    depends_on:
      rabbitmq:
        condition: service_healthy
      ollama:
        condition: service_started
    networks:
      - doc-pipeline
    volumes:
      - ./shared:/app/shared:ro

  extraction-worker:
    build: ./services/extraction-worker
    container_name: extraction-worker
    deploy:
      replicas: 3
    environment:
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD:-password}@rabbitmq:5672/
      OLLAMA_URL: http://ollama:11434
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-minioadmin}
    depends_on:
      rabbitmq:
        condition: service_healthy
      ollama:
        condition: service_started
    networks:
      - doc-pipeline
    volumes:
      - ./shared:/app/shared:ro

  indexing-worker:
    build: ./services/indexing-worker
    container_name: indexing-worker
    deploy:
      replicas: 2
    environment:
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD:-password}@rabbitmq:5672/
      OLLAMA_URL: http://ollama:11434
      OPENSEARCH_URL: http://opensearch:9200
      POSTGRES_URL: postgresql://postgres:${POSTGRES_PASSWORD:-password}@postgres:5432/documents
    depends_on:
      rabbitmq:
        condition: service_healthy
      opensearch:
        condition: service_healthy
      postgres:
        condition: service_healthy
    networks:
      - doc-pipeline
    volumes:
      - ./shared:/app/shared:ro

  search-service:
    build: ./services/search-service
    container_name: search-service
    environment:
      OPENSEARCH_URL: http://opensearch:9200
      POSTGRES_URL: postgresql://postgres:${POSTGRES_PASSWORD:-password}@postgres:5432/documents
      REDIS_URL: redis://redis:6379/0
    depends_on:
      opensearch:
        condition: service_healthy
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - doc-pipeline

  metadata-service:
    build: ./services/metadata-service
    container_name: metadata-service
    environment:
      POSTGRES_URL: postgresql://postgres:${POSTGRES_PASSWORD:-password}@postgres:5432/documents
      REDIS_URL: redis://redis:6379/0
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD:-password}@rabbitmq:5672/
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - doc-pipeline

  notification-service:
    build: ./services/notification-service
    container_name: notification-service
    environment:
      REDIS_URL: redis://redis:6379/0
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD:-password}@rabbitmq:5672/
    depends_on:
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - doc-pipeline

  frontend:
    build: ./frontend
    container_name: frontend
    ports:
      - "3000:80"
    depends_on:
      - api-gateway
    networks:
      - doc-pipeline

volumes:
  rabbitmq_data:
  redis_data:
  postgres_data:
  opensearch_data:
  minio_data:
  ollama_data:

networks:
  doc-pipeline:
    driver: bridge
```

---

## Shared Event Library

### `shared/events/publisher.py`
```python
import json
from typing import Dict, Any
import pika
from datetime import datetime

class EventPublisher:
    def __init__(self, rabbitmq_url: str):
        self.connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url)
        )
        self.channel = self.connection.channel()

        # Declare exchanges
        self.channel.exchange_declare(
            exchange='documents',
            exchange_type='topic',
            durable=True
        )

    def publish(self, event_type: str, payload: Dict[str, Any]):
        """
        Publish an event to the message bus.

        Args:
            event_type: e.g., 'document.uploaded', 'document.classified'
            payload: Event data
        """
        event = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'payload': payload
        }

        self.channel.basic_publish(
            exchange='documents',
            routing_key=event_type,
            body=json.dumps(event),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type='application/json'
            )
        )

        print(f"Published event: {event_type}")

    def close(self):
        self.connection.close()
```

### `shared/events/consumer.py`
```python
import json
from typing import Callable, Dict
import pika

class EventConsumer:
    def __init__(self, rabbitmq_url: str, queue_name: str, event_patterns: list):
        """
        Args:
            queue_name: Unique queue name for this consumer
            event_patterns: List of routing keys to subscribe to (e.g., ['document.uploaded'])
        """
        self.connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url)
        )
        self.channel = self.connection.channel()

        # Declare exchange
        self.channel.exchange_declare(
            exchange='documents',
            exchange_type='topic',
            durable=True
        )

        # Declare queue
        self.channel.queue_declare(queue=queue_name, durable=True)

        # Bind queue to patterns
        for pattern in event_patterns:
            self.channel.queue_bind(
                exchange='documents',
                queue=queue_name,
                routing_key=pattern
            )

        self.queue_name = queue_name
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler function for an event type."""
        self.handlers[event_type] = handler

    def start(self):
        """Start consuming events."""
        def callback(ch, method, properties, body):
            event = json.loads(body)
            event_type = event['event_type']

            if event_type in self.handlers:
                try:
                    self.handlers[event_type](event['payload'])
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"Error processing event: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            else:
                print(f"No handler for event type: {event_type}")
                ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback
        )

        print(f"Started consuming from queue: {self.queue_name}")
        self.channel.start_consuming()
```

---

## Event Flow Example

### Document Upload Flow
```
1. User uploads document
   ↓
2. API Gateway → Ingestion Service
   ↓
3. Ingestion Service:
   - Validates file
   - Stores to MinIO
   - Saves metadata to PostgreSQL
   - Publishes "document.uploaded" event
   ↓
4. RabbitMQ receives event
   ↓
5. Classification Worker consumes event:
   - Downloads file from MinIO
   - Classifies using Ollama
   - Publishes "document.classified" event
   ↓
6. Extraction Worker consumes event:
   - Downloads file from MinIO
   - Extracts metadata with Docling + LLM
   - Publishes "document.extracted" event
   ↓
7. Indexing Worker consumes event:
   - Generates embeddings
   - Indexes to OpenSearch
   - Updates PostgreSQL status
   - Publishes "document.indexed" event
   ↓
8. Notification Service consumes event:
   - Sends WebSocket notification to client
   - "Document processing complete!"
```

---

## Benefits of Event-Driven Architecture

### 1. **Loose Coupling** 🔗
- Services don't need to know about each other
- Add/remove services without affecting others
- Easy to test services in isolation

### 2. **Scalability** 📈
- Scale workers independently based on queue depth
- Add more classification workers if classification is slow
- Auto-scaling based on metrics

### 3. **Resilience** 🛡️
- If a worker crashes, messages stay in queue
- Automatic retry with dead-letter queues
- No data loss

### 4. **Flexibility** 🔄
- Easy to add new processing steps
- A/B testing of different algorithms
- Replay events for reprocessing

### 5. **Observability** 👁️
- Track events through the system
- Measure processing time per stage
- Identify bottlenecks

---

## Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)
1. ✅ Set up RabbitMQ/Redis Streams
2. ✅ Set up MinIO for file storage
3. ✅ Create shared event library
4. ✅ Update docker-compose.yml

### Phase 2: Extract Workers (Week 2)
1. ✅ Create classification-worker container
2. ✅ Create extraction-worker container
3. ✅ Create indexing-worker container
4. ✅ Keep API as event publisher (hybrid mode)

### Phase 3: Split Services (Week 3)
1. ✅ Extract ingestion logic to ingestion-service
2. ✅ Extract search logic to search-service
3. ✅ Extract metadata logic to metadata-service
4. ✅ Add API gateway

### Phase 4: Add Advanced Features (Week 4)
1. ✅ Add notification-service
2. ✅ Implement dead-letter queues
3. ✅ Add monitoring and metrics
4. ✅ Add health checks

### Phase 5: Production Hardening (Week 5)
1. ✅ Add authentication/authorization
2. ✅ Implement rate limiting
3. ✅ Add distributed tracing
4. ✅ Performance testing and optimization

---

## Monitoring & Observability

### Prometheus Metrics
```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus_data:/prometheus

grafana:
  image: grafana/grafana
  ports:
    - "3001:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: admin
  volumes:
    - grafana_data:/var/lib/grafana
```

### Metrics to Track
- Queue depth per event type
- Processing time per worker type
- Success/failure rates
- Document throughput (docs/hour)
- Worker CPU/memory usage
- API response times

---

## Kubernetes Deployment (Future)

### Helm Chart Structure
```
helm/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── ingestion-deployment.yaml
    ├── classification-deployment.yaml
    ├── extraction-deployment.yaml
    ├── indexing-deployment.yaml
    ├── search-deployment.yaml
    ├── metadata-deployment.yaml
    ├── notification-deployment.yaml
    ├── hpa.yaml  # Horizontal Pod Autoscaler
    └── service.yaml
```

### Auto-scaling Example
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: classification-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: classification-worker
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: rabbitmq_queue_messages
        selector:
          matchLabels:
            queue: document.uploaded
      target:
        type: AverageValue
        averageValue: "30"  # Scale up if >30 messages per pod
```

---

## Conclusion

This event-driven microservices architecture provides:
- ✅ **Modularity**: Each service has a single responsibility
- ✅ **Scalability**: Scale components independently
- ✅ **Resilience**: Fault isolation and automatic retry
- ✅ **Maintainability**: Easy to update individual services
- ✅ **Observability**: Track events through the system
- ✅ **Flexibility**: Add new features without breaking existing ones

**Next Steps:** Start with Phase 1 infrastructure setup!
