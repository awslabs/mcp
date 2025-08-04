"""
Optimized Multi-Region Executor for CloudWAN MCP.

This module provides high-performance parallel execution of AWS operations across regions with:
- Smart region selection and execution routing
- Parallel operation execution with controlled concurrency
- Error handling and aggregation
- Performance tracking and optimization
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, TypeVar

from .client_registry import ClientRegistry, ClientType

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExecutionMode(Enum):
    """Execution modes for multi-region operations."""

    PARALLEL = "parallel"  # Execute in all regions in parallel
    SEQUENTIAL = "sequential"  # Execute in regions sequentially
    FALLBACK = "fallback"  # Try regions in sequence until success
    FASTEST = "fastest"  # Execute in parallel, return first successful result


@dataclass
class RegionalResult:
    """Result from a single regional operation."""

    region: str
    success: bool
    result: Optional[Any] = None
    error: Optional[Exception] = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MultiRegionResult:
    """Aggregated result from multi-region operation."""

    service: str
    operation: str
    results: Dict[str, RegionalResult] = field(default_factory=dict)
    success_count: int = 0
    failure_count: int = 0
    execution_time_ms: float = 0.0
    completed: bool = False
    primary_result: Optional[Any] = None
    primary_region: Optional[str] = None
    fallback_regions_used: List[str] = field(default_factory=list)


class OptimizedMultiRegionExecutor:
    """
    Optimized executor for multi-region AWS operations.

    Features:
    - Parallel execution with configurable concurrency
    - Smart region selection based on operation characteristics
    - Automatic error handling and result aggregation
    - Performance monitoring and optimization
    - Fallback mechanisms for resilience
    """

    def __init__(
        self,
        client_registry: ClientRegistry,
        max_concurrency: int = 5,
        default_regions: Optional[List[str]] = None,
        default_mode: ExecutionMode = ExecutionMode.PARALLEL,
    ):
        """
        Initialize multi-region executor.

        Args:
            client_registry: Client registry for obtaining AWS clients
            max_concurrency: Maximum concurrent regional operations
            default_regions: Default regions to use
            default_mode: Default execution mode
        """
        self.client_registry = client_registry
        self.max_concurrency = max_concurrency
        self.default_regions = default_regions or client_registry.regions
        self.default_mode = default_mode

        # Regional strategy from client registry
        self.regional_strategy = client_registry.regional_strategy

        # Performance tracking
        self._execution_history: List[MultiRegionResult] = []
        self._max_history_size = 100

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrency)

        logger.info(
            f"OptimizedMultiRegionExecutor initialized with {len(self.default_regions)} regions, "
            f"max concurrency: {max_concurrency}, default mode: {default_mode.value}"
        )

    async def execute(
        self,
        service: str,
        operation: str,
        regions: Optional[List[str]] = None,
        operation_kwargs: Optional[Dict[str, Any]] = None,
        mode: Optional[ExecutionMode] = None,
        timeout: Optional[float] = None,
        client_type: ClientType = ClientType.OPTIMIZED,
    ) -> MultiRegionResult:
        """
        Execute operation across multiple regions.

        Args:
            service: AWS service name
            operation: Operation name
            regions: Regions to execute in (defaults to all configured regions)
            operation_kwargs: Arguments for the operation
            mode: Execution mode
            timeout: Operation timeout in seconds
            client_type: Type of client to use

        Returns:
            Multi-region operation result

        Raises:
            asyncio.TimeoutError: If operation times out
            Exception: If operation fails in all regions in FALLBACK mode
        """
        start_time = time.time()
        regions = regions or self.default_regions
        mode = mode or self.default_mode
        operation_kwargs = operation_kwargs or {}

        # Create result container
        result = MultiRegionResult(service=service, operation=operation)

        # Execute based on mode
        if mode == ExecutionMode.PARALLEL:
            await self._execute_parallel(
                result,
                service,
                operation,
                regions,
                operation_kwargs,
                timeout,
                client_type,
            )
        elif mode == ExecutionMode.SEQUENTIAL:
            await self._execute_sequential(
                result,
                service,
                operation,
                regions,
                operation_kwargs,
                timeout,
                client_type,
            )
        elif mode == ExecutionMode.FALLBACK:
            await self._execute_fallback(
                result,
                service,
                operation,
                regions,
                operation_kwargs,
                timeout,
                client_type,
            )
        elif mode == ExecutionMode.FASTEST:
            await self._execute_fastest(
                result,
                service,
                operation,
                regions,
                operation_kwargs,
                timeout,
                client_type,
            )

        # Calculate execution time
        result.execution_time_ms = (time.time() - start_time) * 1000
        result.completed = True

        # Store in history (limited size)
        self._execution_history.append(result)
        if len(self._execution_history) > self._max_history_size:
            self._execution_history = self._execution_history[-self._max_history_size :]

        return result

    async def _execute_parallel(
        self,
        result: MultiRegionResult,
        service: str,
        operation: str,
        regions: List[str],
        operation_kwargs: Dict[str, Any],
        timeout: Optional[float],
        client_type: ClientType,
    ) -> None:
        """Execute operation in all regions in parallel with concurrency control."""
        tasks = []
        for region in regions:
            task = self._execute_in_region(
                service, operation, region, operation_kwargs, client_type
            )
            tasks.append(task)

        # Wait for all tasks to complete, with timeout if specified
        if timeout:
            done, pending = await asyncio.wait(
                tasks, timeout=timeout, return_when=asyncio.ALL_COMPLETED
            )
            # Cancel pending tasks if timeout
            for task in pending:
                task.cancel()
        else:
            done = await asyncio.gather(*tasks)

        # Process results
        for regional_result in done:
            if isinstance(regional_result, RegionalResult):
                result.results[regional_result.region] = regional_result
                if regional_result.success:
                    result.success_count += 1
                    # Use first successful result as primary if not set
                    if result.primary_result is None:
                        result.primary_result = regional_result.result
                        result.primary_region = regional_result.region
                else:
                    result.failure_count += 1

    async def _execute_sequential(
        self,
        result: MultiRegionResult,
        service: str,
        operation: str,
        regions: List[str],
        operation_kwargs: Dict[str, Any],
        timeout: Optional[float],
        client_type: ClientType,
    ) -> None:
        """Execute operation in regions sequentially."""
        # Set timeout for entire operation if specified
        if timeout:
            try:
                # Create task with timeout
                async with asyncio.timeout(timeout):
                    for region in regions:
                        regional_result = await self._execute_in_region_direct(
                            service, operation, region, operation_kwargs, client_type
                        )
                        result.results[region] = regional_result
                        if regional_result.success:
                            result.success_count += 1
                            # Use first successful result as primary if not set
                            if result.primary_result is None:
                                result.primary_result = regional_result.result
                                result.primary_region = regional_result.region
                        else:
                            result.failure_count += 1
            except asyncio.TimeoutError:
                logger.warning(
                    f"Sequential execution timed out after {timeout}s: {service}.{operation}"
                )
        else:
            # No timeout
            for region in regions:
                regional_result = await self._execute_in_region_direct(
                    service, operation, region, operation_kwargs, client_type
                )
                result.results[region] = regional_result
                if regional_result.success:
                    result.success_count += 1
                    # Use first successful result as primary if not set
                    if result.primary_result is None:
                        result.primary_result = regional_result.result
                        result.primary_region = regional_result.region
                else:
                    result.failure_count += 1

    async def _execute_fallback(
        self,
        result: MultiRegionResult,
        service: str,
        operation: str,
        regions: List[str],
        operation_kwargs: Dict[str, Any],
        timeout: Optional[float],
        client_type: ClientType,
    ) -> None:
        """Execute operation with region fallback until success."""
        # Use regional strategy to order regions optimally
        ordered_regions = []
        for _ in range(len(regions)):
            # Get next best region that's not already in ordered_regions
            available_regions = [r for r in regions if r not in ordered_regions]
            if not available_regions:
                break

            best_region = self.regional_strategy.select_region(
                service, operation, available_regions
            )
            ordered_regions.append(best_region)

        # Set timeout for entire operation if specified
        if timeout:
            try:
                async with asyncio.timeout(timeout):
                    for region in ordered_regions:
                        regional_result = await self._execute_in_region_direct(
                            service, operation, region, operation_kwargs, client_type
                        )
                        result.results[region] = regional_result

                        if regional_result.success:
                            result.success_count += 1
                            result.primary_result = regional_result.result
                            result.primary_region = regional_result.region
                            # In fallback mode, we stop at first success
                            break
                        else:
                            result.failure_count += 1
                            result.fallback_regions_used.append(region)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Fallback execution timed out after {timeout}s: {service}.{operation}"
                )
        else:
            # No timeout
            for region in ordered_regions:
                regional_result = await self._execute_in_region_direct(
                    service, operation, region, operation_kwargs, client_type
                )
                result.results[region] = regional_result

                if regional_result.success:
                    result.success_count += 1
                    result.primary_result = regional_result.result
                    result.primary_region = regional_result.region
                    # In fallback mode, we stop at first success
                    break
                else:
                    result.failure_count += 1
                    result.fallback_regions_used.append(region)

    async def _execute_fastest(
        self,
        result: MultiRegionResult,
        service: str,
        operation: str,
        regions: List[str],
        operation_kwargs: Dict[str, Any],
        timeout: Optional[float],
        client_type: ClientType,
    ) -> None:
        """Execute operation in all regions and return first successful result."""
        # Create a Future to signal completion
        completion_future = asyncio.Future()

        # Track which regions have been tried
        regions_tried = set()

        # Function to process results and signal completion on first success
        def process_result(task):
            if task.exception():
                return

            regional_result = task.result()
            result.results[regional_result.region] = regional_result
            regions_tried.add(regional_result.region)

            if regional_result.success:
                result.success_count += 1
                if not completion_future.done():
                    # First successful result becomes primary
                    result.primary_result = regional_result.result
                    result.primary_region = regional_result.region
                    completion_future.set_result(True)
            else:
                result.failure_count += 1

                # Check if all regions tried and none succeeded
                if len(regions_tried) == len(regions) and result.success_count == 0:
                    if not completion_future.done():
                        completion_future.set_result(False)

        # Create tasks for all regions
        tasks = []
        for region in regions:
            task = asyncio.create_task(
                self._execute_in_region_direct(
                    service, operation, region, operation_kwargs, client_type
                )
            )
            task.add_done_callback(process_result)
            tasks.append(task)

        # Wait for first success or all completions, with timeout if specified
        try:
            if timeout:
                await asyncio.wait_for(completion_future, timeout)
            else:
                await completion_future

            # Cancel remaining tasks if we got a successful result
            if result.success_count > 0:
                for region in regions:
                    if region != result.primary_region and region not in result.results:
                        # Add as cancelled in results
                        result.results[region] = RegionalResult(
                            region=region,
                            success=False,
                            error=asyncio.CancelledError("Operation succeeded in another region"),
                        )
        except asyncio.TimeoutError:
            logger.warning(f"Fastest execution timed out after {timeout}s: {service}.{operation}")
        finally:
            # Cancel any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

    async def _execute_in_region(
        self,
        service: str,
        operation: str,
        region: str,
        operation_kwargs: Dict[str, Any],
        client_type: ClientType,
    ) -> RegionalResult:
        """
        Execute operation in a region with concurrency control.

        This method uses a semaphore to limit concurrent executions.
        """
        async with self._semaphore:
            return await self._execute_in_region_direct(
                service, operation, region, operation_kwargs, client_type
            )

    async def _execute_in_region_direct(
        self,
        service: str,
        operation: str,
        region: str,
        operation_kwargs: Dict[str, Any],
        client_type: ClientType,
    ) -> RegionalResult:
        """
        Execute operation in a specific region.

        Args:
            service: AWS service name
            operation: Operation name
            region: AWS region
            operation_kwargs: Operation arguments
            client_type: Type of client to use

        Returns:
            Regional operation result
        """
        start_time = time.time()

        try:
            # Get client from registry
            client = await self.client_registry.get_client(service, region, client_type)

            # Execute operation
            operation_func = getattr(client, operation)
            result = await operation_func(**operation_kwargs)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Update region health metrics
            self.regional_strategy.update_region_health(region, service, True, latency_ms)

            # Return successful result
            return RegionalResult(region=region, success=True, result=result, latency_ms=latency_ms)

        except Exception as e:
            # Calculate latency even for failures
            latency_ms = (time.time() - start_time) * 1000

            # Classify error type
            error_type = str(type(e).__name__)

            # Update region health metrics
            self.regional_strategy.update_region_health(
                region, service, False, latency_ms, error_type
            )

            # Log error
            logger.warning(f"Operation {service}.{operation} failed in {region}: {str(e)}")

            # Return failed result
            return RegionalResult(region=region, success=False, error=e, latency_ms=latency_ms)

    def get_regional_stats(self, service: str) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for regions by service.

        Args:
            service: AWS service name

        Returns:
            Dictionary of region stats
        """
        # Get metrics from regional strategy
        region_metrics = self.regional_strategy.get_all_region_metrics()

        # Filter and enhance metrics for specific service
        service_metrics = {}
        for region, metrics in region_metrics.items():
            # Get latency for this service if available
            avg_latency = 0.0
            if "avg_latency_ms" in metrics and service in metrics["avg_latency_ms"]:
                avg_latency = metrics["avg_latency_ms"][service]

            # Get success rate based on execution history
            service_results = [
                result
                for result in self._execution_history
                if result.service == service and region in result.results
            ]

            success_count = sum(
                1
                for result in service_results
                if region in result.results and result.results[region].success
            )
            total_count = len(service_results)
            success_rate = success_count / total_count if total_count > 0 else 0.0

            service_metrics[region] = {
                "health": metrics.get("health", "unknown"),
                "avg_latency_ms": avg_latency,
                "success_count": success_count,
                "total_count": total_count,
                "success_rate": success_rate,
                "error_count": metrics.get("error_count", 0),
                "throttling_count": metrics.get("throttling_count", 0),
                "last_success": metrics.get("last_success", None),
                "last_failure": metrics.get("last_failure", None),
            }

        return service_metrics

    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary of execution stats
        """
        if not self._execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time_ms": 0.0,
                "services": {},
            }

        # Calculate overall statistics
        total_executions = len(self._execution_history)
        successful_executions = sum(
            1 for result in self._execution_history if result.success_count > 0
        )
        success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
        avg_execution_time = (
            sum(result.execution_time_ms for result in self._execution_history) / total_executions
        )

        # Calculate per-service statistics
        services = {}
        for result in self._execution_history:
            if result.service not in services:
                services[result.service] = {
                    "operations": {},
                    "total_executions": 0,
                    "successful_executions": 0,
                    "avg_execution_time_ms": 0.0,
                }

            service_stats = services[result.service]
            service_stats["total_executions"] += 1
            if result.success_count > 0:
                service_stats["successful_executions"] += 1

            # Update average execution time
            current_avg = service_stats["avg_execution_time_ms"]
            current_count = service_stats["total_executions"]
            service_stats["avg_execution_time_ms"] = (
                current_avg * (current_count - 1) + result.execution_time_ms
            ) / current_count

            # Track per-operation statistics
            if result.operation not in service_stats["operations"]:
                service_stats["operations"][result.operation] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "avg_execution_time_ms": 0.0,
                    "regions_used": set(),
                }

            op_stats = service_stats["operations"][result.operation]
            op_stats["total_executions"] += 1
            if result.success_count > 0:
                op_stats["successful_executions"] += 1

            # Update average execution time
            current_avg = op_stats["avg_execution_time_ms"]
            current_count = op_stats["total_executions"]
            op_stats["avg_execution_time_ms"] = (
                current_avg * (current_count - 1) + result.execution_time_ms
            ) / current_count

            # Track regions used
            for region in result.results:
                op_stats["regions_used"].add(region)

        # Convert sets to lists for JSON serialization
        for service_name, service_stats in services.items():
            for op_name, op_stats in service_stats["operations"].items():
                op_stats["regions_used"] = list(op_stats["regions_used"])

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": success_rate,
            "avg_execution_time_ms": avg_execution_time,
            "services": services,
        }

    async def execute_aggregated(
        self,
        service: str,
        operation: str,
        aggregation_function: Callable[[Dict[str, Any]], T],
        regions: Optional[List[str]] = None,
        operation_kwargs: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        timeout: Optional[float] = None,
        client_type: ClientType = ClientType.OPTIMIZED,
    ) -> T:
        """
        Execute operation across multiple regions and aggregate results.

        Args:
            service: AWS service name
            operation: Operation name
            aggregation_function: Function to aggregate results from multiple regions
            regions: Regions to execute in (defaults to all configured regions)
            operation_kwargs: Arguments for the operation
            mode: Execution mode
            timeout: Operation timeout in seconds
            client_type: Type of client to use

        Returns:
            Aggregated result

        Raises:
            asyncio.TimeoutError: If operation times out
            Exception: If operation fails in all regions
        """
        # Execute across regions
        result = await self.execute(
            service=service,
            operation=operation,
            regions=regions,
            operation_kwargs=operation_kwargs,
            mode=mode,
            timeout=timeout,
            client_type=client_type,
        )

        # If no successful results, raise exception
        if result.success_count == 0:
            raise Exception(f"Operation {service}.{operation} failed in all regions")

        # Extract successful results
        successful_results = {
            region: regional_result.result
            for region, regional_result in result.results.items()
            if regional_result.success
        }

        # Aggregate results
        return aggregation_function(successful_results)
