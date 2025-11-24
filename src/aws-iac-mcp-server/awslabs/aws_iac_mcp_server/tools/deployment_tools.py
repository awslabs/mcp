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

"""CloudFormation deployment troubleshooting tools."""

import boto3
import botocore.config
from ..models.deployment_models import DeploymentResponse, FailedResource, StackEvent
from ..utils.failure_cases import match_failure_case
from datetime import datetime, timedelta
from typing import List, Optional


# CloudFormation's source IP in CloudTrail events
CLOUDTRAIL_SOURCE_IP_FOR_CLOUDFORMATION = 'cloudformation.amazonaws.com'

session_config = botocore.config.Config(
    user_agent_extra='aws-iac-mcp-server/1.0.0',
)


def troubleshoot_deployment(
    stack_name: str,
    region: str,
    include_cloudtrail: bool = True
) -> DeploymentResponse:
    """Troubleshoot CloudFormation deployment failures using describe_events API with CloudTrail.

    This MCP server executes AWS API calls using your credentials and shares the response data with
    your third-party AI model provider (e.g., Q, Claude Desktop, Kiro, Cline). Users are
    responsible for understanding your AI provider's data handling practices and ensuring
    compliance with your organization's security and privacy requirements when using this tool
    with AWS resources.

    Data retrieved:
    - CloudFormation stack events (describe_stacks, describe_events with FailedEvents filter)
    - CloudTrail API call logs (lookup_events)

    Data lifecycle:
    - Fetched from AWS APIs using user's configured credentials
    - Stored in memory during function execution
    - Returned as DeploymentResponse to MCP server
    - Garbage collected when function completes
    - Text representation persists in LLM agent's conversation context until session ends

    Args:
        stack_name: Name of the CloudFormation stack
        region: AWS region where the stack is deployed
        include_cloudtrail: Whether to include CloudTrail analysis

    Returns:
        DeploymentResponse with deployment troubleshooting results
    """
    try:
        # Create boto3 clients
        cfn_client = boto3.client('cloudformation', region_name=region, config=session_config)

        # Get stack status
        try:
            stacks = cfn_client.describe_stacks(StackName=stack_name)['Stacks']
            if not stacks:
                raise Exception(f'Stack {stack_name} not found')
            stack_status = stacks[0].get('StackStatus', 'UNKNOWN')
        except cfn_client.exceptions.ClientError as e:
            raise Exception(f'Stack {stack_name} not found or inaccessible: {str(e)}')

        # Get failed events only using describe_events API
        cloudformation_events = cfn_client.describe_events(
            StackName=stack_name, Filters={'FailedEvents': True}
        )['OperationEvents']

        # Convert events to dataclass models
        events: List[StackEvent] = []
        failed_resources: List[FailedResource] = []
        remediation_steps: List[str] = []

        for event in cloudformation_events:
            timestamp = event.get('Timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            # Add to events list
            events.append(
                StackEvent(
                    timestamp=timestamp,
                    resource_type=event.get('ResourceType', 'Unknown'),
                    logical_resource_id=event.get('LogicalResourceId', 'Unknown'),
                    resource_status=event.get('ResourceStatus', 'Unknown'),
                    resource_status_reason=event.get('ResourceStatusReason'),
                )
            )

            # Add to failed resources if it's a failure
            if 'FAILED' in event.get('ResourceStatus', ''):
                cloudtrail_link = None
                if include_cloudtrail:
                    # Generate CloudTrail link for this event
                    start_time = (timestamp - timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    end_time = (timestamp + timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    cloudtrail_link = (
                        f'https://console.aws.amazon.com/cloudtrailv2/home?region={region}#/events'
                        f'?StartTime={start_time}&EndTime={end_time}&ReadOnly=false'
                    )

                failed_resources.append(
                    FailedResource(
                        logical_id=event.get('LogicalResourceId', 'Unknown'),
                        resource_type=event.get('ResourceType', 'Unknown'),
                        status=event.get('ResourceStatus', 'Unknown'),
                        status_reason=event.get('ResourceStatusReason', 'No reason provided'),
                        timestamp=timestamp,
                        cloudtrail_link=cloudtrail_link,
                    )
                )

                # Match against known failure patterns for remediation
                error_reason = event.get('ResourceStatusReason', '')
                resource_type = event.get('ResourceType', '')

                # Determine operation from event type
                operation = _determine_operation(event.get('ResourceStatus', ''))

                matched_case = match_failure_case(error_reason, resource_type, operation)
                if matched_case and matched_case.get('remediation'):
                    remediation_steps.append(matched_case['remediation'])

        # Generate root cause analysis
        if failed_resources:
            root_cause_analysis = (
                f'Found {len(failed_resources)} failed resource(s). '
                f'Primary failure: {failed_resources[0].status_reason}'
            )
        else:
            root_cause_analysis = 'No failed resources found in stack events.'

        # Generate console deeplink
        console_deeplink = (
            f'https://console.aws.amazon.com/cloudformation/home?'
            f'region={region}#/stacks/stackinfo?stackId={stack_name}'
        )

        # Build and return response
        return DeploymentResponse(
            stack_name=stack_name,
            stack_status=stack_status,
            failed_resources=failed_resources,
            events=events,
            root_cause_analysis=root_cause_analysis,
            remediation_steps=remediation_steps if remediation_steps else ['Review stack events for details'],
            console_deeplink=console_deeplink,
        )

    except Exception as e:
        # Return error as DeploymentResponse
        return DeploymentResponse(
            stack_name=stack_name,
            stack_status='ERROR',
            failed_resources=[],
            events=[],
            root_cause_analysis=f'Error troubleshooting deployment: {str(e)}',
            remediation_steps=['Check stack name and AWS credentials', 'Verify stack exists in the specified region'],
            console_deeplink=f'https://console.aws.amazon.com/cloudformation/home?region={region}',
        )


def _determine_operation(resource_status: str) -> Optional[str]:
    """Determine operation type from resource status.

    Args:
        resource_status: CloudFormation resource status string

    Returns:
        Operation type (CREATE, UPDATE, DELETE) or None
    """
    if 'DELETE' in resource_status:
        return 'DELETE'
    elif 'CREATE' in resource_status:
        return 'CREATE'
    elif 'UPDATE' in resource_status:
        return 'UPDATE'
    return None
