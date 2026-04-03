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


async def list_core_networks(
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the Cloud WAN core network is deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List all Cloud WAN core networks in the specified region.

    Use this tool when:
    - Starting Cloud WAN troubleshooting and need to identify available core networks
    - Discovering Cloud WAN infrastructure in a specific region
    - Need to find the core network ID before calling other Cloud WAN tools
    - Validating Cloud WAN deployment exists in a region

    WORKFLOW CONTEXT:
    This is typically the FIRST tool to call when troubleshooting Cloud WAN issues.
    After identifying the core network ID, use get_cloudwan_details() for detailed analysis.

    Returns:
        Dict containing:
        - core_networks: List of core network objects with ID, ARN, state, and tags
        - region: The queried AWS region
        - total_count: Number of core networks found

    Raises:
        ToolError: If no core networks found or AWS API call fails
    """
    try:
        client = get_aws_client('networkmanager', region, profile_name)
        response = client.list_core_networks()

        core_networks = response.get('CoreNetworks', [])

        if not core_networks:
            raise ToolError(
                f'No CloudWAN core networks found in the specified region: {region}. VALIDATE PARAMETERS BEFORE CONTINUING'
            )

        return {
            'core_networks': core_networks,
            'region': region,
            'total_count': len(core_networks),
        }

    except Exception as e:
        raise ToolError(
            f'Error listing CloudWAN core networks: Error :{str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
