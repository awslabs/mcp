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

import boto3
import botocore.config
import json
from ..utils.failure_cases import match_failure_case
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class StackEvent:
    """CloudFormation stack event."""

    timestamp: datetime
    resource_type: str
    logical_resource_id: str
    resource_status: str
    resource_status_reason: Optional[str] = None


@dataclass
class FailedResource:
    """Failed CloudFormation resource."""

    logical_id: str
    resource_type: str
    status: str
    status_reason: str
    timestamp: datetime
    cloudtrail_link: Optional[str] = None


@dataclass
class DeploymentResponse:
    """Complete deployment troubleshooting response."""

    stack_name: str
    stack_status: str
    failed_resources: List[FailedResource]
    events: List[StackEvent]
    root_cause_analysis: str
    remediation_steps: List[str]
    console_deeplink: str

    def model_dump(self) -> dict:
        """Convert to dict for compatibility with existing code."""
        return asdict(self)


# CloudFormation's source IP in CloudTrail events
CLOUDTRAIL_SOURCE_IP_FOR_CLOUDFORMATION = 'cloudformation.amazonaws.com'

session_config = botocore.config.Config(
    user_agent_extra='aws-iac-mcp-server/1.0.0',
)


class DeploymentTroubleshooter:
    """Troubleshoots CloudFormation deployment failures using describe_events API with CloudTrail.

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
    - Returned as JSON to MCP server
    - Garbage collected when function completes
    - Text representation persists in LLM agent's conversation context until session ends
    """

    def __init__(self, region: str = 'us-east-1'):
        """Initialize troubleshooter with AWS region."""
        self.region = region
        self.cfn_client = boto3.client('cloudformation', region_name=region, config=session_config)
        self.cloudtrail_client = boto3.client(
            'cloudtrail', region_name=region, config=session_config
        )

    def filter_cloudtrail_events(
        self, cloudtrail_events: List[Dict], cloudformation_events: List[Dict]
    ) -> Dict[str, Any]:
        """Filter CloudTrail events based on CFN Console logic.

        Filters for:
        1. Events from CloudFormation service (sourceIPAddress)
        2. Events with error codes
        3. Events matching failed resources
        """
        cloudtrail_events_list = []
        cloudtrail_url = ''

        if not cloudformation_events:
            return {'cloudtrail_events': [], 'cloudtrail_url': '', 'has_relevant_events': False}

        # Use first failed event for time window
        first_event = cloudformation_events[0]
        timestamp = first_event.get('Timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        if not isinstance(timestamp, datetime):
            return {'cloudtrail_events': [], 'cloudtrail_url': '', 'has_relevant_events': False}

        start_time = (timestamp - timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%S.%f')[
            :-3
        ] + 'Z'
        end_time = (timestamp + timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        # Base CloudTrail URL
        base_url = f'https://console.aws.amazon.com/cloudtrailv2/home?region={self.region}#/events'
        cloudtrail_url = f'{base_url}?StartTime={start_time}&EndTime={end_time}&ReadOnly=false'

        for event in cloudtrail_events:
            cloudtrail_event_data = json.loads(event.get('CloudTrailEvent', '{}'))

            # Filter for CloudFormation-initiated events with errors
            has_error = cloudtrail_event_data.get('errorCode') or cloudtrail_event_data.get(
                'errorMessage'
            )
            is_cfn_event = (
                cloudtrail_event_data.get('sourceIPAddress')
                == CLOUDTRAIL_SOURCE_IP_FOR_CLOUDFORMATION
            )

            if is_cfn_event and has_error:
                event_info = {
                    'event_name': event.get('EventName'),
                    'event_time': str(event.get('EventTime')),
                    'error_code': cloudtrail_event_data.get('errorCode', ''),
                    'error_message': cloudtrail_event_data.get('errorMessage', ''),
                    'username': event.get('Username', ''),
                }
                cloudtrail_events_list.append(event_info)

        return {
            'cloudtrail_events': cloudtrail_events_list,
            'cloudtrail_url': cloudtrail_url,
            'has_relevant_events': len(cloudtrail_events_list) > 0,
        }

    def troubleshoot_stack_deployment(
        self,
        stack_name: str,
        include_cloudtrail: bool = True
    ) -> DeploymentResponse:
        """Collect CloudFormation failure events using describe_events API.

        Args:
            stack_name: Name of the CloudFormation stack
            include_cloudtrail: Whether to include CloudTrail analysis

        Returns:
            DeploymentResponse with deployment troubleshooting results
        """
        try:
            # Get stack status
            try:
                stacks = self.cfn_client.describe_stacks(StackName=stack_name)['Stacks']
                if not stacks:
                    raise Exception(f'Stack {stack_name} not found')
                stack_status = stacks[0].get('StackStatus', 'UNKNOWN')
            except self.cfn_client.exceptions.ClientError as e:
                raise Exception(f'Stack {stack_name} not found or inaccessible: {str(e)}')

            # Get failed events only using new API
            cloudformation_events = self.cfn_client.describe_events(
                StackName=stack_name, Filters={'FailedEvents': True}
            )['OperationEvents']

            # Convert events to StackEvent models
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
                            f'https://console.aws.amazon.com/cloudtrailv2/home?region={self.region}#/events'
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
                operation = None
                if 'DELETE' in event.get('ResourceStatus', ''):
                    operation = 'DELETE'
                elif 'CREATE' in event.get('ResourceStatus', ''):
                    operation = 'CREATE'
                elif 'UPDATE' in event.get('ResourceStatus', ''):
                    operation = 'UPDATE'

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
                f'region={self.region}#/stacks/stackinfo?stackId={stack_name}'
            )

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
                console_deeplink=f'https://console.aws.amazon.com/cloudformation/home?region={self.region}',
            )
