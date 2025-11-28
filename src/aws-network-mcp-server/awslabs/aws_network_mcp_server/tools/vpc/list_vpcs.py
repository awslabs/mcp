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


async def list_vpcs(
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
    """List all VPCs in the specified AWS region.

    Use this tool when:
    - Starting network troubleshooting to identify available VPCs
    - Discovering VPC infrastructure before detailed analysis
    - Finding VPC IDs needed for other tools like get_vpc_network_details()
    - Auditing VPC inventory across regions
    - Locating VPCs by name or CIDR block from tags

    Common workflows:
    1. List VPCs → Identify target VPC → get_vpc_network_details() for routing/security
    2. List VPCs → Find VPC with specific CIDR → get_vpc_flow_logs() for traffic analysis
    3. List VPCs → Identify Transit Gateway attachments → get_tgw_details()

    Returns:
        Dict containing:
        - vpcs: List of VPC objects with ID, CIDR blocks, state, tags, and attributes
        - region: AWS region queried
        - total_count: Number of VPCs found

    Each VPC includes:
    - VpcId: Unique identifier for use with other tools
    - CidrBlock: Primary IPv4 CIDR range
    - State: VPC state (available, pending)
    - Tags: Name and custom tags for identification
    - IsDefault: Whether this is the default VPC
    """
    try:
        client = get_aws_client('ec2', region, profile_name)
        response = client.describe_vpcs()

        return {
            'vpcs': response.get('Vpcs', []),
            'region': region,
            'total_count': len(response.get('Vpcs', [])),
        }
    except Exception as e:
        raise ToolError(
            f'Error listing VPCs. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
