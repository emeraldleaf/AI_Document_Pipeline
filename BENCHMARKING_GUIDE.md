# Benchmarking Guide

## How to Measure Extraction Quality

This guide explains how to objectively measure whether changes improve your metadata extraction.

**Current Best Performance**: 95.0% F1 Score, 100% Recall, 12.3s/document (llama3.2:3b + improved schema)

## Quick Start

```bash
# 1. Establish baseline (current system)
python benchmark_extraction.py --baseline --name current_system

# 2. Test with improvements (e.g., Docling)
python benchmark_extraction.py --compare --docling \
  --baseline-file benchmarks/benchmark_results_current_system_*.json

# 3. Review comparison report
```

## Metrics Explained

### **Precision**
**What**: Of the fields extracted, how many are correct?
**Formula**: `correct_fields / total_extracted`
**Good**: >0.85 (85%+)
**Current**: 90.6%

### **Recall** ⭐ **(Critical for Completeness)**
**What**: Of the expected fields, how many were found?
**Formula**: `fields_found / total_expected`
**Good**: >0.95 (95%+)
**Current**: 100% 🎯

### **F1 Score** ⭐ **(Most Important)**
**What**: Balanced measure of precision and recall
**Formula**: `2 * (precision * recall) / (precision + recall)`
**Good**: >0.90 (90%+)
**Current**: 95.0% 🏆

### **Confidence**
**What**: Model's self-assessed confidence
**Range**: 0.0 - 1.0
**Note**: May not correlate with actual accuracy

### **Processing Time**
**What**: Seconds per document
**Good**: <15s for simple docs, <30s for complex
**Current**: 12.3s

## Understanding Results

### Example Output

```
BENCHMARK COMPARISON
================================================================================
Baseline: corrected_baseline (2025-11-07T17:56:50)
Comparison: improved_schema (2025-11-07T18:10:22)

SUMMARY METRICS
--------------------------------------------------------------------------------
avg_precision      : 0.873 → 0.906 📈 (+0.033, +3.8%)
avg_recall         : 0.930 → 1.000 📈 (+0.070, +7.5%)
avg_f1_score       : 0.900 → 0.950 📈 (+0.050, +5.6%)
avg_confidence     : 0.940 → 0.955 📈 (+0.015, +1.6%)
avg_processing_time: 11.60s → 12.30s 🐌 (+0.70s, +6.0%)

VERDICT
--------------------------------------------------------------------------------
✅ IMPROVED: Better accuracy with minimal speed impact
```

### Real Results from Our Testing

**Schema Improvements (SUCCESS)**:
- F1 Score: 90.0% → 95.0% 📈 (+5.6%)
- Recall: 93.0% → 100% 📈 (+7.5%)
- Precision: 87.3% → 90.6% 📈 (+3.8%)
- Speed: 11.6s → 12.3s 🐌 (+6%)

**Phi-4 Model Test (FAILURE)**:
- F1 Score: 90.0% → 86.3% 📉 (-4.1%)
- Speed: 11.6s → 51.6s 🐌 (+4.4x slower)
- Verdict: ❌ REJECTED

### What This Means

- **📈 Better**: Metric improved
- **📉 Worse**: Metric declined
- **➡️  Same**: No change
- **⚡ Faster**: Processing time decreased
- **🐌 Slower**: Processing time increased

### Decision Matrix

| F1 Score | Speed Change | Example | Verdict |
|----------|--------------|---------|---------|
| ⬆️ +5%+ | ⬆️ <10% slower | Schema improvements | 🎉 **ADOPT** - Clear win! |
| ⬆️ +3-5% | ⬆️ <25% slower | Docling on PDFs | ✅ **CONSIDER** - Worth it |
| ⬇️ Worse | ⬆️ Any faster | Phi-4 model | ❌ **REJECT** - Don't do this |
| ⬇️ Worse | ⬇️ Slower | Most bad changes | ❌ **REVERT** - Revert immediately |

**Real Examples from Our Testing**:
- **Schema improvements**: +5.6% F1, +6% slower → ✅ **ADOPTED**
- **Phi-4 model**: -4.1% F1, +344% slower → ❌ **REJECTED**

## Adding Test Documents

Edit `benchmark_extraction.py` and add to `load_ground_truth()`:

```python
ground_truth = {
    "your_document.pdf": {
        "invoice_number": "INV-123",
        "total_amount": 1500.00,
        # ... expected fields
    },
}
```

Place the document in `test_documents/` directory.

## Testing Different Improvements

### Test Docling Parser

```bash
python benchmark_extraction.py --compare --docling \
  --baseline-file benchmarks/baseline_*.json
```

### Test Different Model

```bash
python benchmark_extraction.py --compare --model phi4 \
  --baseline-file benchmarks/baseline_*.json
```

### Test Schema Changes

```bash
# Edit config/metadata_schemas.yaml with improvements
# Then test:
python benchmark_extraction.py --compare --name improved_schema \
  --baseline-file benchmarks/baseline_*.json
```

