"""
AWS Circuit Breaker Pattern Implementation for Production Reliability.

This module provides comprehensive circuit breaker functionality for AWS API calls with:
- Circuit breaker states: CLOSED, OPEN, HALF_OPEN
- Service-specific configuration and thresholds
- Exponential backoff with jitter
- Health monitoring and metrics
- Integration with AWS SDK rate limiting
- Graceful degradation patterns
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from threading import Lock, RLock
import statistics

from botocore.exceptions import ClientError, BotoCoreError
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential_jitter,
        retry_if_exception_type,
        before_sleep_log,
        after_log,
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # Simple fallback decorators and functions
    def retry(**kwargs):
        def decorator(func):
            return func
        return decorator
    def stop_after_attempt(n):
        return None
    def wait_exponential_jitter(**kwargs):
        return None
    def retry_if_exception_type(exc_type):
        return None
    def before_sleep_log(logger, log_level):
        return None
    def after_log(logger, log_level):
        return None

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation - requests allowed
    OPEN = "open"  # Failure threshold exceeded - requests blocked
    HALF_OPEN = "half_open"  # Testing phase - limited requests allowed


class FailureType(Enum):
    """Types of failures that can trigger circuit breaker."""

    THROTTLING = "throttling"  # AWS API rate limiting
    TIMEOUT = "timeout"  # Request timeout
    CONNECTION_ERROR = "connection"  # Network connectivity issues
    SERVICE_ERROR = "service_error"  # AWS service errors (5xx)
    AUTHENTICATION = "authentication"  # Auth/credential errors
    UNKNOWN = "unknown"  # Other errors


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Failures before opening circuit
    recovery_timeout: int = 60  # Seconds to wait before half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout_seconds: float = 30.0  # Request timeout

    # Service-specific rate limit handling
    max_requests_per_second: float = 10.0  # Max request rate
    burst_capacity: int = 20  # Burst allowance

    # Exponential backoff parameters
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    jitter: bool = True  # Add random jitter to delays

    # Health check configuration
    health_check_interval: int = 30  # Health check frequency
    enable_adaptive_timeout: bool = True  # Adjust timeout based on latency

    # Advanced features
    enable_graceful_degradation: bool = True
    failure_decay_rate: float = 0.1  # Rate at which old failures decay


@dataclass
class ServiceSpecificConfig:
    """Service-specific circuit breaker configurations."""

    # NetworkManager (most critical - very limited API rate)
    NETWORKMANAGER = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120,
        success_threshold=2,
        timeout_seconds=45.0,
        max_requests_per_second=2.0,  # Very conservative
        burst_capacity=5,
        base_delay=2.0,
        max_delay=120.0,
        health_check_interval=60,
    )

    # EC2 (high volume calls)
    EC2 = CircuitBreakerConfig(
        failure_threshold=8,
        recovery_timeout=45,
        success_threshold=3,
        timeout_seconds=20.0,
        max_requests_per_second=20.0,
        burst_capacity=50,
        base_delay=0.5,
        max_delay=30.0,
        health_check_interval=20,
    )

    # ELB (frequent health checks)
    ELB = CircuitBreakerConfig(
        failure_threshold=6,
        recovery_timeout=30,
        success_threshold=3,
        timeout_seconds=15.0,
        max_requests_per_second=15.0,
        burst_capacity=30,
        base_delay=0.5,
        max_delay=20.0,
        health_check_interval=15,
    )

    # CloudWatch (metrics and logs)
    CLOUDWATCH = CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=30,
        success_threshold=4,
        timeout_seconds=25.0,
        max_requests_per_second=25.0,
        burst_capacity=60,
        base_delay=0.3,
        max_delay=15.0,
        health_check_interval=10,
    )

    # Default for other services
    DEFAULT = CircuitBreakerConfig()


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker performance and health."""

    state: CircuitBreakerState = CircuitBreakerState.CLOSED

    # Counters
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    blocked_requests: int = 0

    # Failure tracking
    consecutive_failures: int = 0
    failure_rate: float = 0.0
    failures_by_type: Dict[FailureType, int] = field(default_factory=dict)

    # Timing metrics
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Performance metrics
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)

    # Rate limiting
    current_request_rate: float = 0.0
    rate_limit_violations: int = 0

    # Health status
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0


