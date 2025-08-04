"""
Memory Optimization Engine for Large-Scale CloudWAN Topology Processing.

This module implements comprehensive memory management strategies for processing
large AWS network topologies with thousands of elements and connections.

Key features:
- Memory-efficient data structures with __slots__
- Streaming topology discovery for large datasets
- Memory-aware caching and pooling
- Lazy loading and progressive rendering
- Real-time memory monitoring and alerting
- Memory pressure handling and circuit breakers
"""

import asyncio
import gc
import logging
import psutil
import tracemalloc
import weakref
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Union,
    Iterator,
    Callable,
)
from weakref import WeakValueDictionary, WeakSet
import sys
import threading

from ..models.network import NetworkElement, NetworkConnection


class MemoryPressureLevel(Enum):
    """Memory pressure levels for system monitoring."""

    LOW = "low"  # < 60% memory usage
    MODERATE = "moderate"  # 60-75% memory usage
    HIGH = "high"  # 75-85% memory usage
    CRITICAL = "critical"  # 85-95% memory usage
    EMERGENCY = "emergency"  # > 95% memory usage


class MemoryOptimizationStrategy(Enum):
    """Memory optimization strategies."""

    CONSERVATIVE = "conservative"  # Minimal memory usage
    BALANCED = "balanced"  # Balance memory vs performance
    AGGRESSIVE = "aggressive"  # Maximum performance


@dataclass
class MemoryMetrics:
    """Memory usage metrics and statistics."""

    __slots__ = (
        "timestamp",
        "total_memory_mb",
        "used_memory_mb",
        "available_memory_mb",
        "memory_percent",
        "process_memory_mb",
        "pressure_level",
        "gc_collections",
        "object_counts",
        "peak_memory_mb",
        "memory_growth_rate",
    )

    timestamp: float
    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    pressure_level: MemoryPressureLevel
    gc_collections: Dict[int, int] = field(default_factory=dict)
    object_counts: Dict[str, int] = field(default_factory=dict)
    peak_memory_mb: float = 0.0
    memory_growth_rate: float = 0.0


class MemoryEfficientNetworkElement:
    """Memory-optimized network element with __slots__ for reduced overhead."""

    __slots__ = (
        "id",
        "name",
        "element_type",
        "region",
        "availability_zone",
        "state",
        "cidr_blocks",
        "tags",
        "_parent_id",
        "_child_ids_ref",
        "ip_addresses",
        "dns_names",
        "ports",
        "segment_name",
        "core_network_id",
        "attachment_id",
        "_raw_data_ref",
    )

    def __init__(
        self,
        id: str,
        name: str,
        element_type: str,
        region: str,
        availability_zone: str = None,
        state: str = "unknown",
    ):
        self.id = id
        self.name = name
        self.element_type = element_type
        self.region = region
        self.availability_zone = availability_zone
        self.state = state

        # Use more memory-efficient structures
        self.cidr_blocks = []  # Only create when needed
        self.tags = {}  # Only create when needed
        self.ip_addresses = []  # Only create when needed
        self.dns_names = []  # Only create when needed
        self.ports = []  # Only create when needed

        # Use weak references for relationships to avoid circular references
        self._parent_id = None
        self._child_ids_ref = None  # WeakSet created only when needed

        # Optional fields - use None to save memory
        self.segment_name = None
        self.core_network_id = None
        self.attachment_id = None

        # Use weak reference for raw data to allow GC
        self._raw_data_ref = None

    @property
    def parent_id(self) -> Optional[str]:
        return self._parent_id

    @parent_id.setter
    def parent_id(self, value: Optional[str]):
        self._parent_id = value

    @property
    def child_ids(self) -> Set[str]:
        if self._child_ids_ref is None:
            self._child_ids_ref = set()
        return self._child_ids_ref

    def add_child_id(self, child_id: str):
        if self._child_ids_ref is None:
            self._child_ids_ref = set()
        self._child_ids_ref.add(child_id)

    def set_raw_data(self, data: Dict[str, Any]):
        """Store raw data with weak reference to allow GC."""
        if data:
            # Store in object pool for potential reuse
            self._raw_data_ref = weakref.ref(data)

    def get_raw_data(self) -> Optional[Dict[str, Any]]:
        """Retrieve raw data if still in memory."""
        if self._raw_data_ref:
            return self._raw_data_ref()
        return None

    def memory_footprint(self) -> int:
        """Calculate approximate memory footprint in bytes."""
        size = sys.getsizeof(self)
        size += sys.getsizeof(self.id) if self.id else 0
        size += sys.getsizeof(self.name) if self.name else 0
        size += sys.getsizeof(self.cidr_blocks) + sum(sys.getsizeof(c) for c in self.cidr_blocks)
        size += sys.getsizeof(self.tags) + sum(
            sys.getsizeof(k) + sys.getsizeof(v) for k, v in self.tags.items()
        )
        size += sys.getsizeof(self.ip_addresses) + sum(
            sys.getsizeof(ip) for ip in self.ip_addresses
        )
        return size


