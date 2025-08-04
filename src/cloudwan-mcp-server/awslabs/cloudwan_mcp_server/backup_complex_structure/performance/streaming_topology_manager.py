"""
Streaming Topology Manager for Memory-Efficient Large Network Processing.

This module implements streaming topology discovery and processing to handle
enterprise-scale network topologies (1000+ elements) with minimal memory usage.
"""

import asyncio
import logging
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Iterator,
    AsyncIterator,
    Callable,
)
import gc
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from ..tools.visualization.topology_discovery import (
    NetworkTopology,
    NetworkElement,
    NetworkConnection,
    NetworkElementType,
)
from .memory_optimization import (
    MemoryEfficientNetworkElement,
    MemoryEfficientNetworkConnection,
    MemoryOptimizedTopology,
    MemoryMonitor,
    MemoryCircuitBreaker,
    MemoryPressureLevel,
    memory_efficient,
    get_memory_stats,
)


class StreamingChunkType(Enum):
    """Types of streaming chunks for topology processing."""

    GLOBAL_NETWORKS = "global_networks"
    CORE_NETWORKS = "core_networks"
    TRANSIT_GATEWAYS = "transit_gateways"
    VPCS = "vpcs"
    SEGMENTS = "segments"
    CONNECTIONS = "connections"
    NETWORK_FUNCTIONS = "network_functions"


