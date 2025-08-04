"""
Foundation engines for CloudWAN MCP Server.

This module provides the core processing engines that underpin all MCP tools.
These engines implement proven patterns adapted from legacy scripts while
providing modern async/await interfaces and enhanced error handling.

High-Performance Engines:
- HighPerformanceIPResolver: Optimized for <2s IP resolution target
- AsyncExecutorBridge: Direct ThreadPoolExecutor pattern adaptation to anyio
- HighPerformanceBenchmarkSuite: Comprehensive performance validation

Transit Gateway Analysis Engines (Agent 3):
- TransitGatewayRouteEngine: Comprehensive route analysis with longest-prefix matching
- TGWPeeringDiscoveryEngine: Multi-hop peering chain discovery and analysis
- RouteResolutionEngine: End-to-end route resolution with path analysis
- CrossAccountTGWAnalyzer: Cross-account security and compliance analysis
- TGWPerformanceAnalyzer: Performance monitoring and optimization
"""

from .ip_resolution_engine import IPResolutionEngine
from .multi_region_engine import MultiRegionProcessingEngine
from .high_performance_ip_resolver import HighPerformanceIPResolver
from .async_executor_bridge import AsyncExecutorBridge
from .high_performance_benchmarks import HighPerformanceBenchmarkSuite

# Transit Gateway Analysis Engines
from .transit_gateway_route_engine import TransitGatewayRouteEngine
from .tgw_peering_discovery_engine import TGWPeeringDiscoveryEngine
from .route_resolution_engine import RouteResolutionEngine
from .cross_account_tgw_analyzer import (
    CrossAccountTransitGatewayAnalyzer as CrossAccountTGWAnalyzer,
)
from .tgw_performance_analyzer import TGWPerformanceAnalyzer

__all__ = [
    # Foundation engines
    "MultiRegionProcessingEngine",
    "IPResolutionEngine",
    "HighPerformanceIPResolver",
    "AsyncExecutorBridge",
    "HighPerformanceBenchmarkSuite",
    # Transit Gateway engines
    "TransitGatewayRouteEngine",
    "TGWPeeringDiscoveryEngine",
    "RouteResolutionEngine",
    "CrossAccountTGWAnalyzer",
    "TGWPerformanceAnalyzer",
]
