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
from .failure_cases import match_failure_case
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


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
        self, stack_name: str, include_cloudtrail: bool = True
    ) -> Dict[str, Any]:
        """Collect CloudFormation failure events using describe_events API."""
        try:
            response = {
                'status': 'success',
                'stack_name': stack_name,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'raw_data': {},
            }

            # Get stack status
            try:
                stacks = self.cfn_client.describe_stacks(StackName=stack_name)['Stacks']
                if not stacks:
                    raise Exception(f'Stack {stack_name} not found')
                response['raw_data']['stack_status'] = stacks[0].get('StackStatus')
            except self.cfn_client.exceptions.ClientError as e:
                raise Exception(f'Stack {stack_name} not found or inaccessible: {str(e)}')

            # Get failed events only using new API
            cloudformation_events = self.cfn_client.describe_events(
                StackName=stack_name, Filters={'FailedEvents': True}
            )['OperationEvents']

            # Match events against known failure patterns
            matched_failures = []
            for event in cloudformation_events:
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
                if matched_case:
                    matched_failures.append({'event': event, 'matched_case': matched_case})

            response['raw_data']['cloudformation_events'] = cloudformation_events
            response['raw_data']['matched_failures'] = matched_failures
            response['raw_data']['failed_event_count'] = len(cloudformation_events)
            response['raw_data']['matched_failure_count'] = len(matched_failures)

            # Get CloudTrail events if enabled and we have failures
            if include_cloudtrail and cloudformation_events:
                error_event = next(
                    (
                        e
                        for e in cloudformation_events
                        if e.get('EventType') in ['PROVISIONING_ERROR', 'VALIDATION_ERROR']
                    ),
                    cloudformation_events[0],
                )
                event_time = error_event.get('Timestamp')
                if isinstance(event_time, str):
                    event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))

                cloudtrail_start = event_time - timedelta(seconds=60)
                cloudtrail_end = event_time + timedelta(seconds=60)

                trail_events = self.cloudtrail_client.lookup_events(
                    StartTime=cloudtrail_start,
                    EndTime=cloudtrail_end,
                    LookupAttributes=[{'AttributeKey': 'ReadOnly', 'AttributeValue': 'false'}],
                    MaxResults=50,
                )['Events']

                cloudtrail_result = self.filter_cloudtrail_events(
                    trail_events, cloudformation_events
                )
                response['raw_data']['filtered_cloudtrail'] = cloudtrail_result

            return json.loads(json.dumps(response, default=str))
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'stack_name': stack_name,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
            }
