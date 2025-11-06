"""
End-to-End Testing Framework for AI Document Pipeline
Tests accuracy across all architectural boundaries: OCR, Extraction, Classification
"""

import asyncio
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics
import logging

from src.domain import load_configuration, Result
from src.services import (
    TesseractOCRService,
    OllamaClassificationService,
    DocumentProcessingService,
    create_document_processing_service,
    create_ollama_service,
)
from src.infrastructure import create_extraction_service


logger = logging.getLogger(__name__)


@dataclass
class GroundTruth:
    """Ground truth data for testing."""
    file_path: Path
    expected_category: str
    expected_text_keywords: List[str]  # Key terms that should be extracted
    expected_confidence_min: float = 0.7  # Minimum expected confidence
    notes: str = ""


@dataclass
class OCRAccuracyMetrics:
    """OCR accuracy measurements."""
    file_path: Path
    success: bool
    confidence: Optional[float]
    word_count: int
    keyword_matches: int
    keyword_total: int
    character_accuracy: Optional[float] = None
    processing_time: float = 0.0
    error: Optional[str] = None
    
    @property
    def keyword_accuracy(self) -> float:
        """Calculate keyword extraction accuracy."""
        return self.keyword_matches / self.keyword_total if self.keyword_total > 0 else 0.0


@dataclass
class ExtractionAccuracyMetrics:
    """Document extraction accuracy measurements."""
    file_path: Path
    success: bool
    text_length: int
    metadata_complete: bool
    format_supported: bool
    processing_time: float = 0.0
    error: Optional[str] = None


@dataclass
class ClassificationAccuracyMetrics:
    """Classification accuracy measurements."""
    file_path: Path
    success: bool
    predicted_category: Optional[str]
    expected_category: str
    confidence: Optional[float]
    correct_prediction: bool
    processing_time: float = 0.0
    reasoning: Optional[str] = None
    error: Optional[str] = None


@dataclass
class EndToEndMetrics:
    """Complete end-to-end test results."""
    file_path: Path
    overall_success: bool
    ocr_metrics: Optional[OCRAccuracyMetrics]
    extraction_metrics: ExtractionAccuracyMetrics
    classification_metrics: ClassificationAccuracyMetrics
    total_processing_time: float
    timestamp: datetime


