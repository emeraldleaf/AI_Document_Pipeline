#!/bin/bash

# Contract Testing Runner
# ========================
# Runs Consumer-Driven Contract tests locally

set -e

echo "🔗 Running Consumer-Driven Contract Tests"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if services are running
echo -e "${YELLOW}Checking service availability...${NC}"

# Check API
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ API service is running${NC}"
else
    echo -e "${RED}✗ API service not available at http://localhost:8000${NC}"
    echo -e "${YELLOW}💡 Start the API with: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000${NC}"
    exit 1
fi

# Check database (optional for contract tests)
if nc -z localhost 5432 2>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL not available (some tests may be skipped)${NC}"
fi

# Check OpenSearch (optional for contract tests)
if curl -s http://localhost:9200/_cluster/health > /dev/null; then
    echo -e "${GREEN}✓ OpenSearch is running${NC}"
else
    echo -e "${YELLOW}⚠ OpenSearch not available (some tests may be skipped)${NC}"
fi

echo ""

# Install contract testing dependencies if needed
echo -e "${YELLOW}Installing contract testing dependencies...${NC}"
if [ -f "tests/contracts/requirements-contracts.txt" ]; then
    pip install -r tests/contracts/requirements-contracts.txt --quiet
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

echo ""

# Validate contract files
echo -e "${YELLOW}Validating contract files...${NC}"
python tests/contracts/test_api_contracts.py
echo -e "${GREEN}✓ Contract validation complete${NC}"

echo ""

# Run contract tests
echo -e "${YELLOW}Running contract tests...${NC}"

# Create test results directory
mkdir -p test-results/contracts

# Run tests with coverage
python -m pytest tests/contracts/ \
    --tb=short \
    --verbose \
    --junitxml=test-results/contracts/junit.xml \
    --html=test-results/contracts/report.html \
    --self-contained-html

TEST_EXIT_CODE=$?

echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                Contract Tests PASSED! ✅                  ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}🎉 All contracts are satisfied!${NC}"
    echo -e "${GREEN}📊 Frontend and API are compatible${NC}"
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║               Contract Tests FAILED! ❌                   ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${RED}💥 Contract violations detected!${NC}"
    echo -e "${YELLOW}📋 Check the test output above for details${NC}"
    echo -e "${YELLOW}🔧 Update contracts or fix API to resolve issues${NC}"
fi

echo ""
echo -e "${YELLOW}📁 Test reports available at:${NC}"
echo "  - HTML Report: test-results/contracts/report.html"
echo "  - JUnit XML: test-results/contracts/junit.xml"

echo ""
echo -e "${YELLOW}📖 Contract files:${NC}"
echo "  - tests/contracts/*.json"
echo "  - tests/contracts/test_api_contracts.py"

exit $TEST_EXIT_CODE