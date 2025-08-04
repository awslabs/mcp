"""
MCP Tool integration for Enhanced CloudWAN Topology Discovery Engine.

This module provides MCP tool wrappers for the Enhanced Topology Discovery Engine,
allowing clients to discover and analyze CloudWAN infrastructure through the MCP protocol.
"""

import logging
from typing import Any, Dict, List, Optional

from ..aws.client_manager import AWSClientManager
from ..models.base import BaseResponse
from ..tools.base import BaseTool, ToolError
from .visualization.enhanced_topology_discovery import (
    EnhancedNetworkTopologyDiscovery,
    NetworkTopology,
    TopologyDiscoveryResponse,
    DiscoveryStatus,
)

logger = logging.getLogger(__name__)


class DiscoverCompleteTopologyTool(BaseTool):
    """
    MCP Tool for discovering complete CloudWAN topology across multiple regions.

    This tool provides comprehensive discovery of CloudWAN infrastructure including:
    - Global Networks and Core Networks
    - Regional VPCs and Transit Gateways
    - Network segments and attachments
    - Cross-region peering relationships
    - Network Function Groups
    """

    name = "discover_complete_topology"
    description = """
    Discover complete CloudWAN topology across specified AWS regions with intelligent 
    caching and performance optimization. Returns comprehensive network infrastructure 
    analysis including hierarchical relationships and cross-region connectivity.
    """

    def __init__(self, client_manager: AWSClientManager):
        """
        Initialize the topology discovery tool.

        Args:
            client_manager: AWS client manager instance
        """
        super().__init__(client_manager)
        self.discovery_engine = EnhancedNetworkTopologyDiscovery(
            client_manager=client_manager,
            max_workers=10,
            cache_ttl=300,
            enable_incremental_updates=True,
        )

    async def execute(
        self,
        regions: List[str],
        include_cross_region_analysis: bool = True,
        enable_nfg_discovery: bool = True,
        discovery_id: Optional[str] = None,
        max_workers: Optional[int] = None,
        cache_ttl: Optional[int] = None,
    ) -> TopologyDiscoveryResponse:
        """
        Execute complete topology discovery.

        Args:
            regions: List of AWS regions to analyze
            include_cross_region_analysis: Include cross-region peering analysis
            enable_nfg_discovery: Enable Network Function Group discovery
            discovery_id: Optional custom discovery session ID
            max_workers: Override maximum concurrent workers
            cache_ttl: Override cache time-to-live in seconds

        Returns:
            Complete topology discovery response

        Raises:
            ToolError: If discovery fails or invalid parameters provided
        """
        if not regions:
            raise ToolError("At least one region must be specified for topology discovery")

        if len(regions) > 20:
            raise ToolError("Maximum 20 regions supported for single discovery operation")

        try:
            logger.info(f"Starting topology discovery across {len(regions)} regions")

            # Update engine configuration if overrides provided
            if max_workers is not None:
                self.discovery_engine.max_workers = max_workers
            if cache_ttl is not None:
                self.discovery_engine.cache_ttl = cache_ttl

            # Execute discovery
            topology = await self.discovery_engine.discover_complete_topology(
                regions=regions,
                include_cross_region_analysis=include_cross_region_analysis,
                enable_nfg_discovery=enable_nfg_discovery,
                discovery_id=discovery_id,
            )

            # Calculate summary statistics
            total_components = self._calculate_total_components(topology)
            performance_summary = self._build_performance_summary(topology)

            # Build response
            response = TopologyDiscoveryResponse(
                success=topology.overall_status != DiscoveryStatus.FAILED,
                topology=topology,
                regions_analyzed=list(topology.regional_topologies.keys()),
                total_components=total_components,
                performance_summary=performance_summary,
                message=f"Topology discovery completed with {topology.coverage_percentage:.1f}% coverage",
            )

            logger.info(f"Topology discovery completed: {total_components} components discovered")
            return response

        except Exception as e:
            logger.error(f"Topology discovery failed: {e}")
            raise ToolError(f"Topology discovery failed: {str(e)}")

    def _calculate_total_components(self, topology: NetworkTopology) -> int:
        """Calculate total number of components discovered."""
        total = len(topology.global_networks)

        # Add core networks
        for gn in topology.global_networks:
            total += len(gn.core_networks)

        # Add regional components
        for regional_topology in topology.regional_topologies.values():
            total += len(regional_topology.vpcs)
            total += len(regional_topology.transit_gateways)
            total += len(regional_topology.cloudwan_attachments)
            total += len(regional_topology.segments)

        # Add cross-region and NFG components
        total += len(topology.cross_region_peerings)
        total += len(topology.network_function_groups)

        return total

    def _build_performance_summary(self, topology: NetworkTopology) -> Dict[str, Any]:
        """Build performance analysis summary."""
        metrics = topology.discovery_metrics

        return {
            "discovery_duration_seconds": metrics.duration_seconds,
            "regions_processed": metrics.regions_processed,
            "components_per_second": self._calculate_total_components(topology)
            / max(metrics.duration_seconds, 0.1),
            "cache_hit_rate_percent": metrics.cache_hit_rate,
            "api_calls_made": metrics.api_calls_made,
            "errors_encountered": metrics.errors_encountered,
            "components_by_type": {
                component_type.value: count
                for component_type, count in metrics.components_discovered.items()
            },
        }


