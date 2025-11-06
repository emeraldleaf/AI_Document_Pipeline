#!/usr/bin/env python3
"""
Example script demonstrating end-to-end accuracy and performance testing
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

from tests.test_accuracy_framework import AccuracyTestFramework, GroundTruth
from tests.test_performance_benchmark import PerformanceBenchmark


async def run_quick_accuracy_test():
    """Run a quick accuracy test on sample documents."""
    print("="*60)
    print("QUICK ACCURACY TEST")
    print("="*60)
    
    framework = AccuracyTestFramework()
    await framework.initialize()
    
    # Create sample ground truth data
    sample_ground_truths = [
        GroundTruth(
            file_path=Path("documents/input"),  # Will check first available file
            expected_category="document",
            expected_text_keywords=["text", "document", "content"],
            expected_confidence_min=0.5
        )
    ]
    
    # Find first available test file
    input_dir = Path("documents/input")
    if input_dir.exists():
        test_files = list(input_dir.glob("*"))
        test_files = [f for f in test_files if f.is_file() and f.suffix.lower() in ['.pdf', '.txt', '.jpg', '.png', '.tiff']]
        
        if test_files:
            sample_ground_truths[0].file_path = test_files[0]
            print(f"Testing file: {test_files[0]}")
            
            # Run end-to-end test
            result = await framework.test_end_to_end(sample_ground_truths[0])
            
            print(f"Overall Success: {result.overall_success}")
            print(f"Total Processing Time: {result.total_processing_time:.2f}s")
            
            if result.extraction_metrics:
                print(f"Extraction Success: {result.extraction_metrics.success}")
                print(f"Text Length: {result.extraction_metrics.text_length}")
            
            if result.classification_metrics:
                print(f"Classification Success: {result.classification_metrics.success}")
                print(f"Predicted Category: {result.classification_metrics.predicted_category}")
                print(f"Confidence: {result.classification_metrics.confidence}")
            
            if result.ocr_metrics:
                print(f"OCR Success: {result.ocr_metrics.success}")
                print(f"OCR Confidence: {result.ocr_metrics.confidence}")
                print(f"Keyword Accuracy: {result.ocr_metrics.keyword_accuracy:.2%}")
            
            return result
        else:
            print("No test files found in documents/input/")
    else:
        print("documents/input/ directory not found")
    
    return None


async def run_quick_performance_test():
    """Run a quick performance test."""
    print("\n" + "="*60)
    print("QUICK PERFORMANCE TEST")
    print("="*60)
    
    benchmark = PerformanceBenchmark()
    
    # Find test files
    input_dir = Path("documents/input")
    if not input_dir.exists():
        print("documents/input/ directory not found")
        return None
    
    test_files = list(input_dir.glob("*"))
    test_files = [f for f in test_files if f.is_file() and f.suffix.lower() in ['.pdf', '.txt', '.jpg', '.png', '.tiff']]
    
    if not test_files:
        print("No test files found")
        return None
    
    # Limit to first 3 files for quick test
    test_files = test_files[:3]
    print(f"Testing {len(test_files)} files...")
    
    # Run performance benchmark
    results = await benchmark.run_benchmark_suite(test_files, ["end_to_end"])
    
    if "end_to_end" in results:
        summary = results["end_to_end"]
        print(f"Files Processed: {summary.total_files}")
        print(f"Success Rate: {summary.successful_operations}/{summary.total_files}")
        print(f"Average Processing Time: {summary.average_processing_time:.2f}s")
        print(f"Operations per Second: {summary.operations_per_second:.2f}")
        print(f"Peak Memory Usage: {summary.peak_memory_mb:.1f} MB")
    
    return results


async def create_sample_ground_truth():
    """Create a sample ground truth file for testing."""
    print("\n" + "="*60)
    print("CREATING SAMPLE GROUND TRUTH")
    print("="*60)
    
    # Find available test files
    input_dir = Path("documents/input")
    if not input_dir.exists():
        print("documents/input/ directory not found - creating sample directories")
        input_dir.mkdir(parents=True, exist_ok=True)
        return
    
    test_files = list(input_dir.glob("*"))
    test_files = [f for f in test_files if f.is_file()]
    
    if not test_files:
        print("No files found - add some documents to documents/input/ first")
        return
    
    # Create ground truth based on available files
    ground_truth_data = {
        "description": "Sample ground truth data for testing",
        "version": "1.0",
        "test_cases": [],
        "categories": ["document", "invoice", "contract", "resume", "receipt", "report", "other"],
        "test_metadata": {
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "Auto-generated sample test suite",
            "total_test_cases": 0
        }
    }
    
    # Add test cases for available files
    for file_path in test_files[:5]:  # Limit to first 5 files
        # Guess category based on filename
        filename_lower = file_path.name.lower()
        if "invoice" in filename_lower:
            category = "invoice"
            keywords = ["invoice", "amount", "total", "bill"]
        elif "contract" in filename_lower:
            category = "contract"
            keywords = ["agreement", "contract", "terms", "party"]
        elif "resume" in filename_lower or "cv" in filename_lower:
            category = "resume"
            keywords = ["experience", "education", "skills", "employment"]
        elif "receipt" in filename_lower:
            category = "receipt"
            keywords = ["receipt", "total", "tax", "store"]
        elif "report" in filename_lower:
            category = "report"
            keywords = ["report", "analysis", "findings", "conclusion"]
        else:
            category = "document"
            keywords = ["text", "document", "content", "information"]
        
        test_case = {
            "file_path": str(file_path),
            "expected_category": category,
            "expected_keywords": keywords,
            "expected_confidence_min": 0.7,
            "notes": f"Auto-generated test case for {file_path.name}"
        }
        
        ground_truth_data["test_cases"].append(test_case)
    
    ground_truth_data["test_metadata"]["total_test_cases"] = len(ground_truth_data["test_cases"])
    
    # Save ground truth file
    output_path = Path("tests/sample_ground_truth.json")
    with open(output_path, 'w') as f:
        json.dump(ground_truth_data, f, indent=2)
    
    print(f"Created sample ground truth file: {output_path}")
    print(f"Test cases: {len(ground_truth_data['test_cases'])}")
    
    return output_path


async def main():
    """Main function to run example tests."""
    print("AI Document Pipeline - End-to-End Testing Example")
    print("This script demonstrates accuracy and performance testing capabilities.")
    
    try:
        # Create sample ground truth if needed
        await create_sample_ground_truth()
        
        # Run quick tests
        accuracy_result = await run_quick_accuracy_test()
        performance_result = await run_quick_performance_test()
        
        print("\n" + "="*60)
        print("TESTING COMPLETE")
        print("="*60)
        print("Next steps:")
        print("1. Review the results above")
        print("2. Add more test documents to documents/input/")
        print("3. Update tests/sample_ground_truth.json with accurate expected results")
        print("4. Run comprehensive tests:")
        print("   python tests/test_accuracy_framework.py tests/sample_ground_truth.json")
        print("   python tests/test_performance_benchmark.py documents/input/")
        print("5. See END_TO_END_TESTING_GUIDE.md for detailed instructions")
        
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you have test documents in documents/input/")
        print("2. Check that all dependencies are installed")
        print("3. Verify configuration settings")
        print("4. Review END_TO_END_TESTING_GUIDE.md for setup instructions")
        return False


if __name__ == "__main__":
    asyncio.run(main())