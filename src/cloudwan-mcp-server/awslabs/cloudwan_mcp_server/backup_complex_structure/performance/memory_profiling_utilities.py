"""
Memory Profiling Utilities for CloudWAN MCP System.

This module provides comprehensive memory profiling tools designed specifically
for large-scale network topology processing with enterprise-grade analysis capabilities.
"""

import asyncio
import gc
import logging
import tracemalloc
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from contextlib import contextmanager, asynccontextmanager
from collections import defaultdict, deque
import threading

# Memory analysis tools
try:
    import psutil
    import objgraph

    ADVANCED_PROFILING = True
except ImportError:
    ADVANCED_PROFILING = False

# Memory optimization integration
from .memory_optimization import (
    MemoryMonitor,
    MemoryProfiler,
    get_memory_usage,
    format_memory_size,
)

# Streaming topology integration
from .streaming_topology_manager import StreamingTopologyManager, StreamingChunk

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Comprehensive memory snapshot for analysis."""

    __slots__ = (
        "timestamp",
        "total_memory",
        "current_memory",
        "peak_memory",
        "memory_blocks",
        "top_allocations",
        "object_counts",
        "gc_stats",
        "stack_trace",
        "component_memory",
        "memory_growth",
    )

    timestamp: datetime
    total_memory: int
    current_memory: int
    peak_memory: int
    memory_blocks: int
    top_allocations: List[Dict[str, Any]]
    object_counts: Dict[str, int]
    gc_stats: Dict[str, Any]
    stack_trace: Optional[List[str]] = None
    component_memory: Dict[str, int] = field(default_factory=dict)
    memory_growth: Optional[int] = None


@dataclass
class MemoryProfileResult:
    """Result of memory profiling analysis."""

    __slots__ = (
        "function_name",
        "total_time",
        "memory_peak",
        "memory_growth",
        "allocations",
        "deallocations",
        "snapshots",
        "bottlenecks",
        "recommendations",
        "efficiency_score",
    )

    function_name: str
    total_time: float
    memory_peak: int
    memory_growth: int
    allocations: int
    deallocations: int
    snapshots: List[MemorySnapshot]
    bottlenecks: List[str]
    recommendations: List[str]
    efficiency_score: float


class MemoryProfiler:
    """Advanced memory profiler for topology processing."""

    def __init__(
        self,
        snapshot_interval: float = 0.1,
        max_snapshots: int = 1000,
        track_components: bool = True,
    ):
        self.snapshot_interval = snapshot_interval
        self.max_snapshots = max_snapshots
        self.track_components = track_components

        # Profiling state
        self.active_profiles: Dict[str, Dict[str, Any]] = {}
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self.component_trackers: Dict[str, Callable[[], int]] = {}
        self.baseline_memory: Optional[int] = None

        # Thread-local storage for profiling context
        self.local_storage = threading.local()

        # Memory tracking
        self.memory_monitor = MemoryMonitor()

        self.logger = logging.getLogger(__name__)

        # Initialize tracemalloc if not already started
        if not tracemalloc.is_tracing():
            tracemalloc.start()

    def register_component_tracker(self, name: str, tracker: Callable[[], int]):
        """Register a component memory tracker."""
        self.component_trackers[name] = tracker
        self.logger.debug(f"Registered component tracker: {name}")

    def take_snapshot(self, label: str = None) -> MemorySnapshot:
        """Take a comprehensive memory snapshot."""
        timestamp = datetime.now()

        # Get tracemalloc snapshot
        snapshot = tracemalloc.take_snapshot()

        # Current memory usage
        current_memory = tracemalloc.get_traced_memory()[0]
        peak_memory = tracemalloc.get_traced_memory()[1]

        # Memory blocks
        memory_blocks = len(snapshot.traces)

        # Top allocations
        top_stats = snapshot.statistics("lineno")[:10]
        top_allocations = []
        for stat in top_stats:
            top_allocations.append(
                {
                    "filename": (stat.traceback.format()[0] if stat.traceback else "unknown"),
                    "size": stat.size,
                    "count": stat.count,
                    "size_mb": stat.size / (1024 * 1024),
                }
            )

        # Object counts
        object_counts = {}
        if ADVANCED_PROFILING:
            object_counts = objgraph.typestats()
        else:
            # Basic object counting
            all_objects = gc.get_objects()
            type_counts = defaultdict(int)
            for obj in all_objects:
                type_counts[type(obj).__name__] += 1
            object_counts = dict(type_counts)

        # GC statistics
        gc_stats = {
            "collections": gc.get_stats(),
            "garbage_count": len(gc.garbage) if hasattr(gc, "garbage") else 0,
            "object_count": len(gc.get_objects()),
        }

        # Component memory
        component_memory = {}
        for name, tracker in self.component_trackers.items():
            try:
                component_memory[name] = tracker()
            except Exception as e:
                self.logger.warning(f"Error getting memory for component {name}: {e}")
                component_memory[name] = 0

        # Memory growth calculation
        memory_growth = None
        if self.baseline_memory is not None:
            memory_growth = current_memory - self.baseline_memory

        snapshot_obj = MemorySnapshot(
            timestamp=timestamp,
            total_memory=get_memory_usage(),
            current_memory=current_memory,
            peak_memory=peak_memory,
            memory_blocks=memory_blocks,
            top_allocations=top_allocations,
            object_counts=object_counts,
            gc_stats=gc_stats,
            component_memory=component_memory,
            memory_growth=memory_growth,
        )

        self.snapshots.append(snapshot_obj)

        if label:
            self.logger.info(f"Memory snapshot '{label}': {format_memory_size(current_memory)}")

        return snapshot_obj

    @contextmanager
    def profile(
        self,
        function_name: str,
        continuous_snapshots: bool = True,
        gc_collect: bool = True,
    ):
        """Context manager for profiling memory usage."""
        if gc_collect:
            gc.collect()

        # Set baseline
        self.baseline_memory = tracemalloc.get_traced_memory()[0]

        # Store profiling context
        profile_data = {
            "function_name": function_name,
            "start_time": time.time(),
            "start_memory": self.baseline_memory,
            "snapshots": [],
            "peak_memory": 0,
            "continuous_snapshots": continuous_snapshots,
        }

        self.active_profiles[function_name] = profile_data

        # Take initial snapshot
        initial_snapshot = self.take_snapshot(f"{function_name}_start")
        profile_data["snapshots"].append(initial_snapshot)

        # Start continuous snapshots if requested
        snapshot_thread = None
        if continuous_snapshots:
            snapshot_thread = threading.Thread(
                target=self._continuous_snapshot_loop,
                args=(function_name,),
                daemon=True,
            )
            snapshot_thread.start()

        try:
            yield self
        finally:
            # Stop continuous snapshots
            if continuous_snapshots and function_name in self.active_profiles:
                self.active_profiles[function_name]["stop_snapshots"] = True
                if snapshot_thread and snapshot_thread.is_alive():
                    snapshot_thread.join(timeout=1)

            # Take final snapshot
            final_snapshot = self.take_snapshot(f"{function_name}_end")

            # Calculate results
            if function_name in self.active_profiles:
                profile_data = self.active_profiles[function_name]
                profile_data["snapshots"].append(final_snapshot)
                profile_data["end_time"] = time.time()
                profile_data["end_memory"] = final_snapshot.current_memory
                profile_data["peak_memory"] = final_snapshot.peak_memory

                # Generate profile result
                result = self._generate_profile_result(profile_data)

                # Log summary
                self.logger.info(
                    f"Memory profile '{function_name}': "
                    f"Peak: {format_memory_size(result.memory_peak)}, "
                    f"Growth: {format_memory_size(result.memory_growth)}, "
                    f"Efficiency: {result.efficiency_score:.2f}"
                )

                # Clean up
                del self.active_profiles[function_name]

            if gc_collect:
                gc.collect()

    def _continuous_snapshot_loop(self, function_name: str):
        """Continuous snapshot loop for profiling."""
        while function_name in self.active_profiles:
            profile_data = self.active_profiles[function_name]

            if profile_data.get("stop_snapshots", False):
                break

            try:
                snapshot = self.take_snapshot()
                profile_data["snapshots"].append(snapshot)

                # Update peak memory
                if snapshot.current_memory > profile_data["peak_memory"]:
                    profile_data["peak_memory"] = snapshot.current_memory

                time.sleep(self.snapshot_interval)

            except Exception as e:
                self.logger.warning(f"Error in continuous snapshot loop: {e}")
                break

    def _generate_profile_result(self, profile_data: Dict[str, Any]) -> MemoryProfileResult:
        """Generate comprehensive profile result."""
        function_name = profile_data["function_name"]
        total_time = profile_data["end_time"] - profile_data["start_time"]
        memory_peak = profile_data["peak_memory"]
        memory_growth = profile_data["end_memory"] - profile_data["start_memory"]
        snapshots = profile_data["snapshots"]

        # Calculate allocations and deallocations
        allocations = 0
        deallocations = 0

        for i in range(1, len(snapshots)):
            prev_snapshot = snapshots[i - 1]
            curr_snapshot = snapshots[i]

            memory_diff = curr_snapshot.current_memory - prev_snapshot.current_memory
            if memory_diff > 0:
                allocations += memory_diff
            else:
                deallocations += abs(memory_diff)

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(snapshots)

        # Generate recommendations
        recommendations = self._generate_recommendations(snapshots, memory_peak, memory_growth)

        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score(memory_peak, memory_growth, total_time)

        return MemoryProfileResult(
            function_name=function_name,
            total_time=total_time,
            memory_peak=memory_peak,
            memory_growth=memory_growth,
            allocations=allocations,
            deallocations=deallocations,
            snapshots=snapshots,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            efficiency_score=efficiency_score,
        )

    def _identify_bottlenecks(self, snapshots: List[MemorySnapshot]) -> List[str]:
        """Identify memory bottlenecks from snapshots."""
        bottlenecks = []

        if len(snapshots) < 2:
            return bottlenecks

        # Check for memory leaks
        memory_trend = []
        for snapshot in snapshots:
            memory_trend.append(snapshot.current_memory)

        # Simple trend analysis
        if len(memory_trend) >= 3:
            start_avg = sum(memory_trend[:3]) / 3
            end_avg = sum(memory_trend[-3:]) / 3

            if end_avg > start_avg * 1.5:
                bottlenecks.append("Potential memory leak detected")

        # Check for excessive allocations
        max_allocations = 0
        for snapshot in snapshots:
            for alloc in snapshot.top_allocations:
                if alloc["size"] > max_allocations:
                    max_allocations = alloc["size"]

        if max_allocations > 100 * 1024 * 1024:  # 100MB
            bottlenecks.append("Large single allocation detected")

        # Check for GC pressure
        for snapshot in snapshots:
            if snapshot.gc_stats.get("garbage_count", 0) > 1000:
                bottlenecks.append("High garbage collection pressure")
                break

        return bottlenecks

    def _generate_recommendations(
        self, snapshots: List[MemorySnapshot], memory_peak: int, memory_growth: int
    ) -> List[str]:
        """Generate memory optimization recommendations."""
        recommendations = []

        # Memory growth recommendations
        if memory_growth > 50 * 1024 * 1024:  # 50MB
            recommendations.append("Consider using memory pooling for large objects")

        # Peak memory recommendations
        if memory_peak > 1024 * 1024 * 1024:  # 1GB
            recommendations.append("Consider streaming processing for large datasets")

        # Object count recommendations
        if snapshots:
            latest_snapshot = snapshots[-1]

            # Check for excessive object creation
            for obj_type, count in latest_snapshot.object_counts.items():
                if count > 100000:  # 100K objects
                    recommendations.append(
                        f"High {obj_type} object count - consider object pooling"
                    )

        # GC recommendations
        if snapshots:
            gc_collections = sum(
                sum(gen["collections"] for gen in snapshot.gc_stats.get("collections", []))
                for snapshot in snapshots
            )

            if gc_collections > 100:
                recommendations.append("Frequent GC collections - consider larger object lifetimes")

        return recommendations

    def _calculate_efficiency_score(
        self, memory_peak: int, memory_growth: int, total_time: float
    ) -> float:
        """Calculate memory efficiency score (0-1)."""
        # Base score
        score = 1.0

        # Penalize high peak memory
        if memory_peak > 100 * 1024 * 1024:  # 100MB
            score -= 0.2

        if memory_peak > 500 * 1024 * 1024:  # 500MB
            score -= 0.3

        # Penalize memory growth
        if memory_growth > 10 * 1024 * 1024:  # 10MB
            score -= 0.2

        if memory_growth > 50 * 1024 * 1024:  # 50MB
            score -= 0.3

        # Penalize slow execution
        if total_time > 10.0:  # 10 seconds
            score -= 0.1

        return max(0.0, score)

    def compare_snapshots(
        self, snapshot1: MemorySnapshot, snapshot2: MemorySnapshot
    ) -> Dict[str, Any]:
        """Compare two memory snapshots."""
        return {
            "time_diff": (snapshot2.timestamp - snapshot1.timestamp).total_seconds(),
            "memory_diff": snapshot2.current_memory - snapshot1.current_memory,
            "peak_diff": snapshot2.peak_memory - snapshot1.peak_memory,
            "blocks_diff": snapshot2.memory_blocks - snapshot1.memory_blocks,
            "object_diffs": {
                obj_type: snapshot2.object_counts.get(obj_type, 0)
                - snapshot1.object_counts.get(obj_type, 0)
                for obj_type in set(snapshot1.object_counts.keys())
                | set(snapshot2.object_counts.keys())
            },
            "component_diffs": {
                component: snapshot2.component_memory.get(component, 0)
                - snapshot1.component_memory.get(component, 0)
                for component in set(snapshot1.component_memory.keys())
                | set(snapshot2.component_memory.keys())
            },
        }

    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report."""
        if not self.snapshots:
            return {}

        latest_snapshot = self.snapshots[-1]

        return {
            "current_memory": {
                "total": latest_snapshot.total_memory,
                "current": latest_snapshot.current_memory,
                "peak": latest_snapshot.peak_memory,
                "blocks": latest_snapshot.memory_blocks,
            },
            "top_allocations": latest_snapshot.top_allocations[:5],
            "object_counts": dict(list(latest_snapshot.object_counts.items())[:10]),
            "component_memory": latest_snapshot.component_memory,
            "gc_stats": latest_snapshot.gc_stats,
            "snapshot_count": len(self.snapshots),
            "profiling_active": len(self.active_profiles) > 0,
        }


