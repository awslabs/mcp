"""
Comprehensive Benchmarking Suite for CloudWAN MCP Memory Optimization.

This module provides enterprise-grade performance benchmarking specifically
designed for large-scale network topology processing with memory optimization.
"""

import asyncio
import gc
import json
import logging
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Memory optimization components
from .memory_optimization import (
    MemoryMonitor,
    MemoryCircuitBreaker,
    ObjectPool,
    get_memory_usage,
    format_memory_size,
)

# Streaming topology components
from .streaming_topology_manager import (
    StreamingTopologyManager,
    StreamingChunk,
    StreamingTopologyProcessor,
)

# Profiling components
from .memory_profiling_utilities import (
    MemoryProfiler,
)

# Monitoring components

# Network topology models
from ..models.network import NetworkTopology, NetworkElement, NetworkConnection

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    __slots__ = (
        "name",
        "duration",
        "memory_peak",
        "memory_growth",
        "throughput",
        "success_rate",
        "error_count",
        "metadata",
        "timestamp",
    )

    name: str
    duration: float
    memory_peak: int
    memory_growth: int
    throughput: float
    success_rate: float
    error_count: int
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results and statistics."""

    __slots__ = ("name", "results", "summary_stats", "performance_targets", "passed")

    name: str
    results: List[BenchmarkResult]
    summary_stats: Dict[str, Any]
    performance_targets: Dict[str, Any]
    passed: bool


class PerformanceBenchmark:
    """Base class for performance benchmarks."""

    def __init__(self, name: str, target_memory_mb: int = 500, target_duration: float = 60.0):
        self.name = name
        self.target_memory_mb = target_memory_mb
        self.target_duration = target_duration
        self.results: List[BenchmarkResult] = []
        self.profiler = MemoryProfiler()
        self.logger = logging.getLogger(__name__)

    async def run_benchmark(self, iterations: int = 5) -> BenchmarkSuite:
        """Run benchmark with specified iterations."""
        self.logger.info(f"Starting benchmark '{self.name}' with {iterations} iterations")

        results = []

        for i in range(iterations):
            self.logger.info(f"Running iteration {i+1}/{iterations}")

            # Ensure clean state
            gc.collect()

            try:
                result = await self._run_single_iteration(i)
                results.append(result)

                # Brief pause between iterations
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in iteration {i+1}: {e}")

                # Create error result
                error_result = BenchmarkResult(
                    name=f"{self.name}_iteration_{i+1}",
                    duration=0.0,
                    memory_peak=0,
                    memory_growth=0,
                    throughput=0.0,
                    success_rate=0.0,
                    error_count=1,
                    metadata={"error": str(e)},
                    timestamp=datetime.now(),
                )
                results.append(error_result)

        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(results)

        # Check if targets were met
        performance_targets = {
            "memory_mb": self.target_memory_mb,
            "duration_seconds": self.target_duration,
            "min_throughput": 100.0,  # elements/second
            "min_success_rate": 0.95,
        }

        passed = self._check_performance_targets(summary_stats, performance_targets)

        suite = BenchmarkSuite(
            name=self.name,
            results=results,
            summary_stats=summary_stats,
            performance_targets=performance_targets,
            passed=passed,
        )

        self.logger.info(f"Benchmark '{self.name}' completed: {'PASSED' if passed else 'FAILED'}")
        return suite

    async def _run_single_iteration(self, iteration: int) -> BenchmarkResult:
        """Run a single benchmark iteration."""
        start_time = time.time()
        initial_memory = get_memory_usage()

        with self.profiler.profile(f"{self.name}_iteration_{iteration}"):
            try:
                # Run the actual benchmark
                throughput, success_rate, error_count, metadata = await self._execute_benchmark()

                end_time = time.time()
                final_memory = get_memory_usage()

                # Get memory statistics from profiler
                memory_peak = max(
                    snapshot.current_memory
                    for snapshot in self.profiler.snapshots
                    if snapshot.timestamp >= datetime.fromtimestamp(start_time)
                )

                return BenchmarkResult(
                    name=f"{self.name}_iteration_{iteration}",
                    duration=end_time - start_time,
                    memory_peak=memory_peak,
                    memory_growth=final_memory - initial_memory,
                    throughput=throughput,
                    success_rate=success_rate,
                    error_count=error_count,
                    metadata=metadata,
                    timestamp=datetime.now(),
                )

            except Exception as e:
                self.logger.error(f"Error in benchmark execution: {e}")
                raise

    async def _execute_benchmark(self) -> Tuple[float, float, int, Dict[str, Any]]:
        """Execute the actual benchmark logic. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _execute_benchmark")

    def _calculate_summary_stats(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Calculate summary statistics for benchmark results."""
        if not results:
            return {}

        # Filter out error results for statistics
        valid_results = [r for r in results if r.error_count == 0]

        if not valid_results:
            return {"error": "No valid results to analyze"}

        durations = [r.duration for r in valid_results]
        memory_peaks = [r.memory_peak for r in valid_results]
        memory_growths = [r.memory_growth for r in valid_results]
        throughputs = [r.throughput for r in valid_results]
        success_rates = [r.success_rate for r in valid_results]

        return {
            "iterations": len(results),
            "valid_iterations": len(valid_results),
            "error_count": sum(r.error_count for r in results),
            "duration": {
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
                "min": min(durations),
                "max": max(durations),
            },
            "memory_peak": {
                "mean": statistics.mean(memory_peaks),
                "median": statistics.median(memory_peaks),
                "stdev": statistics.stdev(memory_peaks) if len(memory_peaks) > 1 else 0,
                "min": min(memory_peaks),
                "max": max(memory_peaks),
            },
            "memory_growth": {
                "mean": statistics.mean(memory_growths),
                "median": statistics.median(memory_growths),
                "stdev": (statistics.stdev(memory_growths) if len(memory_growths) > 1 else 0),
                "min": min(memory_growths),
                "max": max(memory_growths),
            },
            "throughput": {
                "mean": statistics.mean(throughputs),
                "median": statistics.median(throughputs),
                "stdev": statistics.stdev(throughputs) if len(throughputs) > 1 else 0,
                "min": min(throughputs),
                "max": max(throughputs),
            },
            "success_rate": {
                "mean": statistics.mean(success_rates),
                "median": statistics.median(success_rates),
                "stdev": (statistics.stdev(success_rates) if len(success_rates) > 1 else 0),
                "min": min(success_rates),
                "max": max(success_rates),
            },
        }

    def _check_performance_targets(
        self, summary_stats: Dict[str, Any], targets: Dict[str, Any]
    ) -> bool:
        """Check if benchmark met performance targets."""
        if "error" in summary_stats:
            return False

        # Check memory target
        if summary_stats["memory_peak"]["max"] > targets["memory_mb"] * 1024 * 1024:
            return False

        # Check duration target
        if summary_stats["duration"]["max"] > targets["duration_seconds"]:
            return False

        # Check throughput target
        if summary_stats["throughput"]["min"] < targets["min_throughput"]:
            return False

        # Check success rate target
        if summary_stats["success_rate"]["min"] < targets["min_success_rate"]:
            return False

        return True


class TopologyProcessingBenchmark(PerformanceBenchmark):
    """Benchmark for topology processing performance."""

    def __init__(self, element_count: int = 1000, connection_count: int = 2000):
        super().__init__(
            name=f"topology_processing_{element_count}e_{connection_count}c",
            target_memory_mb=1000,  # 1GB for large topology
            target_duration=30.0,
        )
        self.element_count = element_count
        self.connection_count = connection_count
        self.streaming_manager = StreamingTopologyManager()

    async def _execute_benchmark(self) -> Tuple[float, float, int, Dict[str, Any]]:
        """Execute topology processing benchmark."""
        # Generate test topology
        topology = self._generate_test_topology()

        # Process topology with streaming manager
        processed_elements = 0
        errors = 0

        start_time = time.time()

        try:
            async for chunk in self.streaming_manager.stream_topology_chunks(
                topology, chunk_size=100
            ):
                processed_elements += len(chunk.elements)

                # Simulate some processing
                await asyncio.sleep(0.01)

        except Exception as e:
            errors += 1
            self.logger.error(f"Error processing topology: {e}")

        end_time = time.time()
        duration = end_time - start_time

        # Calculate metrics
        throughput = processed_elements / duration if duration > 0 else 0
        success_rate = 1.0 - (errors / max(1, processed_elements))

        metadata = {
            "element_count": self.element_count,
            "connection_count": self.connection_count,
            "processed_elements": processed_elements,
            "chunks_processed": processed_elements // 100,
        }

        return throughput, success_rate, errors, metadata

    def _generate_test_topology(self) -> NetworkTopology:
        """Generate a test network topology."""
        elements = []
        connections = []

        # Generate elements
        for i in range(self.element_count):
            element = NetworkElement(
                id=f"element_{i}",
                name=f"Test Element {i}",
                element_type="vpc",
                region=f"us-west-{(i % 2) + 1}",
                metadata={"test": True, "index": i},
            )
            elements.append(element)

        # Generate connections
        for i in range(self.connection_count):
            source_idx = i % len(elements)
            target_idx = (i + 1) % len(elements)

            connection = NetworkConnection(
                id=f"connection_{i}",
                source_id=elements[source_idx].id,
                target_id=elements[target_idx].id,
                connection_type="vpc_peering",
                metadata={"test": True, "index": i},
            )
            connections.append(connection)

        return NetworkTopology(
            elements=elements, connections=connections, metadata={"test_topology": True}
        )


class StreamingMemoryBenchmark(PerformanceBenchmark):
    """Benchmark for streaming memory optimization."""

    def __init__(self, chunk_count: int = 50, elements_per_chunk: int = 200):
        super().__init__(
            name=f"streaming_memory_{chunk_count}c_{elements_per_chunk}e",
            target_memory_mb=500,
            target_duration=20.0,
        )
        self.chunk_count = chunk_count
        self.elements_per_chunk = elements_per_chunk
        self.streaming_processor = StreamingTopologyProcessor()

    async def _execute_benchmark(self) -> Tuple[float, float, int, Dict[str, Any]]:
        """Execute streaming memory benchmark."""
        processed_chunks = 0
        errors = 0

        start_time = time.time()

        # Process chunks with memory monitoring
        async for result in self.streaming_processor.stream_process_topology(
            self._generate_test_topology(), self._process_chunk, memory_threshold_mb=300
        ):
            processed_chunks += 1

            if isinstance(result, Exception):
                errors += 1

        end_time = time.time()
        duration = end_time - start_time

        # Calculate metrics
        throughput = processed_chunks / duration if duration > 0 else 0
        success_rate = 1.0 - (errors / max(1, processed_chunks))

        metadata = {
            "chunk_count": self.chunk_count,
            "elements_per_chunk": self.elements_per_chunk,
            "processed_chunks": processed_chunks,
            "memory_threshold_mb": 300,
        }

        return throughput, success_rate, errors, metadata

    def _generate_test_topology(self) -> NetworkTopology:
        """Generate test topology for streaming."""
        elements = []

        total_elements = self.chunk_count * self.elements_per_chunk

        for i in range(total_elements):
            element = NetworkElement(
                id=f"stream_element_{i}",
                name=f"Stream Element {i}",
                element_type="transit_gateway",
                region=f"us-east-{(i % 2) + 1}",
                metadata={"streaming": True, "index": i},
            )
            elements.append(element)

        return NetworkTopology(elements=elements, connections=[], metadata={"streaming_test": True})

    async def _process_chunk(self, chunk: StreamingChunk) -> Dict[str, Any]:
        """Process a streaming chunk."""
        # Simulate processing
        await asyncio.sleep(0.05)

        return {
            "chunk_id": chunk.chunk_id,
            "element_count": len(chunk.elements),
            "processed": True,
        }


class MemoryOptimizationBenchmark(PerformanceBenchmark):
    """Benchmark for memory optimization techniques."""

    def __init__(self, optimization_level: str = "high"):
        super().__init__(
            name=f"memory_optimization_{optimization_level}",
            target_memory_mb=300,
            target_duration=15.0,
        )
        self.optimization_level = optimization_level
        self.memory_monitor = MemoryMonitor()
        self.circuit_breaker = MemoryCircuitBreaker()

    async def _execute_benchmark(self) -> Tuple[float, float, int, Dict[str, Any]]:
        """Execute memory optimization benchmark."""
        # Test object pool performance
        object_pool = ObjectPool(
            factory=lambda: NetworkElement(
                id="pool_element",
                name="Pool Element",
                element_type="vpc",
                region="us-west-1",
            )
        )

        operations = 10000
        successful_operations = 0
        errors = 0

        start_time = time.time()

        for i in range(operations):
            try:
                # Get object from pool
                obj = object_pool.get()

                # Simulate some work
                obj.metadata = {"operation": i}

                # Return to pool
                object_pool.return_object(obj)

                successful_operations += 1

                # Memory monitoring
                if i % 1000 == 0:
                    current_memory = get_memory_usage()
                    self.memory_monitor.record_memory_usage(current_memory)

                    if self.circuit_breaker.should_break():
                        self.logger.warning("Circuit breaker activated")
                        break

            except Exception as e:
                errors += 1
                self.logger.error(f"Error in operation {i}: {e}")

        end_time = time.time()
        duration = end_time - start_time

        # Calculate metrics
        throughput = successful_operations / duration if duration > 0 else 0
        success_rate = successful_operations / operations

        metadata = {
            "optimization_level": self.optimization_level,
            "operations": operations,
            "successful_operations": successful_operations,
            "pool_size": len(object_pool.available_objects),
            "memory_readings": len(self.memory_monitor.memory_history),
        }

        return throughput, success_rate, errors, metadata


class ConcurrencyBenchmark(PerformanceBenchmark):
    """Benchmark for concurrent processing performance."""

    def __init__(self, worker_count: int = 10, tasks_per_worker: int = 100):
        super().__init__(
            name=f"concurrency_{worker_count}w_{tasks_per_worker}t",
            target_memory_mb=800,
            target_duration=25.0,
        )
        self.worker_count = worker_count
        self.tasks_per_worker = tasks_per_worker

    async def _execute_benchmark(self) -> Tuple[float, float, int, Dict[str, Any]]:
        """Execute concurrency benchmark."""
        total_tasks = self.worker_count * self.tasks_per_worker
        completed_tasks = 0
        errors = 0

        start_time = time.time()

        # Create tasks
        tasks = []
        for worker_id in range(self.worker_count):
            task = asyncio.create_task(self._worker_task(worker_id, self.tasks_per_worker))
            tasks.append(task)

        # Wait for completion
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        # Process results
        for result in results:
            if isinstance(result, Exception):
                errors += 1
            else:
                completed_tasks += result

        # Calculate metrics
        throughput = completed_tasks / duration if duration > 0 else 0
        success_rate = completed_tasks / total_tasks

        metadata = {
            "worker_count": self.worker_count,
            "tasks_per_worker": self.tasks_per_worker,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
        }

        return throughput, success_rate, errors, metadata

    async def _worker_task(self, worker_id: int, task_count: int) -> int:
        """Execute tasks for a single worker."""
        completed = 0

        for i in range(task_count):
            try:
                # Simulate some work
                await asyncio.sleep(0.01)

                # Create and process a network element
                element = NetworkElement(
                    id=f"worker_{worker_id}_element_{i}",
                    name=f"Worker {worker_id} Element {i}",
                    element_type="cloudwan_edge",
                    region="us-west-1",
                    metadata={"worker_id": worker_id, "task_id": i},
                )

                # Simulate processing
                _ = element.to_dict()

                completed += 1

            except Exception as e:
                self.logger.error(f"Error in worker {worker_id}, task {i}: {e}")

        return completed


class BenchmarkRunner:
    """Main benchmark runner for comprehensive performance testing."""

    def __init__(self, output_directory: str = "benchmark_results"):
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)

        self.benchmarks: List[PerformanceBenchmark] = []
        self.results: Dict[str, BenchmarkSuite] = {}

        self.logger = logging.getLogger(__name__)

    def add_benchmark(self, benchmark: PerformanceBenchmark):
        """Add a benchmark to the runner."""
        self.benchmarks.append(benchmark)
        self.logger.info(f"Added benchmark: {benchmark.name}")

    def add_standard_benchmarks(self):
        """Add standard benchmark suite."""
        # Small topology benchmarks
        self.add_benchmark(TopologyProcessingBenchmark(element_count=100, connection_count=200))
        self.add_benchmark(StreamingMemoryBenchmark(chunk_count=10, elements_per_chunk=50))
        self.add_benchmark(MemoryOptimizationBenchmark(optimization_level="medium"))
        self.add_benchmark(ConcurrencyBenchmark(worker_count=5, tasks_per_worker=50))

        # Medium topology benchmarks
        self.add_benchmark(TopologyProcessingBenchmark(element_count=500, connection_count=1000))
        self.add_benchmark(StreamingMemoryBenchmark(chunk_count=25, elements_per_chunk=100))
        self.add_benchmark(MemoryOptimizationBenchmark(optimization_level="high"))
        self.add_benchmark(ConcurrencyBenchmark(worker_count=10, tasks_per_worker=100))

        # Large topology benchmarks
        self.add_benchmark(TopologyProcessingBenchmark(element_count=1000, connection_count=2000))
        self.add_benchmark(StreamingMemoryBenchmark(chunk_count=50, elements_per_chunk=200))

        self.logger.info(f"Added {len(self.benchmarks)} standard benchmarks")

    async def run_all_benchmarks(self, iterations: int = 3) -> Dict[str, BenchmarkSuite]:
        """Run all configured benchmarks."""
        self.logger.info(
            f"Running {len(self.benchmarks)} benchmarks with {iterations} iterations each"
        )

        results = {}

        for benchmark in self.benchmarks:
            try:
                self.logger.info(f"Starting benchmark: {benchmark.name}")

                result = await benchmark.run_benchmark(iterations)
                results[benchmark.name] = result

                # Save individual results
                self._save_benchmark_result(result)

                self.logger.info(
                    f"Completed benchmark: {benchmark.name} - {'PASSED' if result.passed else 'FAILED'}"
                )

            except Exception as e:
                self.logger.error(f"Error running benchmark {benchmark.name}: {e}")

        self.results = results

        # Save comprehensive report
        self._save_comprehensive_report()

        return results

    def _save_benchmark_result(self, result: BenchmarkSuite):
        """Save individual benchmark result."""
        filename = f"{result.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_directory / filename

        # Convert to serializable format
        data = {
            "name": result.name,
            "passed": result.passed,
            "summary_stats": result.summary_stats,
            "performance_targets": result.performance_targets,
            "results": [
                {
                    "name": r.name,
                    "duration": r.duration,
                    "memory_peak": r.memory_peak,
                    "memory_growth": r.memory_growth,
                    "throughput": r.throughput,
                    "success_rate": r.success_rate,
                    "error_count": r.error_count,
                    "metadata": r.metadata,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in result.results
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Saved benchmark result to: {filepath}")

    def _save_comprehensive_report(self):
        """Save comprehensive benchmark report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_report_{timestamp}.json"
        filepath = self.output_directory / filename

        # Calculate overall statistics
        total_benchmarks = len(self.results)
        passed_benchmarks = sum(1 for r in self.results.values() if r.passed)

        report = {
            "timestamp": timestamp,
            "total_benchmarks": total_benchmarks,
            "passed_benchmarks": passed_benchmarks,
            "overall_pass_rate": (
                passed_benchmarks / total_benchmarks if total_benchmarks > 0 else 0
            ),
            "benchmark_results": {
                name: {
                    "passed": result.passed,
                    "summary_stats": result.summary_stats,
                    "performance_targets": result.performance_targets,
                }
                for name, result in self.results.items()
            },
        }

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Saved comprehensive report to: {filepath}")

    def get_summary_report(self) -> Dict[str, Any]:
        """Get summary report of all benchmark results."""
        if not self.results:
            return {}

        total_benchmarks = len(self.results)
        passed_benchmarks = sum(1 for r in self.results.values() if r.passed)

        # Collect memory statistics
        memory_peaks = []
        durations = []
        throughputs = []

        for result in self.results.values():
            if result.summary_stats and "memory_peak" in result.summary_stats:
                memory_peaks.append(result.summary_stats["memory_peak"]["max"])
            if result.summary_stats and "duration" in result.summary_stats:
                durations.append(result.summary_stats["duration"]["max"])
            if result.summary_stats and "throughput" in result.summary_stats:
                throughputs.append(result.summary_stats["throughput"]["min"])

        return {
            "total_benchmarks": total_benchmarks,
            "passed_benchmarks": passed_benchmarks,
            "overall_pass_rate": passed_benchmarks / total_benchmarks,
            "aggregate_stats": {
                "max_memory_peak": max(memory_peaks) if memory_peaks else 0,
                "max_duration": max(durations) if durations else 0,
                "min_throughput": min(throughputs) if throughputs else 0,
                "avg_memory_peak": (sum(memory_peaks) / len(memory_peaks) if memory_peaks else 0),
            },
            "benchmark_status": {name: result.passed for name, result in self.results.items()},
        }


# Factory function for easy benchmark creation
def create_benchmark_runner(
    output_directory: str = "benchmark_results",
) -> BenchmarkRunner:
    """Create a benchmark runner with standard configuration."""
    return BenchmarkRunner(output_directory)


# Example usage
if __name__ == "__main__":

    async def main():
        # Create benchmark runner
        runner = create_benchmark_runner()

        # Add standard benchmarks
        runner.add_standard_benchmarks()

        # Run benchmarks
        results = await runner.run_all_benchmarks(iterations=2)

        # Print summary
        summary = runner.get_summary_report()
        print("\nBenchmark Summary:")
        print(f"Total benchmarks: {summary['total_benchmarks']}")
        print(f"Passed benchmarks: {summary['passed_benchmarks']}")
        print(f"Overall pass rate: {summary['overall_pass_rate']:.2%}")

        if summary["aggregate_stats"]:
            print(
                f"Max memory peak: {format_memory_size(summary['aggregate_stats']['max_memory_peak'])}"
            )
            print(f"Max duration: {summary['aggregate_stats']['max_duration']:.2f}s")
            print(f"Min throughput: {summary['aggregate_stats']['min_throughput']:.2f} ops/s")

    asyncio.run(main())
