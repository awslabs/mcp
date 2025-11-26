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
import time
from awslabs.aws_network_mcp_server.utils.aws_common import get_aws_client
from datetime import datetime, timedelta, timezone
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def get_cwan_logs(
    time_period: Annotated[
        Optional[int],
        Field(
            ...,
            description='How many minutes into history to get the logs for. By default this is 180 minutes',
        ),
    ] = 180,
    event_type: Annotated[
        Optional[str], Field(..., description='Event type to filter logs')
    ] = None,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Retrieve AWS Cloud WAN event logs for troubleshooting topology changes and routing updates.

    Use this tool when:
    - Investigating recent Cloud WAN connectivity issues or outages
    - Analyzing topology changes (attachment additions/removals, segment changes)
    - Tracking routing updates and propagation across the core network
    - Correlating network events with specific timestamps
    - Auditing Cloud WAN configuration changes over time

    Common troubleshooting scenarios:
    - "Why did connectivity break 2 hours ago?"
    - "What attachments were recently added or removed?"
    - "When did routing change for this segment?"
    - "Show me all topology changes in the last day"

    Event types available for filtering:
    - "Network Manager Topology Change": Attachment/segment modifications, peering changes
    - "Network Manager Routing Update": Route propagation, routing table updates

    Important limitations:
    - Only works with default AWS Cloud WAN logging (us-west-2, /aws/events/networkmanagerloggroup)
    - Maximum lookback period depends on log retention settings
    - Returns up to 10 most recent events matching criteria

    Returns:
        Dict containing:
        - summary: Event counts by change type and edge location
        - events_by_location: Grouped events with timestamps, change descriptions, segments, and ARNs
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=time_period if time_period else 180)

    query_string = 'fields @timestamp, @message'
    sort = ' | sort @timestamp desc'

    filter = None
    if event_type:
        if event_type == 'Network Manager Topology Change':
            filter = ' | filter @message like /"detail-type":"Network Manager Topology Change"/'
        elif event_type == 'Network Manager Routing Update':
            filter = ' | filter @message like /"detail-type":"Network Manager Routing Update"/'
        else:
            raise ToolError(
                f'Event type {event_type} is not supported. Supported types are: Network Manager Topology Change, Network Manager Routing Update'
            )

    query_string = query_string + (filter or '') + sort

    try:
        logs_client = get_aws_client('logs', 'us-west-2', profile_name)

        response = logs_client.start_query(
            logGroupName='/aws/events/networkmanagerloggroup',
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query_string,
            limit=10,
        )

        query_id = response['queryId']

        while True:
            query_response = logs_client.get_query_results(queryId=query_id)
            if query_response['status'] == 'Complete':
                if query_response['results'] == []:
                    raise ToolError(
                        'No flow logs found for the AWS Network Firewall. REQUIRED TO VALIDATE PARAMETERS BEFORE CONTINUING'
                    )
                else:
                    break
            elif query_response['status'] == 'Failed' or query_response['status'] == 'Timeout':
                raise ToolError(
                    f'There was an error with the query. Query status: {query_response["status"]}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
                )
            else:
                time.sleep(1)

    except Exception as e:
        raise ToolError(
            f'There was an error getting AWS Cloud WAN logs. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    logs_result = []
    for result in query_response['results']:
        for field in result:
            if field.get('field') == '@message':
                logs_result.append(json.loads(field.get('value')))

    # Group and format logs
    grouped = {}
    summary = {'total_events': len(logs_result), 'by_change_type': {}, 'by_edge_location': {}}

    for log in logs_result:
        detail = log.get('detail', {})
        change_type = detail.get('changeType', 'UNKNOWN')
        edge_location = detail.get('edgeLocation', 'UNKNOWN')

        # Update summary
        summary['by_change_type'][change_type] = summary['by_change_type'].get(change_type, 0) + 1
        summary['by_edge_location'][edge_location] = (
            summary['by_edge_location'].get(edge_location, 0) + 1
        )

        # Group by edge location
        if edge_location not in grouped:
            grouped[edge_location] = []

        grouped[edge_location].append(
            {
                'timestamp': log.get('time'),
                'change_type': change_type,
                'description': detail.get('changeDescription'),
                'segment': detail.get('segmentName'),
                'attachment_arn': detail.get('attachmentArn'),
                'core_network_arn': detail.get('coreNetworkArn'),
            }
        )

    return {'summary': summary, 'events_by_location': grouped}
