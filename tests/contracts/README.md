# Consumer-Driven Contract Testing

This directory contains Consumer-Driven Contract (CDC) tests for the AI Document Pipeline microservices. CDC testing ensures that API changes don't break frontend expectations by validating contracts between consumers (frontend) and providers (API).

## 📋 Overview

- **Purpose**: Prevent integration hell in microservices by catching API compatibility issues early
- **Framework**: [Pact](https://pact.io/) - industry standard for CDC testing
- **Coverage**: All major API endpoints (search, documents, batch upload, health/stats)

## 📁 Directory Structure

```
tests/contracts/
├── contracts/                    # Generated Pact contract files
├── frontend-api-search-contract.json      # Search endpoint contract
├── frontend-api-documents-contract.json   # Documents endpoint contract
├── frontend-api-batch-contract.json       # Batch upload contract
├── frontend-api-health-contract.json      # Health/stats contract
├── test_api_contracts.py         # Contract validation tests
└── requirements-contracts.txt    # Contract testing dependencies
```

## 🚀 Quick Start

### Prerequisites

1. **Services Running**: Start the API and dependencies:
   ```bash
   # Start all services
   docker-compose up -d

   # Or start API manually
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

2. **Dependencies**: Install contract testing libraries:
   ```bash
   pip install -r tests/contracts/requirements-contracts.txt
   ```

### Run Contract Tests

```bash
# Run all contract tests
./scripts/run_contract_tests.sh

# Or run directly with pytest
python -m pytest tests/contracts/ --tb=short --verbose
```

## 📝 Contract Files

Each contract defines the expected API behavior from the frontend's perspective:

### Search Contract (`frontend-api-search-contract.json`)
- **Endpoint**: `GET /api/search`
- **Purpose**: Semantic search with filters
- **Validates**: Query parameters, response format, error handling

### Documents Contract (`frontend-api-documents-contract.json`)
- **Endpoint**: `GET /api/documents/{id}`
- **Purpose**: Document retrieval and metadata
- **Validates**: Document structure, metadata fields, error responses

### Batch Upload Contract (`frontend-api-batch-contract.json`)
- **Endpoint**: `POST /api/documents/batch`
- **Purpose**: Bulk document processing
- **Validates**: File upload, processing status, error handling

### Health Contract (`frontend-api-health-contract.json`)
- **Endpoint**: `GET /api/health`
- **Purpose**: Service health and statistics
- **Validates**: Health status, metrics format, uptime information

## 🔧 Development Workflow

### When API Changes

1. **Update Contract**: Modify the relevant JSON contract file
2. **Run Tests**: Execute contract tests to validate changes
3. **Fix Issues**: Update API or contract until tests pass
4. **Commit**: Include contract updates with API changes

### When Frontend Changes

1. **Review Contracts**: Check if new requirements need contract updates
2. **Update Contracts**: Add new expectations to contract files
3. **Validate**: Run tests against updated contracts
4. **Coordinate**: Work with API team to implement changes

## 🧪 Test Structure

The `test_api_contracts.py` file contains:

- **Contract Validation**: Ensures contracts are properly formatted
- **API Compatibility**: Tests actual API responses against contracts
- **Error Scenarios**: Validates error handling and edge cases
- **Performance Checks**: Basic response time validation

## 🔄 CI/CD Integration

Contract tests run automatically in CI/CD:

- **Trigger**: On pull requests and pushes to main
- **Services**: Spins up API, PostgreSQL, and OpenSearch containers
- **Reports**: Generates HTML and JUnit test reports
- **Failure**: Blocks deployment if contracts are violated

See: `.github/workflows/contract-tests.yml`

## 🛠️ Troubleshooting

### Common Issues

**"Service not available"**
- Ensure API is running on `http://localhost:8000`
- Check Docker containers: `docker-compose ps`

**"Contract validation failed"**
- Review contract JSON syntax
- Compare with API response format
- Update contract expectations

**"Pact library not found"**
- Install dependencies: `pip install -r tests/contracts/requirements-contracts.txt`
- Check Python environment

### Debug Mode

Run tests with detailed output:
```bash
python -m pytest tests/contracts/ -v -s --tb=long
```

## 📊 Reports

Test results are saved to `test-results/contracts/`:
- **HTML Report**: `report.html` - Interactive test results
- **JUnit XML**: `junit.xml` - Machine-readable format for CI

## 🎯 Best Practices

1. **Keep Contracts Current**: Update contracts with every API change
2. **Test Early**: Run contracts during development, not just CI
3. **Version Contracts**: Use semantic versioning for contract changes
4. **Document Changes**: Include contract updates in PR descriptions
5. **Monitor Failures**: Set up alerts for contract test failures

## 📚 Resources

- [Pact Documentation](https://pact.io/documentation)
- [Consumer-Driven Contracts](https://martinfowler.com/articles/consumerDrivenContracts.html)
- [API Contract Testing Guide](https://pact.io/consumer)

## 🤝 Contributing

When making API changes:
1. Update relevant contract files
2. Run contract tests locally
3. Include contract changes in your PR
4. Update this README if needed

---

**Need Help?** Check the [main README](../README.md) or open an issue.