@dataclass
class RequestContext:
    """Context for individual requests through circuit breaker."""

    service: str
    operation: str
    region: str
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempt_number: int = 1
    max_attempts: int = 3
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RateLimiter:
    """Token bucket rate limiter for AWS API calls."""

    def __init__(self, max_rate: float, burst_capacity: int):
        """
        Initialize rate limiter.

        Args:
            max_rate: Maximum requests per second
            burst_capacity: Maximum burst requests allowed
        """
        self.max_rate = max_rate
        self.burst_capacity = burst_capacity
        self.tokens = float(burst_capacity)
        self.last_update = time.time()
        self._lock = Lock()

    def acquire(self, tokens_requested: int = 1) -> bool:
        """
        Acquire tokens for request.

        Args:
            tokens_requested: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if rate limited
        """
        with self._lock:
            now = time.time()
            time_elapsed = now - self.last_update

            # Add tokens based on time elapsed
            tokens_to_add = time_elapsed * self.max_rate
            self.tokens = min(self.burst_capacity, self.tokens + tokens_to_add)
            self.last_update = now

            # Check if we have enough tokens
            if self.tokens >= tokens_requested:
                self.tokens -= tokens_requested
                return True
            return False

    def get_wait_time(self, tokens_requested: int = 1) -> float:
        """Get time to wait before tokens are available."""
        with self._lock:
            if self.tokens >= tokens_requested:
                return 0.0

            tokens_needed = tokens_requested - self.tokens
            return tokens_needed / self.max_rate


