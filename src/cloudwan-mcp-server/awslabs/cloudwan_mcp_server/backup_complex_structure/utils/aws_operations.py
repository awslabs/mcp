"""
Common utilities for AWS operations across tools.

This module provides reusable patterns for multi-region operations,
error handling, and resource discovery.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Callable, TypeVar
from functools import wraps
from contextlib import asynccontextmanager

from botocore.exceptions import ClientError, BotoCoreError
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # Simple fallback decorators
    def retry(**kwargs):
        def decorator(func):
            return func
        return decorator
    def stop_after_attempt(n):
        return None
    def wait_exponential(**kwargs):
        return None
    def retry_if_exception(exc_type):
        return None

from ..aws.client_manager import AWSClientManager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AWSSemaphoreManager:
    """
    Manages semaphores for AWS API concurrency control.

    This class limits the number of concurrent AWS API calls per service and region
    to prevent overwhelming AWS APIs and avoid throttling.
    """

    def __init__(self, default_limit: int = 10):
        """
        Initialize concurrency manager.

        Args:
            default_limit: Default concurrency limit per service/region
        """
        self.default_limit = default_limit
        self._service_limits: Dict[str, int] = {}
        self._region_limits: Dict[str, int] = {}
        self._service_region_limits: Dict[str, Dict[str, int]] = {}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._lock = asyncio.Lock()

    def set_service_limit(self, service: str, limit: int) -> None:
        """Set concurrency limit for a specific AWS service."""
        self._service_limits[service] = limit

    def set_region_limit(self, region: str, limit: int) -> None:
        """Set concurrency limit for a specific AWS region."""
        self._region_limits[region] = limit

    def set_service_region_limit(self, service: str, region: str, limit: int) -> None:
        """Set concurrency limit for a specific service in a specific region."""
        if service not in self._service_region_limits:
            self._service_region_limits[service] = {}
        self._service_region_limits[service][region] = limit

    def get_limit(self, service: str, region: str) -> int:
        """Get effective concurrency limit for service/region combination."""
        # Check for service+region specific limit
        if (
            service in self._service_region_limits
            and region in self._service_region_limits[service]
        ):
            return self._service_region_limits[service][region]

        # Check for service-specific limit
        if service in self._service_limits:
            return self._service_limits[service]

        # Check for region-specific limit
        if region in self._region_limits:
            return self._region_limits[region]

        # Fall back to default
        return self.default_limit

    async def get_semaphore(self, service: str, region: str) -> asyncio.Semaphore:
        """Get or create semaphore for specific service/region combination."""
        key = f"{service}:{region}"

        async with self._lock:
            if key not in self._semaphores:
                limit = self.get_limit(service, region)
                self._semaphores[key] = asyncio.Semaphore(limit)
            return self._semaphores[key]

    @asynccontextmanager
    async def acquire(self, service: str, region: str):
        """Acquire semaphore for a specific service/region combination.

        Usage:
            async with semaphore_manager.acquire("ec2", "us-west-2"):
                # Make AWS API call here
        """
        semaphore = await self.get_semaphore(service, region)
        try:
            await semaphore.acquire()
            yield
        finally:
            semaphore.release()

    def get_status(self) -> Dict[str, Any]:
        """Get status of all semaphores."""
        status = {
            "default_limit": self.default_limit,
            "service_limits": self._service_limits.copy(),
            "region_limits": self._region_limits.copy(),
            "active_semaphores": {},
        }

        for key, sem in self._semaphores.items():
            service, region = key.split(":")
            limit = self.get_limit(service, region)
            status["active_semaphores"][key] = {"limit": limit, "available": sem._value}

        return status


# Global semaphore manager instance
semaphore_manager = AWSSemaphoreManager()


class AWSOperationError(Exception):
    """Base exception for AWS operation failures."""

    pass


class MultiRegionOperationError(AWSOperationError):
    """Exception for multi-region operation failures."""

    def __init__(self, message: str, region_errors: Dict[str, str]):
        super().__init__(message)
        self.region_errors = region_errors


def handle_aws_errors(operation_name: str):
    """
    Decorator to handle common AWS errors with specific error messages.

    Args:
        operation_name: Name of the operation for error messages
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_message = e.response["Error"]["Message"]

                if error_code == "UnauthorizedOperation":
                    raise AWSOperationError(
                        f"{operation_name} failed: Insufficient permissions. "
                        f"Ensure your IAM role has the required permissions. "
                        f"Details: {error_message}"
                    )
                elif error_code == "ResourceNotFoundException":
                    raise AWSOperationError(
                        f"{operation_name} failed: Resource not found. " f"Details: {error_message}"
                    )
                elif error_code == "ThrottlingException":
                    raise AWSOperationError(
                        f"{operation_name} failed: AWS API rate limit exceeded. "
                        "Please retry after a few moments."
                    )
                else:
                    raise AWSOperationError(
                        f"{operation_name} failed with {error_code}: {error_message}"
                    )
            except BotoCoreError as e:
                raise AWSOperationError(
                    f"{operation_name} failed: AWS connection error. "
                    f"Please check your network connectivity. Details: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name}: {str(e)}", exc_info=True)
                raise AWSOperationError(f"{operation_name} failed with unexpected error: {str(e)}")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_message = e.response["Error"]["Message"]

                if error_code == "UnauthorizedOperation":
                    raise AWSOperationError(
                        f"{operation_name} failed: Insufficient permissions. "
                        f"Details: {error_message}"
                    )
                else:
                    raise AWSOperationError(
                        f"{operation_name} failed with {error_code}: {error_message}"
                    )

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


