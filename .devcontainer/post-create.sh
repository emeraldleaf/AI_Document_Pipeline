#!/bin/bash

# Post-create script for DevContainer
# This script runs after the container is created

set -e

echo "🚀 Running post-create setup..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Install Python dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
if [ -f /workspace/requirements.txt ]; then
    pip install -r /workspace/requirements.txt
    echo -e "${GREEN}✓ Main dependencies installed${NC}"
fi

# Install shared library dependencies
if [ -f /workspace/shared/events/requirements.txt ]; then
    pip install -r /workspace/shared/events/requirements.txt
    echo -e "${GREEN}✓ Shared events library dependencies installed${NC}"
fi

if [ -f /workspace/shared/models/requirements.txt ]; then
    pip install -r /workspace/shared/models/requirements.txt
    echo -e "${GREEN}✓ Shared models library dependencies installed${NC}"
fi

# Install microservice-specific dependencies
for service in ingestion classification-worker extraction-worker indexing-worker notification-service; do
    if [ -f /workspace/services/$service/requirements.txt ]; then
        pip install -r /workspace/services/$service/requirements.txt
        echo -e "${GREEN}✓ $service dependencies installed${NC}"
    fi
done

# Install contract testing dependencies
echo -e "${YELLOW}📋 Installing contract testing dependencies...${NC}"
if [ -f /workspace/tests/contracts/requirements-contracts.txt ]; then
    pip install -r /workspace/tests/contracts/requirements-contracts.txt
    echo -e "${GREEN}✓ Contract testing dependencies installed${NC}"
fi

# Set up pre-commit hooks (optional)
echo -e "${YELLOW}🔧 Setting up Git hooks...${NC}"
if [ -f /workspace/.pre-commit-config.yaml ]; then
    pip install pre-commit
    cd /workspace && pre-commit install
    echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
else
    echo -e "${YELLOW}⚠ No .pre-commit-config.yaml found, skipping${NC}"
fi

# Create .env file if it doesn't exist
if [ ! -f /workspace/.env ]; then
    echo -e "${YELLOW}📝 Creating .env file from .env.example...${NC}"
    if [ -f /workspace/.env.example ]; then
        cp /workspace/.env.example /workspace/.env
        echo -e "${GREEN}✓ .env file created${NC}"
        echo -e "${YELLOW}⚠ Please update .env with your configuration${NC}"
    fi
fi

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for infrastructure services...${NC}"

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
max_attempts=30
attempt=0
until PGPASSWORD=devpassword psql -h postgres -U postgres -d documents -c '\q' 2>/dev/null || [ $attempt -eq $max_attempts ]; do
    attempt=$((attempt + 1))
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${YELLOW}⚠ PostgreSQL not ready yet (will be available shortly)${NC}"
else
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
fi

# Wait for RabbitMQ
echo "Waiting for RabbitMQ..."
max_attempts=30
attempt=0
until nc -z rabbitmq 5672 || [ $attempt -eq $max_attempts ]; do
    attempt=$((attempt + 1))
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${YELLOW}⚠ RabbitMQ not ready yet (will be available shortly)${NC}"
else
    echo -e "${GREEN}✓ RabbitMQ is ready${NC}"
fi

# Wait for OpenSearch
echo "Waiting for OpenSearch..."
max_attempts=30
attempt=0
until curl -s http://opensearch:9200/_cluster/health >/dev/null || [ $attempt -eq $max_attempts ]; do
    attempt=$((attempt + 1))
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${YELLOW}⚠ OpenSearch not ready yet (will be available shortly)${NC}"
else
    echo -e "${GREEN}✓ OpenSearch is ready${NC}"
fi

# Print helpful information
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         DevContainer Setup Complete! 🎉                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📚 Quick Start:${NC}"
echo ""
echo "  1. Start all microservices:"
echo "     ./scripts/start_all.sh"
echo ""
echo "  2. Run tests:"
echo "     pytest tests/"
echo ""
echo "  3. Access services:"
echo "     - RabbitMQ Management: http://localhost:15672 (admin/password)"
echo "     - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "     - Ingestion API: http://localhost:8000"
echo "     - WebSocket: ws://localhost:8001"
echo ""
echo "  4. Pull Ollama models (required for classification/extraction):"
echo "     docker exec -it \$(docker ps -q -f name=ollama) ollama pull llama3.2-vision:11b"
echo "     docker exec -it \$(docker ps -q -f name=ollama) ollama pull llama3.2:3b"
echo ""
echo -e "${YELLOW}📖 Documentation:${NC}"
echo "  - Microservices: README_MICROSERVICES.md"
echo "  - Quick Start: MICROSERVICES_QUICK_START.md"
echo "  - Architecture: EVENT_DRIVEN_ARCHITECTURE.md"
echo "  - SQLModel: SQLMODEL_INTEGRATION.md"
echo ""
echo -e "${GREEN}✨ Happy coding!${NC}"
echo ""
