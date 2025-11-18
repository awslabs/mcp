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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


# CloudFormation's source IP in CloudTrail events
CLOUDTRAIL_SOURCE_IP_FOR_CLOUDFORMATION = 'cloudformation.amazonaws.com'

session_config = botocore.config.Config(
    user_agent_extra='iac-mcp-server/1.0.0',
)


class DeploymentTroubleshooter:
    """Troubleshoots CloudFormation deployment failures by fetching stack events and CloudTrail logs.

    This MCP server executes AWS API calls using your credentials and shares the response data with
    your third-party AI model provider (e.g., Q, Claude Desktop, Kiro, Cline). Users are
    responsible for understanding your AI provider's data handling practices and ensuring
    compliance with your organization's security and privacy requirements when using this tool
    with AWS resources.

    Data retrieved:
    - CloudFormation stack events (describe_stacks, describe_stack_events)
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
        self, cloudtrail_events: List[Dict], root_cause_event: Dict
    ) -> Dict[str, Any]:
        """Filter CloudTrail events based on CFN Console logic.

        Filters for:
        1. Events from CloudFormation service (sourceIPAddress)
        2. Events with error codes
        3. Events matching the failed resource
        """
        filtered_events = []
        cloudtrail_url = ''

        if not root_cause_event:
            return {'filtered_events': [], 'cloudtrail_url': '', 'has_relevant_events': False}

        timestamp = root_cause_event.get('Timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        if not isinstance(timestamp, datetime):
            return {'filtered_events': [], 'cloudtrail_url': '', 'has_relevant_events': False}

        start_time = (timestamp - timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%S.%f')[
            :-3
        ] + 'Z'
        end_time = (timestamp + timedelta(seconds=60)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        # Base CloudTrail URL - use standard console domain
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
                filtered_events.append(event_info)

        return {
            'filtered_events': filtered_events,
            'cloudtrail_url': cloudtrail_url,
            'has_relevant_events': len(filtered_events) > 0,
        }

    def filter_cloudformation_stack_events(self, events: List[Dict]) -> Dict[str, Any]:
        """Filter cancelled events to identify root cause failures."""
        failed_events = []
        cancelled_events = []

        for event in events:
            status = event.get('ResourceStatus', '')
            reason = event.get('ResourceStatusReason', '')

            if 'FAILED' in status:
                if (
                    'cancelled' in reason.lower()
                    or 'resource creation cancelled' in reason.lower()
                ):
                    cancelled_events.append(event)
                else:
                    failed_events.append(event)

        root_cause = failed_events[0] if failed_events else None

        return {
            'root_cause_event': root_cause,
            'actual_failures': failed_events,
            'cascading_cancellations': cancelled_events,
            'analysis': f'Found {len(failed_events)} actual failures and {len(cancelled_events)} cascading cancellations',
        }

    def troubleshoot_stack_deployment(
        self,
        stack_name: str,
        include_logs: bool = True,
        include_cloudtrail: bool = True,
        failure_timestamp: Optional[datetime] = None,
        symptoms_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Collect comprehensive CloudFormation stack data for LLM analysis."""
        try:
            if failure_timestamp is None:
                raise ValueError('failure_timestamp is required')
            # Ensure failure_timestamp is timezone-aware
            if failure_timestamp.tzinfo is None:
                failure_timestamp = failure_timestamp.replace(tzinfo=timezone.utc)

            analysis_start_time = failure_timestamp - timedelta(minutes=2)
            analysis_stop_time = failure_timestamp + timedelta(minutes=2)

            response = {
                'status': 'success',
                'stack_name': stack_name,
                'analysis_timestamp': analysis_start_time.isoformat(),
                'timewindow_start': analysis_start_time,
                'timewindow_stop': analysis_stop_time,
                'assessment': '',
                'raw_data': {},
            }

            # Get stack info and events
            try:
                stacks = self.cfn_client.describe_stacks(StackName=stack_name)['Stacks']
                if not stacks:
                    raise Exception(f'Stack {stack_name} not found')
                stack_info = stacks[0]
                response['raw_data']['stack_status'] = stack_info.get('StackStatus')

                # Get events - works for all stack states including ROLLBACK_COMPLETE
                cfn_events = self.cfn_client.describe_stack_events(StackName=stack_name)[
                    'StackEvents'
                ]
            except self.cfn_client.exceptions.ClientError as e:
                raise Exception(f'Stack {stack_name} not found or inaccessible: {str(e)}')

            cloudformation_events = [
                e
                for e in cfn_events
                if analysis_start_time <= e['Timestamp'] <= analysis_stop_time
            ]

            # Filter root cause events
            filtered_result = self.filter_cloudformation_stack_events(cloudformation_events)
            response['raw_data']['filtered_events'] = filtered_result

            # Lookup CloudTrail events if enabled
            if include_cloudtrail:
                root_cause = filtered_result.get('root_cause_event')

                # Lookup CloudTrail events in the failure window
                cloudtrail_start = failure_timestamp - timedelta(seconds=60)
                cloudtrail_end = failure_timestamp + timedelta(seconds=60)

                # Server-side filtering for write operations only (matches CFN Console)
                trail_events = self.cloudtrail_client.lookup_events(
                    StartTime=cloudtrail_start,
                    EndTime=cloudtrail_end,
                    LookupAttributes=[{'AttributeKey': 'ReadOnly', 'AttributeValue': 'false'}],
                    MaxResults=50,
                )['Events']

                # Filter CloudTrail events using CFN Console logic
                cloudtrail_result = self.filter_cloudtrail_events(trail_events, root_cause or {})
                response['raw_data']['cloudtrail_events'] = trail_events
                response['raw_data']['filtered_cloudtrail'] = cloudtrail_result

                # Log CloudTrail events (first 10) with deep link

                # Check if events are missing due to indexing delay

            # Convert all datetime objects to strings for JSON serialization
            return json.loads(json.dumps(response, default=str))
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'stack_name': stack_name,
                'assessment': f'Error analyzing stack: {str(e)}',
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
            }
