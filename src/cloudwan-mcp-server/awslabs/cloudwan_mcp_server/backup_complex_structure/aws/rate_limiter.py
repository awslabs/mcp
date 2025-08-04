"""
AWS Rate Limiter Implementation for CloudWAN MCP Server.

This module provides comprehensive rate limiting functionality for AWS API calls with:
- Configurable rate limits per service and operation
- Token bucket algorithm for rate limiting
- Exponential backoff with jitter for retries
- Adaptive rate limiting based on service responses
- Detailed metrics and logging for monitoring
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, cast
from threading import Lock, RLock

from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""

    pass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter behavior."""

    # Request rates
    requests_per_second: float = 5.0  # Default requests per second
    burst_capacity: int = 10  # Default burst capacity

    # Retry configuration
    max_retries: int = 3  # Maximum retry attempts
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 30.0  # Maximum delay in seconds
    jitter_factor: float = 0.5  # Jitter factor (0-1)

    # Advanced settings
    adaptive_adjustment: bool = True  # Adjust limits based on service responses
    metric_window_size: int = 100  # Number of requests for moving average
    log_level: int = logging.INFO  # Logging level


@dataclass
class ServiceRateLimits:
    """Service-specific rate limit configurations."""

    # Network Manager (most constrained)
    NETWORKMANAGER = RateLimitConfig(
        requests_per_second=2.0,
        burst_capacity=5,
        max_retries=3,
        base_delay=2.0,
        max_delay=60.0,
    )

    # EC2 (higher limits but still constrained)
    EC2 = RateLimitConfig(
        requests_per_second=10.0,
        burst_capacity=20,
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
    )

    # CloudWatch (metrics and logs)
    CLOUDWATCH = RateLimitConfig(
        requests_per_second=15.0,
        burst_capacity=30,
        max_retries=3,
        base_delay=0.5,
        max_delay=20.0,
    )

    # Default for other services
    DEFAULT = RateLimitConfig()


@dataclass
class RateLimitMetrics:
    """Metrics for rate limiter performance and monitoring."""

    total_requests: int = 0
    throttled_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_attempts: int = 0

    # Timing metrics
    last_request_time: Optional[datetime] = None
    total_wait_time: float = 0.0
    avg_wait_time: float = 0.0

    # Request rate metrics
    current_request_rate: float = 0.0
    response_times: List[float] = field(default_factory=list)

    # Adaptive metrics
    rate_adjustments: int = 0
    current_limit_factor: float = 1.0  # Multiplier for configured rate


