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


async def get_lb_target_health(
    target_group_arn: Annotated[
        str,
        Field(..., description='The ARN of the target group to check health for.'),
    ],
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the target group is deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get per-target health status with failure reasons for a target group.

    Use this tool when:
    - Diagnosing why targets are unhealthy in a load balancer target group
    - Checking health check status and failure reason codes for registered targets
    - Verifying target registration and health after deployment changes
    - Identifying draining, unused, or unavailable targets

    Common workflows:
    1. get_lb_details() → Identify target group → get_lb_target_health() for per-target status
    2. get_lb_target_health() → Find unhealthy target → get_eni_details() for network analysis
    3. list_load_balancers() → get_lb_details() → get_lb_target_health() for full diagnostics

    Returns:
        Dict containing:
        - target_group: TG metadata with ARN, name, protocol, port, health check config, LB ARNs
        - targets: List of targets with ID, port, health status, and reason code
        - region: AWS region queried
    """
    if (
        'arn:aws:elasticloadbalancing:' not in target_group_arn
        or 'targetgroup/' not in target_group_arn
    ):
        raise ToolError(
            'Error getting target health. Error: Invalid target_group_arn format. '
            'Must be a valid ELBv2 target group ARN containing "targetgroup/". '
            'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    try:
        client = get_aws_client('elbv2', region, profile_name)

        # Get target group metadata
        tg_response = client.describe_target_groups(TargetGroupArns=[target_group_arn])
        tgs = tg_response.get('TargetGroups', [])
        if not tgs:
            raise ToolError(
                f'Error getting target health. Error: Target group not found: {target_group_arn}. '
                f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
            )
        target_group = tgs[0]

        # Get per-target health
        health_response = client.describe_target_health(TargetGroupArn=target_group_arn)
        targets = health_response.get('TargetHealthDescriptions', [])

        return {
            'target_group': target_group,
            'targets': targets,
            'region': region,
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f'Error getting target health. Error: {str(e)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
