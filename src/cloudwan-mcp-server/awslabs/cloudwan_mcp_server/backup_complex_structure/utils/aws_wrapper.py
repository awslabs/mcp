"""
Central AWS operation wrapper with unified error handling.

This module provides a centralized wrapper for AWS operations with:
- Retry logic with exponential backoff
- Rate limiting and concurrency control
- Comprehensive error classification and handling
- Performance monitoring and metrics
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, TypeVar

from botocore.exceptions import ClientError, BotoCoreError

from .aws_operations import (
    semaphore_manager,
    is_retryable_error,
    calculate_backoff,
    AWSOperationError,
    MultiRegionOperationError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AWSOperation:
    """
    AWS operation wrapper with comprehensive resilience features.

    This class provides a unified way to execute AWS operations with:
    - Retries with exponential backoff
    - Concurrency control and rate limiting
    - Error handling and classification
    - Metrics and performance monitoring
    - Cross-region operations

    Usage:
        aws_op = AWSOperation(aws_manager)
        result = await aws_op.execute(
            service="ec2",
            operation="describe_instances",
            region="us-west-2",
            kwargs={"InstanceIds": ["i-1234567890abcdef0"]}
        )
    """

    def __init__(
        self,
        aws_manager: Any,
        default_concurrency: int = 10,
        default_retries: int = 3,
        default_backoff: float = 1.0,
        default_jitter: float = 0.1,
        enable_metrics: bool = True,
    ):
        """
        Initialize AWS operation wrapper.

        Args:
            aws_manager: AWS client manager instance
            default_concurrency: Default concurrency limit per service/region
            default_retries: Default number of retry attempts
            default_backoff: Default initial backoff time in seconds
            default_jitter: Default jitter factor for backoff calculation
            enable_metrics: Whether to enable performance metrics
        """
        self.aws_manager = aws_manager
        self.default_concurrency = default_concurrency
        self.default_retries = default_retries
        self.default_backoff = default_backoff
        self.default_jitter = default_jitter
        self.enable_metrics = enable_metrics

        # Configure default concurrency
        semaphore_manager.default_limit = default_concurrency

    async def execute(
        self,
        service: str,
        operation: str,
        region: str,
        kwargs: Dict[str, Any] = None,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None,
        jitter: Optional[float] = None,
    ) -> Any:
        """
        Execute AWS operation with resilience features.

        Args:
            service: AWS service name
            operation: AWS operation name
            region: AWS region
            kwargs: Operation keyword arguments
            max_retries: Maximum retry attempts (overrides default)
            initial_backoff: Initial backoff time in seconds (overrides default)
            jitter: Jitter factor (overrides default)

        Returns:
            Operation result

        Raises:
            AWSOperationError: Operation failed after retries
        """
        # Set default values if not provided
        kwargs = kwargs or {}
        max_retries = max_retries or self.default_retries
        initial_backoff = initial_backoff or self.default_backoff
        jitter = jitter or self.default_jitter

        # Get start time for performance metrics
        start_time = time.time()

        try:
            async with semaphore_manager.acquire(service, region):
                # Get async AWS client - CRITICAL FIX: Use get_client_async() instead of get_client()
                client = await self.aws_manager.get_client_async(service, region)

                # Get operation method
                operation_func = getattr(client, operation, None)
                if not operation_func:
                    raise AWSOperationError(
                        f"Operation {operation} not found for service {service}"
                    )

                # Execute with retry
                retries = 0
                while True:
                    try:
                        result = await operation_func(**kwargs)
                        # Record successful operation
                        if self.enable_metrics:
                            self._record_metrics(
                                service,
                                operation,
                                region,
                                time.time() - start_time,
                                True,
                            )
                        return result

                    except Exception as e:
                        # Check if error is retryable and we have retries left
                        if retries >= max_retries or not is_retryable_error(e):
                            # Record failed operation
                            if self.enable_metrics:
                                self._record_metrics(
                                    service,
                                    operation,
                                    region,
                                    time.time() - start_time,
                                    False,
                                )

                            # Rethrow exception with context
                            self._handle_exception(e, service, operation, region)

                        # Calculate backoff with jitter
                        retry_delay = calculate_backoff(retries, initial_backoff, jitter)

                        logger.warning(
                            f"Retryable error in {service}.{operation} (region {region}), "
                            f"attempt {retries+1}/{max_retries}, "
                            f"retrying in {retry_delay:.2f}s: {str(e)}"
                        )

                        await asyncio.sleep(retry_delay)
                        retries += 1

        except AWSOperationError:
            # Just re-raise our custom exception
            raise

        except Exception as e:
            # Record failed operation
            if self.enable_metrics:
                self._record_metrics(service, operation, region, time.time() - start_time, False)

            # Handle unexpected exceptions
            self._handle_exception(e, service, operation, region)

    async def execute_multi_region(
        self,
        service: str,
        operation: str,
        regions: List[str],
        kwargs: Dict[str, Any] = None,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None,
        jitter: Optional[float] = None,
        fail_fast: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute operation across multiple regions.

        Args:
            service: AWS service name
            operation: AWS operation name
            regions: List of AWS regions
            kwargs: Operation keyword arguments
            max_retries: Maximum retry attempts (overrides default)
            initial_backoff: Initial backoff time in seconds (overrides default)
            jitter: Jitter factor (overrides default)
            fail_fast: Whether to raise exception on first region failure

        Returns:
            Dictionary mapping region to operation result

        Raises:
            MultiRegionOperationError: Operation failed in all regions
        """
        # Set default values if not provided
        kwargs = kwargs or {}

        results = {}
        errors = {}

        # Create tasks for each region
        tasks = []
        for region in regions:
            tasks.append(
                self._execute_region(
                    service=service,
                    operation=operation,
                    region=region,
                    kwargs=kwargs,
                    max_retries=max_retries,
                    initial_backoff=initial_backoff,
                    jitter=jitter,
                )
            )

        # Execute operations concurrently
        completed = await asyncio.gather(*tasks, return_exceptions=(not fail_fast))

        # Process results
        for i, (region, result) in enumerate(zip(regions, completed)):
            if isinstance(result, Exception):
                errors[region] = str(result)
            else:
                results[region] = result

        # Handle failures
        if not results and errors:
            raise MultiRegionOperationError(
                f"Operation {service}.{operation} failed in all regions", errors
            )

        return results

    async def _execute_region(
        self,
        service: str,
        operation: str,
        region: str,
        kwargs: Dict[str, Any],
        max_retries: Optional[int],
        initial_backoff: Optional[float],
        jitter: Optional[float],
    ) -> tuple[str, Any]:
        """Execute operation in a specific region and return (region, result)."""
        try:
            result = await self.execute(
                service=service,
                operation=operation,
                region=region,
                kwargs=kwargs,
                max_retries=max_retries,
                initial_backoff=initial_backoff,
                jitter=jitter,
            )
            return region, result

        except Exception as e:
            # Convert AWSOperationError to MultiRegionOperationError
            logger.warning(f"Operation {service}.{operation} failed in region {region}: {e}")
            return region, {"error": str(e)}

    def _handle_exception(
        self, exception: Exception, service: str, operation: str, region: str
    ) -> None:
        """
        Handle and rethrow AWS exceptions with proper context.

        Args:
            exception: Original exception
            service: AWS service name
            operation: AWS operation name
            region: AWS region

        Raises:
            AWSOperationError: Enhanced error with context
        """
        if isinstance(exception, ClientError):
            error_code = exception.response.get("Error", {}).get("Code", "Unknown")
            error_message = exception.response.get("Error", {}).get("Message", str(exception))

            if error_code == "AccessDeniedException" or error_code == "UnauthorizedOperation":
                raise AWSOperationError(
                    f"Access denied for {service}.{operation} in {region}: {error_message}"
                )

            elif error_code == "ValidationException" or error_code == "InvalidParameterException":
                raise AWSOperationError(
                    f"Invalid parameters for {service}.{operation} in {region}: {error_message}"
                )

            elif error_code == "ServiceException":
                raise AWSOperationError(
                    f"AWS service error for {service}.{operation} in {region}: {error_message}"
                )

            else:
                raise AWSOperationError(
                    f"{service}.{operation} failed in {region} with {error_code}: {error_message}"
                )

        elif isinstance(exception, BotoCoreError):
            raise AWSOperationError(
                f"Connection error for {service}.{operation} in {region}: {str(exception)}"
            )

        else:
            # Generic error
            raise AWSOperationError(
                f"Unexpected error in {service}.{operation} in {region}: {str(exception)}"
            )

    def _record_metrics(
        self, service: str, operation: str, region: str, duration: float, success: bool
    ) -> None:
        """
        Record performance metrics for AWS operation.

        Args:
            service: AWS service name
            operation: AWS operation name
            region: AWS region
            duration: Operation duration in seconds
            success: Whether operation was successful
        """
        try:
            # Record metrics if performance analytics is available
            if hasattr(self.aws_manager, "performance"):
                self.aws_manager.performance.record_operation(
                    service=service,
                    operation=operation,
                    region=region,
                    duration_ms=duration * 1000,
                    success=success,
                )
        except Exception as e:
            logger.warning(f"Failed to record metrics: {e}")

    def configure_from_config(self, config: Dict[str, Any]) -> None:
        """
        Configure AWS operation wrapper from configuration dictionary.

        Args:
            config: Configuration dictionary
        """
        # Configure concurrency
        concurrency_config = config.get("aws_concurrency", {})
        if concurrency_config:
            # Set default limit
            if "default_limit" in concurrency_config:
                semaphore_manager.default_limit = concurrency_config["default_limit"]
                self.default_concurrency = concurrency_config["default_limit"]

            # Set service-specific limits
            for service, limit in concurrency_config.get("service_limits", {}).items():
                semaphore_manager.set_service_limit(service, limit)

            # Set region-specific limits
            for region, limit in concurrency_config.get("region_limits", {}).items():
                semaphore_manager.set_region_limit(region, limit)

        # Configure resilience settings
        resilience_config = config.get("aws_resilience", {})
        if resilience_config:
            if "max_retries" in resilience_config:
                self.default_retries = resilience_config["max_retries"]

            if "initial_backoff" in resilience_config:
                self.default_backoff = resilience_config["initial_backoff"]

            if "jitter_factor" in resilience_config:
                self.default_jitter = resilience_config["jitter_factor"]

        logger.info(
            f"AWS operation wrapper configured with concurrency limit {self.default_concurrency} and {self.default_retries} retries"
        )