class TopologyMemoryProfiler:
    """Specialized memory profiler for topology processing."""

    def __init__(self, streaming_manager: StreamingTopologyManager):
        self.streaming_manager = streaming_manager
        self.base_profiler = MemoryProfiler()
        self.topology_snapshots: Dict[str, List[MemorySnapshot]] = {}

        # Register topology-specific trackers
        self.base_profiler.register_component_tracker("topology_chunks", self._get_chunk_memory)

        self.base_profiler.register_component_tracker("topology_cache", self._get_cache_memory)

        self.logger = logging.getLogger(__name__)

    def _get_chunk_memory(self) -> int:
        """Get memory usage of topology chunks."""
        # This would integrate with actual chunk memory tracking
        return 0  # Placeholder

    def _get_cache_memory(self) -> int:
        """Get memory usage of topology cache."""
        # This would integrate with actual cache memory tracking
        return 0  # Placeholder

    @asynccontextmanager
    async def profile_topology_processing(self, topology_id: str):
        """Profile topology processing with streaming support."""
        with self.base_profiler.profile(f"topology_{topology_id}"):
            try:
                yield self
            finally:
                # Store topology-specific snapshots
                if f"topology_{topology_id}" in self.base_profiler.active_profiles:
                    profile_data = self.base_profiler.active_profiles[f"topology_{topology_id}"]
                    self.topology_snapshots[topology_id] = profile_data["snapshots"]

    def profile_chunk_processing(self, chunk: StreamingChunk) -> MemorySnapshot:
        """Profile individual chunk processing."""
        with self.base_profiler.profile(f"chunk_{chunk.chunk_id}", continuous_snapshots=False):
            # Process chunk (this would be actual chunk processing)
            time.sleep(0.1)  # Simulate processing

            return self.base_profiler.take_snapshot(f"chunk_{chunk.chunk_id}")

    def get_topology_memory_analysis(self, topology_id: str) -> Dict[str, Any]:
        """Get detailed memory analysis for a topology."""
        if topology_id not in self.topology_snapshots:
            return {}

        snapshots = self.topology_snapshots[topology_id]

        if not snapshots:
            return {}

        # Calculate memory trends
        memory_trend = [s.current_memory for s in snapshots]
        peak_memory = max(memory_trend)
        final_memory = memory_trend[-1]
        initial_memory = memory_trend[0]

        # Calculate efficiency metrics
        memory_efficiency = (
            1.0 - (peak_memory - initial_memory) / peak_memory if peak_memory > 0 else 1.0
        )

        return {
            "topology_id": topology_id,
            "snapshot_count": len(snapshots),
            "memory_trend": memory_trend,
            "peak_memory": peak_memory,
            "final_memory": final_memory,
            "memory_growth": final_memory - initial_memory,
            "memory_efficiency": memory_efficiency,
            "processing_time": (snapshots[-1].timestamp - snapshots[0].timestamp).total_seconds(),
            "avg_memory": sum(memory_trend) / len(memory_trend),
        }


