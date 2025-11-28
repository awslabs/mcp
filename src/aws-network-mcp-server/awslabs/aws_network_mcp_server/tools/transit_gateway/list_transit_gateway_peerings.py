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


async def list_tgw_peerings(
    transit_gateway_id: Annotated[str, Field(..., description='Transit Gateway ID')],
    transit_gateway_region: Annotated[
        str, Field(..., description='AWS region where Transit Gateway is deployed')
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> List[Dict[str, Any]]:
    """List all Transit Gateway peerings.

    Use this tool when:
    - Investigating connectivity between Transit Gateways in different regions or accounts
    - Analyzing Transit Gateway to Cloud WAN Core Network connections
    - Troubleshooting cross-region or cross-account routing issues
    - Validating peering attachment states and configurations
    - Mapping network topology across multiple Transit Gateways

    This tool retrieves all peering attachments for a specified Transit Gateway,
    including peerings to other Transit Gateways and Cloud WAN Core Networks.
    Each peering includes state, requester/accepter details, and attachment metadata.

    Common troubleshooting scenarios:
    - "Why can't traffic flow between two Transit Gateways?"
    - "Is my Transit Gateway properly peered with Cloud WAN?"
    - "What peering connections exist for this Transit Gateway?"

    Returns:
        List of peering attachments with details including:
        - TransitGatewayAttachmentId: Unique peering attachment identifier
        - State: Current state (available, pending, deleting, etc.)
        - RequesterTgwInfo: Source Transit Gateway details (ID, region, account)
        - AccepterTgwInfo: Destination Transit Gateway details
        - CreationTime: When the peering was created
        - Tags: Resource tags for identification
    """
    try:
        ec2_client = get_aws_client('ec2', transit_gateway_region, profile_name)

        response = ec2_client.describe_transit_gateway_peering_attachments(
            Filters=[{'Name': 'transit-gateway-id', 'Values': [transit_gateway_id]}]
        )

        return response.get('TransitGatewayPeeringAttachments', [])
    except Exception as e:
        raise ToolError(
            f'Error listing Transit Gateway peerings. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
