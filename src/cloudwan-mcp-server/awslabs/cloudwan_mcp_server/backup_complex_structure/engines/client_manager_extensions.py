"""
AWS Client Manager Extensions for Foundation Engines.

This module provides enhanced connection pooling, circuit breaker patterns,
and performance optimization specifically designed for the foundation engines.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import anyio
from botocore.exceptions import BotoCoreError, ClientError

from ..aws.client_manager import AWSClientManager

logger = logging.getLogger(__name__)


class ConnectionHealthStatus(Enum):
    """Connection health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CIRCUIT_OPEN = "circuit_open"
    FAILED = "failed"


@dataclass
class ConnectionMetrics:
    """Metrics for AWS service connections."""

    service: str
    region: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    last_request_time: float = 0.0
    error_rate: float = 0.0
    circuit_breaker_trips: int = 0
    health_status: ConnectionHealthStatus = ConnectionHealthStatus.HEALTHY


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0
    half_open_max_calls: int = 3
    min_requests_for_evaluation: int = 10


@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration."""

    max_pool_size: int = 50
    min_pool_size: int = 5
    connection_timeout_seconds: float = 30.0
    idle_timeout_seconds: float = 300.0
    max_retries: int = 3
    backoff_multiplier: float = 2.0


class CircuitBreaker:
    """Circuit breaker for AWS service connections."""

    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = ConnectionHealthStatus.HEALTHY
        self.half_open_attempts = 0
        self._lock = anyio.Lock()

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check circuit state
            if self.state == ConnectionHealthStatus.CIRCUIT_OPEN:
                if time.time() - self.last_failure_time > self.config.recovery_timeout_seconds:
                    self.state = ConnectionHealthStatus.DEGRADED  # Half-open
                    self.half_open_attempts = 0
                else:
                    raise Exception("Circuit breaker is OPEN")

            elif self.state == ConnectionHealthStatus.DEGRADED:
                if self.half_open_attempts >= self.config.half_open_max_calls:
                    raise Exception("Circuit breaker is HALF-OPEN - max attempts reached")

        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            if self.state == ConnectionHealthStatus.DEGRADED:
                self.half_open_attempts += 1
                if self.half_open_attempts >= self.config.half_open_max_calls:
                    # Reset to healthy
                    self.state = ConnectionHealthStatus.HEALTHY
                    self.failure_count = 0
            else:
                self.failure_count = max(0, self.failure_count - 1)

    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == ConnectionHealthStatus.DEGRADED:
                # Half-open attempt failed, go back to open
                self.state = ConnectionHealthStatus.CIRCUIT_OPEN
            elif self.failure_count >= self.config.failure_threshold:
                self.state = ConnectionHealthStatus.CIRCUIT_OPEN

    def get_status(self) -> ConnectionHealthStatus:
        """Get current circuit breaker status."""
        return self.state


class ConnectionPool:
    """Enhanced connection pool for AWS clients."""

    def __init__(
        self,
        service: str,
        region: str,
        aws_manager: AWSClientManager,
        config: ConnectionPoolConfig = None,
    ):
        self.service = service
        self.region = region
        self.aws_manager = aws_manager
        self.config = config or ConnectionPoolConfig()

        # Connection tracking
        self._active_connections: set[str] = set()
        self._connection_last_used: dict[str, float] = {}
        self._metrics = ConnectionMetrics(service=service, region=region)
        self._latency_samples = deque(maxlen=100)

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker()

        # Locks
        self._pool_lock = anyio.Lock()

    @asynccontextmanager
    async def get_client(self):
        """Get client from pool with circuit breaker protection."""
        connection_id = f"{self.service}:{self.region}:{id(self)}"
        start_time = time.time()

        try:
            # Use circuit breaker protection
            async def create_client():
                return await self._create_client_internal()

            client = await self.circuit_breaker.call(create_client)

            # Track active connection
            async with self._pool_lock:
                self._active_connections.add(connection_id)
                self._connection_last_used[connection_id] = time.time()

            try:
                yield client
                # Success metrics
                latency_ms = (time.time() - start_time) * 1000
                await self._record_success(latency_ms)

            finally:
                # Cleanup connection
                async with self._pool_lock:
                    self._active_connections.discard(connection_id)

        except Exception as e:
            # Failure metrics
            await self._record_failure(str(e))
            raise

    async def _create_client_internal(self):
        """Create AWS client internally."""
        # Check pool limits
        async with self._pool_lock:
            if len(self._active_connections) >= self.config.max_pool_size:
                # Wait for available connection or timeout
                await self._wait_for_available_connection()

        # Create client using AWS manager
        return await self.aws_manager.get_client(self.service, self.region)

    async def _wait_for_available_connection(self):
        """Wait for connection to become available."""
        timeout = self.config.connection_timeout_seconds
        start_time = time.time()

        while time.time() - start_time < timeout:
            if len(self._active_connections) < self.config.max_pool_size:
                return
            await anyio.sleep(0.1)

        raise Exception(f"Connection pool timeout for {self.service} in {self.region}")

    async def _record_success(self, latency_ms: float):
        """Record successful operation."""
        async with self._pool_lock:
            self._metrics.total_requests += 1
            self._metrics.successful_requests += 1
            self._metrics.last_request_time = time.time()

            # Update latency metrics
            self._latency_samples.append(latency_ms)
            if self._latency_samples:
                self._metrics.average_latency_ms = sum(self._latency_samples) / len(
                    self._latency_samples
                )
                sorted_samples = sorted(self._latency_samples)
                p95_index = int(0.95 * len(sorted_samples))
                self._metrics.p95_latency_ms = sorted_samples[p95_index] if sorted_samples else 0

            # Update error rate
            if self._metrics.total_requests > 0:
                self._metrics.error_rate = (
                    self._metrics.failed_requests / self._metrics.total_requests
                )

    async def _record_failure(self, error_message: str):
        """Record failed operation."""
        async with self._pool_lock:
            self._metrics.total_requests += 1
            self._metrics.failed_requests += 1
            self._metrics.last_request_time = time.time()

            # Update error rate
            if self._metrics.total_requests > 0:
                self._metrics.error_rate = (
                    self._metrics.failed_requests / self._metrics.total_requests
                )

            # Update health status based on error rate
            if self._metrics.total_requests >= 10 and self._metrics.error_rate > 0.5:
                self._metrics.health_status = ConnectionHealthStatus.FAILED
            elif self._metrics.error_rate > 0.2:
                self._metrics.health_status = ConnectionHealthStatus.DEGRADED

    async def cleanup_idle_connections(self):
        """Clean up idle connections."""
        current_time = time.time()
        idle_threshold = current_time - self.config.idle_timeout_seconds

        async with self._pool_lock:
            idle_connections = [
                conn_id
                for conn_id, last_used in self._connection_last_used.items()
                if last_used < idle_threshold
            ]

            for conn_id in idle_connections:
                self._active_connections.discard(conn_id)
                del self._connection_last_used[conn_id]

    def get_metrics(self) -> ConnectionMetrics:
        """Get connection pool metrics."""
        return self._metrics

    def get_status(self) -> dict[str, Any]:
        """Get connection pool status."""
        return {
            "service": self.service,
            "region": self.region,
            "active_connections": len(self._active_connections),
            "max_pool_size": self.config.max_pool_size,
            "health_status": self._metrics.health_status.value,
            "circuit_breaker_status": self.circuit_breaker.get_status().value,
            "error_rate": self._metrics.error_rate,
            "average_latency_ms": self._metrics.average_latency_ms,
            "total_requests": self._metrics.total_requests,
        }


class EnhancedAWSClientManager:
    """
    Enhanced AWS Client Manager with connection pooling and circuit breakers.

    This class extends the base AWSClientManager with advanced features needed
    by the foundation engines:
    - Per-service connection pooling
    - Circuit breaker patterns
    - Performance monitoring
    - Adaptive timeout management
    - Region health tracking
    """

    def __init__(
        self,
        base_aws_manager: AWSClientManager,
        connection_pool_config: ConnectionPoolConfig = None,
        circuit_breaker_config: CircuitBreakerConfig = None,
        enable_connection_pooling: bool = True,
        enable_circuit_breakers: bool = True,
        cleanup_interval_seconds: float = 300.0,
    ):
        """
        Initialize Enhanced AWS Client Manager.

        Args:
            base_aws_manager: Base AWS client manager
            connection_pool_config: Connection pool configuration
            circuit_breaker_config: Circuit breaker configuration
            enable_connection_pooling: Enable connection pooling
            enable_circuit_breakers: Enable circuit breakers
            cleanup_interval_seconds: Cleanup interval for idle connections
        """
        self.base_aws_manager = base_aws_manager
        self.connection_pool_config = connection_pool_config or ConnectionPoolConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.enable_connection_pooling = enable_connection_pooling
        self.enable_circuit_breakers = enable_circuit_breakers
        self.cleanup_interval_seconds = cleanup_interval_seconds

        # Connection pools per service/region
        self._connection_pools: dict[str, ConnectionPool] = {}
        self._pool_lock = anyio.Lock()

        # Background cleanup task
        self._cleanup_task: asyncio.Task | None = None
        self._shutdown_event = anyio.Event()

        logger.info(
            f"EnhancedAWSClientManager initialized - "
            f"pooling: {enable_connection_pooling}, "
            f"circuit_breakers: {enable_circuit_breakers}"
        )

    async def start(self):
        """Start background tasks."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop background tasks."""
        self._shutdown_event.set()
        if self._cleanup_task:
            await self._cleanup_task

    @asynccontextmanager
    async def get_client(self, service: str, region: str):
        """Get enhanced AWS client with pooling and circuit breaker protection."""
        if not self.enable_connection_pooling:
            # Fallback to base manager
            async with self.base_aws_manager.client_context(service, region) as client:
                yield client
            return

        # Get or create connection pool
        pool_key = f"{service}:{region}"

        async with self._pool_lock:
            if pool_key not in self._connection_pools:
                self._connection_pools[pool_key] = ConnectionPool(
                    service=service,
                    region=region,
                    aws_manager=self.base_aws_manager,
                    config=self.connection_pool_config,
                )

        pool = self._connection_pools[pool_key]

        # Use connection pool
        async with pool.get_client() as client:
            yield client

    async def execute_with_retries(
        self,
        service: str,
        region: str,
        operation: Callable,
        *args,
        max_retries: int | None = None,
        **kwargs,
    ):
        """Execute operation with retries and circuit breaker protection."""
        max_retries = max_retries or self.connection_pool_config.max_retries
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                async with self.get_client(service, region) as client:
                    return await operation(client, *args, **kwargs)

            except Exception as e:
                last_exception = e

                # Check if we should retry
                if attempt < max_retries and self._should_retry_error(e):
                    backoff_time = self.connection_pool_config.backoff_multiplier**attempt
                    logger.debug(
                        f"Retrying {service} operation in {region} "
                        f"(attempt {attempt + 1}/{max_retries + 1}) "
                        f"after {backoff_time}s: {str(e)}"
                    )
                    await anyio.sleep(backoff_time)
                else:
                    break

        # All retries failed
        raise last_exception

    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if error should be retried."""
        if isinstance(error, ClientError):
            error_code = error.response.get("Error", {}).get("Code", "")
            # Don't retry client errors that won't succeed on retry
            non_retryable_codes = {
                "ValidationException",
                "InvalidParameterValue",
                "AccessDenied",
                "UnauthorizedOperation",
                "ResourceNotFoundException",
            }
            return error_code not in non_retryable_codes

        # Retry network and service errors
        return isinstance(error, (BotoCoreError, ConnectionError, TimeoutError))

    async def _cleanup_loop(self):
        """Background cleanup loop for idle connections."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Clean up idle connections in all pools
                    async with self._pool_lock:
                        cleanup_tasks = []
                        for pool in self._connection_pools.values():
                            cleanup_tasks.append(pool.cleanup_idle_connections())

                        if cleanup_tasks:
                            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

                    # Wait for next cleanup cycle
                    with anyio.move_on_after(self.cleanup_interval_seconds):
                        await self._shutdown_event.wait()

                except Exception as e:
                    logger.error(f"Error in cleanup loop: {e}")
                    await anyio.sleep(60)  # Wait before retrying

        except Exception as e:
            logger.error(f"Cleanup loop failed: {e}")

    def get_connection_metrics(self) -> dict[str, Any]:
        """Get comprehensive connection metrics."""
        metrics = {
            "pools": {},
            "summary": {
                "total_pools": len(self._connection_pools),
                "healthy_pools": 0,
                "degraded_pools": 0,
                "failed_pools": 0,
                "total_active_connections": 0,
            },
        }

        for pool_key, pool in self._connection_pools.items():
            pool_metrics = pool.get_metrics()
            pool_status = pool.get_status()

            metrics["pools"][pool_key] = {
                "metrics": {
                    "total_requests": pool_metrics.total_requests,
                    "successful_requests": pool_metrics.successful_requests,
                    "failed_requests": pool_metrics.failed_requests,
                    "error_rate": pool_metrics.error_rate,
                    "average_latency_ms": pool_metrics.average_latency_ms,
                    "p95_latency_ms": pool_metrics.p95_latency_ms,
                },
                "status": pool_status,
            }

            # Update summary
            metrics["summary"]["total_active_connections"] += pool_status["active_connections"]

            if pool_status["health_status"] == "healthy":
                metrics["summary"]["healthy_pools"] += 1
            elif pool_status["health_status"] == "degraded":
                metrics["summary"]["degraded_pools"] += 1
            else:
                metrics["summary"]["failed_pools"] += 1

        return metrics

    def get_region_health_summary(self) -> dict[str, dict[str, Any]]:
        """Get health summary by region."""
        region_health = defaultdict(
            lambda: {
                "services": {},
                "overall_health": "healthy",
                "total_connections": 0,
                "error_rate": 0.0,
                "average_latency_ms": 0.0,
            }
        )

        for pool_key, pool in self._connection_pools.items():
            service, region = pool_key.split(":", 1)
            pool_metrics = pool.get_metrics()
            pool_status = pool.get_status()

            region_health[region]["services"][service] = {
                "health_status": pool_status["health_status"],
                "error_rate": pool_metrics.error_rate,
                "average_latency_ms": pool_metrics.average_latency_ms,
                "active_connections": pool_status["active_connections"],
            }

            region_health[region]["total_connections"] += pool_status["active_connections"]

        # Calculate overall health per region
        for region, health_data in region_health.items():
            service_healths = [svc["health_status"] for svc in health_data["services"].values()]

            if all(h == "healthy" for h in service_healths):
                health_data["overall_health"] = "healthy"
            elif any(h == "failed" for h in service_healths):
                health_data["overall_health"] = "failed"
            else:
                health_data["overall_health"] = "degraded"

            # Calculate aggregate metrics
            if health_data["services"]:
                error_rates = [svc["error_rate"] for svc in health_data["services"].values()]
                latencies = [svc["average_latency_ms"] for svc in health_data["services"].values()]

                health_data["error_rate"] = sum(error_rates) / len(error_rates)
                health_data["average_latency_ms"] = sum(latencies) / len(latencies)

        return dict(region_health)

    async def health_check_region(self, region: str) -> dict[str, Any]:
        """Perform comprehensive health check for a region."""
        health_results = {
            "region": region,
            "timestamp": datetime.now(UTC).isoformat(),
            "services": {},
            "overall_healthy": True,
        }

        # Test core services
        test_services = ["ec2", "networkmanager", "sts"]

        for service in test_services:
            try:
                # Simple operation to test connectivity
                if service == "ec2":
                    async with self.get_client(service, region) as client:
                        await client.describe_regions(RegionNames=[region])
                elif service == "networkmanager" and region == "us-west-2":
                    # NetworkManager is global, only test in us-west-2
                    async with self.get_client(service, region) as client:
                        await client.describe_global_networks(MaxResults=1)
                elif service == "sts":
                    async with self.get_client(service, region) as client:
                        await client.get_caller_identity()

                health_results["services"][service] = {"healthy": True, "error": None}

            except Exception as e:
                health_results["services"][service] = {
                    "healthy": False,
                    "error": str(e),
                }
                health_results["overall_healthy"] = False

        return health_results

    def reset_circuit_breakers(self, service: str | None = None, region: str | None = None):
        """Reset circuit breakers for specified service/region or all."""
        for pool_key, pool in self._connection_pools.items():
            pool_service, pool_region = pool_key.split(":", 1)

            if (service is None or pool_service == service) and (
                region is None or pool_region == region
            ):
                pool.circuit_breaker.state = ConnectionHealthStatus.HEALTHY
                pool.circuit_breaker.failure_count = 0
                logger.info(f"Reset circuit breaker for {pool_key}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
