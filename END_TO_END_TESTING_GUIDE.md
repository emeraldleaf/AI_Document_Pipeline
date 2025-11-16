# End-to-End Testing Guide for AI Document Pipeline

This guide provides comprehensive instructions for testing accuracy and performance across all architectural boundaries of the AI Document Pipeline.

## Overview

The testing framework evaluates three main architectural boundaries:
1. **OCR Layer** - Text extraction from images and scanned documents
2. **Extraction Layer** - Document content and metadata extraction
3. **Classification Layer** - Document categorization using AI

## Quick Start

### 1. Prepare Ground Truth Data

Create a ground truth file with expected results for your test documents:

```bash
# Copy the template
cp tests/ground_truth_template.json tests/my_ground_truth.json

# Edit with your test files and expected results
```

### 2. Run Accuracy Tests

```bash
# Run complete accuracy test suite
python tests/test_accuracy_framework.py tests/my_ground_truth.json --output-dir results/accuracy

# View summary results
cat results/accuracy/summary_report_*.json
```

### 3. Run Performance Benchmarks

```bash
# Run performance benchmarks on test files
python tests/test_performance_benchmark.py documents/input/ --output-dir results/performance

# Benchmark specific operations
python tests/test_performance_benchmark.py documents/input/ --operations ocr extraction classification
```

## Ground Truth Data Format

The ground truth file defines expected results for testing:

```json
{
  "test_cases": [
    {
      "file_path": "documents/input/sample_invoice.pdf",
      "expected_category": "invoice",
      "expected_keywords": ["invoice", "amount", "total"],
      "expected_confidence_min": 0.8,
      "notes": "Standard invoice format"
    }
  ]
}
```

### Required Fields:
- `file_path`: Path to test document
- `expected_category`: Expected classification result
- `expected_keywords`: Terms that should be extracted by OCR
- `expected_confidence_min`: Minimum acceptable confidence score

## Accuracy Testing

### OCR Accuracy Metrics

**Measures:**
- Text extraction success rate
- Keyword detection accuracy
- OCR confidence scores
- Processing time

**Key Indicators:**
- **Keyword Accuracy**: Percentage of expected keywords found
- **Confidence Score**: OCR engine's confidence in results
- **Success Rate**: Percentage of files processed without errors

```bash
# Test OCR accuracy on image files
python -c "
import asyncio
from tests.test_accuracy_framework import AccuracyTestFramework
from pathlib import Path

async def test_ocr():
    framework = AccuracyTestFramework()
    result = await framework.test_ocr_accuracy(
        Path('documents/input/scanned_document.jpg'),
        ['invoice', 'total', 'amount']
    )
    print(f'OCR Accuracy: {result.keyword_accuracy:.2%}')
    print(f'Confidence: {result.confidence:.2f}')

asyncio.run(test_ocr())
"
```

### Extraction Accuracy Metrics

**Measures:**
- Document parsing success rate
- Text length and completeness
- Metadata extraction completeness
- Format support coverage

**Key Indicators:**
- **Extraction Success**: Percentage of documents successfully parsed
- **Metadata Completeness**: Availability of file metadata
- **Text Quality**: Length and coherence of extracted text

### Classification Accuracy Metrics

**Measures:**
- Category prediction accuracy
- Confidence scores
- Per-category performance
- Reasoning quality

**Key Indicators:**
- **Overall Accuracy**: Percentage of correctly classified documents
- **Per-Category Accuracy**: Performance breakdown by document type
- **Confidence Distribution**: Reliability of confidence scores

```bash
# Test classification accuracy
python -c "
import asyncio
from tests.test_accuracy_framework import AccuracyTestFramework
from pathlib import Path

async def test_classification():
    framework = AccuracyTestFramework()
    await framework.initialize()
    result = await framework.test_classification_accuracy(
        Path('documents/input/sample_invoice.pdf'),
        'invoice'
    )
    print(f'Prediction: {result.predicted_category}')
    print(f'Correct: {result.correct_prediction}')
    print(f'Confidence: {result.confidence:.2f}')

asyncio.run(test_classification())
"
```

## Performance Testing

### Throughput Metrics

**Measures:**
- Files processed per second
- Data throughput (MB/s)
- Concurrent processing capacity

### Latency Metrics

**Measures:**
- Average processing time per file
- 95th percentile response times
- Time breakdown by operation

### Resource Usage

**Measures:**
- Peak memory consumption
- CPU utilization
- Disk I/O patterns

```bash
# Monitor resource usage during processing
python tests/test_performance_benchmark.py documents/input/ \
  --operations end_to_end \
  --output-dir results/performance/$(date +%Y%m%d)
```

## Test Data Preparation

### 1. Create Diverse Test Set

Include documents that represent:
- Different file formats (PDF, images, text)
- Various quality levels (high-res, scanned, poor quality)
- Multiple categories and domains
- Edge cases and challenging content

### 2. Establish Baselines