async def search_across_regions(
    aws_manager: AWSClientManager,
    regions: List[str],
    search_func: Callable,
    operation_name: str,
    max_workers: Optional[int] = None,
    service: str = "generic",
) -> Dict[str, Any]:
    """
    Execute a search operation across multiple AWS regions concurrently.

    Args:
        aws_manager: AWS client manager instance
        regions: List of regions to search
        search_func: Async function to execute in each region
        operation_name: Name of the operation for logging
        max_workers: Maximum number of concurrent workers

    Returns:
        Dictionary mapping region to search results

    Raises:
        MultiRegionOperationError: If all regions fail
    """
    results = {}
    errors = {}

    if not regions:
        raise ValueError("No regions specified for search")

    # Use ThreadPoolExecutor for concurrent execution
    max_workers = max_workers or min(len(regions), 10)

    # Configure semaphore manager with max_workers
    for region in regions:
        semaphore_manager.set_service_region_limit(service, region, max_workers)

    async def search_region(region: str) -> tuple[str, Any]:
        try:
            logger.debug(f"Searching {operation_name} in region {region}")
            # Use semaphore to control concurrency
            async with semaphore_manager.acquire(service, region):
                result = await search_func(aws_manager, region)
                return region, result
        except Exception as e:
            logger.warning(f"Error in {operation_name} for region {region}: {str(e)}")
            errors[region] = str(e)
            return region, None

    # Execute searches concurrently
    tasks = [search_region(region) for region in regions]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    for item in completed:
        if isinstance(item, Exception):
            continue
        region, result = item
        if result is not None:
            results[region] = result

    # If all regions failed, raise error
    if not results and errors:
        raise MultiRegionOperationError(f"All regions failed for {operation_name}", errors)

    return results


@asynccontextmanager
async def aws_client_context(aws_manager: AWSClientManager, service: str, region: str):
    """
    Context manager for AWS client operations with proper cleanup.

    Args:
        aws_manager: AWS client manager instance
        service: AWS service name
        region: AWS region

    Yields:
        AWS client instance
    """
    async with aws_manager.client_context(service, region) as client:
        yield client


# Set of retryable AWS error codes
RETRYABLE_AWS_ERRORS = {
    # Connection/network errors
    "ConnectionError",
    "ConnectionClosedError",
    "ReadTimeoutError",
    # Throttling/rate limiting errors
    "ThrottlingException",
    "RequestLimitExceeded",
    "TooManyRequestsException",
    "Throttling",
    "RequestThrottledException",
    "LimitExceededException",
    "RequestThrottled",
    "SlowDown",
    "PriorRequestNotComplete",
    "TransactionInProgressException",
    # Temporary service errors
    "InternalServerError",
    "ServiceUnavailable",
    "ServiceFailure",
    "InternalFailure",
    "InternalServiceError",
    # Capacity errors
    "RequestTimeout",
    "RequestTimeoutException",
    "ProvisionedThroughputExceededException",
    # Transient state errors
    "RequestExpired",
    "ExpiredTokenException",
    "TokenRefreshRequired",
}


