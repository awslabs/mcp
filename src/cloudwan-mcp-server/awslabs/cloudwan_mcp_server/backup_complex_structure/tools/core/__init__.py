"""
Core operational MCP tools for CloudWAN.

This module contains the fundamental operational tools for CloudWAN management:
- IP address discovery and analysis
- Network path tracing
- VPC and segment discovery
- Core network analysis
- Route analysis
"""

from typing import TYPE_CHECKING, Dict, Any, List

if TYPE_CHECKING:
    from mcp import McpServer
    from ...aws.client_manager import AWSClientManager
    from ...config import CloudWANConfig

from mcp.types import TextContent


def register_core_tools(
    server: "McpServer", aws_manager: "AWSClientManager", config: "CloudWANConfig"
) -> None:
    """
    Register all core operational tools with the MCP server.

    This function registers the 14 core operational tools:
    1. find_ip_details - Find comprehensive IP address information
    2. network_path_trace - Trace network paths with inspection detection
    3. discover_vpc_resources - Discover VPC resources and configuration
    4. list_core_networks - List and analyze core networks
    5. analyze_segments - Analyze CloudWAN segments and routing
    6. analyze_tgw_peers - Analyze Transit Gateway peers
    7. query_firewall_logs - Query AWS Network Firewall logs
    8. analyze_route_tables - Comprehensive route table analysis
    9. discover_network_interfaces - Find and analyze ENIs
    10. analyze_security_groups - Security group rule analysis
    11. discover_subnets - Subnet discovery and analysis
    12. analyze_nacls - Network ACL analysis
    13. query_flow_logs - VPC Flow Logs analysis
    14. analyze_route_propagation - Route propagation analysis
    """
    # Import tool implementations
    from .tgw_route_analyzer import TGWRouteAnalyzer
    from .segment_route_analyzer import SegmentRouteAnalyzer
    from .tgw_peer_analyzer import TGWPeerAnalyzer
    from .path_tracing import (
        NetworkPathTracingTool,
        EnhancedNetworkPathTracingTool,
        SegmentConnectivityTool,
        VPCConnectivityTool,
    )

    # Register Phase 3 route analysis tools
    tgw_route_analyzer = TGWRouteAnalyzer(aws_manager, config)
    segment_route_analyzer = SegmentRouteAnalyzer(aws_manager, config)
    tgw_peer_analyzer = TGWPeerAnalyzer(aws_manager, config)

    # Register path tracing tools
    network_path_tracer = NetworkPathTracingTool(aws_manager, config)
    enhanced_path_tracer = EnhancedNetworkPathTracingTool(aws_manager, config)
    segment_connectivity_tool = SegmentConnectivityTool(aws_manager, config)
    vpc_connectivity_tool = VPCConnectivityTool(aws_manager, config)

    # Register tools with MCP server using correct v1.12.0 decorator API
    # Tools that use create_mcp_tool()
    @server.tool(
        name=tgw_route_analyzer.tool_name,
        description=tgw_route_analyzer.description,
        inputSchema=tgw_route_analyzer.input_schema,
    )
    async def handle_tgw_route_analyzer(arguments: Dict[str, Any]) -> List[TextContent]:
        return await tgw_route_analyzer.execute(**arguments)

    @server.tool(
        name=segment_route_analyzer.tool_name,
        description=segment_route_analyzer.description,
        inputSchema=segment_route_analyzer.input_schema,
    )
    async def handle_segment_route_analyzer(arguments: Dict[str, Any]) -> List[TextContent]:
        return await segment_route_analyzer.execute(**arguments)

    @server.tool(
        name=tgw_peer_analyzer.tool_name,
        description=tgw_peer_analyzer.description,
        inputSchema=tgw_peer_analyzer.input_schema,
    )
    async def handle_tgw_peer_analyzer(arguments: Dict[str, Any]) -> List[TextContent]:
        return await tgw_peer_analyzer.execute(**arguments)

    # Register path tracing tool (renamed from network_path_tracer)
    @server.tool(
        name="trace_network_path",  # Simplified name
        description=network_path_tracer.description,
        inputSchema=network_path_tracer.input_schema,
    )
    async def handle_trace_network_path(arguments: Dict[str, Any]) -> List[TextContent]:
        return await network_path_tracer.execute(**arguments)

    # Skip enhanced_path_tracer as it's redundant with the main path tracer

    @server.tool(
        name=segment_connectivity_tool.tool_name,
        description=segment_connectivity_tool.description,
        inputSchema=segment_connectivity_tool.input_schema,
    )
    async def handle_segment_connectivity(arguments: Dict[str, Any]) -> List[TextContent]:
        return await segment_connectivity_tool.execute(**arguments)

    @server.tool(
        name=vpc_connectivity_tool.tool_name,
        description=vpc_connectivity_tool.description,
        inputSchema=vpc_connectivity_tool.input_schema,
    )
    async def handle_vpc_connectivity(arguments: Dict[str, Any]) -> List[TextContent]:
        return await vpc_connectivity_tool.execute(**arguments)

    # TODO: Add other core tools as they are implemented
    # from .ip_tools import register_ip_tools
    # from .network_tools import register_network_tools
    # from .analysis_tools import register_analysis_tools
    # register_ip_tools(server, aws_manager, config)
    # register_network_tools(server, aws_manager, config)
    # register_analysis_tools(server, aws_manager, config)
