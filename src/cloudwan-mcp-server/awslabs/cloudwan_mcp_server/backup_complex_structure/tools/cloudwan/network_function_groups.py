"""Network Function Groups management tools for CloudWAN MCP Server.

This module provides comprehensive tools for working with Network Function Groups
in AWS Cloud WAN environments, including discovery, analysis, and policy management.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field
from mcp.types import CallToolResult, TextContent

from ...engines.network_function_group_analyzer import NetworkFunctionGroupAnalyzer
from ...models.base import BaseResponse
from ..base import BaseMCPTool, handle_errors


class NetworkFunctionGroupsListResponse(BaseResponse):
    """Response model for listing Network Function Groups."""

    network_function_groups: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0


class NetworkFunctionGroupDetailsResponse(BaseResponse):
    """Response model for Network Function Group details."""

    network_function_group: Optional[Dict[str, Any]] = None


class NetworkFunctionGroupRoutingPathResponse(BaseResponse):
    """Response model for Network Function Group routing paths."""

    routing_paths: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0


class NetworkFunctionGroupPolicyAnalysisResponse(BaseResponse):
    """Response model for Network Function Group policy analysis."""

    policy_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0


class ListNetworkFunctionGroupsTool(BaseMCPTool):
    """Tool for listing and discovering Network Function Groups."""

    @property
    def tool_name(self) -> str:
        return "list_network_function_groups"

    @property
    def description(self) -> str:
        return """
        List all Network Function Groups (NFGs) in a Core Network.
        
        Network Function Groups allow you to centrally define policy-based routing for
        network traffic through service functions like firewalls, intrusion detection
        systems, and proxies.
        
        This tool discovers all Network Function Groups in a given AWS Cloud WAN 
        Core Network and provides high-level information about their configuration
        and status.
        
        Args:
            core_network_id: ID of the Core Network to analyze
            include_routing_analysis: Include detailed routing analysis (default: False)
            include_performance_metrics: Include performance metrics (default: False)
            force_refresh: Force refresh of cached data (default: False)
        
        Returns:
            List of Network Function Groups with their configuration and status
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "AWS Cloud WAN Core Network ID",
                },
                "include_routing_analysis": {
                    "type": "boolean",
                    "description": "Include detailed routing analysis",
                    "default": False,
                },
                "include_performance_metrics": {
                    "type": "boolean",
                    "description": "Include performance metrics",
                    "default": False,
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Force refresh of cached data",
                    "default": False,
                },
            },
            "required": ["core_network_id"],
        }

    @handle_errors
    async def execute(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute the tool to list Network Function Groups."""
        core_network_id = arguments["core_network_id"]
        include_routing_analysis = arguments.get("include_routing_analysis", False)
        include_performance_metrics = arguments.get("include_performance_metrics", False)
        force_refresh = arguments.get("force_refresh", False)
        
        self.logger.info(f"Listing Network Function Groups for Core Network: {core_network_id}")

        # Initialize the analyzer engine
        analyzer = NetworkFunctionGroupAnalyzer(self.aws_manager, self.config)

        # Get all Network Function Groups
        nfgs = await analyzer.discover_all_network_function_groups(
            core_network_id,
            include_routing_analysis=include_routing_analysis,
            include_performance_metrics=include_performance_metrics,
            force_refresh=force_refresh,
        )

        # Process results for response
        nfg_list = []
        for nfg in nfgs:
            nfg_list.append(
                {
                    "name": nfg.name,
                    "function_type": str(nfg.function_type),
                    "routing_behavior": str(nfg.routing_behavior),
                    "send_to_segments": nfg.send_to_segments,
                    "send_via_mode": nfg.send_via_mode,
                    "bypass_allowed": nfg.bypass_allowed,
                    "is_active": nfg.is_active,
                    "insertion_points": len(nfg.insertion_points),
                    "configuration_errors": len(nfg.configuration_errors) > 0,
                }
            )

        response = NetworkFunctionGroupsListResponse(
            success=True,
            message=f"Found {len(nfg_list)} Network Function Groups",
            network_function_groups=nfg_list,
            total_count=len(nfg_list),
        )
        return CallToolResult(content=[TextContent(type="text", text=response.model_dump_json(indent=2))])


class GetNetworkFunctionGroupDetailsTool(BaseMCPTool):
    """Tool for getting detailed information about a Network Function Group."""

    @property
    def tool_name(self) -> str:
        return "get_network_function_group_details"

    @property
    def description(self) -> str:
        return """
        Get detailed information about a specific Network Function Group (NFG).
        
        This tool provides comprehensive details about a Network Function Group,
        including its configuration, routing behavior, service insertion points,
        and performance metrics.
        
        Args:
            core_network_id: ID of the Core Network
            nfg_name: Name of the Network Function Group
            include_routing_analysis: Include detailed routing analysis (default: True)
            include_performance_metrics: Include performance metrics (default: True)
            force_refresh: Force refresh of cached data (default: False)
        
        Returns:
            Detailed information about the Network Function Group
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "AWS Cloud WAN Core Network ID",
                },
                "nfg_name": {
                    "type": "string",
                    "description": "Name of the Network Function Group",
                },
                "include_routing_analysis": {
                    "type": "boolean",
                    "description": "Include detailed routing analysis",
                    "default": True,
                },
                "include_performance_metrics": {
                    "type": "boolean",
                    "description": "Include performance metrics",
                    "default": True,
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Force refresh of cached data",
                    "default": False,
                },
            },
            "required": ["core_network_id", "nfg_name"],
        }

    @handle_errors
    async def execute(
        self,
        core_network_id: str,
        nfg_name: str,
        include_routing_analysis: bool = True,
        include_performance_metrics: bool = True,
        force_refresh: bool = False,
    ) -> NetworkFunctionGroupDetailsResponse:
        """Execute the tool to get Network Function Group details."""
        self.logger.info(
            f"Getting details for Network Function Group: {nfg_name} in Core Network: {core_network_id}"
        )

        # Initialize the analyzer engine
        analyzer = NetworkFunctionGroupAnalyzer(self.aws_manager, self.config)

        # Get NFG details
        nfg = await analyzer.analyze_network_function_group(
            core_network_id,
            nfg_name,
            include_routing_analysis=include_routing_analysis,
            include_performance_metrics=include_performance_metrics,
            force_refresh=force_refresh,
        )

        # Process for response
        nfg_details = {
            "name": nfg.name,
            "core_network_id": nfg.core_network_id,
            "function_type": str(nfg.function_type),
            "description": nfg.description,
            "routing_behavior": str(nfg.routing_behavior),
            "send_to_segments": nfg.send_to_segments,
            "send_via_mode": nfg.send_via_mode,
            "bypass_allowed": nfg.bypass_allowed,
            "is_active": nfg.is_active,
            "require_attachment_acceptance": nfg.require_attachment_acceptance,
            "policy_version": nfg.policy_version,
            # Routing analysis
            "routing_rules": [
                {
                    "rule_id": rule.rule_id,
                    "priority": rule.priority,
                    "action": str(rule.action),
                    "is_active": rule.is_active,
                    "match_count": rule.match_count,
                }
                for rule in nfg.routing_rules
            ],
            # Service insertion
            "insertion_points": [
                {
                    "insertion_id": point.insertion_id,
                    "location": point.location,
                    "segment_name": point.segment_name,
                    "function_type": str(point.function_type),
                    "insertion_mode": point.insertion_mode,
                    "health_status": point.health_status,
                }
                for point in nfg.insertion_points
            ],
            "supported_protocols": nfg.supported_protocols,
            # Performance metrics if included
            "traffic_volume": nfg.traffic_volume if include_performance_metrics else {},
            "performance_metrics": (nfg.performance_metrics if include_performance_metrics else {}),
            "error_rates": nfg.error_rates if include_performance_metrics else {},
            # Configuration errors
            "configuration_errors": nfg.configuration_errors,
        }

        return NetworkFunctionGroupDetailsResponse(
            success=True,
            message=f"Successfully retrieved details for {nfg_name}",
            network_function_group=nfg_details,
        )


