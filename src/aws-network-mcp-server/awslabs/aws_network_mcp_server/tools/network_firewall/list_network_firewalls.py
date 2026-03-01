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
from typing import Annotated, Any, Dict, Optional


async def list_firewalls(
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the Network Firewalls are deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List all AWS Network Firewalls in the specified region.

    Use this tool when:
    - Starting network troubleshooting to identify available firewalls
    - Discovering which Network Firewalls exist before analyzing rules or logs
    - Validating firewall deployment across regions
    - Getting firewall names/ARNs needed for other firewall tools

    WORKFLOW:
    1. Call this tool to discover available Network Firewalls
    2. Use get_firewall_rules() with firewall_name to analyze rules
    3. Use get_network_firewall_flow_logs() to examine traffic patterns

    RELATED TOOLS:
    - Use get_firewall_rules() to inspect firewall rule configurations
    - Use get_network_firewall_flow_logs() to analyze traffic through firewalls
    - Use detect_tgw_inspection() to identify firewalls attached to Transit Gateway

    Returns:
        Dict containing:
        - firewalls: List of firewall objects with name and ARN
        - region: AWS region queried
        - total_count: Number of firewalls found
    """
    try:
        client = get_aws_client('network-firewall', region, profile_name)
        response = client.list_firewalls()

        return {
            'firewalls': response.get('Firewalls', []),
            'region': region,
            'total_count': len(response.get('Firewalls', [])),
        }
    except Exception as e:
        raise ToolError(
            f'Error listing Network Firewalls: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
