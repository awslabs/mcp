"""
Multi-Region Concurrent Processing Engine.

This engine provides async/await patterns adapted from legacy ThreadPoolExecutor code,
implementing region-aware error handling with graceful service degradation.
Designed for 5+ concurrent regions with error isolation and <2 second response times.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

import anyio
from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientError, AWSClientManager
from ..utils.aws_operations import AWSOperationError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RegionHealthStatus(Enum):
    """Health status for regions."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class RegionExecutionResult:
    """Result from a single region execution."""

    region: str
    success: bool
    data: Any = None
    error: str | None = None
    error_code: str | None = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    health_status: RegionHealthStatus = RegionHealthStatus.UNKNOWN


@dataclass
class MultiRegionResult:
    """Aggregated result from multi-region operation."""

    operation_name: str
    total_regions: int
    successful_regions: list[str] = field(default_factory=list)
    failed_regions: list[str] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    total_execution_time_ms: float = 0.0
    performance_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegionLoadBalancer:
    """Load balancer for region selection and health management."""

    region_health: dict[str, RegionHealthStatus] = field(default_factory=dict)
    region_latencies: dict[str, list[float]] = field(default_factory=dict)
    region_error_counts: dict[str, int] = field(default_factory=dict)
    max_latency_samples: int = 10
    health_check_interval: float = 300.0  # 5 minutes
    last_health_check: dict[str, float] = field(default_factory=dict)


