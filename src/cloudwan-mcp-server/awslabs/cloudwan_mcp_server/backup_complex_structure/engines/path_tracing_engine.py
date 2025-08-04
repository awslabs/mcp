"""
Path Tracing Engine for CloudWAN Networks.

This engine provides comprehensive end-to-end path discovery and tracing capabilities
for CloudWAN networks, implementing advanced graph-based algorithms for multi-hop
routing analysis, Network Function Group processing, and cross-account path discovery.

Features:
- BFS/DFS path discovery algorithms for CloudWAN networks
- Multi-hop routing through Network Function Groups
- CloudWAN segment isolation and policy evaluation
- Cross-account path discovery via AWS RAM shared resources
- Performance optimization with caching and parallel processing
- Path ranking by cost, latency, and reliability
"""

import asyncio
import ipaddress
import networkx as nx
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from .route_resolution_engine import (
    RouteResolutionEngine,
    PathStatus,
)
from .tgw_peering_discovery_engine import (
    TGWPeeringDiscoveryEngine,
)
from .network_function_group_analyzer import NetworkFunctionGroupAnalyzer
from .cloudwan_policy_evaluator import CloudWANPolicyEvaluator
from .async_executor_bridge import AsyncExecutorBridge


class PathDiscoveryAlgorithm(str, Enum):
    """Path discovery algorithm types."""

    BFS = "breadth_first_search"
    DFS = "depth_first_search"
    DIJKSTRA = "dijkstra_shortest_path"
    A_STAR = "a_star_heuristic"


class PathType(str, Enum):
    """Types of network paths."""

    DIRECT = "direct"
    MULTI_HOP = "multi_hop"
    CROSS_SEGMENT = "cross_segment"
    CROSS_ACCOUNT = "cross_account"
    INSPECTION_ROUTED = "inspection_routed"


class PathRankingCriteria(str, Enum):
    """Path ranking criteria."""

    COST = "cost"
    LATENCY = "latency"
    RELIABILITY = "reliability"
    HOP_COUNT = "hop_count"
    BANDWIDTH = "bandwidth"


@dataclass
class NetworkNode:
    """Network node in path discovery graph."""

    node_id: str
    node_type: str  # vpc, tgw, cloudwan_core, segment, inspection_vpc
    region: str
    account_id: str
    ip_range: Optional[str] = None
    segment_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Performance metrics
    latency_ms: float = 0.0
    cost_factor: float = 1.0
    reliability_score: float = 1.0
    bandwidth_mbps: Optional[float] = None


@dataclass
class NetworkEdge:
    """Network edge (connection) in path discovery graph."""

    source_node: str
    destination_node: str
    edge_type: str  # attachment, peering, policy_route, inspection
    connection_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Path characteristics
    weight: float = 1.0
    latency_ms: float = 0.0
    cost: float = 0.0
    reliability: float = 1.0
    bandwidth_mbps: Optional[float] = None
    is_bidirectional: bool = True


@dataclass
class DiscoveredPath:
    """Discovered network path between two endpoints."""

    source_ip: str
    destination_ip: str
    path_nodes: List[NetworkNode]
    path_edges: List[NetworkEdge]
    path_type: PathType
    hop_count: int

    # Path metrics
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    reliability_score: float = 1.0
    bottleneck_bandwidth_mbps: Optional[float] = None

    # Policy information
    segment_isolation_rules: List[str] = field(default_factory=list)
    network_function_groups: List[str] = field(default_factory=list)
    inspection_points: List[str] = field(default_factory=list)

    # Analysis results
    is_reachable: bool = True
    path_status: PathStatus = PathStatus.REACHABLE
    failure_points: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Discovery metadata
    discovery_algorithm: PathDiscoveryAlgorithm = PathDiscoveryAlgorithm.BFS
    discovery_time_ms: float = 0.0
    confidence_score: float = 1.0