@dataclass
class StreamingChunk:
    """Represents a chunk of topology data for streaming processing."""

    __slots__ = (
        "chunk_id",
        "chunk_type",
        "elements",
        "connections",
        "metadata",
        "region",
        "priority",
        "processing_time",
        "memory_usage",
    )

    chunk_id: str
    chunk_type: StreamingChunkType
    elements: List[MemoryEfficientNetworkElement] = field(default_factory=list)
    connections: List[MemoryEfficientNetworkConnection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    region: Optional[str] = None
    priority: int = 0
    processing_time: float = 0.0
    memory_usage: int = 0

    def estimate_memory_usage(self) -> int:
        """Estimate memory usage of this chunk in bytes."""
        memory_usage = sys.getsizeof(self)

        # Estimate element memory
        for element in self.elements:
            memory_usage += element.memory_footprint()

        # Estimate connection memory
        for connection in self.connections:
            memory_usage += sys.getsizeof(connection)

        # Estimate metadata memory
        memory_usage += sys.getsizeof(self.metadata)
        for key, value in self.metadata.items():
            memory_usage += sys.getsizeof(key) + sys.getsizeof(value)

        return memory_usage


class StreamingTopologyProcessor:
    """Processes topology data in streaming chunks to minimize memory usage."""

    def __init__(
        self,
        chunk_size: int = 100,
        max_memory_mb: float = 500.0,
        max_concurrent_chunks: int = 5,
        enable_monitoring: bool = True,
    ):
        self.chunk_size = chunk_size
        self.max_memory_mb = max_memory_mb
        self.max_concurrent_chunks = max_concurrent_chunks
        self.enable_monitoring = enable_monitoring

        # Processing state
        self.chunks_processed = 0
        self.total_elements_processed = 0
        self.total_connections_processed = 0
        self.processing_queue = asyncio.Queue()
        self.active_chunks = weakref.WeakSet()

        # Memory management
        self.memory_monitor = MemoryMonitor() if enable_monitoring else None
        self.circuit_breaker = MemoryCircuitBreaker(memory_threshold_percent=80.0)

        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="topo-stream")

        self.logger = logging.getLogger(__name__)

    async def start_monitoring(self):
        """Start memory monitoring if enabled."""
        if self.memory_monitor:
            await self.memory_monitor.start_monitoring()

    async def stop_monitoring(self):
        """Stop memory monitoring."""
        if self.memory_monitor:
            await self.memory_monitor.stop_monitoring()

    @memory_efficient(max_memory_mb=500.0, enable_profiling=True)
    async def stream_process_topology(
        self,
        topology: NetworkTopology,
        processor_func: Callable[[StreamingChunk], Any],
        region_filter: Optional[List[str]] = None,
    ) -> AsyncIterator[Any]:
        """
        Stream-process a topology with memory-efficient chunking.

        Args:
            topology: The network topology to process
            processor_func: Function to process each chunk
            region_filter: Optional list of regions to filter by

        Yields:
            Processed results for each chunk
        """
        try:
            # Start monitoring
            await self.start_monitoring()

            # Create chunks in priority order
            chunk_generators = [
                self._create_global_network_chunks(topology, region_filter),
                self._create_core_network_chunks(topology, region_filter),
                self._create_transit_gateway_chunks(topology, region_filter),
                self._create_vpc_chunks(topology, region_filter),
                self._create_segment_chunks(topology, region_filter),
                self._create_connection_chunks(topology, region_filter),
                self._create_network_function_chunks(topology, region_filter),
            ]

            # Process chunks with memory management
            semaphore = asyncio.Semaphore(self.max_concurrent_chunks)

            async def process_chunk_with_circuit_breaker(chunk: StreamingChunk):
                """Process a chunk with circuit breaker protection."""
                async with semaphore:
                    with self.circuit_breaker.protect(f"chunk-{chunk.chunk_id}"):
                        start_time = time.time()

                        # Add to active chunks for memory tracking
                        self.active_chunks.add(chunk)

                        try:
                            # Process chunk
                            result = await self._process_chunk_safely(chunk, processor_func)

                            # Update metrics
                            chunk.processing_time = time.time() - start_time
                            chunk.memory_usage = chunk.estimate_memory_usage()

                            self.chunks_processed += 1
                            self.total_elements_processed += len(chunk.elements)
                            self.total_connections_processed += len(chunk.connections)

                            return result

                        finally:
                            # Remove from active chunks
                            self.active_chunks.discard(chunk)

                            # Force garbage collection periodically
                            if self.chunks_processed % 10 == 0:
                                gc.collect()

            # Process all chunks
            tasks = []
            for generator in chunk_generators:
                async for chunk in generator:
                    # Check memory pressure
                    if self.memory_monitor:
                        current_metrics = self.memory_monitor.get_current_metrics()
                        if current_metrics.pressure_level in [
                            MemoryPressureLevel.HIGH,
                            MemoryPressureLevel.CRITICAL,
                        ]:
                            # Wait for some tasks to complete
                            if tasks:
                                await asyncio.wait(tasks[:5], return_when=asyncio.FIRST_COMPLETED)
                                tasks = [t for t in tasks if not t.done()]

                    # Create processing task
                    task = asyncio.create_task(process_chunk_with_circuit_breaker(chunk))
                    tasks.append(task)

                    # Yield results as they complete
                    if len(tasks) >= self.max_concurrent_chunks:
                        done, pending = await asyncio.wait(
                            tasks, return_when=asyncio.FIRST_COMPLETED
                        )

                        for task in done:
                            try:
                                result = await task
                                yield result
                            except Exception as e:
                                self.logger.error(f"Chunk processing failed: {e}")

                        tasks = list(pending)

            # Process remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if not isinstance(result, Exception):
                        yield result

        finally:
            # Stop monitoring
            await self.stop_monitoring()

    async def _process_chunk_safely(
        self, chunk: StreamingChunk, processor_func: Callable[[StreamingChunk], Any]
    ) -> Any:
        """Process a chunk with error handling and memory management."""
        try:
            # Check if processor function is async
            if asyncio.iscoroutinefunction(processor_func):
                return await processor_func(chunk)
            else:
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(self.thread_pool, processor_func, chunk)

        except Exception as e:
            self.logger.error(f"Failed to process chunk {chunk.chunk_id}: {e}")
            return {"chunk_id": chunk.chunk_id, "error": str(e), "success": False}

    async def _create_global_network_chunks(
        self, topology: NetworkTopology, region_filter: Optional[List[str]]
    ) -> AsyncIterator[StreamingChunk]:
        """Create chunks for global networks."""
        global_network_elements = [
            element
            for element in topology.elements.values()
            if element.element_type == NetworkElementType.GLOBAL_NETWORK
        ]

        for i in range(0, len(global_network_elements), self.chunk_size):
            chunk_elements = global_network_elements[i : i + self.chunk_size]

            # Convert to memory-efficient format
            efficient_elements = []
            for element in chunk_elements:
                efficient_element = self._convert_to_efficient_element(element)
                efficient_elements.append(efficient_element)

            chunk = StreamingChunk(
                chunk_id=f"global-networks-{i // self.chunk_size}",
                chunk_type=StreamingChunkType.GLOBAL_NETWORKS,
                elements=efficient_elements,
                priority=10,  # High priority
                metadata={
                    "batch_index": i // self.chunk_size,
                    "total_elements": len(chunk_elements),
                },
            )

            yield chunk

    async def _create_core_network_chunks(
        self, topology: NetworkTopology, region_filter: Optional[List[str]]
    ) -> AsyncIterator[StreamingChunk]:
        """Create chunks for core networks."""
        core_network_elements = [
            element
            for element in topology.elements.values()
            if element.element_type == NetworkElementType.CORE_NETWORK
        ]

        for i in range(0, len(core_network_elements), self.chunk_size):
            chunk_elements = core_network_elements[i : i + self.chunk_size]

            # Convert to memory-efficient format
            efficient_elements = []
            for element in chunk_elements:
                efficient_element = self._convert_to_efficient_element(element)
                efficient_elements.append(efficient_element)

            chunk = StreamingChunk(
                chunk_id=f"core-networks-{i // self.chunk_size}",
                chunk_type=StreamingChunkType.CORE_NETWORKS,
                elements=efficient_elements,
                priority=9,  # High priority
                metadata={
                    "batch_index": i // self.chunk_size,
                    "total_elements": len(chunk_elements),
                },
            )

            yield chunk

    async def _create_transit_gateway_chunks(
        self, topology: NetworkTopology, region_filter: Optional[List[str]]
    ) -> AsyncIterator[StreamingChunk]:
        """Create chunks for transit gateways."""
        tgw_elements = [
            element
            for element in topology.elements.values()
            if element.element_type == NetworkElementType.TRANSIT_GATEWAY
        ]

        # Filter by region if specified
        if region_filter:
            tgw_elements = [element for element in tgw_elements if element.region in region_filter]

        for i in range(0, len(tgw_elements), self.chunk_size):
            chunk_elements = tgw_elements[i : i + self.chunk_size]

            # Convert to memory-efficient format
            efficient_elements = []
            for element in chunk_elements:
                efficient_element = self._convert_to_efficient_element(element)
                efficient_elements.append(efficient_element)

            chunk = StreamingChunk(
                chunk_id=f"transit-gateways-{i // self.chunk_size}",
                chunk_type=StreamingChunkType.TRANSIT_GATEWAYS,
                elements=efficient_elements,
                priority=8,  # High priority
                region=chunk_elements[0].region if chunk_elements else None,
                metadata={
                    "batch_index": i // self.chunk_size,
                    "total_elements": len(chunk_elements),
                    "region": chunk_elements[0].region if chunk_elements else None,
                },
            )

            yield chunk

    async def _create_vpc_chunks(
        self, topology: NetworkTopology, region_filter: Optional[List[str]]
    ) -> AsyncIterator[StreamingChunk]:
        """Create chunks for VPCs."""
        vpc_elements = [
            element
            for element in topology.elements.values()
            if element.element_type == NetworkElementType.VPC
        ]

        # Filter by region if specified
        if region_filter:
            vpc_elements = [element for element in vpc_elements if element.region in region_filter]

        # Group by region for better cache locality
        region_groups = {}
        for element in vpc_elements:
            region = element.region
            if region not in region_groups:
                region_groups[region] = []
            region_groups[region].append(element)

        for region, elements in region_groups.items():
            for i in range(0, len(elements), self.chunk_size):
                chunk_elements = elements[i : i + self.chunk_size]

                # Convert to memory-efficient format
                efficient_elements = []
                for element in chunk_elements:
                    efficient_element = self._convert_to_efficient_element(element)
                    efficient_elements.append(efficient_element)

                chunk = StreamingChunk(
                    chunk_id=f"vpcs-{region}-{i // self.chunk_size}",
                    chunk_type=StreamingChunkType.VPCS,
                    elements=efficient_elements,
                    priority=7,  # Medium priority
                    region=region,
                    metadata={
                        "batch_index": i // self.chunk_size,
                        "total_elements": len(chunk_elements),
                        "region": region,
                    },
                )

                yield chunk

    async def _create_segment_chunks(
        self, topology: NetworkTopology, region_filter: Optional[List[str]]
    ) -> AsyncIterator[StreamingChunk]:
        """Create chunks for segments."""
        segment_elements = [
            element
            for element in topology.elements.values()
            if element.element_type == NetworkElementType.SEGMENT
        ]

        for i in range(0, len(segment_elements), self.chunk_size):
            chunk_elements = segment_elements[i : i + self.chunk_size]

            # Convert to memory-efficient format
            efficient_elements = []
            for element in chunk_elements:
                efficient_element = self._convert_to_efficient_element(element)
                efficient_elements.append(efficient_element)

            chunk = StreamingChunk(
                chunk_id=f"segments-{i // self.chunk_size}",
                chunk_type=StreamingChunkType.SEGMENTS,
                elements=efficient_elements,
                priority=6,  # Medium priority
                metadata={
                    "batch_index": i // self.chunk_size,
                    "total_elements": len(chunk_elements),
                },
            )

            yield chunk

    async def _create_connection_chunks(
        self, topology: NetworkTopology, region_filter: Optional[List[str]]
    ) -> AsyncIterator[StreamingChunk]:
        """Create chunks for connections."""
        connections = topology.connections

        for i in range(0, len(connections), self.chunk_size):
            chunk_connections = connections[i : i + self.chunk_size]

            # Convert to memory-efficient format
            efficient_connections = []
            for connection in chunk_connections:
                efficient_connection = self._convert_to_efficient_connection(connection)
                efficient_connections.append(efficient_connection)

            chunk = StreamingChunk(
                chunk_id=f"connections-{i // self.chunk_size}",
                chunk_type=StreamingChunkType.CONNECTIONS,
                connections=efficient_connections,
                priority=5,  # Medium priority
                metadata={
                    "batch_index": i // self.chunk_size,
                    "total_connections": len(chunk_connections),
                },
            )

            yield chunk

    async def _create_network_function_chunks(
        self, topology: NetworkTopology, region_filter: Optional[List[str]]
    ) -> AsyncIterator[StreamingChunk]:
        """Create chunks for network function groups."""
        nfg_elements = [
            element
            for element in topology.elements.values()
            if element.element_type == NetworkElementType.NETWORK_FUNCTION_GROUP
        ]

        for i in range(0, len(nfg_elements), self.chunk_size):
            chunk_elements = nfg_elements[i : i + self.chunk_size]

            # Convert to memory-efficient format
            efficient_elements = []
            for element in chunk_elements:
                efficient_element = self._convert_to_efficient_element(element)
                efficient_elements.append(efficient_element)

            chunk = StreamingChunk(
                chunk_id=f"network-functions-{i // self.chunk_size}",
                chunk_type=StreamingChunkType.NETWORK_FUNCTIONS,
                elements=efficient_elements,
                priority=4,  # Lower priority
                metadata={
                    "batch_index": i // self.chunk_size,
                    "total_elements": len(chunk_elements),
                },
            )

            yield chunk

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
        if hasattr(element, "cidr_blocks") and element.cidr_blocks:
            efficient.cidr_blocks = list(element.cidr_blocks)
        if hasattr(element, "tags") and element.tags:
            efficient.tags = dict(element.tags)
        if hasattr(element, "ip_addresses") and element.ip_addresses:
            efficient.ip_addresses = list(element.ip_addresses)

        # Set additional fields
        if hasattr(element, "segment_name"):
            efficient.segment_name = element.segment_name
        if hasattr(element, "core_network_id"):
            efficient.core_network_id = element.core_network_id
        if hasattr(element, "attachment_id"):
            efficient.attachment_id = element.attachment_id

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
        if hasattr(connection, "cost"):
            efficient.cost = connection.cost
        if hasattr(connection, "attachment_id"):
            efficient.attachment_id = connection.attachment_id
        if hasattr(connection, "segment_name"):
            efficient.segment_name = connection.segment_name

        return efficient

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        memory_stats = get_memory_stats()

        return {
            "chunks_processed": self.chunks_processed,
            "total_elements_processed": self.total_elements_processed,
            "total_connections_processed": self.total_connections_processed,
            "active_chunks": len(self.active_chunks),
            "memory_stats": memory_stats,
            "circuit_breaker_state": self.circuit_breaker.state,
        }

    async def close(self):
        """Clean up resources."""
        await self.stop_monitoring()
        self.thread_pool.shutdown(wait=True)