class MemoryLeakDetector:
    """Detect and analyze memory leaks in topology processing."""

    def __init__(self, check_interval: float = 30.0, growth_threshold: float = 0.1):  # 10% growth
        self.check_interval = check_interval
        self.growth_threshold = growth_threshold
        self.memory_history: deque = deque(maxlen=100)
        self.leak_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.checking = False
        self.check_task: Optional[asyncio.Task] = None

        self.logger = logging.getLogger(__name__)

    def add_leak_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for leak detection."""
        self.leak_callbacks.append(callback)

    async def start_detection(self):
        """Start leak detection monitoring."""
        if self.checking:
            return

        self.checking = True
        self.check_task = asyncio.create_task(self._detection_loop())
        self.logger.info("Memory leak detection started")

    async def stop_detection(self):
        """Stop leak detection monitoring."""
        if not self.checking:
            return

        self.checking = False

        if self.check_task and not self.check_task.done():
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Memory leak detection stopped")

    async def _detection_loop(self):
        """Main leak detection loop."""
        while self.checking:
            try:
                current_memory = get_memory_usage()
                self.memory_history.append((datetime.now(), current_memory))

                # Check for leaks
                leak_info = self._analyze_for_leaks()
                if leak_info:
                    # Notify callbacks
                    for callback in self.leak_callbacks:
                        try:
                            callback(leak_info)
                        except Exception as e:
                            self.logger.error(f"Error in leak callback: {e}")

                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in leak detection loop: {e}")
                await asyncio.sleep(self.check_interval)

    def _analyze_for_leaks(self) -> Optional[Dict[str, Any]]:
        """Analyze memory history for potential leaks."""
        if len(self.memory_history) < 5:
            return None

        # Get recent memory values
        recent_memory = [mem for _, mem in list(self.memory_history)[-5:]]

        # Check for consistent growth
        growth_count = 0
        for i in range(1, len(recent_memory)):
            if recent_memory[i] > recent_memory[i - 1]:
                growth_count += 1

        # If most recent measurements show growth
        if growth_count >= 3:
            first_memory = recent_memory[0]
            last_memory = recent_memory[-1]
            growth_rate = (last_memory - first_memory) / first_memory

            if growth_rate > self.growth_threshold:
                return {
                    "type": "memory_leak_detected",
                    "growth_rate": growth_rate,
                    "memory_start": first_memory,
                    "memory_end": last_memory,
                    "samples": len(recent_memory),
                    "timestamp": datetime.now(),
                }

        return None

    def get_memory_trend(self) -> List[Dict[str, Any]]:
        """Get memory trend data."""
        return [
            {"timestamp": timestamp.isoformat(), "memory_mb": memory / (1024 * 1024)}
            for timestamp, memory in self.memory_history
        ]


# Factory functions for easy creation
def create_memory_profiler(**kwargs) -> MemoryProfiler:
    """Create a memory profiler instance."""
    return MemoryProfiler(**kwargs)


def create_topology_profiler(
    streaming_manager: StreamingTopologyManager,
) -> TopologyMemoryProfiler:
    """Create a topology memory profiler."""
    return TopologyMemoryProfiler(streaming_manager)


def create_leak_detector(**kwargs) -> MemoryLeakDetector:
    """Create a memory leak detector."""
    return MemoryLeakDetector(**kwargs)


# Example usage and testing
if __name__ == "__main__":

    async def main():
        # Create profiler
        profiler = create_memory_profiler()

        # Example profiling
        with profiler.profile("example_function"):
            # Simulate some memory-intensive work
            data = [i for i in range(100000)]
            data2 = {i: str(i) for i in range(10000)}

            # Take intermediate snapshot
            snapshot = profiler.take_snapshot("intermediate")

            # More work
            data3 = [data, data2] * 100

        # Get memory report
        report = profiler.get_memory_report()
        print(f"Memory report: {report}")

        # Test leak detector
        leak_detector = create_leak_detector(check_interval=1.0)

        def leak_callback(leak_info):
            print(f"Leak detected: {leak_info}")

        leak_detector.add_leak_callback(leak_callback)

        await leak_detector.start_detection()
        await asyncio.sleep(5)
        await leak_detector.stop_detection()

    asyncio.run(main())