class CircuitBreaker:
    """
    Production-ready circuit breaker for AWS API calls.

    Implements the circuit breaker pattern with:
    - State management (CLOSED/OPEN/HALF_OPEN)
    - Service-specific configurations
    - Rate limiting integration
    - Comprehensive metrics and monitoring
    - Graceful degradation patterns
    """

    def __init__(
        self,
        name: str,
        service: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback_handler: Optional[Callable] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Unique name for this circuit breaker
            service: AWS service name (e.g., 'networkmanager', 'ec2')
            config: Circuit breaker configuration
            fallback_handler: Optional fallback function for degraded service
        """
        self.name = name
        self.service = service.lower()
        self.config = config or self._get_service_config(service)
        self.fallback_handler = fallback_handler

        # State management
        self._state = CircuitBreakerState.CLOSED
        self._state_lock = RLock()

        # Metrics and monitoring
        self.metrics = CircuitBreakerMetrics()
        self._metrics_lock = Lock()

        # Rate limiting
        self.rate_limiter = RateLimiter(
            self.config.max_requests_per_second, self.config.burst_capacity
        )

        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_running = False

        # Recent failures for pattern analysis
        self._recent_failures: List[Tuple[datetime, FailureType, str]] = []
        self._failure_lock = Lock()

        logger.info(
            f"Circuit breaker '{name}' initialized for service '{service}' "
            f"with threshold={config.failure_threshold if config else 5}"
        )

    def _get_service_config(self, service: str) -> CircuitBreakerConfig:
        """Get service-specific configuration."""
        service_upper = service.upper()
        if hasattr(ServiceSpecificConfig, service_upper):
            return getattr(ServiceSpecificConfig, service_upper)
        return ServiceSpecificConfig.DEFAULT

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._state_lock:
            return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset from OPEN to HALF_OPEN."""
        with self._metrics_lock:
            if self.metrics.last_failure_time is None:
                return True

            time_since_failure = (
                datetime.now(timezone.utc) - self.metrics.last_failure_time
            ).total_seconds()

            return time_since_failure >= self.config.recovery_timeout

    def _classify_failure(self, exception: Exception) -> FailureType:
        """Classify the type of failure for circuit breaker logic."""
        if isinstance(exception, ClientError):
            error_code = exception.response.get("Error", {}).get("Code", "")

            # AWS throttling errors
            if error_code in [
                "Throttling",
                "ThrottlingException",
                "RequestLimitExceeded",
                "TooManyRequestsException",
                "LimitExceedException",
            ]:
                return FailureType.THROTTLING

            # Authentication/authorization errors
            elif error_code in [
                "AccessDenied",
                "UnauthorizedOperation",
                "InvalidUserID.NotFound",
                "TokenRefreshRequired",
                "ExpiredToken",
            ]:
                return FailureType.AUTHENTICATION

            # Service errors (5xx equivalent)
            elif error_code.startswith("Internal") or error_code.endswith("Exception"):
                return FailureType.SERVICE_ERROR

        elif isinstance(exception, (asyncio.TimeoutError, TimeoutError)):
            return FailureType.TIMEOUT

        elif isinstance(exception, (ConnectionError, BotoCoreError)):
            return FailureType.CONNECTION_ERROR

        return FailureType.UNKNOWN

    def _calculate_backoff_delay(self, attempt: int, failure_type: FailureType) -> float:
        """Calculate exponential backoff delay with jitter."""
        # Base delay varies by failure type
        type_multipliers = {
            FailureType.THROTTLING: 2.0,  # Longer delays for throttling
            FailureType.TIMEOUT: 1.5,  # Medium delays for timeouts
            FailureType.CONNECTION_ERROR: 1.2,  # Shorter delays for connection issues
            FailureType.SERVICE_ERROR: 1.8,  # Longer delays for service errors
            FailureType.AUTHENTICATION: 3.0,  # Longest delays for auth issues
            FailureType.UNKNOWN: 1.0,  # Default delay
        }

        multiplier = type_multipliers.get(failure_type, 1.0)
        base_delay = self.config.base_delay * multiplier

        # Exponential backoff: base_delay * (2 ** (attempt - 1))
        delay = base_delay * (2 ** (attempt - 1))

        # Cap at maximum delay
        delay = min(delay, self.config.max_delay)

        # Add jitter if enabled
        if self.config.jitter:
            jitter_factor = random.uniform(0.5, 1.5)
            delay *= jitter_factor

        return delay

    def _record_failure(self, exception: Exception, context: RequestContext) -> None:
        """Record a failure and update circuit breaker state."""
        failure_type = self._classify_failure(exception)
        current_time = datetime.now(timezone.utc)

        with self._failure_lock:
            # Add to recent failures
            self._recent_failures.append((current_time, failure_type, str(exception)))

            # Keep only recent failures (last hour)
            cutoff_time = current_time - timedelta(hours=1)
            self._recent_failures = [
                (time, ftype, msg)
                for time, ftype, msg in self._recent_failures
                if time > cutoff_time
            ]

        with self._metrics_lock:
            self.metrics.failed_requests += 1
            self.metrics.consecutive_failures += 1
            self.metrics.last_failure_time = current_time

            # Update failure counts by type
            if failure_type not in self.metrics.failures_by_type:
                self.metrics.failures_by_type[failure_type] = 0
            self.metrics.failures_by_type[failure_type] += 1

            # Calculate failure rate
            total_requests = self.metrics.total_requests
            if total_requests > 0:
                self.metrics.failure_rate = self.metrics.failed_requests / total_requests

        # Check if we should open the circuit
        with self._state_lock:
            if (
                self._state == CircuitBreakerState.CLOSED
                and self.metrics.consecutive_failures >= self.config.failure_threshold
            ):
                self._transition_to_open()
            elif (
                self._state == CircuitBreakerState.HALF_OPEN
                and self.metrics.consecutive_failures >= 1
            ):
                self._transition_to_open()

        logger.warning(
            f"Circuit breaker '{self.name}' recorded failure: {failure_type.value} - "
            f"{str(exception)[:100]}... (consecutive: {self.metrics.consecutive_failures})"
        )

    def _record_success(self, response_time: float, context: RequestContext) -> None:
        """Record a successful request."""
        current_time = datetime.now(timezone.utc)

        with self._metrics_lock:
            self.metrics.successful_requests += 1
            self.metrics.consecutive_failures = 0  # Reset consecutive failures
            self.metrics.last_success_time = current_time

            # Update response time metrics
            self.metrics.response_times.append(response_time)

            # Keep only recent response times (last 100)
            if len(self.metrics.response_times) > 100:
                self.metrics.response_times = self.metrics.response_times[-100:]

            # Update averages
            if self.metrics.response_times:
                self.metrics.avg_response_time = statistics.mean(self.metrics.response_times)
                self.metrics.p95_response_time = (
                    statistics.quantiles(self.metrics.response_times, n=20)[18]
                    if len(self.metrics.response_times) >= 20
                    else self.metrics.avg_response_time
                )

        # Check if we should close the circuit from half-open state
        with self._state_lock:
            if (
                self._state == CircuitBreakerState.HALF_OPEN
                and self.metrics.successful_requests >= self.config.success_threshold
            ):
                self._transition_to_closed()

        logger.debug(
            f"Circuit breaker '{self.name}' recorded success: "
            f"response_time={response_time:.3f}s, state={self._state.value}"
        )

    def _transition_to_open(self) -> None:
        """Transition circuit breaker to OPEN state."""
        old_state = self._state
        self._state = CircuitBreakerState.OPEN

        with self._metrics_lock:
            self.metrics.state = self._state
            self.metrics.state_changed_at = datetime.now(timezone.utc)

        logger.error(
            f"Circuit breaker '{self.name}' OPENED: {old_state.value} -> {self._state.value} "
            f"(failures: {self.metrics.consecutive_failures}/{self.config.failure_threshold})"
        )

    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to HALF_OPEN state."""
        old_state = self._state
        self._state = CircuitBreakerState.HALF_OPEN

        with self._metrics_lock:
            self.metrics.state = self._state
            self.metrics.state_changed_at = datetime.now(timezone.utc)
            # Reset consecutive failures to give half-open state a chance
            self.metrics.consecutive_failures = 0

        logger.info(
            f"Circuit breaker '{self.name}' HALF-OPEN: {old_state.value} -> {self._state.value} "
            f"(recovery attempt after {self.config.recovery_timeout}s)"
        )

    def _transition_to_closed(self) -> None:
        """Transition circuit breaker to CLOSED state."""
        old_state = self._state
        self._state = CircuitBreakerState.CLOSED

        with self._metrics_lock:
            self.metrics.state = self._state
            self.metrics.state_changed_at = datetime.now(timezone.utc)
            self.metrics.consecutive_failures = 0

        logger.info(
            f"Circuit breaker '{self.name}' CLOSED: {old_state.value} -> {self._state.value} "
            f"(recovery successful after {self.metrics.successful_requests} successes)"
        )

    def _should_allow_request(self) -> bool:
        """Determine if a request should be allowed through the circuit."""
        with self._state_lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True
            elif self._state == CircuitBreakerState.OPEN:
                # Check if we should attempt reset
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                    return True
                return False
            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Allow limited requests in half-open state
                return True

        return False

    def _handle_rate_limiting(self) -> None:
        """Handle rate limiting before executing request."""
        if not self.rate_limiter.acquire():
            wait_time = self.rate_limiter.get_wait_time()
            if wait_time > 0:
                with self._metrics_lock:
                    self.metrics.rate_limit_violations += 1

                logger.debug(f"Rate limiting triggered for '{self.name}', waiting {wait_time:.2f}s")
                time.sleep(wait_time)

                # Try again after waiting
                if not self.rate_limiter.acquire():
                    raise Exception("Rate limit exceeded even after waiting")

    async def call(
        self, func: Callable, *args, context: Optional[RequestContext] = None, **kwargs
    ) -> Any:
        """
        Execute function call through circuit breaker.

        Args:
            func: Function to execute
            *args: Function arguments
            context: Request context for tracking
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback result

        Raises:
            Exception: If circuit is open and no fallback available
        """
        # Create context if not provided
        if context is None:
            context = RequestContext(
                service=self.service,
                operation=getattr(func, "__name__", "unknown"),
                region=kwargs.get("region", "unknown"),
            )

        # Update total request count
        with self._metrics_lock:
            self.metrics.total_requests += 1

        # Check if request should be allowed
        if not self._should_allow_request():
            with self._metrics_lock:
                self.metrics.blocked_requests += 1

            if self.fallback_handler and self.config.enable_graceful_degradation:
                logger.info(f"Circuit breaker '{self.name}' using fallback handler")
                return await self.fallback_handler(*args, **kwargs)

            raise Exception(
                f"Circuit breaker '{self.name}' is OPEN - request blocked "
                f"(failure threshold exceeded: {self.metrics.consecutive_failures}/"
                f"{self.config.failure_threshold})"
            )

        # Handle rate limiting
        self._handle_rate_limiting()

        # Execute request with retry logic
        return await self._execute_with_retry(func, context, *args, **kwargs)

    async def _execute_with_retry(
        self, func: Callable, context: RequestContext, *args, **kwargs
    ) -> Any:
        """Execute function with intelligent retry logic."""
        last_exception = None

        for attempt in range(1, context.max_attempts + 1):
            context.attempt_number = attempt
            start_time = time.time()

            try:
                # Set timeout if specified
                if context.timeout or self.config.timeout_seconds:
                    timeout = context.timeout or self.config.timeout_seconds

                    if asyncio.iscoroutinefunction(func):
                        result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    else:
                        # For sync functions, we can't easily apply timeout in async context
                        result = func(*args, **kwargs)
                else:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                # Record success
                response_time = time.time() - start_time
                self._record_success(response_time, context)

                return result

            except Exception as e:
                last_exception = e
                response_time = time.time() - start_time

                # Record failure
                self._record_failure(e, context)

                # Don't retry on final attempt
                if attempt == context.max_attempts:
                    break

                # Calculate backoff delay
                failure_type = self._classify_failure(e)
                delay = self._calculate_backoff_delay(attempt, failure_type)

                logger.debug(
                    f"Circuit breaker '{self.name}' attempt {attempt}/{context.max_attempts} "
                    f"failed: {str(e)[:100]}... Retrying in {delay:.2f}s"
                )

                await asyncio.sleep(delay)

        # All attempts failed
        if last_exception:
            raise last_exception

        raise Exception("Request failed after all retry attempts")

    def call_sync(
        self, func: Callable, *args, context: Optional[RequestContext] = None, **kwargs
    ) -> Any:
        """
        Synchronous version of call method.

        Args:
            func: Function to execute
            *args: Function arguments
            context: Request context for tracking
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback result
        """
        # Create context if not provided
        if context is None:
            context = RequestContext(
                service=self.service,
                operation=getattr(func, "__name__", "unknown"),
                region=kwargs.get("region", "unknown"),
            )

        # Update total request count
        with self._metrics_lock:
            self.metrics.total_requests += 1

        # Check if request should be allowed
        if not self._should_allow_request():
            with self._metrics_lock:
                self.metrics.blocked_requests += 1

            if self.fallback_handler and self.config.enable_graceful_degradation:
                logger.info(f"Circuit breaker '{self.name}' using fallback handler")
                return self.fallback_handler(*args, **kwargs)

            raise Exception(
                f"Circuit breaker '{self.name}' is OPEN - request blocked "
                f"(failure threshold exceeded: {self.metrics.consecutive_failures}/"
                f"{self.config.failure_threshold})"
            )

        # Handle rate limiting
        self._handle_rate_limiting()

        # Execute request with retry logic
        return self._execute_with_retry_sync(func, context, *args, **kwargs)

    def _execute_with_retry_sync(
        self, func: Callable, context: RequestContext, *args, **kwargs
    ) -> Any:
        """Synchronous version of execute with retry."""
        last_exception = None

        for attempt in range(1, context.max_attempts + 1):
            context.attempt_number = attempt
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Record success
                response_time = time.time() - start_time
                self._record_success(response_time, context)

                return result

            except Exception as e:
                last_exception = e
                response_time = time.time() - start_time

                # Record failure
                self._record_failure(e, context)

                # Don't retry on final attempt
                if attempt == context.max_attempts:
                    break

                # Calculate backoff delay
                failure_type = self._classify_failure(e)
                delay = self._calculate_backoff_delay(attempt, failure_type)

                logger.debug(
                    f"Circuit breaker '{self.name}' attempt {attempt}/{context.max_attempts} "
                    f"failed: {str(e)[:100]}... Retrying in {delay:.2f}s"
                )

                time.sleep(delay)

        # All attempts failed
        if last_exception:
            raise last_exception

        raise Exception("Request failed after all retry attempts")

    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get current circuit breaker metrics."""
        with self._metrics_lock:
            # Update current request rate
            current_time = time.time()
            with self.rate_limiter._lock:
                self.metrics.current_request_rate = (
                    self.rate_limiter.burst_capacity - self.rate_limiter.tokens
                ) / max(current_time - self.rate_limiter.last_update, 1.0)

            return self.metrics

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        metrics = self.get_metrics()
        current_time = datetime.now(timezone.utc)

        # Analyze recent failure patterns
        with self._failure_lock:
            recent_failures_count = len(self._recent_failures)
            failure_types_recent = {}
            if self._recent_failures:
                for _, failure_type, _ in self._recent_failures:
                    failure_types_recent[failure_type.value] = (
                        failure_types_recent.get(failure_type.value, 0) + 1
                    )

        # Calculate time since last state change
        time_in_state = (current_time - metrics.state_changed_at).total_seconds()

        return {
            "circuit_breaker": {
                "name": self.name,
                "service": self.service,
                "state": metrics.state.value,
                "time_in_state_seconds": time_in_state,
                "is_healthy": metrics.is_healthy,
            },
            "request_metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "blocked_requests": metrics.blocked_requests,
                "success_rate": (metrics.successful_requests / max(metrics.total_requests, 1)),
                "failure_rate": metrics.failure_rate,
                "consecutive_failures": metrics.consecutive_failures,
            },
            "performance_metrics": {
                "avg_response_time_ms": metrics.avg_response_time * 1000,
                "p95_response_time_ms": metrics.p95_response_time * 1000,
                "current_request_rate": metrics.current_request_rate,
                "rate_limit_violations": metrics.rate_limit_violations,
            },
            "failure_analysis": {
                "recent_failures_1h": recent_failures_count,
                "failure_types_recent": failure_types_recent,
                "failure_types_total": {k.value: v for k, v in metrics.failures_by_type.items()},
                "last_failure": (
                    metrics.last_failure_time.isoformat() if metrics.last_failure_time else None
                ),
                "last_success": (
                    metrics.last_success_time.isoformat() if metrics.last_success_time else None
                ),
            },
            "configuration": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "max_requests_per_second": self.config.max_requests_per_second,
                "timeout_seconds": self.config.timeout_seconds,
            },
        }

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._state_lock:
            old_state = self._state
            self._state = CircuitBreakerState.CLOSED

        with self._metrics_lock:
            self.metrics.state = self._state
            self.metrics.consecutive_failures = 0
            self.metrics.state_changed_at = datetime.now(timezone.utc)

        logger.info(
            f"Circuit breaker '{self.name}' manually reset: {old_state.value} -> "
            f"{self._state.value}"
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Could add cleanup logic here if needed
        pass


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers with centralized monitoring.

    Provides:
    - Centralized circuit breaker creation and management
    - Global health monitoring
    - Metrics aggregation across all circuit breakers
    - Service-specific circuit breaker routing
    """

    def __init__(self):
        """Initialize circuit breaker manager."""
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = RLock()
        self._default_configs: Dict[str, CircuitBreakerConfig] = {}

        logger.info("Circuit breaker manager initialized")

    def get_or_create_circuit_breaker(
        self,
        service: str,
        operation: str,
        region: Optional[str] = None,
        config: Optional[CircuitBreakerConfig] = None,
        fallback_handler: Optional[Callable] = None,
    ) -> CircuitBreaker:
        """
        Get existing or create new circuit breaker.

        Args:
            service: AWS service name
            operation: Operation name
            region: AWS region (optional)
            config: Custom configuration
            fallback_handler: Optional fallback function

        Returns:
            Circuit breaker instance
        """
        # Create unique name for circuit breaker
        name = f"{service}:{operation}"
        if region:
            name += f":{region}"

        with self._lock:
            if name not in self._circuit_breakers:
                # Use provided config or get service-specific config
                cb_config = config or self._get_service_config(service)

                # Create new circuit breaker
                circuit_breaker = CircuitBreaker(
                    name=name,
                    service=service,
                    config=cb_config,
                    fallback_handler=fallback_handler,
                )

                self._circuit_breakers[name] = circuit_breaker
                logger.debug(f"Created new circuit breaker: {name}")

            return self._circuit_breakers[name]

    def _get_service_config(self, service: str) -> CircuitBreakerConfig:
        """Get service-specific configuration."""
        service_upper = service.upper()
        if hasattr(ServiceSpecificConfig, service_upper):
            return getattr(ServiceSpecificConfig, service_upper)
        return ServiceSpecificConfig.DEFAULT

    def get_all_circuit_breakers(self) -> Dict[str, CircuitBreaker]:
        """Get all managed circuit breakers."""
        with self._lock:
            return self._circuit_breakers.copy()

    def get_global_health_status(self) -> Dict[str, Any]:
        """Get aggregated health status across all circuit breakers."""
        with self._lock:
            circuit_breakers = self._circuit_breakers.copy()

        if not circuit_breakers:
            return {
                "global_status": "no_circuit_breakers",
                "circuit_breakers": {},
                "summary": {
                    "total_circuit_breakers": 0,
                    "healthy_count": 0,
                    "open_count": 0,
                    "half_open_count": 0,
                    "total_requests": 0,
                    "total_failures": 0,
                    "global_success_rate": 0.0,
                },
            }

        # Collect metrics from all circuit breakers
        all_status = {}
        summary = {
            "total_circuit_breakers": len(circuit_breakers),
            "healthy_count": 0,
            "open_count": 0,
            "half_open_count": 0,
            "closed_count": 0,
            "total_requests": 0,
            "total_successful_requests": 0,
            "total_failed_requests": 0,
            "total_blocked_requests": 0,
            "global_success_rate": 0.0,
        }

        for name, cb in circuit_breakers.items():
            status = cb.get_health_status()
            all_status[name] = status

            # Aggregate metrics
            req_metrics = status["request_metrics"]
            summary["total_requests"] += req_metrics["total_requests"]
            summary["total_successful_requests"] += req_metrics["successful_requests"]
            summary["total_failed_requests"] += req_metrics["failed_requests"]
            summary["total_blocked_requests"] += req_metrics["blocked_requests"]

            # Count states
            state = status["circuit_breaker"]["state"]
            if state == "closed":
                summary["closed_count"] += 1
                if status["circuit_breaker"]["is_healthy"]:
                    summary["healthy_count"] += 1
            elif state == "open":
                summary["open_count"] += 1
            elif state == "half_open":
                summary["half_open_count"] += 1

        # Calculate global success rate
        if summary["total_requests"] > 0:
            summary["global_success_rate"] = (
                summary["total_successful_requests"] / summary["total_requests"]
            )

        # Determine global status
        if summary["open_count"] > len(circuit_breakers) * 0.5:
            global_status = "critical"  # More than 50% open
        elif summary["open_count"] > 0:
            global_status = "degraded"  # Some open
        elif summary["half_open_count"] > 0:
            global_status = "recovering"  # Some recovering
        else:
            global_status = "healthy"  # All closed

        return {
            "global_status": global_status,
            "circuit_breakers": all_status,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def reset_all_circuit_breakers(self) -> int:
        """Reset all circuit breakers to CLOSED state."""
        with self._lock:
            count = 0
            for cb in self._circuit_breakers.values():
                if cb.state != CircuitBreakerState.CLOSED:
                    cb.reset()
                    count += 1

            logger.info(f"Reset {count} circuit breakers to CLOSED state")
            return count

    def cleanup_unused_circuit_breakers(self, max_idle_time: int = 3600) -> int:
        """Remove circuit breakers that haven't been used recently."""
        current_time = datetime.now(timezone.utc)
        cleanup_count = 0

        with self._lock:
            names_to_remove = []

            for name, cb in self._circuit_breakers.items():
                metrics = cb.get_metrics()

                # Check if circuit breaker has been idle
                last_activity = max(
                    metrics.last_success_time or datetime.min.replace(tzinfo=timezone.utc),
                    metrics.last_failure_time or datetime.min.replace(tzinfo=timezone.utc),
                )

                idle_time = (current_time - last_activity).total_seconds()

                if idle_time > max_idle_time:
                    names_to_remove.append(name)

            # Remove idle circuit breakers
            for name in names_to_remove:
                del self._circuit_breakers[name]
                cleanup_count += 1

        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} unused circuit breakers")

        return cleanup_count