class MemoryEfficientNetworkConnection:
    """Memory-optimized network connection with __slots__."""

    __slots__ = (
        "source_id",
        "target_id",
        "connection_type",
        "state",
        "bandwidth",
        "latency_ms",
        "cost",
        "attachment_id",
        "segment_name",
        "_metadata_ref",
    )

    def __init__(
        self,
        source_id: str,
        target_id: str,
        connection_type: str,
        state: str = "active",
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.connection_type = connection_type
        self.state = state

        # Optional fields - use None to save memory
        self.bandwidth = None
        self.latency_ms = None
        self.cost = None
        self.attachment_id = None
        self.segment_name = None

        # Use weak reference for additional metadata
        self._metadata_ref = None

    def set_metadata(self, metadata: Dict[str, Any]):
        """Store metadata with weak reference."""
        if metadata:
            self._metadata_ref = weakref.ref(metadata)

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Retrieve metadata if still in memory."""
        if self._metadata_ref:
            return self._metadata_ref()
        return None


class ObjectPool:
    """Object pool for reusing frequently created objects."""

    def __init__(self, factory: Callable, max_size: int = 1000):
        self.factory = factory
        self.max_size = max_size
        self._pool = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def get(self, *args, **kwargs):
        """Get an object from the pool or create a new one."""
        with self._lock:
            if self._pool:
                obj = self._pool.popleft()
                # Reinitialize the object
                obj.__init__(*args, **kwargs)
                return obj

        # Create new object if pool is empty
        return self.factory(*args, **kwargs)

    def put(self, obj):
        """Return an object to the pool."""
        with self._lock:
            if len(self._pool) < self.max_size:
                self._pool.append(obj)


class MemoryPool:
    """Memory pool for managing reusable memory chunks."""

    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        self.chunk_size = chunk_size
        self._available_chunks = deque()
        self._allocated_chunks = WeakSet()
        self._lock = threading.Lock()

    def allocate(self, size: int) -> bytearray:
        """Allocate a memory chunk of requested size."""
        if size <= self.chunk_size:
            with self._lock:
                if self._available_chunks:
                    chunk = self._available_chunks.popleft()
                    self._allocated_chunks.add(chunk)
                    return chunk

        # Create new chunk
        chunk = bytearray(max(size, self.chunk_size))
        with self._lock:
            self._allocated_chunks.add(chunk)
        return chunk

    def deallocate(self, chunk: bytearray):
        """Return a chunk to the available pool."""
        with self._lock:
            if chunk in self._allocated_chunks:
                self._allocated_chunks.discard(chunk)
                if len(self._available_chunks) < 100:  # Limit pool size
                    # Clear the chunk and reuse it
                    chunk[:] = bytearray(len(chunk))
                    self._available_chunks.append(chunk)


class StreamingTopologyIterator:
    """Iterator for processing large topologies in chunks."""

    def __init__(
        self,
        elements: Dict[str, Any],
        chunk_size: int = 100,
        memory_threshold_mb: float = 500.0,
    ):
        self.elements = elements
        self.chunk_size = chunk_size
        self.memory_threshold_mb = memory_threshold_mb
        self._element_ids = list(elements.keys())
        self._current_index = 0
        self._current_chunk = []
        self.logger = logging.getLogger(__name__)

    def __iter__(self) -> Iterator[List[MemoryEfficientNetworkElement]]:
        return self

    def __next__(self) -> List[MemoryEfficientNetworkElement]:
        if self._current_index >= len(self._element_ids):
            raise StopIteration

        # Check memory pressure before loading next chunk
        memory_info = psutil.virtual_memory()
        current_memory_mb = memory_info.used / (1024 * 1024)

        if current_memory_mb > self.memory_threshold_mb:
            # Force garbage collection
            gc.collect()
            self.logger.warning(f"Memory threshold exceeded: {current_memory_mb}MB")

        # Load next chunk
        chunk_elements = []
        chunk_end = min(self._current_index + self.chunk_size, len(self._element_ids))

        for i in range(self._current_index, chunk_end):
            element_id = self._element_ids[i]
            element_data = self.elements[element_id]

            # Convert to memory-efficient element
            efficient_element = self._convert_to_efficient_element(element_data)
            chunk_elements.append(efficient_element)

        self._current_index = chunk_end
        return chunk_elements

    def _convert_to_efficient_element(self, element_data: Any) -> MemoryEfficientNetworkElement:
        """Convert standard element to memory-efficient version."""
        if hasattr(element_data, "id"):
            # Convert from NetworkElement
            efficient = MemoryEfficientNetworkElement(
                id=element_data.id,
                name=element_data.name,
                element_type=str(element_data.element_type),
                region=element_data.region,
                availability_zone=element_data.availability_zone,
                state=element_data.state,
            )

            # Copy essential data only
            if hasattr(element_data, "cidr_blocks") and element_data.cidr_blocks:
                efficient.cidr_blocks = list(element_data.cidr_blocks)
            if hasattr(element_data, "tags") and element_data.tags:
                efficient.tags = dict(element_data.tags)

            return efficient
        else:
            # Handle dictionary format
            return MemoryEfficientNetworkElement(
                id=element_data.get("id", ""),
                name=element_data.get("name", ""),
                element_type=element_data.get("element_type", ""),
                region=element_data.get("region", ""),
                availability_zone=element_data.get("availability_zone"),
                state=element_data.get("state", "unknown"),
            )


class MemoryOptimizedTopology:
    """Memory-optimized topology container with streaming capabilities."""

    def __init__(
        self,
        strategy: MemoryOptimizationStrategy = MemoryOptimizationStrategy.BALANCED,
        max_elements_in_memory: int = 10000,
        enable_compression: bool = True,
    ):
        self.strategy = strategy
        self.max_elements_in_memory = max_elements_in_memory
        self.enable_compression = enable_compression

        # Use weak references to allow garbage collection
        self._elements_cache = WeakValueDictionary()
        self._connections_cache = WeakValueDictionary()

        # Element and connection pools
        self._element_pool = ObjectPool(MemoryEfficientNetworkElement, max_size=1000)
        self._connection_pool = ObjectPool(MemoryEfficientNetworkConnection, max_size=1000)

        # Memory tracking
        self._memory_usage_mb = 0.0
        self._peak_memory_mb = 0.0

        # Statistics
        self.regions = set()
        self.element_counts = {}
        self.connection_counts = {}

        self.logger = logging.getLogger(__name__)

    def add_element(self, element: Union[NetworkElement, MemoryEfficientNetworkElement]) -> str:
        """Add element to topology with memory management."""

        # Convert to memory-efficient format if needed
        if not isinstance(element, MemoryEfficientNetworkElement):
            efficient_element = self._convert_to_efficient_element(element)
        else:
            efficient_element = element

        # Check memory limits
        if len(self._elements_cache) >= self.max_elements_in_memory:
            self._evict_least_recently_used_elements()

        # Store in cache
        self._elements_cache[efficient_element.id] = efficient_element

        # Update statistics
        self.regions.add(efficient_element.region)
        element_type = efficient_element.element_type
        self.element_counts[element_type] = self.element_counts.get(element_type, 0) + 1

        # Update memory usage estimation
        self._update_memory_usage()

        return efficient_element.id

    def get_element(self, element_id: str) -> Optional[MemoryEfficientNetworkElement]:
        """Get element by ID with lazy loading if needed."""
        return self._elements_cache.get(element_id)

    def stream_elements(
        self,
        element_type: Optional[str] = None,
        region: Optional[str] = None,
        chunk_size: int = 100,
    ) -> Iterator[List[MemoryEfficientNetworkElement]]:
        """Stream elements in chunks for memory-efficient processing."""

        matching_elements = []
        for element in self._elements_cache.values():
            if element_type and element.element_type != element_type:
                continue
            if region and element.region != region:
                continue
            matching_elements.append(element)

        # Yield elements in chunks
        for i in range(0, len(matching_elements), chunk_size):
            chunk = matching_elements[i : i + chunk_size]
            yield chunk

    def add_connection(
        self, connection: Union[NetworkConnection, MemoryEfficientNetworkConnection]
    ) -> str:
        """Add connection to topology with memory management."""

        # Convert to memory-efficient format if needed
        if not isinstance(connection, MemoryEfficientNetworkConnection):
            efficient_connection = self._convert_to_efficient_connection(connection)
        else:
            efficient_connection = connection

        # Generate connection ID
        connection_id = f"{efficient_connection.source_id}->{efficient_connection.target_id}"

        # Store in cache
        self._connections_cache[connection_id] = efficient_connection

        # Update statistics
        conn_type = efficient_connection.connection_type
        self.connection_counts[conn_type] = self.connection_counts.get(conn_type, 0) + 1

        return connection_id

    def get_connections_for_element(
        self, element_id: str
    ) -> List[MemoryEfficientNetworkConnection]:
        """Get all connections for a specific element."""
        connections = []
        for connection in self._connections_cache.values():
            if connection.source_id == element_id or connection.target_id == element_id:
                connections.append(connection)
        return connections

    def _convert_to_efficient_element(
        self, element: NetworkElement
    ) -> MemoryEfficientNetworkElement:
        """Convert NetworkElement to memory-efficient version."""
        efficient = MemoryEfficientNetworkElement(
            id=element.id,
            name=element.name,
            element_type=str(element.element_type),
            region=element.region,
            availability_zone=element.availability_zone,
            state=element.state,
        )

        # Copy only essential data
        if element.cidr_blocks:
            efficient.cidr_blocks = list(element.cidr_blocks)
        if element.tags:
            efficient.tags = dict(element.tags)
        if element.ip_addresses:
            efficient.ip_addresses = list(element.ip_addresses)

        return efficient

    def _convert_to_efficient_connection(
        self, connection: NetworkConnection
    ) -> MemoryEfficientNetworkConnection:
        """Convert NetworkConnection to memory-efficient version."""
        efficient = MemoryEfficientNetworkConnection(
            source_id=connection.source_id,
            target_id=connection.target_id,
            connection_type=str(connection.connection_type),
            state=connection.state,
        )

        # Copy optional fields if they exist
        if hasattr(connection, "bandwidth"):
            efficient.bandwidth = connection.bandwidth
        if hasattr(connection, "latency_ms"):
            efficient.latency_ms = connection.latency_ms

        return efficient

    def _evict_least_recently_used_elements(self, count: int = None):
        """Evict least recently used elements to free memory."""
        if count is None:
            count = max(100, len(self._elements_cache) // 10)  # Evict 10% by default

        # Simple eviction - in production, implement proper LRU
        elements_to_evict = list(self._elements_cache.keys())[:count]
        for element_id in elements_to_evict:
            self._elements_cache.pop(element_id, None)

        self.logger.info(f"Evicted {len(elements_to_evict)} elements from memory")

    def _update_memory_usage(self):
        """Update memory usage estimation."""
        current_mb = (len(self._elements_cache) * 1024 + len(self._connections_cache) * 256) / (
            1024 * 1024
        )
        self._memory_usage_mb = current_mb
        if current_mb > self._peak_memory_mb:
            self._peak_memory_mb = current_mb

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        return {
            "elements_in_memory": len(self._elements_cache),
            "connections_in_memory": len(self._connections_cache),
            "estimated_memory_mb": self._memory_usage_mb,
            "peak_memory_mb": self._peak_memory_mb,
            "total_regions": len(self.regions),
            "element_counts": self.element_counts.copy(),
            "connection_counts": self.connection_counts.copy(),
        }

    def clear_cache(self):
        """Clear all cached data to free memory."""
        self._elements_cache.clear()
        self._connections_cache.clear()
        self._memory_usage_mb = 0.0
        gc.collect()
        self.logger.info("Topology cache cleared")


class MemoryMonitor:
    """Real-time memory monitoring and alerting system."""

    def __init__(
        self,
        check_interval: float = 5.0,
        alert_thresholds: Optional[Dict[MemoryPressureLevel, float]] = None,
    ):
        self.check_interval = check_interval
        self.alert_thresholds = alert_thresholds or {
            MemoryPressureLevel.MODERATE: 60.0,
            MemoryPressureLevel.HIGH: 75.0,
            MemoryPressureLevel.CRITICAL: 85.0,
            MemoryPressureLevel.EMERGENCY: 95.0,
        }

        self._monitoring = False
        self._monitor_task = None
        self._metrics_history = deque(maxlen=1000)
        self._alert_callbacks = []
        self._last_gc_time = 0

        self.logger = logging.getLogger(__name__)

    async def start_monitoring(self):
        """Start memory monitoring."""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            self.logger.info("Memory monitoring started")

    async def stop_monitoring(self):
        """Stop memory monitoring."""
        if self._monitoring:
            self._monitoring = False
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            self.logger.info("Memory monitoring stopped")

    def add_alert_callback(self, callback: Callable[[MemoryMetrics], None]):
        """Add callback for memory alerts."""
        self._alert_callbacks.append(callback)

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                metrics = self._collect_metrics()
                self._metrics_history.append(metrics)

                # Check for pressure levels and alerts
                await self._check_pressure_levels(metrics)

                # Automatic garbage collection if needed
                await self._auto_gc(metrics)

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Error in memory monitoring: {e}")
                await asyncio.sleep(self.check_interval)

    def _collect_metrics(self) -> MemoryMetrics:
        """Collect current memory metrics."""
        import time

        # System memory
        memory = psutil.virtual_memory()

        # Process memory
        process = psutil.Process()
        process_memory = process.memory_info()

        # GC statistics
        gc_stats = {i: gc.get_count()[i] for i in range(len(gc.get_count()))}

        # Determine pressure level
        pressure_level = self._determine_pressure_level(memory.percent)

        # Object counts
        object_counts = {}
        if hasattr(gc, "get_objects"):
            all_objects = gc.get_objects()
            for obj in all_objects[:1000]:  # Limit to first 1000 for performance
                obj_type = type(obj).__name__
                object_counts[obj_type] = object_counts.get(obj_type, 0) + 1

        # Calculate growth rate
        memory_growth_rate = 0.0
        if len(self._metrics_history) >= 2:
            prev_memory = self._metrics_history[-1].process_memory_mb
            current_memory = process_memory.rss / (1024 * 1024)
            time_diff = time.time() - self._metrics_history[-1].timestamp
            if time_diff > 0:
                memory_growth_rate = (current_memory - prev_memory) / time_diff

        return MemoryMetrics(
            timestamp=time.time(),
            total_memory_mb=memory.total / (1024 * 1024),
            used_memory_mb=memory.used / (1024 * 1024),
            available_memory_mb=memory.available / (1024 * 1024),
            memory_percent=memory.percent,
            process_memory_mb=process_memory.rss / (1024 * 1024),
            pressure_level=pressure_level,
            gc_collections=gc_stats,
            object_counts=object_counts,
            peak_memory_mb=max(
                (self._metrics_history[-1].peak_memory_mb if self._metrics_history else 0),
                process_memory.rss / (1024 * 1024),
            ),
            memory_growth_rate=memory_growth_rate,
        )

    def _determine_pressure_level(self, memory_percent: float) -> MemoryPressureLevel:
        """Determine memory pressure level based on usage percentage."""
        if memory_percent >= self.alert_thresholds[MemoryPressureLevel.EMERGENCY]:
            return MemoryPressureLevel.EMERGENCY
        elif memory_percent >= self.alert_thresholds[MemoryPressureLevel.CRITICAL]:
            return MemoryPressureLevel.CRITICAL
        elif memory_percent >= self.alert_thresholds[MemoryPressureLevel.HIGH]:
            return MemoryPressureLevel.HIGH
        elif memory_percent >= self.alert_thresholds[MemoryPressureLevel.MODERATE]:
            return MemoryPressureLevel.MODERATE
        else:
            return MemoryPressureLevel.LOW

    async def _check_pressure_levels(self, metrics: MemoryMetrics):
        """Check memory pressure and trigger alerts."""
        if metrics.pressure_level != MemoryPressureLevel.LOW:
            for callback in self._alert_callbacks:
                try:
                    await asyncio.get_event_loop().run_in_executor(None, callback, metrics)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")

    async def _auto_gc(self, metrics: MemoryMetrics):
        """Perform automatic garbage collection when needed."""
        import time

        current_time = time.time()

        # Force GC if memory pressure is high or it's been a while
        should_gc = (
            metrics.pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]
            or (current_time - self._last_gc_time) > 60.0  # Force GC every minute
        )

        if should_gc:
            await asyncio.get_event_loop().run_in_executor(None, gc.collect)
            self._last_gc_time = current_time
            self.logger.debug(
                f"Garbage collection triggered - pressure level: {metrics.pressure_level}"
            )

    def get_metrics_history(self, count: int = 100) -> List[MemoryMetrics]:
        """Get recent memory metrics history."""
        return list(self._metrics_history)[-count:]

    def get_current_metrics(self) -> MemoryMetrics:
        """Get current memory metrics."""
        return self._collect_metrics()


class MemoryCircuitBreaker:
    """Circuit breaker for memory-intensive operations."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        memory_threshold_percent: float = 85.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.memory_threshold_percent = memory_threshold_percent

        self._failure_count = 0
        self._last_failure_time = 0
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

        self.logger = logging.getLogger(__name__)

    @contextmanager
    def protect(self, operation_name: str = "memory_operation"):
        """Context manager for protecting memory-intensive operations."""

        # Check circuit breaker state
        if self._state == "OPEN":
            if self._should_attempt_reset():
                self._state = "HALF_OPEN"
                self.logger.info(f"Circuit breaker entering HALF_OPEN state for {operation_name}")
            else:
                raise MemoryError(f"Circuit breaker OPEN for {operation_name}")

        # Check current memory before operation
        memory = psutil.virtual_memory()
        if memory.percent > self.memory_threshold_percent:
            self._record_failure(operation_name)
            raise MemoryError(f"Memory threshold exceeded: {memory.percent}%")

        try:
            yield

            # Operation succeeded
            if self._state == "HALF_OPEN":
                self._reset()
                self.logger.info(f"Circuit breaker reset to CLOSED for {operation_name}")

        except (MemoryError, Exception):
            self._record_failure(operation_name)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        import time

        return (time.time() - self._last_failure_time) > self.recovery_timeout

    def _record_failure(self, operation_name: str):
        """Record a failure and potentially open the circuit."""
        import time

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "OPEN"
            self.logger.warning(
                f"Circuit breaker OPENED for {operation_name} after {self._failure_count} failures"
            )

    def _reset(self):
        """Reset the circuit breaker."""
        self._failure_count = 0
        self._last_failure_time = 0
        self._state = "CLOSED"

    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        return self._state


class MemoryProfiling:
    """Memory profiling utilities for performance analysis."""

    def __init__(self, enable_tracemalloc: bool = True):
        self.enable_tracemalloc = enable_tracemalloc
        self._profiling_active = False
        self._snapshots = []

        if enable_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start()

    @contextmanager
    def profile(self, operation_name: str):
        """Context manager for profiling memory usage of an operation."""

        # Take snapshot before operation
        if self.enable_tracemalloc:
            snapshot_before = tracemalloc.take_snapshot()
        else:
            snapshot_before = None

        memory_before = psutil.Process().memory_info()

        try:
            yield
        finally:
            # Take snapshot after operation
            if self.enable_tracemalloc:
                snapshot_after = tracemalloc.take_snapshot()

                # Calculate top differences
                top_stats = snapshot_after.compare_to(snapshot_before, "lineno")

                logging.getLogger(__name__).info(
                    f"Memory profile for {operation_name}:\n"
                    + "\n".join(str(stat) for stat in top_stats[:10])
                )

            memory_after = psutil.Process().memory_info()
            memory_diff = (memory_after.rss - memory_before.rss) / (1024 * 1024)

            logging.getLogger(__name__).info(
                f"Memory usage change for {operation_name}: {memory_diff:.2f} MB"
            )

    def get_top_memory_consumers(self, count: int = 10) -> List[str]:
        """Get top memory consumers by line."""
        if not self.enable_tracemalloc:
            return []

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")

        return [str(stat) for stat in top_stats[:count]]


# Global instances
memory_monitor = MemoryMonitor()
memory_circuit_breaker = MemoryCircuitBreaker()
memory_profiler = MemoryProfiling()


def memory_efficient(max_memory_mb: float = 500.0, enable_profiling: bool = False):
    """Decorator for memory-efficient function execution."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):

            operation_name = f"{func.__name__}"

            # Use circuit breaker protection
            with memory_circuit_breaker.protect(operation_name):

                # Use profiling if enabled
                if enable_profiling:
                    with memory_profiler.profile(operation_name):
                        return await func(*args, **kwargs)
                else:
                    return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):

            operation_name = f"{func.__name__}"

            # Use circuit breaker protection
            with memory_circuit_breaker.protect(operation_name):

                # Use profiling if enabled
                if enable_profiling:
                    with memory_profiler.profile(operation_name):
                        return func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Convenience functions
async def start_memory_monitoring():
    """Start global memory monitoring."""
    await memory_monitor.start_monitoring()


async def stop_memory_monitoring():
    """Stop global memory monitoring."""
    await memory_monitor.stop_monitoring()


def get_memory_stats() -> Dict[str, Any]:
    """Get comprehensive memory statistics."""
    current_metrics = memory_monitor.get_current_metrics()

    return {
        "current_metrics": {
            "memory_percent": current_metrics.memory_percent,
            "process_memory_mb": current_metrics.process_memory_mb,
            "available_memory_mb": current_metrics.available_memory_mb,
            "pressure_level": current_metrics.pressure_level.value,
        },
        "circuit_breaker_state": memory_circuit_breaker.state,
        "gc_stats": current_metrics.gc_collections,
        "top_objects": dict(list(current_metrics.object_counts.items())[:10]),
        "memory_growth_rate_mb_per_sec": current_metrics.memory_growth_rate,
    }


def force_garbage_collection():
    """Force garbage collection to free memory."""
    collected = gc.collect()
    logging.getLogger(__name__).info(f"Garbage collection freed {collected} objects")
    return collected
