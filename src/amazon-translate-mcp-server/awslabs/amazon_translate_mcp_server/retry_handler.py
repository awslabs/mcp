# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Retry logic with exponential backoff for Amazon Translate MCP Server.

This module provides comprehensive retry mechanisms for handling transient
failures, rate limiting, and service unavailability with configurable
exponential backoff strategies.
"""

import asyncio
import logging
import random
import time
from .exceptions import (
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    TranslateException,
    map_aws_error,
)
from functools import wraps
from typing import Any, Callable, List, Optional, Type


logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay in seconds for first retry
            max_delay: Maximum delay in seconds between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
            retryable_exceptions: List of exception types that should trigger retries

        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            RateLimitError,
            ServiceUnavailableError,
            TimeoutError,
        ]

    def calculate_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """Calculate delay for the given attempt number.

        Args:
            attempt: Current attempt number (0-based)
            retry_after: Optional retry_after value from rate limiting

        Returns:
            Delay in seconds

        """
        if retry_after is not None:
            # Use server-specified retry_after with some jitter
            delay = float(retry_after)
            if self.jitter:
                delay += random.uniform(0, min(delay * 0.1, 5.0))  # nosec B311 - jitter timing only
            return min(delay, self.max_delay)

        # Calculate exponential backoff delay
        delay = self.base_delay * (self.exponential_base**attempt)

        # Add jitter to prevent thundering herd
        if self.jitter:
            delay += random.uniform(0, delay * 0.1)  # nosec B311 - jitter timing only

        return min(delay, self.max_delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should trigger a retry.

        Args:
            exception: The exception that occurred
            attempt: Current attempt number (0-based)

        Returns:
            True if the operation should be retried

        """
        if attempt >= self.max_attempts:
            return False

        # Check if exception type is retryable
        for retryable_type in self.retryable_exceptions:
            if isinstance(exception, retryable_type):
                return True

        # Check for specific AWS errors that should be retried
        from botocore.exceptions import ClientError

        if isinstance(exception, ClientError) or hasattr(exception, 'response'):
            error_code = getattr(exception, 'response', {}).get('Error', {}).get('Code', '')
            retryable_aws_errors = [
                'ThrottlingException',
                'TooManyRequestsException',
                'ServiceUnavailableException',
                'InternalServiceException',
                'RequestTimeout',
                'RequestTimeoutException',
            ]
            if error_code in retryable_aws_errors:
                return True

        return False


class RetryHandler:
    """Handles retry logic with exponential backoff."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry handler.

        Args:
            config: Retry configuration, uses default if None

        """
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')

    def retry(self, func: Callable, *args, correlation_id: Optional[str] = None, **kwargs) -> Any:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            correlation_id: Optional correlation ID for tracking
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            TranslateException: If all retry attempts fail

        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                self.logger.debug(
                    f'Executing function {func.__name__}, attempt {attempt + 1}/{self.config.max_attempts}',
                    extra={'correlation_id': correlation_id},
                )
                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                # Map AWS errors to custom exceptions
                if not isinstance(e, TranslateException):
                    e = map_aws_error(e, correlation_id)

                # Check if we should retry
                if not self.config.should_retry(e, attempt):
                    self.logger.error(
                        f'Function {func.__name__} failed with non-retryable error: {e}',
                        extra={'correlation_id': correlation_id},
                    )
                    raise e

                # Calculate delay for next attempt
                retry_after = getattr(e, 'retry_after', None)
                delay = self.config.calculate_delay(attempt, retry_after)

                self.logger.warning(
                    f'Function {func.__name__} failed (attempt {attempt + 1}/{self.config.max_attempts}), '
                    f'retrying in {delay:.2f}s: {e}',
                    extra={'correlation_id': correlation_id},
                )

                # Wait before retry (except on last attempt)
                if attempt < self.config.max_attempts - 1:
                    time.sleep(delay)

        # All attempts failed
        self.logger.error(
            f'Function {func.__name__} failed after {self.config.max_attempts} attempts',
            extra={'correlation_id': correlation_id},
        )

        if isinstance(last_exception, TranslateException):
            raise last_exception
        elif last_exception is not None:
            raise map_aws_error(last_exception, correlation_id)
        else:
            raise TranslateException('All retry attempts failed with no recorded exception')

    async def async_retry(
        self, func: Callable, *args, correlation_id: Optional[str] = None, **kwargs
    ) -> Any:
        """Execute async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            correlation_id: Optional correlation ID for tracking
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            TranslateException: If all retry attempts fail

        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                self.logger.debug(
                    f'Executing async function {func.__name__}, attempt {attempt + 1}/{self.config.max_attempts}',
                    extra={'correlation_id': correlation_id},
                )
                return await func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                # Map AWS errors to custom exceptions
                if not isinstance(e, TranslateException):
                    e = map_aws_error(e, correlation_id)

                # Check if we should retry
                if not self.config.should_retry(e, attempt):
                    self.logger.error(
                        f'Async function {func.__name__} failed with non-retryable error: {e}',
                        extra={'correlation_id': correlation_id},
                    )
                    raise e

                # Calculate delay for next attempt
                retry_after = getattr(e, 'retry_after', None)
                delay = self.config.calculate_delay(attempt, retry_after)

                self.logger.warning(
                    f'Async function {func.__name__} failed (attempt {attempt + 1}/{self.config.max_attempts}), '
                    f'retrying in {delay:.2f}s: {e}',
                    extra={'correlation_id': correlation_id},
                )

                # Wait before retry (except on last attempt)
                if attempt < self.config.max_attempts - 1:
                    await asyncio.sleep(delay)

        # All attempts failed
        self.logger.error(
            f'Async function {func.__name__} failed after {self.config.max_attempts} attempts',
            extra={'correlation_id': correlation_id},
        )

        if isinstance(last_exception, TranslateException):
            raise last_exception
        elif last_exception is not None:
            raise map_aws_error(last_exception, correlation_id)
        else:
            raise TranslateException('All retry attempts failed with no recorded exception')


def with_retry(config: Optional[RetryConfig] = None, correlation_id_param: str = 'correlation_id'):
    """Add retry logic to functions.

    Args:
        config: Retry configuration
        correlation_id_param: Name of parameter containing correlation ID

    Returns:
        Decorated function with retry logic

    """

    def decorator(func: Callable) -> Callable:
        retry_handler = RetryHandler(config)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract correlation ID from parameters
            correlation_id = kwargs.pop(correlation_id_param, None)

            return retry_handler.retry(func, *args, correlation_id=correlation_id, **kwargs)

        return wrapper

    return decorator


def with_async_retry(
    config: Optional[RetryConfig] = None, correlation_id_param: str = 'correlation_id'
):
    """Add retry logic to async functions.

    Args:
        config: Retry configuration
        correlation_id_param: Name of parameter containing correlation ID

    Returns:
        Decorated async function with retry logic

    """

    def decorator(func: Callable) -> Callable:
        retry_handler = RetryHandler(config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract correlation ID from parameters
            correlation_id = kwargs.pop(correlation_id_param, None)

            return await retry_handler.async_retry(
                func, *args, correlation_id=correlation_id, **kwargs
            )

        return wrapper

    return decorator


# Default retry configurations for different operation types
DEFAULT_RETRY_CONFIG = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=60.0)

BATCH_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=300.0,  # 5 minutes max delay for batch operations
)

TERMINOLOGY_RETRY_CONFIG = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=30.0)

TRANSLATION_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,  # Shorter delays for real-time translation
)
