# Testing Strategy and Organization

## Overview

The AI Document Pipeline project has a comprehensive testing strategy with tests organized in different locations for different purposes.

## Test Organization

### `/tests/` folder - Unit Tests
This folder contains **unit tests** for the application modules, following Python testing best practices:

- **Purpose**: Test individual components in isolation
- **Scope**: Test domain logic, service implementations, and Protocol interfaces
- **Framework**: pytest with pytest-asyncio for async testing
- **Coverage**: Tests both new Protocol-based architecture and legacy compatibility

#### Current Test Files:
- `test_extractors.py` - Tests for legacy document extractors (updated for new architecture)
- `test_ollama_service.py` - Tests for Ollama integration service
- `test_new_architecture.py` - Comprehensive tests for new Protocol-based architecture

#### Test Coverage Areas:
1. **Domain Models**: DocumentMetadata, ExtractedContent, Result types
2. **Protocol Implementations**: OCR, Classification, Extraction services
3. **Infrastructure Layer**: Document extractors, service integrations
4. **Backward Compatibility**: Legacy imports and API compatibility
5. **Error Handling**: Result types, async operations, service failures

### `/scripts/` folder - Integration Tests & Utilities
This folder contains **integration test scripts** and **utility scripts** for development and validation:

- **Purpose**: Test real system integration and provide development utilities
- **Scope**: End-to-end testing with actual services (Tesseract, file I/O)
- **Framework**: Standalone Python scripts with rich console output
- **Usage**: Manual execution for validation and debugging

#### Current Script Files:
- `test_ocr.py` - Integration test for OCR functionality with real images

#### Script Purposes:
1. **OCR Integration Testing**: Validates Tesseract installation and OCR processing
2. **Sample Processing**: Tests actual document processing workflows
3. **Development Utilities**: Helper scripts for debugging and validation
4. **System Validation**: Ensures external dependencies are properly configured

## Running Tests

### Unit Tests (Automated)
```bash
# Run all unit tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_new_architecture.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Integration Scripts (Manual)
```bash
# Test OCR functionality
python scripts/test_ocr.py

# Test specific functionality as needed
python scripts/[script_name].py
```

## Test Quality Standards

### Unit Tests Requirements:
- ✅ **Protocol Testing**: All Protocol implementations tested
- ✅ **Async Support**: Full async/await testing with pytest-asyncio
- ✅ **Mocking**: External dependencies properly mocked
- ✅ **Error Cases**: Both success and failure scenarios tested
- ✅ **Type Safety**: Tests validate type hints and contracts
- ✅ **Backward Compatibility**: Legacy API compatibility verified

### Integration Scripts Requirements:
- ✅ **Real Dependencies**: Tests with actual Tesseract, file system
- ✅ **Visual Feedback**: Rich console output for debugging
- ✅ **Error Reporting**: Clear error messages and troubleshooting
- ✅ **Development Support**: Useful for development workflow

## Test Results Summary

### Current Test Status:
- **36 total tests** passing (as of last run)
- **21 new architecture tests** covering Protocol-based design
- **15 legacy tests** ensuring backward compatibility
- **0 test failures** - all quality checks pass
- **Async testing** fully supported with pytest-asyncio

### Coverage Areas:
1. **Domain Layer**: 100% coverage of protocols and models
2. **Services Layer**: All service implementations tested
3. **Infrastructure Layer**: Document extractors and integrations
4. **CLI Layer**: Framework ready for CLI testing
5. **Error Handling**: Comprehensive Result type testing

## Future Testing Enhancements

### Planned Improvements:
1. **Coverage Reporting**: Add automated coverage reports
2. **Performance Tests**: Add benchmarking for large documents
3. **E2E Tests**: Full pipeline tests with real documents
4. **CI/CD Integration**: Automated testing in GitHub Actions
5. **Property-Based Testing**: Add hypothesis testing for edge cases

### Test Data Management:
1. **Sample Documents**: Create test document fixtures
2. **Mock Services**: Enhanced mocking for external services
3. **Test Isolation**: Ensure tests don't affect each other
4. **Cleanup**: Proper test cleanup and resource management

## Best Practices

### For Unit Tests (`/tests/`):
- Use pytest fixtures for setup/teardown
- Mock external dependencies (Ollama, file system)
- Test both success and error paths
- Use descriptive test names
- Group related tests in classes

### For Integration Scripts (`/scripts/`):
- Provide clear output and progress indicators
- Include troubleshooting information
- Handle missing dependencies gracefully
- Test with real files and services
- Include setup/validation steps

This testing strategy ensures both the reliability of individual components and the proper integration of the entire system.

---

## See Also

### Testing Documentation
- **[END_TO_END_TESTING_GUIDE.md](END_TO_END_TESTING_GUIDE.md)** - Complete testing guide with ground truth format
- **[TESTING_QUICK_REFERENCE.md](TESTING_QUICK_REFERENCE.md)** - Quick testing commands and metrics

### Architecture Documentation
- **[SOLID_ARCHITECTURE.md](SOLID_ARCHITECTURE.md)** - Protocol-based design enables easy testing
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component overview

### Related Guides
- **[README.md](README.md)** - Main project documentation
- **[OCR_IMPLEMENTATION.md](OCR_IMPLEMENTATION.md)** - OCR testing integration

---

**Last Updated:** October 2025