def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an AWS exception should be retried.

    Args:
        exception: The exception to check

    Returns:
        True if the exception is retryable
    """
    if isinstance(exception, ClientError):
        error_code = exception.response.get("Error", {}).get("Code", "")
        return error_code in RETRYABLE_AWS_ERRORS
    elif isinstance(exception, (ConnectionError, TimeoutError)):
        return True
    elif isinstance(exception, BotoCoreError):
        # Most BotoCoreErrors are retryable as they relate to AWS infrastructure
        return True
    return False


def calculate_backoff(
    retry_attempt: int, initial_backoff: float = 1.0, jitter_factor: float = 0.1
) -> float:
    """
    Calculate backoff time with exponential increase and jitter.

    Args:
        retry_attempt: Current retry attempt (0-based)
        initial_backoff: Base backoff time in seconds
        jitter_factor: Random jitter factor (0-1)

    Returns:
        Backoff time in seconds
    """
    # Calculate exponential backoff: initial_backoff * 2^attempt
    backoff = initial_backoff * (2**retry_attempt)

    # Add random jitter to avoid thundering herd
    jitter = backoff * jitter_factor * random.random()

    return backoff + jitter


def with_retry(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    jitter: float = 0.1,
    service: str = None,
    region: str = None,
):
    """
    Decorator to add retry logic to AWS operations with adaptive backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff in seconds
        jitter: Jitter factor to avoid thundering herd

    Returns:
        Decorated function with retry logic
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract service and region from kwargs if not provided
            svc = service or kwargs.get("service")
            reg = region or kwargs.get("region")

            # Default values if still not found
            svc = svc or "default"
            reg = reg or "global"

            retries = 0
            last_exception = None

            # Use concurrency control if service and region are provided
            async with semaphore_manager.acquire(svc, reg):
                while retries <= max_retries:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        # Check if error is retryable
                        if retries >= max_retries or not is_retryable_error(e):
                            raise

                        last_exception = e
                        retry_delay = calculate_backoff(retries, initial_backoff, jitter)

                        logger.warning(
                            f"Retryable error in {func.__name__}, "
                            f"attempt {retries+1}/{max_retries}, "
                            f"retrying in {retry_delay:.2f}s: {str(e)}"
                        )

                        await asyncio.sleep(retry_delay)
                        retries += 1

                # If we've exhausted retries, raise the last exception
                raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            retries = 0
            last_exception = None

            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Check if error is retryable
                    if retries >= max_retries or not is_retryable_error(e):
                        raise

                    last_exception = e
                    retry_delay = calculate_backoff(retries, initial_backoff, jitter)

                    logger.warning(
                        f"Retryable error in {func.__name__}, "
                        f"attempt {retries+1}/{max_retries}, "
                        f"retrying in {retry_delay:.2f}s: {str(e)}"
                    )

                    time.sleep(retry_delay)
                    retries += 1

            # If we've exhausted retries, raise the last exception
            raise last_exception

        return wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception(is_retryable_error),
)
async def retry_aws_operation(operation: Callable, *args, **kwargs) -> Any:
    """
    Retry an AWS operation with exponential backoff using tenacity.

    Args:
        operation: The operation to retry
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation

    Returns:
        Result of the operation
    """
    return await operation(*args, **kwargs)


def validate_resource_constraints(
    resource_type: str, resource_id: str, allowed_patterns: List[str]
) -> bool:
    """
    Validate resource against allowed patterns.

    Args:
        resource_type: Type of AWS resource
        resource_id: Resource identifier
        allowed_patterns: List of allowed patterns

    Returns:
        True if resource matches allowed patterns
    """
    import re

    for pattern in allowed_patterns:
        if re.match(pattern, resource_id):
            return True
    return False


def batch_aws_operations(items: List[T], batch_size: int = 25) -> List[List[T]]:
    """
    Split items into batches for AWS API operations.

    Many AWS APIs have limits on batch operations (e.g., 25 items).

    Args:
        items: List of items to batch
        batch_size: Maximum items per batch

    Returns:
        List of batches
    """
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