class MultiRegionProcessingEngine:
    """
    High-performance multi-region concurrent processing engine.

    Features:
    - Async/await patterns adapted from ThreadPoolExecutor legacy code
    - Region-aware error handling with graceful service degradation
    - Intelligent load balancing and region health monitoring
    - Performance optimization with adaptive concurrency
    - Error isolation preventing cascade failures
    - Result caching with configurable TTL
    """

    def __init__(
        self,
        aws_manager: AWSClientManager,
        max_concurrent_regions: int = 10,
        default_timeout_seconds: int = 30,
        retry_attempts: int = 3,
        circuit_breaker_threshold: int = 5,
        enable_region_health_monitoring: bool = True,
        performance_target_ms: float = 2000.0,
    ):
        """
        Initialize Multi-Region Processing Engine.

        Args:
            aws_manager: AWS client manager instance
            max_concurrent_regions: Maximum concurrent region operations
            default_timeout_seconds: Default timeout for operations
            retry_attempts: Number of retry attempts for failed operations
            circuit_breaker_threshold: Error threshold for circuit breaker
            enable_region_health_monitoring: Enable health monitoring
            performance_target_ms: Target performance in milliseconds
        """
        self.aws_manager = aws_manager
        self.max_concurrent_regions = max_concurrent_regions
        self.default_timeout_seconds = default_timeout_seconds
        self.retry_attempts = retry_attempts
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.enable_region_health_monitoring = enable_region_health_monitoring
        self.performance_target_ms = performance_target_ms

        # Initialize load balancer and health monitoring
        self.load_balancer = RegionLoadBalancer()
        self._execution_cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl: float = 300.0  # 5 minutes default

        logger.info(
            f"MultiRegionProcessingEngine initialized - "
            f"max_concurrent_regions: {max_concurrent_regions}, "
            f"performance_target: {performance_target_ms}ms"
        )

    async def execute_multi_region_operation(
        self,
        operation_name: str,
        regions: list[str],
        operation_func: Callable,
        operation_args: dict[str, Any] = None,
        timeout_seconds: int | None = None,
        enable_caching: bool = True,
        cache_ttl: float | None = None,
        priority_regions: list[str] | None = None,
        error_tolerance: float = 0.3,  # Allow 30% failures
    ) -> MultiRegionResult:
        """
        Execute operation across multiple regions with advanced error handling.

        Args:
            operation_name: Name of the operation for logging and metrics
            regions: List of regions to execute operation in
            operation_func: Async function to execute (takes aws_manager, region, **args)
            operation_args: Arguments to pass to operation function
            timeout_seconds: Operation timeout
            enable_caching: Enable result caching
            cache_ttl: Cache TTL in seconds
            priority_regions: Regions to prioritize (execute first)
            error_tolerance: Fraction of regions that can fail (0.0-1.0)

        Returns:
            MultiRegionResult with aggregated results and metrics
        """
        start_time = time.time()
        operation_args = operation_args or {}
        timeout_seconds = timeout_seconds or self.default_timeout_seconds
        cache_ttl = cache_ttl or self._cache_ttl

        logger.info(
            f"Starting multi-region operation '{operation_name}' " f"across {len(regions)} regions"
        )

        # Check cache first
        if enable_caching:
            cache_key = self._generate_cache_key(operation_name, regions, operation_args)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for operation '{operation_name}'")
                return cached_result

        # Filter and prioritize regions based on health
        if self.enable_region_health_monitoring:
            regions = await self._filter_healthy_regions(regions)

        # Prioritize regions if specified
        if priority_regions:
            ordered_regions = []
            priority_set = set(priority_regions)
            # Add priority regions first
            for region in regions:
                if region in priority_set:
                    ordered_regions.append(region)
            # Add remaining regions
            for region in regions:
                if region not in priority_set:
                    ordered_regions.append(region)
            regions = ordered_regions

        # Execute operations with controlled concurrency
        semaphore = anyio.Semaphore(min(self.max_concurrent_regions, len(regions)))
        region_tasks = []

        for region in regions:
            task = self._execute_region_operation_with_semaphore(
                semaphore=semaphore,
                operation_name=operation_name,
                region=region,
                operation_func=operation_func,
                operation_args=operation_args,
                timeout_seconds=timeout_seconds,
            )
            region_tasks.append(task)

        # Execute all tasks concurrently with anyio
        region_results = []

        async def execute_all_tasks():
            # Use asyncio.gather for now since we have asyncio tasks
            nonlocal region_results
            region_results = await asyncio.gather(*region_tasks, return_exceptions=True)

        await execute_all_tasks()

        # Process results and build response
        result = await self._process_region_results(
            operation_name=operation_name,
            regions=regions,
            region_results=region_results,
            error_tolerance=error_tolerance,
            total_execution_time_ms=(time.time() - start_time) * 1000,
        )

        # Update region health metrics
        if self.enable_region_health_monitoring:
            await self._update_region_health_metrics(region_results)

        # Cache successful results
        if enable_caching and result.successful_regions:
            cache_key = self._generate_cache_key(operation_name, regions, operation_args)
            self._cache_result(cache_key, result, cache_ttl)

        logger.info(
            f"Multi-region operation '{operation_name}' completed - "
            f"successful: {len(result.successful_regions)}, "
            f"failed: {len(result.failed_regions)}, "
            f"time: {result.total_execution_time_ms:.0f}ms"
        )

        return result

    async def _execute_region_operation_with_semaphore(
        self,
        semaphore: anyio.Semaphore,
        operation_name: str,
        region: str,
        operation_func: Callable,
        operation_args: dict[str, Any],
        timeout_seconds: int,
    ) -> RegionExecutionResult:
        """Execute operation in a single region with semaphore control."""
        async with semaphore:
            return await self._execute_region_operation(
                operation_name=operation_name,
                region=region,
                operation_func=operation_func,
                operation_args=operation_args,
                timeout_seconds=timeout_seconds,
            )

    async def _execute_region_operation(
        self,
        operation_name: str,
        region: str,
        operation_func: Callable,
        operation_args: dict[str, Any],
        timeout_seconds: int,
    ) -> RegionExecutionResult:
        """Execute operation in a single region with retries and error handling."""
        start_time = time.time()
        retry_count = 0
        last_error = None

        # Check circuit breaker
        if self._is_circuit_breaker_open(region):
            return RegionExecutionResult(
                region=region,
                success=False,
                error="Circuit breaker open - too many recent failures",
                error_code="CIRCUIT_BREAKER_OPEN",
                execution_time_ms=(time.time() - start_time) * 1000,
                health_status=RegionHealthStatus.FAILED,
            )

        for attempt in range(self.retry_attempts + 1):
            try:
                # Execute with timeout
                with anyio.move_on_after(timeout_seconds) as cancel_scope:
                    result_data = await operation_func(self.aws_manager, region, **operation_args)

                if cancel_scope.cancelled_caught:
                    raise AWSOperationError(f"Operation timed out after {timeout_seconds} seconds")

                # Success path
                execution_time_ms = (time.time() - start_time) * 1000
                self._record_region_success(region, execution_time_ms)

                return RegionExecutionResult(
                    region=region,
                    success=True,
                    data=result_data,
                    execution_time_ms=execution_time_ms,
                    retry_count=retry_count,
                    health_status=RegionHealthStatus.HEALTHY,
                )

            except (ClientError, AWSClientError, AWSOperationError) as e:
                last_error = e
                retry_count += 1

                # Determine if we should retry
                if attempt < self.retry_attempts and self._should_retry_error(e):
                    backoff_time = min(2**attempt, 10)  # Exponential backoff, max 10s
                    logger.debug(
                        f"Retrying {operation_name} in {region} "
                        f"(attempt {attempt + 1}/{self.retry_attempts + 1}) "
                        f"after {backoff_time}s: {str(e)}"
                    )
                    await anyio.sleep(backoff_time)
                    continue
                else:
                    break

            except Exception as e:
                last_error = e
                logger.error(
                    f"Unexpected error in {operation_name} for region {region}: {str(e)}",
                    exc_info=True,
                )
                break

        # All retries failed
        execution_time_ms = (time.time() - start_time) * 1000
        error_code = self._extract_error_code(last_error)

        self._record_region_failure(region, error_code)

        return RegionExecutionResult(
            region=region,
            success=False,
            error=str(last_error),
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            retry_count=retry_count,
            health_status=RegionHealthStatus.FAILED,
        )

    async def _process_region_results(
        self,
        operation_name: str,
        regions: list[str],
        region_results: list[RegionExecutionResult | Exception],
        error_tolerance: float,
        total_execution_time_ms: float,
    ) -> MultiRegionResult:
        """Process and aggregate region results."""
        successful_regions = []
        failed_regions = []
        results = {}
        errors = {}
        performance_metrics = {
            "average_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "fastest_region": None,
            "slowest_region": None,
            "regions_within_target": 0,
        }

        valid_results = []
        latencies = []

        for i, result in enumerate(region_results):
            region = regions[i] if i < len(regions) else f"unknown-{i}"

            if isinstance(result, Exception):
                logger.error(f"Task failed for region {region}: {result}")
                failed_regions.append(region)
                errors[region] = str(result)
                continue

            if isinstance(result, RegionExecutionResult):
                valid_results.append(result)
                latencies.append(result.execution_time_ms)

                if result.success:
                    successful_regions.append(result.region)
                    results[result.region] = result.data
                else:
                    failed_regions.append(result.region)
                    errors[result.region] = result.error or "Unknown error"

        # Calculate performance metrics
        if latencies:
            performance_metrics["average_latency_ms"] = sum(latencies) / len(latencies)
            performance_metrics["p95_latency_ms"] = (
                sorted(latencies)[int(0.95 * len(latencies))] if latencies else 0
            )
            performance_metrics["fastest_region"] = (
                min(valid_results, key=lambda r: r.execution_time_ms).region
                if valid_results
                else None
            )
            performance_metrics["slowest_region"] = (
                max(valid_results, key=lambda r: r.execution_time_ms).region
                if valid_results
                else None
            )
            performance_metrics["regions_within_target"] = sum(
                1 for lat in latencies if lat <= self.performance_target_ms
            )

        # Check if we met error tolerance
        total_regions = len(regions)
        success_rate = len(successful_regions) / total_regions if total_regions > 0 else 0

        if success_rate < (1.0 - error_tolerance):
            logger.warning(
                f"Operation '{operation_name}' failed to meet error tolerance: "
                f"{success_rate:.2%} success rate < {(1.0 - error_tolerance):.2%} required"
            )

        return MultiRegionResult(
            operation_name=operation_name,
            total_regions=total_regions,
            successful_regions=successful_regions,
            failed_regions=failed_regions,
            results=results,
            errors=errors,
            total_execution_time_ms=total_execution_time_ms,
            performance_metrics=performance_metrics,
        )

    async def _filter_healthy_regions(self, regions: list[str]) -> list[str]:
        """Filter regions based on health status."""
        healthy_regions = []
        current_time = time.time()

        for region in regions:
            # Check if health check is needed
            last_check = self.load_balancer.last_health_check.get(region, 0)
            if current_time - last_check > self.load_balancer.health_check_interval:
                await self._perform_health_check(region)
                self.load_balancer.last_health_check[region] = current_time

            # Include healthy and degraded regions, exclude failed
            health_status = self.load_balancer.region_health.get(region, RegionHealthStatus.UNKNOWN)
            if health_status in [
                RegionHealthStatus.HEALTHY,
                RegionHealthStatus.DEGRADED,
                RegionHealthStatus.UNKNOWN,
            ]:
                healthy_regions.append(region)
            else:
                logger.warning(
                    f"Excluding region {region} due to health status: {health_status.value}"
                )

        return healthy_regions

    async def _perform_health_check(self, region: str) -> RegionHealthStatus:
        """Perform health check for a region."""
        try:
            # Simple health check: describe regions
            async with self.aws_manager.client_context("ec2", region) as ec2:
                await ec2.describe_regions(RegionNames=[region])

            self.load_balancer.region_health[region] = RegionHealthStatus.HEALTHY
            return RegionHealthStatus.HEALTHY

        except Exception as e:
            logger.warning(f"Health check failed for region {region}: {e}")
            self.load_balancer.region_health[region] = RegionHealthStatus.FAILED
            return RegionHealthStatus.FAILED

    async def _update_region_health_metrics(
        self, region_results: list[RegionExecutionResult | Exception]
    ):
        """Update region health metrics based on execution results."""
        for result in region_results:
            if isinstance(result, RegionExecutionResult):
                region = result.region

                # Update latency tracking
                if region not in self.load_balancer.region_latencies:
                    self.load_balancer.region_latencies[region] = []

                latencies = self.load_balancer.region_latencies[region]
                latencies.append(result.execution_time_ms)

                # Keep only recent samples
                if len(latencies) > self.load_balancer.max_latency_samples:
                    latencies.pop(0)

                # Update health status
                if result.success:
                    self.load_balancer.region_health[region] = RegionHealthStatus.HEALTHY
                    # Reset error count on success
                    self.load_balancer.region_error_counts[region] = 0
                else:
                    # Increment error count
                    error_count = self.load_balancer.region_error_counts.get(region, 0) + 1
                    self.load_balancer.region_error_counts[region] = error_count

                    # Update health status based on error count
                    if error_count >= self.circuit_breaker_threshold:
                        self.load_balancer.region_health[region] = RegionHealthStatus.FAILED
                    elif error_count >= self.circuit_breaker_threshold // 2:
                        self.load_balancer.region_health[region] = RegionHealthStatus.DEGRADED

    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried."""
        if isinstance(error, ClientError):
            error_code = error.response.get("Error", {}).get("Code", "")
            # Don't retry permission or resource not found errors
            non_retryable_codes = {
                "UnauthorizedOperation",
                "AccessDenied",
                "InvalidUserID.NotFound",
                "ResourceNotFoundException",
                "ValidationException",
            }
            return error_code not in non_retryable_codes

        return isinstance(error, AWSOperationError)

    def _extract_error_code(self, error: Exception) -> str:
        """Extract error code from exception."""
        if isinstance(error, ClientError):
            return error.response.get("Error", {}).get("Code", "ClientError")
        elif isinstance(error, AWSClientError):
            return "AWSClientError"
        elif isinstance(error, AWSOperationError):
            return "AWSOperationError"
        else:
            return type(error).__name__

    def _is_circuit_breaker_open(self, region: str) -> bool:
        """Check if circuit breaker is open for a region."""
        error_count = self.load_balancer.region_error_counts.get(region, 0)
        return error_count >= self.circuit_breaker_threshold

    def _record_region_success(self, region: str, execution_time_ms: float):
        """Record successful operation for region."""
        self.load_balancer.region_error_counts[region] = 0
        self.load_balancer.region_health[region] = RegionHealthStatus.HEALTHY

    def _record_region_failure(self, region: str, error_code: str):
        """Record failed operation for region."""
        error_count = self.load_balancer.region_error_counts.get(region, 0) + 1
        self.load_balancer.region_error_counts[region] = error_count

        if error_count >= self.circuit_breaker_threshold:
            self.load_balancer.region_health[region] = RegionHealthStatus.FAILED

    def _generate_cache_key(
        self, operation_name: str, regions: list[str], args: dict[str, Any]
    ) -> str:
        """Generate cache key for operation."""
        import hashlib
        import json

        key_data = {
            "operation": operation_name,
            "regions": sorted(regions),
            "args": args,
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def _get_cached_result(self, cache_key: str) -> MultiRegionResult | None:
        """Get cached result if still valid."""
        if cache_key in self._execution_cache:
            result, cached_time = self._execution_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return result
            else:
                # Remove expired cache entry
                del self._execution_cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: MultiRegionResult, ttl: float):
        """Cache operation result."""
        self._execution_cache[cache_key] = (result, time.time())

        # Simple cache cleanup - remove old entries
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, cached_time) in self._execution_cache.items()
            if current_time - cached_time > ttl
        ]
        for key in expired_keys:
            del self._execution_cache[key]

    def get_region_health_status(self) -> dict[str, dict[str, Any]]:
        """Get current region health status and metrics."""
        status = {}

        for region in self.aws_manager.get_supported_regions():
            health = self.load_balancer.region_health.get(region, RegionHealthStatus.UNKNOWN)
            error_count = self.load_balancer.region_error_counts.get(region, 0)
            latencies = self.load_balancer.region_latencies.get(region, [])

            status[region] = {
                "health_status": health.value,
                "error_count": error_count,
                "average_latency_ms": (sum(latencies) / len(latencies) if latencies else 0),
                "last_health_check": self.load_balancer.last_health_check.get(region),
                "circuit_breaker_open": self._is_circuit_breaker_open(region),
            }

        return status

    def clear_cache(self):
        """Clear the execution cache."""
        self._execution_cache.clear()
        logger.info("Multi-region processing engine cache cleared")

    def reset_region_health(self, region: str | None = None):
        """Reset region health metrics."""
        if region:
            regions_to_reset = [region]
        else:
            regions_to_reset = list(self.load_balancer.region_health.keys())

        for r in regions_to_reset:
            self.load_balancer.region_health[r] = RegionHealthStatus.UNKNOWN
            self.load_balancer.region_error_counts[r] = 0
            self.load_balancer.region_latencies[r] = []

        logger.info(f"Reset health metrics for regions: {regions_to_reset}")


# Alias for backward compatibility
MultiRegionEngine = MultiRegionProcessingEngine
