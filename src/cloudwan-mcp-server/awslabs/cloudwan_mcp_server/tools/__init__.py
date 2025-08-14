# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools package for AWS CloudWAN MCP Server."""

from . import base
from .configuration import ConfigurationTools
from .core_network import CoreNetworkTools
from .discovery import DiscoveryTools
from .network_analysis import NetworkAnalysisTools
from .nfg_management import NFGManagementTools
from .transit_gateway import TransitGatewayTools

__all__ = [
    "base",
    "ConfigurationTools",
    "CoreNetworkTools", 
    "DiscoveryTools",
    "NetworkAnalysisTools",
    "NFGManagementTools",
    "TransitGatewayTools"
]


def register_all_tools(mcp_server):
    """Register all tool modules with the MCP server.
    
    This implements the modular architecture described in MODULARIZATION_STRATEGY.md,
    organizing 17 tools into 6 focused modules with single responsibility.
    
    Args:
        mcp_server: FastMCP server instance
        
    Returns:
        List of registered tool instances
    """
    tool_instances = []
    
    # Phase 2: Core Tools Migration (highest complexity first)
    
    # 1. Network Analysis Tools (3 tools - highest complexity)
    network_analysis = NetworkAnalysisTools(mcp_server)
    tool_instances.append(network_analysis)
    
    # 2. Core Network Management Tools (4 tools - core functionality)  
    core_network = CoreNetworkTools(mcp_server)
    tool_instances.append(core_network)
    
    # 3. Network Function Groups Tools (3 tools - specialized functionality)
    nfg_management = NFGManagementTools(mcp_server)
    tool_instances.append(nfg_management)
    
    # Phase 3: Supporting Tools Migration
    
    # 4. Transit Gateway Tools (3 tools)
    transit_gateway = TransitGatewayTools(mcp_server)
    tool_instances.append(transit_gateway)
    
    # 5. Discovery Tools (2 tools)
    discovery = DiscoveryTools(mcp_server)
    tool_instances.append(discovery)
    
    # 6. Configuration Tools (2 tools)
    configuration = ConfigurationTools(mcp_server)
    tool_instances.append(configuration)
    
    return tool_instances
