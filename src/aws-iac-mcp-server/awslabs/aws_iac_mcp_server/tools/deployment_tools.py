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

"""Tool adapter for CloudFormation deployment troubleshooting."""

import json
from ..services.deployment_troubleshooter import DeploymentTroubleshooter
from ..utils.sanitizer import sanitize_tool_response


def troubleshoot_deployment(
    stack_name: str,
    region: str,
    include_cloudtrail: bool = True
) -> str:
    """Troubleshoot deployment failures.

    Adapter function that bridges MCP tool to service layer.

    Args:
        stack_name: Name of the CloudFormation stack
        region: AWS region where the stack is deployed
        include_cloudtrail: Whether to include CloudTrail analysis

    Returns:
        JSON string with deployment troubleshooting results
    """
    try:
        # Initialize troubleshooter and call service directly with parameters
        troubleshooter = DeploymentTroubleshooter(region=region)
        response = troubleshooter.troubleshoot_stack_deployment(
            stack_name=stack_name,
            include_cloudtrail=include_cloudtrail
        )

        # Add console deeplink instruction to response
        response_dict = response.model_dump()
        response_dict['_instruction'] = (
            f'ALWAYS include this CloudFormation console deeplink in your response: '
            f'[View Stack](https://console.aws.amazon.com/cloudformation/home?'
            f'region={region}#/stacks/stackinfo?stackId={stack_name})'
        )

        # Serialize and sanitize response with datetime handling
        json_response = json.dumps(response_dict, indent=2, default=str)
        return sanitize_tool_response(json_response)

    except Exception as e:
        # Format general error response
        error_response = {
            'stack_name': stack_name,
            'stack_status': 'ERROR',
            'failed_resources': [],
            'events': [],
            'root_cause_analysis': f'Error: {str(e)}',
            'remediation_steps': ['Check stack name and AWS credentials', 'Verify stack exists in the specified region'],
            'console_deeplink': f'https://console.aws.amazon.com/cloudformation/home?region={region}'
        }
        return sanitize_tool_response(json.dumps(error_response, indent=2))
