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


VALID_LB_TYPES = ('application', 'network', 'gateway')


async def list_load_balancers(
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the load balancers are deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
    lb_type: Annotated[
        Optional[str],
        Field(
            ...,
            description='Filter by load balancer type: "application", "network", or "gateway". Returns all types if not specified.',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List all ELBv2 load balancers in the specified AWS region.

    Use this tool when:
    - Starting load balancer troubleshooting to identify available ALBs, NLBs, and GLBs
    - Discovering load balancer infrastructure before detailed analysis
    - Finding load balancer ARNs needed for get_lb_details()
    - Auditing load balancer inventory across regions
    - Filtering load balancers by type (application, network, gateway)

    Common workflows:
    1. List LBs → Identify target LB → get_lb_details() for listeners/target groups
    2. List LBs → Find unhealthy LB → get_lb_target_health() for target diagnostics
    3. List LBs → Identify VPC → get_vpc_network_details() for network context

    Returns:
        Dict containing:
        - load_balancers: List of load balancer objects with ARN, name, type, scheme, state, DNS, VPC, AZs
        - count: Number of load balancers found
        - region: AWS region queried
    """
    if lb_type is not None and lb_type not in VALID_LB_TYPES:
        raise ToolError(
            f'Error listing load balancers. Error: Invalid lb_type "{lb_type}". '
            f'Must be one of: {", ".join(VALID_LB_TYPES)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    try:
        client = get_aws_client('elbv2', region, profile_name)
        paginator = client.get_paginator('describe_load_balancers')
        load_balancers = []
        for page in paginator.paginate():
            load_balancers.extend(page.get('LoadBalancers', []))

        if lb_type is not None:
            load_balancers = [lb for lb in load_balancers if lb.get('Type') == lb_type]

        return {
            'load_balancers': load_balancers,
            'count': len(load_balancers),
            'region': region,
        }
    except Exception as e:
        raise ToolError(
            f'Error listing load balancers. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