class TokenBucketRateLimiter:
    """Token bucket implementation for rate limiting."""

    def __init__(self, rate: float, capacity: int):
        """
        Initialize rate limiter.

        Args:
            rate: Tokens added per second
            capacity: Maximum token capacity (bucket size)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = Lock()

    def _add_tokens(self):
        """Add tokens based on elapsed time."""
        now = time.monotonic()
        time_elapsed = now - self.last_update
        self.last_update = now

        tokens_to_add = time_elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)

    async def acquire(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Tuple of (success, wait_time_if_any)
        """
        with self._lock:
            self._add_tokens()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0

            # Calculate wait time if not enough tokens
            missing_tokens = tokens - self.tokens
            wait_time = missing_tokens / self.rate

            return False, wait_time

    def try_acquire_sync(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to acquire tokens (synchronous version).

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Tuple of (success, wait_time_if_any)
        """
        with self._lock:
            self._add_tokens()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0

            # Calculate wait time if not enough tokens
            missing_tokens = tokens - self.tokens
            wait_time = missing_tokens / self.rate

            return False, wait_time


class AwsApiRateLimiter:
    """
    Rate limiter for AWS API calls with intelligent retry handling.

    Features:
    - Per-service rate limiting with configurable limits
    - Token bucket algorithm for smooth rate control
    - Exponential backoff with jitter for retries
    - Metrics collection for monitoring and debugging
    - Adaptive rate adjustment based on AWS response
    """

    def __init__(
        self,
        service: str,
        operation: Optional[str] = None,
        region: Optional[str] = None,
        config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize AWS API rate limiter.

        Args:
            service: AWS service name
            operation: Optional operation name (for more granular limits)
            region: Optional AWS region
            config: Custom rate limit configuration
        """
        self.service = service.lower()
        self.operation = operation
        self.region = region

        # Get service-specific config or use provided config
        self.config = config or self._get_service_config(service)

        # Create rate limiter based on configuration
        self.rate_limiter = TokenBucketRateLimiter(
            self.config.requests_per_second, self.config.burst_capacity
        )

        # Metrics
        self.metrics = RateLimitMetrics()
        self._metrics_lock = RLock()

        # Cache key for storing rate limit data
        self._cache_key = f"rate_limit:{service}"
        if operation:
            self._cache_key += f":{operation}"
        if region:
            self._cache_key += f":{region}"

        logger.debug(
            f"Rate limiter initialized for {service}"
            f"{f':{operation}' if operation else ''}"
            f"{f' in {region}' if region else ''}"
            f" with {self.config.requests_per_second} req/s"
        )

    def _get_service_config(self, service: str) -> RateLimitConfig:
        """Get service-specific configuration."""
        service_upper = service.upper()
        if hasattr(ServiceRateLimits, service_upper):
            return getattr(ServiceRateLimits, service_upper)
        return ServiceRateLimits.DEFAULT

    def _calculate_retry_delay(self, attempt: int, is_throttling: bool = False) -> float:
        """
        Calculate delay for retry with exponential backoff and jitter.

        Args:
            attempt: The retry attempt number (1-indexed)
            is_throttling: Whether retry is due to throttling

        Returns:
            Delay in seconds
        """
        # For throttling, use more conservative backoff
        base = self.config.base_delay * (2.0 if is_throttling else 1.0)

        # Exponential backoff: base_delay * (2 ^ (attempt - 1))
        delay = base * (2 ** (attempt - 1))

        # Cap at maximum delay
        delay = min(delay, self.config.max_delay)

        # Add jitter
        if self.config.jitter_factor > 0:
            jitter_range = delay * self.config.jitter_factor
            delay = delay - (jitter_range / 2) + (random.random() * jitter_range)

        return delay

    def _is_throttling_exception(self, exception: Exception) -> bool:
        """Check if exception is related to throttling."""
        if isinstance(exception, ClientError):
            error_code = exception.response.get("Error", {}).get("Code", "")
            return error_code in [
                "Throttling",
                "ThrottlingException",
                "RequestLimitExceeded",
                "TooManyRequestsException",
                "LimitExceedException",
            ]
        return False

    def _update_metrics(self, wait_time: float = 0.0, response_time: float = 0.0) -> None:
        """Update rate limiter metrics."""
        with self._metrics_lock:
            self.metrics.last_request_time = datetime.now(timezone.utc)

            if wait_time > 0:
                self.metrics.total_wait_time += wait_time
                self.metrics.throttled_requests += 1

            if response_time > 0:
                self.metrics.response_times.append(response_time)
                # Keep only recent responses
                if len(self.metrics.response_times) > self.config.metric_window_size:
                    self.metrics.response_times = self.metrics.response_times[
                        -self.config.metric_window_size :
                    ]

            # Update average wait time
            if self.metrics.total_requests > 0:
                self.metrics.avg_wait_time = (
                    self.metrics.total_wait_time / self.metrics.total_requests
                )

    def _adjust_rate_if_needed(self, was_throttled: bool) -> None:
        """Adaptively adjust rate limit based on service responses."""
        if not self.config.adaptive_adjustment:
            return

        with self._metrics_lock:
            if was_throttled:
                # Reduce rate by 10% for throttling
                self.metrics.current_limit_factor *= 0.9
                self.metrics.rate_adjustments += 1

                # Update rate limiter with new rate
                with self.rate_limiter._lock:
                    self.rate_limiter.rate = (
                        self.config.requests_per_second * self.metrics.current_limit_factor
                    )

                logger.debug(
                    f"Reduced rate limit for {self.service} to "
                    f"{self.rate_limiter.rate:.2f} req/s "
                    f"(factor: {self.metrics.current_limit_factor:.2f})"
                )
            elif self.metrics.current_limit_factor < 1.0 and self.metrics.throttled_requests == 0:
                # Gradually increase rate if no throttling
                throttle_ratio = self.metrics.throttled_requests / max(
                    1, self.metrics.total_requests
                )
                if throttle_ratio < 0.01:  # Less than 1% throttling
                    self.metrics.current_limit_factor = min(
                        1.0, self.metrics.current_limit_factor * 1.05
                    )
                    self.metrics.rate_adjustments += 1

                    # Update rate limiter with new rate
                    with self.rate_limiter._lock:
                        self.rate_limiter.rate = (
                            self.config.requests_per_second * self.metrics.current_limit_factor
                        )

                    logger.debug(
                        f"Increased rate limit for {self.service} to "
                        f"{self.rate_limiter.rate:.2f} req/s "
                        f"(factor: {self.metrics.current_limit_factor:.2f})"
                    )

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with rate limiting and retries.

        Args:
            func: Function to execute
            *args: Function positional arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RateLimitExceededError: If max retries exceeded due to throttling
            Exception: Original exception if not related to throttling
        """
        with self._metrics_lock:
            self.metrics.total_requests += 1

        # Try to acquire token for the request
        acquired, wait_time = await self.rate_limiter.acquire()

        if not acquired:
            with self._metrics_lock:
                self.metrics.throttled_requests += 1

            if wait_time > 0:
                logger.log(
                    self.config.log_level,
                    f"Rate limit reached for {self.service}, "
                    f"waiting {wait_time:.2f}s before request",
                )

                # Update metrics with wait time
                self._update_metrics(wait_time=wait_time)

                # Wait for next token
                await asyncio.sleep(wait_time)

                # Try again after waiting
                acquired, _ = await self.rate_limiter.acquire()
                if not acquired:
                    logger.warning(
                        f"Failed to acquire rate limit token even after waiting "
                        f"{wait_time:.2f}s for {self.service}"
                    )
                    raise RateLimitExceededError(
                        f"Rate limit exceeded for {self.service} and "
                        f"couldn't acquire token after waiting"
                    )

        # Execute with retries
        last_exception = None
        for attempt in range(1, self.config.max_retries + 1):
            start_time = time.monotonic()
            was_throttled = False

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Record success
                response_time = time.monotonic() - start_time
                self._update_metrics(response_time=response_time)

                with self._metrics_lock:
                    self.metrics.successful_requests += 1

                # Adjust rate if needed (no throttling)
                self._adjust_rate_if_needed(was_throttled=False)

                return result

            except Exception as e:
                last_exception = e
                response_time = time.monotonic() - start_time

                # Check if exception is due to throttling
                was_throttled = self._is_throttling_exception(e)

                with self._metrics_lock:
                    self.metrics.failed_requests += 1
                    if attempt < self.config.max_retries:
                        self.metrics.retry_attempts += 1

                # Update metrics
                self._update_metrics(response_time=response_time)

                # Adjust rate if throttled
                if was_throttled:
                    self._adjust_rate_if_needed(was_throttled=True)

                # Don't retry on final attempt or non-throttling errors
                if attempt == self.config.max_retries or not was_throttled:
                    break

                # Calculate backoff delay
                delay = self._calculate_retry_delay(attempt, is_throttling=was_throttled)

                logger.log(
                    self.config.log_level,
                    f"Request to {self.service} throttled (attempt {attempt}/{self.config.max_retries}), "
                    f"retrying in {delay:.2f}s",
                )

                await asyncio.sleep(delay)

        # All retries failed
        if last_exception:
            if self._is_throttling_exception(last_exception):
                # Convert to RateLimitExceededError for throttling
                logger.warning(
                    f"Rate limit exceeded for {self.service} after "
                    f"{self.config.max_retries} retries"
                )
                raise RateLimitExceededError(
                    f"Rate limit exceeded for {self.service} after "
                    f"{self.config.max_retries} retries: {str(last_exception)}"
                )

            # Re-raise original exception for other errors
            raise last_exception

        # This should never happen
        raise Exception("Request failed without an exception")

    def execute_sync(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with rate limiting and retries (synchronous version).

        Args:
            func: Function to execute
            *args: Function positional arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RateLimitExceededError: If max retries exceeded due to throttling
            Exception: Original exception if not related to throttling
        """
        with self._metrics_lock:
            self.metrics.total_requests += 1

        # Try to acquire token for the request
        acquired, wait_time = self.rate_limiter.try_acquire_sync()

        if not acquired:
            with self._metrics_lock:
                self.metrics.throttled_requests += 1

            if wait_time > 0:
                logger.log(
                    self.config.log_level,
                    f"Rate limit reached for {self.service}, "
                    f"waiting {wait_time:.2f}s before request",
                )

                # Update metrics with wait time
                self._update_metrics(wait_time=wait_time)

                # Wait for next token
                time.sleep(wait_time)

                # Try again after waiting
                acquired, _ = self.rate_limiter.try_acquire_sync()
                if not acquired:
                    logger.warning(
                        f"Failed to acquire rate limit token even after waiting "
                        f"{wait_time:.2f}s for {self.service}"
                    )
                    raise RateLimitExceededError(
                        f"Rate limit exceeded for {self.service} and "
                        f"couldn't acquire token after waiting"
                    )

        # Execute with retries
        last_exception = None
        for attempt in range(1, self.config.max_retries + 1):
            start_time = time.monotonic()
            was_throttled = False

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Record success
                response_time = time.monotonic() - start_time
                self._update_metrics(response_time=response_time)

                with self._metrics_lock:
                    self.metrics.successful_requests += 1

                # Adjust rate if needed (no throttling)
                self._adjust_rate_if_needed(was_throttled=False)

                return result

            except Exception as e:
                last_exception = e
                response_time = time.monotonic() - start_time

                # Check if exception is due to throttling
                was_throttled = self._is_throttling_exception(e)

                with self._metrics_lock:
                    self.metrics.failed_requests += 1
                    if attempt < self.config.max_retries:
                        self.metrics.retry_attempts += 1

                # Update metrics
                self._update_metrics(response_time=response_time)

                # Adjust rate if throttled
                if was_throttled:
                    self._adjust_rate_if_needed(was_throttled=True)

                # Don't retry on final attempt or non-throttling errors
                if attempt == self.config.max_retries or not was_throttled:
                    break

                # Calculate backoff delay
                delay = self._calculate_retry_delay(attempt, is_throttling=was_throttled)

                logger.log(
                    self.config.log_level,
                    f"Request to {self.service} throttled (attempt {attempt}/{self.config.max_retries}), "
                    f"retrying in {delay:.2f}s",
                )

                time.sleep(delay)

        # All retries failed
        if last_exception:
            if self._is_throttling_exception(last_exception):
                # Convert to RateLimitExceededError for throttling
                logger.warning(
                    f"Rate limit exceeded for {self.service} after "
                    f"{self.config.max_retries} retries"
                )
                raise RateLimitExceededError(
                    f"Rate limit exceeded for {self.service} after "
                    f"{self.config.max_retries} retries: {str(last_exception)}"
                )

            # Re-raise original exception for other errors
            raise last_exception

        # This should never happen
        raise Exception("Request failed without an exception")

    def get_metrics(self) -> RateLimitMetrics:
        """Get current rate limiter metrics."""
        with self._metrics_lock:
            return self.metrics

    def get_status(self) -> Dict[str, Any]:
        """Get detailed status information."""
        with self._metrics_lock:
            metrics = self.metrics

            # Calculate success rate
            success_rate = 0.0
            if metrics.total_requests > 0:
                success_rate = metrics.successful_requests / metrics.total_requests

            # Calculate average response time
            avg_response_time = 0.0
            if metrics.response_times:
                avg_response_time = sum(metrics.response_times) / len(metrics.response_times)

            return {
                "service": self.service,
                "operation": self.operation,
                "region": self.region,
                "config": {
                    "requests_per_second": self.config.requests_per_second,
                    "burst_capacity": self.config.burst_capacity,
                    "max_retries": self.config.max_retries,
                    "adaptive_adjustment": self.config.adaptive_adjustment,
                },
                "metrics": {
                    "total_requests": metrics.total_requests,
                    "successful_requests": metrics.successful_requests,
                    "failed_requests": metrics.failed_requests,
                    "throttled_requests": metrics.throttled_requests,
                    "retry_attempts": metrics.retry_attempts,
                    "success_rate": success_rate,
                    "avg_wait_time": metrics.avg_wait_time,
                    "avg_response_time": avg_response_time,
                    "current_limit_factor": metrics.current_limit_factor,
                },
            }


class RateLimiterManager:
    """
    Manager for rate limiters with centralized configuration.

    Features:
    - Centralized rate limiter creation and management
    - Service-specific rate limits
    - Operation-specific rate limits
    - Global rate limiting metrics and monitoring
    """

    def __init__(self):
        """Initialize rate limiter manager."""
        self._rate_limiters: Dict[str, AwsApiRateLimiter] = {}
        self._lock = RLock()
        self._service_configs: Dict[str, RateLimitConfig] = {}
        self._global_metrics = {
            "total_requests": 0,
            "throttled_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_wait_time": 0.0,
            "rate_adjustments": 0,
        }

    def _get_limiter_key(
        self,
        service: str,
        operation: Optional[str] = None,
        region: Optional[str] = None,
    ) -> str:
        """Generate unique key for rate limiter."""
        key = service.lower()
        if operation:
            key += f":{operation}"
        if region:
            key += f":{region}"
        return key

    def get_or_create_rate_limiter(
        self,
        service: str,
        operation: Optional[str] = None,
        region: Optional[str] = None,
        config: Optional[RateLimitConfig] = None,
    ) -> AwsApiRateLimiter:
        """
        Get existing or create new rate limiter.

        Args:
            service: AWS service name
            operation: Optional operation name
            region: Optional AWS region
            config: Optional custom configuration

        Returns:
            Rate limiter instance
        """
        key = self._get_limiter_key(service, operation, region)

        with self._lock:
            if key not in self._rate_limiters:
                # Use provided config or get service-specific config
                limiter = AwsApiRateLimiter(
                    service=service,
                    operation=operation,
                    region=region,
                    config=config or self._service_configs.get(service.upper()),
                )

                self._rate_limiters[key] = limiter
                logger.debug(f"Created new rate limiter: {key}")

            return self._rate_limiters[key]

    def set_service_config(self, service: str, config: RateLimitConfig) -> None:
        """
        Set service-specific rate limit configuration.

        Args:
            service: AWS service name (case-insensitive)
            config: Rate limit configuration
        """
        service_upper = service.upper()
        with self._lock:
            self._service_configs[service_upper] = config

    def get_all_rate_limiters(self) -> Dict[str, AwsApiRateLimiter]:
        """Get all managed rate limiters."""
        with self._lock:
            return self._rate_limiters.copy()

    def get_global_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics across all rate limiters."""
        metrics = {
            "total_requests": 0,
            "throttled_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retry_attempts": 0,
            "total_wait_time": 0.0,
            "avg_wait_time": 0.0,
            "services": set(),
            "operations": set(),
        }

        with self._lock:
            # Collect metrics from all rate limiters
            for key, limiter in self._rate_limiters.items():
                limiter_metrics = limiter.get_metrics()

                metrics["total_requests"] += limiter_metrics.total_requests
                metrics["throttled_requests"] += limiter_metrics.throttled_requests
                metrics["successful_requests"] += limiter_metrics.successful_requests
                metrics["failed_requests"] += limiter_metrics.failed_requests
                metrics["retry_attempts"] += limiter_metrics.retry_attempts
                metrics["total_wait_time"] += limiter_metrics.total_wait_time

                if limiter.service:
                    metrics["services"].add(limiter.service)
                if limiter.operation:
                    metrics["operations"].add(limiter.operation)

            # Calculate averages
            if metrics["total_requests"] > 0:
                metrics["avg_wait_time"] = metrics["total_wait_time"] / metrics["total_requests"]

            # Convert sets to counts
            metrics["unique_services"] = len(metrics["services"])
            metrics["unique_operations"] = len(metrics["operations"])
            del metrics["services"]
            del metrics["operations"]

        return metrics

    def clear_metrics(self) -> None:
        """Reset metrics for all rate limiters."""
        with self._lock:
            for limiter in self._rate_limiters.values():
                with limiter._metrics_lock:
                    limiter.metrics = RateLimitMetrics()

            self._global_metrics = {
                "total_requests": 0,
                "throttled_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_wait_time": 0.0,
                "rate_adjustments": 0,
            }


# Global rate limiter manager instance
_rate_limiter_manager = RateLimiterManager()


def get_rate_limiter_manager() -> RateLimiterManager:
    """Get the global rate limiter manager instance."""
    return _rate_limiter_manager


# Type variable for generic function types
T = TypeVar("T")


def with_rate_limiter(
    service: str,
    operation: Optional[str] = None,
    region: Optional[str] = None,
    config: Optional[RateLimitConfig] = None,
):
    """
    Decorator to wrap functions with rate limiting protection.

    Args:
        service: AWS service name
        operation: Operation name (defaults to function name)
        region: AWS region (optional)
        config: Custom rate limit configuration (optional)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_name = operation or func.__name__
        manager = get_rate_limiter_manager()

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Get or create rate limiter
                rate_limiter = manager.get_or_create_rate_limiter(
                    service=service, operation=op_name, region=region, config=config
                )

                # Execute with rate limiting
                return await rate_limiter.execute(func, *args, **kwargs)

            return cast(Callable[..., T], async_wrapper)
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Get or create rate limiter
                rate_limiter = manager.get_or_create_rate_limiter(
                    service=service, operation=op_name, region=region, config=config
                )

                # Execute with rate limiting
                return rate_limiter.execute_sync(func, *args, **kwargs)

            return cast(Callable[..., T], sync_wrapper)

    return decorator


@dataclass
class RetryState:
    """State for retry operations."""

    attempts: int = 0
    max_attempts: int = 3
    last_exception: Optional[Exception] = None
    wait_times: List[float] = field(default_factory=list)
    total_wait_time: float = 0.0


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter_factor: float = 0.5,
    retry_on: Optional[List[str]] = None,
    **kwargs,
) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to retry
        *args: Function arguments
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter_factor: Jitter factor (0-1)
        retry_on: List of exception names to retry on (defaults to throttling exceptions)
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Exception: Last exception after all retries
    """
    # Default throttling exceptions
    if retry_on is None:
        retry_on = [
            "Throttling",
            "ThrottlingException",
            "RequestLimitExceeded",
            "TooManyRequestsException",
            "LimitExceedException",
        ]

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            # Check if we should retry
            should_retry = False
            if isinstance(e, ClientError):
                error_code = e.response.get("Error", {}).get("Code", "")
                should_retry = error_code in retry_on

            # Don't retry on final attempt or if not in retry_on
            if attempt == max_retries or not should_retry:
                break

            # Calculate backoff delay
            delay = base_delay * (2 ** (attempt - 1))
            delay = min(delay, max_delay)

            # Add jitter
            if jitter_factor > 0:
                jitter_range = delay * jitter_factor
                delay = delay - (jitter_range / 2) + (random.random() * jitter_range)

            logger.info(
                f"Request failed (attempt {attempt}/{max_retries}), " f"retrying in {delay:.2f}s"
            )

            await asyncio.sleep(delay)

    # All retries failed
    if last_exception:
        raise last_exception

    # This should never happen
    raise Exception("Request failed without an exception")


def retry_with_backoff_sync(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter_factor: float = 0.5,
    retry_on: Optional[List[str]] = None,
    **kwargs,
) -> Any:
    """
    Retry a function with exponential backoff (synchronous version).

    Args:
        func: Function to retry
        *args: Function arguments
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter_factor: Jitter factor (0-1)
        retry_on: List of exception names to retry on (defaults to throttling exceptions)
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Exception: Last exception after all retries
    """
    # Default throttling exceptions
    if retry_on is None:
        retry_on = [
            "Throttling",
            "ThrottlingException",
            "RequestLimitExceeded",
            "TooManyRequestsException",
            "LimitExceedException",
        ]

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            # Check if we should retry
            should_retry = False
            if isinstance(e, ClientError):
                error_code = e.response.get("Error", {}).get("Code", "")
                should_retry = error_code in retry_on

            # Don't retry on final attempt or if not in retry_on
            if attempt == max_retries or not should_retry:
                break

            # Calculate backoff delay
            delay = base_delay * (2 ** (attempt - 1))
            delay = min(delay, max_delay)

            # Add jitter
            if jitter_factor > 0:
                jitter_range = delay * jitter_factor
                delay = delay - (jitter_range / 2) + (random.random() * jitter_range)

            logger.info(
                f"Request failed (attempt {attempt}/{max_retries}), " f"retrying in {delay:.2f}s"
            )

            time.sleep(delay)

    # All retries failed
    if last_exception:
        raise last_exception

    # This should never happen
    raise Exception("Request failed without an exception")
