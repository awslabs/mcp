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


async def list_cwan_peerings(
    core_network_id: Annotated[str, Field(..., description='Cloud WAN Core Network ID.')],
    core_network_region: Annotated[
        str, Field(..., description='Region where Cloud WAN core network is deployed.')
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> List[Dict[str, Any]]:
    """List all Transit Gateway peerings for a Cloud WAN core network.

    Use this tool when:
    - Investigating connectivity between Cloud WAN and Transit Gateways
    - Troubleshooting cross-region or cross-account network connectivity
    - Validating peering configurations and states
    - Mapping network topology between Cloud WAN and Transit Gateway environments
    - Analyzing hybrid network architectures

    WORKFLOW CONTEXT:
    - Use after get_cloudwan_details() to understand core network structure
    - Use before get_cloudwan_peering_details() to identify specific peering IDs
    - Combine with list_tgw_peerings() for complete peering visibility

    Returns:
        List of Transit Gateway peering dictionaries containing:
        - PeeringId: Unique identifier for the peering
        - CoreNetworkId: Source Cloud WAN core network ID
        - TransitGatewayArn: Target Transit Gateway ARN
        - State: Peering state (CREATING, AVAILABLE, DELETING, etc.)
        - EdgeLocation: AWS region where peering exists
        - ResourceArn: Full ARN of the peering resource
        - Tags: Associated resource tags
    """
    try:
        nm_client = get_aws_client('networkmanager', core_network_region, profile_name)

        peerings = []
        next_token = None

        while True:
            params = {'CoreNetworkId': core_network_id}
            if next_token:
                params['NextToken'] = next_token

            response = nm_client.list_peerings(**params)

            for peering in response.get('Peerings', []):
                if peering.get('PeeringType') == 'TRANSIT_GATEWAY':
                    peerings.append(peering)

            next_token = response.get('NextToken')
            if not next_token:
                break
    except Exception as e:
        raise ToolError(
            f'Error getting Cloud WAN peerings. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    return peerings
