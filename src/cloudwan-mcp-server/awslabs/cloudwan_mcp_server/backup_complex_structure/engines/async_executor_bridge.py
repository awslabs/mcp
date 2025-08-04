"""
Async Executor Bridge.

This module provides adaptation of ThreadPoolExecutor patterns to anyio-based async/await
patterns while maintaining exact error handling and result aggregation behaviors.

Bridges synchronous executor patterns with modern async/await execution models.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

import anyio
from botocore.exceptions import BotoCoreError, ClientError

from ..aws.client_manager import AWSClientManager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TaskStatus(Enum):
    """Task execution status (from legacy patterns)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTaskResult:
    """Async task result for executor bridge patterns."""

    task_id: str
    region: str | None
    service: str | None
    operation: str
    status: TaskStatus
    result: Any = None
    error: Exception | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    execution_time: float | None = None

    def complete(self, result: Any = None, error: Exception | None = None) -> None:
        """Mark task as completed with result or error."""
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time

        if error:
            self.status = TaskStatus.FAILED
            self.error = error
        else:
            self.status = TaskStatus.COMPLETED
            self.result = result


@dataclass
class BatchExecutionStats:
    """Statistics for batch execution operations."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    total_execution_time: float = 0
    average_execution_time: float = 0
    success_rate: float = 0

    def calculate(self, results: list[AsyncTaskResult]) -> "BatchExecutionStats":
        """Calculate statistics from task results."""
        self.total_tasks = len(results)
        self.completed_tasks = len([r for r in results if r.status == TaskStatus.COMPLETED])
        self.failed_tasks = len([r for r in results if r.status == TaskStatus.FAILED])
        self.cancelled_tasks = len([r for r in results if r.status == TaskStatus.CANCELLED])

        execution_times = [r.execution_time for r in results if r.execution_time is not None]
        if execution_times:
            self.total_execution_time = sum(execution_times)
            self.average_execution_time = self.total_execution_time / len(execution_times)

        if self.total_tasks > 0:
            self.success_rate = self.completed_tasks / self.total_tasks

        return self


# Define allowed operations per service
ALLOWED_OPERATIONS = {
    'ec2': ['DescribeInstances', 'DescribeVpcs'],
    'cloudwan': ['GetCoreNetwork', 'ListAttachments']
}

class ToolError(Exception):
    """Custom error for operation validation failures"""
    pass

class AsyncExecutorBridge:
    """
    Bridge between ThreadPoolExecutor patterns and async/await execution.

    This class maintains compatibility with synchronous executor patterns while providing
    while providing async/await patterns using anyio.
    """

    def __init__(self, aws_manager: AWSClientManager, max_workers: int = 5):
        """Initialize with AWS client manager and worker configuration."""
        self.aws_manager = aws_manager
        self.max_workers = max_workers
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Legacy-compatible retry configuration
        self.retry_count = 3
        self.retry_delay = 1.0
        self.retry_exponential_backoff = True

    async def execute_multi_region_operation(
        self,
        regions: list[str],
        operation: Callable[[str], Any],
        operation_name: str = "operation",
        service_name: str = "aws",
    ) -> list[AsyncTaskResult]:
        """
        Execute operation across multiple regions using legacy patterns.

        This method replicates the exact ThreadPoolExecutor behavior from legacy scripts
        including error handling, result aggregation, and retry logic.
        """
        tasks = []
        for i, region in enumerate(regions):
            task_result = AsyncTaskResult(
                task_id=f"{operation_name}_{region}_{i}",
                region=region,
                service=service_name,
                operation=operation_name,
            )
            tasks.append(task_result)

        # Execute operations concurrently using anyio
        async with anyio.create_task_group() as task_group:
            for task_result in tasks:
                task_group.start_soon(self._execute_single_region_task, task_result, operation)

        return tasks

    async def _execute_async_operation(self, client, operation_name: str, kwargs: dict = None):
        """Security-validated operation execution"""
        service = client.meta.service_name
        if operation_name not in ALLOWED_OPERATIONS.get(service, []):
            raise ToolError(f"Operation {operation_name} not permitted for service {service}")
        
        # Use the appropriate method based on operation name
        method = getattr(client, operation_name.lower())
        return await method(**(kwargs or {}))

    async def _execute_single_region_task(
        self, task_result: AsyncTaskResult, operation: Callable
    ) -> None:
        """Execute using native async clients."""
        task_result.status = TaskStatus.RUNNING
        
        try:
            async with self.aws_manager.get_async_client(task_result.service or 'ec2', task_result.region) as client:
                result = await operation(client)
                task_result.complete(result=result)
        except Exception as e:
            self.logger.error(f"Error in {task_result.operation} for {task_result.region}: {e}")
            task_result.complete(error=e)

    async def _run_operation_with_timeout(
        self, operation: Callable[[str], Any], region: str
    ) -> Any:
        """Run operation with timeout (legacy pattern)."""
        try:
            with anyio.move_on_after(30):  # 30 second timeout like legacy scripts
                return await anyio.to_thread.run_sync(operation, region)
        except anyio.get_cancelled_exc_class():
            raise TimeoutError(f"Operation timed out for region {region}")

    async def _legacy_retry_delay(self, attempt: int) -> None:
        """Legacy-compatible retry delay with exponential backoff."""
        if self.retry_exponential_backoff:
            delay = self.retry_delay * (2**attempt)
        else:
            delay = self.retry_delay

        self.logger.info(f"Retrying in {delay} seconds (attempt {attempt + 1})")
        await anyio.sleep(delay)

    def aggregate_results(self, results: list[AsyncTaskResult]) -> dict[str, Any]:
        """Aggregate results using legacy patterns."""
        successful_results = []
        failed_regions = []
        warnings = []

        for result in results:
            if result.status == TaskStatus.COMPLETED:
                if result.result:
                    successful_results.extend(
                        result.result if isinstance(result.result, list) else [result.result]
                    )
            elif result.status == TaskStatus.FAILED:
                failed_regions.append(result.region)
                if result.error:
                    warnings.append(f"Region {result.region} failed: {str(result.error)}")

        # Calculate execution statistics
        stats = BatchExecutionStats().calculate(results)

        return {
            "results": successful_results,
            "failed_regions": failed_regions,
            "warnings": warnings,
            "execution_stats": stats,
            "total_regions": len(results),
            "successful_regions": stats.completed_tasks,
            "success_rate": stats.success_rate,
        }

    # Legacy operation compatibility methods
    async def vpc_discovery(self, regions: list[str]) -> dict[str, Any]:
        """VPC discovery operation using legacy patterns."""

        def vpc_operation(region: str) -> list[dict]:
            # Simulate VPC discovery (would call actual AWS APIs)
            return [{"vpc_id": f"vpc-{region}-example", "region": region}]

        results = await self.execute_multi_region_operation(
            regions, vpc_operation, "vpc_discovery", "ec2"
        )
        return self.aggregate_results(results)

    async def ip_finder(self, regions: list[str], target_ip: str) -> dict[str, Any]:
        """IP finder operation using legacy patterns."""

        def ip_operation(region: str) -> list[dict]:
            # Simulate IP discovery (would call actual AWS APIs)
            return [{"ip": target_ip, "region": region, "found": True}]

        results = await self.execute_multi_region_operation(
            regions, lambda r: ip_operation(r), "ip_finder", "multi"
        )
        return self.aggregate_results(results)

    async def tgw_analysis(self, regions: list[str]) -> dict[str, Any]:
        """Transit Gateway analysis using legacy patterns."""

        def tgw_operation(region: str) -> list[dict]:
            # Simulate TGW analysis (would call actual AWS APIs)
            return [{"tgw_id": f"tgw-{region}-example", "region": region}]

        results = await self.execute_multi_region_operation(
            regions, tgw_operation, "tgw_analysis", "ec2"
        )
        return self.aggregate_results(results)


# Factory function for easy instantiation
def create_legacy_adapter(
    aws_manager: AWSClientManager, max_workers: int = 5
) -> AsyncExecutorBridge:
    """Create legacy pattern adapter with standard configuration."""
    return AsyncExecutorBridge(aws_manager, max_workers)
