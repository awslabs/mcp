"""
High-Performance Engine Benchmarking Suite.

This module provides comprehensive benchmarking and validation for high-performance engines
specifically designed to validate the <2 second IP resolution target for 90% of queries.

Based on Agent 1: Foundation Engine Architect specifications for performance validation.
"""

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import anyio

from ..aws.client_manager import AWSClientManager
from .high_performance_ip_resolver import (
    HighPerformanceIPResolver,
    ResolutionStrategy,
)
from .async_executor_bridge import AsyncExecutorBridge
from .multi_region_engine import MultiRegionProcessingEngine

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Individual benchmark test result."""

    test_name: str
    engine_type: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    execution_time_seconds: float

    # Performance metrics
    average_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float

    # Target achievement
    target_ms: float
    queries_under_target: int
    target_achievement_rate: float

    # Additional metrics
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    throughput_qps: float = 0.0

    # Resource utilization
    peak_memory_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # Test configuration
    concurrency_level: int = 1
    test_duration_seconds: float = 0.0
    regions_tested: List[str] = field(default_factory=list)

    # Detailed timing data
    response_times_ms: List[float] = field(default_factory=list)

    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_queries > 0:
            self.error_rate = self.failed_queries / self.total_queries
            self.target_achievement_rate = self.queries_under_target / self.total_queries

        if self.execution_time_seconds > 0:
            self.throughput_qps = self.total_queries / self.execution_time_seconds


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""

    report_id: str
    generated_at: datetime
    test_environment: Dict[str, Any]
    benchmark_results: List[BenchmarkResult] = field(default_factory=list)

    # Overall performance summary
    overall_target_achievement: float = 0.0
    best_performing_engine: Optional[str] = None
    worst_performing_engine: Optional[str] = None

    # Recommendations
    performance_grade: str = "F"  # A, B, C, D, F
    optimization_recommendations: List[str] = field(default_factory=list)
    configuration_recommendations: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate overall metrics and grades."""
        if self.benchmark_results:
            # Calculate overall target achievement
            total_queries = sum(r.total_queries for r in self.benchmark_results)
            total_under_target = sum(r.queries_under_target for r in self.benchmark_results)

            if total_queries > 0:
                self.overall_target_achievement = total_under_target / total_queries

            # Find best and worst performers
            if len(self.benchmark_results) > 1:
                best = max(self.benchmark_results, key=lambda r: r.target_achievement_rate)
                worst = min(self.benchmark_results, key=lambda r: r.target_achievement_rate)
                self.best_performing_engine = (
                    f"{best.engine_type} ({best.target_achievement_rate:.1%})"
                )
                self.worst_performing_engine = (
                    f"{worst.engine_type} ({worst.target_achievement_rate:.1%})"
                )

            # Assign performance grade
            self.performance_grade = self._calculate_grade()

    def _calculate_grade(self) -> str:
        """Calculate performance grade based on target achievement."""
        if self.overall_target_achievement >= 0.95:
            return "A"
        elif self.overall_target_achievement >= 0.90:
            return "B"
        elif self.overall_target_achievement >= 0.75:
            return "C"
        elif self.overall_target_achievement >= 0.50:
            return "D"
        else:
            return "F"


