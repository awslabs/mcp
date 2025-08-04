"""
Circuit Breaker Pattern Implementation for AWS API Calls.

This module provides a robust circuit breaker implementation to improve
resilience when making AWS API calls. The circuit breaker prevents
cascading failures by temporarily suspending operations to a failing service.

Features:
- Service and region specific circuit breakers
- Configurable thresholds, timeouts, and back-off strategies
- Comprehensive state tracking and metrics collection
- Automatic retry with exponential back-off
- Health check mechanism for circuit recovery
- Context manager support for easy integration
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Generic,
)

from botocore.exceptions import (
    ClientError,
    ConnectionError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
    ServiceNotAvailableError,
    ThrottlingError,
    RequestTimeoutException,
)

logger = logging.getLogger(__name__)

# Generic type for function return value
T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Normal operation, requests pass through
    OPEN = "OPEN"  # Circuit is tripped, requests fail fast
    HALF_OPEN = "HALF_OPEN"  # Testing if service is healthy again


class CircuitBreakerError(Exception):
    """Error raised when circuit is open."""

    pass


@dataclass
class CircuitBreakerMetrics:
    """Performance and health metrics for a circuit breaker."""

    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    rejection_count: int = 0
    retry_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_latency_ms: float = 0
    avg_latency_ms: float = 0
    trip_count: int = 0
    state_changes: List[Tuple[datetime, CircuitState]] = field(default_factory=list)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Number of failures to trip the circuit
    timeout_seconds: int = 60  # Time the circuit stays open before attempting recovery
    half_open_max_calls: int = 3  # Max calls in half-open state
    success_threshold: int = 2  # Consecutive successes to close circuit from half-open
    retry_max_attempts: int = 3  # Max retry attempts
    retry_initial_delay_ms: int = 100  # Initial delay between retries
    retry_backoff_factor: float = 2.0  # Exponential backoff factor
    retry_max_delay_ms: int = 10000  # Maximum delay between retries
    retry_jitter_factor: float = 0.2  # Random jitter factor for retry delays
    track_latency: bool = True  # Track API call latency


class CircuitBreaker(Generic[T]):
    """
    Circuit breaker implementation for AWS API calls.

    The circuit breaker pattern prevents system overload by failing fast
    when a downstream service is experiencing issues.

    Attributes:
        name: Circuit breaker identifier
        config: Circuit breaker configuration
        state: Current state (CLOSED, OPEN, HALF_OPEN)
        metrics: Performance and health metrics
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        expected_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker identifier (typically service:region)
            config: Circuit breaker configuration
            expected_exceptions: List of exception types to handle
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # Default exception types to monitor (can be extended)
        self.expected_exceptions = expected_exceptions or [
            ClientError,
            ConnectionError,
            ConnectTimeoutError,
            EndpointConnectionError,
            ReadTimeoutError,
            ServiceNotAvailableError,
            ThrottlingError,
            RequestTimeoutException,
        ]

        # Circuit state
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.now(timezone.utc)
        self.last_error: Optional[Exception] = None
        self.half_open_calls = 0

        # Metrics
        self.metrics = CircuitBreakerMetrics()
        self.metrics.state_changes.append((self.last_state_change, self.state))

        # Locking mechanism for thread safety
        self._lock = RLock()

        logger.info(f"Circuit breaker '{name}' initialized in {self.state} state")

    def __call__(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Call wrapped function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: When circuit is open
            Exception: Original exception from wrapped function
        """
        # Check circuit state first
        with self._lock:
            if self.state == CircuitState.OPEN:
                # Check if timeout has elapsed to transition to half-open
                if self._should_transition_to_half_open():
                    self._transition_to_half_open()
                else:
                    self.metrics.rejection_count += 1
                    raise CircuitBreakerError(
                        f"Circuit '{self.name}' is OPEN. "
                        f"Last failure: {self._format_last_failure()}"
                    )

            if (
                self.state == CircuitState.HALF_OPEN
                and self.half_open_calls >= self.config.half_open_max_calls
            ):
                self.metrics.rejection_count += 1
                raise CircuitBreakerError(
                    f"Circuit '{self.name}' is HALF_OPEN and at test call limit. "
                    f"Waiting for results of previous test calls."
                )

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1

        # Execute function with retry logic
        start_time = time.time()
        retry_count = 0
        last_exception = None

        while retry_count <= self.config.retry_max_attempts:
            try:
                if retry_count > 0:
                    # Calculate backoff delay with jitter
                    delay = min(
                        self.config.retry_max_delay_ms,
                        self.config.retry_initial_delay_ms
                        * (self.config.retry_backoff_factor ** (retry_count - 1)),
                    )
                    # Add jitter to prevent thundering herd
                    jitter = delay * self.config.retry_jitter_factor * (2 * (0.5 - time.time() % 1))
                    delay_with_jitter = max(0, delay + jitter)

                    # Log retry attempt
                    logger.debug(
                        f"Circuit '{self.name}' retry {retry_count}/{self.config.retry_max_attempts} "
                        f"after {delay_with_jitter:.2f}ms"
                    )
                    time.sleep(delay_with_jitter / 1000)

                    self.metrics.retry_count += 1

                # Execute the function
                result = func(*args, **kwargs)

                # Record execution time
                execution_time_ms = (time.time() - start_time) * 1000

                # Handle successful call
                self._handle_success(execution_time_ms)

                return result

            except tuple(self.expected_exceptions) as e:
                last_exception = e
                retry_count += 1

                # If this is the last retry attempt or circuit is in half-open state
                if (
                    retry_count > self.config.retry_max_attempts
                    or self.state == CircuitState.HALF_OPEN
                ):
                    # Handle failure after all retries
                    self._handle_failure(e)

                    # In half-open state, a single failure returns to open state
                    if self.state == CircuitState.HALF_OPEN:
                        self._transition_to_open()

                    # Raise the original exception
                    raise e

            except Exception as e:
                # For unexpected exceptions, record failure but don't retry
                self._handle_failure(e)
                raise e

        # Should never reach here due to the loop logic, but just in case
        if last_exception:
            raise last_exception

        # Type checker hint - we'll never get here
        raise RuntimeError("Unexpected end of circuit breaker execution")  # pragma: no cover

    async def __async_call__(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Call wrapped async function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: When circuit is open
            Exception: Original exception from wrapped function
        """
        # Check circuit state first
        with self._lock:
            if self.state == CircuitState.OPEN:
                # Check if timeout has elapsed to transition to half-open
                if self._should_transition_to_half_open():
                    self._transition_to_half_open()
                else:
                    self.metrics.rejection_count += 1
                    raise CircuitBreakerError(
                        f"Circuit '{self.name}' is OPEN. "
                        f"Last failure: {self._format_last_failure()}"
                    )

            if (
                self.state == CircuitState.HALF_OPEN
                and self.half_open_calls >= self.config.half_open_max_calls
            ):
                self.metrics.rejection_count += 1
                raise CircuitBreakerError(
                    f"Circuit '{self.name}' is HALF_OPEN and at test call limit. "
                    f"Waiting for results of previous test calls."
                )

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1

        # Execute function with retry logic
        start_time = time.time()
        retry_count = 0
        last_exception = None

        while retry_count <= self.config.retry_max_attempts:
            try:
                if retry_count > 0:
                    # Calculate backoff delay with jitter
                    delay = min(
                        self.config.retry_max_delay_ms,
                        self.config.retry_initial_delay_ms
                        * (self.config.retry_backoff_factor ** (retry_count - 1)),
                    )
                    # Add jitter to prevent thundering herd
                    jitter = delay * self.config.retry_jitter_factor * (2 * (0.5 - time.time() % 1))
                    delay_with_jitter = max(0, delay + jitter)

                    # Log retry attempt
                    logger.debug(
                        f"Circuit '{self.name}' retry {retry_count}/{self.config.retry_max_attempts} "
                        f"after {delay_with_jitter:.2f}ms"
                    )
                    await asyncio.sleep(delay_with_jitter / 1000)

                    self.metrics.retry_count += 1

                # Execute the async function
                result = await func(*args, **kwargs)

                # Record execution time
                execution_time_ms = (time.time() - start_time) * 1000

                # Handle successful call
                self._handle_success(execution_time_ms)

                return result

            except tuple(self.expected_exceptions) as e:
                last_exception = e
                retry_count += 1

                # If this is the last retry attempt or circuit is in half-open state
                if (
                    retry_count > self.config.retry_max_attempts
                    or self.state == CircuitState.HALF_OPEN
                ):
                    # Handle failure after all retries
                    self._handle_failure(e)

                    # In half-open state, a single failure returns to open state
                    if self.state == CircuitState.HALF_OPEN:
                        self._transition_to_open()

                    # Raise the original exception
                    raise e

            except Exception as e:
                # For unexpected exceptions, record failure but don't retry
                self._handle_failure(e)
                raise e

        # Should never reach here due to the loop logic, but just in case
        if last_exception:
            raise last_exception

        # Type checker hint - we'll never get here
        raise RuntimeError("Unexpected end of circuit breaker execution")  # pragma: no cover

    def _handle_success(self, execution_time_ms: float) -> None:
        """
        Handle successful function execution.

        Args:
            execution_time_ms: Execution time in milliseconds
        """
        with self._lock:
            self.metrics.success_count += 1
            self.metrics.consecutive_successes += 1
            self.metrics.consecutive_failures = 0
            self.metrics.last_success_time = datetime.now(timezone.utc)

            if self.config.track_latency:
                self.metrics.total_latency_ms += execution_time_ms
                self.metrics.avg_latency_ms = (
                    self.metrics.total_latency_ms / self.metrics.success_count
                )

            # In half-open state, check if we've reached success threshold
            if (
                self.state == CircuitState.HALF_OPEN
                and self.metrics.consecutive_successes >= self.config.success_threshold
            ):
                self._transition_to_closed()

    def _handle_failure(self, exception: Exception) -> None:
        """
        Handle function execution failure.

        Args:
            exception: The exception that occurred
        """
        with self._lock:
            self.last_error = exception
            self.metrics.failure_count += 1
            self.metrics.consecutive_failures += 1
            self.metrics.consecutive_successes = 0
            self.metrics.last_failure_time = datetime.now(timezone.utc)

            # Check if we need to timeout
            if isinstance(
                exception,
                (ReadTimeoutError, ConnectTimeoutError, RequestTimeoutException),
            ):
                self.metrics.timeout_count += 1

            # In closed state, check if we need to trip the circuit
            if (
                self.state == CircuitState.CLOSED
                and self.metrics.consecutive_failures >= self.config.failure_threshold
            ):
                self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition the circuit to OPEN state."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now(timezone.utc)
        self.metrics.state_changes.append((self.last_state_change, self.state))
        self.metrics.trip_count += 1

        logger.warning(
            f"Circuit '{self.name}' tripped from {old_state} to {self.state} "
            f"after {self.metrics.consecutive_failures} consecutive failures. "
            f"Last error: {self._format_last_failure()}"
        )

    def _transition_to_half_open(self) -> None:
        """Transition the circuit to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = datetime.now(timezone.utc)
        self.half_open_calls = 0
        self.metrics.state_changes.append((self.last_state_change, self.state))

        logger.info(
            f"Circuit '{self.name}' transitioned from {old_state} to {self.state} "
            f"after timeout period. Testing service with up to {self.config.half_open_max_calls} calls."
        )

    def _transition_to_closed(self) -> None:
        """Transition the circuit to CLOSED state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.now(timezone.utc)
        self.half_open_calls = 0
        self.metrics.state_changes.append((self.last_state_change, self.state))

        logger.info(
            f"Circuit '{self.name}' recovered from {old_state} to {self.state} "
            f"after {self.metrics.consecutive_successes} consecutive successes."
        )

    def _should_transition_to_half_open(self) -> bool:
        """Check if circuit should transition from OPEN to HALF_OPEN."""
        if self.state != CircuitState.OPEN:
            return False

        elapsed = (datetime.now(timezone.utc) - self.last_state_change).total_seconds()
        return elapsed >= self.config.timeout_seconds

    def _format_last_failure(self) -> str:
        """Format the last failure for logging."""
        if not self.last_error:
            return "Unknown error"

        if isinstance(self.last_error, ClientError):
            # Extract error code and message from ClientError
            error_code = self.last_error.response.get("Error", {}).get("Code", "UnknownError")
            error_message = self.last_error.response.get("Error", {}).get(
                "Message", str(self.last_error)
            )
            return f"{error_code}: {error_message}"

        return str(self.last_error)

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.last_state_change = datetime.now(timezone.utc)
            self.half_open_calls = 0
            self.last_error = None

            # Reset metrics
            self.metrics = CircuitBreakerMetrics()
            self.metrics.state_changes.append((self.last_state_change, self.state))

            logger.info(f"Circuit '{self.name}' reset to {self.state} state")

    def force_open(self) -> None:
        """Force circuit to OPEN state."""
        with self._lock:
            old_state = self.state
            self.state = CircuitState.OPEN
            self.last_state_change = datetime.now(timezone.utc)
            self.metrics.state_changes.append((self.last_state_change, self.state))

            logger.warning(
                f"Circuit '{self.name}' manually forced from {old_state} to {self.state}"
            )

    def force_closed(self) -> None:
        """Force circuit to CLOSED state."""
        with self._lock:
            old_state = self.state
            self.state = CircuitState.CLOSED
            self.last_state_change = datetime.now(timezone.utc)
            self.half_open_calls = 0
            self.metrics.state_changes.append((self.last_state_change, self.state))

            logger.warning(
                f"Circuit '{self.name}' manually forced from {old_state} to {self.state}"
            )

    def get_health(self) -> Dict[str, Any]:
        """Get detailed health and metrics information."""
        with self._lock:
            total_calls = self.metrics.success_count + self.metrics.failure_count
            success_rate = self.metrics.success_count / total_calls if total_calls > 0 else 1.0

            return {
                "name": self.name,
                "state": self.state,
                "last_state_change": self.last_state_change.isoformat(),
                "state_age_seconds": (
                    datetime.now(timezone.utc) - self.last_state_change
                ).total_seconds(),
                "calls": {
                    "success": self.metrics.success_count,
                    "failure": self.metrics.failure_count,
                    "timeout": self.metrics.timeout_count,
                    "rejection": self.metrics.rejection_count,
                    "retry": self.metrics.retry_count,
                    "total": total_calls,
                    "success_rate": success_rate,
                },
                "consecutive": {
                    "success": self.metrics.consecutive_successes,
                    "failure": self.metrics.consecutive_failures,
                },
                "latency_ms": {
                    "avg": self.metrics.avg_latency_ms,
                    "total": self.metrics.total_latency_ms,
                },
                "trips": self.metrics.trip_count,
                "last_failure": {
                    "time": (
                        self.metrics.last_failure_time.isoformat()
                        if self.metrics.last_failure_time
                        else None
                    ),
                    "error": self._format_last_failure() if self.last_error else None,
                },
                "last_success": {
                    "time": (
                        self.metrics.last_success_time.isoformat()
                        if self.metrics.last_success_time
                        else None
                    ),
                },
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "timeout_seconds": self.config.timeout_seconds,
                    "success_threshold": self.config.success_threshold,
                    "retry_max_attempts": self.config.retry_max_attempts,
                },
            }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    This class provides a centralized registry for creating and retrieving
    circuit breakers by service and region, ensuring consistent configuration
    across the application.
    """

    def __init__(
        self,
        default_config: Optional[CircuitBreakerConfig] = None,
        service_configs: Optional[Dict[str, CircuitBreakerConfig]] = None,
    ):
        """
        Initialize the circuit breaker registry.

        Args:
            default_config: Default configuration for all circuit breakers
            service_configs: Service-specific configurations
        """
        self.default_config = default_config or CircuitBreakerConfig()
        self.service_configs = service_configs or {}

        # Circuit breaker instances
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._lock = RLock()

        logger.info("Circuit breaker registry initialized")

    def get_circuit_breaker(
        self, service: str, region: str, operation: Optional[str] = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker for the specified service and region.

        Args:
            service: AWS service name
            region: AWS region
            operation: Optional operation name for fine-grained circuit breakers

        Returns:
            CircuitBreaker instance
        """
        if operation:
            key = f"{service}:{region}:{operation}"
        else:
            key = f"{service}:{region}"

        with self._lock:
            if key not in self._circuits:
                # Get appropriate config
                config = self.service_configs.get(service, self.default_config)

                # Create new circuit breaker
                self._circuits[key] = CircuitBreaker(name=key, config=config)
                logger.debug(f"Created new circuit breaker for {key}")

            return self._circuits[key]

    def reset_all(self) -> None:
        """Reset all circuit breakers to their initial state."""
        with self._lock:
            for circuit in self._circuits.values():
                circuit.reset()

        logger.info(f"Reset {len(self._circuits)} circuit breakers")

    def get_all_circuits(self) -> Dict[str, CircuitBreaker]:
        """Get all registered circuit breakers."""
        with self._lock:
            return self._circuits.copy()

    def get_health_report(self) -> Dict[str, Any]:
        """Get health report for all circuit breakers."""
        with self._lock:
            circuits = self._circuits.copy()

        report = {
            "summary": {
                "total_circuits": len(circuits),
                "open_circuits": sum(1 for c in circuits.values() if c.state == CircuitState.OPEN),
                "half_open_circuits": sum(
                    1 for c in circuits.values() if c.state == CircuitState.HALF_OPEN
                ),
                "closed_circuits": sum(
                    1 for c in circuits.values() if c.state == CircuitState.CLOSED
                ),
                "total_trips": sum(c.metrics.trip_count for c in circuits.values()),
                "total_success": sum(c.metrics.success_count for c in circuits.values()),
                "total_failure": sum(c.metrics.failure_count for c in circuits.values()),
            },
            "circuits": {name: circuit.get_health() for name, circuit in circuits.items()},
        }

        # Calculate overall success rate
        total_calls = report["summary"]["total_success"] + report["summary"]["total_failure"]
        success_rate = report["summary"]["total_success"] / total_calls if total_calls > 0 else 1.0
        report["summary"]["overall_success_rate"] = success_rate

        return report


# Global circuit breaker registry
default_registry = CircuitBreakerRegistry()