### Test Both Docling + Different Model

```bash
python benchmark_extraction.py --compare --docling --model phi4 \
  --baseline-file benchmarks/baseline_*.json
```

## Continuous Benchmarking

### Before Making Changes

```bash
# Save current performance
python benchmark_extraction.py --baseline --name before_changes
```

### After Making Changes

```bash
# Test and compare
python benchmark_extraction.py --compare --name after_changes \
  --baseline-file benchmarks/benchmark_results_before_changes_*.json
```

### Track Over Time

Keep all benchmark results in `benchmarks/` directory to see trends.

## Interpreting Trade-offs

### Accuracy vs Speed

**Our Results**:
- **+5.6% F1, +6% slower**: ✅ Worth it (schema improvements)
- **-4.1% F1, +344% slower**: ❌ Not worth it (Phi-4 model)

**General Guidelines**:
- **5%+ better F1, <10% slower**: Usually worth it
- **3-5% better F1, <25% slower**: Consider based on use case
- **<3% better F1, >25% slower**: Usually not worth it
- **Any F1 decrease**: Revert immediately

### Cost Considerations

- Local models (Ollama): Speed is main cost (time)
- API models: $ cost per document
- OCR processing: Additional time cost
- Schema improvements: Minimal cost, high benefit

## Best Practices

1. **Always establish baseline first** - Don't assume improvements work
2. **Test on diverse documents** - Different formats, layouts, complexity
3. **Focus on F1 score** - Best overall metric for balanced performance
4. **Prioritize recall for critical fields** - Better to find everything than miss important data
5. **Schema improvements are low-hanging fruit** - Often give big gains with little effort
6. **Bigger models aren't always better** - Test empirically, don't assume
7. **Consider your use case**:
   - Batch processing overnight? Speed less important
   - Real-time API? Speed critical
   - High-stakes (legal/finance)? Accuracy critical

### Lessons from Our Testing

**✅ What Worked**:
- Schema refinement: +5.6% F1 with clear field descriptions
- Systematic benchmarking: Caught wrong ground truth early
- llama3.2:3b model: Good balance of speed vs accuracy

**❌ What Didn't Work**:
- Phi-4 model: Worse accuracy despite 4x more parameters
- Assuming bigger = better: Always test empirically

## Troubleshooting

### Low Precision (Many Incorrect Extractions)

- **Symptoms**: High recall, low precision, F1 score suffering
- **Causes**: Model hallucinating fields, unclear schema guidance
- **Solutions**:
  - ✅ Improve field descriptions in `config/metadata_schemas.yaml`
  - Try more specific examples in schema
  - Consider smaller model (less likely to hallucinate)

### Low Recall (Missing Fields)

- **Symptoms**: High precision, low recall, missing expected fields
- **Causes**: Model not finding fields, poor document parsing
- **Solutions**:
  - ✅ Add specific guidance for missing fields in schema
  - Try Docling for better document structure parsing
  - Check document quality (OCR if needed)

### Slow Processing

- **Symptoms**: Processing time >15s per document
- **Causes**: Large model, complex documents, inefficient parsing
- **Solutions**:
  - Try smaller model (llama3.2:3b instead of larger models)
  - Reduce max_text_length in config
  - Disable unnecessary OCR

### Inconsistent Results

- **Symptoms**: Same document gives different results
- **Causes**: Model stochasticity, document variability
- **Solutions**:
  - Run multiple times and average results
  - Check document preprocessing consistency
  - May need document-type-specific tuning

### Wrong Ground Truth (Silent Failure)

- **Symptoms**: Benchmark shows "improvements" that aren't real
- **Causes**: Incorrect expected values in test data
- **Solutions**:
  - ✅ Double-check ground truth manually
  - Start with small test set you can verify
  - Use real production data for ground truth when possible

## Summary

**Current Best Performance**: 95.0% F1 Score, 100% Recall 🎯

**Golden Rule**: Improve F1 score without significant speed regression.

**Proven Strategies**:
- ✅ Schema refinement (biggest impact, lowest effort)
- ✅ Systematic benchmarking (catch issues early)
- ❌ Bigger models (don't assume they help)

**Target Metrics** (Achieved):
- F1 Score: >0.90 (90%) ✅ **ACHIEVED: 95.0%**
- Recall: >0.95 (95%) ✅ **ACHIEVED: 100%**
- Precision: >0.85 (85%) ✅ **ACHIEVED: 90.6%**
- Processing Time: <15s per document ✅ **ACHIEVED: 12.3s**

**Next Goals**:
- Test on 20+ diverse documents
- Test PDF extraction with Docling
- Target 98% F1 score

Use this benchmarking system to make data-driven decisions about improvements!

**Quick Reference**:
```bash
# Establish baseline
python benchmark_extraction.py --baseline --name my_test

# Test improvement
python benchmark_extraction.py --compare --name improved_version \
  --baseline-file benchmarks/benchmark_results_my_test_*.json
```
