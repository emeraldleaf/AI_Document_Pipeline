#!/usr/bin/env python3
"""
Performance Benchmarking Tool for AI Document Pipeline
Measures throughput, latency, and resource usage across architectural boundaries
"""

import asyncio
import time
import psutil
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics
import logging

from src.domain import load_configuration
from src.services import create_document_processing_service, create_ollama_service
from src.infrastructure import create_extraction_service
from src.services.ocr_service import TesseractOCRService


logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """System resource usage metrics."""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read: int
    disk_io_write: int
    timestamp: float


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation."""
    operation: str
    file_path: Path
    file_size_mb: float
    processing_time: float
    throughput_mb_per_sec: float
    success: bool
    error: Optional[str] = None
    start_resources: Optional[ResourceMetrics] = None
    end_resources: Optional[ResourceMetrics] = None


@dataclass
class BenchmarkSummary:
    """Summary of benchmark results."""
    total_files: int
    successful_operations: int
    failed_operations: int
    total_processing_time: float
    average_processing_time: float
    median_processing_time: float
    total_throughput_mb_per_sec: float
    average_file_size_mb: float
    operations_per_second: float
    peak_memory_mb: float
    average_cpu_percent: float


class PerformanceBenchmark:
    """Performance benchmarking framework."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the benchmark framework."""
        self.config = load_configuration(config_path)
        self.ocr_service = TesseractOCRService()
        self.extraction_service = None
        self.classification_service = None
        self.document_service = None
        self.metrics: List[PerformanceMetrics] = []
        self.resource_history: List[ResourceMetrics] = []
    
    async def initialize(self):
        """Initialize async services."""
        self.extraction_service = create_extraction_service(self.ocr_service)
        self.classification_service = create_ollama_service(self.config)
        self.document_service = await create_document_processing_service(
            extraction_service=self.extraction_service,
            classification_service=self.classification_service,
            config=self.config,
        )
    
    def get_resource_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics."""
        process = psutil.Process()
        disk_io = psutil.disk_io_counters()
        
        return ResourceMetrics(
            cpu_percent=psutil.cpu_percent(),
            memory_mb=process.memory_info().rss / 1024 / 1024,
            memory_percent=process.memory_percent(),
            disk_io_read=disk_io.read_bytes if disk_io else 0,
            disk_io_write=disk_io.write_bytes if disk_io else 0,
            timestamp=time.time()
        )
    
    async def benchmark_ocr_operation(self, file_path: Path) -> PerformanceMetrics:
        """Benchmark OCR operation performance."""
        start_resources = self.get_resource_metrics()
        start_time = time.time()
        file_size_mb = file_path.stat().st_size / 1024 / 1024
        
        try:
            if not self.ocr_service.is_supported(str(file_path)):
                return PerformanceMetrics(
                    operation="ocr",
                    file_path=file_path,
                    file_size_mb=file_size_mb,
                    processing_time=0.0,
                    throughput_mb_per_sec=0.0,
                    success=False,
                    error="File format not supported",
                    start_resources=start_resources
                )
            
            result = await self.ocr_service.extract_text(str(file_path))
            
            end_time = time.time()
            end_resources = self.get_resource_metrics()
            processing_time = end_time - start_time
            throughput = file_size_mb / processing_time if processing_time > 0 else 0
            
            return PerformanceMetrics(
                operation="ocr",
                file_path=file_path,
                file_size_mb=file_size_mb,
                processing_time=processing_time,
                throughput_mb_per_sec=throughput,
                success=result.is_success,
                error=result.error if not result.is_success else None,
                start_resources=start_resources,
                end_resources=end_resources
            )
            
        except Exception as e:
            end_time = time.time()
            end_resources = self.get_resource_metrics()
            processing_time = end_time - start_time
            
            return PerformanceMetrics(
                operation="ocr",
                file_path=file_path,
                file_size_mb=file_size_mb,
                processing_time=processing_time,
                throughput_mb_per_sec=0.0,
                success=False,
                error=str(e),
                start_resources=start_resources,
                end_resources=end_resources
            )
    
    async def benchmark_extraction_operation(self, file_path: Path) -> PerformanceMetrics:
        """Benchmark document extraction performance."""
        start_resources = self.get_resource_metrics()
        start_time = time.time()
        file_size_mb = file_path.stat().st_size / 1024 / 1024
        
        try:
            result = await self.extraction_service.extract_content(file_path)
            
            end_time = time.time()
            end_resources = self.get_resource_metrics()
            processing_time = end_time - start_time
            throughput = file_size_mb / processing_time if processing_time > 0 else 0
            
            return PerformanceMetrics(
                operation="extraction",
                file_path=file_path,
                file_size_mb=file_size_mb,
                processing_time=processing_time,
                throughput_mb_per_sec=throughput,
                success=result.is_success,
                error=result.error if not result.is_success else None,
                start_resources=start_resources,
                end_resources=end_resources
            )
            
        except Exception as e:
            end_time = time.time()
            end_resources = self.get_resource_metrics()
            processing_time = end_time - start_time
            
            return PerformanceMetrics(
                operation="extraction",
                file_path=file_path,
                file_size_mb=file_size_mb,
                processing_time=processing_time,
                throughput_mb_per_sec=0.0,
                success=False,
                error=str(e),
                start_resources=start_resources,
                end_resources=end_resources
            )
    
    async def benchmark_classification_operation(self, file_path: Path) -> PerformanceMetrics:
        """Benchmark classification performance."""
        start_resources = self.get_resource_metrics()
        start_time = time.time()
        file_size_mb = file_path.stat().st_size / 1024 / 1024
        
        try:
            # First extract content
            extraction_result = await self.extraction_service.extract_content(file_path)
            if not extraction_result.is_success:
                end_time = time.time()
                end_resources = self.get_resource_metrics()
                processing_time = end_time - start_time
                
                return PerformanceMetrics(
                    operation="classification",
                    file_path=file_path,
                    file_size_mb=file_size_mb,
                    processing_time=processing_time,
                    throughput_mb_per_sec=0.0,
                    success=False,
                    error=f"Extraction failed: {extraction_result.error}",
                    start_resources=start_resources
                )
            
            content = extraction_result.value
            categories = self.config.get_categories()
            
            result = await self.classification_service.classify_document(content, categories)
            
            end_time = time.time()
            end_resources = self.get_resource_metrics()
            processing_time = end_time - start_time
            throughput = file_size_mb / processing_time if processing_time > 0 else 0
            
            return PerformanceMetrics(
                operation="classification",
                file_path=file_path,
                file_size_mb=file_size_mb,
                processing_time=processing_time,
                throughput_mb_per_sec=throughput,
                success=result.is_success,
                error=result.error if not result.is_success else None,
                start_resources=start_resources,
                end_resources=end_resources
            )
            
        except Exception as e:
            end_time = time.time()
            end_resources = self.get_resource_metrics()
            processing_time = end_time - start_time
            
            return PerformanceMetrics(
                operation="classification",
                file_path=file_path,
                file_size_mb=file_size_mb,
                processing_time=processing_time,
                throughput_mb_per_sec=0.0,
                success=False,
                error=str(e),
                start_resources=start_resources,
                end_resources=end_resources
            )
    
    async def benchmark_end_to_end_operation(self, file_path: Path) -> PerformanceMetrics:
        """Benchmark complete end-to-end processing performance."""
        start_resources = self.get_resource_metrics()
        start_time = time.time()
        file_size_mb = file_path.stat().st_size / 1024 / 1024
        
        try:
            categories = self.config.get_categories()
            result = await self.document_service.process_document(file_path, categories)
            
            end_time = time.time()
            end_resources = self.get_resource_metrics()
            processing_time = end_time - start_time
            throughput = file_size_mb / processing_time if processing_time > 0 else 0
            
            return PerformanceMetrics(
                operation="end_to_end",
                file_path=file_path,
                file_size_mb=file_size_mb,
                processing_time=processing_time,
                throughput_mb_per_sec=throughput,
                success=result.is_success,
                error=result.error if not result.is_success else None,
                start_resources=start_resources,
                end_resources=end_resources
            )
            
        except Exception as e:
            end_time = time.time()
            end_resources = self.get_resource_metrics()
            processing_time = end_time - start_time
            
            return PerformanceMetrics(
                operation="end_to_end",
                file_path=file_path,
                file_size_mb=file_size_mb,
                processing_time=processing_time,
                throughput_mb_per_sec=0.0,
                success=False,
                error=str(e),
                start_resources=start_resources,
                end_resources=end_resources
            )
    
    async def run_benchmark_suite(
        self, 
        test_files: List[Path], 
        operations: List[str] = None
    ) -> Dict[str, BenchmarkSummary]:
        """Run complete benchmark suite across all operations."""
        if operations is None:
            operations = ["ocr", "extraction", "classification", "end_to_end"]
        
        await self.initialize()
        
        logger.info(f"Starting benchmark suite with {len(test_files)} files")
        logger.info(f"Operations to benchmark: {operations}")
        
        results = {}
        
        for operation in operations:
            logger.info(f"Benchmarking {operation} operation...")
            operation_metrics = []
            
            for file_path in test_files:
                if not file_path.exists():
                    logger.warning(f"Test file not found: {file_path}")
                    continue
                
                try:
                    if operation == "ocr":
                        metric = await self.benchmark_ocr_operation(file_path)
                    elif operation == "extraction":
                        metric = await self.benchmark_extraction_operation(file_path)
                    elif operation == "classification":
                        metric = await self.benchmark_classification_operation(file_path)
                    elif operation == "end_to_end":
                        metric = await self.benchmark_end_to_end_operation(file_path)
                    else:
                        logger.warning(f"Unknown operation: {operation}")
                        continue
                    
                    operation_metrics.append(metric)
                    self.metrics.append(metric)
                    
                    # Track resource usage
                    if metric.end_resources:
                        self.resource_history.append(metric.end_resources)
                    
                    logger.info(f"  {file_path.name}: {metric.processing_time:.2f}s, "
                              f"{metric.throughput_mb_per_sec:.2f} MB/s")
                    
                except Exception as e:
                    logger.error(f"Benchmark failed for {file_path}: {e}")
            
            # Calculate summary for this operation
            if operation_metrics:
                results[operation] = self.calculate_benchmark_summary(operation_metrics)
        
        return results
    
    def calculate_benchmark_summary(self, metrics: List[PerformanceMetrics]) -> BenchmarkSummary:
        """Calculate summary statistics for benchmark results."""
        if not metrics:
            raise ValueError("No metrics provided for summary calculation")
        
        successful_metrics = [m for m in metrics if m.success]
        processing_times = [m.processing_time for m in successful_metrics]
        file_sizes = [m.file_size_mb for m in metrics]
        throughputs = [m.throughput_mb_per_sec for m in successful_metrics if m.throughput_mb_per_sec > 0]
        
        # Resource metrics
        memory_values = []
        cpu_values = []
        
        for metric in metrics:
            if metric.end_resources:
                memory_values.append(metric.end_resources.memory_mb)
                cpu_values.append(metric.end_resources.cpu_percent)
        
        total_processing_time = sum(processing_times)
        operations_per_second = len(successful_metrics) / total_processing_time if total_processing_time > 0 else 0
        
        return BenchmarkSummary(
            total_files=len(metrics),
            successful_operations=len(successful_metrics),
            failed_operations=len(metrics) - len(successful_metrics),
            total_processing_time=total_processing_time,
            average_processing_time=statistics.mean(processing_times) if processing_times else 0,
            median_processing_time=statistics.median(processing_times) if processing_times else 0,
            total_throughput_mb_per_sec=sum(throughputs),
            average_file_size_mb=statistics.mean(file_sizes) if file_sizes else 0,
            operations_per_second=operations_per_second,
            peak_memory_mb=max(memory_values) if memory_values else 0,
            average_cpu_percent=statistics.mean(cpu_values) if cpu_values else 0
        )
    
    def export_benchmark_results(self, results: Dict[str, BenchmarkSummary], output_path: Path):
        """Export benchmark results to JSON."""
        export_data = {
            "benchmark_summary": {op: asdict(summary) for op, summary in results.items()},
            "detailed_metrics": [asdict(metric) for metric in self.metrics],
            "resource_history": [asdict(resource) for resource in self.resource_history],
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                "platform": psutil.os.name,
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Benchmark results exported to: {output_path}")
    
    def print_benchmark_summary(self, results: Dict[str, BenchmarkSummary]):
        """Print formatted benchmark summary."""
        print("\n" + "="*80)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("="*80)
        
        for operation, summary in results.items():
            print(f"\n{operation.upper()} OPERATION:")
            print(f"  Total Files: {summary.total_files}")
            print(f"  Success Rate: {summary.successful_operations}/{summary.total_files} "
                  f"({summary.successful_operations/summary.total_files:.1%})")
            print(f"  Average Processing Time: {summary.average_processing_time:.2f}s")
            print(f"  Median Processing Time: {summary.median_processing_time:.2f}s")
            print(f"  Operations per Second: {summary.operations_per_second:.2f}")
            print(f"  Total Throughput: {summary.total_throughput_mb_per_sec:.2f} MB/s")
            print(f"  Peak Memory Usage: {summary.peak_memory_mb:.1f} MB")
            print(f"  Average CPU Usage: {summary.average_cpu_percent:.1f}%")


async def main():
    """Main function to run performance benchmarks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run performance benchmarks")
    parser.add_argument("test_dir", type=Path, help="Directory containing test files")
    parser.add_argument("--operations", nargs="+", 
                       choices=["ocr", "extraction", "classification", "end_to_end"],
                       default=["end_to_end"],
                       help="Operations to benchmark")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark_results"),
                       help="Output directory for results")
    parser.add_argument("--config", type=Path, help="Configuration file path")
    parser.add_argument("--file-pattern", default="*", help="File pattern to match")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Find test files
    test_files = list(args.test_dir.glob(args.file_pattern))
    test_files = [f for f in test_files if f.is_file()]
    
    if not test_files:
        print(f"No test files found in {args.test_dir} with pattern {args.file_pattern}")
        return
    
    print(f"Found {len(test_files)} test files")
    
    # Create output directory
    args.output_dir.mkdir(exist_ok=True)
    
    # Run benchmarks
    benchmark = PerformanceBenchmark(args.config)
    results = await benchmark.run_benchmark_suite(test_files, args.operations)
    
    # Export and display results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark.export_benchmark_results(results, args.output_dir / f"benchmark_results_{timestamp}.json")
    benchmark.print_benchmark_summary(results)


if __name__ == "__main__":
    asyncio.run(main())