class StreamingTopologyManager:
    """
    High-level manager for streaming topology operations.

    Coordinates between topology discovery and streaming processing
    to handle large-scale network topologies efficiently.
    """

    def __init__(
        self,
        aws_manager,
        chunk_size: int = 100,
        max_memory_mb: float = 500.0,
        max_concurrent_operations: int = 10,
    ):
        self.aws_manager = aws_manager
        self.chunk_size = chunk_size
        self.max_memory_mb = max_memory_mb
        self.max_concurrent_operations = max_concurrent_operations

        # Initialize processor
        self.processor = StreamingTopologyProcessor(
            chunk_size=chunk_size,
            max_memory_mb=max_memory_mb,
            max_concurrent_chunks=max_concurrent_operations,
        )

        # Initialize optimized topology storage
        self.optimized_topology = MemoryOptimizedTopology(
            max_elements_in_memory=chunk_size * 2,  # Keep 2 chunks in memory
            enable_compression=True,
        )

        self.logger = logging.getLogger(__name__)

    @memory_efficient(max_memory_mb=1000.0, enable_profiling=True)
    async def discover_and_process_topology(
        self,
        regions: Optional[List[str]] = None,
        include_performance_metrics: bool = False,
        include_cross_account: bool = False,
        processor_func: Optional[Callable[[StreamingChunk], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Discover and process topology in a streaming fashion.

        Args:
            regions: AWS regions to analyze
            include_performance_metrics: Whether to include performance data
            include_cross_account: Whether to include cross-account resources
            processor_func: Optional custom processor function

        Returns:
            Dictionary with processing results and statistics
        """
        try:
            # Import here to avoid circular imports
            from ..tools.visualization.topology_discovery import (
                NetworkTopologyDiscovery,
            )

            # Initialize discovery
            discovery = NetworkTopologyDiscovery(self.aws_manager)

            # Discover topology with limited depth to reduce memory usage
            self.logger.info("Starting streaming topology discovery...")

            topology = await discovery.discover_complete_topology(
                regions=regions,
                include_performance_metrics=include_performance_metrics,
                include_cross_account=include_cross_account,
                include_network_functions=True,
                include_multi_hop_analysis=False,  # Disable to save memory
                max_depth=2,  # Limit depth for memory efficiency
            )

            self.logger.info(f"Discovered topology with {len(topology.elements)} elements")

            # Process topology in streaming fashion
            results = []
            processor = processor_func or self._default_processor

            async for result in self.processor.stream_process_topology(
                topology=topology, processor_func=processor, region_filter=regions
            ):
                results.append(result)

                # Add processed elements to optimized topology
                if isinstance(result, dict) and "elements" in result:
                    for element in result["elements"]:
                        self.optimized_topology.add_element(element)

                if isinstance(result, dict) and "connections" in result:
                    for connection in result["connections"]:
                        self.optimized_topology.add_connection(connection)

            # Get final statistics
            processing_stats = self.processor.get_processing_stats()
            topology_stats = self.optimized_topology.get_memory_stats()

            return {
                "success": True,
                "total_results": len(results),
                "processing_stats": processing_stats,
                "topology_stats": topology_stats,
                "original_topology": {
                    "elements": len(topology.elements),
                    "connections": len(topology.connections),
                    "regions": len(topology.regions),
                },
                "optimized_topology": {
                    "elements_in_memory": topology_stats["elements_in_memory"],
                    "connections_in_memory": topology_stats["connections_in_memory"],
                    "estimated_memory_mb": topology_stats["estimated_memory_mb"],
                },
            }

        except Exception as e:
            self.logger.error(f"Streaming topology discovery failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_stats": self.processor.get_processing_stats(),
            }

    def _default_processor(self, chunk: StreamingChunk) -> Dict[str, Any]:
        """Default processor that simply collects chunk data."""
        return {
            "chunk_id": chunk.chunk_id,
            "chunk_type": chunk.chunk_type.value,
            "elements": chunk.elements,
            "connections": chunk.connections,
            "element_count": len(chunk.elements),
            "connection_count": len(chunk.connections),
            "region": chunk.region,
            "metadata": chunk.metadata,
            "success": True,
        }

    @asynccontextmanager
    async def streaming_context(self):
        """Context manager for streaming operations."""
        try:
            await self.processor.start_monitoring()
            yield self
        finally:
            await self.processor.stop_monitoring()

    def get_element_stream(
        self,
        element_type: Optional[str] = None,
        region: Optional[str] = None,
        chunk_size: int = 100,
    ) -> Iterator[List[MemoryEfficientNetworkElement]]:
        """Get streaming iterator for elements."""
        return self.optimized_topology.stream_elements(
            element_type=element_type, region=region, chunk_size=chunk_size
        )

    def get_topology_summary(self) -> Dict[str, Any]:
        """Get summary of the current topology state."""
        topology_stats = self.optimized_topology.get_memory_stats()
        processing_stats = self.processor.get_processing_stats()

        return {
            "topology": topology_stats,
            "processing": processing_stats,
            "memory_efficiency": {
                "elements_per_mb": topology_stats["elements_in_memory"]
                / max(1, topology_stats["estimated_memory_mb"]),
                "connections_per_mb": topology_stats["connections_in_memory"]
                / max(1, topology_stats["estimated_memory_mb"]),
                "memory_pressure": processing_stats["memory_stats"]["current_metrics"][
                    "pressure_level"
                ],
            },
        }

    async def close(self):
        """Clean up resources."""
        await self.processor.close()
        self.optimized_topology.clear_cache()