@dataclass
class PathAnalysisResult:
    """Comprehensive path analysis result."""

    source_ip: str
    destination_ip: str
    discovered_paths: List[DiscoveredPath]
    primary_path: Optional[DiscoveredPath] = None
    alternative_paths: List[DiscoveredPath] = field(default_factory=list)

    # Path comparison
    path_diversity_score: float = 0.0
    load_balancing_capable: bool = False
    failover_paths: List[DiscoveredPath] = field(default_factory=list)

    # Analysis metadata
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    total_analysis_time_ms: float = 0.0
    algorithm_used: PathDiscoveryAlgorithm = PathDiscoveryAlgorithm.BFS
    max_paths_analyzed: int = 10


class PathTracingEngine:
    """
    Advanced path tracing engine for CloudWAN networks.

    Implements sophisticated path discovery algorithms using graph theory and
    network analysis to provide comprehensive end-to-end path intelligence.
    """

    def __init__(
        self,
        aws_manager: AWSClientManager,
        config: CloudWANConfig,
        route_engine: RouteResolutionEngine,
        peering_engine: TGWPeeringDiscoveryEngine,
        nfg_analyzer: NetworkFunctionGroupAnalyzer,
        policy_evaluator: CloudWANPolicyEvaluator,
    ):
        """
        Initialize the path tracing engine.

        Args:
            aws_manager: AWS client manager instance
            config: CloudWAN configuration
            route_engine: Route resolution engine
            peering_engine: TGW peering discovery engine
            nfg_analyzer: Network Function Group analyzer
            policy_evaluator: CloudWAN policy evaluator
        """
        self.aws_manager = aws_manager
        self.config = config
        self.route_engine = route_engine
        self.peering_engine = peering_engine
        self.nfg_analyzer = nfg_analyzer
        self.policy_evaluator = policy_evaluator
        self.legacy_adapter = AsyncExecutorBridge(aws_manager, config)

        # Network topology graph
        self._topology_graph = nx.MultiDiGraph()
        self._graph_last_updated: Optional[datetime] = None
        self._graph_ttl = timedelta(minutes=15)

        # Caching for performance
        self._path_cache: Dict[str, Tuple[PathAnalysisResult, datetime]] = {}
        self._topology_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._cache_ttl = timedelta(minutes=10)

        # Performance optimization
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="PathTracing")
        self._max_concurrent_discoveries = 5

        # Path ranking weights
        self._ranking_weights = {
            PathRankingCriteria.COST: 0.3,
            PathRankingCriteria.LATENCY: 0.3,
            PathRankingCriteria.RELIABILITY: 0.2,
            PathRankingCriteria.HOP_COUNT: 0.2,
        }

    async def discover_paths(
        self,
        source_ip: str,
        destination_ip: str,
        algorithm: PathDiscoveryAlgorithm = PathDiscoveryAlgorithm.BFS,
        max_paths: int = 10,
        max_hops: int = 15,
        include_cross_account: bool = True,
        enable_caching: bool = True,
    ) -> PathAnalysisResult:
        """
        Discover all possible paths between source and destination IPs.

        Args:
            source_ip: Source IP address
            destination_ip: Destination IP address
            algorithm: Path discovery algorithm to use
            max_paths: Maximum number of paths to discover
            max_hops: Maximum hops per path
            include_cross_account: Include cross-account paths
            enable_caching: Enable result caching

        Returns:
            Comprehensive path analysis result
        """
        start_time = datetime.now()

        # Validate IP addresses
        try:
            ipaddress.ip_address(source_ip)
            ipaddress.ip_address(destination_ip)
        except ValueError:
            return PathAnalysisResult(
                source_ip=source_ip,
                destination_ip=destination_ip,
                discovered_paths=[],
                total_analysis_time_ms=0.0,
            )

        # Check cache first
        cache_key = f"{source_ip}:{destination_ip}:{algorithm.value}:{max_paths}:{max_hops}"
        if enable_caching and cache_key in self._path_cache:
            cached_result, cached_time = self._path_cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_result

        try:
            # Ensure topology graph is current
            await self._update_topology_graph()

            # Find source and destination nodes
            source_nodes = await self._find_nodes_for_ip(source_ip)
            destination_nodes = await self._find_nodes_for_ip(destination_ip)

            if not source_nodes or not destination_nodes:
                return PathAnalysisResult(
                    source_ip=source_ip,
                    destination_ip=destination_ip,
                    discovered_paths=[],
                    total_analysis_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                )

            # Discover paths using selected algorithm
            discovered_paths = []

            if algorithm == PathDiscoveryAlgorithm.BFS:
                discovered_paths = await self._discover_paths_bfs(
                    source_nodes, destination_nodes, max_paths, max_hops
                )
            elif algorithm == PathDiscoveryAlgorithm.DFS:
                discovered_paths = await self._discover_paths_dfs(
                    source_nodes, destination_nodes, max_paths, max_hops
                )
            elif algorithm == PathDiscoveryAlgorithm.DIJKSTRA:
                discovered_paths = await self._discover_paths_dijkstra(
                    source_nodes, destination_nodes, max_paths
                )
            elif algorithm == PathDiscoveryAlgorithm.A_STAR:
                discovered_paths = await self._discover_paths_a_star(
                    source_nodes, destination_nodes, max_paths
                )

            # Filter cross-account paths if not requested
            if not include_cross_account:
                discovered_paths = [
                    path for path in discovered_paths if path.path_type != PathType.CROSS_ACCOUNT
                ]

            # Enhance paths with detailed analysis
            await self._enhance_paths_with_analysis(discovered_paths)

            # Rank and prioritize paths
            ranked_paths = await self._rank_paths(discovered_paths)

            # Create analysis result
            result = PathAnalysisResult(
                source_ip=source_ip,
                destination_ip=destination_ip,
                discovered_paths=ranked_paths,
                primary_path=ranked_paths[0] if ranked_paths else None,
                alternative_paths=ranked_paths[1:] if len(ranked_paths) > 1 else [],
                path_diversity_score=self._calculate_path_diversity(ranked_paths),
                load_balancing_capable=len(ranked_paths) > 1,
                failover_paths=[p for p in ranked_paths[1:] if p.reliability_score > 0.8],
                total_analysis_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                algorithm_used=algorithm,
                max_paths_analyzed=max_paths,
            )

            # Cache result
            if enable_caching:
                self._path_cache[cache_key] = (result, datetime.now())

            return result

        except Exception:
            return PathAnalysisResult(
                source_ip=source_ip,
                destination_ip=destination_ip,
                discovered_paths=[],
                total_analysis_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

    async def _update_topology_graph(self) -> None:
        """Update the network topology graph with current infrastructure."""
        if self._graph_last_updated and datetime.now() - self._graph_last_updated < self._graph_ttl:
            return

        # Clear existing graph
        self._topology_graph.clear()

        # Build graph concurrently
        tasks = [
            self._add_vpc_nodes(),
            self._add_tgw_nodes(),
            self._add_cloudwan_nodes(),
            self._add_peering_edges(),
            self._add_attachment_edges(),
            self._add_policy_edges(),
        ]

        await asyncio.gather(*tasks, return_exceptions=True)
        self._graph_last_updated = datetime.now()

    async def _add_vpc_nodes(self) -> None:
        """Add VPC nodes to topology graph."""
        try:
            for region in self.config.aws.regions:
                ec2_client = await self.aws_manager.get_client("ec2", region)

                response = await ec2_client.describe_vpcs()
                vpcs = response.get("Vpcs", [])

                for vpc in vpcs:
                    node = NetworkNode(
                        node_id=vpc["VpcId"],
                        node_type="vpc",
                        region=region,
                        account_id=vpc.get("OwnerId", ""),
                        ip_range=vpc.get("CidrBlock"),
                        metadata=vpc,
                    )

                    self._topology_graph.add_node(node.node_id, **node.__dict__)

        except Exception:
            # Continue with partial topology if VPC discovery fails
            pass

    async def _add_tgw_nodes(self) -> None:
        """Add Transit Gateway nodes to topology graph."""
        try:
            for region in self.config.aws.regions:
                ec2_client = await self.aws_manager.get_client("ec2", region)

                response = await ec2_client.describe_transit_gateways()
                tgws = response.get("TransitGateways", [])

                for tgw in tgws:
                    node = NetworkNode(
                        node_id=tgw["TransitGatewayId"],
                        node_type="tgw",
                        region=region,
                        account_id=tgw.get("OwnerId", ""),
                        metadata=tgw,
                    )

                    self._topology_graph.add_node(node.node_id, **node.__dict__)

        except Exception:
            pass

    async def _add_cloudwan_nodes(self) -> None:
        """Add CloudWAN Core Network and segment nodes to topology graph."""
        try:
            networkmanager_client = await self.aws_manager.get_client("networkmanager", "us-west-2")

            # Get Global Networks
            response = await networkmanager_client.list_global_networks()
            global_networks = response.get("GlobalNetworks", [])

            for gn in global_networks:
                gn_id = gn["GlobalNetworkId"]

                # Get Core Networks
                core_networks_response = await networkmanager_client.list_core_networks(
                    GlobalNetworkId=gn_id
                )

                for cn in core_networks_response.get("CoreNetworks", []):
                    # Add Core Network node
                    cn_node = NetworkNode(
                        node_id=cn["CoreNetworkId"],
                        node_type="cloudwan_core",
                        region="global",
                        account_id=cn.get("OwnerAccountId", ""),
                        metadata=cn,
                    )
                    self._topology_graph.add_node(cn_node.node_id, **cn_node.__dict__)

                    # Add segment nodes
                    segments = await self._get_core_network_segments(cn["CoreNetworkId"])
                    for segment in segments:
                        segment_node = NetworkNode(
                            node_id=f"{cn['CoreNetworkId']}-{segment['name']}",
                            node_type="cloudwan_segment",
                            region="global",
                            account_id=cn.get("OwnerAccountId", ""),
                            segment_name=segment["name"],
                            metadata=segment,
                        )
                        self._topology_graph.add_node(segment_node.node_id, **segment_node.__dict__)

        except Exception:
            pass

    async def _add_peering_edges(self) -> None:
        """Add peering connection edges to topology graph."""
        try:
            for region in self.config.aws.regions:
                ec2_client = await self.aws_manager.get_client("ec2", region)

                # TGW peering connections
                response = await ec2_client.describe_transit_gateway_peering_attachments()
                peering_attachments = response.get("TransitGatewayPeeringAttachments", [])

                for attachment in peering_attachments:
                    if attachment.get("State") == "available":
                        requester_tgw = attachment.get("RequesterTgwInfo", {}).get(
                            "TransitGatewayId"
                        )
                        accepter_tgw = attachment.get("AccepterTgwInfo", {}).get("TransitGatewayId")

                        if requester_tgw and accepter_tgw:
                            edge = NetworkEdge(
                                source_node=requester_tgw,
                                destination_node=accepter_tgw,
                                edge_type="tgw_peering",
                                connection_id=attachment["TransitGatewayAttachmentId"],
                                metadata=attachment,
                            )

                            self._topology_graph.add_edge(
                                edge.source_node,
                                edge.destination_node,
                                key=edge.connection_id,
                                **edge.__dict__,
                            )

        except Exception:
            pass

    async def _add_attachment_edges(self) -> None:
        """Add attachment edges between VPCs, TGWs, and CloudWAN."""
        try:
            for region in self.config.aws.regions:
                ec2_client = await self.aws_manager.get_client("ec2", region)

                # TGW VPC attachments
                response = await ec2_client.describe_transit_gateway_vpc_attachments()
                vpc_attachments = response.get("TransitGatewayVpcAttachments", [])

                for attachment in vpc_attachments:
                    if attachment.get("State") == "available":
                        tgw_id = attachment.get("TransitGatewayId")
                        vpc_id = attachment.get("VpcId")

                        if tgw_id and vpc_id:
                            edge = NetworkEdge(
                                source_node=vpc_id,
                                destination_node=tgw_id,
                                edge_type="vpc_attachment",
                                connection_id=attachment["TransitGatewayAttachmentId"],
                                metadata=attachment,
                            )

                            self._topology_graph.add_edge(
                                edge.source_node,
                                edge.destination_node,
                                key=edge.connection_id,
                                **edge.__dict__,
                            )

        except Exception:
            pass

    async def _add_policy_edges(self) -> None:
        """Add CloudWAN policy-based routing edges."""
        try:
            # This would analyze CloudWAN policies and add routing edges
            # between segments based on send-to/send-via rules
            policy_edges = await self.policy_evaluator.get_policy_routing_edges()

            for edge_info in policy_edges:
                edge = NetworkEdge(
                    source_node=edge_info["source"],
                    destination_node=edge_info["destination"],
                    edge_type="policy_route",
                    connection_id=edge_info["policy_id"],
                    metadata=edge_info,
                )

                self._topology_graph.add_edge(
                    edge.source_node,
                    edge.destination_node,
                    key=edge.connection_id,
                    **edge.__dict__,
                )

        except Exception:
            pass

    async def _find_nodes_for_ip(self, ip_address: str) -> List[str]:
        """Find network nodes that contain the given IP address."""
        matching_nodes = []

        try:
            target_ip = ipaddress.ip_address(ip_address)

            for node_id, node_data in self._topology_graph.nodes(data=True):
                ip_range = node_data.get("ip_range")
                if ip_range:
                    try:
                        network = ipaddress.ip_network(ip_range)
                        if target_ip in network:
                            matching_nodes.append(node_id)
                    except ValueError:
                        continue

        except ValueError:
            pass

        return matching_nodes

    async def _discover_paths_bfs(
        self,
        source_nodes: List[str],
        destination_nodes: List[str],
        max_paths: int,
        max_hops: int,
    ) -> List[DiscoveredPath]:
        """Discover paths using Breadth-First Search algorithm."""
        discovered_paths = []

        for source_node in source_nodes:
            for destination_node in destination_nodes:
                try:
                    # Use NetworkX BFS to find all simple paths
                    paths = list(
                        nx.all_simple_paths(
                            self._topology_graph,
                            source_node,
                            destination_node,
                            cutoff=max_hops,
                        )
                    )

                    for path_nodes in paths[:max_paths]:
                        discovered_path = await self._create_discovered_path(
                            path_nodes, PathDiscoveryAlgorithm.BFS
                        )
                        if discovered_path:
                            discovered_paths.append(discovered_path)

                except nx.NetworkXNoPath:
                    continue

        return discovered_paths[:max_paths]

    async def _discover_paths_dfs(
        self,
        source_nodes: List[str],
        destination_nodes: List[str],
        max_paths: int,
        max_hops: int,
    ) -> List[DiscoveredPath]:
        """Discover paths using Depth-First Search algorithm."""
        discovered_paths = []

        for source_node in source_nodes:
            for destination_node in destination_nodes:
                try:
                    # Custom DFS implementation with depth limit
                    paths = self._dfs_find_paths(source_node, destination_node, max_hops, max_paths)

                    for path_nodes in paths:
                        discovered_path = await self._create_discovered_path(
                            path_nodes, PathDiscoveryAlgorithm.DFS
                        )
                        if discovered_path:
                            discovered_paths.append(discovered_path)

                except Exception:
                    continue

        return discovered_paths[:max_paths]

    async def _discover_paths_dijkstra(
        self, source_nodes: List[str], destination_nodes: List[str], max_paths: int
    ) -> List[DiscoveredPath]:
        """Discover shortest paths using Dijkstra's algorithm."""
        discovered_paths = []

        for source_node in source_nodes:
            for destination_node in destination_nodes:
                try:
                    # Find shortest path by weight
                    path_nodes = nx.shortest_path(
                        self._topology_graph,
                        source_node,
                        destination_node,
                        weight="weight",
                    )

                    discovered_path = await self._create_discovered_path(
                        path_nodes, PathDiscoveryAlgorithm.DIJKSTRA
                    )
                    if discovered_path:
                        discovered_paths.append(discovered_path)

                except nx.NetworkXNoPath:
                    continue

        return discovered_paths[:max_paths]

    async def _discover_paths_a_star(
        self, source_nodes: List[str], destination_nodes: List[str], max_paths: int
    ) -> List[DiscoveredPath]:
        """Discover paths using A* heuristic algorithm."""
        discovered_paths = []

        def heuristic(node1, node2):
            """Simple heuristic based on node types."""
            node1_data = self._topology_graph.nodes[node1]
            node2_data = self._topology_graph.nodes[node2]

            # Prefer direct connections and shorter regional distances
            if node1_data.get("region") == node2_data.get("region"):
                return 1.0
            return 2.0

        for source_node in source_nodes:
            for destination_node in destination_nodes:
                try:
                    path_nodes = nx.astar_path(
                        self._topology_graph,
                        source_node,
                        destination_node,
                        heuristic=heuristic,
                        weight="weight",
                    )

                    discovered_path = await self._create_discovered_path(
                        path_nodes, PathDiscoveryAlgorithm.A_STAR
                    )
                    if discovered_path:
                        discovered_paths.append(discovered_path)

                except nx.NetworkXNoPath:
                    continue

        return discovered_paths[:max_paths]

    def _dfs_find_paths(
        self,
        source: str,
        destination: str,
        max_depth: int,
        max_paths: int,
        visited: Optional[Set[str]] = None,
        path: Optional[List[str]] = None,
    ) -> List[List[str]]:
        """Custom DFS path finding with depth limit."""
        if visited is None:
            visited = set()
        if path is None:
            path = []

        visited.add(source)
        path.append(source)

        paths = []

        if source == destination:
            paths.append(path.copy())
        elif len(path) < max_depth:
            for neighbor in self._topology_graph.neighbors(source):
                if neighbor not in visited and len(paths) < max_paths:
                    paths.extend(
                        self._dfs_find_paths(
                            neighbor,
                            destination,
                            max_depth,
                            max_paths - len(paths),
                            visited.copy(),
                            path.copy(),
                        )
                    )

        return paths

    async def _create_discovered_path(
        self, path_node_ids: List[str], algorithm: PathDiscoveryAlgorithm
    ) -> Optional[DiscoveredPath]:
        """Create a DiscoveredPath object from node IDs."""
        if len(path_node_ids) < 2:
            return None

        try:
            # Build path nodes
            path_nodes = []
            for node_id in path_node_ids:
                node_data = self._topology_graph.nodes[node_id]
                node = NetworkNode(
                    **{k: v for k, v in node_data.items() if k in NetworkNode.__annotations__}
                )
                path_nodes.append(node)

            # Build path edges
            path_edges = []
            for i in range(len(path_node_ids) - 1):
                source_id = path_node_ids[i]
                dest_id = path_node_ids[i + 1]

                # Get edge data (there might be multiple edges)
                edge_data = self._topology_graph.get_edge_data(source_id, dest_id)
                if edge_data:
                    # Use the first edge if multiple exist
                    first_edge_key = list(edge_data.keys())[0]
                    edge_info = edge_data[first_edge_key]

                    edge = NetworkEdge(
                        **{k: v for k, v in edge_info.items() if k in NetworkEdge.__annotations__}
                    )
                    path_edges.append(edge)

            # Determine path type
            path_type = self._determine_path_type(path_nodes, path_edges)

            # Create discovered path
            discovered_path = DiscoveredPath(
                source_ip="",  # Will be set by caller
                destination_ip="",  # Will be set by caller
                path_nodes=path_nodes,
                path_edges=path_edges,
                path_type=path_type,
                hop_count=len(path_nodes) - 1,
                discovery_algorithm=algorithm,
            )

            return discovered_path

        except Exception:
            return None

    def _determine_path_type(
        self, path_nodes: List[NetworkNode], path_edges: List[NetworkEdge]
    ) -> PathType:
        """Determine the type of discovered path."""
        if len(path_nodes) <= 2:
            return PathType.DIRECT

        # Check for cross-account
        accounts = {node.account_id for node in path_nodes if node.account_id}
        if len(accounts) > 1:
            return PathType.CROSS_ACCOUNT

        # Check for cross-segment (CloudWAN)
        segments = {node.segment_name for node in path_nodes if node.segment_name}
        if len(segments) > 1:
            return PathType.CROSS_SEGMENT

        # Check for inspection routing
        if any(node.node_type == "inspection_vpc" for node in path_nodes):
            return PathType.INSPECTION_ROUTED

        return PathType.MULTI_HOP

    async def _enhance_paths_with_analysis(self, paths: List[DiscoveredPath]) -> None:
        """Enhance discovered paths with detailed analysis."""
        enhancement_tasks = [self._enhance_single_path(path) for path in paths]
        await asyncio.gather(*enhancement_tasks, return_exceptions=True)

    async def _enhance_single_path(self, path: DiscoveredPath) -> None:
        """Enhance a single path with detailed analysis."""
        try:
            # Calculate metrics
            path.total_latency_ms = sum(edge.latency_ms for edge in path.path_edges)
            path.total_cost = sum(edge.cost for edge in path.path_edges)
            path.reliability_score = min(edge.reliability for edge in path.path_edges)

            # Calculate bottleneck bandwidth
            bandwidths = [edge.bandwidth_mbps for edge in path.path_edges if edge.bandwidth_mbps]
            if bandwidths:
                path.bottleneck_bandwidth_mbps = min(bandwidths)

            # Analyze CloudWAN policies
            await self._analyze_path_policies(path)

            # Check for inspection points
            await self._identify_inspection_points(path)

            # Calculate confidence score
            path.confidence_score = self._calculate_path_confidence(path)

        except Exception as e:
            path.warnings.append(f"Path enhancement failed: {str(e)}")

    async def _analyze_path_policies(self, path: DiscoveredPath) -> None:
        """Analyze CloudWAN policies affecting the path."""
        try:
            cloudwan_nodes = [
                node
                for node in path.path_nodes
                if node.node_type in ["cloudwan_core", "cloudwan_segment"]
            ]

            if cloudwan_nodes:
                policy_analysis = await self.policy_evaluator.analyze_path_policies(
                    path.path_nodes, path.path_edges
                )

                path.segment_isolation_rules = policy_analysis.get("isolation_rules", [])
                path.network_function_groups = policy_analysis.get("nfg_rules", [])

        except Exception as e:
            path.warnings.append(f"Policy analysis failed: {str(e)}")

    async def _identify_inspection_points(self, path: DiscoveredPath) -> None:
        """Identify inspection points in the path."""
        inspection_points = []

        for node in path.path_nodes:
            if node.node_type == "inspection_vpc":
                inspection_points.append(node.node_id)
            elif "inspection" in node.metadata.get("tags", {}).values():
                inspection_points.append(node.node_id)

        path.inspection_points = inspection_points

    def _calculate_path_confidence(self, path: DiscoveredPath) -> float:
        """Calculate confidence score for path reliability."""
        base_confidence = 0.9

        # Reduce confidence for longer paths
        hop_penalty = min(0.3, path.hop_count * 0.02)

        # Reduce confidence for cross-account paths
        cross_account_penalty = 0.1 if path.path_type == PathType.CROSS_ACCOUNT else 0.0

        # Reduce confidence for warnings
        warning_penalty = min(0.2, len(path.warnings) * 0.05)

        return max(0.1, base_confidence - hop_penalty - cross_account_penalty - warning_penalty)

    async def _rank_paths(self, paths: List[DiscoveredPath]) -> List[DiscoveredPath]:
        """Rank paths based on multiple criteria."""
        if not paths:
            return paths

        # Calculate composite scores
        for path in paths:
            score = 0.0

            # Normalize metrics for scoring
            if self._ranking_weights[PathRankingCriteria.LATENCY] > 0:
                max_latency = max(p.total_latency_ms for p in paths) or 1
                latency_score = 1.0 - (path.total_latency_ms / max_latency)
                score += latency_score * self._ranking_weights[PathRankingCriteria.LATENCY]

            if self._ranking_weights[PathRankingCriteria.COST] > 0:
                max_cost = max(p.total_cost for p in paths) or 1
                cost_score = 1.0 - (path.total_cost / max_cost)
                score += cost_score * self._ranking_weights[PathRankingCriteria.COST]

            if self._ranking_weights[PathRankingCriteria.RELIABILITY] > 0:
                score += (
                    path.reliability_score * self._ranking_weights[PathRankingCriteria.RELIABILITY]
                )

            if self._ranking_weights[PathRankingCriteria.HOP_COUNT] > 0:
                max_hops = max(p.hop_count for p in paths) or 1
                hop_score = 1.0 - (path.hop_count / max_hops)
                score += hop_score * self._ranking_weights[PathRankingCriteria.HOP_COUNT]

            # Store composite score in metadata
            path.path_nodes[0].metadata["composite_score"] = score

        # Sort by composite score (highest first)
        return sorted(
            paths,
            key=lambda p: p.path_nodes[0].metadata.get("composite_score", 0),
            reverse=True,
        )

    def _calculate_path_diversity(self, paths: List[DiscoveredPath]) -> float:
        """Calculate diversity score for multiple paths."""
        if len(paths) <= 1:
            return 0.0

        # Calculate diversity based on unique nodes across paths
        all_nodes = set()
        unique_nodes = set()

        for path in paths:
            path_node_ids = {node.node_id for node in path.path_nodes}
            all_nodes.update(path_node_ids)
            unique_nodes.update(path_node_ids)

        # Diversity = unique nodes / total node occurrences
        total_node_occurrences = sum(len(path.path_nodes) for path in paths)
        if total_node_occurrences == 0:
            return 0.0

        return len(unique_nodes) / total_node_occurrences

    async def _get_core_network_segments(self, core_network_id: str) -> List[Dict[str, Any]]:
        """Get segments for a Core Network."""
        try:
            # This would query the CloudWAN policy document to extract segments
            policy_doc = await self.policy_evaluator.get_core_network_policy(core_network_id)
            return policy_doc.get("segments", [])
        except Exception:
            return []

    async def trace_detailed_path(
        self,
        source_ip: str,
        destination_ip: str,
        include_performance_metrics: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform detailed path tracing with hop-by-hop analysis.

        Args:
            source_ip: Source IP address
            destination_ip: Destination IP address
            include_performance_metrics: Include performance metrics

        Returns:
            Detailed path trace results
        """
        # Discover paths first
        path_analysis = await self.discover_paths(source_ip, destination_ip, max_paths=1)

        if not path_analysis.primary_path:
            return {
                "source_ip": source_ip,
                "destination_ip": destination_ip,
                "status": "no_path_found",
                "trace_hops": [],
            }

        primary_path = path_analysis.primary_path

        # Build detailed hop information
        trace_hops = []
        for i, (node, edge) in enumerate(
            zip(primary_path.path_nodes, primary_path.path_edges + [None])
        ):
            hop_info = {
                "hop_number": i + 1,
                "node_id": node.node_id,
                "node_type": node.node_type,
                "region": node.region,
                "account_id": node.account_id,
                "ip_range": node.ip_range,
                "segment_name": node.segment_name,
            }

            if edge:
                hop_info["next_hop"] = {
                    "connection_id": edge.connection_id,
                    "connection_type": edge.edge_type,
                    "latency_ms": edge.latency_ms,
                    "cost": edge.cost,
                    "reliability": edge.reliability,
                }

            if include_performance_metrics:
                hop_info["performance_metrics"] = {
                    "latency_ms": node.latency_ms,
                    "cost_factor": node.cost_factor,
                    "reliability_score": node.reliability_score,
                    "bandwidth_mbps": node.bandwidth_mbps,
                }

            trace_hops.append(hop_info)

        return {
            "source_ip": source_ip,
            "destination_ip": destination_ip,
            "status": "path_found",
            "path_type": primary_path.path_type.value,
            "total_hops": primary_path.hop_count,
            "total_latency_ms": primary_path.total_latency_ms,
            "total_cost": primary_path.total_cost,
            "reliability_score": primary_path.reliability_score,
            "confidence_score": primary_path.confidence_score,
            "trace_hops": trace_hops,
            "inspection_points": primary_path.inspection_points,
            "warnings": primary_path.warnings,
            "analysis_time_ms": path_analysis.total_analysis_time_ms,
        }

    async def cleanup(self):
        """Cleanup resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
        self._path_cache.clear()
        self._topology_cache.clear()
        self._topology_graph.clear()
