"""
MCP Tools for CloudWAN operations.

This module contains all the MCP tool implementations organized by category:
- Core operational tools
- Critical troubleshooting tools  
- Operational intelligence tools
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp import McpServer
    from ..aws.client_manager import AWSClientManager
    from ..config import CloudWANConfig


def register_all_tools(
    server: "McpServer", aws_manager: "AWSClientManager", config: "CloudWANConfig"
) -> None:
    """
    Register all MCP tools with the server.

    This function registers all 50+ CloudWAN operational tools:
    - 14 Core Operational Tools
    - 9 Critical Troubleshooting Tools
    - 10 Operational Intelligence Tools
    - 5 Enterprise Operations Tools
    - 4 Security Analysis Tools
    - 10 Real-time Monitoring Tools
    - 6 Professional Diagram Tools (NEW)
    """
    # Import and register tool categories
    from .core import register_core_tools
    from .troubleshooting import register_troubleshooting_tools

    from .intelligence import register_intelligence_tools
    # from .operations import register_operations_tools     # TODO: Fix add_tool
    from .security import register_security_tools
    from .monitoring import register_monitoring_tools
    from .visualization import register_visualization_tools
    from .cloudwan_diagram_tools import register_cloudwan_diagram_tools

    # Register diagram tools first (high value, low risk)
    register_cloudwan_diagram_tools(server, aws_manager, config)

    # Register remaining tool categories
    register_core_tools(server, aws_manager, config)
    register_troubleshooting_tools(server, aws_manager, config)
    register_intelligence_tools(server, aws_manager, config)
    # register_operations_tools(server, aws_manager, config)      # TODO: Fix add_tool
    register_security_tools(server, aws_manager, config)
    register_monitoring_tools(server, aws_manager, config)
    register_visualization_tools(server, aws_manager, config)


def register_all_tools_v2(server_instance) -> None:
    """
    Register all MCP tools with priority-based phased registration.

    This uses the server's register_tool method with priority-based phased loading:
    Phase 1 (Priority 1): Core operational tools - Essential functionality
    Phase 2 (Priority 2): Troubleshooting tools - Diagnostic capabilities
    Phase 3 (Priority 3): Intelligence tools - Advanced analysis
    Phase 4 (Priority 4): Operations tools - Management features
    Phase 5 (Priority 5): Security tools - Security analysis
    Phase 6 (Priority 6): Monitoring tools - Real-time monitoring
    Phase 7 (Priority 7): Visualization tools - Diagram generation
    """
    from ..base_server import ToolRegistrationHelper

    # Create tool registration helper for dependency resolution
    registration_helper = ToolRegistrationHelper(server_instance)

    # Helper function to create handler wrapper (maintain compatibility)
    def create_handler_wrapper(tool_instance):
        """Create a wrapper that handles the signature mismatch"""
        return registration_helper.create_handler_wrapper(tool_instance)

    # Priority-based tool definitions
    # Format: (module_path, class_name, tool_name, priority, dependencies)
    priority_tool_definitions = [
        # Phase 1: Core operational tools (Priority 1) - Essential functionality
        (
            "src.cloudwan_mcp.tools.core.discovery",
            "GlobalNetworkDiscoveryTool",
            "get_global_networks",
            1,
            None,
        ),  # Properly registered
        (
            "src.cloudwan_mcp.tools.core.discovery",
            "CoreNetworkDiscoveryTool",
            "list_core_networks",
            1,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.core.discovery",
            "VPCDiscoveryTool",
            "discover_vpcs",
            1,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.core.discovery",
            "IPDetailsDiscoveryTool",
            "discover_ip_details",
            1,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.core.path_tracing",
            "NetworkPathTracingTool",
            "trace_network_path",
            1,
            None,
        ),
        # Phase 2: Troubleshooting tools (Priority 2) - Diagnostic capabilities
        (
            "src.cloudwan_mcp.tools.troubleshooting.connectivity_analyzer",
            "ConnectivityAnalyzerTool",
            "analyze_connectivity",
            2,
            ["get_global_networks"],
        ),
        (
            "src.cloudwan_mcp.tools.troubleshooting.route_analyzer",
            "RouteAnalyzerTool",
            "analyze_routes",
            2,
            ["discover_vpcs"],
        ),
        (
            "src.cloudwan_mcp.tools.troubleshooting.bandwidth_analyzer",
            "BandwidthAnalyzerTool",
            "analyze_bandwidth",
            2,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.troubleshooting.latency_monitor",
            "LatencyMonitorTool",
            "monitor_latency",
            2,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.troubleshooting.packet_analyzer",
            "PacketAnalyzerTool",
            "analyze_packets",
            2,
            None,
        ),
        # Phase 3: Intelligence tools (Priority 3) - Advanced analysis
        (
            "src.cloudwan_mcp.tools.intelligence.network_anomaly_detector",
            "NetworkAnomalyDetectorTool",
            "detect_network_anomalies",
            3,
            ["analyze_connectivity"],
        ),
        (
            "src.cloudwan_mcp.tools.intelligence.traffic_pattern_analyzer",
            "TrafficPatternAnalyzerTool",
            "analyze_traffic_patterns",
            3,
            ["analyze_bandwidth"],
        ),
        (
            "src.cloudwan_mcp.tools.intelligence.cost_optimizer",
            "CostOptimizerTool",
            "optimize_costs",
            3,
            ["get_global_networks"],
        ),
        (
            "src.cloudwan_mcp.tools.intelligence.capacity_planner",
            "CapacityPlannerTool",
            "plan_capacity",
            3,
            ["analyze_traffic_patterns"],
        ),
        (
            "src.cloudwan_mcp.tools.intelligence.security_analyzer",
            "SecurityAnalyzerTool",
            "analyze_security",
            3,
            ["discover_vpcs"],
        ),
        # Phase 4: Operations tools (Priority 4) - Management features
        (
            "src.cloudwan_mcp.tools.operations.config_manager",
            "ConfigManagerTool",
            "manage_config",
            4,
            ["list_core_networks"],
        ),
        (
            "src.cloudwan_mcp.tools.operations.deployment_manager",
            "DeploymentManagerTool",
            "manage_deployment",
            4,
            ["manage_config"],
        ),
        (
            "src.cloudwan_mcp.tools.operations.backup_manager",
            "BackupManagerTool",
            "manage_backups",
            4,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.operations.update_manager",
            "UpdateManagerTool",
            "manage_updates",
            4,
            ["manage_deployment"],
        ),
        (
            "src.cloudwan_mcp.tools.operations.maintenance_scheduler",
            "MaintenanceSchedulerTool",
            "schedule_maintenance",
            4,
            None,
        ),
        # Phase 5: Security tools (Priority 5) - Security analysis
        (
            "src.cloudwan_mcp.tools.security.compliance_checker",
            "ComplianceCheckerTool",
            "check_compliance",
            5,
            ["analyze_security"],
        ),
        (
            "src.cloudwan_mcp.tools.security.vulnerability_scanner",
            "VulnerabilityScannerTool",
            "scan_vulnerabilities",
            5,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.security.access_analyzer",
            "AccessAnalyzerTool",
            "analyze_access",
            5,
            ["discover_vpcs"],
        ),
        # Phase 6: Monitoring tools (Priority 6) - Real-time monitoring
        (
            "src.cloudwan_mcp.tools.monitoring.performance_monitor",
            "PerformanceMonitorTool",
            "monitor_performance",
            6,
            ["monitor_latency"],
        ),
        (
            "src.cloudwan_mcp.tools.monitoring.health_monitor",
            "HealthMonitorTool",
            "monitor_health",
            6,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.monitoring.alerting_system",
            "AlertingSystemTool",
            "manage_alerts",
            6,
            ["monitor_performance"],
        ),
        (
            "src.cloudwan_mcp.tools.monitoring.metrics_collector",
            "MetricsCollectorTool",
            "collect_metrics",
            6,
            None,
        ),
        (
            "src.cloudwan_mcp.tools.monitoring.dashboard_generator",
            "DashboardGeneratorTool",
            "generate_dashboard",
            6,
            ["collect_metrics"],
        ),
        # Phase 7: Visualization tools (Priority 7) - Diagram generation
        (
            "src.cloudwan_mcp.tools.visualization.network_topology_visualizer",
            "NetworkTopologyVisualizationTool",
            "visualize_network_topology",
            7,
            ["get_global_networks"],
        ),
        (
            "src.cloudwan_mcp.tools.visualization.flow_visualizer",
            "FlowVisualizationTool",
            "visualize_flows",
            7,
            ["analyze_traffic_patterns"],
        ),
        (
            "src.cloudwan_mcp.tools.visualization.performance_visualizer",
            "PerformanceVisualizationTool",
            "visualize_performance",
            7,
            ["monitor_performance"],
        ),
        (
            "src.cloudwan_mcp.tools.visualization.cost_visualizer",
            "CostVisualizationTool",
            "visualize_costs",
            7,
            ["optimize_costs"],
        ),
        (
            "src.cloudwan_mcp.tools.visualization.security_visualizer",
            "SecurityVisualizationTool",
            "visualize_security",
            7,
            ["analyze_security"],
        ),
        (
            "src.cloudwan_mcp.tools.visualization.compliance_visualizer",
            "ComplianceVisualizationTool",
            "visualize_compliance",
            7,
            ["check_compliance"],
        ),
    ]

    # Register tools in priority order with dependency resolution
    for (
        module_path,
        class_name,
        tool_name,
        priority,
        dependencies,
    ) in priority_tool_definitions:
        try:
            # Check dependencies if any
            if dependencies:
                missing_deps = []
                for dep in dependencies:
                    if not server_instance.is_tool_registered(dep):
                        missing_deps.append(dep)

                if missing_deps:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Skipping {tool_name} due to missing dependencies: {', '.join(missing_deps)}"
                    )
                    continue

            # Dynamic import
            module = __import__(module_path, fromlist=[class_name])
            tool_class = getattr(module, class_name)

            # Register tool safely with error handling and dependency tracking
            registration_helper.register_tool_safely(
                tool_class, tool_name, dependencies=dependencies
            )

        except ImportError as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to import {class_name} from {module_path}: {e}")
        except AttributeError as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Class {class_name} not found in {module_path}: {e}")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error registering {tool_name}: {e}")

    # Log registration summary
    summary = registration_helper.get_registration_summary()
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Tool registration completed: {summary['successful']}/{summary['total_attempted']} tools registered successfully"
    )

    if summary["failed"] > 0:
        logger.warning(f"Failed to register {summary['failed']} tools:")
        for failed_tool in summary["failed_tools"]:
            logger.warning(
                f"  - {failed_tool['tool']}: {failed_tool['error']} - {failed_tool['details']}"
            )


def register_all_tools_v2_legacy_fallback(server_instance) -> None:
    """
    Legacy fallback registration for backward compatibility.

    This maintains the old manual registration pattern as a fallback.
    """

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

    # Import tools that are ready
    from .core.network_path_tracing import NetworkPathTracingTool
    from .core.discovery import IPDetailsDiscoveryTool

    # Register path tracing tool
    path_tracer = NetworkPathTracingTool(server_instance.aws_manager, server_instance.config)
    server_instance.register_tool(
        name="trace_network_path",
        description=path_tracer.description,
        input_schema=path_tracer.input_schema,
        handler=create_handler_wrapper(path_tracer),
    )

    # Register IP discovery tool
    ip_discovery = IPDetailsDiscoveryTool(server_instance.aws_manager, server_instance.config)
    server_instance.register_tool(
        name="discover_ip_details",
        description=ip_discovery.description,
        input_schema=ip_discovery.input_schema,
        handler=create_handler_wrapper(ip_discovery),
    )

    # Add VPC discovery tool
    from .core.discovery import VPCDiscoveryTool

    vpc_discovery = VPCDiscoveryTool(server_instance.aws_manager, server_instance.config)
    server_instance.register_tool(
        name="discover_vpcs",
        description=vpc_discovery.description,
        input_schema=vpc_discovery.input_schema,
        handler=create_handler_wrapper(vpc_discovery),
    )

    # Add Core Network discovery tool
    from .core.discovery import CoreNetworkDiscoveryTool

    core_network_discovery = CoreNetworkDiscoveryTool(
        server_instance.aws_manager, server_instance.config
    )
    server_instance.register_tool(
        name="list_core_networks",
        description=core_network_discovery.description,
        input_schema=core_network_discovery.input_schema,
        handler=create_handler_wrapper(core_network_discovery),
    )

    # Add Transit Gateway Routes tool
    from .core.tgw_routes import TransitGatewayRoutesTool

    tgw_routes_tool = TransitGatewayRoutesTool(server_instance.aws_manager, server_instance.config)
    server_instance.register_tool(
        name="manage_tgw_routes",
        description=tgw_routes_tool.description,
        input_schema=tgw_routes_tool.input_schema,
        handler=create_handler_wrapper(tgw_routes_tool),
    )

    # Add Global Network discovery tool
    from .core.discovery import GlobalNetworkDiscoveryTool

    global_network_discovery = GlobalNetworkDiscoveryTool(
        server_instance.aws_manager, server_instance.config
    )
    server_instance.register_tool(
        name="get_global_networks",
        description=global_network_discovery.description,
        input_schema=global_network_discovery.input_schema,
        handler=create_handler_wrapper(global_network_discovery),
    )

    # Add Network Topology Visualization Tool
    try:
        from .visualization.network_topology_visualizer import (
            NetworkTopologyVisualizationTool,
        )

        topology_viz_tool = NetworkTopologyVisualizationTool(
            server_instance.aws_manager, server_instance.config
        )
        server_instance.register_tool(
            name="visualize_network_topology",
            description=topology_viz_tool.description,
            input_schema=topology_viz_tool.input_schema,
            handler=create_handler_wrapper(topology_viz_tool),
        )
    except ImportError as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to import NetworkTopologyVisualizationTool: {e}")

    # Add TGW Peers Discovery Tool
    from .core.get_tgw_peers import GetTGWPeersTool

    tgw_peers_tool = GetTGWPeersTool(server_instance.aws_manager, server_instance.config)
    server_instance.register_tool(
        name="get_tgw_peers",
        description=tgw_peers_tool.description,
        input_schema=tgw_peers_tool.input_schema,
        handler=create_handler_wrapper(tgw_peers_tool),
    )

    # TODO: Add Anomaly Detection Tool once it follows the standard tool pattern

    # Register security tools
    try:
        from .security.firewall_logs_analyzer import FirewallLogsAnalyzerTool

        firewall_logs_analyzer = FirewallLogsAnalyzerTool(
            server_instance.aws_manager, server_instance.config
        )
        server_instance.register_tool(
            name=firewall_logs_analyzer.tool_name,
            description=firewall_logs_analyzer.description,
            input_schema=firewall_logs_analyzer.input_schema,
            handler=create_handler_wrapper(firewall_logs_analyzer),
        )
    except ImportError as e:
        server_instance.logger.warning(f"Failed to import FirewallLogsAnalyzerTool: {e}")

    # TODO: Add more tools as we fix them
