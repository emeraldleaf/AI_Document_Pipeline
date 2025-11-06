# End-to-End Testing Quick Reference

## 🚀 Quick Start Commands

```bash
# Run example test
python examples/test_example.py

# Test accuracy with ground truth
python tests/test_accuracy_framework.py tests/ground_truth_template.json

# Benchmark performance
python tests/test_performance_benchmark.py documents/input/ --operations end_to_end

# Install additional dependencies
pip install psutil
```

## 📊 Key Metrics Measured

### OCR Accuracy
- **Keyword Detection**: % of expected terms found
- **Confidence Score**: OCR engine confidence (0-1)
- **Success Rate**: % files processed without errors

### Extraction Accuracy  
- **Parse Success**: % documents successfully extracted
- **Metadata Completeness**: File info availability
- **Text Quality**: Content length and coherence

### Classification Accuracy
- **Overall Accuracy**: % correctly classified documents
- **Per-Category**: Performance by document type
- **Confidence Distribution**: Reliability of predictions

### Performance Metrics
- **Throughput**: Files/second, MB/second
- **Latency**: Average/median processing time
- **Resources**: Peak memory, CPU usage

## 🎯 Accuracy Thresholds

| Metric | Good | Excellent |
|--------|------|-----------|
| Overall Pipeline | ≥85% | ≥95% |
| OCR (clear text) | ≥95% | ≥99% |
| OCR (scanned) | ≥80% | ≥90% |
| Classification | ≥90% | ≥95% |
| Extraction | ≥98% | ≥99.5% |

## ⚡ Performance Benchmarks

| Operation | Typical Range | Good Performance |
|-----------|---------------|------------------|
| PDF Extraction | 5-50 MB/s | >20 MB/s |
| OCR Processing | 0.5-5 MB/s | >2 MB/s |
| Classification | 10-100 docs/s | >50 docs/s |
| End-to-End | 5-30 docs/s | >15 docs/s |

## 🔧 Architecture Boundaries Tested

```
┌─────────────────┐
│   Input File    │
└─────────────────┘
         │
         ▼
┌─────────────────┐ ◄─── OCR Layer Testing
│   OCR Service   │      • Text extraction accuracy
└─────────────────┘      • Confidence scores
         │               • Processing speed
         ▼
┌─────────────────┐ ◄─── Extraction Layer Testing  
│ Document        │      • Content parsing
│ Extraction      │      • Metadata extraction
└─────────────────┘      • Format support
         │
         ▼
┌─────────────────┐ ◄─── Classification Layer Testing
│ AI              │      • Category prediction
│ Classification  │      • Confidence levels
└─────────────────┘      • Reasoning quality
         │
         ▼
┌─────────────────┐ ◄─── End-to-End Testing
│ Final Result    │      • Overall accuracy
└─────────────────┘      • Complete pipeline performance
```

## 📁 File Structure

```
tests/
├── test_accuracy_framework.py      # Accuracy testing framework
├── test_performance_benchmark.py   # Performance benchmarking  
├── ground_truth_template.json      # Sample ground truth data
└── sample_ground_truth.json        # Auto-generated test data

examples/
└── test_example.py                 # Quick start example

results/
├── accuracy/                       # Accuracy test results
│   ├── detailed_results_*.csv
│   └── summary_report_*.json
└── performance/                    # Performance test results
    └── benchmark_results_*.json
```

## 🛠️ Common Commands

```bash
# Test single document accuracy
python -c "
import asyncio
from tests.test_accuracy_framework import AccuracyTestFramework
from pathlib import Path

async def test():
    framework = AccuracyTestFramework()
    await framework.initialize()
    result = await framework.test_classification_accuracy(
        Path('document.pdf'), 'invoice'
    )
    print(f'Accuracy: {result.correct_prediction}')

asyncio.run(test())
"

# Monitor resource usage
python -c "
import psutil, time
process = psutil.Process()
for i in range(5):
    print(f'Memory: {process.memory_info().rss/1024/1024:.1f}MB')
    time.sleep(1)
"

# Quick performance check
time python examples/test_example.py
```

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: psutil` | `pip install psutil` |
| No test files found | Add documents to `documents/input/` |
| OCR accuracy low | Check image quality, try different formats |
| Classification errors | Review categories, check model responses |
| Memory usage high | Reduce batch size, check for leaks |
| Slow performance | Monitor CPU/disk, optimize async operations |

## 📈 Monitoring & CI/CD

```yaml
# GitHub Actions example
name: Quality Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Test Accuracy
        run: python tests/test_accuracy_framework.py tests/ci_ground_truth.json
      - name: Benchmark Performance  
        run: python tests/test_performance_benchmark.py documents/regression/
```

## 📚 Next Steps

1. **Add Test Data**: Place documents in `documents/input/`
2. **Create Ground Truth**: Update `tests/ground_truth_template.json`
3. **Run Tests**: Use commands above to validate accuracy
4. **Monitor Performance**: Set up regular benchmarking
5. **Automate**: Add to CI/CD pipeline for continuous validation

---

## See Also

### Testing Documentation
- **[END_TO_END_TESTING_GUIDE.md](END_TO_END_TESTING_GUIDE.md)** - Complete testing guide with detailed instructions
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing strategy and organization

### Architecture Documentation
- **[SOLID_ARCHITECTURE.md](SOLID_ARCHITECTURE.md)** - Protocol-based design enables easy testing
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and component overview

### Related Guides
- **[README.md](README.md)** - Main project documentation
- **[OCR_IMPLEMENTATION.md](OCR_IMPLEMENTATION.md)** - OCR implementation details

---

**Last Updated:** October 2025