class AWSRateLimiter:
    """
    Rate limiter for AWS API calls to prevent throttling.

    Uses token bucket algorithm to rate limit calls to AWS APIs.
    Adapts to AWS throttling responses by reducing token refill rate.
    """

    def __init__(self, max_calls_per_second: float = 10.0, bucket_size: int = 20):
        """
        Initialize rate limiter.

        Args:
            max_calls_per_second: Maximum calls per second
            bucket_size: Maximum number of tokens in the bucket
        """
        self.max_calls_per_second = max_calls_per_second
        self.bucket_size = bucket_size
        self.tokens = bucket_size
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
        self.throttle_count = 0
        self.throttle_reset_time = 0

    async def acquire(self):
        """
        Acquire a token for an AWS API call.

        Blocks until a token is available.
        """
        async with self.lock:
            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - self.last_refill
            self.last_refill = now

            # Calculate token refill rate with adaptive throttling
            refill_rate = self.max_calls_per_second
            if self.throttle_count > 0:
                # Reduce refill rate when throttling occurs
                backoff_factor = min(0.5, 0.1 * self.throttle_count)
                refill_rate = max(0.5, refill_rate * (1 - backoff_factor))

                # Reset throttle count after a period
                if now > self.throttle_reset_time:
                    self.throttle_count = max(0, self.throttle_count - 1)

            # Add tokens based on elapsed time and rate
            tokens_to_add = elapsed * refill_rate
            self.tokens = min(self.bucket_size, self.tokens + tokens_to_add)

            # If no tokens available, wait
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / refill_rate
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 1  # We'll use this token immediately

            # Consume token
            self.tokens -= 1

    def record_throttling(self):
        """Record a throttling event to adjust future rate limiting."""
        self.throttle_count += 1
        self.throttle_reset_time = time.time() + 60  # Reset after a minute

        # Reduce available tokens immediately
        self.tokens = max(0, self.tokens - 5)


def format_aws_tags(tags: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Convert AWS tag format to simple dictionary.

    Args:
        tags: AWS tags in [{'Key': 'k', 'Value': 'v'}] format

    Returns:
        Dictionary mapping tag keys to values
    """
    return {tag.get("Key", ""): tag.get("Value", "") for tag in tags if "Key" in tag}


async def execute_with_concurrency_control(
    func: Callable, service: str, region: str, *args, **kwargs
) -> Any:
    """
    Execute AWS operation with concurrency control.

    Args:
        func: AWS operation function to execute
        service: AWS service name
        region: AWS region
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the AWS operation
    """
    async with semaphore_manager.acquire(service, region):
        try:
            result = await func(*args, **kwargs)
            return result
        except ClientError as e:
            # Check if this is a throttling error
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in [
                "ThrottlingException",
                "RequestLimitExceeded",
                "TooManyRequestsException",
                "Throttling",
            ]:
                # Record throttling for adaptive rate limiting
                logger.warning(f"Throttling occurred for {service} in {region}: {str(e)}")
                # Temporarily reduce concurrency limit
                current_limit = semaphore_manager.get_limit(service, region)
                if current_limit > 1:
                    new_limit = max(1, current_limit // 2)  # Reduce by 50%
                    semaphore_manager.set_service_region_limit(service, region, new_limit)
                    logger.info(
                        f"Reduced concurrency limit for {service}:{region} from {current_limit} to {new_limit}"
                    )
            raise


def configure_concurrency_limits(config: Dict[str, Any]) -> None:
    """
    Configure concurrency limits from configuration.

    Args:
        config: Dictionary with concurrency configuration
    """
    # Set default limit
    if "default_limit" in config:
        semaphore_manager.default_limit = config["default_limit"]

    # Set service-specific limits
    for service, limit in config.get("service_limits", {}).items():
        semaphore_manager.set_service_limit(service, limit)

    # Set region-specific limits
    for region, limit in config.get("region_limits", {}).items():
        semaphore_manager.set_region_limit(region, limit)

    # Set service-region specific limits
    for service, regions in config.get("service_region_limits", {}).items():
        for region, limit in regions.items():
            semaphore_manager.set_service_region_limit(service, region, limit)

    logger.info(f"Configured AWS concurrency limits: {semaphore_manager.get_status()}")


def parse_arn(arn: str) -> Dict[str, str]:
    """
    Parse AWS ARN into components.

    Args:
        arn: AWS ARN string

    Returns:
        Dictionary with ARN components
    """
    parts = arn.split(":")
    if len(parts) < 6:
        raise ValueError(f"Invalid ARN format: {arn}")

    return {
        "arn": parts[0],
        "partition": parts[1],
        "service": parts[2],
        "region": parts[3],
        "account": parts[4],
        "resource": ":".join(parts[5:]),
    }
