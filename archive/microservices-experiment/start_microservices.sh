#!/bin/bash
#
# AI Document Pipeline - Microservices Startup Script
#
# This script will:
# 1. Start all infrastructure services
# 2. Wait for services to be healthy
# 3. Pull required AI models
# 4. Start all application services
# 5. Run health checks
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose-microservices.yml"
OLLAMA_CONTAINER="doc-pipeline-ollama"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   AI Document Pipeline - Microservices Deployment         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print colored messages
print_step() {
    echo -e "\n${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    print_step "Checking Docker..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if docker-compose file exists
check_compose_file() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "docker-compose file not found: $COMPOSE_FILE"
        exit 1
    fi
}

# Function to start infrastructure services
start_infrastructure() {
    print_step "Starting infrastructure services..."

    docker-compose -f "$COMPOSE_FILE" up -d \
        rabbitmq \
        redis \
        postgres \
        opensearch \
        minio \
        minio-setup \
        ollama

    print_success "Infrastructure services started"
}

# Function to wait for service health
wait_for_service() {
    local service=$1
    local max_attempts=60
    local attempt=1

    print_step "Waiting for $service to be healthy..."

    while [ $attempt -le $max_attempts ]; do
        local health=$(docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -c "healthy" || true)

        if [ "$health" -gt 0 ]; then
            print_success "$service is healthy"
            return 0
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "$service did not become healthy in time"
    return 1
}

# Function to check if Ollama model exists
check_ollama_model() {
    local model=$1
    docker exec "$OLLAMA_CONTAINER" ollama list | grep -q "$model"
}

# Function to pull Ollama models
pull_ollama_models() {
    print_step "Checking Ollama models..."

    local models=("llama3.2-vision" "llama3.2" "nomic-embed-text")

    for model in "${models[@]}"; do
        if check_ollama_model "$model"; then
            print_success "$model already installed"
        else
            print_step "Pulling $model (this may take several minutes)..."
            docker exec "$OLLAMA_CONTAINER" ollama pull "$model"
            print_success "$model installed"
        fi
    done
}

# Function to start application services
start_applications() {
    print_step "Starting application services..."

    docker-compose -f "$COMPOSE_FILE" up -d --build \
        ingestion-service \
        classification-worker \
        extraction-worker \
        indexing-worker \
        notification-service

    print_success "Application services started"
}

# Function to check service health via HTTP
check_http_health() {
    local name=$1
    local url=$2

    if curl -s -f "$url" > /dev/null 2>&1; then
        print_success "$name is responding"
        return 0
    else
        print_warning "$name is not responding yet"
        return 1
    fi
}

# Function to run health checks
run_health_checks() {
    print_step "Running health checks..."

    sleep 5  # Give services time to start

    check_http_health "Ingestion Service" "http://localhost:8000/health"
    check_http_health "Notification Service" "http://localhost:8001/health"
    check_http_health "RabbitMQ" "http://localhost:15672"
    check_http_health "MinIO" "http://localhost:9001"
    check_http_health "OpenSearch" "http://localhost:9200/_cluster/health"
}

# Function to display service URLs
display_urls() {
    echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Services Started Successfully!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}\n"

    echo "📡 API Endpoints:"
    echo "   Ingestion API:     http://localhost:8000"
    echo "   API Documentation: http://localhost:8000/docs"
    echo "   Notification API:  http://localhost:8001"
    echo ""
    echo "🎛️  Management UIs:"
    echo "   RabbitMQ:          http://localhost:15672  (admin/password)"
    echo "   MinIO Console:     http://localhost:9001   (minioadmin/minioadmin123)"
    echo "   OpenSearch:        http://localhost:9200"
    echo ""
    echo "📊 Quick Test:"
    echo "   Upload a document:"
    echo "   curl -X POST http://localhost:8000/api/upload -F \"file=@your-file.pdf\""
    echo ""
    echo "📚 Documentation:"
    echo "   Quick Start:       MICROSERVICES_QUICK_START.md"
    echo "   Deployment Guide:  DEPLOYMENT_GUIDE.md"
    echo "   Architecture:      EVENT_DRIVEN_ARCHITECTURE.md"
    echo ""
    echo "🔍 Monitor Services:"
    echo "   View logs:         docker-compose -f $COMPOSE_FILE logs -f"
    echo "   Check status:      docker-compose -f $COMPOSE_FILE ps"
    echo ""
}

# Function to display next steps
display_next_steps() {
    echo "🚀 Next Steps:"
    echo ""
    echo "1. Upload a test document:"
    echo "   curl -X POST http://localhost:8000/api/upload -F \"file=@test.pdf\""
    echo ""
    echo "2. Monitor progress in RabbitMQ UI:"
    echo "   open http://localhost:15672"
    echo ""
    echo "3. Run end-to-end test:"
    echo "   python test_microservices_e2e.py test_documents/sample.pdf"
    echo ""
    echo "4. Scale workers as needed:"
    echo "   docker-compose -f $COMPOSE_FILE up -d --scale classification-worker=5"
    echo ""
}

# Main execution
main() {
    # Check prerequisites
    check_docker
    check_compose_file

    # Start infrastructure
    start_infrastructure

    # Wait for critical services
    wait_for_service "rabbitmq"
    wait_for_service "postgres"
    wait_for_service "opensearch"
    wait_for_service "minio"

    # Pull AI models
    pull_ollama_models

    # Start applications
    start_applications

    # Run health checks
    run_health_checks

    # Display information
    display_urls
    display_next_steps

    echo -e "${GREEN}✓ Deployment complete!${NC}\n"
}

# Run main function
main
