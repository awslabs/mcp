"""
Operational intelligence MCP tools for CloudWAN.

This module contains advanced intelligence and automation tools for CloudWAN
operations:
- Configuration drift detection
- Policy simulation and impact analysis
- Network event monitoring
- Automated troubleshooting runbooks
- LLM-enhanced NFG policy analysis
"""

from typing import TYPE_CHECKING
from .nfg_data_analyzer import NFGDataAnalyzerTool

if TYPE_CHECKING:
    from mcp import McpServer
    from ...aws.client_manager import AWSClientManager
    from ...config import CloudWANConfig

__all__ = [
    'NFGDataAnalyzerTool',
    'register_intelligence_tools'
]


def register_intelligence_tools(
    server: "McpServer", aws_manager: "AWSClientManager", config: "CloudWANConfig"
) -> None:
    """
    Register all operational intelligence tools with the MCP server.

    This function registers the 10 operational intelligence tools:
    1. detect_configuration_drift - Detect and analyze configuration drift
    2. simulate_policy_changes - Policy change simulation and impact analysis
    3. monitor_network_events - Real-time network event monitoring
    4. analyze_change_impact - Change impact analysis and recommendations
    5. generate_troubleshooting_runbook - Automated troubleshooting guidance
    6. generate_network_diagram - Visual network topology generation
    7. explain_routing_decisions - Routing decision explanation and analysis
    8. visualize_policy_flow - Policy flow visualization and analysis
    9. monitor_cloudwan_events - CloudWAN-specific event monitoring
    10. validate_nfg_configuration - Network Function Group validation
    11. analyze_cross_account_connectivity - Cross-account analysis
    12. analyze_longest_prefix_match - LPM routing analysis
    """
    # Import tool implementations
    from .drift_tools import register_drift_tools
    from .simulation_tools import register_simulation_tools
    from .monitoring_tools import register_monitoring_tools
    from .analysis_tools import register_analysis_tools

    # Register tool categories
    register_drift_tools(server, aws_manager, config)
    register_simulation_tools(server, aws_manager, config)
    register_monitoring_tools(server, aws_manager, config)
    register_analysis_tools(server, aws_manager, config)
    
    # Register data-only NFG policy analysis tool
    nfg_data_analyzer = NFGDataAnalyzerTool(aws_manager, config)
    server.add_tool(
        nfg_data_analyzer.tool_name,
        nfg_data_analyzer.description,
        nfg_data_analyzer.input_schema,
        nfg_data_analyzer.execute,
    )
