"""
Performance Benchmarks and Optimization Suite for Foundation Engines.

This module provides comprehensive performance testing, benchmarking, and
optimization recommendations for the Multi-Region Processing Engine and
IP Resolution Engine.
"""

import asyncio
import json
import logging
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import anyio

from ..aws.client_manager import AWSClientManager
from .client_manager_extensions import EnhancedAWSClientManager
from .ip_resolution_engine import IPResolutionEngine
from .multi_region_engine import MultiRegionProcessingEngine

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of performance benchmarks."""

    LATENCY = "latency"
    THROUGHPUT = "throughput"
    CONCURRENCY = "concurrency"
    SCALABILITY = "scalability"
    ERROR_HANDLING = "error_handling"


class PerformanceGrade(Enum):
    """Performance grades."""

    EXCELLENT = "A+"
    GOOD = "A"
    ACCEPTABLE = "B"
    NEEDS_IMPROVEMENT = "C"
    POOR = "D"
    FAILED = "F"


@dataclass
class BenchmarkMetrics:
    """Metrics from a performance benchmark."""

    benchmark_name: str
    benchmark_type: BenchmarkType
    duration_seconds: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    average_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    throughput_ops_per_second: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    performance_grade: PerformanceGrade = PerformanceGrade.ACCEPTABLE
    recommendations: list[str] = field(default_factory=list)
    raw_latencies: list[float] = field(default_factory=list)


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""

    category: str
    priority: int  # 1 = high, 5 = low
    description: str
    expected_improvement: str
    implementation_effort: str  # low, medium, high
    configuration_changes: dict[str, Any] = field(default_factory=dict)


class PerformanceBenchmarkSuite:
    """
    Comprehensive performance benchmark suite for foundation engines.

    Tests multiple scenarios:
    - Single region operations
    - Multi-region concurrent operations
    - High load scenarios
    - Error recovery performance
    - Memory and CPU efficiency
    - CloudWAN context resolution performance
    """

    def __init__(
        self,
        aws_manager: AWSClientManager,
        multi_region_engine: MultiRegionProcessingEngine | None = None,
        ip_resolution_engine: IPResolutionEngine | None = None,
        enhanced_client_manager: EnhancedAWSClientManager | None = None,
    ):
        """
        Initialize Performance Benchmark Suite.

        Args:
            aws_manager: Base AWS client manager
            multi_region_engine: Multi-region processing engine to test
            ip_resolution_engine: IP resolution engine to test
            enhanced_client_manager: Enhanced client manager to test
        """
        self.aws_manager = aws_manager
        self.multi_region_engine = multi_region_engine or MultiRegionProcessingEngine(aws_manager)
        self.ip_resolution_engine = ip_resolution_engine or IPResolutionEngine(aws_manager)
        self.enhanced_client_manager = enhanced_client_manager

        # Performance targets
        self.performance_targets = {
            "ip_resolution_ms": 2000.0,  # 2 second target
            "multi_region_p95_ms": 3000.0,  # 3 second P95 target
            "error_rate_threshold": 0.05,  # 5% error rate threshold
            "throughput_ops_per_second": 10.0,  # Minimum ops/sec
        }

        logger.info("Performance benchmark suite initialized")

    async def run_comprehensive_benchmark(
        self,
        regions: list[str] | None = None,
        test_ip_addresses: list[str] | None = None,
        duration_seconds: float = 300.0,
        concurrent_requests: int = 10,
    ) -> dict[str, BenchmarkMetrics]:
        """
        Run comprehensive performance benchmark across all engines.

        Args:
            regions: AWS regions to test (defaults to configured regions)
            test_ip_addresses: IP addresses to test (uses defaults if None)
            duration_seconds: Duration of sustained load test
            concurrent_requests: Number of concurrent requests

        Returns:
            Dictionary of benchmark results by test name
        """
        logger.info(f"Starting comprehensive benchmark - duration: {duration_seconds}s")

        regions = regions or self.aws_manager.get_supported_regions()[:5]  # Limit to 5 regions
        test_ip_addresses = test_ip_addresses or [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "208.67.222.222",  # OpenDNS
            "amazon.com",  # Hostname resolution test
            "192.168.1.1",  # Private IP test
        ]

        benchmark_results = {}

        # 1. IP Resolution Latency Test
        logger.info("Running IP resolution latency benchmark")
        benchmark_results["ip_resolution_latency"] = await self._benchmark_ip_resolution_latency(
            test_ip_addresses, regions
        )

        # 2. Multi-Region Concurrency Test
        logger.info("Running multi-region concurrency benchmark")
        benchmark_results["multi_region_concurrency"] = (
            await self._benchmark_multi_region_concurrency(regions, concurrent_requests)
        )

        # 3. Sustained Load Test
        logger.info("Running sustained load benchmark")
        benchmark_results["sustained_load"] = await self._benchmark_sustained_load(
            test_ip_addresses, regions, duration_seconds, concurrent_requests
        )

        # 4. Error Recovery Test
        logger.info("Running error recovery benchmark")
        benchmark_results["error_recovery"] = await self._benchmark_error_recovery(regions)

        # 5. Memory Efficiency Test
        logger.info("Running memory efficiency benchmark")
        benchmark_results["memory_efficiency"] = await self._benchmark_memory_efficiency(
            test_ip_addresses, regions
        )

        # 6. CloudWAN Context Performance
        logger.info("Running CloudWAN context benchmark")
        benchmark_results["cloudwan_context"] = await self._benchmark_cloudwan_context_performance(
            regions
        )

        # Generate performance grades and recommendations
        for test_name, metrics in benchmark_results.items():
            metrics.performance_grade = self._calculate_performance_grade(metrics)
            metrics.recommendations = self._generate_recommendations(metrics)

        logger.info("Comprehensive benchmark completed")
        return benchmark_results

    async def _benchmark_ip_resolution_latency(
        self, test_ip_addresses: list[str], regions: list[str]
    ) -> BenchmarkMetrics:
        """Benchmark IP resolution latency."""
        start_time = time.time()
        latencies = []
        successful_ops = 0
        failed_ops = 0

        for ip_address in test_ip_addresses:
            try:
                op_start = time.time()
                result = await self.ip_resolution_engine.resolve_ip_address(
                    ip_address=ip_address,
                    regions=regions[:3],  # Limit regions for latency test
                    include_security_analysis=True,
                    include_cloudwan_context=True,
                )
                op_time = (time.time() - op_start) * 1000  # ms
                latencies.append(op_time)

                if result.success:
                    successful_ops += 1
                else:
                    failed_ops += 1

            except Exception as e:
                logger.warning(f"IP resolution failed for {ip_address}: {e}")
                failed_ops += 1

        return self._calculate_benchmark_metrics(
            benchmark_name="IP Resolution Latency",
            benchmark_type=BenchmarkType.LATENCY,
            duration_seconds=time.time() - start_time,
            total_operations=len(test_ip_addresses),
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            latencies=latencies,
        )

    async def _benchmark_multi_region_concurrency(
        self, regions: list[str], concurrent_requests: int
    ) -> BenchmarkMetrics:
        """Benchmark multi-region concurrent operations."""
        start_time = time.time()
        latencies = []
        successful_ops = 0
        failed_ops = 0

        async def test_operation(aws_manager: AWSClientManager, region: str) -> dict[str, Any]:
            """Test operation for multi-region benchmark."""
            # Simple EC2 describe operation
            ec2 = aws_manager.get_sync_client("ec2", region)
            response = ec2.describe_regions(RegionNames=[region])
            return {"regions": response.get("Regions", [])}

        # Run concurrent multi-region operations
        tasks = []
        for _ in range(concurrent_requests):
            task = self._time_multi_region_operation(
                operation_name="describe_regions_test",
                regions=regions,
                operation_func=test_operation,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                failed_ops += 1
            elif isinstance(result, tuple):
                latency_ms, success = result
                latencies.append(latency_ms)
                if success:
                    successful_ops += 1
                else:
                    failed_ops += 1

        return self._calculate_benchmark_metrics(
            benchmark_name="Multi-Region Concurrency",
            benchmark_type=BenchmarkType.CONCURRENCY,
            duration_seconds=time.time() - start_time,
            total_operations=concurrent_requests,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            latencies=latencies,
        )

    async def _benchmark_sustained_load(
        self,
        test_ip_addresses: list[str],
        regions: list[str],
        duration_seconds: float,
        concurrent_requests: int,
    ) -> BenchmarkMetrics:
        """Benchmark sustained load performance."""
        start_time = time.time()
        end_time = start_time + duration_seconds
        latencies = []
        successful_ops = 0
        failed_ops = 0

        # Create semaphore to control concurrency
        semaphore = anyio.Semaphore(concurrent_requests)

        async def sustained_operation():
            nonlocal successful_ops, failed_ops, latencies

            async with semaphore:
                ip_address = test_ip_addresses[successful_ops % len(test_ip_addresses)]
                try:
                    op_start = time.time()
                    result = await self.ip_resolution_engine.resolve_ip_address(
                        ip_address=ip_address,
                        regions=regions[:2],  # Limit regions for sustained load
                        include_security_analysis=False,  # Reduce complexity
                        include_cloudwan_context=False,
                    )
                    op_time = (time.time() - op_start) * 1000
                    latencies.append(op_time)

                    if result.success:
                        successful_ops += 1
                    else:
                        failed_ops += 1

                except Exception:
                    failed_ops += 1

        # Run sustained load
        tasks = []
        while time.time() < end_time:
            if len(tasks) < concurrent_requests:
                task = asyncio.create_task(sustained_operation())
                tasks.append(task)

            # Clean up completed tasks
            tasks = [t for t in tasks if not t.done()]

            await anyio.sleep(0.1)  # Small delay

        # Wait for remaining tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return self._calculate_benchmark_metrics(
            benchmark_name="Sustained Load",
            benchmark_type=BenchmarkType.THROUGHPUT,
            duration_seconds=time.time() - start_time,
            total_operations=successful_ops + failed_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            latencies=latencies,
        )

    async def _benchmark_error_recovery(self, regions: list[str]) -> BenchmarkMetrics:
        """Benchmark error recovery performance."""
        start_time = time.time()
        latencies = []
        successful_ops = 0
        failed_ops = 0

        # Test operations that will likely fail in some regions
        async def error_prone_operation(
            aws_manager: AWSClientManager, region: str
        ) -> dict[str, Any]:
            """Operation that may fail to test error recovery."""
            try:
                # Try to access a service that might not be available
                ecs = aws_manager.get_sync_client("ecs", region)
                response = ecs.list_clusters(maxResults=1)
                return {"clusters": response.get("clusterArns", [])}
            except Exception:
                # Simulate recovery by falling back to EC2
                ec2 = aws_manager.get_sync_client("ec2", region)
                response = ec2.describe_regions(RegionNames=[region])
                return {"regions": response.get("Regions", [])}

        # Run error recovery tests
        for region in regions:
            try:
                op_start = time.time()
                result = await self.multi_region_engine.execute_multi_region_operation(
                    operation_name="error_recovery_test",
                    regions=[region],
                    operation_func=error_prone_operation,
                    error_tolerance=0.8,  # High error tolerance
                )
                op_time = (time.time() - op_start) * 1000
                latencies.append(op_time)

                if result.successful_regions:
                    successful_ops += 1
                else:
                    failed_ops += 1

            except Exception:
                failed_ops += 1

        return self._calculate_benchmark_metrics(
            benchmark_name="Error Recovery",
            benchmark_type=BenchmarkType.ERROR_HANDLING,
            duration_seconds=time.time() - start_time,
            total_operations=len(regions),
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            latencies=latencies,
        )

    async def _benchmark_memory_efficiency(
        self, test_ip_addresses: list[str], regions: list[str]
    ) -> BenchmarkMetrics:
        """Benchmark memory usage efficiency."""
        import os

        import psutil

        start_time = time.time()
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        latencies = []
        successful_ops = 0
        failed_ops = 0

        # Run memory-intensive operations
        for ip_address in test_ip_addresses:
            for region in regions[:2]:  # Limit regions
                try:
                    op_start = time.time()
                    result = await self.ip_resolution_engine.resolve_ip_address(
                        ip_address=ip_address,
                        regions=[region],
                        include_security_analysis=True,
                        include_cloudwan_context=True,
                        enable_caching=False,  # Disable caching to test memory usage
                    )
                    op_time = (time.time() - op_start) * 1000
                    latencies.append(op_time)

                    if result.success:
                        successful_ops += 1
                    else:
                        failed_ops += 1

                except Exception:
                    failed_ops += 1

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = final_memory - initial_memory

        metrics = self._calculate_benchmark_metrics(
            benchmark_name="Memory Efficiency",
            benchmark_type=BenchmarkType.SCALABILITY,
            duration_seconds=time.time() - start_time,
            total_operations=len(test_ip_addresses) * len(regions[:2]),
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            latencies=latencies,
        )
        metrics.memory_usage_mb = memory_usage

        return metrics

    async def _benchmark_cloudwan_context_performance(self, regions: list[str]) -> BenchmarkMetrics:
        """Benchmark CloudWAN context resolution performance."""
        start_time = time.time()
        latencies = []
        successful_ops = 0
        failed_ops = 0

        # Test CloudWAN context resolution
        async def cloudwan_test_operation(
            aws_manager: AWSClientManager, region: str
        ) -> dict[str, Any]:
            """Test CloudWAN context resolution."""
            try:
                # Try to get global networks
                async with aws_manager.client_context("networkmanager", "us-west-2") as nm:
                    response = await nm.describe_global_networks(MaxResults=5)
                    return {"global_networks": response.get("GlobalNetworks", [])}
            except Exception:
                # Return empty result if CloudWAN is not available
                return {"global_networks": []}

        for region in regions[:3]:  # Limit regions for CloudWAN test
            try:
                op_start = time.time()
                result = await self.multi_region_engine.execute_multi_region_operation(
                    operation_name="cloudwan_context_test",
                    regions=[region],
                    operation_func=cloudwan_test_operation,
                )
                op_time = (time.time() - op_start) * 1000
                latencies.append(op_time)

                if result.successful_regions:
                    successful_ops += 1
                else:
                    failed_ops += 1

            except Exception:
                failed_ops += 1

        return self._calculate_benchmark_metrics(
            benchmark_name="CloudWAN Context Performance",
            benchmark_type=BenchmarkType.LATENCY,
            duration_seconds=time.time() - start_time,
            total_operations=len(regions[:3]),
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            latencies=latencies,
        )

    async def _time_multi_region_operation(
        self, operation_name: str, regions: list[str], operation_func: Callable
    ) -> tuple[float, bool]:
        """Time a multi-region operation."""
        start_time = time.time()
        try:
            result = await self.multi_region_engine.execute_multi_region_operation(
                operation_name=operation_name,
                regions=regions,
                operation_func=operation_func,
            )
            latency_ms = (time.time() - start_time) * 1000
            return latency_ms, len(result.successful_regions) > 0
        except Exception:
            latency_ms = (time.time() - start_time) * 1000
            return latency_ms, False

    def _calculate_benchmark_metrics(
        self,
        benchmark_name: str,
        benchmark_type: BenchmarkType,
        duration_seconds: float,
        total_operations: int,
        successful_operations: int,
        failed_operations: int,
        latencies: list[float],
    ) -> BenchmarkMetrics:
        """Calculate comprehensive benchmark metrics."""
        if not latencies:
            latencies = [0.0]  # Avoid division by zero

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p50_latency = statistics.median(sorted_latencies) if sorted_latencies else 0.0
        p95_latency = (
            sorted_latencies[int(0.95 * len(sorted_latencies))] if sorted_latencies else 0.0
        )
        p99_latency = (
            sorted_latencies[int(0.99 * len(sorted_latencies))] if sorted_latencies else 0.0
        )

        return BenchmarkMetrics(
            benchmark_name=benchmark_name,
            benchmark_type=benchmark_type,
            duration_seconds=duration_seconds,
            total_operations=total_operations,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            average_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_latency_ms=max(latencies) if latencies else 0.0,
            min_latency_ms=min(latencies) if latencies else 0.0,
            throughput_ops_per_second=(
                total_operations / duration_seconds if duration_seconds > 0 else 0.0
            ),
            error_rate=(failed_operations / total_operations if total_operations > 0 else 0.0),
            memory_usage_mb=0.0,  # Will be set by specific benchmarks
            cpu_usage_percent=0.0,  # Will be set by specific benchmarks
            raw_latencies=latencies,
        )

    def _calculate_performance_grade(self, metrics: BenchmarkMetrics) -> PerformanceGrade:
        """Calculate performance grade based on metrics."""
        score = 100.0  # Start with perfect score

        # Deduct points for high latency
        if metrics.benchmark_type == BenchmarkType.LATENCY:
            if metrics.p95_latency_ms > self.performance_targets["ip_resolution_ms"]:
                score -= 30
            elif metrics.p95_latency_ms > self.performance_targets["ip_resolution_ms"] * 0.75:
                score -= 15

        # Deduct points for high error rate
        if metrics.error_rate > self.performance_targets["error_rate_threshold"]:
            score -= 40
        elif metrics.error_rate > self.performance_targets["error_rate_threshold"] / 2:
            score -= 20

        # Deduct points for low throughput
        if (
            metrics.benchmark_type == BenchmarkType.THROUGHPUT
            and metrics.throughput_ops_per_second
            < self.performance_targets["throughput_ops_per_second"]
        ):
            score -= 25

        # Deduct points for high memory usage
        if metrics.memory_usage_mb > 500:  # MB
            score -= 15

        # Convert score to grade
        if score >= 95:
            return PerformanceGrade.EXCELLENT
        elif score >= 85:
            return PerformanceGrade.GOOD
        elif score >= 70:
            return PerformanceGrade.ACCEPTABLE
        elif score >= 60:
            return PerformanceGrade.NEEDS_IMPROVEMENT
        elif score >= 50:
            return PerformanceGrade.POOR
        else:
            return PerformanceGrade.FAILED

    def _generate_recommendations(self, metrics: BenchmarkMetrics) -> list[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Latency recommendations
        if metrics.p95_latency_ms > self.performance_targets["ip_resolution_ms"]:
            recommendations.append(
                f"High P95 latency ({metrics.p95_latency_ms:.0f}ms). "
                "Consider reducing concurrent regions or enabling caching."
            )

        # Error rate recommendations
        if metrics.error_rate > self.performance_targets["error_rate_threshold"]:
            recommendations.append(
                f"High error rate ({metrics.error_rate:.2%}). "
                "Check circuit breaker settings and retry configuration."
            )

        # Throughput recommendations
        if (
            metrics.benchmark_type == BenchmarkType.THROUGHPUT
            and metrics.throughput_ops_per_second
            < self.performance_targets["throughput_ops_per_second"]
        ):
            recommendations.append(
                f"Low throughput ({metrics.throughput_ops_per_second:.1f} ops/sec). "
                "Consider increasing concurrency limits or connection pooling."
            )

        # Memory recommendations
        if metrics.memory_usage_mb > 300:
            recommendations.append(
                f"High memory usage ({metrics.memory_usage_mb:.0f}MB). "
                "Consider implementing result streaming or reducing cache sizes."
            )

        # General recommendations based on benchmark type
        if metrics.benchmark_type == BenchmarkType.CONCURRENCY:
            recommendations.append(
                "For better concurrency performance, consider tuning max_concurrent_regions "
                "and implementing adaptive load balancing."
            )

        return recommendations

    def generate_optimization_recommendations(
        self, benchmark_results: dict[str, BenchmarkMetrics]
    ) -> list[OptimizationRecommendation]:
        """Generate detailed optimization recommendations based on benchmark results."""
        recommendations = []

        # Analyze IP resolution performance
        ip_metrics = benchmark_results.get("ip_resolution_latency")
        if ip_metrics and ip_metrics.p95_latency_ms > self.performance_targets["ip_resolution_ms"]:
            recommendations.append(
                OptimizationRecommendation(
                    category="IP Resolution",
                    priority=1,
                    description="IP resolution latency exceeds 2 second target",
                    expected_improvement="30-50% latency reduction",
                    implementation_effort="medium",
                    configuration_changes={
                        "max_concurrent_services": 6,
                        "cache_ttl_seconds": 600,
                        "dns_resolution_timeout": 1.0,
                    },
                )
            )

        # Analyze multi-region performance
        mr_metrics = benchmark_results.get("multi_region_concurrency")
        if mr_metrics and mr_metrics.error_rate > 0.1:
            recommendations.append(
                OptimizationRecommendation(
                    category="Multi-Region Processing",
                    priority=2,
                    description="High error rate in multi-region operations",
                    expected_improvement="50% error reduction",
                    implementation_effort="low",
                    configuration_changes={
                        "retry_attempts": 5,
                        "circuit_breaker_threshold": 3,
                        "max_concurrent_regions": 8,
                    },
                )
            )

        # Analyze memory efficiency
        mem_metrics = benchmark_results.get("memory_efficiency")
        if mem_metrics and mem_metrics.memory_usage_mb > 400:
            recommendations.append(
                OptimizationRecommendation(
                    category="Memory Optimization",
                    priority=3,
                    description="High memory usage during operations",
                    expected_improvement="40% memory reduction",
                    implementation_effort="high",
                    configuration_changes={
                        "cache_ttl_seconds": 180,
                        "max_cache_size": 500,
                        "enable_result_streaming": True,
                    },
                )
            )

        # Sort by priority
        recommendations.sort(key=lambda r: r.priority)
        return recommendations

    def generate_performance_report(
        self,
        benchmark_results: dict[str, BenchmarkMetrics],
        output_file: str | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "summary": {
                "total_benchmarks": len(benchmark_results),
                "excellent_grades": 0,
                "good_grades": 0,
                "acceptable_grades": 0,
                "needs_improvement_grades": 0,
                "poor_grades": 0,
                "failed_grades": 0,
            },
            "benchmarks": {},
            "optimization_recommendations": [],
            "performance_targets": self.performance_targets,
        }

        # Process benchmark results
        for test_name, metrics in benchmark_results.items():
            report["benchmarks"][test_name] = {
                "performance_grade": metrics.performance_grade.value,
                "duration_seconds": metrics.duration_seconds,
                "total_operations": metrics.total_operations,
                "success_rate": (
                    metrics.successful_operations / metrics.total_operations
                    if metrics.total_operations > 0
                    else 0
                ),
                "error_rate": metrics.error_rate,
                "average_latency_ms": metrics.average_latency_ms,
                "p95_latency_ms": metrics.p95_latency_ms,
                "throughput_ops_per_second": metrics.throughput_ops_per_second,
                "memory_usage_mb": metrics.memory_usage_mb,
                "recommendations": metrics.recommendations,
            }

            # Update summary
            grade_key = f"{metrics.performance_grade.value.lower().replace('+', '').replace(' ', '_')}_grades"
            if grade_key in report["summary"]:
                report["summary"][grade_key] += 1

        # Generate optimization recommendations
        recommendations = self.generate_optimization_recommendations(benchmark_results)
        report["optimization_recommendations"] = [
            {
                "category": rec.category,
                "priority": rec.priority,
                "description": rec.description,
                "expected_improvement": rec.expected_improvement,
                "implementation_effort": rec.implementation_effort,
                "configuration_changes": rec.configuration_changes,
            }
            for rec in recommendations
        ]

        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Performance report saved to {output_file}")

        return report
