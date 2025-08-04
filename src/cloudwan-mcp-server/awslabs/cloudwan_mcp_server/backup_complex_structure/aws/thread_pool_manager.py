"""
Dynamic ThreadPoolExecutor Manager with Adaptive Scaling.

This module provides intelligent thread pool management with:
- Adaptive scaling based on workload
- Memory-aware thread allocation
- Performance monitoring and optimization
- Regional thread pool isolation  
- Circuit breaker patterns for fault tolerance
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from queue import Queue, Empty
from threading import Lock, RLock, Event
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
import statistics

from .performance_analytics import AWSPerformanceAnalytics

logger = logging.getLogger(__name__)


@dataclass
class ThreadPoolConfig:
    """Configuration for dynamic thread pool management."""

    min_workers: int = 5
    max_workers: int = 100
    target_queue_size: int = 10
    scale_up_threshold: float = 0.8  # Scale up when queue is 80% full
    scale_down_threshold: float = 0.2  # Scale down when queue is 20% full
    memory_limit_mb: int = 512  # Memory limit for thread pool operations
    cpu_threshold: float = 80.0  # CPU usage threshold for scaling decisions
    scale_up_delay: int = 30  # Seconds to wait before scaling up
    scale_down_delay: int = 60  # Seconds to wait before scaling down
    health_check_interval: int = 30  # Health check interval in seconds
    max_task_duration: int = 300  # Maximum task duration in seconds
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5  # Failed tasks before opening circuit
    circuit_breaker_timeout: int = 60  # Circuit breaker timeout in seconds


@dataclass
class ThreadPoolMetrics:
    """Metrics for thread pool performance monitoring."""

    current_workers: int = 0
    active_workers: int = 0
    idle_workers: int = 0
    queue_size: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_duration: float = 0.0
    peak_workers: int = 0
    total_scale_ups: int = 0
    total_scale_downs: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    circuit_breaker_trips: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TaskExecution:
    """Information about a task execution."""

    task_id: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    region: Optional[str] = None
    service: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        expected_exception: Optional[type] = None,
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.expected_exception = expected_exception or Exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        with self._lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.timeout_seconds:
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failure_count = 0
                return result

            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"

                raise e


class DynamicThreadPoolManager:
    """
    Dynamic Thread Pool Manager with adaptive scaling and performance optimization.

    Features:
    - Adaptive scaling based on workload and system resources
    - Regional thread pool isolation
    - Performance monitoring and analytics
    - Circuit breaker pattern for fault tolerance
    - Memory and CPU aware scaling decisions
    """

    def __init__(
        self,
        config: Optional[ThreadPoolConfig] = None,
        performance_analytics: Optional[AWSPerformanceAnalytics] = None,
        regions: Optional[List[str]] = None,
    ):
        """
        Initialize Dynamic Thread Pool Manager.

        Args:
            config: Thread pool configuration
            performance_analytics: Performance monitoring instance
            regions: AWS regions for regional pool isolation
        """
        self.config = config or ThreadPoolConfig()
        self.performance_analytics = performance_analytics or AWSPerformanceAnalytics()
        self.regions = regions or ["us-east-1", "us-west-2", "eu-west-1", "eu-west-2"]

        # Regional thread pools
        self._regional_pools: Dict[str, ThreadPoolExecutor] = {}
        self._pool_locks: Dict[str, Lock] = {}

        # Global thread pool for non-regional tasks
        self._global_pool: Optional[ThreadPoolExecutor] = None
        self._global_lock = Lock()

        # Metrics and monitoring
        self._metrics: Dict[str, ThreadPoolMetrics] = {}
        self._metrics_lock = RLock()
        self._task_history: List[TaskExecution] = []
        self._task_history_lock = Lock()

        # Scaling management
        self._last_scale_time: Dict[str, float] = {}
        self._scaling_lock = Lock()

        # Circuit breakers per region
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_running = False
        self._shutdown_event = Event()

        # Task tracking
        self._active_tasks: Dict[str, Set[str]] = {}  # region -> task_ids
        self._task_queues: Dict[str, Queue] = {}

        self._initialize_pools()

        logger.info(
            f"DynamicThreadPoolManager initialized - "
            f"regions: {len(self.regions)}, "
            f"worker range: {self.config.min_workers}-{self.config.max_workers}"
        )

    def _initialize_pools(self) -> None:
        """Initialize thread pools for all regions."""
        # Initialize global pool
        self._global_pool = ThreadPoolExecutor(
            max_workers=self.config.min_workers, thread_name_prefix="aws-global"
        )

        # Initialize regional pools
        for region in self.regions:
            self._regional_pools[region] = ThreadPoolExecutor(
                max_workers=self.config.min_workers, thread_name_prefix=f"aws-{region}"
            )
            self._pool_locks[region] = Lock()
            self._metrics[region] = ThreadPoolMetrics(current_workers=self.config.min_workers)
            self._circuit_breakers[region] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                timeout_seconds=self.config.circuit_breaker_timeout,
            )
            self._active_tasks[region] = set()
            self._task_queues[region] = Queue()

        # Initialize global metrics
        self._metrics["global"] = ThreadPoolMetrics(current_workers=self.config.min_workers)
        self._circuit_breakers["global"] = CircuitBreaker(
            failure_threshold=self.config.circuit_breaker_threshold,
            timeout_seconds=self.config.circuit_breaker_timeout,
        )
        self._active_tasks["global"] = set()
        self._task_queues["global"] = Queue()

    async def start_monitoring(self) -> None:
        """Start background monitoring and scaling tasks."""
        if self._health_check_running:
            return

        self._health_check_running = True
        self._health_check_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Thread pool monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring tasks."""
        self._health_check_running = False
        self._shutdown_event.set()

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        logger.info("Thread pool monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Background monitoring and auto-scaling loop."""
        while self._health_check_running:
            try:
                await self._update_metrics()
                await self._check_scaling_conditions()
                await self._cleanup_completed_tasks()

                await asyncio.sleep(self.config.health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Thread pool monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _update_metrics(self) -> None:
        """Update performance metrics for all pools."""
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=1)

        with self._metrics_lock:
            for pool_name in ["global"] + self.regions:
                metrics = self._metrics[pool_name]
                pool = self._get_pool(pool_name)

                if pool:
                    # Update worker counts
                    metrics.current_workers = pool._max_workers
                    metrics.queue_size = self._task_queues[pool_name].qsize()

                    # Update system metrics
                    metrics.memory_usage_mb = system_memory.used / 1024 / 1024
                    metrics.cpu_usage_percent = system_cpu

                    # Calculate active workers (approximate)
                    metrics.active_workers = len(self._active_tasks[pool_name])
                    metrics.idle_workers = max(0, metrics.current_workers - metrics.active_workers)

                    # Update peak workers
                    metrics.peak_workers = max(metrics.peak_workers, metrics.current_workers)

                    metrics.last_updated = datetime.now(timezone.utc)

    async def _check_scaling_conditions(self) -> None:
        """Check if any pools need scaling up or down."""
        current_time = time.time()

        for pool_name in ["global"] + self.regions:
            with self._scaling_lock:
                last_scale = self._last_scale_time.get(pool_name, 0)
                metrics = self._metrics[pool_name]

                # Check if enough time has passed since last scaling
                scale_up_ready = current_time - last_scale > self.config.scale_up_delay
                scale_down_ready = current_time - last_scale > self.config.scale_down_delay

                # Calculate queue utilization
                queue_utilization = (
                    metrics.queue_size / self.config.target_queue_size
                    if self.config.target_queue_size > 0
                    else 0
                )

                # Check scaling conditions
                should_scale_up = (
                    scale_up_ready
                    and queue_utilization > self.config.scale_up_threshold
                    and metrics.current_workers < self.config.max_workers
                    and metrics.memory_usage_mb < self.config.memory_limit_mb
                    and metrics.cpu_usage_percent < self.config.cpu_threshold
                )

                should_scale_down = (
                    scale_down_ready
                    and queue_utilization < self.config.scale_down_threshold
                    and metrics.current_workers > self.config.min_workers
                    and metrics.active_workers < metrics.current_workers * 0.5
                )

                if should_scale_up:
                    await self._scale_pool_up(pool_name)
                    self._last_scale_time[pool_name] = current_time
                elif should_scale_down:
                    await self._scale_pool_down(pool_name)
                    self._last_scale_time[pool_name] = current_time

    async def _scale_pool_up(self, pool_name: str) -> None:
        """Scale up thread pool for a specific region or global pool."""
        pool = self._get_pool(pool_name)
        if not pool:
            return

        current_workers = pool._max_workers
        new_workers = min(
            current_workers + max(1, current_workers // 4),  # Scale by 25%
            self.config.max_workers,
        )

        if new_workers > current_workers:
            # Create new pool with more workers
            old_pool = pool
            new_pool = ThreadPoolExecutor(
                max_workers=new_workers, thread_name_prefix=f"aws-{pool_name}"
            )

            # Replace the pool
            if pool_name == "global":
                self._global_pool = new_pool
            else:
                self._regional_pools[pool_name] = new_pool

            # Update metrics
            with self._metrics_lock:
                self._metrics[pool_name].current_workers = new_workers
                self._metrics[pool_name].total_scale_ups += 1

            logger.info(f"Scaled up {pool_name} pool: {current_workers} -> {new_workers} workers")

            # Schedule old pool shutdown (give running tasks time to complete)
            asyncio.create_task(self._delayed_pool_shutdown(old_pool, 60))

    async def _scale_pool_down(self, pool_name: str) -> None:
        """Scale down thread pool for a specific region or global pool."""
        pool = self._get_pool(pool_name)
        if not pool:
            return

        current_workers = pool._max_workers
        new_workers = max(
            current_workers - max(1, current_workers // 4),  # Scale down by 25%
            self.config.min_workers,
        )

        if new_workers < current_workers:
            # Create new pool with fewer workers
            old_pool = pool
            new_pool = ThreadPoolExecutor(
                max_workers=new_workers, thread_name_prefix=f"aws-{pool_name}"
            )

            # Replace the pool
            if pool_name == "global":
                self._global_pool = new_pool
            else:
                self._regional_pools[pool_name] = new_pool

            # Update metrics
            with self._metrics_lock:
                self._metrics[pool_name].current_workers = new_workers
                self._metrics[pool_name].total_scale_downs += 1

            logger.info(f"Scaled down {pool_name} pool: {current_workers} -> {new_workers} workers")

            # Schedule old pool shutdown
            asyncio.create_task(self._delayed_pool_shutdown(old_pool, 60))

    async def _delayed_pool_shutdown(self, pool: ThreadPoolExecutor, delay: int) -> None:
        """Shutdown a thread pool after a delay to allow tasks to complete."""
        await asyncio.sleep(delay)
        try:
            pool.shutdown(wait=True)
        except Exception as e:
            logger.warning(f"Error during delayed pool shutdown: {e}")

    async def _cleanup_completed_tasks(self) -> None:
        """Clean up completed task history to prevent memory leaks."""
        with self._task_history_lock:
            # Keep only recent task history (last 1000 tasks)
            if len(self._task_history) > 1000:
                self._task_history = self._task_history[-1000:]

            # Update average task duration
            if self._task_history:
                completed_tasks = [t for t in self._task_history if t.duration is not None]
                if completed_tasks:
                    durations = [t.duration for t in completed_tasks]
                    avg_duration = statistics.mean(durations)

                    with self._metrics_lock:
                        for metrics in self._metrics.values():
                            metrics.avg_task_duration = avg_duration

    def _get_pool(self, pool_name: str) -> Optional[ThreadPoolExecutor]:
        """Get thread pool by name."""
        if pool_name == "global":
            return self._global_pool
        return self._regional_pools.get(pool_name)

    def submit_task(
        self,
        func: Callable,
        *args,
        region: Optional[str] = None,
        service: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Submit task to appropriate thread pool.

        Args:
            func: Function to execute
            *args: Function arguments
            region: AWS region (for regional pool selection)
            service: AWS service name
            task_id: Optional task identifier
            **kwargs: Function keyword arguments

        Returns:
            Future object for the task
        """
        pool_name = region if region in self.regions else "global"
        pool = self._get_pool(pool_name)

        if not pool:
            raise ValueError(f"No thread pool available for {pool_name}")

        # Generate task ID if not provided
        if not task_id:
            task_id = f"{pool_name}-{int(time.time() * 1000)}"

        # Add task to queue tracking
        self._task_queues[pool_name].put(task_id)
        self._active_tasks[pool_name].add(task_id)

        # Create task execution record
        task_execution = TaskExecution(
            task_id=task_id, start_time=time.time(), region=region, service=service
        )

        # Wrap function with monitoring and circuit breaker
        def monitored_func(*args, **kwargs):
            try:
                # Circuit breaker protection
                if self.config.enable_circuit_breaker:
                    result = self._circuit_breakers[pool_name].call(func, *args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Update task execution record
                task_execution.end_time = time.time()
                task_execution.duration = task_execution.end_time - task_execution.start_time
                task_execution.success = True

                # Update metrics
                with self._metrics_lock:
                    self._metrics[pool_name].completed_tasks += 1

                return result

            except Exception as e:
                # Update task execution record
                task_execution.end_time = time.time()
                task_execution.duration = task_execution.end_time - task_execution.start_time
                task_execution.success = False
                task_execution.error = str(e)

                # Update metrics
                with self._metrics_lock:
                    self._metrics[pool_name].failed_tasks += 1
                    if isinstance(e, Exception) and "circuit breaker" in str(e).lower():
                        self._metrics[pool_name].circuit_breaker_trips += 1

                raise e

            finally:
                # Clean up task tracking
                try:
                    self._task_queues[pool_name].get_nowait()
                except Empty:
                    pass

                self._active_tasks[pool_name].discard(task_id)

                # Add to task history
                with self._task_history_lock:
                    self._task_history.append(task_execution)

                # Record performance metrics
                if self.performance_analytics and task_execution.duration:
                    self.performance_analytics.record_task_execution(
                        service=service or "unknown",
                        region=region or "global",
                        duration_ms=task_execution.duration * 1000,
                        success=task_execution.success,
                    )

        # Submit to thread pool
        future = pool.submit(monitored_func, *args, **kwargs)

        logger.debug(f"Submitted task {task_id} to {pool_name} pool")
        return future

    def submit_batch(
        self,
        tasks: List[Tuple[Callable, tuple, dict]],
        region: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> List[Any]:
        """
        Submit multiple tasks and wait for all to complete.

        Args:
            tasks: List of (function, args, kwargs) tuples
            region: AWS region for pool selection
            timeout: Maximum time to wait for completion

        Returns:
            List of results in the same order as input tasks
        """
        futures = []
        for i, (func, args, kwargs) in enumerate(tasks):
            task_id = f"batch-{int(time.time() * 1000)}-{i}"
            future = self.submit_task(func, *args, region=region, task_id=task_id, **kwargs)
            futures.append(future)

        # Wait for all tasks to complete
        results = []
        for future in as_completed(futures, timeout=timeout):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Batch task failed: {e}")
                results.append({"error": str(e)})

        return results

    def get_metrics(
        self, pool_name: Optional[str] = None
    ) -> Union[ThreadPoolMetrics, Dict[str, ThreadPoolMetrics]]:
        """
        Get performance metrics for thread pools.

        Args:
            pool_name: Specific pool name, or None for all pools

        Returns:
            Metrics for specified pool or all pools
        """
        with self._metrics_lock:
            if pool_name:
                return self._metrics.get(pool_name, ThreadPoolMetrics())
            return self._metrics.copy()

    def get_pool_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all thread pools."""
        all_metrics = self.get_metrics()

        status = {
            "config": {
                "min_workers": self.config.min_workers,
                "max_workers": self.config.max_workers,
                "target_queue_size": self.config.target_queue_size,
                "memory_limit_mb": self.config.memory_limit_mb,
                "cpu_threshold": self.config.cpu_threshold,
                "circuit_breaker_enabled": self.config.enable_circuit_breaker,
            },
            "pools": {},
            "summary": {
                "total_pools": len(all_metrics),
                "total_workers": sum(m.current_workers for m in all_metrics.values()),
                "total_active_tasks": sum(len(tasks) for tasks in self._active_tasks.values()),
                "total_completed_tasks": sum(m.completed_tasks for m in all_metrics.values()),
                "total_failed_tasks": sum(m.failed_tasks for m in all_metrics.values()),
                "avg_success_rate": self._calculate_success_rate(),
            },
        }

        for pool_name, metrics in all_metrics.items():
            circuit_breaker = self._circuit_breakers.get(pool_name)
            status["pools"][pool_name] = {
                "workers": {
                    "current": metrics.current_workers,
                    "active": metrics.active_workers,
                    "idle": metrics.idle_workers,
                    "peak": metrics.peak_workers,
                },
                "tasks": {
                    "queue_size": metrics.queue_size,
                    "completed": metrics.completed_tasks,
                    "failed": metrics.failed_tasks,
                    "avg_duration_ms": metrics.avg_task_duration * 1000,
                },
                "scaling": {
                    "scale_ups": metrics.total_scale_ups,
                    "scale_downs": metrics.total_scale_downs,
                },
                "resources": {
                    "memory_usage_mb": metrics.memory_usage_mb,
                    "cpu_usage_percent": metrics.cpu_usage_percent,
                },
                "circuit_breaker": {
                    "state": circuit_breaker.state if circuit_breaker else "N/A",
                    "failure_count": (circuit_breaker.failure_count if circuit_breaker else 0),
                    "trips": metrics.circuit_breaker_trips,
                },
                "last_updated": metrics.last_updated.isoformat(),
            }

        return status

    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate across all pools."""
        total_completed = sum(m.completed_tasks for m in self._metrics.values())
        total_failed = sum(m.failed_tasks for m in self._metrics.values())
        total_tasks = total_completed + total_failed

        if total_tasks == 0:
            return 1.0

        return total_completed / total_tasks

    async def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown all thread pools.

        Args:
            wait: Whether to wait for running tasks to complete
        """
        logger.info("Shutting down Dynamic Thread Pool Manager")

        # Stop monitoring
        await self.stop_monitoring()

        # Shutdown all pools
        pools_to_shutdown = []

        if self._global_pool:
            pools_to_shutdown.append(self._global_pool)

        pools_to_shutdown.extend(self._regional_pools.values())

        # Shutdown pools concurrently
        shutdown_tasks = []
        for pool in pools_to_shutdown:
            # Create the coroutine properly
            async def shutdown_pool(p):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: p.shutdown(wait=wait))

            shutdown_tasks.append(shutdown_pool(pool))

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        # Clear all data structures
        self._regional_pools.clear()
        self._pool_locks.clear()
        self._metrics.clear()
        self._active_tasks.clear()
        self._task_queues.clear()
        self._circuit_breakers.clear()

        with self._task_history_lock:
            self._task_history.clear()

        logger.info("Dynamic Thread Pool Manager shutdown completed")

    def __del__(self):
        """Cleanup on garbage collection."""
        try:
            # Can't run async cleanup in __del__, just shutdown pools synchronously
            if self._global_pool:
                self._global_pool.shutdown(wait=False)

            for pool in self._regional_pools.values():
                pool.shutdown(wait=False)

        except Exception:
            pass  # Ignore cleanup errors during destruction