class GetTopologySnapshotTool(BaseTool):
    """
    MCP Tool for retrieving cached topology snapshots.

    This tool allows retrieval of previously discovered topology data
    for comparison and incremental analysis.
    """

    name = "get_topology_snapshot"
    description = """
    Retrieve a previously cached topology snapshot by discovery ID.
    Useful for comparing topology changes over time or retrieving
    historical network state information.
    """

    def __init__(self, client_manager: AWSClientManager):
        """
        Initialize the snapshot retrieval tool.

        Args:
            client_manager: AWS client manager instance
        """
        super().__init__(client_manager)
        self.discovery_engine = EnhancedNetworkTopologyDiscovery(
            client_manager=client_manager,
            max_workers=5,
            cache_ttl=300,
            enable_incremental_updates=True,
        )

    async def execute(
        self, discovery_id: str, include_metrics: bool = True
    ) -> TopologyDiscoveryResponse:
        """
        Retrieve topology snapshot by discovery ID.

        Args:
            discovery_id: Discovery session ID to retrieve
            include_metrics: Include discovery metrics in response

        Returns:
            Topology discovery response with cached data

        Raises:
            ToolError: If snapshot not found or retrieval fails
        """
        try:
            # Check if snapshot exists in cache
            if discovery_id not in self.discovery_engine._topology_snapshots:
                raise ToolError(f"Topology snapshot '{discovery_id}' not found in cache")

            topology = self.discovery_engine._topology_snapshots[discovery_id]

            # Build response
            response = TopologyDiscoveryResponse(
                success=True,
                topology=topology,
                regions_analyzed=list(topology.regional_topologies.keys()),
                total_components=self._calculate_total_components(topology),
                performance_summary=(
                    self._build_performance_summary(topology) if include_metrics else {}
                ),
                message=f"Retrieved cached topology snapshot: {discovery_id}",
            )

            logger.info(f"Retrieved topology snapshot: {discovery_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to retrieve topology snapshot: {e}")
            raise ToolError(f"Failed to retrieve topology snapshot: {str(e)}")

    def _calculate_total_components(self, topology: NetworkTopology) -> int:
        """Calculate total number of components discovered."""
        total = len(topology.global_networks)

        for gn in topology.global_networks:
            total += len(gn.core_networks)

        for regional_topology in topology.regional_topologies.values():
            total += len(regional_topology.vpcs)
            total += len(regional_topology.transit_gateways)
            total += len(regional_topology.cloudwan_attachments)
            total += len(regional_topology.segments)

        total += len(topology.cross_region_peerings)
        total += len(topology.network_function_groups)

        return total

    def _build_performance_summary(self, topology: NetworkTopology) -> Dict[str, Any]:
        """Build performance analysis summary."""
        metrics = topology.discovery_metrics

        return {
            "discovery_duration_seconds": metrics.duration_seconds,
            "regions_processed": metrics.regions_processed,
            "cache_hit_rate_percent": metrics.cache_hit_rate,
            "api_calls_made": metrics.api_calls_made,
            "errors_encountered": metrics.errors_encountered,
        }


