"""
Route Resolution Engine with Longest-Prefix Matching.

This engine provides comprehensive route resolution capabilities across Transit Gateway
peering connections, implementing longest-prefix matching algorithms, next-hop 
determination, and end-to-end path analysis.

Features:
- Longest-prefix matching algorithm implementation
- Multi-hop route resolution across TGW peering
- Next-hop determination with multiple path support
- Route conflict detection and resolution
- Path optimization and cost analysis
- Performance metrics and caching
"""

import asyncio
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from .transit_gateway_route_engine import (
    TransitGatewayRouteEngine,
    RouteEntry,
)
from .tgw_peering_discovery_engine import (
    TGWPeeringDiscoveryEngine,
    TGWPeeringConnection,
)
from .async_executor_bridge import AsyncExecutorBridge


class RouteResolutionType(str, Enum):
    """Route resolution types."""

    EXACT_MATCH = "exact_match"
    LONGEST_PREFIX = "longest_prefix"
    DEFAULT_ROUTE = "default_route"
    NO_ROUTE = "no_route"


class PathStatus(str, Enum):
    """Path status for route resolution."""

    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    PARTIAL = "partial"
    BLACKHOLE = "blackhole"
    UNKNOWN = "unknown"


@dataclass
class RouteResolutionResult:
    """Result of route resolution for a target IP/CIDR."""

    target_ip: str
    resolution_type: RouteResolutionType
    matched_route: Optional[RouteEntry] = None
    next_hop_tgw_id: Optional[str] = None
    next_hop_attachment_id: Optional[str] = None
    path_status: PathStatus = PathStatus.UNKNOWN
    hop_count: int = 0
    total_path: List[str] = field(default_factory=list)  # List of TGW IDs in path
    alternative_paths: List[Dict[str, Any]] = field(default_factory=list)
    resolution_time_ms: float = 0.0
    confidence_score: float = 0.0  # 0.0 to 1.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class MultiPathAnalysis:
    """Analysis of multiple paths to a destination."""

    destination: str
    primary_path: Optional[RouteResolutionResult] = None
    backup_paths: List[RouteResolutionResult] = field(default_factory=list)
    load_balancing_possible: bool = False
    failover_capability: bool = False
    path_diversity_score: float = 0.0
    recommended_path: Optional[str] = None


@dataclass
class RoutingTable:
    """Consolidated routing table across multiple TGWs."""

    tgw_id: str
    region: str
    routes: List[RouteEntry] = field(default_factory=list)
    peering_connections: List[TGWPeeringConnection] = field(default_factory=list)
    next_hop_mapping: Dict[str, str] = field(default_factory=dict)  # attachment_id -> next_tgw_id
    last_updated: Optional[datetime] = None