```bash
# Create baseline measurements
mkdir -p baselines/$(date +%Y%m%d)

# Run accuracy tests
python tests/test_accuracy_framework.py tests/baseline_ground_truth.json \
  --output-dir baselines/$(date +%Y%m%d)/accuracy

# Run performance tests  
python tests/test_performance_benchmark.py documents/baseline/ \
  --output-dir baselines/$(date +%Y%m%d)/performance
```

### 3. Version Control Test Data

```bash
# Track test data versions
git add tests/ground_truth_*.json
git add documents/test_data/
git commit -m "Add test data for accuracy validation"
```

## Interpreting Results

### Accuracy Thresholds

**Recommended Minimums:**
- Overall Pipeline Accuracy: ≥ 85%
- OCR Accuracy (clear text): ≥ 95%
- OCR Accuracy (scanned): ≥ 80% 
- Classification Accuracy: ≥ 90%
- Extraction Success Rate: ≥ 98%

### Performance Benchmarks

**Typical Performance:**
- PDF Extraction: 5-50 MB/s
- OCR Processing: 0.5-5 MB/s
- Classification: 10-100 docs/s

### Red Flags

Watch for:
- Accuracy drops below 80% overall
- Processing times > 30s per document
- Memory usage > 2GB per process
- Error rates > 5%

## Continuous Testing

### 1. Automated Testing

Add to CI/CD pipeline:

```yaml
# .github/workflows/accuracy-tests.yml
name: Accuracy Tests
on: [push, pull_request]
jobs:
  accuracy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run accuracy tests
        run: python tests/test_accuracy_framework.py tests/ci_ground_truth.json
```

### 2. Performance Monitoring

```bash
# Weekly performance regression tests
crontab -e
# Add: 0 2 * * 1 cd /path/to/project && python tests/test_performance_benchmark.py documents/regression/ --output-dir results/weekly/$(date +%Y%m%d)
```

### 3. Results Tracking

```bash
# Compare results over time
python -c "
import json
from pathlib import Path

# Load recent results
results_dir = Path('results/accuracy')
recent_files = sorted(results_dir.glob('summary_report_*.json'))[-5:]

for file in recent_files:
    with open(file) as f:
        data = json.load(f)
    
    print(f'{file.stem}: {data[\"summary\"][\"overall_accuracy\"]:.2%}')
"
```

## Troubleshooting

### Common Issues

**Low OCR Accuracy:**
- Check image quality and resolution
- Verify language settings
- Consider image preprocessing
- Test with different OCR engines

**Classification Errors:**
- Review training data quality
- Adjust category definitions
- Check for ambiguous documents
- Validate model responses

**Performance Issues:**
- Monitor resource usage
- Check for memory leaks
- Optimize batch sizes
- Consider async processing

### Debug Commands

```bash
# Detailed error analysis
python tests/test_accuracy_framework.py tests/debug_ground_truth.json --output-dir debug_results

# Single file debugging
python -c "
import asyncio
from src.services import create_document_processing_service
from pathlib import Path

async def debug_file():
    service = await create_document_processing_service()
    result = await service.process_document(Path('problem_file.pdf'), ['invoice', 'contract'])
    print(f'Result: {result}')

asyncio.run(debug_file())
"

# Resource monitoring
python -c "
import psutil
import time

process = psutil.Process()
for i in range(10):
    print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB, CPU: {process.cpu_percent():.1f}%')
    time.sleep(1)
"
```

## Custom Metrics

### Add Custom Accuracy Metrics

Extend the `AccuracyTestFramework` class:

```python
class CustomAccuracyFramework(AccuracyTestFramework):
    async def test_custom_metric(self, file_path: Path) -> float:
        """Add your custom accuracy measurement."""
        # Your custom logic here
        return accuracy_score
```

### Add Custom Performance Metrics

Extend the `PerformanceBenchmark` class:

```python
class CustomPerformanceBenchmark(PerformanceBenchmark):
    async def benchmark_custom_operation(self, file_path: Path) -> PerformanceMetrics:
        """Add your custom performance measurement."""
        # Your custom benchmarking logic here
        return metrics
```

## Best Practices

1. **Regular Testing**: Run accuracy tests weekly, performance tests daily
2. **Version Control**: Track all test data and results in version control
3. **Baseline Comparison**: Always compare against established baselines
4. **Document Changes**: Log any configuration or model changes
5. **Monitor Trends**: Watch for gradual degradation over time
6. **Test in Production**: Validate results with real-world documents

## Integration with Development Workflow

```bash
# Pre-commit accuracy check
git add . && python tests/test_accuracy_framework.py tests/quick_ground_truth.json && git commit

# Performance regression test
python tests/test_performance_benchmark.py documents/regression/ --operations end_to_end

# Release validation
python tests/test_accuracy_framework.py tests/comprehensive_ground_truth.json --output-dir release_validation/
```

This comprehensive testing framework ensures you can measure and maintain high accuracy across all architectural boundaries while monitoring performance and identifying areas for improvement.

---

## See Also

### Testing Documentation
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing strategy and organization
### Architecture Documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component overview
- **[README.md](README.md)** - Main project documentation

---

**Last Updated:** November 2025