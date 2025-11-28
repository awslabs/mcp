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


async def list_transit_gateways(
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the Transit Gateways are deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List all AWS Transit Gateways in the specified region.

    Use this tool when:
    - Starting network troubleshooting to discover available Transit Gateways
    - Planning network architecture changes across regions
    - Auditing Transit Gateway deployments
    - Finding Transit Gateway IDs for use with other tools like get_tgw_details()

    Workflow:
    1. Call this tool to discover Transit Gateways in a region
    2. Use get_tgw_details() with specific Transit Gateway ID for detailed information
    3. Use get_all_tgw_routes() or get_tgw_routes() to analyze routing
    4. Use detect_tgw_inspection() to identify firewall inspection points

    Returns:
        Dict containing:
        - transit_gateways: List of Transit Gateway objects with full AWS details
          (ID, state, ASN, route table settings, tags, etc.)
        - region: The AWS region queried
        - total_count: Number of Transit Gateways found
    """
    try:
        client = get_aws_client('ec2', region, profile_name)
        response = client.describe_transit_gateways()

        return {
            'transit_gateways': response.get('TransitGateways', []),
            'region': region,
            'total_count': len(response.get('TransitGateways', [])),
        }
    except Exception as e:
        raise ToolError(
            f'Error listing Transit Gateways. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