class AccuracyTestFramework:
    """Framework for testing accuracy across all architectural boundaries."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the testing framework."""
        self.config = load_configuration(config_path)
        self.ocr_service = TesseractOCRService()
        self.extraction_service = create_extraction_service(self.ocr_service)
        self.classification_service = create_ollama_service(self.config)
        self.document_service = None  # Will be created async
        self.results: List[EndToEndMetrics] = []
    
    async def initialize(self):
        """Initialize async services."""
        self.document_service = await create_document_processing_service(
            extraction_service=self.extraction_service,
            classification_service=self.classification_service,
            config=self.config,
        )
    
    def load_ground_truth(self, ground_truth_file: Path) -> List[GroundTruth]:
        """Load ground truth data from JSON file."""
        try:
            with open(ground_truth_file, 'r') as f:
                data = json.load(f)
            
            ground_truths = []
            for item in data['test_cases']:
                ground_truths.append(GroundTruth(
                    file_path=Path(item['file_path']),
                    expected_category=item['expected_category'],
                    expected_text_keywords=item['expected_keywords'],
                    expected_confidence_min=item.get('expected_confidence_min', 0.7),
                    notes=item.get('notes', '')
                ))
            
            logger.info(f"Loaded {len(ground_truths)} ground truth test cases")
            return ground_truths
            
        except Exception as e:
            logger.error(f"Failed to load ground truth: {e}")
            return []
    
    async def test_ocr_accuracy(self, file_path: Path, expected_keywords: List[str]) -> OCRAccuracyMetrics:
        """Test OCR accuracy for image files."""
        start_time = datetime.now()
        
        try:
            if not self.ocr_service.is_supported(str(file_path)):
                return OCRAccuracyMetrics(
                    file_path=file_path,
                    success=False,
                    confidence=None,
                    word_count=0,
                    keyword_matches=0,
                    keyword_total=len(expected_keywords),
                    processing_time=0.0,
                    error="File format not supported for OCR"
                )
            
            result = await self.ocr_service.extract_text(str(file_path))
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if not result.is_success:
                return OCRAccuracyMetrics(
                    file_path=file_path,
                    success=False,
                    confidence=None,
                    word_count=0,
                    keyword_matches=0,
                    keyword_total=len(expected_keywords),
                    processing_time=processing_time,
                    error=result.error
                )
            
            ocr_data = result.value
            extracted_text = ocr_data.text.lower()
            
            # Count keyword matches
            keyword_matches = sum(1 for keyword in expected_keywords 
                                if keyword.lower() in extracted_text)
            
            return OCRAccuracyMetrics(
                file_path=file_path,
                success=True,
                confidence=ocr_data.confidence,
                word_count=ocr_data.word_count,
                keyword_matches=keyword_matches,
                keyword_total=len(expected_keywords),
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return OCRAccuracyMetrics(
                file_path=file_path,
                success=False,
                confidence=None,
                word_count=0,
                keyword_matches=0,
                keyword_total=len(expected_keywords),
                processing_time=processing_time,
                error=str(e)
            )
    
    async def test_extraction_accuracy(self, file_path: Path) -> ExtractionAccuracyMetrics:
        """Test document extraction accuracy."""
        start_time = datetime.now()
        
        try:
            result = await self.extraction_service.extract_content(file_path)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if not result.is_success:
                return ExtractionAccuracyMetrics(
                    file_path=file_path,
                    success=False,
                    text_length=0,
                    metadata_complete=False,
                    format_supported=False,
                    processing_time=processing_time,
                    error=result.error
                )
            
            content = result.value
            
            # Check metadata completeness
            metadata_complete = all([
                content.metadata.file_name,
                content.metadata.file_type,
                content.metadata.file_size > 0,
            ])
            
            return ExtractionAccuracyMetrics(
                file_path=file_path,
                success=True,
                text_length=len(content.text),
                metadata_complete=metadata_complete,
                format_supported=True,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return ExtractionAccuracyMetrics(
                file_path=file_path,
                success=False,
                text_length=0,
                metadata_complete=False,
                format_supported=False,
                processing_time=processing_time,
                error=str(e)
            )
    
    async def test_classification_accuracy(
        self, 
        file_path: Path, 
        expected_category: str
    ) -> ClassificationAccuracyMetrics:
        """Test classification accuracy."""
        start_time = datetime.now()
        
        try:
            # First extract content
            extraction_result = await self.extraction_service.extract_content(file_path)
            if not extraction_result.is_success:
                processing_time = (datetime.now() - start_time).total_seconds()
                return ClassificationAccuracyMetrics(
                    file_path=file_path,
                    success=False,
                    predicted_category=None,
                    expected_category=expected_category,
                    confidence=None,
                    correct_prediction=False,
                    processing_time=processing_time,
                    error=f"Extraction failed: {extraction_result.error}"
                )
            
            content = extraction_result.value
            categories = self.config.get_categories()
            
            # Classify the document
            classification_result = await self.classification_service.classify_document(
                content, categories
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if not classification_result.is_success:
                return ClassificationAccuracyMetrics(
                    file_path=file_path,
                    success=False,
                    predicted_category=None,
                    expected_category=expected_category,
                    confidence=None,
                    correct_prediction=False,
                    processing_time=processing_time,
                    error=classification_result.error
                )
            
            classification = classification_result.value
            correct_prediction = classification.category.lower() == expected_category.lower()
            
            return ClassificationAccuracyMetrics(
                file_path=file_path,
                success=True,
                predicted_category=classification.category,
                expected_category=expected_category,
                confidence=classification.confidence,
                correct_prediction=correct_prediction,
                processing_time=processing_time,
                reasoning=classification.reasoning
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return ClassificationAccuracyMetrics(
                file_path=file_path,
                success=False,
                predicted_category=None,
                expected_category=expected_category,
                confidence=None,
                correct_prediction=False,
                processing_time=processing_time,
                error=str(e)
            )
    
    async def test_end_to_end(self, ground_truth: GroundTruth) -> EndToEndMetrics:
        """Run complete end-to-end test for a single document."""
        start_time = datetime.now()
        
        logger.info(f"Testing: {ground_truth.file_path}")
        
        # Test each layer
        ocr_metrics = None
        if self.ocr_service.is_supported(str(ground_truth.file_path)):
            ocr_metrics = await self.test_ocr_accuracy(
                ground_truth.file_path, 
                ground_truth.expected_text_keywords
            )
        
        extraction_metrics = await self.test_extraction_accuracy(ground_truth.file_path)
        classification_metrics = await self.test_classification_accuracy(
            ground_truth.file_path, 
            ground_truth.expected_category
        )
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Determine overall success
        overall_success = (
            extraction_metrics.success and 
            classification_metrics.success and
            (ocr_metrics is None or ocr_metrics.success)
        )
        
        return EndToEndMetrics(
            file_path=ground_truth.file_path,
            overall_success=overall_success,
            ocr_metrics=ocr_metrics,
            extraction_metrics=extraction_metrics,
            classification_metrics=classification_metrics,
            total_processing_time=total_time,
            timestamp=datetime.now()
        )
    
    async def run_accuracy_tests(self, ground_truth_file: Path) -> Dict[str, any]:
        """Run complete accuracy test suite."""
        logger.info("Starting end-to-end accuracy testing")
        
        await self.initialize()
        ground_truths = self.load_ground_truth(ground_truth_file)
        
        if not ground_truths:
            raise ValueError("No ground truth data loaded")
        
        # Test each document
        for ground_truth in ground_truths:
            if not ground_truth.file_path.exists():
                logger.warning(f"Test file not found: {ground_truth.file_path}")
                continue
            
            try:
                metrics = await self.test_end_to_end(ground_truth)
                self.results.append(metrics)
            except Exception as e:
                logger.error(f"Test failed for {ground_truth.file_path}: {e}")
        
        # Calculate summary statistics
        return self.calculate_accuracy_summary()
    
    def calculate_accuracy_summary(self) -> Dict[str, any]:
        """Calculate comprehensive accuracy statistics."""
        if not self.results:
            return {"error": "No test results available"}
        
        # Overall metrics
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r.overall_success])
        overall_accuracy = successful_tests / total_tests
        
        # OCR metrics
        ocr_results = [r.ocr_metrics for r in self.results if r.ocr_metrics]
        ocr_accuracy = len([o for o in ocr_results if o.success]) / len(ocr_results) if ocr_results else 0
        avg_ocr_confidence = statistics.mean([o.confidence for o in ocr_results if o.confidence]) if ocr_results else 0
        avg_keyword_accuracy = statistics.mean([o.keyword_accuracy for o in ocr_results]) if ocr_results else 0
        
        # Extraction metrics
        extraction_results = [r.extraction_metrics for r in self.results]
        extraction_accuracy = len([e for e in extraction_results if e.success]) / len(extraction_results)
        avg_text_length = statistics.mean([e.text_length for e in extraction_results if e.success])
        metadata_completeness = len([e for e in extraction_results if e.metadata_complete]) / len(extraction_results)
        
        # Classification metrics
        classification_results = [r.classification_metrics for r in self.results]
        classification_accuracy = len([c for c in classification_results if c.correct_prediction]) / len(classification_results)
        avg_classification_confidence = statistics.mean([c.confidence for c in classification_results if c.confidence]) if classification_results else 0
        
        # Performance metrics
        avg_processing_time = statistics.mean([r.total_processing_time for r in self.results])
        
        # Category breakdown
        category_accuracy = {}
        for result in self.results:
            category = result.classification_metrics.expected_category
            if category not in category_accuracy:
                category_accuracy[category] = {"correct": 0, "total": 0}
            
            category_accuracy[category]["total"] += 1
            if result.classification_metrics.correct_prediction:
                category_accuracy[category]["correct"] += 1
        
        # Calculate accuracy per category
        for category in category_accuracy:
            stats = category_accuracy[category]
            stats["accuracy"] = stats["correct"] / stats["total"]
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "overall_accuracy": overall_accuracy,
                "average_processing_time": avg_processing_time,
            },
            "ocr_metrics": {
                "ocr_accuracy": ocr_accuracy,
                "average_confidence": avg_ocr_confidence,
                "keyword_accuracy": avg_keyword_accuracy,
                "tests_with_ocr": len(ocr_results),
            },
            "extraction_metrics": {
                "extraction_accuracy": extraction_accuracy,
                "average_text_length": avg_text_length,
                "metadata_completeness": metadata_completeness,
            },
            "classification_metrics": {
                "classification_accuracy": classification_accuracy,
                "average_confidence": avg_classification_confidence,
                "category_breakdown": category_accuracy,
            },
            "timestamp": datetime.now().isoformat(),
        }
    
    def export_detailed_results(self, output_path: Path):
        """Export detailed test results to CSV."""
        if not self.results:
            logger.warning("No results to export")
            return
        
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = [
                'file_path', 'overall_success', 'total_processing_time',
                'extraction_success', 'extraction_time', 'text_length', 'metadata_complete',
                'classification_success', 'predicted_category', 'expected_category', 
                'correct_prediction', 'classification_confidence', 'classification_time',
                'ocr_success', 'ocr_confidence', 'keyword_accuracy', 'ocr_time',
                'timestamp'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                row = {
                    'file_path': str(result.file_path),
                    'overall_success': result.overall_success,
                    'total_processing_time': result.total_processing_time,
                    'extraction_success': result.extraction_metrics.success,
                    'extraction_time': result.extraction_metrics.processing_time,
                    'text_length': result.extraction_metrics.text_length,
                    'metadata_complete': result.extraction_metrics.metadata_complete,
                    'classification_success': result.classification_metrics.success,
                    'predicted_category': result.classification_metrics.predicted_category,
                    'expected_category': result.classification_metrics.expected_category,
                    'correct_prediction': result.classification_metrics.correct_prediction,
                    'classification_confidence': result.classification_metrics.confidence,
                    'classification_time': result.classification_metrics.processing_time,
                    'timestamp': result.timestamp.isoformat(),
                }
                
                if result.ocr_metrics:
                    row.update({
                        'ocr_success': result.ocr_metrics.success,
                        'ocr_confidence': result.ocr_metrics.confidence,
                        'keyword_accuracy': result.ocr_metrics.keyword_accuracy,
                        'ocr_time': result.ocr_metrics.processing_time,
                    })
                
                writer.writerow(row)
        
        logger.info(f"Detailed results exported to: {output_path}")
    
    def export_summary_report(self, summary_data: Dict, output_path: Path):
        """Export summary report to JSON."""
        with open(output_path, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        logger.info(f"Summary report exported to: {output_path}")


async def main():
    """Main function to run accuracy tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run end-to-end accuracy tests")
    parser.add_argument("ground_truth", type=Path, help="Path to ground truth JSON file")
    parser.add_argument("--output-dir", type=Path, default=Path("test_results"), 
                       help="Output directory for results")
    parser.add_argument("--config", type=Path, help="Configuration file path")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create output directory
    args.output_dir.mkdir(exist_ok=True)
    
    # Run tests
    framework = AccuracyTestFramework(args.config)
    
    try:
        summary = await framework.run_accuracy_tests(args.ground_truth)
        
        # Export results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        framework.export_detailed_results(args.output_dir / f"detailed_results_{timestamp}.csv")
        framework.export_summary_report(summary, args.output_dir / f"summary_report_{timestamp}.json")
        
        # Print summary
        print("\n" + "="*60)
        print("ACCURACY TEST RESULTS SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['summary']['total_tests']}")
        print(f"Overall Accuracy: {summary['summary']['overall_accuracy']:.2%}")
        print(f"Average Processing Time: {summary['summary']['average_processing_time']:.2f}s")
        print()
        print(f"OCR Accuracy: {summary['ocr_metrics']['ocr_accuracy']:.2%}")
        print(f"Extraction Accuracy: {summary['extraction_metrics']['extraction_accuracy']:.2%}")
        print(f"Classification Accuracy: {summary['classification_metrics']['classification_accuracy']:.2%}")
        print()
        print("Category Breakdown:")
        for category, stats in summary['classification_metrics']['category_breakdown'].items():
            print(f"  {category}: {stats['accuracy']:.2%} ({stats['correct']}/{stats['total']})")
        
        return summary
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())