# Global circuit breaker manager instance
_circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager instance."""
    return _circuit_breaker_manager


# Decorator for automatic circuit breaker integration
def with_circuit_breaker(
    service: str,
    operation: Optional[str] = None,
    region: Optional[str] = None,
    config: Optional[CircuitBreakerConfig] = None,
    fallback_handler: Optional[Callable] = None,
):
    """
    Decorator to wrap functions with circuit breaker protection.

    Args:
        service: AWS service name
        operation: Operation name (defaults to function name)
        region: AWS region
        config: Custom circuit breaker configuration
        fallback_handler: Optional fallback function
    """

    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__
        cb_manager = get_circuit_breaker_manager()

        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                circuit_breaker = cb_manager.get_or_create_circuit_breaker(
                    service=service,
                    operation=op_name,
                    region=region,
                    config=config,
                    fallback_handler=fallback_handler,
                )

                context = RequestContext(
                    service=service,
                    operation=op_name,
                    region=region or kwargs.get("region", "unknown"),
                )

                return await circuit_breaker.call(func, *args, context=context, **kwargs)

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs):
                circuit_breaker = cb_manager.get_or_create_circuit_breaker(
                    service=service,
                    operation=op_name,
                    region=region,
                    config=config,
                    fallback_handler=fallback_handler,
                )

                context = RequestContext(
                    service=service,
                    operation=op_name,
                    region=region or kwargs.get("region", "unknown"),
                )

                return circuit_breaker.call_sync(func, *args, context=context, **kwargs)

            return sync_wrapper

    return decorator
