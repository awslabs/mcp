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


async def get_lb_details(
    lb_arn: Annotated[
        str,
        Field(..., description='The ARN of the load balancer to retrieve details for.'),
    ],
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the load balancer is deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get detailed configuration for a specific load balancer including listeners and target groups.

    Use this tool when:
    - Diagnosing connectivity issues with a specific ALB, NLB, or GLB
    - Reviewing listener configuration (protocols, ports, default actions)
    - Identifying associated target groups and their health check settings
    - Checking security group associations for ALBs and NLBs
    - Verifying AZ mapping and subnet placement

    Common workflows:
    1. get_lb_details() → Review listeners → Check target groups → get_lb_target_health()
    2. get_lb_details() → Check security groups → get_eni_details() for deeper SG analysis
    3. list_load_balancers() → get_lb_details() → Identify misconfigured listeners

    Returns:
        Dict containing:
        - load_balancer: LB config with ARN, name, type, scheme, state, DNS, VPC, AZs, security groups
        - listeners: List of listeners or None if sub-call failed
        - listeners_error: Error message if listeners retrieval failed
        - target_groups: List of target groups or None if sub-call failed
        - target_groups_error: Error message if target groups retrieval failed
        - region: AWS region queried
    """
    if not lb_arn.startswith('arn:aws:elasticloadbalancing:'):
        raise ToolError(
            'Error getting load balancer details. Error: Invalid lb_arn format. '
            'Must start with "arn:aws:elasticloadbalancing:". '
            'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    try:
        client = get_aws_client('elbv2', region, profile_name)
        response = client.describe_load_balancers(LoadBalancerArns=[lb_arn])
        lbs = response.get('LoadBalancers', [])
        if not lbs:
            raise ToolError(
                f'Error getting load balancer details. Error: Load balancer not found: {lb_arn}. '
                f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
            )
        lb = lbs[0]
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f'Error getting load balancer details. Error: {str(e)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    # Handle security groups: present for ALB, optional for NLB, absent for GLB
    lb_type = lb.get('Type', '')
    if lb_type == 'gateway':
        lb['SecurityGroups'] = None
    elif 'SecurityGroups' not in lb:
        lb['SecurityGroups'] = []

    # Retrieve listeners with independent error handling
    listeners = None
    listeners_error = None
    try:
        listener_paginator = client.get_paginator('describe_listeners')
        listeners = []
        for page in listener_paginator.paginate(LoadBalancerArn=lb_arn):
            listeners.extend(page.get('Listeners', []))
    except Exception as e:
        listeners = None
        listeners_error = str(e)

    # Retrieve target groups with independent error handling
    target_groups = None
    target_groups_error = None
    try:
        tg_paginator = client.get_paginator('describe_target_groups')
        target_groups = []
        for page in tg_paginator.paginate(LoadBalancerArn=lb_arn):
            target_groups.extend(page.get('TargetGroups', []))
    except Exception as e:
        target_groups = None
        target_groups_error = str(e)

    return {
        'load_balancer': lb,
        'listeners': listeners,
        'listeners_error': listeners_error,
        'target_groups': target_groups,
        'target_groups_error': target_groups_error,
        'region': region,
    }
