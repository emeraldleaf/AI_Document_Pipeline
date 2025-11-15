#!/usr/bin/env python3
"""
Benchmark Metadata Extraction Quality
=======================================

Measures extraction quality metrics to compare different approaches.

Metrics tracked:
- Field extraction rate (% of expected fields found)
- Accuracy (correctness of extracted values)
- Confidence scores
- Processing time
- Cost (if using paid APIs)

Usage:
    python benchmark_extraction.py --baseline  # Establish baseline
    python benchmark_extraction.py --compare   # Compare to baseline
"""

import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm_metadata_extractor import ConfigurableMetadataExtractor

try:
    from docling_metadata_extractor import DoclingMetadataExtractor
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False


class ExtractionBenchmark:
    """Benchmark metadata extraction quality and performance."""

    def __init__(self, test_documents_dir: str = "test_documents"):
        self.test_dir = Path(test_documents_dir)
        self.results = []

    def load_ground_truth(self) -> Dict[str, Dict[str, Any]]:
        """
        Load ground truth metadata for test documents.

        Returns dictionary mapping filename -> expected metadata
        """
        ground_truth = {
            "receipt_001.txt": {
                "invoice_number": "REC-2024-10-31-001",
                "invoice_date": "2024-10-31",
                "vendor_name": "Office Supplies Plus",
                "vendor_address": "555 Commerce Street, Seattle, WA 98101",
                "vendor_phone": "(206) 555-0200",
                "customer_name": "Sarah Johnson",
                "currency": "USD",
                "subtotal": 204.33,
                "tax_amount": 20.64,
                "tax_rate": 10.1,
                "total_amount": 224.97,
                "payment_method": "Corporate Credit Card",
                "item_count": 8,
            },
            "invoice_001.txt": {
                "invoice_number": "INV-2024-001",
                "invoice_date": "2024-10-31",
                "due_date": "2024-11-30",
                "vendor_name": "Acme Corporation",
                "vendor_address": "123 Business Street, San Francisco, CA 94102",
                "vendor_phone": "(415) 555-0100",
                "vendor_email": "billing@acmecorp.com",
                "customer_name": "Widget Company",
                "customer_address": "456 Client Avenue, New York, NY 10001",
                "subtotal": 10750.00,
                "tax_amount": 913.75,
                "tax_rate": 8.5,
                "total_amount": 11663.75,
                "payment_terms": "Net 30 days",
                "currency": "USD",
                "item_count": 3,
            },
            "technical_manual_20_pages.pdf": {
                "document_title": "Technical Implementation Manual",
                "document_type": "Technical Manual",
                "version": "2.0",
                "publication_date": "November 2025",
                "author_organization": "System Architecture Team",
                "document_purpose": "System Architecture and Deployment Guide",
                "system_requirements": "16GB RAM, 4 CPU cores, 100GB storage",
                "database_version": "PostgreSQL 15+",
                "api_type": "REST API",
                "authentication_method": "OAuth2",
                "deployment_method": "Docker Compose",
                "monitoring_tools": "Prometheus, Grafana",
                "security_standard": "TLS 1.3",
                "backup_frequency": "Daily",
                "testing_coverage": "85%",
                "maintenance_schedule": "Weekly security updates",
                "support_level": "Enterprise support contracts",
            },
            "contract_001.txt": {
                "contract_number": "CONT-2024-001",
                "contract_type": "Service Agreement",
                "title": "Service Agreement",
                "party_a": "Tech Solutions Inc.",
                "party_b": "Enterprise Corp",
                "execution_date": "October 1, 2024",
                "effective_date": "October 1, 2024",
                "expiration_date": "September 30, 2025",
                "contract_value": 5000.00,
                "currency": "USD",
                "payment_schedule": "Monthly",
                "duration_months": 12,
                "renewal_terms": "Automatically renews for successive 12-month periods",
                "termination_clause": True,
                "notice_period_days": 60,
                "status": "Active",
                "is_signed": True,
            },
            "email_meeting_notes.txt": {
                "subject": "Meeting Notes - Product Strategy Session",
                "sender_name": "Sarah Williams",
                "sender_email": "sarah.williams@company.com",
                "recipients": ["Michael Chen", "David Park", "Emma Rodriguez", "Lisa Thompson", "James Kim"],
                "sent_date": "2024-10-28T10:00:00",
                "message_type": "Meeting Notes",
                "has_attachments": False,
                "attachment_count": 0,
                "priority": "Normal",
                "is_meeting_related": True,
                "meeting_date": "2024-10-28T10:00:00",
                "has_action_items": True,
                "summary": "Q4 Product Roadmap Review, Enterprise Feature Prioritization, Resource Allocation, Go-to-Market Strategy",
            },
            # Add more test documents here
        }
        return ground_truth

    def calculate_metrics(
        self,
        extracted: Dict[str, Any],
        expected: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate quality metrics for extraction.

        Metrics:
        - precision: % of extracted fields that are correct
        - recall: % of expected fields that were extracted
        - f1_score: harmonic mean of precision and recall
        - field_accuracy: exact match accuracy per field
        """
        # Remove metadata fields from comparison
        metadata_fields = ['extraction_method', 'extraction_model',
                          'extraction_confidence', 'extracted_at', 'file_name']

        extracted_clean = {k: v for k, v in extracted.items()
                          if k not in metadata_fields and v is not None}

        # Calculate precision (of extracted fields, how many are correct?)
        correct = 0
        total_extracted = len(extracted_clean)

        for field, value in extracted_clean.items():
            if field in expected:
                expected_value = expected[field]

                # Handle numeric comparison with tolerance
                if isinstance(value, (int, float)) and isinstance(expected_value, (int, float)):
                    if abs(value - expected_value) < 0.01:
                        correct += 1
                # String comparison (case-insensitive, whitespace-normalized)
                elif isinstance(value, str) and isinstance(expected_value, str):
                    if value.lower().strip() == expected_value.lower().strip():
                        correct += 1
                    # Partial match for addresses (some variation is OK)
                    elif 'address' in field.lower():
                        # Check if main components are present
                        expected_parts = expected_value.lower().split()
                        value_parts = value.lower().split()
                        if len(set(expected_parts) & set(value_parts)) >= len(expected_parts) * 0.7:
                            correct += 1
                # Exact match for other types
                elif value == expected_value:
                    correct += 1

        precision = (correct / total_extracted) if total_extracted > 0 else 0.0

        # Calculate recall (of expected fields, how many were extracted?)
        found = sum(1 for field in expected if field in extracted_clean)
        recall = found / len(expected) if expected else 0.0

        # F1 score
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        # Field-by-field breakdown
        field_results = {}
        for field in expected:
            if field in extracted_clean:
                extracted_val = extracted_clean[field]
                expected_val = expected[field]

                # Check if correct
                is_correct = False
                if isinstance(extracted_val, (int, float)) and isinstance(expected_val, (int, float)):
                    is_correct = abs(extracted_val - expected_val) < 0.01
                elif isinstance(extracted_val, str) and isinstance(expected_val, str):
                    is_correct = extracted_val.lower().strip() == expected_val.lower().strip()
                    if not is_correct and 'address' in field.lower():
                        expected_parts = expected_val.lower().split()
                        extracted_parts = extracted_val.lower().split()
                        is_correct = len(set(expected_parts) & set(extracted_parts)) >= len(expected_parts) * 0.7
                else:
                    is_correct = extracted_val == expected_val

                field_results[field] = "✓" if is_correct else "✗"
            else:
                field_results[field] = "missing"

        return {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3),
            "fields_extracted": total_extracted,
            "fields_expected": len(expected),
            "fields_correct": correct,
            "field_breakdown": field_results,
        }

    def run_extraction_test(
        self,
        filename: str,
        extractor: ConfigurableMetadataExtractor,
        category: str = "invoices"
    ) -> Tuple[Dict[str, Any], float]:
        """
        Run extraction on a test document and measure time.

        Returns: (extracted_metadata, processing_time_seconds)
        """
        file_path = self.test_dir / filename

        if not file_path.exists():
            logger.error(f"Test file not found: {file_path}")
            return {}, 0.0

        # Check if this is a PDF and we have Docling available
        is_pdf = filename.lower().endswith('.pdf')
        use_docling_file_method = is_pdf and hasattr(extractor, 'extract_from_file')

        if use_docling_file_method:
            # Use Docling's file extraction for PDFs
            logger.info(f"Using Docling file extraction for PDF: {filename}")
            start_time = time.time()
            metadata = extractor.extract_from_file(
                file_path=str(file_path),
                category=category,
                file_metadata={"file_name": filename}
            )
            processing_time = time.time() - start_time
        else:
            # Read as text for other files
            content = file_path.read_text()

            # Time the extraction
            start_time = time.time()
            metadata = extractor.extract(
                text=content,
                category=category,
                file_metadata={"file_name": filename}
            )
            processing_time = time.time() - start_time

        return metadata, processing_time

    def run_benchmark(
        self,
        extractor_config: Dict[str, Any],
        name: str = "default",
        use_docling: bool = False
    ) -> Dict[str, Any]:
        """
        Run full benchmark suite.

        Args:
            extractor_config: Configuration for extractor (model, etc.)
            name: Name for this benchmark run
            use_docling: Use Docling for enhanced document parsing

        Returns:
            Aggregated results
        """
        logger.info(f"Running benchmark: {name}")
        logger.info(f"Config: {extractor_config}")
        logger.info(f"Using Docling: {use_docling}")

        ground_truth = self.load_ground_truth()

        # Initialize extractor
        if use_docling and DOCLING_AVAILABLE:
            extractor = DoclingMetadataExtractor(**extractor_config)
            extractor_config['parser'] = 'docling'
        else:
            extractor = ConfigurableMetadataExtractor(**extractor_config)
            extractor_config['parser'] = 'basic'

        results = []
        total_time = 0.0

        for filename, expected in ground_truth.items():
            logger.info(f"\nTesting: {filename}")

            # Skip PDFs if Docling is not available
            is_pdf = filename.lower().endswith('.pdf')
            if is_pdf and not (use_docling and DOCLING_AVAILABLE):
                logger.warning(f"Skipping PDF {filename} - Docling not available")
                continue

            # Determine category based on filename/content
            if "receipt" in filename.lower():
                category = "invoices"
            elif "invoice" in filename.lower():
                category = "invoices"
            elif "technical_manual" in filename.lower() or "manual" in filename.lower():
                category = "technical_manuals"
            elif "contract" in filename.lower():
                category = "contracts"
            elif "email" in filename.lower() or "meeting" in filename.lower():
                category = "correspondence"
            elif "report" in filename.lower():
                category = "reports"
            else:
                category = "correspondence"  # Default fallback

            logger.info(f"Using category: {category}")

            # Run extraction
            extracted, proc_time = self.run_extraction_test(filename, extractor, category)
            total_time += proc_time

            # Calculate metrics
            metrics = self.calculate_metrics(extracted, expected)

            # Store results
            result = {
                "filename": filename,
                "processing_time": round(proc_time, 2),
                "confidence": extracted.get("extraction_confidence", 0.0),
                "metrics": metrics,
                "extracted": extracted,
                "expected": expected,
            }
            results.append(result)

            # Log summary
            logger.info(f"  Precision: {metrics['precision']:.1%}")
            logger.info(f"  Recall: {metrics['recall']:.1%}")
            logger.info(f"  F1 Score: {metrics['f1_score']:.1%}")
            logger.info(f"  Time: {proc_time:.2f}s")
            logger.info(f"  Confidence: {result['confidence']:.2f}")

        # Aggregate metrics
        avg_precision = sum(r["metrics"]["precision"] for r in results) / len(results)
        avg_recall = sum(r["metrics"]["recall"] for r in results) / len(results)
        avg_f1 = sum(r["metrics"]["f1_score"] for r in results) / len(results)
        avg_confidence = sum(r["confidence"] for r in results) / len(results)
        avg_time = total_time / len(results)

        benchmark_result = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "config": extractor_config,
            "summary": {
                "avg_precision": round(avg_precision, 3),
                "avg_recall": round(avg_recall, 3),
                "avg_f1_score": round(avg_f1, 3),
                "avg_confidence": round(avg_confidence, 3),
                "avg_processing_time": round(avg_time, 2),
                "total_documents": len(results),
            },
            "detailed_results": results,
        }

        return benchmark_result

    def save_results(self, results: Dict[str, Any], output_file: str = None):
        """Save benchmark results to JSON file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"benchmark_results_{results['name']}_{timestamp}.json"

        output_path = Path("benchmarks") / output_file
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"\n✓ Results saved to: {output_path}")
        return output_path

    def compare_benchmarks(self, baseline_file: str, comparison_file: str):
        """Compare two benchmark results and show improvements."""
        baseline = json.loads(Path(baseline_file).read_text())
        comparison = json.loads(Path(comparison_file).read_text())

        logger.info("\n" + "=" * 80)
        logger.info("BENCHMARK COMPARISON")
        logger.info("=" * 80)

        logger.info(f"\nBaseline: {baseline['name']} ({baseline['timestamp']})")
        logger.info(f"Comparison: {comparison['name']} ({comparison['timestamp']})")

        # Compare summary metrics
        logger.info("\n" + "-" * 80)
        logger.info("SUMMARY METRICS")
        logger.info("-" * 80)

        metrics = ['avg_precision', 'avg_recall', 'avg_f1_score', 'avg_confidence']

        for metric in metrics:
            baseline_val = baseline['summary'][metric]
            comparison_val = comparison['summary'][metric]
            delta = comparison_val - baseline_val
            delta_pct = (delta / baseline_val * 100) if baseline_val > 0 else 0

            symbol = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"

            logger.info(f"{metric:20s}: {baseline_val:.3f} → {comparison_val:.3f} "
                       f"{symbol} ({delta:+.3f}, {delta_pct:+.1f}%)")

        # Processing time
        baseline_time = baseline['summary']['avg_processing_time']
        comparison_time = comparison['summary']['avg_processing_time']
        time_delta = comparison_time - baseline_time
        time_delta_pct = (time_delta / baseline_time * 100) if baseline_time > 0 else 0

        symbol = "⚡" if time_delta < 0 else "🐌" if time_delta > 0 else "➡️"
        logger.info(f"{'avg_processing_time':20s}: {baseline_time:.2f}s → {comparison_time:.2f}s "
                   f"{symbol} ({time_delta:+.2f}s, {time_delta_pct:+.1f}%)")

        # Overall verdict
        logger.info("\n" + "-" * 80)
        logger.info("VERDICT")
        logger.info("-" * 80)

        f1_improved = comparison['summary']['avg_f1_score'] > baseline['summary']['avg_f1_score']
        faster = comparison_time < baseline_time

        if f1_improved and faster:
            logger.info("🎉 IMPROVED: Better accuracy AND faster!")
        elif f1_improved:
            logger.info("✅ IMPROVED: Better accuracy (but slower)")
        elif faster:
            logger.info("⚡ IMPROVED: Faster (but lower accuracy)")
        else:
            logger.info("⚠️  NO IMPROVEMENT: Consider reverting changes")

        return {
            "improved": f1_improved,
            "faster": faster,
            "f1_delta": comparison['summary']['avg_f1_score'] - baseline['summary']['avg_f1_score'],
            "time_delta": time_delta,
        }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark metadata extraction quality")
    parser.add_argument("--baseline", action="store_true", help="Run baseline benchmark")
    parser.add_argument("--compare", action="store_true", help="Run comparison benchmark")
    parser.add_argument("--model", default="llama3.2:3b", help="Ollama model to use")
    parser.add_argument("--name", default=None, help="Name for this benchmark")
    parser.add_argument("--baseline-file", help="Baseline file for comparison")
    parser.add_argument("--comparison-file", help="Comparison file")
    parser.add_argument("--docling", action="store_true", help="Use Docling for document parsing")

    args = parser.parse_args()

    # Configure logger
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    benchmark = ExtractionBenchmark()

    if args.baseline:
        # Run baseline benchmark
        parser_suffix = "_docling" if args.docling else ""
        name = args.name or f"baseline_{args.model.replace(':', '_')}{parser_suffix}"
        config = {"model": args.model}

        results = benchmark.run_benchmark(config, name=name, use_docling=args.docling)
        output_file = benchmark.save_results(results)

        logger.info("\n" + "=" * 80)
        logger.info("BASELINE ESTABLISHED")
        logger.info("=" * 80)
        logger.info(f"F1 Score: {results['summary']['avg_f1_score']:.1%}")
        logger.info(f"Processing Time: {results['summary']['avg_processing_time']:.2f}s")
        logger.info(f"\nTo compare against this baseline:")
        logger.info(f"  python benchmark_extraction.py --compare --baseline-file {output_file}")

    elif args.compare:
        # Run comparison
        parser_suffix = "_docling" if args.docling else ""
        name = args.name or f"comparison_{args.model.replace(':', '_')}{parser_suffix}"
        config = {"model": args.model}

        results = benchmark.run_benchmark(config, name=name, use_docling=args.docling)
        comparison_file = benchmark.save_results(results)

        if args.baseline_file:
            benchmark.compare_benchmarks(args.baseline_file, comparison_file)
        else:
            logger.info("\n⚠️  No baseline file specified. Use --baseline-file to compare.")

    else:
        # Just run a quick benchmark
        logger.info("Running quick benchmark (use --baseline or --compare for full workflow)")
        config = {"model": args.model}
        results = benchmark.run_benchmark(config, name="quick_test")

        logger.info("\n" + "=" * 80)
        logger.info("RESULTS SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Precision: {results['summary']['avg_precision']:.1%}")
        logger.info(f"Recall: {results['summary']['avg_recall']:.1%}")
        logger.info(f"F1 Score: {results['summary']['avg_f1_score']:.1%}")
        logger.info(f"Confidence: {results['summary']['avg_confidence']:.1%}")
        logger.info(f"Avg Time: {results['summary']['avg_processing_time']:.2f}s")


if __name__ == "__main__":
    main()