class CalculateNetworkFunctionGroupPathsTool(BaseMCPTool):
    """Tool for calculating routing paths through Network Function Groups."""

    @property
    def tool_name(self) -> str:
        return "calculate_nfg_routing_paths"

    @property
    def description(self) -> str:
        return """
        Calculate possible routing paths through Network Function Groups.
        
        This tool analyzes possible network paths between two segments,
        considering Network Function Group routing policies and constraints.
        It helps understand traffic flow through service functions like
        firewalls, IDS/IPS, and proxies.
        
        Args:
            core_network_id: ID of the Core Network
            source_segment: Source segment name
            destination_segment: Destination segment name
            include_nfg_constraints: Include NFG routing constraints (default: True)
            max_hops: Maximum number of hops to consider (default: 5)
        
        Returns:
            List of possible routing paths with hop information
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "AWS Cloud WAN Core Network ID",
                },
                "source_segment": {
                    "type": "string",
                    "description": "Source segment name",
                },
                "destination_segment": {
                    "type": "string",
                    "description": "Destination segment name",
                },
                "include_nfg_constraints": {
                    "type": "boolean",
                    "description": "Include NFG routing constraints",
                    "default": True,
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum number of hops to consider",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["core_network_id", "source_segment", "destination_segment"],
        }

    @handle_errors
    async def execute(
        self,
        core_network_id: str,
        source_segment: str,
        destination_segment: str,
        include_nfg_constraints: bool = True,
        max_hops: int = 5,
    ) -> NetworkFunctionGroupRoutingPathResponse:
        """Execute the tool to calculate routing paths."""
        self.logger.info(
            f"Calculating routing paths from {source_segment} to {destination_segment} in Core Network: {core_network_id}"
        )

        # Initialize the analyzer engine
        analyzer = NetworkFunctionGroupAnalyzer(self.aws_manager, self.config)

        # Calculate routing paths
        paths = await analyzer.calculate_multi_hop_routing_paths(
            core_network_id,
            source_segment,
            destination_segment,
            include_nfg_constraints=include_nfg_constraints,
            max_hops=max_hops,
        )

        # Process for response
        path_list = []
        for path in paths:
            path_list.append(
                {
                    "path_id": path.path_id,
                    "source_segment": path.source_segment,
                    "destination_segment": path.destination_segment,
                    "hops": path.hops,
                    "network_functions": path.network_functions,
                    "total_latency_ms": path.total_latency_ms,
                    "path_cost": path.path_cost,
                    "is_optimal": path.is_optimal,
                    "alternate_paths": path.alternate_paths,
                    "has_policy_constraints": len(path.policy_constraints) > 0,
                }
            )

        return NetworkFunctionGroupRoutingPathResponse(
            success=True,
            message=f"Found {len(path_list)} routing paths from {source_segment} to {destination_segment}",
            routing_paths=path_list,
            total_count=len(path_list),
        )


class AnalyzeNetworkFunctionGroupPoliciesTool(BaseMCPTool):
    """Tool for analyzing Network Function Group policies."""

    @property
    def tool_name(self) -> str:
        return "analyze_nfg_policies"

    @property
    def description(self) -> str:
        return """
        Analyze Network Function Group send-to and send-via policies.
        
        This tool evaluates the configuration and effectiveness of Network Function Group
        routing policies, identifies potential conflicts, and provides recommendations
        for optimization.
        
        Args:
            core_network_id: ID of the Core Network
            nfg_name: Optional specific NFG name to evaluate (default: None - all NFGs)
        
        Returns:
            Policy evaluation results with recommendations
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "AWS Cloud WAN Core Network ID",
                },
                "nfg_name": {
                    "type": "string",
                    "description": "Optional specific NFG name to evaluate",
                },
            },
            "required": ["core_network_id"],
        }

    @handle_errors
    async def execute(
        self, core_network_id: str, nfg_name: Optional[str] = None
    ) -> NetworkFunctionGroupPolicyAnalysisResponse:
        """Execute the tool to analyze NFG policies."""
        self.logger.info(
            f"Analyzing Network Function Group policies for {nfg_name or 'all NFGs'} in Core Network: {core_network_id}"
        )

        # Initialize the analyzer engine
        analyzer = NetworkFunctionGroupAnalyzer(self.aws_manager, self.config)

        # Analyze policies
        policy_results = await analyzer.evaluate_send_to_send_via_policies(
            core_network_id, nfg_name=nfg_name
        )

        return NetworkFunctionGroupPolicyAnalysisResponse(
            success=True,
            message=f"Analyzed policies for {len(policy_results)} Network Function Groups",
            policy_analysis=policy_results,
            total_count=len(policy_results),
        )


