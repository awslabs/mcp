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

"""AWS Core Networking MCP Server, that provides tools for AWS core network services for troubleshooting and analysis."""

import logging
import sys
from awslabs.aws_network_mcp_server.tools import (
    cloud_wan,
    general,
    network_firewall,
    transit_gateway,
    vpc,
    vpn,
)
from fastmcp import FastMCP


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


mcp = FastMCP(
    name='awslabs.aws-core-network-mcp-server',
    instructions="""
    AWS Core Network MCP Server - Read-only troubleshooting tools for AWS networking services.

    ## CRITICAL FIRST STEP
    ALWAYS call get_path_trace_methodology() before analyzing connectivity issues. This provides the systematic approach needed for effective troubleshooting.

    ## Available Services
    - Cloud WAN: Core networks, routes, attachments, peerings, inspection detection
    - Transit Gateway: Details, routes, peerings, flow logs, inspection detection
    - VPC: Network configuration, flow logs, ENI details
    - Network Firewall: Rules and flow logs
    - VPN: Connection details
    - General: IP lookup, ENI analysis

    ## Troubleshooting Workflow
    1. DISCOVER: Use find_ip_address() to locate resources by IP across regions
    2. ANALYZE: Use get_eni_details() for security groups, NACLs, and route tables
    3. TRACE: Follow routing through VPC → Transit Gateway → Cloud WAN using route tools
    4. INSPECT: Use detect_tgw_inspection() or detect_cloudwan_inspection() to find firewalls in path
    5. VERIFY: Check flow logs (VPC, TGW, Network Firewall) to confirm traffic patterns

    ## Common Use Cases
    - Connectivity issues: get_path_trace_methodology → find_ip_address → get_eni_details → get_vpc_network_details
    - Cloud WAN routing: list_core_networks → get_cloudwan_details → get_cloudwan_routes
    - Transit Gateway routing: list_transit_gateways → get_tgw_details → get_all_tgw_routes
    - Firewall analysis: detect_tgw_inspection → get_firewall_rules → get_network_firewall_flow_logs
    - Traffic verification: get_vpc_flow_logs / get_tgw_flow_logs (filter by srcaddr, dstaddr, ports)

    ## Key Capabilities
    - Multi-region IP address search with find_ip_address(all_regions=True)
    - Comprehensive ENI details including security groups, NACLs, and routing
    - Cloud WAN policy analysis and route simulation
    - Transit Gateway peering and cross-account routing
    - Firewall detection in inspection architectures
    - Flow log analysis with filtering (source/dest IP, ports, action)

    ## Important Notes
    - All tools are READ-ONLY - use findings to guide AWS Console/CLI changes
    - Requires AWS credentials configured (env vars, ~/.aws/credentials, or IAM role)
    - Flow logs require CloudWatch Logs configuration in AWS
    - Transit Gateway route tools require Network Manager registration
    - Use profile_name parameter for multi-account access
    """,
    version='1.0.0',
)

# Register tools at module level
logger.info('Registering tools...')
for module in (general, cloud_wan, network_firewall, transit_gateway, vpc, vpn):
    for tool_name in module.__all__:
        mcp.tool(getattr(module, tool_name))
logger.info('Tools registered successfully')


def main():
    """Run the MCP server."""
    logger.info('Starting MCP server...')
    mcp.run()


if __name__ == '__main__':
    main()
