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


from awslabs.aws_network_mcp_server.utils.aws_common import get_aws_client
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


async def list_vpn_connections(
    vpn_region: Annotated[str, Field(..., description='AWS region where the VPNs are deployed.')],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> List[Dict[str, Any]]:
    """List all Site-to-Site VPN connections in specified AWS region.

    Use this tool when:
    - Discovering VPN connections for hybrid connectivity troubleshooting
    - Analyzing VPN tunnel status and configuration
    - Identifying VPN connections attached to Transit Gateways or Virtual Private Gateways
    - Investigating connectivity issues between on-premises and AWS
    - Auditing VPN infrastructure in a region

    Returns comprehensive VPN details including:
    - VPN connection ID, state, and type
    - Customer Gateway and Virtual Private Gateway/Transit Gateway associations
    - Tunnel status and configuration (excludes sensitive CustomerGatewayConfiguration)
    - BGP ASN and routing information
    - Tags and metadata

    Common troubleshooting workflow:
    1. List VPN connections to identify relevant VPN
    2. Check tunnel status (UP/DOWN) for connectivity issues
    3. Verify Transit Gateway or VGW attachments
    4. Cross-reference with Transit Gateway routes or VPC route tables

    Note: CustomerGatewayConfiguration is excluded from results for security.
    """
    try:
        ec2_client = get_aws_client('ec2', vpn_region, profile_name)
        response = ec2_client.describe_vpn_connections()

        # Remove CustomerGatewayConfiguration from each VPN connection
        for vpn in response['VpnConnections']:
            vpn.pop('CustomerGatewayConfiguration', None)

        return response['VpnConnections']
    except Exception as e:
        raise ToolError(
            f'Error listing VPN connections. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
