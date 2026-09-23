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


async def get_cwan_policy(
    core_network_id: Annotated[str, Field(..., description='AWS Cloud WAN core network ID')],
    region: Annotated[
        str, Field(..., description='AWS region where the Cloud WAN core network is deployed')
    ],
    policy_version_id: Annotated[
        Optional[int],
        Field(
            ...,
            description='Specific policy version ID to retrieve. If not provided, returns the current LIVE policy.',
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
    """Get the current Cloud WAN policy document for a core network.

    Use this tool when:
    - You need to examine the current routing policy configuration
    - Analyzing segment definitions, actions, and routing rules
    - Troubleshooting policy-related routing issues
    - Comparing policy versions or validating policy changes
    - Understanding network function groups and service insertion configuration

    WORKFLOW CONTEXT:
    This tool retrieves the policy document which defines how traffic is routed
    between segments. Use after identifying the core network ID with list_core_networks().

    The policy document contains:
    - Segment definitions and their edge locations
    - Segment actions (attachment associations, routing rules)
    - Network function groups for service insertion
    - Core network configuration (ASN ranges, edge locations)

    Returns:
        Dict containing:
        - core_network_id: The queried core network ID
        - policy_version_id: The version ID of the returned policy
        - policy_document: The full policy document with segments, actions, and rules
        - change_set_state: State of the policy (e.g., READY_TO_EXECUTE, EXECUTED)
        - policy_errors: Any errors in the policy (if present)

    Raises:
        ToolError: If the core network or policy is not found, or AWS API call fails
    """
    try:
        client = get_aws_client('networkmanager', region, profile_name)

        if policy_version_id is not None:
            response = client.get_core_network_policy(
                CoreNetworkId=core_network_id, PolicyVersionId=policy_version_id
            )
        else:
            response = client.get_core_network_policy(CoreNetworkId=core_network_id, Alias='LIVE')

        policy_data = response.get('CoreNetworkPolicy', {})
        policy_document = json.loads(policy_data.get('PolicyDocument', '{}'))

        return {
            'core_network_id': policy_data.get('CoreNetworkId'),
            'policy_version_id': policy_data.get('PolicyVersionId'),
            'policy_document': policy_document,
            'change_set_state': policy_data.get('ChangeSetState'),
            'policy_errors': policy_data.get('PolicyErrors', []),
        }

    except client.exceptions.ResourceNotFoundException:
        raise ToolError(
            f'Core network or policy not found for ID: {core_network_id}. '
            'VALIDATE the core_network_id parameter before continuing.'
        )
    except Exception as e:
        raise ToolError(
            f'Error getting Cloud WAN policy document: {str(e)}. '
            'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
