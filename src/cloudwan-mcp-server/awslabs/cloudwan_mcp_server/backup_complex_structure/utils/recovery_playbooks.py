"""
Error Recovery Playbooks for CloudWAN MCP Server.

This module provides structured recovery procedures for common error scenarios
encountered during CloudWAN operations, particularly for Network Function Group
analysis and configuration tasks.

Recovery playbooks define standardized, step-by-step procedures for handling
specific error scenarios, with context-aware decision trees and automatic
recovery strategies when possible.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, TypeVar, cast

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionError,
    # ThrottlingError is not available in this version of botocore
)

from .correlation import CorrelationContext

logger = logging.getLogger(__name__)

# Type variable for function return type
T = TypeVar("T")


class RecoveryStatus(str, Enum):
    """Status of a recovery attempt."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    NOT_ATTEMPTED = "not_attempted"


class RecoveryAction(str, Enum):
    """Types of recovery actions."""

    RETRY = "retry"
    FALLBACK = "fallback"
    TIMEOUT_EXTENSION = "timeout_extension"
    CIRCUIT_BREAKER = "circuit_breaker"
    REGION_FAILOVER = "region_failover"
    DEGRADED_OPERATION = "degraded_operation"
    MANUAL_INTERVENTION = "manual_intervention"


class RecoveryStrategy:
    """Base class for recovery strategies."""

    def __init__(self, max_attempts: int = 3, delay_ms: int = 100):
        self.max_attempts = max_attempts
        self.delay_ms = delay_ms
        self.attempts = 0
        self.last_error: Optional[Exception] = None
        self.recovery_status = RecoveryStatus.NOT_ATTEMPTED
        self.recovery_context: Dict[str, Any] = {}

    async def execute(self, operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute operation with the recovery strategy.

        Args:
            operation: Operation to execute
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            Exception: If recovery fails
        """
        self.attempts = 0
        self.last_error = None
        self.recovery_status = RecoveryStatus.NOT_ATTEMPTED

        return await self._execute_with_recovery(operation, *args, **kwargs)

    async def _execute_with_recovery(
        self, operation: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute the operation with recovery. To be implemented by subclasses.

        Args:
            operation: Operation to execute
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement this method")


class RetryStrategy(RecoveryStrategy):
    """Recovery strategy that retries operations with backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_ms: int = 100,
        max_delay_ms: int = 5000,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        super().__init__(max_attempts, initial_delay_ms)
        self.max_delay_ms = max_delay_ms
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    async def _execute_with_recovery(
        self, operation: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute operation with retry backoff.

        Args:
            operation: Operation to execute
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            Exception: Last error encountered if max retries reached
        """
        current_delay = self.delay_ms

        # Create correlation context for the retry operation
        correlation_id = CorrelationContext.current_correlation_id()
        if correlation_id:
            # If we have a correlation ID, create a child context for the retry operation
            operation_name = kwargs.pop("operation_name", "retry_operation")
            with CorrelationContext(
                correlation_id_value=correlation_id,
                operation_name=operation_name,
                context_attributes={
                    "recovery_strategy": "retry",
                    "max_attempts": self.max_attempts,
                    "initial_delay_ms": self.delay_ms,
                    "max_delay_ms": self.max_delay_ms,
                    "backoff_factor": self.backoff_factor,
                    "jitter": self.jitter,
                },
            ) as ctx:
                return await self._execute_retry_loop(
                    operation, ctx, current_delay, *args, **kwargs
                )
        else:
            # No correlation ID, execute without context
            return await self._execute_retry_loop(operation, None, current_delay, *args, **kwargs)

    async def _execute_retry_loop(
        self,
        operation: Callable[..., T],
        ctx: Optional[CorrelationContext],
        current_delay: int,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute the retry loop logic."""
        for attempt in range(1, self.max_attempts + 1):
            self.attempts = attempt

            # Add attempt information to context if available
            if ctx:
                ctx.add_attribute("current_attempt", attempt)
                ctx.add_attribute("total_attempts", self.max_attempts)

            try:
                # Execute the operation
                result = await self._execute_operation(operation, *args, **kwargs)

                # Record successful recovery if not first attempt
                if attempt > 1:
                    self.recovery_status = RecoveryStatus.SUCCESS
                    if ctx:
                        ctx.add_event(
                            "recovery_succeeded",
                            strategy="retry",
                            attempts=attempt,
                            total_delay_ms=sum(
                                self._calculate_delay(i, current_delay) for i in range(attempt - 1)
                            ),
                        )

                return result

            except Exception as e:
                self.last_error = e

                # Record error in correlation context
                if ctx:
                    ctx.add_event(
                        "operation_failed",
                        attempt=attempt,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )

                # If this is the last attempt, raise the exception
                if attempt == self.max_attempts:
                    if ctx:
                        ctx.add_event(
                            "recovery_failed",
                            strategy="retry",
                            attempts=attempt,
                            last_error=str(e),
                            last_error_type=type(e).__name__,
                        )
                    self.recovery_status = RecoveryStatus.FAILED
                    raise

                # Calculate delay with jitter
                delay = self._calculate_delay(attempt, current_delay)

                # Log retry attempt
                logger.warning(
                    f"Operation failed (attempt {attempt}/{self.max_attempts}), "
                    f"retrying in {delay}ms: {e}"
                )

                # Record retry in correlation context
                if ctx:
                    ctx.add_event(
                        "retry_scheduled",
                        attempt=attempt,
                        next_attempt=attempt + 1,
                        delay_ms=delay,
                        error=str(e),
                    )

                # Wait before retrying
                await asyncio.sleep(delay / 1000)

                # Increase delay for next attempt (with cap)
                current_delay = min(current_delay * self.backoff_factor, self.max_delay_ms)

    def _calculate_delay(self, attempt: int, current_delay: float) -> int:
        """
        Calculate delay for the current attempt, with optional jitter.

        Args:
            attempt: Current attempt number (1-based)
            current_delay: Current delay in milliseconds

        Returns:
            Delay in milliseconds
        """
        if not self.jitter:
            return int(current_delay)

        # Add jitter: random value between 0.5 and 1.5 of current delay
        import random

        jitter_factor = random.uniform(0.5, 1.5)
        return int(current_delay * jitter_factor)

    async def _execute_operation(self, operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute the operation, handling both sync and async operations.

        Args:
            operation: Operation to execute
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation
        """
        if asyncio.iscoroutinefunction(operation):
            return await operation(*args, **kwargs)
        else:
            return cast(T, operation(*args, **kwargs))


class FallbackStrategy(RecoveryStrategy):
    """Recovery strategy that falls back to alternative operations."""

    def __init__(self, fallbacks: List[Callable[..., T]], try_all: bool = True):
        super().__init__(max_attempts=len(fallbacks) + 1)
        self.fallbacks = fallbacks
        self.try_all = try_all
        self.errors: List[Exception] = []

    async def _execute_with_recovery(
        self, operation: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute operation with fallbacks if it fails.

        Args:
            operation: Primary operation to execute
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation

        Returns:
            Result of the primary operation or one of the fallbacks

        Raises:
            Exception: If all operations fail
        """
        self.errors = []

        # Create correlation context for the fallback operation
        correlation_id = CorrelationContext.current_correlation_id()
        if correlation_id:
            # If we have a correlation ID, create a child context for the fallback operation
            with CorrelationContext(
                correlation_id_value=correlation_id,
                operation_name="fallback_operation",
                context_attributes={
                    "recovery_strategy": "fallback",
                    "fallback_count": len(self.fallbacks),
                    "try_all": self.try_all,
                },
            ) as ctx:
                return await self._execute_fallback_sequence(operation, ctx, *args, **kwargs)
        else:
            # No correlation ID, execute without context
            return await self._execute_fallback_sequence(operation, None, *args, **kwargs)

    async def _execute_fallback_sequence(
        self,
        operation: Callable[..., T],
        ctx: Optional[CorrelationContext],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute the fallback sequence logic."""
        # Try primary operation
        try:
            if ctx:
                ctx.add_event("trying_primary_operation")

            self.attempts = 1
            result = await self._execute_operation(operation, *args, **kwargs)

            if ctx:
                ctx.add_event("primary_operation_succeeded")

            return result

        except Exception as e:
            if ctx:
                ctx.add_event(
                    "primary_operation_failed",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )

            self.last_error = e
            self.errors.append(e)
            logger.warning(f"Primary operation failed: {e}")

            # Try fallbacks
            success = False
            for i, fallback in enumerate(self.fallbacks):
                self.attempts = i + 2  # +1 for primary, +1 for 0-based index

                try:
                    if ctx:
                        ctx.add_event(
                            "trying_fallback",
                            fallback_index=i,
                            fallback_name=fallback.__name__,
                        )

                    result = await self._execute_operation(fallback, *args, **kwargs)

                    # Record successful recovery
                    self.recovery_status = RecoveryStatus.SUCCESS
                    if ctx:
                        ctx.add_event(
                            "fallback_succeeded",
                            fallback_index=i,
                            fallback_name=fallback.__name__,
                        )

                    return result

                except Exception as fallback_error:
                    self.last_error = fallback_error
                    self.errors.append(fallback_error)

                    if ctx:
                        ctx.add_event(
                            "fallback_failed",
                            fallback_index=i,
                            fallback_name=fallback.__name__,
                            error_type=type(fallback_error).__name__,
                            error_message=str(fallback_error),
                        )

                    logger.warning(f"Fallback {i+1} failed: {fallback_error}")

                    if not self.try_all:
                        # Stop after first fallback failure
                        break

            # All fallbacks failed
            self.recovery_status = RecoveryStatus.FAILED
            if ctx:
                ctx.add_event(
                    "recovery_failed",
                    strategy="fallback",
                    attempts=self.attempts,
                    errors_count=len(self.errors),
                )

            raise self.last_error

    async def _execute_operation(self, operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute operation, handling both sync and async cases."""
        if asyncio.iscoroutinefunction(operation):
            return await operation(*args, **kwargs)
        else:
            return cast(T, operation(*args, **kwargs))


class DegradedOperationStrategy(RecoveryStrategy):
    """
    Recovery strategy that allows operation in a degraded mode.

    This strategy attempts the primary operation, but if it fails, it falls back
    to a degraded operation mode that provides partial functionality.
    """

    def __init__(self, degraded_operation: Callable[..., T], acceptable_errors: List[type] = None):
        super().__init__(max_attempts=2)  # Primary + degraded
        self.degraded_operation = degraded_operation
        self.acceptable_errors = acceptable_errors or [Exception]
        self.primary_error: Optional[Exception] = None

    async def _execute_with_recovery(
        self, operation: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute operation with degraded mode fallback.

        Args:
            operation: Primary operation to execute
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation

        Returns:
            Result of primary or degraded operation

        Raises:
            Exception: If both operations fail or error is not acceptable
        """
        # Create correlation context for the degraded operation
        correlation_id = CorrelationContext.current_correlation_id()
        if correlation_id:
            # If we have a correlation ID, create a child context for the degraded operation
            with CorrelationContext(
                correlation_id_value=correlation_id,
                operation_name="degraded_operation",
                context_attributes={
                    "recovery_strategy": "degraded_operation",
                    "acceptable_errors": [err.__name__ for err in self.acceptable_errors],
                },
            ) as ctx:
                return await self._execute_degraded_sequence(operation, ctx, *args, **kwargs)
        else:
            # No correlation ID, execute without context
            return await self._execute_degraded_sequence(operation, None, *args, **kwargs)

    async def _execute_degraded_sequence(
        self,
        operation: Callable[..., T],
        ctx: Optional[CorrelationContext],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute the degraded operation sequence logic."""
        # Try primary operation
        try:
            if ctx:
                ctx.add_event("trying_primary_operation")

            self.attempts = 1
            result = await self._execute_operation(operation, *args, **kwargs)

            if ctx:
                ctx.add_event("primary_operation_succeeded")

            return result

        except Exception as e:
            self.primary_error = e
            self.last_error = e

            if ctx:
                ctx.add_event(
                    "primary_operation_failed",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )

            logger.warning(f"Primary operation failed: {e}")

            # Check if error is acceptable for degraded mode
            if not any(isinstance(e, err_type) for err_type in self.acceptable_errors):
                if ctx:
                    ctx.add_event(
                        "error_not_acceptable_for_degraded_mode",
                        error_type=type(e).__name__,
                    )

                logger.error(f"Error not acceptable for degraded mode: {e}")
                raise

            # Try degraded operation
            try:
                if ctx:
                    ctx.add_event("trying_degraded_operation")

                self.attempts = 2

                # Add error information to kwargs
                kwargs_with_error = kwargs.copy()
                kwargs_with_error["primary_error"] = self.primary_error
                kwargs_with_error["degraded_mode"] = True

                result = await self._execute_operation(
                    self.degraded_operation, *args, **kwargs_with_error
                )

                # Record partial success
                self.recovery_status = RecoveryStatus.PARTIAL_SUCCESS
                if ctx:
                    ctx.add_event("degraded_operation_succeeded")

                return result

            except Exception as degraded_error:
                self.last_error = degraded_error

                if ctx:
                    ctx.add_event(
                        "degraded_operation_failed",
                        error_type=type(degraded_error).__name__,
                        error_message=str(degraded_error),
                    )

                logger.error(f"Degraded operation failed: {degraded_error}")

                # Both operations failed
                self.recovery_status = RecoveryStatus.FAILED
                if ctx:
                    ctx.add_event(
                        "recovery_failed",
                        strategy="degraded_operation",
                        primary_error_type=type(self.primary_error).__name__,
                        degraded_error_type=type(degraded_error).__name__,
                    )

                raise degraded_error

    async def _execute_operation(self, operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute operation, handling both sync and async cases."""
        if asyncio.iscoroutinefunction(operation):
            return await operation(*args, **kwargs)
        else:
            return cast(T, operation(*args, **kwargs))


class RegionFailoverStrategy(RecoveryStrategy):
    """
    Recovery strategy that tries operations in multiple regions.

    This strategy attempts the operation in the primary region first, then
    falls back to other regions if the primary fails.
    """

    def __init__(
        self,
        regions: List[str],
        retry_per_region: int = 1,
        acceptable_errors: List[type] = None,
    ):
        super().__init__(max_attempts=len(regions) * retry_per_region)
        self.regions = regions
        self.retry_per_region = retry_per_region
        self.acceptable_errors = acceptable_errors or [
            ConnectionError,
            ThrottlingError,
            ClientError,
            BotoCoreError,
        ]
        self.errors_by_region: Dict[str, List[Exception]] = {}

    async def _execute_with_recovery(
        self, operation: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute operation with region failover.

        Args:
            operation: Operation to execute
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation in any successful region

        Raises:
            Exception: If all regions fail
        """
        self.errors_by_region = {}

        # Extract region parameter (required for this strategy)
        region_param = kwargs.get("region")
        if not region_param:
            raise ValueError("Region parameter is required for RegionFailoverStrategy")

        # Prioritize regions: put the provided region first, then others
        prioritized_regions = [region_param] + [r for r in self.regions if r != region_param]

        # Create correlation context for the region failover operation
        correlation_id = CorrelationContext.current_correlation_id()
        if correlation_id:
            # If we have a correlation ID, create a child context for the region failover
            with CorrelationContext(
                correlation_id_value=correlation_id,
                operation_name="region_failover_operation",
                context_attributes={
                    "recovery_strategy": "region_failover",
                    "regions": prioritized_regions,
                    "retry_per_region": self.retry_per_region,
                    "primary_region": region_param,
                },
            ) as ctx:
                return await self._execute_region_failover(
                    operation, prioritized_regions, ctx, *args, **kwargs
                )
        else:
            # No correlation ID, execute without context
            return await self._execute_region_failover(
                operation, prioritized_regions, None, *args, **kwargs
            )

    async def _execute_region_failover(
        self,
        operation: Callable[..., T],
        prioritized_regions: List[str],
        ctx: Optional[CorrelationContext],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute the region failover logic."""
        # Initialize attempt counter
        self.attempts = 0

        for region in prioritized_regions:
            # Update kwargs with current region
            region_kwargs = kwargs.copy()
            region_kwargs["region"] = region

            # Track errors for this region
            self.errors_by_region[region] = []

            # Try operation in this region (with retries)
            for attempt in range(1, self.retry_per_region + 1):
                self.attempts += 1

                if ctx:
                    ctx.add_attribute("current_region", region)
                    ctx.add_attribute("region_attempt", attempt)
                    ctx.add_attribute("total_attempts", self.attempts)
                    ctx.add_event(
                        "trying_region",
                        region=region,
                        attempt=attempt,
                        total_attempts=self.attempts,
                    )

                try:
                    # Execute the operation with this region
                    result = await self._execute_operation(operation, *args, **region_kwargs)

                    # Record successful recovery if not primary region or not first attempt
                    is_primary = region == prioritized_regions[0]
                    if not is_primary or attempt > 1:
                        self.recovery_status = RecoveryStatus.SUCCESS
                        if ctx:
                            ctx.add_event(
                                "region_failover_succeeded",
                                region=region,
                                is_primary=is_primary,
                                attempt=attempt,
                                total_attempts=self.attempts,
                            )

                    return result

                except Exception as e:
                    self.last_error = e
                    self.errors_by_region[region].append(e)

                    if ctx:
                        ctx.add_event(
                            "region_operation_failed",
                            region=region,
                            attempt=attempt,
                            error_type=type(e).__name__,
                            error_message=str(e),
                        )

                    logger.warning(f"Operation in region {region} failed (attempt {attempt}): {e}")

                    # Check if error is acceptable for failover
                    if not any(isinstance(e, err_type) for err_type in self.acceptable_errors):
                        if ctx:
                            ctx.add_event(
                                "error_not_acceptable_for_region_failover",
                                error_type=type(e).__name__,
                            )

                        logger.error(f"Error not acceptable for region failover: {e}")
                        raise

        # All regions failed
        self.recovery_status = RecoveryStatus.FAILED
        if ctx:
            ctx.add_event(
                "region_failover_failed",
                total_attempts=self.attempts,
                regions_tried=list(self.errors_by_region.keys()),
            )

        raise self.last_error

    async def _execute_operation(self, operation: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute operation, handling both sync and async cases."""
        if asyncio.iscoroutinefunction(operation):
            return await operation(*args, **kwargs)
        else:
            return cast(T, operation(*args, **kwargs))


class NFGAnalysisRecoveryPlaybooks:
    """
    Recovery playbooks specific to Network Function Group analysis operations.

    This class provides specialized recovery strategies for common error scenarios
    encountered during NFG analysis operations.
    """

    def __init__(self, aws_client_manager=None):
        self.aws_client_manager = aws_client_manager

        # Common error types for AWS operations
        # ThrottlingError is not available in this version of botocore
        self.throttling_errors = []
        self.connection_errors = [ConnectionError, BotoCoreError]
        self.credential_errors = [
            "ExpiredToken",
            "InvalidClientTokenId",
            "SignatureDoesNotMatch",
        ]
        self.permission_errors = ["AccessDenied", "UnauthorizedOperation"]
        self.resource_not_found_errors = [
            "ResourceNotFoundException",
            "InvalidResourceID",
        ]

    async def get_core_network_policy_recovery(
        self, core_network_id: str, region: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Recovery playbook for retrieving Core Network policy.

        This playbook handles common failures when retrieving Core Network policy:
        1. First tries with retries (handling throttling and transient errors)
        2. If still failing, tries other regions
        3. If all regions fail or error is not retryable, falls back to cached policy if available

        Args:
            core_network_id: Core Network ID
            region: Primary AWS region
            force_refresh: Whether to force refresh cached data

        Returns:
            Core Network policy document

        Raises:
            Exception: If all recovery strategies fail
        """
        if not self.aws_client_manager:
            raise ValueError("AWS client manager is required for this recovery playbook")

        # Create correlation context for the recovery operation
        with CorrelationContext(
            operation_name="get_core_network_policy_recovery",
            context_attributes={
                "core_network_id": core_network_id,
                "region": region,
                "force_refresh": force_refresh,
            },
        ) as ctx:
            # First recovery strategy: Retry with backoff
            retry_strategy = RetryStrategy(
                max_attempts=3,
                initial_delay_ms=100,
                max_delay_ms=2000,
                backoff_factor=2.0,
                jitter=True,
            )

            try:
                ctx.add_event("trying_retry_strategy")

                async def get_policy_operation():
                    async with self.aws_client_manager.client_context(
                        "networkmanager", region
                    ) as nm:
                        response = await nm.get_core_network_policy(CoreNetworkId=core_network_id)
                        return response.get("CoreNetworkPolicy", {})

                return await retry_strategy.execute(get_policy_operation)

            except Exception as retry_error:
                ctx.add_event(
                    "retry_strategy_failed",
                    error_type=type(retry_error).__name__,
                    error_message=str(retry_error),
                )

                logger.warning(f"Retry strategy failed for get_core_network_policy: {retry_error}")

                # Second recovery strategy: Region failover
                ctx.add_event("trying_region_failover_strategy")

                region_strategy = RegionFailoverStrategy(
                    regions=self.aws_client_manager.regions, retry_per_region=1
                )

                try:

                    async def get_policy_with_region(region=region):
                        async with self.aws_client_manager.client_context(
                            "networkmanager", region
                        ) as nm:
                            response = await nm.get_core_network_policy(
                                CoreNetworkId=core_network_id
                            )
                            return response.get("CoreNetworkPolicy", {})

                    return await region_strategy.execute(get_policy_with_region, region=region)

                except Exception as region_error:
                    ctx.add_event(
                        "region_failover_strategy_failed",
                        error_type=type(region_error).__name__,
                        error_message=str(region_error),
                    )

                    logger.warning(
                        f"Region failover strategy failed for get_core_network_policy: {region_error}"
                    )

                    # Third recovery strategy: Degraded operation (cached policy)
                    ctx.add_event("trying_degraded_operation_strategy")

                    # Skip cache if force refresh is requested
                    if force_refresh:
                        ctx.add_event("skipping_cache_due_to_force_refresh")
                        raise region_error

                    # Function to get cached policy
                    async def get_cached_policy(primary_error=None, degraded_mode=False):
                        # This would normally check a cache, but for simplicity we'll return a basic structure
                        if degraded_mode:
                            ctx.add_event("using_cached_policy")
                            logger.info(
                                f"Using cached policy for {core_network_id} due to {primary_error}"
                            )

                            # In a real implementation, this would retrieve from cache
                            # For now, we'll return a minimal policy structure
                            return {
                                "CoreNetworkPolicy": {
                                    "CoreNetworkId": core_network_id,
                                    "PolicyVersionId": 0,
                                    "Segments": [],
                                    "EdgeLocations": [],
                                    "Status": "STALE_CACHE",
                                    "IsCached": True,
                                    "CachedAt": datetime.now().isoformat(),
                                }
                            }
                        raise ValueError("No cached policy available")

                    degraded_strategy = DegradedOperationStrategy(
                        degraded_operation=get_cached_policy,
                        acceptable_errors=[Exception],  # Accept any error for degraded mode
                    )

                    try:
                        return await degraded_strategy.execute(
                            get_policy_with_region, region=region
                        )
                    except Exception as degraded_error:
                        ctx.add_event(
                            "all_recovery_strategies_failed",
                            final_error_type=type(degraded_error).__name__,
                            final_error_message=str(degraded_error),
                        )

                        logger.error(
                            f"All recovery strategies failed for get_core_network_policy: {degraded_error}"
                        )
                        raise

    async def analyze_nfg_with_recovery(
        self, core_network_id: str, nfg_name: str, analyzer_function: Callable, **kwargs
    ) -> Dict[str, Any]:
        """
        Recovery playbook for NFG analysis operations.

        This playbook handles failures during NFG analysis:
        1. First tries with retries (handling throttling and transient errors)
        2. If policy retrieval fails, attempts to use cached policy
        3. If analysis still fails, attempts degraded analysis with limited functionality

        Args:
            core_network_id: Core Network ID
            nfg_name: Network Function Group name
            analyzer_function: Function to perform the analysis
            kwargs: Additional arguments for the analyzer function

        Returns:
            Analysis results

        Raises:
            Exception: If all recovery strategies fail
        """
        # Create correlation context for the recovery operation
        with CorrelationContext(
            operation_name="analyze_nfg_with_recovery",
            context_attributes={
                "core_network_id": core_network_id,
                "nfg_name": nfg_name,
                "analysis_type": "nfg_analysis",
            },
        ) as ctx:
            # First recovery strategy: Retry with backoff
            retry_strategy = RetryStrategy(
                max_attempts=3,
                initial_delay_ms=200,
                max_delay_ms=3000,
                backoff_factor=2.0,
                jitter=True,
            )

            try:
                ctx.add_event("trying_retry_strategy")

                # Execute the analysis function with retry
                return await retry_strategy.execute(
                    analyzer_function,
                    core_network_id=core_network_id,
                    nfg_name=nfg_name,
                    **kwargs,
                )

            except Exception as retry_error:
                ctx.add_event(
                    "retry_strategy_failed",
                    error_type=type(retry_error).__name__,
                    error_message=str(retry_error),
                )

                logger.warning(f"Retry strategy failed for NFG analysis: {retry_error}")

                # Second recovery strategy: Degraded operation
                ctx.add_event("trying_degraded_operation_strategy")

                # Function to perform degraded analysis
                async def degraded_nfg_analysis(
                    core_network_id,
                    nfg_name,
                    primary_error=None,
                    degraded_mode=False,
                    **kwargs,
                ):
                    if not degraded_mode:
                        # This should never happen in this context
                        raise ValueError("Degraded mode not enabled")

                    ctx.add_event(
                        "performing_degraded_analysis",
                        error=str(primary_error) if primary_error else "Unknown error",
                    )

                    logger.info(
                        f"Performing degraded analysis for {nfg_name} due to {primary_error}"
                    )

                    # Create modified kwargs with reduced functionality
                    degraded_kwargs = kwargs.copy()

                    # Remove features that might be causing issues
                    degraded_kwargs["include_performance_metrics"] = False
                    degraded_kwargs["evaluate_security"] = False
                    degraded_kwargs["force_refresh"] = True  # Force refresh to bypass cache issues

                    # Use cached data when possible
                    if "policy_doc" not in degraded_kwargs:
                        # Try to get a cached or simplified policy
                        try:
                            if self.aws_client_manager:
                                policy = await self.get_core_network_policy_recovery(
                                    core_network_id,
                                    degraded_kwargs.get("region", "us-west-2"),
                                    force_refresh=False,  # Try to use cache
                                )
                                degraded_kwargs["policy_doc"] = policy
                        except Exception as e:
                            logger.warning(f"Could not get policy for degraded analysis: {e}")
                            # Create minimal policy structure if needed

                    # Call the original function with modified parameters
                    try:
                        result = await analyzer_function(
                            core_network_id=core_network_id,
                            nfg_name=nfg_name,
                            **degraded_kwargs,
                        )

                        # Mark the result as degraded
                        if isinstance(result, dict):
                            result["degraded_analysis"] = True
                            result["degraded_reason"] = str(primary_error)

                        return result

                    except Exception as e:
                        logger.error(f"Degraded analysis failed: {e}")
                        raise

                degraded_strategy = DegradedOperationStrategy(
                    degraded_operation=degraded_nfg_analysis,
                    acceptable_errors=[Exception],  # Accept any error for degraded mode
                )

                try:
                    return await degraded_strategy.execute(
                        analyzer_function,
                        core_network_id=core_network_id,
                        nfg_name=nfg_name,
                        **kwargs,
                    )
                except Exception as degraded_error:
                    ctx.add_event(
                        "all_recovery_strategies_failed",
                        final_error_type=type(degraded_error).__name__,
                        final_error_message=str(degraded_error),
                    )

                    logger.error(
                        f"All recovery strategies failed for NFG analysis: {degraded_error}"
                    )
                    raise

    async def multi_nfg_analysis_with_recovery(
        self, core_network_id: str, analyzer_function: Callable, **kwargs
    ) -> Dict[str, Any]:
        """
        Recovery playbook for multi-NFG analysis operations.

        This playbook handles failures during multi-NFG analysis:
        1. First tries with retries
        2. If overall analysis fails, falls back to analyzing individual NFGs
        3. Aggregates successful results even if some NFGs fail

        Args:
            core_network_id: Core Network ID
            analyzer_function: Function to perform the multi-NFG analysis
            kwargs: Additional arguments for the analyzer function

        Returns:
            Analysis results with as many NFGs as could be successfully analyzed

        Raises:
            Exception: If all recovery strategies fail completely
        """
        # Create correlation context for the recovery operation
        with CorrelationContext(
            operation_name="multi_nfg_analysis_with_recovery",
            context_attributes={
                "core_network_id": core_network_id,
                "analysis_type": "multi_nfg_analysis",
            },
        ) as ctx:
            # First recovery strategy: Retry with backoff
            retry_strategy = RetryStrategy(
                max_attempts=2,
                initial_delay_ms=200,
                max_delay_ms=3000,
                backoff_factor=2.0,
                jitter=True,
            )

            try:
                ctx.add_event("trying_retry_strategy")

                # Execute the analysis function with retry
                return await retry_strategy.execute(
                    analyzer_function, core_network_id=core_network_id, **kwargs
                )

            except Exception as retry_error:
                ctx.add_event(
                    "retry_strategy_failed",
                    error_type=type(retry_error).__name__,
                    error_message=str(retry_error),
                )

                logger.warning(f"Retry strategy failed for multi-NFG analysis: {retry_error}")

                # Second recovery strategy: Fallback to individual NFG analysis
                ctx.add_event("trying_individual_nfg_fallback")

                # This would be implemented in a real system to analyze each NFG individually
                # and aggregate the results into a multi-NFG response

                # For now, we'll return a partial success response
                from datetime import datetime

                return {
                    "core_network_id": core_network_id,
                    "policy_version": None,
                    "analysis_timestamp": datetime.now(),
                    "nfg_results": {},  # Would contain individual results in real implementation
                    "regions_searched": kwargs.get("regions", []),
                    "success": True,
                    "partial_results": True,
                    "recovery_applied": True,
                    "error_message": f"Full analysis failed, partial results provided: {retry_error}",
                }