def register_network_function_group_tools(server_instance) -> None:
    """Register Network Function Group tools with the server."""

    # Helper function to create handler wrapper
    def create_handler_wrapper(tool_instance):
        """Create a wrapper that handles the signature mismatch"""

        async def wrapper(**kwargs):
            # Check if the tool expects 'arguments' parameter
            import inspect

            sig = inspect.signature(tool_instance.execute)
            params = list(sig.parameters.keys())

            # If it expects 'arguments' as first positional param, wrap kwargs
            if params and params[0] == "arguments":
                return await tool_instance.execute(kwargs)
            else:
                # Otherwise pass kwargs directly
                return await tool_instance.execute(**kwargs)

        return wrapper

    # Register List NFGs tool
    list_nfgs_tool = ListNetworkFunctionGroupsTool(
        server_instance.aws_manager, server_instance.config
    )
    server_instance.register_tool(
        name=list_nfgs_tool.tool_name,
        description=list_nfgs_tool.description,
        input_schema=list_nfgs_tool.input_schema,
        handler=create_handler_wrapper(list_nfgs_tool),
    )

    # Register Get NFG Details tool
    get_nfg_details_tool = GetNetworkFunctionGroupDetailsTool(
        server_instance.aws_manager, server_instance.config
    )
    server_instance.register_tool(
        name=get_nfg_details_tool.tool_name,
        description=get_nfg_details_tool.description,
        input_schema=get_nfg_details_tool.input_schema,
        handler=create_handler_wrapper(get_nfg_details_tool),
    )

    # Register Calculate NFG Paths tool
    calc_paths_tool = CalculateNetworkFunctionGroupPathsTool(
        server_instance.aws_manager, server_instance.config
    )
    server_instance.register_tool(
        name=calc_paths_tool.tool_name,
        description=calc_paths_tool.description,
        input_schema=calc_paths_tool.input_schema,
        handler=create_handler_wrapper(calc_paths_tool),
    )

    # Register Analyze NFG Policies tool
    analyze_policies_tool = AnalyzeNetworkFunctionGroupPoliciesTool(
        server_instance.aws_manager, server_instance.config
    )
    server_instance.register_tool(
        name=analyze_policies_tool.tool_name,
        description=analyze_policies_tool.description,
        input_schema=analyze_policies_tool.input_schema,
        handler=create_handler_wrapper(analyze_policies_tool),
    )
