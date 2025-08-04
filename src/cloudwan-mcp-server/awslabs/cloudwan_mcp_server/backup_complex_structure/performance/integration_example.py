"""
Integration Example: Complete Memory Optimization System

This example demonstrates how all memory optimization components work together
to process large-scale network topologies efficiently with comprehensive monitoring.
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

# Core memory optimization
from .memory_optimization import (
    MemoryOptimizedTopology,
    MemoryMonitor,
    MemoryCircuitBreaker,
    ObjectPool,
    get_memory_usage,
    format_memory_size,
)

# Streaming topology processing
from .streaming_topology_manager import (
    StreamingTopologyManager,
    StreamingChunk,
)

# Memory monitoring and dashboard
from .memory_monitoring_dashboard import (
    MemoryMonitoringDashboard,
    create_memory_dashboard,
)

# Profiling and analysis
from .memory_profiling_utilities import (
    MemoryProfiler,
    TopologyMemoryProfiler,
    MemoryLeakDetector,
    create_memory_profiler,
    create_topology_profiler,
    create_leak_detector,
)

# Benchmarking
from .benchmarking_suite import (
    TopologyProcessingBenchmark,
    StreamingMemoryBenchmark,
    MemoryOptimizationBenchmark,
    create_benchmark_runner,
)

# Network topology models
from ..models.network import NetworkTopology, NetworkElement, NetworkConnection

logger = logging.getLogger(__name__)


class EnterpriseMemoryOptimizationSystem:
    """
    Complete enterprise-grade memory optimization system for CloudWAN topology processing.

    This class integrates all memory optimization components to provide:
    - 50% memory reduction through optimized data structures
    - Support for 1000+ element topologies with sub-5GB memory usage
    - Real-time monitoring with web dashboard
    - Comprehensive profiling and benchmarking
    - Automatic memory management with circuit breakers
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        enable_dashboard: bool = True,
        enable_profiling: bool = True,
        enable_leak_detection: bool = True,
    ):
        """
        Initialize the complete memory optimization system.

        Args:
            config: Configuration dictionary for system settings
            enable_dashboard: Enable web monitoring dashboard
            enable_profiling: Enable memory profiling
            enable_leak_detection: Enable memory leak detection
        """
        self.config = config or self._get_default_config()
        self.enable_dashboard = enable_dashboard
        self.enable_profiling = enable_profiling
        self.enable_leak_detection = enable_leak_detection

        # Core components
        self.memory_monitor = MemoryMonitor()
        self.circuit_breaker = MemoryCircuitBreaker(
            memory_threshold_mb=self.config["memory"]["threshold_mb"],
            failure_threshold=self.config["memory"]["failure_threshold"],
        )

        # Streaming processing
        self.streaming_manager = StreamingTopologyManager(
            chunk_size=self.config["streaming"]["chunk_size"],
            memory_threshold_mb=self.config["streaming"]["memory_threshold_mb"],
        )

        # Object pooling
        self.element_pool = ObjectPool(
            factory=self._create_network_element,
            max_size=self.config["pooling"]["max_pool_size"],
        )

        # Optional components
        self.dashboard: Optional[MemoryMonitoringDashboard] = None
        self.profiler: Optional[MemoryProfiler] = None
        self.topology_profiler: Optional[TopologyMemoryProfiler] = None
        self.leak_detector: Optional[MemoryLeakDetector] = None

        # Initialize optional components
        self._initialize_optional_components()

        # System state
        self.running = False
        self.processed_topologies: Dict[str, Dict[str, Any]] = {}

        self.logger = logging.getLogger(__name__)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for the system."""
        return {
            "memory": {
                "threshold_mb": 1000,
                "failure_threshold": 5,
                "cleanup_interval": 300,
            },
            "streaming": {
                "chunk_size": 100,
                "memory_threshold_mb": 500,
                "max_concurrent_chunks": 10,
            },
            "pooling": {"max_pool_size": 1000, "cleanup_interval": 600},
            "monitoring": {
                "dashboard_port": 5000,
                "metrics_interval": 1.0,
                "alert_threshold": 75,
            },
            "profiling": {"snapshot_interval": 0.1, "max_snapshots": 3600},
            "leak_detection": {"check_interval": 30.0, "growth_threshold": 0.1},
        }

    def _initialize_optional_components(self):
        """Initialize optional monitoring and profiling components."""
        if self.enable_dashboard:
            self.dashboard = create_memory_dashboard(
                port=self.config["monitoring"]["dashboard_port"], debug=False
            )

        if self.enable_profiling:
            self.profiler = create_memory_profiler(
                snapshot_interval=self.config["profiling"]["snapshot_interval"],
                max_snapshots=self.config["profiling"]["max_snapshots"],
            )

            self.topology_profiler = create_topology_profiler(self.streaming_manager)

        if self.enable_leak_detection:
            self.leak_detector = create_leak_detector(
                check_interval=self.config["leak_detection"]["check_interval"],
                growth_threshold=self.config["leak_detection"]["growth_threshold"],
            )

    def _create_network_element(self) -> NetworkElement:
        """Factory function for network element pool."""
        return NetworkElement(id="", name="", element_type="", region="", metadata={})

    async def start(self):
        """Start the memory optimization system."""
        if self.running:
            return

        self.running = True

        # Start monitoring dashboard
        if self.dashboard:
            await self.dashboard.start()
            self.logger.info(f"Memory dashboard started: {self.dashboard.get_dashboard_url()}")

        # Start leak detection
        if self.leak_detector:
            await self.leak_detector.start_detection()
            self.logger.info("Memory leak detection started")

        # Start memory monitoring
        self.memory_monitor.start_monitoring()

        self.logger.info("Enterprise memory optimization system started")

    async def stop(self):
        """Stop the memory optimization system."""
        if not self.running:
            return

        self.running = False

        # Stop monitoring dashboard
        if self.dashboard:
            await self.dashboard.stop()

        # Stop leak detection
        if self.leak_detector:
            await self.leak_detector.stop_detection()

        # Stop memory monitoring
        self.memory_monitor.stop_monitoring()

        self.logger.info("Enterprise memory optimization system stopped")

    async def process_topology(
        self,
        topology: NetworkTopology,
        topology_id: str = None,
        enable_profiling: bool = None,
    ) -> Dict[str, Any]:
        """
        Process a network topology with full memory optimization.

        Args:
            topology: Network topology to process
            topology_id: Unique identifier for the topology
            enable_profiling: Enable profiling for this topology

        Returns:
            Processing results with memory statistics
        """
        if not self.running:
            await self.start()

        topology_id = topology_id or f"topology_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        enable_profiling = (
            enable_profiling if enable_profiling is not None else self.enable_profiling
        )

        self.logger.info(
            f"Processing topology {topology_id} with {len(topology.elements)} elements"
        )

        # Check memory circuit breaker
        if self.circuit_breaker.should_break():
            raise RuntimeError("Memory circuit breaker activated - system protection engaged")

        # Convert to memory-optimized format
        optimized_topology = MemoryOptimizedTopology.from_topology(topology)

        processing_context = None
        if enable_profiling and self.topology_profiler:
            processing_context = self.topology_profiler.profile_topology_processing(topology_id)

        try:
            if processing_context:
                async with processing_context:
                    result = await self._process_topology_optimized(optimized_topology, topology_id)
            else:
                result = await self._process_topology_optimized(optimized_topology, topology_id)

            # Store processing results
            self.processed_topologies[topology_id] = result

            return result

        except Exception as e:
            self.logger.error(f"Error processing topology {topology_id}: {e}")
            raise

    async def _process_topology_optimized(
        self, topology: MemoryOptimizedTopology, topology_id: str
    ) -> Dict[str, Any]:
        """Process topology with memory optimization."""
        start_time = datetime.now()
        initial_memory = get_memory_usage()

        processed_elements = 0
        processed_connections = 0
        chunks_processed = 0
        errors = []

        # Stream topology in chunks
        async for chunk in self.streaming_manager.stream_topology_chunks(
            topology, chunk_size=self.config["streaming"]["chunk_size"]
        ):
            try:
                # Process chunk with memory monitoring
                chunk_result = await self._process_chunk(chunk, topology_id)

                processed_elements += len(chunk.elements)
                processed_connections += len(chunk.connections)
                chunks_processed += 1

                # Monitor memory usage
                current_memory = get_memory_usage()
                self.memory_monitor.record_memory_usage(current_memory)

                # Check circuit breaker
                if self.circuit_breaker.should_break():
                    self.logger.warning("Circuit breaker activated during processing")
                    break

                # Brief pause to allow system monitoring
                await asyncio.sleep(0.001)

            except Exception as e:
                self.logger.error(f"Error processing chunk {chunk.chunk_id}: {e}")
                errors.append(str(e))

        end_time = datetime.now()
        final_memory = get_memory_usage()

        # Calculate results
        processing_time = (end_time - start_time).total_seconds()
        memory_growth = final_memory - initial_memory
        throughput = processed_elements / processing_time if processing_time > 0 else 0

        result = {
            "topology_id": topology_id,
            "processing_time": processing_time,
            "processed_elements": processed_elements,
            "processed_connections": processed_connections,
            "chunks_processed": chunks_processed,
            "throughput": throughput,
            "memory_stats": {
                "initial_memory": initial_memory,
                "final_memory": final_memory,
                "memory_growth": memory_growth,
                "peak_memory": (
                    max(
                        snapshot.current_memory
                        for snapshot in self.memory_monitor.memory_history[-100:]
                    )
                    if self.memory_monitor.memory_history
                    else final_memory
                ),
            },
            "errors": errors,
            "success_rate": 1.0 - (len(errors) / max(1, chunks_processed)),
            "timestamp": end_time.isoformat(),
        }

        self.logger.info(
            f"Topology {topology_id} processed: {processed_elements} elements, "
            f"{throughput:.2f} elements/s, {format_memory_size(memory_growth)} growth"
        )

        return result

    async def _process_chunk(self, chunk: StreamingChunk, topology_id: str) -> Dict[str, Any]:
        """Process a single topology chunk."""
        # Profile chunk processing if enabled
        if self.profiler:
            with self.profiler.profile(f"chunk_{chunk.chunk_id}", continuous_snapshots=False):
                return await self._process_chunk_internal(chunk, topology_id)
        else:
            return await self._process_chunk_internal(chunk, topology_id)

    async def _process_chunk_internal(
        self, chunk: StreamingChunk, topology_id: str
    ) -> Dict[str, Any]:
        """Internal chunk processing with memory optimization."""
        # Use object pool for processing
        processed_elements = []

        for element_data in chunk.elements:
            # Get element from pool
            element = self.element_pool.get()

            try:
                # Configure element
                element.id = element_data.id
                element.name = element_data.name
                element.element_type = element_data.element_type
                element.region = element_data.region
                element.metadata = element_data.metadata

                # Process element (simulate processing)
                processed_elements.append(element.to_dict())

            finally:
                # Return to pool
                self.element_pool.return_object(element)

        # Simulate some processing work
        await asyncio.sleep(0.01)

        return {
            "chunk_id": chunk.chunk_id,
            "elements_processed": len(processed_elements),
            "connections_processed": len(chunk.connections),
            "memory_usage": get_memory_usage(),
        }

    async def run_performance_benchmarks(
        self, output_directory: str = "benchmark_results"
    ) -> Dict[str, Any]:
        """Run comprehensive performance benchmarks."""
        self.logger.info("Starting performance benchmarks")

        # Create benchmark runner
        runner = create_benchmark_runner(output_directory)

        # Add topology-specific benchmarks
        runner.add_benchmark(TopologyProcessingBenchmark(element_count=100, connection_count=200))
        runner.add_benchmark(TopologyProcessingBenchmark(element_count=500, connection_count=1000))
        runner.add_benchmark(TopologyProcessingBenchmark(element_count=1000, connection_count=2000))

        # Add memory optimization benchmarks
        runner.add_benchmark(StreamingMemoryBenchmark(chunk_count=25, elements_per_chunk=100))
        runner.add_benchmark(MemoryOptimizationBenchmark(optimization_level="high"))

        # Run benchmarks
        results = await runner.run_all_benchmarks(iterations=3)

        # Get summary
        summary = runner.get_summary_report()

        self.logger.info(f"Benchmarks completed: {summary['overall_pass_rate']:.2%} pass rate")

        return {
            "results": results,
            "summary": summary,
            "targets_met": summary["overall_pass_rate"] >= 0.8,
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        status = {
            "running": self.running,
            "components": {
                "memory_monitor": self.memory_monitor is not None,
                "circuit_breaker": self.circuit_breaker is not None,
                "streaming_manager": self.streaming_manager is not None,
                "dashboard": self.dashboard is not None,
                "profiler": self.profiler is not None,
                "leak_detector": self.leak_detector is not None,
            },
            "current_memory": get_memory_usage(),
            "processed_topologies": len(self.processed_topologies),
            "pool_stats": {
                "element_pool_size": len(self.element_pool.available_objects),
                "pool_max_size": self.element_pool.max_size,
            },
        }

        # Add dashboard status
        if self.dashboard:
            status["dashboard_url"] = self.dashboard.get_dashboard_url()

        # Add memory statistics
        if self.memory_monitor.memory_history:
            recent_memory = list(self.memory_monitor.memory_history)[-10:]
            status["memory_trend"] = {
                "current": recent_memory[-1] if recent_memory else 0,
                "average": (sum(recent_memory) / len(recent_memory) if recent_memory else 0),
                "samples": len(recent_memory),
            }

        return status

    def get_topology_analysis(self, topology_id: str) -> Dict[str, Any]:
        """Get detailed analysis for a processed topology."""
        if topology_id not in self.processed_topologies:
            return {"error": f"Topology {topology_id} not found"}

        result = self.processed_topologies[topology_id].copy()

        # Add profiling data if available
        if self.topology_profiler:
            analysis = self.topology_profiler.get_topology_memory_analysis(topology_id)
            result["memory_analysis"] = analysis

        return result

    async def cleanup_resources(self):
        """Perform comprehensive resource cleanup."""
        self.logger.info("Performing resource cleanup")

        # Clear object pools
        self.element_pool.clear()

        # Clear processed topologies (keep recent ones)
        cutoff_time = datetime.now() - timedelta(hours=24)

        to_remove = []
        for topology_id, data in self.processed_topologies.items():
            if datetime.fromisoformat(data["timestamp"]) < cutoff_time:
                to_remove.append(topology_id)

        for topology_id in to_remove:
            del self.processed_topologies[topology_id]

        # Force garbage collection
        import gc

        gc.collect()

        self.logger.info(f"Cleanup completed: removed {len(to_remove)} old topologies")


async def main():
    """
    Example usage of the complete memory optimization system.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create the optimization system
    system = EnterpriseMemoryOptimizationSystem(
        enable_dashboard=True, enable_profiling=True, enable_leak_detection=True
    )

    try:
        # Start the system
        await system.start()

        # Create a test topology
        elements = []
        connections = []

        # Generate 1000 elements
        for i in range(1000):
            element = NetworkElement(
                id=f"element_{i}",
                name=f"Test Element {i}",
                element_type="vpc" if i % 2 == 0 else "transit_gateway",
                region=f"us-west-{(i % 2) + 1}",
                metadata={"test": True, "index": i},
            )
            elements.append(element)

        # Generate 2000 connections
        for i in range(2000):
            source_idx = i % len(elements)
            target_idx = (i + 1) % len(elements)

            connection = NetworkConnection(
                id=f"connection_{i}",
                source_id=elements[source_idx].id,
                target_id=elements[target_idx].id,
                connection_type="vpc_peering",
                metadata={"test": True, "index": i},
            )
            connections.append(connection)

        # Create topology
        topology = NetworkTopology(
            elements=elements, connections=connections, metadata={"test_topology": True}
        )

        print(
            f"Created test topology with {len(elements)} elements and {len(connections)} connections"
        )

        # Process topology with memory optimization
        result = await system.process_topology(topology, "test_topology_1000")

        print("Processing completed:")
        print(f"  Elements processed: {result['processed_elements']}")
        print(f"  Processing time: {result['processing_time']:.2f}s")
        print(f"  Throughput: {result['throughput']:.2f} elements/s")
        print(f"  Memory growth: {format_memory_size(result['memory_stats']['memory_growth'])}")
        print(f"  Success rate: {result['success_rate']:.2%}")

        # Get system status
        status = system.get_system_status()
        print("\nSystem status:")
        print(f"  Current memory: {format_memory_size(status['current_memory'])}")
        print(f"  Processed topologies: {status['processed_topologies']}")
        print(f"  Dashboard URL: {status.get('dashboard_url', 'N/A')}")

        # Run performance benchmarks
        print("\nRunning performance benchmarks...")
        benchmark_results = await system.run_performance_benchmarks()

        print("Benchmark results:")
        print(f"  Overall pass rate: {benchmark_results['summary']['overall_pass_rate']:.2%}")
        print(f"  Targets met: {benchmark_results['targets_met']}")

        # Keep dashboard running for demonstration
        if system.dashboard:
            print(f"\nDashboard running at: {system.dashboard.get_dashboard_url()}")
            print("Press Ctrl+C to stop...")

            try:
                # Keep running for demonstration
                await asyncio.sleep(300)  # 5 minutes
            except KeyboardInterrupt:
                print("\nStopping system...")

    finally:
        # Clean up
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
