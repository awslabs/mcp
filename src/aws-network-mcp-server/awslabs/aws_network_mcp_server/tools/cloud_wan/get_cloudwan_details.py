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

import json
from awslabs.aws_network_mcp_server.utils.aws_common import get_aws_client
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def get_cwan(
    core_network_id: Annotated[str, Field(..., description='AWS Cloud WAN core network ID')],
    core_network_region: Annotated[
        str, Field(..., description='AWS region where the Cloud WAN is deployed')
    ],
    next_token: Annotated[
        Optional[str],
        Field(
            ...,
            description='Next token for Core Network Attachment pagination. If this is provided, tool will only return the next page of attachment details.',
        ),
    ] = None,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get comprehensive AWS Cloud WAN Core Network configuration and state.

    Use this tool when:
    - Starting Cloud WAN troubleshooting to understand network topology
    - Analyzing routing issues between segments or attachments
    - Validating policy configuration and attachment associations
    - Investigating connectivity problems in multi-region networks
    - Auditing network architecture and attachment states

    This tool retrieves the complete Cloud WAN configuration including core network details,
    live policy document, and all attachments. It's typically the first tool to call when
    troubleshooting Cloud WAN issues.

    Workflow:
    1. Call this tool to get core network overview and policy
    2. Review segments, network function groups, and edges
    3. Examine attachment details to identify relevant VPCs, VPNs, or peerings
    4. Use get_cloudwan_routes() to analyze routing for specific segments
    5. Use detect_cloudwan_inspection() if traffic inspection is involved

    Pagination:
    If next_token is present in the response, call again with the token to retrieve
    additional attachments. When next_token is provided, only attachment data is returned.

    Returns:
        Dict containing:
        - core_network: Core network metadata (segments, edges, ASNs, state)
        - live_policy: Full policy document with segment actions and routing rules
        - attachments: List of all attachments (VPC, VPN, peering, Connect)
        - next_token: Pagination token if more attachments exist (None if complete)
    """
    try:
        nm_client = get_aws_client('networkmanager', core_network_region, profile_name)

        if next_token:
            attachments = nm_client.list_attachments(
                CoreNetworkId=core_network_id, NextToken=next_token
            )
            return {
                'attachments': attachments['Attachments'],
                'next_token': attachments.get('NextToken', None),
            }

        core_network = nm_client.get_core_network(CoreNetworkId=core_network_id)['CoreNetwork']

        policy = nm_client.get_core_network_policy(CoreNetworkId=core_network_id, Alias='LIVE')
        live_policy = json.loads(policy['CoreNetworkPolicy']['PolicyDocument'])

        # Get Attachments
        attachments = nm_client.list_attachments(CoreNetworkId=core_network_id)

    except Exception as e:
        raise ToolError(
            f'There was an error getting AWS Core Network details. VALIDATE parameter information before continuing. Error: {str(e)}'
        )

    return {
        'core_network': core_network,
        'live_policy': live_policy,
        'attachments': attachments['Attachments'],
        'next_token': attachments.get('NextToken', None),
    }