class GetDiscoveryStatisticsTool(BaseTool):
    """
    MCP Tool for retrieving discovery engine statistics and performance metrics.

    This tool provides insights into the discovery engine's performance,
    cache utilization, and operational statistics.
    """

    name = "get_discovery_statistics"
    description = """
    Get comprehensive statistics about the topology discovery engine including
    cache utilization, performance metrics, and operational statistics.
    """

    def __init__(self, client_manager: AWSClientManager):
        """
        Initialize the statistics tool.

        Args:
            client_manager: AWS client manager instance
        """
        super().__init__(client_manager)
        self.discovery_engine = EnhancedNetworkTopologyDiscovery(
            client_manager=client_manager,
            max_workers=5,
            cache_ttl=300,
            enable_incremental_updates=True,
        )

    async def execute(self) -> BaseResponse:
        """
        Get discovery engine statistics.

        Returns:
            Statistics response with engine metrics
        """
        try:
            stats = self.discovery_engine.get_discovery_statistics()

            # Add additional runtime statistics
            stats.update(
                {
                    "available_snapshots": list(self.discovery_engine._topology_snapshots.keys()),
                    "component_relationships_count": len(
                        self.discovery_engine._component_relationships
                    ),
                    "cache_entries": len(self.discovery_engine._discovery_cache),
                }
            )

            response = BaseResponse(
                success=True,
                data=stats,
                message="Discovery engine statistics retrieved successfully",
            )

            logger.info("Retrieved discovery engine statistics")
            return response

        except Exception as e:
            logger.error(f"Failed to retrieve discovery statistics: {e}")
            raise ToolError(f"Failed to retrieve discovery statistics: {str(e)}")


class IncrementalTopologyUpdateTool(BaseTool):
    """
    MCP Tool for performing incremental topology updates.

    This tool enables efficient topology updates by comparing against
    a baseline topology and discovering only changed components.
    """

    name = "incremental_topology_update"
    description = """
    Perform incremental topology update based on a previous discovery baseline.
    This is more efficient than full discovery when checking for changes
    in an existing topology.
    """

    def __init__(self, client_manager: AWSClientManager):
        """
        Initialize the incremental update tool.

        Args:
            client_manager: AWS client manager instance
        """
        super().__init__(client_manager)
        self.discovery_engine = EnhancedNetworkTopologyDiscovery(
            client_manager=client_manager,
            max_workers=10,
            cache_ttl=300,
            enable_incremental_updates=True,
        )

    async def execute(
        self, base_discovery_id: str, regions: List[str]
    ) -> TopologyDiscoveryResponse:
        """
        Perform incremental topology update.

        Args:
            base_discovery_id: Previous discovery ID to use as baseline
            regions: Regions to check for updates

        Returns:
            Updated topology discovery response

        Raises:
            ToolError: If baseline not found or update fails
        """
        if not regions:
            raise ToolError("At least one region must be specified for incremental update")

        try:
            logger.info(f"Starting incremental topology update from baseline: {base_discovery_id}")

            # Attempt incremental update
            topology = await self.discovery_engine.get_incremental_update(
                base_discovery_id=base_discovery_id, regions=regions
            )

            if topology is None:
                raise ToolError(
                    f"Baseline topology '{base_discovery_id}' not found for incremental update"
                )

            # Build response
            response = TopologyDiscoveryResponse(
                success=topology.overall_status != DiscoveryStatus.FAILED,
                topology=topology,
                regions_analyzed=list(topology.regional_topologies.keys()),
                total_components=self._calculate_total_components(topology),
                performance_summary=self._build_performance_summary(topology),
                message=f"Incremental topology update completed from baseline: {base_discovery_id}",
            )

            logger.info("Incremental topology update completed")
            return response

        except Exception as e:
            logger.error(f"Incremental topology update failed: {e}")
            raise ToolError(f"Incremental topology update failed: {str(e)}")

    def _calculate_total_components(self, topology: NetworkTopology) -> int:
        """Calculate total number of components discovered."""
        total = len(topology.global_networks)

        for gn in topology.global_networks:
            total += len(gn.core_networks)

        for regional_topology in topology.regional_topologies.values():
            total += len(regional_topology.vpcs)
            total += len(regional_topology.transit_gateways)
            total += len(regional_topology.cloudwan_attachments)
            total += len(regional_topology.segments)

        total += len(topology.cross_region_peerings)
        total += len(topology.network_function_groups)

        return total

    def _build_performance_summary(self, topology: NetworkTopology) -> Dict[str, Any]:
        """Build performance analysis summary."""
        metrics = topology.discovery_metrics

        return {
            "discovery_duration_seconds": metrics.duration_seconds,
            "regions_processed": metrics.regions_processed,
            "cache_hit_rate_percent": metrics.cache_hit_rate,
            "api_calls_made": metrics.api_calls_made,
            "errors_encountered": metrics.errors_encountered,
        }
