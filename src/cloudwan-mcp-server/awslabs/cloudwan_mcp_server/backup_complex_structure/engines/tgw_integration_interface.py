"""
Transit Gateway Integration Interface.

This module provides a unified interface that integrates all Transit Gateway
analysis engines with the existing foundation engines and CloudWAN engines,
creating a comprehensive TGW analysis ecosystem.

Features:
- Unified interface for all TGW analysis capabilities
- Integration with foundation engines (Agent 1) and CloudWAN engines (Agent 2)
- Orchestrated multi-engine analysis workflows
- Performance optimization across engine boundaries
- Centralized error handling and result aggregation
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig

# Foundation engines
from .ip_resolution_engine import IPResolutionEngine
from .multi_region_engine import MultiRegionProcessingEngine

# Transit Gateway engines
from .transit_gateway_route_engine import TransitGatewayRouteEngine, RouteTableAnalysis
from .tgw_peering_discovery_engine import (
    TGWPeeringDiscoveryEngine,
    TGWPeeringConnection,
)
from .route_resolution_engine import RouteResolutionEngine, RouteResolutionResult
from .cross_account_tgw_analyzer import (
    CrossAccountTGWAnalyzer,
    CrossAccountPeeringAnalysis,
)
from .tgw_performance_analyzer import TGWPerformanceAnalyzer


@dataclass
class ComprehensiveTGWAnalysis:
    """Comprehensive TGW analysis results combining all engines."""

    # Basic information
    transit_gateway_id: str
    region: str
    analysis_timestamp: datetime

    # Route analysis
    route_analysis: Optional[List[RouteTableAnalysis]] = None

    # Peering analysis
    peering_analysis: Optional[List[TGWPeeringConnection]] = None

    # Route resolution
    route_resolution_samples: List[RouteResolutionResult] = field(default_factory=list)

    # Cross-account analysis
    cross_account_analysis: List[CrossAccountPeeringAnalysis] = field(default_factory=list)

    # Performance analysis
    performance_analysis: Optional[Dict[str, Any]] = None

    # Integration insights
    connectivity_matrix: Dict[str, Dict[str, str]] = field(default_factory=dict)
    optimization_recommendations: List[str] = field(default_factory=list)
    security_findings: List[Dict[str, Any]] = field(default_factory=list)

    # Analysis metadata
    engines_used: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    confidence_score: float = 0.0


class TGWIntegrationInterface:
    """
    Unified interface for comprehensive Transit Gateway analysis.

    Orchestrates multiple analysis engines to provide complete TGW insights
    including routing, peering, performance, and security analysis.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """
        Initialize the integration interface.

        Args:
            aws_manager: AWS client manager instance
            config: CloudWAN configuration
        """
        self.aws_manager = aws_manager
        self.config = config

        # Initialize foundation engines
        self.ip_resolution_engine = IPResolutionEngine(aws_manager, config)
        self.multi_region_engine = MultiRegionProcessingEngine(aws_manager, config)

        # Initialize TGW analysis engines
        self.route_engine = TransitGatewayRouteEngine(aws_manager, config)
        self.peering_engine = TGWPeeringDiscoveryEngine(aws_manager, config)
        self.resolution_engine = RouteResolutionEngine(
            aws_manager, config, self.route_engine, self.peering_engine
        )
        self.cross_account_analyzer = CrossAccountTGWAnalyzer(
            aws_manager, config, self.peering_engine, self.route_engine
        )
        self.performance_analyzer = TGWPerformanceAnalyzer(
            aws_manager, config, self.peering_engine, self.route_engine
        )

    async def perform_comprehensive_analysis(
        self,
        transit_gateway_id: str,
        region: str,
        analysis_options: Optional[Dict[str, Any]] = None,
    ) -> ComprehensiveTGWAnalysis:
        """
        Perform comprehensive TGW analysis using all available engines.

        Args:
            transit_gateway_id: Transit Gateway ID to analyze
            region: AWS region
            analysis_options: Optional analysis configuration

        Returns:
            Comprehensive analysis results
        """
        start_time = datetime.now()

        # Set default analysis options
        if analysis_options is None:
            analysis_options = {
                "include_route_analysis": True,
                "include_peering_analysis": True,
                "include_route_resolution": True,
                "include_cross_account_analysis": True,
                "include_performance_analysis": True,
                "route_resolution_samples": ["10.0.0.1", "172.16.1.1", "192.168.1.1"],
                "max_peering_hops": 3,
                "performance_time_range_hours": 24,
            }

        # Initialize analysis result
        analysis = ComprehensiveTGWAnalysis(
            transit_gateway_id=transit_gateway_id,
            region=region,
            analysis_timestamp=start_time,
        )

        try:
            # Execute analysis engines in parallel where possible
            analysis_tasks = []

            # Route analysis
            if analysis_options.get("include_route_analysis", True):
                route_task = self._perform_route_analysis(transit_gateway_id, region)
                analysis_tasks.append(("route_analysis", route_task))
                analysis.engines_used.append("TransitGatewayRouteEngine")

            # Peering analysis
            if analysis_options.get("include_peering_analysis", True):
                peering_task = self._perform_peering_analysis(
                    transit_gateway_id,
                    region,
                    analysis_options.get("max_peering_hops", 3),
                )
                analysis_tasks.append(("peering_analysis", peering_task))
                analysis.engines_used.append("TGWPeeringDiscoveryEngine")

            # Performance analysis
            if analysis_options.get("include_performance_analysis", True):
                performance_task = self._perform_performance_analysis(
                    transit_gateway_id,
                    region,
                    analysis_options.get("performance_time_range_hours", 24),
                )
                analysis_tasks.append(("performance_analysis", performance_task))
                analysis.engines_used.append("TGWPerformanceAnalyzer")

            # Execute parallel tasks
            parallel_results = await asyncio.gather(
                *[task for _, task in analysis_tasks], return_exceptions=True
            )

            # Process parallel results
            for i, (analysis_type, _) in enumerate(analysis_tasks):
                result = parallel_results[i]
                if not isinstance(result, Exception):
                    setattr(analysis, analysis_type, result)

            # Sequential dependent analyses
            if analysis_options.get("include_route_resolution", True) and analysis.peering_analysis:
                analysis.route_resolution_samples = await self._perform_route_resolution(
                    transit_gateway_id,
                    region,
                    analysis_options.get("route_resolution_samples", []),
                )
                analysis.engines_used.append("RouteResolutionEngine")

            if (
                analysis_options.get("include_cross_account_analysis", True)
                and analysis.peering_analysis
            ):
                analysis.cross_account_analysis = await self._perform_cross_account_analysis(
                    transit_gateway_id, region
                )
                analysis.engines_used.append("CrossAccountTGWAnalyzer")

            # Generate integration insights
            await self._generate_integration_insights(analysis)

            # Calculate processing time and confidence
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            analysis.processing_time_ms = processing_time
            analysis.confidence_score = self._calculate_analysis_confidence(analysis)

            return analysis

        except Exception as e:
            # Ensure we return a valid analysis even if some components fail
            analysis.optimization_recommendations.append(f"Analysis partially failed: {str(e)}")
            analysis.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            return analysis

    async def _perform_route_analysis(
        self, transit_gateway_id: str, region: str
    ) -> List[RouteTableAnalysis]:
        """Perform comprehensive route analysis."""
        try:
            return await self.route_engine.analyze_route_tables(
                transit_gateway_id=transit_gateway_id,
                region=region,
                include_associations=True,
            )
        except Exception:
            return []

    async def _perform_peering_analysis(
        self, transit_gateway_id: str, region: str, max_hops: int
    ) -> List[TGWPeeringConnection]:
        """Perform comprehensive peering analysis."""
        try:
            return await self.peering_engine.discover_peering_connections(
                transit_gateway_id=transit_gateway_id,
                region=region,
                max_hop_depth=max_hops,
                include_cross_account=True,
            )
        except Exception:
            return []

    async def _perform_performance_analysis(
        self, transit_gateway_id: str, region: str, time_range_hours: int
    ) -> Dict[str, Any]:
        """Perform comprehensive performance analysis."""
        try:
            return await self.performance_analyzer.analyze_tgw_performance(
                transit_gateway_id=transit_gateway_id,
                region=region,
                time_range_hours=time_range_hours,
                include_peering_analysis=True,
                include_optimization_recommendations=True,
            )
        except Exception:
            return {}

    async def _perform_route_resolution(
        self, transit_gateway_id: str, region: str, sample_ips: List[str]
    ) -> List[RouteResolutionResult]:
        """Perform route resolution for sample IPs."""
        resolution_results = []

        for ip in sample_ips:
            try:
                result = await self.resolution_engine.resolve_route(
                    target_ip=ip, source_tgw_id=transit_gateway_id, source_region=region
                )
                resolution_results.append(result)
            except Exception:
                continue

        return resolution_results

    async def _perform_cross_account_analysis(
        self, transit_gateway_id: str, region: str
    ) -> List[CrossAccountPeeringAnalysis]:
        """Perform cross-account analysis."""
        try:
            return await self.cross_account_analyzer.analyze_cross_account_peering(
                transit_gateway_id=transit_gateway_id,
                region=region,
                include_trust_analysis=True,
                include_security_analysis=True,
                include_compliance_check=True,
            )
        except Exception:
            return []

    async def _generate_integration_insights(self, analysis: ComprehensiveTGWAnalysis):
        """Generate insights by integrating results from multiple engines."""

        # Build connectivity matrix
        if analysis.peering_analysis and analysis.route_resolution_samples:
            analysis.connectivity_matrix = self._build_connectivity_matrix(
                analysis.peering_analysis, analysis.route_resolution_samples
            )

        # Generate optimization recommendations
        analysis.optimization_recommendations = self._generate_integrated_recommendations(analysis)

        # Identify security findings
        analysis.security_findings = self._identify_security_findings(analysis)

    def _build_connectivity_matrix(
        self,
        peering_connections: List[TGWPeeringConnection],
        route_resolutions: List[RouteResolutionResult],
    ) -> Dict[str, Dict[str, str]]:
        """Build connectivity matrix showing reachability between TGWs."""
        matrix = {}

        # Extract unique TGW IDs from peering connections
        tgw_ids = set()
        for conn in peering_connections:
            tgw_ids.add(conn.requester_tgw_id)
            tgw_ids.add(conn.accepter_tgw_id)

        # Initialize matrix
        for source_tgw in tgw_ids:
            matrix[source_tgw] = {}
            for dest_tgw in tgw_ids:
                if source_tgw == dest_tgw:
                    matrix[source_tgw][dest_tgw] = "direct"
                else:
                    matrix[source_tgw][dest_tgw] = "unknown"

        # Update matrix based on peering connections
        for conn in peering_connections:
            if conn.state.value == "available":
                matrix[conn.requester_tgw_id][conn.accepter_tgw_id] = "peered"
                matrix[conn.accepter_tgw_id][conn.requester_tgw_id] = "peered"

        # Update matrix based on route resolution results
        for resolution in route_resolutions:
            if len(resolution.total_path) > 1:
                for i in range(len(resolution.total_path) - 1):
                    source = resolution.total_path[i]
                    dest = resolution.total_path[i + 1]
                    if source in matrix and dest in matrix[source]:
                        matrix[source][dest] = "routable"

        return matrix

    def _generate_integrated_recommendations(self, analysis: ComprehensiveTGWAnalysis) -> List[str]:
        """Generate recommendations by analyzing results from all engines."""
        recommendations = []

        # Route optimization recommendations
        if analysis.route_analysis:
            route_conflicts = sum(len(rt.route_conflicts) for rt in analysis.route_analysis)
            if route_conflicts > 0:
                recommendations.append(
                    f"Resolve {route_conflicts} route conflicts to improve routing efficiency"
                )

        # Peering optimization recommendations
        if analysis.peering_analysis:
            cross_region_peering = sum(
                1 for conn in analysis.peering_analysis if conn.is_cross_region
            )
            if cross_region_peering > 0:
                recommendations.append(
                    f"Review {cross_region_peering} cross-region peering connections for latency optimization"
                )

        # Performance-based recommendations
        if analysis.performance_analysis:
            perf_summary = analysis.performance_analysis.get("performance_summary", {})
            if perf_summary.get("bandwidth_utilization_percent", 0) > 80:
                recommendations.append(
                    "High bandwidth utilization detected - consider load balancing or capacity expansion"
                )

        # Cross-account security recommendations
        if analysis.cross_account_analysis:
            for cross_account in analysis.cross_account_analysis:
                recommendations.extend(cross_account.recommendations)

        # Integration-specific recommendations
        if analysis.connectivity_matrix:
            unreachable_pairs = []
            for source, destinations in analysis.connectivity_matrix.items():
                for dest, status in destinations.items():
                    if status == "unknown" and source != dest:
                        unreachable_pairs.append((source, dest))

            if unreachable_pairs:
                recommendations.append(
                    f"Investigate {len(unreachable_pairs)} potentially unreachable TGW pairs"
                )

        return list(set(recommendations))  # Remove duplicates

    def _identify_security_findings(
        self, analysis: ComprehensiveTGWAnalysis
    ) -> List[Dict[str, Any]]:
        """Identify security findings across all analysis results."""
        findings = []

        # Cross-account security findings
        for cross_account in analysis.cross_account_analysis:
            for finding in cross_account.compliance_findings:
                findings.append(
                    {
                        "source": "cross_account_analysis",
                        "severity": finding.get("status", "unknown"),
                        "finding": finding.get("description", ""),
                        "recommendation": finding.get("recommendation", ""),
                    }
                )

        # Route-based security findings
        if analysis.route_analysis:
            for rt_analysis in analysis.route_analysis:
                # Check for overly permissive routes (0.0.0.0/0)
                default_routes = [
                    route
                    for route in rt_analysis.route_entries
                    if route.destination_cidr == "0.0.0.0/0"
                ]
                if default_routes:
                    findings.append(
                        {
                            "source": "route_analysis",
                            "severity": "warning",
                            "finding": f"Default route (0.0.0.0/0) found in route table {rt_analysis.route_table_id}",
                            "recommendation": "Review default route necessity and scope",
                        }
                    )

        # Performance-based security findings
        if analysis.performance_analysis:
            perf_summary = analysis.performance_analysis.get("performance_summary", {})
            if perf_summary.get("critical_issues_count", 0) > 0:
                findings.append(
                    {
                        "source": "performance_analysis",
                        "severity": "critical",
                        "finding": "Critical performance issues detected",
                        "recommendation": "Investigate performance issues that may indicate security incidents",
                    }
                )

        return findings

    def _calculate_analysis_confidence(self, analysis: ComprehensiveTGWAnalysis) -> float:
        """Calculate overall confidence score for the analysis."""
        confidence_factors = []

        # Route analysis confidence
        if analysis.route_analysis:
            route_confidence = min(100.0, len(analysis.route_analysis) * 20)  # Max 100%
            confidence_factors.append(route_confidence)

        # Peering analysis confidence
        if analysis.peering_analysis is not None:
            peering_confidence = 90.0 if analysis.peering_analysis else 70.0
            confidence_factors.append(peering_confidence)

        # Route resolution confidence
        if analysis.route_resolution_samples:
            successful_resolutions = sum(
                1 for res in analysis.route_resolution_samples if res.confidence_score > 0.7
            )
            resolution_confidence = (
                successful_resolutions / len(analysis.route_resolution_samples)
            ) * 100
            confidence_factors.append(resolution_confidence)

        # Performance analysis confidence
        if analysis.performance_analysis:
            performance_confidence = 85.0  # High confidence for CloudWatch metrics
            confidence_factors.append(performance_confidence)

        # Cross-account analysis confidence
        if analysis.cross_account_analysis:
            cross_account_confidence = 80.0  # Moderate confidence due to access limitations
            confidence_factors.append(cross_account_confidence)

        # Calculate weighted average
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 50.0  # Low confidence if no analysis completed

    async def enhance_existing_tool_response(
        self, tool_response: Any, transit_gateway_id: str, region: str
    ) -> Any:
        """
        Enhance existing MCP tool responses with integrated engine insights.

        Args:
            tool_response: Original tool response
            transit_gateway_id: TGW ID for enhancement
            region: AWS region

        Returns:
            Enhanced response with additional insights
        """
        try:
            # Perform lightweight analysis for enhancement
            quick_analysis = await self.perform_comprehensive_analysis(
                transit_gateway_id=transit_gateway_id,
                region=region,
                analysis_options={
                    "include_route_analysis": True,
                    "include_peering_analysis": True,
                    "include_route_resolution": False,
                    "include_cross_account_analysis": False,
                    "include_performance_analysis": False,
                },
            )

            # Add enhancement metadata to response
            if hasattr(tool_response, "__dict__"):
                tool_response.integration_insights = {
                    "engines_used": quick_analysis.engines_used,
                    "optimization_recommendations": quick_analysis.optimization_recommendations[
                        :3
                    ],  # Top 3
                    "connectivity_summary": len(quick_analysis.connectivity_matrix),
                    "confidence_score": quick_analysis.confidence_score,
                    "enhancement_timestamp": datetime.now().isoformat(),
                }

            return tool_response

        except Exception:
            # Return original response if enhancement fails
            return tool_response

    async def cleanup(self):
        """Cleanup all engine resources."""
        cleanup_tasks = [
            self.route_engine.cleanup(),
            self.peering_engine.cleanup(),
            self.resolution_engine.cleanup(),
            self.cross_account_analyzer.cleanup(),
            self.performance_analyzer.cleanup(),
        ]

        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