class HighPerformanceBenchmarkSuite:
    """
    Comprehensive benchmarking suite for high-performance engines.

    Validates <2 second IP resolution target and provides detailed performance analysis.
    """

    def __init__(
        self,
        aws_manager: AWSClientManager,
        performance_target_ms: float = 2000.0,
        test_ip_pool: Optional[List[str]] = None,
        test_regions: Optional[List[str]] = None,
    ):
        """
        Initialize High-Performance Benchmark Suite.

        Args:
            aws_manager: AWS client manager instance
            performance_target_ms: Target response time in milliseconds (default: 2000ms)
            test_ip_pool: Optional list of test IPs to use
            test_regions: Optional list of regions to test
        """
        self.aws_manager = aws_manager
        self.performance_target_ms = performance_target_ms
        self.test_ip_pool = test_ip_pool or self._generate_test_ip_pool()
        self.test_regions = test_regions or ["us-east-1", "us-west-2", "eu-west-1"]

        self.logger = logging.getLogger(__name__)

        # Initialize engines for testing
        self.high_perf_resolver = None
        self.async_bridge = None
        self.multi_region_engine = None

        self.logger.info(
            f"HighPerformanceBenchmarkSuite initialized - "
            f"target: {performance_target_ms}ms, test_ips: {len(self.test_ip_pool)}, "
            f"regions: {len(self.test_regions)}"
        )

    async def run_comprehensive_benchmark(
        self,
        include_stress_tests: bool = True,
        include_concurrency_tests: bool = True,
        include_cache_tests: bool = True,
        test_duration_minutes: float = 5.0,
    ) -> PerformanceReport:
        """
        Run comprehensive benchmark suite.

        Args:
            include_stress_tests: Include stress testing scenarios
            include_concurrency_tests: Include concurrency testing
            include_cache_tests: Include cache performance testing
            test_duration_minutes: Duration for sustained load tests

        Returns:
            Comprehensive performance report
        """
        self.logger.info("Starting comprehensive high-performance benchmark suite")

        report = PerformanceReport(
            report_id=f"hp-benchmark-{int(time.time())}",
            generated_at=datetime.now(),
            test_environment=self._get_test_environment(),
        )

        try:
            # Initialize engines
            await self._initialize_engines()

            # Core performance tests
            self.logger.info("Running core performance tests...")
            core_results = await self._run_core_performance_tests()
            report.benchmark_results.extend(core_results)

            # Target validation tests
            self.logger.info("Running target validation tests...")
            target_results = await self._run_target_validation_tests()
            report.benchmark_results.extend(target_results)

            # Concurrency tests
            if include_concurrency_tests:
                self.logger.info("Running concurrency tests...")
                concurrency_results = await self._run_concurrency_tests()
                report.benchmark_results.extend(concurrency_results)

            # Cache performance tests
            if include_cache_tests:
                self.logger.info("Running cache performance tests...")
                cache_results = await self._run_cache_performance_tests()
                report.benchmark_results.extend(cache_results)

            # Stress tests
            if include_stress_tests:
                self.logger.info("Running stress tests...")
                stress_results = await self._run_stress_tests(test_duration_minutes)
                report.benchmark_results.extend(stress_results)

            # Generate recommendations
            report.optimization_recommendations = self._generate_optimization_recommendations(
                report
            )
            report.configuration_recommendations = self._generate_configuration_recommendations(
                report
            )

            self.logger.info(
                f"Benchmark complete - Grade: {report.performance_grade}, "
                f"Target Achievement: {report.overall_target_achievement:.1%}"
            )

            return report

        except Exception as e:
            self.logger.error(f"Benchmark suite failed: {e}")
            raise

    async def validate_two_second_target(
        self, sample_size: int = 100, target_achievement_threshold: float = 0.90
    ) -> Dict[str, Any]:
        """
        Validate the <2 second target achievement specifically.

        Args:
            sample_size: Number of queries to test
            target_achievement_threshold: Required achievement rate (default: 90%)

        Returns:
            Validation results with pass/fail status
        """
        self.logger.info(f"Validating <2s target with {sample_size} queries")

        if not self.high_perf_resolver:
            await self._initialize_engines()

        # Run targeted test
        test_ips = self.test_ip_pool[:sample_size]
        results = []

        start_time = time.time()

        for ip in test_ips:
            query_start = time.time()
            try:
                result = await self.high_perf_resolver.resolve_ip_fast(
                    ip_address=ip,
                    regions=self.test_regions[:2],  # Limit for speed
                    enable_early_termination=True,
                )
                query_time_ms = (time.time() - query_start) * 1000
                results.append(query_time_ms)

            except Exception as e:
                self.logger.warning(f"Query failed for {ip}: {e}")
                results.append(self.performance_target_ms * 2)  # Penalty for failure

        execution_time = time.time() - start_time

        # Calculate metrics
        under_target = sum(1 for t in results if t <= self.performance_target_ms)
        achievement_rate = under_target / len(results) if results else 0.0

        validation_result = {
            "target_ms": self.performance_target_ms,
            "sample_size": len(results),
            "queries_under_target": under_target,
            "target_achievement_rate": achievement_rate,
            "required_threshold": target_achievement_threshold,
            "validation_passed": achievement_rate >= target_achievement_threshold,
            "average_response_time_ms": statistics.mean(results) if results else 0,
            "median_response_time_ms": statistics.median(results) if results else 0,
            "p95_response_time_ms": self._calculate_percentile(results, 0.95),
            "p99_response_time_ms": self._calculate_percentile(results, 0.99),
            "total_execution_time_seconds": execution_time,
            "throughput_qps": (len(results) / execution_time if execution_time > 0 else 0),
            "detailed_times": results,
        }

        status = "PASSED" if validation_result["validation_passed"] else "FAILED"
        self.logger.info(
            f"Target validation {status} - Achievement: {achievement_rate:.1%} "
            f"(required: {target_achievement_threshold:.1%})"
        )

        return validation_result

    async def _initialize_engines(self):
        """Initialize all engines for testing."""
        self.logger.debug("Initializing engines for benchmarking")

        # High-performance IP resolver
        self.high_perf_resolver = HighPerformanceIPResolver(
            aws_manager=self.aws_manager,
            performance_target_ms=self.performance_target_ms,
            enable_aggressive_caching=True,  # Test with caching enabled
            dns_timeout_seconds=1.0,
        )

        # legacy Legacy Adapter
        self.async_bridge = AsyncExecutorBridge(
            aws_manager=self.aws_manager, max_workers=10, task_timeout_seconds=30.0
        )

        # Multi-region engine
        self.multi_region_engine = MultiRegionProcessingEngine(
            aws_manager=self.aws_manager,
            max_concurrent_regions=5,
            performance_target_ms=self.performance_target_ms,
        )

    async def _run_core_performance_tests(self) -> List[BenchmarkResult]:
        """Run core performance tests for each engine."""
        results = []

        # Test high-performance IP resolver
        hp_result = await self._benchmark_high_performance_resolver(
            test_name="Core Performance - HighPerformanceIPResolver", sample_size=50
        )
        results.append(hp_result)

        # Test legacy legacy adapter
        iag_result = await self._benchmark_iag_legacy_adapter(
            test_name="Core Performance - AsyncExecutorBridge",
            sample_size=20,  # Smaller sample for legacy adapter
        )
        results.append(iag_result)

        return results

    async def _run_target_validation_tests(self) -> List[BenchmarkResult]:
        """Run specific target validation tests."""
        results = []

        # Test with different strategies
        for strategy in [ResolutionStrategy.FAST_PATH, ResolutionStrategy.STANDARD]:
            result = await self._benchmark_resolution_strategy(
                test_name=f"Target Validation - {strategy.value}",
                strategy=strategy,
                sample_size=75,
            )
            results.append(result)

        return results

    async def _run_concurrency_tests(self) -> List[BenchmarkResult]:
        """Run concurrency performance tests."""
        results = []

        # Test different concurrency levels
        for concurrency in [1, 5, 10, 20]:
            result = await self._benchmark_concurrent_resolution(
                test_name=f"Concurrency Test - {concurrency} concurrent",
                concurrency_level=concurrency,
                queries_per_worker=10,
            )
            results.append(result)

        return results

    async def _run_cache_performance_tests(self) -> List[BenchmarkResult]:
        """Run cache performance tests."""
        results = []

        # Test cache hit performance
        cache_result = await self._benchmark_cache_performance(
            test_name="Cache Performance Test", sample_size=50
        )
        results.append(cache_result)

        return results

    async def _run_stress_tests(self, duration_minutes: float) -> List[BenchmarkResult]:
        """Run sustained stress tests."""
        results = []

        # Sustained load test
        stress_result = await self._benchmark_sustained_load(
            test_name="Sustained Load Test",
            duration_minutes=duration_minutes,
            target_qps=10,
        )
        results.append(stress_result)

        return results

    async def _benchmark_high_performance_resolver(
        self, test_name: str, sample_size: int
    ) -> BenchmarkResult:
        """Benchmark the high-performance IP resolver."""
        self.logger.debug(f"Running {test_name} with {sample_size} queries")

        test_ips = self.test_ip_pool[:sample_size]
        response_times = []
        successful_queries = 0
        failed_queries = 0

        start_time = time.time()

        for ip in test_ips:
            query_start = time.time()
            try:
                result = await self.high_perf_resolver.resolve_ip_fast(
                    ip_address=ip,
                    regions=self.test_regions[:3],
                    enable_early_termination=True,
                )

                query_time_ms = (time.time() - query_start) * 1000
                response_times.append(query_time_ms)

                if result.success:
                    successful_queries += 1
                else:
                    failed_queries += 1

            except Exception as e:
                self.logger.debug(f"Query failed for {ip}: {e}")
                failed_queries += 1
                response_times.append(self.performance_target_ms * 2)  # Penalty

        execution_time = time.time() - start_time

        # Get cache metrics
        cache_metrics = self.high_perf_resolver.get_performance_metrics()

        # Calculate metrics
        under_target = sum(1 for t in response_times if t <= self.performance_target_ms)

        return BenchmarkResult(
            test_name=test_name,
            engine_type="HighPerformanceIPResolver",
            total_queries=len(test_ips),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            execution_time_seconds=execution_time,
            average_response_time_ms=(statistics.mean(response_times) if response_times else 0),
            median_response_time_ms=(statistics.median(response_times) if response_times else 0),
            p95_response_time_ms=self._calculate_percentile(response_times, 0.95),
            p99_response_time_ms=self._calculate_percentile(response_times, 0.99),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            target_ms=self.performance_target_ms,
            queries_under_target=under_target,
            cache_hit_rate=cache_metrics.get("cache_hit_rate", 0.0),
            concurrency_level=1,
            test_duration_seconds=execution_time,
            regions_tested=self.test_regions[:3],
            response_times_ms=response_times,
        )

    async def _benchmark_iag_legacy_adapter(
        self, test_name: str, sample_size: int
    ) -> BenchmarkResult:
        """Benchmark the legacy legacy adapter."""
        self.logger.debug(f"Running {test_name} with {sample_size} queries")

        # Use limited regions for legacy testing
        test_regions = self.test_regions[:2]

        start_time = time.time()

        # Test IP finder operation
        test_ip = self.test_ip_pool[0] if self.test_ip_pool else "10.0.1.100"
        batch_result = await self.async_bridge.execute_legacy_ip_finder(
            target_ip=test_ip, regions=test_regions
        )

        execution_time = time.time() - start_time

        # Calculate response times based on individual task results
        response_times = []
        for task_result in batch_result.results:
            response_times.append(task_result.execution_time_seconds * 1000)  # Convert to ms

        under_target = sum(1 for t in response_times if t <= self.performance_target_ms)

        return BenchmarkResult(
            test_name=test_name,
            engine_type="AsyncExecutorBridge",
            total_queries=batch_result.total_tasks,
            successful_queries=batch_result.completed_tasks,
            failed_queries=batch_result.failed_tasks,
            execution_time_seconds=execution_time,
            average_response_time_ms=(statistics.mean(response_times) if response_times else 0),
            median_response_time_ms=(statistics.median(response_times) if response_times else 0),
            p95_response_time_ms=self._calculate_percentile(response_times, 0.95),
            p99_response_time_ms=self._calculate_percentile(response_times, 0.99),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            target_ms=self.performance_target_ms,
            queries_under_target=under_target,
            concurrency_level=len(test_regions),
            test_duration_seconds=execution_time,
            regions_tested=test_regions,
            response_times_ms=response_times,
        )

    async def _benchmark_resolution_strategy(
        self, test_name: str, strategy: ResolutionStrategy, sample_size: int
    ) -> BenchmarkResult:
        """Benchmark specific resolution strategy."""
        self.logger.debug(f"Running {test_name} with strategy {strategy}")

        test_ips = self.test_ip_pool[:sample_size]
        response_times = []
        successful_queries = 0
        failed_queries = 0

        start_time = time.time()

        for ip in test_ips:
            query_start = time.time()
            try:
                result = await self.high_perf_resolver.resolve_ip_fast(
                    ip_address=ip, regions=self.test_regions[:2], strategy=strategy
                )

                query_time_ms = (time.time() - query_start) * 1000
                response_times.append(query_time_ms)

                if result.success:
                    successful_queries += 1
                else:
                    failed_queries += 1

            except Exception:
                failed_queries += 1
                response_times.append(self.performance_target_ms * 2)

        execution_time = time.time() - start_time
        under_target = sum(1 for t in response_times if t <= self.performance_target_ms)

        return BenchmarkResult(
            test_name=test_name,
            engine_type=f"HighPerformanceIPResolver-{strategy.value}",
            total_queries=len(test_ips),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            execution_time_seconds=execution_time,
            average_response_time_ms=(statistics.mean(response_times) if response_times else 0),
            median_response_time_ms=(statistics.median(response_times) if response_times else 0),
            p95_response_time_ms=self._calculate_percentile(response_times, 0.95),
            p99_response_time_ms=self._calculate_percentile(response_times, 0.99),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            target_ms=self.performance_target_ms,
            queries_under_target=under_target,
            concurrency_level=1,
            test_duration_seconds=execution_time,
            regions_tested=self.test_regions[:2],
            response_times_ms=response_times,
        )

    async def _benchmark_concurrent_resolution(
        self, test_name: str, concurrency_level: int, queries_per_worker: int
    ) -> BenchmarkResult:
        """Benchmark concurrent resolution performance."""
        self.logger.debug(f"Running {test_name} with {concurrency_level} workers")

        total_queries = concurrency_level * queries_per_worker
        test_ips = (self.test_ip_pool * ((total_queries // len(self.test_ip_pool)) + 1))[
            :total_queries
        ]

        response_times = []
        successful_queries = 0
        failed_queries = 0

        start_time = time.time()

        # Create concurrent tasks
        semaphore = anyio.Semaphore(concurrency_level)

        async def resolve_ip(ip: str) -> Tuple[bool, float]:
            async with semaphore:
                query_start = time.time()
                try:
                    result = await self.high_perf_resolver.resolve_ip_fast(
                        ip_address=ip, regions=self.test_regions[:2]
                    )
                    query_time_ms = (time.time() - query_start) * 1000
                    return result.success, query_time_ms
                except Exception:
                    query_time_ms = (time.time() - query_start) * 1000
                    return False, query_time_ms

        # Execute all queries concurrently
        tasks = [resolve_ip(ip) for ip in test_ips]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_time = time.time() - start_time

        # Process results
        for result in results:
            if isinstance(result, Exception):
                failed_queries += 1
                response_times.append(self.performance_target_ms * 2)
            else:
                success, query_time = result
                response_times.append(query_time)
                if success:
                    successful_queries += 1
                else:
                    failed_queries += 1

        under_target = sum(1 for t in response_times if t <= self.performance_target_ms)

        return BenchmarkResult(
            test_name=test_name,
            engine_type="HighPerformanceIPResolver-Concurrent",
            total_queries=total_queries,
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            execution_time_seconds=execution_time,
            average_response_time_ms=(statistics.mean(response_times) if response_times else 0),
            median_response_time_ms=(statistics.median(response_times) if response_times else 0),
            p95_response_time_ms=self._calculate_percentile(response_times, 0.95),
            p99_response_time_ms=self._calculate_percentile(response_times, 0.99),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            target_ms=self.performance_target_ms,
            queries_under_target=under_target,
            concurrency_level=concurrency_level,
            test_duration_seconds=execution_time,
            regions_tested=self.test_regions[:2],
            response_times_ms=response_times,
        )

    async def _benchmark_cache_performance(
        self, test_name: str, sample_size: int
    ) -> BenchmarkResult:
        """Benchmark cache performance with repeated queries."""
        self.logger.debug(f"Running {test_name} with cache testing")

        # Clear caches first
        self.high_perf_resolver.clear_caches()

        # Use smaller set of IPs for cache testing
        cache_test_ips = self.test_ip_pool[: sample_size // 4]

        # First pass - populate cache
        for ip in cache_test_ips:
            try:
                await self.high_perf_resolver.resolve_ip_fast(ip_address=ip)
            except Exception:
                pass

        # Second pass - test cache performance
        response_times = []
        successful_queries = 0
        failed_queries = 0

        start_time = time.time()

        # Query same IPs multiple times to test cache hits
        for _ in range(sample_size // len(cache_test_ips)):
            for ip in cache_test_ips:
                query_start = time.time()
                try:
                    result = await self.high_perf_resolver.resolve_ip_fast(ip_address=ip)
                    query_time_ms = (time.time() - query_start) * 1000
                    response_times.append(query_time_ms)

                    if result.success:
                        successful_queries += 1
                    else:
                        failed_queries += 1

                except Exception:
                    failed_queries += 1
                    response_times.append(self.performance_target_ms * 2)

        execution_time = time.time() - start_time

        # Get cache metrics
        cache_metrics = self.high_perf_resolver.get_performance_metrics()
        under_target = sum(1 for t in response_times if t <= self.performance_target_ms)

        return BenchmarkResult(
            test_name=test_name,
            engine_type="HighPerformanceIPResolver-Cache",
            total_queries=len(response_times),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            execution_time_seconds=execution_time,
            average_response_time_ms=(statistics.mean(response_times) if response_times else 0),
            median_response_time_ms=(statistics.median(response_times) if response_times else 0),
            p95_response_time_ms=self._calculate_percentile(response_times, 0.95),
            p99_response_time_ms=self._calculate_percentile(response_times, 0.99),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            target_ms=self.performance_target_ms,
            queries_under_target=under_target,
            cache_hit_rate=cache_metrics.get("cache_hit_rate", 0.0),
            concurrency_level=1,
            test_duration_seconds=execution_time,
            regions_tested=self.test_regions[:2],
            response_times_ms=response_times,
        )

    async def _benchmark_sustained_load(
        self, test_name: str, duration_minutes: float, target_qps: int
    ) -> BenchmarkResult:
        """Benchmark sustained load performance."""
        self.logger.debug(f"Running {test_name} for {duration_minutes} minutes at {target_qps} QPS")

        duration_seconds = duration_minutes * 60
        interval_seconds = 1.0 / target_qps

        response_times = []
        successful_queries = 0
        failed_queries = 0

        start_time = time.time()
        end_time = start_time + duration_seconds

        ip_index = 0

        while time.time() < end_time:
            query_start = time.time()

            # Get next IP (cycle through available IPs)
            test_ip = self.test_ip_pool[ip_index % len(self.test_ip_pool)]
            ip_index += 1

            try:
                result = await self.high_perf_resolver.resolve_ip_fast(
                    ip_address=test_ip, regions=self.test_regions[:2]
                )

                query_time_ms = (time.time() - query_start) * 1000
                response_times.append(query_time_ms)

                if result.success:
                    successful_queries += 1
                else:
                    failed_queries += 1

            except Exception:
                failed_queries += 1
                response_times.append(self.performance_target_ms * 2)

            # Wait for next query to maintain target QPS
            elapsed = time.time() - query_start
            if elapsed < interval_seconds:
                await asyncio.sleep(interval_seconds - elapsed)

        execution_time = time.time() - start_time
        under_target = sum(1 for t in response_times if t <= self.performance_target_ms)

        return BenchmarkResult(
            test_name=test_name,
            engine_type="HighPerformanceIPResolver-Sustained",
            total_queries=len(response_times),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            execution_time_seconds=execution_time,
            average_response_time_ms=(statistics.mean(response_times) if response_times else 0),
            median_response_time_ms=(statistics.median(response_times) if response_times else 0),
            p95_response_time_ms=self._calculate_percentile(response_times, 0.95),
            p99_response_time_ms=self._calculate_percentile(response_times, 0.99),
            min_response_time_ms=min(response_times) if response_times else 0,
            max_response_time_ms=max(response_times) if response_times else 0,
            target_ms=self.performance_target_ms,
            queries_under_target=under_target,
            concurrency_level=1,
            test_duration_seconds=execution_time,
            regions_tested=self.test_regions[:2],
            response_times_ms=response_times,
        )

    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(percentile * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]

    def _generate_test_ip_pool(self) -> List[str]:
        """Generate pool of test IP addresses."""
        test_ips = []

        # Private IP ranges for testing
        private_ranges = [
            "10.0.1.{}",
            "10.0.2.{}",
            "10.1.1.{}",
            "172.16.1.{}",
            "172.16.2.{}",
            "192.168.1.{}",
            "192.168.10.{}",
        ]

        for range_template in private_ranges:
            for i in range(100, 120):  # Generate 20 IPs per range
                test_ips.append(range_template.format(i))

        # Add some public IPs for DNS testing
        public_ips = [
            "8.8.8.8",
            "8.8.4.4",
            "1.1.1.1",
            "1.0.0.1",
            "208.67.222.222",
            "208.67.220.220",
        ]
        test_ips.extend(public_ips)

        # Add some hostnames for DNS resolution testing
        hostnames = [
            "google.com",
            "amazon.com",
            "microsoft.com",
            "example.com",
            "cloudflare.com",
            "github.com",
        ]
        test_ips.extend(hostnames)

        return test_ips

    def _get_test_environment(self) -> Dict[str, Any]:
        """Get test environment information."""
        return {
            "performance_target_ms": self.performance_target_ms,
            "test_ip_pool_size": len(self.test_ip_pool),
            "test_regions": self.test_regions,
            "aws_profile": getattr(self.aws_manager, "profile", "default"),
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_optimization_recommendations(self, report: PerformanceReport) -> List[str]:
        """Generate optimization recommendations based on results."""
        recommendations = []

        if report.overall_target_achievement < 0.90:
            recommendations.append(
                "Target achievement below 90% - consider increasing cache TTL and DNS timeout"
            )

        # Check for high latency engines
        high_latency_engines = [
            r
            for r in report.benchmark_results
            if r.average_response_time_ms > self.performance_target_ms
        ]

        if high_latency_engines:
            recommendations.append(
                f"High latency detected in {len(high_latency_engines)} tests - "
                "consider reducing max_regions and enabling early termination"
            )

        # Check cache performance
        cache_tests = [r for r in report.benchmark_results if "Cache" in r.engine_type]
        if cache_tests and cache_tests[0].cache_hit_rate < 0.5:
            recommendations.append("Low cache hit rate - consider increasing cache size and TTL")

        # Check concurrency performance
        concurrent_tests = [r for r in report.benchmark_results if "Concurrent" in r.engine_type]
        if concurrent_tests:
            degradation = any(
                r.average_response_time_ms > self.performance_target_ms * 1.5
                for r in concurrent_tests
            )
            if degradation:
                recommendations.append(
                    "Performance degradation under concurrency - "
                    "consider connection pool tuning and service prioritization"
                )

        return recommendations

    def _generate_configuration_recommendations(self, report: PerformanceReport) -> List[str]:
        """Generate configuration recommendations."""
        recommendations = []

        if report.performance_grade in ["C", "D", "F"]:
            recommendations.extend(
                [
                    "Consider reducing max_concurrent_services from 4 to 2",
                    "Enable aggressive DNS caching with 600s TTL",
                    "Limit regions to 2-3 for optimal performance",
                    "Use FAST_PATH strategy for public IPs",
                    "Enable early termination for all queries",
                ]
            )

        return recommendations


def format_performance_report(report: PerformanceReport) -> str:
    """Format performance report for display."""
    lines = []
    lines.append("# High-Performance Engine Benchmark Report")
    lines.append(f"**Report ID**: {report.report_id}")
    lines.append(f"**Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Performance Grade**: {report.performance_grade}")
    lines.append(f"**Target Achievement**: {report.overall_target_achievement:.1%}")
    lines.append("")

    # Summary table
    lines.append("## Performance Summary")
    lines.append("| Test | Engine | Queries | Success Rate | Avg Time (ms) | Target Achievement |")
    lines.append("|------|--------|---------|--------------|---------------|-------------------|")

    for result in report.benchmark_results:
        success_rate = (
            (result.successful_queries / result.total_queries) * 100
            if result.total_queries > 0
            else 0
        )
        lines.append(
            f"| {result.test_name} | {result.engine_type} | {result.total_queries} | "
            f"{success_rate:.1f}% | {result.average_response_time_ms:.0f} | "
            f"{result.target_achievement_rate:.1%} |"
        )

    lines.append("")

    # Recommendations
    if report.optimization_recommendations:
        lines.append("## Optimization Recommendations")
        for rec in report.optimization_recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    if report.configuration_recommendations:
        lines.append("## Configuration Recommendations")
        for rec in report.configuration_recommendations:
            lines.append(f"- {rec}")

    return "\n".join(lines)
