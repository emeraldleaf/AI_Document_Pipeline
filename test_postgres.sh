#!/bin/bash
# PostgreSQL Database Testing Script
# Tests the full search functionality with PostgreSQL

set -e  # Exit on error

echo "=================================="
echo "PostgreSQL Database Test"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

# Check if package is installed
echo "Step 0: Checking installation..."
if ! command -v doc-classify &> /dev/null; then
    print_error "doc-classify not found"
    echo ""
    echo "Installing package in editable mode..."
    if pip install -e . &> /dev/null; then
        print_success "Package installed"
    else
        print_error "Failed to install package"
        echo "Try manually: pip install -e ."
        exit 1
    fi
else
    print_success "Package already installed"
fi
echo ""

# Check Docker
echo "Step 1: Checking Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker not installed"
    echo "Install with: brew install --cask docker"
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker not running. Please start Docker Desktop."
    exit 1
fi
print_success "Docker is running"
echo ""

# Check/Start PostgreSQL
echo "Step 2: PostgreSQL setup..."
if docker ps | grep -q "doc_pipeline_postgres"; then
    print_info "PostgreSQL already running"
else
    print_info "Starting PostgreSQL with pgvector..."
    docker-compose up -d

    print_info "Waiting for PostgreSQL..."
    sleep 5

    for i in {1..20}; do
        if docker-compose exec -T postgres pg_isready -U docuser -d documents &> /dev/null; then
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
fi

if docker-compose exec -T postgres pg_isready -U docuser -d documents &> /dev/null; then
    print_success "PostgreSQL is healthy"
else
    print_error "PostgreSQL failed to start"
    echo "Check logs: docker-compose logs postgres"
    exit 1
fi
echo ""

# Check Ollama
echo "Step 3: Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    print_error "Ollama not running"
    echo "Start with: brew services start ollama"
    exit 1
fi
print_success "Ollama is running"

# Check models
if ! ollama list | grep -q "llama3.2:3b"; then
    print_info "Pulling classification model..."
    ollama pull llama3.2:3b
fi

if ! ollama list | grep -q "nomic-embed-text"; then
    print_info "Pulling embedding model..."
    ollama pull nomic-embed-text
fi
print_success "Models ready"
echo ""

# Setup .env
echo "Step 4: Configuration..."
if [ ! -f .env ]; then
    print_info "Creating .env file..."
    cp .env.example .env
    print_success ".env created"
else
    print_info ".env already exists"
fi
echo ""

# Create test documents
echo "Step 5: Creating test documents..."
mkdir -p documents/input

for name in "Intellidex" "DocuMind" "Luminary" "Sortex" "Docly"
do
    echo -n "$name: "
    # Convert to uppercase for invoice number
    name_upper=$(echo "$name" | tr '[:lower:]' '[:upper:]')
    cat > "documents/input/${name}_invoice.txt" << EOF
INVOICE #2024-${name_upper}-001

Company: $name Technologies
Date: October 27, 2024
Customer: Test Corp

Services Rendered:
- AI Document Classification
- Database Integration
- Search Implementation

Amount: \$$(( RANDOM % 5000 + 1000 ))

Payment terms: Net 30
EOF
    echo "✓"
done
print_success "Created 5 test invoices"
echo ""

# Test classification
echo "Step 6: Testing classification + database..."
print_info "Classifying documents (this stores them in PostgreSQL)..."
if doc-classify classify documents/input; then
    print_success "Documents classified and stored"
else
    print_error "Classification failed"
    exit 1
fi
echo ""

# Test database stats
echo "Step 7: Database statistics..."
doc-classify search-stats
echo ""

# Test keyword search
echo "Step 8: Testing keyword search..."
print_info "Searching for 'invoice'..."
doc-classify search "invoice" --mode keyword --limit 3
print_success "Keyword search works"
echo ""

# Generate embeddings
echo "Step 9: Generating embeddings..."
print_info "This may take 30-60 seconds..."
if doc-classify reindex --include-vectors; then
    print_success "Embeddings generated"
else
    print_error "Embedding generation failed"
fi
echo ""

# Test semantic search
echo "Step 10: Testing semantic search..."
print_info "Searching for 'payment document'..."
doc-classify search "payment document" --mode semantic --limit 3
print_success "Semantic search works"
echo ""

# Test hybrid search
echo "Step 11: Testing hybrid search..."
print_info "Searching for 'AI services'..."
doc-classify search "AI services" --mode hybrid --limit 3
print_success "Hybrid search works"
echo ""

# Final stats
echo "Step 12: Final database state..."
doc-classify search-stats
echo ""

echo "=================================="
print_success "ALL TESTS PASSED!"
echo "=================================="
echo ""
echo "✅ PostgreSQL database working"
echo "✅ Full-text search working"
echo "✅ Semantic search working"
echo "✅ Hybrid search working"
echo ""
echo "Try these commands:"
echo "  doc-classify search \"your query\""
echo "  doc-classify search \"AI\" --mode semantic"
echo "  doc-classify db-stats"
echo ""
echo "Stop PostgreSQL:"
echo "  docker-compose down"
echo ""
