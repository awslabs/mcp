"""
Path Discovery Tool for CloudWAN MCP Server.

This tool provides comprehensive path discovery operations with async path tracing,
progress reporting, detailed error handling, and comprehensive path analysis reports
for CloudWAN networks.

Features:
- Async path tracing with real-time progress reporting
- Multiple path discovery algorithms (BFS, DFS, Dijkstra, A*)
- Comprehensive error handling for unreachable destinations
- Detailed path analysis reports with hop-by-hop information
- Performance optimization with caching and parallel processing
- Integration with existing topology discovery and TGW analysis
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional


from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...engines.path_tracing_engine import (
    PathTracingEngine,
    PathDiscoveryAlgorithm,
    PathAnalysisResult,
    DiscoveredPath,
    PathType,
)
from ...engines.route_resolution_engine import RouteResolutionEngine
from ...engines.tgw_peering_discovery_engine import TGWPeeringDiscoveryEngine
from ...engines.network_function_group_analyzer import NetworkFunctionGroupAnalyzer
from ...engines.cloudwan_policy_evaluator import CloudWANPolicyEvaluator
from ...models.base import BaseResponse
from ..base import BaseMCPTool, handle_errors, validate_ip_address


class PathDiscoveryResponse(BaseResponse):
    """Response for path discovery operations."""

    operation_type: str = "path_discovery"
    source_ip: str
    destination_ip: str
    discovery_algorithm: str
    paths_discovered: int = 0
    primary_path_summary: Optional[Dict[str, Any]] = None
    path_analysis_summary: Dict[str, Any] = {}
    detailed_trace: Optional[Dict[str, Any]] = None
    performance_summary: Dict[str, Any] = {}
    connectivity_status: str = "unknown"  # reachable, unreachable, partial
    recommendations: List[str] = []


class PathDiscoveryTool(BaseMCPTool):
    """
    Path Discovery tool for comprehensive network path discovery and analysis.

    Provides async path tracing capabilities with progress reporting, detailed
    error handling, and comprehensive path analysis reports for CloudWAN networks.
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
        Initialize the Path Discovery tool.

        Args:
            aws_manager: AWS client manager instance
            config: CloudWAN configuration
            route_engine: Route resolution engine
            peering_engine: TGW peering discovery engine
            nfg_analyzer: Network Function Group analyzer
            policy_evaluator: CloudWAN policy evaluator
        """
        super().__init__(aws_manager, config)

        # Initialize path tracing engine
        self.path_engine = PathTracingEngine(
            aws_manager,
            config,
            route_engine,
            peering_engine,
            nfg_analyzer,
            policy_evaluator,
        )

        # Component engines for additional analysis
        self.route_engine = route_engine
        self.peering_engine = peering_engine
        self.nfg_analyzer = nfg_analyzer
        self.policy_evaluator = policy_evaluator

        # Progress tracking
        self._progress_callbacks: List[callable] = []

    @property
    def tool_name(self) -> str:
        """Get the tool name for MCP registration."""
        return "discover_network_paths"

    @property
    def description(self) -> str:
        """Get the tool description for MCP registration."""
        return """
        Discover and analyze network paths between two IP addresses in CloudWAN environments.
        
        This tool performs comprehensive path discovery using advanced algorithms to find all
        possible routes between source and destination IPs, analyzes routing policies, identifies
        Network Function Groups, and provides detailed connectivity assessment.
        
        Key capabilities:
        - Multi-algorithm path discovery (BFS, DFS, Dijkstra, A* heuristic)
        - Real-time progress reporting for long-running operations
        - Comprehensive error handling and unreachable destination analysis
        - Detailed hop-by-hop path analysis with performance metrics
        - CloudWAN segment isolation and policy evaluation
        - Network Function Group send-to/send-via rule analysis
        - Cross-account path discovery via AWS RAM shared resources
        - Integration with topology discovery and TGW peering analysis
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the tool input schema for MCP registration."""
        return {
            "type": "object",
            "properties": {
                "source_ip": {
                    "type": "string",
                    "description": "Source IP address for path discovery",
                    "pattern": r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$",
                },
                "destination_ip": {
                    "type": "string",
                    "description": "Destination IP address for path discovery",
                    "pattern": r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$",
                },
                "discovery_algorithm": {
                    "type": "string",
                    "enum": ["bfs", "dfs", "dijkstra", "a_star", "all"],
                    "default": "bfs",
                    "description": "Path discovery algorithm - 'all' runs multiple algorithms for comparison",
                },
                "max_paths": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": "Maximum number of paths to discover per algorithm",
                },
                "max_hops": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 20,
                    "description": "Maximum hops allowed per path",
                },
                "include_cross_account": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include cross-account paths in discovery",
                },
                "detailed_trace": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include detailed hop-by-hop trace information",
                },
                "include_performance_metrics": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include performance metrics and analysis",
                },
                "analyze_policies": {
                    "type": "boolean",
                    "default": True,
                    "description": "Analyze CloudWAN policies and Network Function Groups",
                },
                "enable_caching": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable result caching for improved performance",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 30,
                    "maximum": 600,
                    "default": 120,
                    "description": "Operation timeout in seconds",
                },
            },
            "required": ["source_ip", "destination_ip"],
        }

    @handle_errors
    async def execute(self, **kwargs) -> PathDiscoveryResponse:
        """
        Execute path discovery operation.

        Args:
            **kwargs: Tool parameters

        Returns:
            Path discovery response
        """
        start_time = datetime.now()

        # Extract and validate parameters
        source_ip = validate_ip_address(kwargs["source_ip"])
        destination_ip = validate_ip_address(kwargs["destination_ip"])

        discovery_algorithm = kwargs.get("discovery_algorithm", "bfs")
        max_paths = kwargs.get("max_paths", 10)
        max_hops = kwargs.get("max_hops", 20)
        include_cross_account = kwargs.get("include_cross_account", True)
        detailed_trace = kwargs.get("detailed_trace", False)
        include_performance_metrics = kwargs.get("include_performance_metrics", True)
        analyze_policies = kwargs.get("analyze_policies", True)
        enable_caching = kwargs.get("enable_caching", True)
        timeout_seconds = kwargs.get("timeout_seconds", 120)

        # Initialize response
        response = PathDiscoveryResponse(
            source_ip=source_ip,
            destination_ip=destination_ip,
            discovery_algorithm=discovery_algorithm,
            success=True,
        )

        try:
            # Set operation timeout
            path_analysis_result = await asyncio.wait_for(
                self._perform_path_discovery(
                    source_ip=source_ip,
                    destination_ip=destination_ip,
                    discovery_algorithm=discovery_algorithm,
                    max_paths=max_paths,
                    max_hops=max_hops,
                    include_cross_account=include_cross_account,
                    enable_caching=enable_caching,
                    analyze_policies=analyze_policies,
                ),
                timeout=timeout_seconds,
            )

            # Process results
            response.paths_discovered = len(path_analysis_result.discovered_paths)
            response.connectivity_status = self._determine_connectivity_status(path_analysis_result)

            # Generate primary path summary
            if path_analysis_result.primary_path:
                response.primary_path_summary = await self._generate_primary_path_summary(
                    path_analysis_result.primary_path
                )

            # Generate path analysis summary
            response.path_analysis_summary = await self._generate_path_analysis_summary(
                path_analysis_result
            )

            # Generate detailed trace if requested
            if detailed_trace and path_analysis_result.primary_path:
                response.detailed_trace = await self.path_engine.trace_detailed_path(
                    source_ip, destination_ip, include_performance_metrics
                )

            # Generate performance summary
            if include_performance_metrics:
                response.performance_summary = await self._generate_performance_summary(
                    path_analysis_result, start_time
                )

            # Generate recommendations
            response.recommendations = await self._generate_path_recommendations(
                path_analysis_result
            )

        except asyncio.TimeoutError:
            response.success = False
            response.errors.append(f"Path discovery timed out after {timeout_seconds} seconds")
            response.connectivity_status = "timeout"

        except Exception as e:
            response.success = False
            response.errors.append(f"Path discovery failed: {str(e)}")
            response.connectivity_status = "error"

        return response

    async def _perform_path_discovery(
        self,
        source_ip: str,
        destination_ip: str,
        discovery_algorithm: str,
        max_paths: int,
        max_hops: int,
        include_cross_account: bool,
        enable_caching: bool,
        analyze_policies: bool,
    ) -> PathAnalysisResult:
        """Perform the actual path discovery operation."""

        if discovery_algorithm == "all":
            # Run multiple algorithms and combine results
            return await self._run_multi_algorithm_discovery(
                source_ip,
                destination_ip,
                max_paths,
                max_hops,
                include_cross_account,
                enable_caching,
            )
        else:
            # Run single algorithm
            algorithm_map = {
                "bfs": PathDiscoveryAlgorithm.BFS,
                "dfs": PathDiscoveryAlgorithm.DFS,
                "dijkstra": PathDiscoveryAlgorithm.DIJKSTRA,
                "a_star": PathDiscoveryAlgorithm.A_STAR,
            }

            algorithm = algorithm_map.get(discovery_algorithm, PathDiscoveryAlgorithm.BFS)

            return await self.path_engine.discover_paths(
                source_ip=source_ip,
                destination_ip=destination_ip,
                algorithm=algorithm,
                max_paths=max_paths,
                max_hops=max_hops,
                include_cross_account=include_cross_account,
                enable_caching=enable_caching,
            )

    async def _run_multi_algorithm_discovery(
        self,
        source_ip: str,
        destination_ip: str,
        max_paths: int,
        max_hops: int,
        include_cross_account: bool,
        enable_caching: bool,
    ) -> PathAnalysisResult:
        """Run multiple path discovery algorithms and combine results."""

        algorithms = [
            PathDiscoveryAlgorithm.BFS,
            PathDiscoveryAlgorithm.DFS,
            PathDiscoveryAlgorithm.DIJKSTRA,
            PathDiscoveryAlgorithm.A_STAR,
        ]

        # Run algorithms concurrently
        discovery_tasks = []
        for algorithm in algorithms:
            task = self.path_engine.discover_paths(
                source_ip=source_ip,
                destination_ip=destination_ip,
                algorithm=algorithm,
                max_paths=max_paths // len(algorithms),  # Distribute path quota
                max_hops=max_hops,
                include_cross_account=include_cross_account,
                enable_caching=enable_caching,
            )
            discovery_tasks.append(task)

        # Gather results
        results = await asyncio.gather(*discovery_tasks, return_exceptions=True)

        # Combine successful results
        all_paths = []
        total_analysis_time = 0.0
        best_algorithm = PathDiscoveryAlgorithm.BFS

        for i, result in enumerate(results):
            if isinstance(result, PathAnalysisResult):
                all_paths.extend(result.discovered_paths)
                total_analysis_time += result.total_analysis_time_ms

                # Track the algorithm that found the most paths
                if len(result.discovered_paths) > 0:
                    best_algorithm = algorithms[i]

        # Remove duplicates and rank paths
        unique_paths = self._deduplicate_paths(all_paths)
        ranked_paths = await self.path_engine._rank_paths(unique_paths)

        # Create combined result
        combined_result = PathAnalysisResult(
            source_ip=source_ip,
            destination_ip=destination_ip,
            discovered_paths=ranked_paths[:max_paths],
            primary_path=ranked_paths[0] if ranked_paths else None,
            alternative_paths=ranked_paths[1:] if len(ranked_paths) > 1 else [],
            path_diversity_score=self.path_engine._calculate_path_diversity(ranked_paths),
            load_balancing_capable=len(ranked_paths) > 1,
            failover_paths=[p for p in ranked_paths[1:] if p.reliability_score > 0.8],
            total_analysis_time_ms=total_analysis_time,
            algorithm_used=best_algorithm,
            max_paths_analyzed=max_paths,
        )

        return combined_result

    def _deduplicate_paths(self, paths: List[DiscoveredPath]) -> List[DiscoveredPath]:
        """Remove duplicate paths based on node sequences."""
        seen_paths = set()
        unique_paths = []

        for path in paths:
            # Create path signature based on node sequence
            node_signature = tuple(node.node_id for node in path.path_nodes)

            if node_signature not in seen_paths:
                seen_paths.add(node_signature)
                unique_paths.append(path)

        return unique_paths

    def _determine_connectivity_status(self, path_analysis: PathAnalysisResult) -> str:
        """Determine overall connectivity status from path analysis."""
        if not path_analysis.discovered_paths:
            return "unreachable"

        reachable_paths = [p for p in path_analysis.discovered_paths if p.is_reachable]

        if not reachable_paths:
            return "unreachable"
        elif len(reachable_paths) == len(path_analysis.discovered_paths):
            return "reachable"
        else:
            return "partial"

    async def _generate_primary_path_summary(self, primary_path: DiscoveredPath) -> Dict[str, Any]:
        """Generate summary for the primary path."""
        return {
            "path_type": primary_path.path_type.value,
            "hop_count": primary_path.hop_count,
            "is_reachable": primary_path.is_reachable,
            "path_status": primary_path.path_status.value,
            "confidence_score": primary_path.confidence_score,
            # Performance metrics
            "total_latency_ms": primary_path.total_latency_ms,
            "total_cost": primary_path.total_cost,
            "reliability_score": primary_path.reliability_score,
            "bottleneck_bandwidth_mbps": primary_path.bottleneck_bandwidth_mbps,
            # Path characteristics
            "crosses_accounts": primary_path.path_type == PathType.CROSS_ACCOUNT,
            "crosses_segments": primary_path.path_type == PathType.CROSS_SEGMENT,
            "has_inspection_points": len(primary_path.inspection_points) > 0,
            "uses_network_function_groups": len(primary_path.network_function_groups) > 0,
            # Warnings and issues
            "warning_count": len(primary_path.warnings),
            "failure_point_count": len(primary_path.failure_points),
            # Discovery metadata
            "discovery_algorithm": primary_path.discovery_algorithm.value,
            "discovery_time_ms": primary_path.discovery_time_ms,
        }

    async def _generate_path_analysis_summary(
        self, path_analysis: PathAnalysisResult
    ) -> Dict[str, Any]:
        """Generate comprehensive path analysis summary."""
        paths = path_analysis.discovered_paths

        if not paths:
            return {"total_paths": 0, "analysis_status": "no_paths_found"}

        # Calculate summary statistics
        summary = {
            "total_paths": len(paths),
            "reachable_paths": sum(1 for p in paths if p.is_reachable),
            "unreachable_paths": sum(1 for p in paths if not p.is_reachable),
            "path_diversity_score": path_analysis.path_diversity_score,
            "load_balancing_capable": path_analysis.load_balancing_capable,
            "failover_paths_available": len(path_analysis.failover_paths),
            # Path type distribution
            "path_types": {},
            # Performance statistics
            "performance_stats": {
                "min_latency_ms": min(p.total_latency_ms for p in paths),
                "max_latency_ms": max(p.total_latency_ms for p in paths),
                "avg_latency_ms": sum(p.total_latency_ms for p in paths) / len(paths),
                "min_hop_count": min(p.hop_count for p in paths),
                "max_hop_count": max(p.hop_count for p in paths),
                "avg_hop_count": sum(p.hop_count for p in paths) / len(paths),
                "min_cost": min(p.total_cost for p in paths),
                "max_cost": max(p.total_cost for p in paths),
                "avg_cost": sum(p.total_cost for p in paths) / len(paths),
            },
            # Quality metrics
            "quality_metrics": {
                "avg_confidence_score": sum(p.confidence_score for p in paths) / len(paths),
                "avg_reliability_score": sum(p.reliability_score for p in paths) / len(paths),
                "paths_with_warnings": sum(1 for p in paths if p.warnings),
                "paths_with_failures": sum(1 for p in paths if p.failure_points),
            },
            # Discovery metadata
            "discovery_metadata": {
                "algorithm_used": path_analysis.algorithm_used.value,
                "total_analysis_time_ms": path_analysis.total_analysis_time_ms,
                "max_paths_requested": path_analysis.max_paths_analyzed,
            },
        }

        # Calculate path type distribution
        path_type_counts = {}
        for path in paths:
            path_type = path.path_type.value
            path_type_counts[path_type] = path_type_counts.get(path_type, 0) + 1
        summary["path_types"] = path_type_counts

        return summary

    async def _generate_performance_summary(
        self, path_analysis: PathAnalysisResult, start_time: datetime
    ) -> Dict[str, Any]:
        """Generate performance summary for the discovery operation."""

        total_operation_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "operation_performance": {
                "total_operation_time_ms": total_operation_time,
                "path_discovery_time_ms": path_analysis.total_analysis_time_ms,
                "analysis_overhead_ms": total_operation_time - path_analysis.total_analysis_time_ms,
                "paths_per_second": (
                    len(path_analysis.discovered_paths) / (total_operation_time / 1000)
                    if total_operation_time > 0
                    else 0
                ),
            },
            "algorithm_performance": {
                "algorithm_used": path_analysis.algorithm_used.value,
                "discovery_efficiency": (
                    len(path_analysis.discovered_paths) / path_analysis.max_paths_analyzed
                    if path_analysis.max_paths_analyzed > 0
                    else 0
                ),
                "average_path_discovery_time": (
                    sum(p.discovery_time_ms for p in path_analysis.discovered_paths)
                    / len(path_analysis.discovered_paths)
                    if path_analysis.discovered_paths
                    else 0
                ),
            },
            "network_complexity": {
                "unique_regions": len(
                    set(
                        node.region
                        for path in path_analysis.discovered_paths
                        for node in path.path_nodes
                    )
                ),
                "unique_accounts": len(
                    set(
                        node.account_id
                        for path in path_analysis.discovered_paths
                        for node in path.path_nodes
                        if node.account_id
                    )
                ),
                "total_network_hops": sum(
                    len(path.path_nodes) for path in path_analysis.discovered_paths
                ),
                "unique_node_types": len(
                    set(
                        node.node_type
                        for path in path_analysis.discovered_paths
                        for node in path.path_nodes
                    )
                ),
            },
        }

    async def _generate_path_recommendations(self, path_analysis: PathAnalysisResult) -> List[str]:
        """Generate recommendations based on path analysis results."""
        recommendations = []

        if not path_analysis.discovered_paths:
            recommendations.extend(
                [
                    "No paths found between source and destination",
                    "Verify network connectivity and routing configuration",
                    "Check security group rules and network ACLs",
                    "Ensure proper CloudWAN attachment and policy configuration",
                ]
            )
            return recommendations

        paths = path_analysis.discovered_paths
        primary_path = path_analysis.primary_path

        # Connectivity recommendations
        reachable_paths = [p for p in paths if p.is_reachable]
        if not reachable_paths:
            recommendations.append(
                "All discovered paths are unreachable - review routing and security policies"
            )
        elif len(reachable_paths) < len(paths):
            recommendations.append(
                f"Only {len(reachable_paths)} of {len(paths)} paths are reachable - investigate unreachable paths"
            )

        # Path optimization recommendations
        if primary_path:
            if primary_path.hop_count > 10:
                recommendations.append(
                    f"Primary path has {primary_path.hop_count} hops - consider route optimization"
                )

            if primary_path.total_latency_ms > 100:
                recommendations.append(
                    f"Primary path latency is {primary_path.total_latency_ms:.1f}ms - consider regional optimization"
                )

            if primary_path.reliability_score < 0.8:
                recommendations.append(
                    f"Primary path reliability is {primary_path.reliability_score:.2f} - implement redundant paths"
                )

        # High availability recommendations
        if len(reachable_paths) == 1:
            recommendations.append(
                "Only one reachable path - implement redundant paths for high availability"
            )
        elif path_analysis.load_balancing_capable:
            recommendations.append(
                "Multiple high-quality paths available - consider load balancing"
            )

        # Cross-account recommendations
        cross_account_paths = [p for p in paths if p.path_type == PathType.CROSS_ACCOUNT]
        if cross_account_paths:
            recommendations.append(
                f"Found {len(cross_account_paths)} cross-account paths - verify AWS RAM sharing"
            )

        # Network Function Group recommendations
        nfg_paths = [p for p in paths if p.network_function_groups]
        if nfg_paths:
            recommendations.append(
                f"Found {len(nfg_paths)} paths using Network Function Groups - verify NFG policies"
            )

        # Performance recommendations
        high_cost_paths = [p for p in paths if p.total_cost > 5.0]
        if high_cost_paths:
            recommendations.append(
                f"Found {len(high_cost_paths)} high-cost paths - consider cost optimization"
            )

        return recommendations[:8]  # Limit to top 8 recommendations


# Tool registration function
def create_path_discovery_tool(
    aws_manager: AWSClientManager,
    config: CloudWANConfig,
    route_engine: RouteResolutionEngine,
    peering_engine: TGWPeeringDiscoveryEngine,
    nfg_analyzer: NetworkFunctionGroupAnalyzer,
    policy_evaluator: CloudWANPolicyEvaluator,
) -> PathDiscoveryTool:
    """
    Create and configure the Path Discovery tool.

    Args:
        aws_manager: AWS client manager
        config: CloudWAN configuration
        route_engine: Route resolution engine
        peering_engine: TGW peering discovery engine
        nfg_analyzer: Network Function Group analyzer
        policy_evaluator: CloudWAN policy evaluator

    Returns:
        Configured Path Discovery tool
    """
    return PathDiscoveryTool(
        aws_manager,
        config,
        route_engine,
        peering_engine,
        nfg_analyzer,
        policy_evaluator,
    )