class RouteResolutionEngine:
    """
    Advanced route resolution engine with longest-prefix matching.

    Provides comprehensive route resolution across Transit Gateway networks
    with support for multi-hop peering, path optimization, and performance analysis.
    """

    def __init__(
        self,
        aws_manager: AWSClientManager,
        config: CloudWANConfig,
        route_engine: TransitGatewayRouteEngine,
        peering_engine: TGWPeeringDiscoveryEngine,
    ):
        """
        Initialize the route resolution engine.

        Args:
            aws_manager: AWS client manager instance
            config: CloudWAN configuration
            route_engine: Transit Gateway route engine
            peering_engine: TGW peering discovery engine
        """
        self.aws_manager = aws_manager
        self.config = config
        self.route_engine = route_engine
        self.peering_engine = peering_engine
        self.legacy_adapter = AsyncExecutorBridge(aws_manager, config)

        # Caching for performance
        self._routing_table_cache: Dict[str, Tuple[RoutingTable, datetime]] = {}
        self._resolution_cache: Dict[str, Tuple[RouteResolutionResult, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)

        # Thread pool for CPU-intensive operations
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="RouteResolution")

    async def resolve_route(
        self,
        target_ip: str,
        source_tgw_id: str,
        source_region: str,
        max_hops: int = 10,
        enable_caching: bool = True,
    ) -> RouteResolutionResult:
        """
        Resolve route to target IP using longest-prefix matching.

        Args:
            target_ip: Target IP address to resolve
            source_tgw_id: Source Transit Gateway ID
            source_region: Source AWS region
            max_hops: Maximum hops to traverse
            enable_caching: Enable result caching

        Returns:
            Route resolution result
        """
        start_time = datetime.now()

        # Validate target IP
        try:
            ipaddress.ip_address(target_ip)
        except ValueError:
            return RouteResolutionResult(
                target_ip=target_ip,
                resolution_type=RouteResolutionType.NO_ROUTE,
                path_status=PathStatus.UNREACHABLE,
                warnings=["Invalid IP address format"],
            )

        # Check cache first
        cache_key = f"{target_ip}:{source_tgw_id}:{source_region}:{max_hops}"
        if enable_caching and cache_key in self._resolution_cache:
            cached_result, cached_time = self._resolution_cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_result

        try:
            # Build routing table for source TGW
            routing_table = await self._build_routing_table(source_tgw_id, source_region)

            # Perform longest-prefix matching
            resolution_result = await self._perform_longest_prefix_matching(
                target_ip, routing_table, max_hops
            )

            # Calculate resolution time
            resolution_time = (datetime.now() - start_time).total_seconds() * 1000
            resolution_result.resolution_time_ms = resolution_time

            # Calculate confidence score
            resolution_result.confidence_score = self._calculate_confidence_score(resolution_result)

            # Cache result
            if enable_caching:
                self._resolution_cache[cache_key] = (resolution_result, datetime.now())

            return resolution_result

        except Exception as e:
            return RouteResolutionResult(
                target_ip=target_ip,
                resolution_type=RouteResolutionType.NO_ROUTE,
                path_status=PathStatus.UNKNOWN,
                warnings=[f"Resolution failed: {str(e)}"],
            )

    async def _build_routing_table(
        self, tgw_id: str, region: str, visited_tgws: Optional[Set[str]] = None
    ) -> RoutingTable:
        """
        Build consolidated routing table for a TGW.

        Args:
            tgw_id: Transit Gateway ID
            region: AWS region
            visited_tgws: Set of visited TGWs to prevent cycles

        Returns:
            Consolidated routing table
        """
        if visited_tgws is None:
            visited_tgws = set()

        # Check cache first
        cache_key = f"{tgw_id}:{region}"
        if cache_key in self._routing_table_cache:
            cached_table, cached_time = self._routing_table_cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_table

        # Prevent infinite loops
        if tgw_id in visited_tgws:
            return RoutingTable(tgw_id=tgw_id, region=region)

        visited_tgws.add(tgw_id)

        try:
            # Get route table analyses for this TGW
            route_analyses = await self.route_engine.analyze_route_tables(
                transit_gateway_id=tgw_id, region=region, include_associations=True
            )

            # Get peering connections
            peering_connections = await self.peering_engine.discover_peering_connections(
                transit_gateway_id=tgw_id,
                region=region,
                max_hop_depth=1,  # Only direct connections for building routing table
            )

            # Consolidate routes from all route tables
            all_routes = []
            for analysis in route_analyses:
                all_routes.extend(analysis.route_entries)

            # Build next-hop mapping from peering connections
            next_hop_mapping = {}
            for conn in peering_connections:
                # Determine the peer TGW (not this TGW)
                peer_tgw_id = (
                    conn.accepter_tgw_id
                    if conn.requester_tgw_id == tgw_id
                    else conn.requester_tgw_id
                )

                # Map the peering attachment to the peer TGW
                next_hop_mapping[conn.peering_attachment_id] = peer_tgw_id

            routing_table = RoutingTable(
                tgw_id=tgw_id,
                region=region,
                routes=all_routes,
                peering_connections=peering_connections,
                next_hop_mapping=next_hop_mapping,
                last_updated=datetime.now(),
            )

            # Cache the routing table
            self._routing_table_cache[cache_key] = (routing_table, datetime.now())

            return routing_table

        except Exception as e:
            raise RuntimeError(f"Failed to build routing table for {tgw_id}: {str(e)}")

    async def _perform_longest_prefix_matching(
        self,
        target_ip: str,
        routing_table: RoutingTable,
        max_hops: int,
        current_hop: int = 0,
        path: Optional[List[str]] = None,
    ) -> RouteResolutionResult:
        """
        Perform longest-prefix matching with multi-hop support.

        Args:
            target_ip: Target IP address
            routing_table: Current TGW routing table
            max_hops: Maximum hops allowed
            current_hop: Current hop count
            path: Current path of TGW IDs

        Returns:
            Route resolution result
        """
        if path is None:
            path = [routing_table.tgw_id]

        if current_hop >= max_hops:
            return RouteResolutionResult(
                target_ip=target_ip,
                resolution_type=RouteResolutionType.NO_ROUTE,
                path_status=PathStatus.PARTIAL,
                hop_count=current_hop,
                total_path=path.copy(),
                warnings=["Maximum hop count exceeded"],
            )

        try:
            target_addr = ipaddress.ip_address(target_ip)
            best_match = None
            longest_prefix = -1

            # Find longest prefix match among active routes
            for route in routing_table.routes:
                if route.state.value != "active":
                    continue

                try:
                    network = ipaddress.ip_network(route.destination_cidr)
                    if target_addr in network and network.prefixlen > longest_prefix:
                        longest_prefix = network.prefixlen
                        best_match = route
                except ValueError:
                    continue

            if not best_match:
                # No matching route found
                return RouteResolutionResult(
                    target_ip=target_ip,
                    resolution_type=RouteResolutionType.NO_ROUTE,
                    path_status=PathStatus.UNREACHABLE,
                    hop_count=current_hop,
                    total_path=path.copy(),
                )

            # Check if this is a blackhole route
            if best_match.state.value == "blackhole":
                return RouteResolutionResult(
                    target_ip=target_ip,
                    resolution_type=RouteResolutionType.LONGEST_PREFIX,
                    matched_route=best_match,
                    path_status=PathStatus.BLACKHOLE,
                    hop_count=current_hop,
                    total_path=path.copy(),
                    warnings=["Route leads to blackhole"],
                )

            # Check if this route points to a local attachment (end of resolution)
            if best_match.target_type and best_match.target_type.lower() in [
                "vpc",
                "vpn",
                "direct-connect-gateway",
            ]:

                return RouteResolutionResult(
                    target_ip=target_ip,
                    resolution_type=RouteResolutionType.LONGEST_PREFIX,
                    matched_route=best_match,
                    next_hop_attachment_id=best_match.attachment_id,
                    path_status=PathStatus.REACHABLE,
                    hop_count=current_hop + 1,
                    total_path=path.copy(),
                )

            # Check if this route points to a peering connection
            if (
                best_match.attachment_id
                and best_match.attachment_id in routing_table.next_hop_mapping
            ):

                next_tgw_id = routing_table.next_hop_mapping[best_match.attachment_id]

                # Prevent loops
                if next_tgw_id in path:
                    return RouteResolutionResult(
                        target_ip=target_ip,
                        resolution_type=RouteResolutionType.LONGEST_PREFIX,
                        matched_route=best_match,
                        path_status=PathStatus.UNREACHABLE,
                        hop_count=current_hop,
                        total_path=path.copy(),
                        warnings=["Routing loop detected"],
                    )

                # Continue resolution at next TGW
                next_path = path + [next_tgw_id]

                # Determine the region for next TGW
                next_region = self._determine_tgw_region(
                    next_tgw_id, routing_table.peering_connections
                )

                # Build routing table for next TGW
                next_routing_table = await self._build_routing_table(
                    next_tgw_id, next_region, set(path)
                )

                # Recursive resolution
                next_result = await self._perform_longest_prefix_matching(
                    target_ip, next_routing_table, max_hops, current_hop + 1, next_path
                )

                # Update path information
                next_result.hop_count = current_hop + 1 + (next_result.hop_count - current_hop - 1)

                return next_result

            # Route found but no clear next hop
            return RouteResolutionResult(
                target_ip=target_ip,
                resolution_type=RouteResolutionType.LONGEST_PREFIX,
                matched_route=best_match,
                path_status=PathStatus.PARTIAL,
                hop_count=current_hop,
                total_path=path.copy(),
                warnings=["Route found but next hop unclear"],
            )

        except Exception as e:
            return RouteResolutionResult(
                target_ip=target_ip,
                resolution_type=RouteResolutionType.NO_ROUTE,
                path_status=PathStatus.UNKNOWN,
                hop_count=current_hop,
                total_path=path.copy(),
                warnings=[f"Resolution error: {str(e)}"],
            )

    def _determine_tgw_region(
        self, tgw_id: str, peering_connections: List[TGWPeeringConnection]
    ) -> str:
        """
        Determine the region for a TGW based on peering connections.

        Args:
            tgw_id: Transit Gateway ID
            peering_connections: List of peering connections

        Returns:
            AWS region for the TGW
        """
        for conn in peering_connections:
            if conn.requester_tgw_id == tgw_id:
                return conn.requester_region
            elif conn.accepter_tgw_id == tgw_id:
                return conn.accepter_region

        # Default fallback
        return self.config.aws.regions[0] if self.config.aws.regions else "us-east-1"

    def _calculate_confidence_score(self, result: RouteResolutionResult) -> float:
        """
        Calculate confidence score for route resolution result.

        Args:
            result: Route resolution result

        Returns:
            Confidence score from 0.0 to 1.0
        """
        base_score = 0.0

        # Base score based on resolution type
        if result.resolution_type == RouteResolutionType.EXACT_MATCH:
            base_score = 1.0
        elif result.resolution_type == RouteResolutionType.LONGEST_PREFIX:
            base_score = 0.9
        elif result.resolution_type == RouteResolutionType.DEFAULT_ROUTE:
            base_score = 0.7
        else:
            base_score = 0.0

        # Adjust based on path status
        if result.path_status == PathStatus.REACHABLE:
            path_modifier = 1.0
        elif result.path_status == PathStatus.PARTIAL:
            path_modifier = 0.6
        elif result.path_status == PathStatus.BLACKHOLE:
            path_modifier = 0.3
        else:
            path_modifier = 0.1

        # Adjust based on hop count (prefer shorter paths)
        hop_modifier = max(0.5, 1.0 - (result.hop_count * 0.1))

        # Adjust based on warnings
        warning_modifier = max(0.5, 1.0 - (len(result.warnings) * 0.1))

        return base_score * path_modifier * hop_modifier * warning_modifier

    async def analyze_multiple_paths(
        self,
        target_ip: str,
        source_tgws: List[Tuple[str, str]],  # List of (tgw_id, region) tuples
        max_hops: int = 10,
    ) -> MultiPathAnalysis:
        """
        Analyze multiple paths to a destination from different source TGWs.

        Args:
            target_ip: Target IP address
            source_tgws: List of source TGW and region tuples
            max_hops: Maximum hops per path

        Returns:
            Multi-path analysis results
        """
        analysis = MultiPathAnalysis(destination=target_ip)

        # Resolve routes from all source TGWs
        resolution_tasks = []
        for tgw_id, region in source_tgws:
            task = self.resolve_route(target_ip, tgw_id, region, max_hops)
            resolution_tasks.append(task)

        results = await asyncio.gather(*resolution_tasks, return_exceptions=True)

        # Process results
        valid_results = []
        for result in results:
            if isinstance(result, RouteResolutionResult):
                valid_results.append(result)

        if not valid_results:
            return analysis

        # Sort by confidence score (highest first)
        valid_results.sort(key=lambda x: x.confidence_score, reverse=True)

        # Set primary and backup paths
        reachable_results = [r for r in valid_results if r.path_status == PathStatus.REACHABLE]

        if reachable_results:
            analysis.primary_path = reachable_results[0]
            analysis.backup_paths = reachable_results[1:]

            # Check for load balancing possibility
            analysis.load_balancing_possible = len(reachable_results) > 1

            # Check for failover capability
            analysis.failover_capability = len(reachable_results) > 1

            # Calculate path diversity score
            analysis.path_diversity_score = self._calculate_path_diversity(reachable_results)

            # Recommend best path
            analysis.recommended_path = (
                reachable_results[0].total_path[0] if reachable_results[0].total_path else None
            )

        return analysis

    def _calculate_path_diversity(self, results: List[RouteResolutionResult]) -> float:
        """
        Calculate path diversity score.

        Args:
            results: List of route resolution results

        Returns:
            Diversity score from 0.0 to 1.0
        """
        if len(results) <= 1:
            return 0.0

        # Calculate diversity based on path differences
        unique_hops = set()
        total_hops = 0

        for result in results:
            for hop in result.total_path:
                unique_hops.add(hop)
                total_hops += 1

        if total_hops == 0:
            return 0.0

        # Diversity score based on unique hops vs total hops
        return len(unique_hops) / total_hops

    async def trace_route_path(
        self,
        target_ip: str,
        source_tgw_id: str,
        source_region: str,
        include_performance_metrics: bool = False,
    ) -> Dict[str, Any]:
        """
        Trace complete route path with detailed hop-by-hop analysis.

        Args:
            target_ip: Target IP address
            source_tgw_id: Source TGW ID
            source_region: Source AWS region
            include_performance_metrics: Include performance metrics

        Returns:
            Detailed path trace results
        """
        result = await self.resolve_route(target_ip, source_tgw_id, source_region)

        trace_result = {
            "target_ip": target_ip,
            "source_tgw_id": source_tgw_id,
            "source_region": source_region,
            "path_status": result.path_status.value,
            "total_hops": result.hop_count,
            "resolution_time_ms": result.resolution_time_ms,
            "confidence_score": result.confidence_score,
            "hop_details": [],
            "warnings": result.warnings,
        }

        # Build hop-by-hop details
        for i, tgw_id in enumerate(result.total_path):
            hop_detail = {
                "hop_number": i + 1,
                "tgw_id": tgw_id,
                "region": source_region,  # Would need to track actual regions per hop
                "matched_route": None,
                "next_hop": (result.total_path[i + 1] if i + 1 < len(result.total_path) else None),
            }

            if i == 0 and result.matched_route:
                hop_detail["matched_route"] = {
                    "destination_cidr": result.matched_route.destination_cidr,
                    "state": result.matched_route.state.value,
                    "route_type": result.matched_route.route_type.value,
                    "target_type": result.matched_route.target_type,
                    "attachment_id": result.matched_route.attachment_id,
                }

            # Add performance metrics if requested
            if include_performance_metrics:
                hop_detail["performance_metrics"] = await self._get_hop_performance_metrics(tgw_id)

            trace_result["hop_details"].append(hop_detail)

        return trace_result

    async def _get_hop_performance_metrics(self, tgw_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a TGW hop.

        Args:
            tgw_id: Transit Gateway ID

        Returns:
            Performance metrics
        """
        # Placeholder for performance metrics
        # In practice, this would query CloudWatch metrics
        return {
            "average_latency_ms": None,
            "packet_loss_percent": 0.0,
            "throughput_mbps": None,
            "connection_count": None,
            "cpu_utilization_percent": None,
        }

    async def cleanup(self):
        """Cleanup resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
        self._routing_table_cache.clear()
        self._resolution_cache.clear()
