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

import time
from awslabs.aws_network_mcp_server.utils.aws_common import get_aws_client
from datetime import datetime, timedelta, timezone
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Dict, List, Optional


async def get_vpc_flow_logs(
    vpc_id: Annotated[str, Field(..., description='VPC ID to search flow logs for.')],
    region: Annotated[
        Optional[str], Field(..., description='AWS region to search the VPC and Logs from')
    ] = None,
    entry_limit: Annotated[
        Optional[str],
        Field(
            ..., description='How many entries of flow logs to try to get. Default 100 entries.'
        ),
    ] = None,
    time_period: Annotated[
        Optional[int],
        Field(
            ...,
            description='How many minutes in to the past to search logs from. By default searching for past 60 minutes',
        ),
    ] = None,
    start_time: Annotated[
        Optional[str],
        Field(
            ...,
            description="Specific start time in ISO 8601 format (e.g., '2024-01-15T10:30:00Z'). If provided, time_period goes backwards from this time.",
        ),
    ] = None,
    action: Annotated[
        Optional[str],
        Field(
            ...,
            description='Action to filter the flow logs. Allowed values are ACCEPT and REJECT.',
        ),
    ] = None,
    srcaddr: Annotated[
        Optional[str],
        Field(
            ...,
            description='Source IP address to filter the flow logs. IP Address needs to be in IPv4 or IPv6 format',
        ),
    ] = None,
    dstaddr: Annotated[
        Optional[str],
        Field(
            ...,
            description='Destination IP address to filter the flow logs. IP Address needs to be in IPv4 or IPv6 format',
        ),
    ] = None,
    srcport: Annotated[
        Optional[int], Field(..., description='Source port to filter the flow logs.')
    ] = None,
    dstport: Annotated[
        Optional[int], Field(..., description='Destination port to filter the flow logs.')
    ] = None,
    interface_id: Annotated[
        Optional[str], Field(..., description='Interface ID to filter the flow logs.')
    ] = None,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> List[Dict[str, str]]:
    """Get VPC Flow Logs stored in CloudWatch Logs.

    Use this tool when:
    - Investigating connectivity issues between resources in a VPC
    - Analyzing traffic patterns to/from specific IP addresses or ports
    - Troubleshooting security group or NACL rule effectiveness
    - Verifying if traffic is being accepted or rejected
    - Identifying which network interfaces are handling specific traffic flows

    Workflow:
    1. Start with basic VPC ID to see recent traffic
    2. Add filters (srcaddr, dstaddr, ports, action) to narrow down specific flows
    3. Analyze results to identify traffic patterns or issues
    4. Use interface_id from results with get_eni_details() for deeper analysis

    Time range configuration:
    - time_period: Minutes to look back in history (default: 60)
    - start_time: Optional end point for the time window (ISO 8601 format)
    - If start_time is provided: Query from (start_time - time_period) to start_time
    - If start_time is NOT provided: Query from (now - time_period) to now
    - Examples:
      * time_period=30 → Last 30 minutes from now
      * start_time='2024-01-15T10:00:00Z', time_period=30 → 09:30 to 10:00
      * start_time='2024-01-15T10:00:00Z' → 09:00 to 10:00 (default 60 min)

    Filtering options:
    - action: Filter by ACCEPT or REJECT to see allowed/blocked traffic
    - srcaddr/dstaddr: Filter by source/destination IP addresses
    - srcport/dstport: Filter by source/destination ports
    - interface_id: Filter by specific network interface
    - entry_limit: Maximum number of entries to return (default: 100)

    Common troubleshooting scenarios:
    - "Why can't I connect to this IP?" → Filter by dstaddr and action=REJECT
    - "Is traffic reaching my instance?" → Filter by interface_id
    - "What's talking to this port?" → Filter by dstport

    Limitations:
    - Returns maximum 100 log entries by default (use entry_limit to adjust)
    - Searches last 60 minutes by default (use time_period to adjust)
    - Only works if VPC Flow Logs are enabled and sent to CloudWatch Logs
    - Requires flow logs to be configured for the VPC
    - Flow logs have ~5-15 minute delay from actual traffic

    Returns:
        List of dicts: VPC flow logs with fields: version, account_id, interface_id,
        srcaddr, dstaddr, srcport, dstport, protocol, packets, bytes, start, end,
        action, logstatus
    """
    try:
        ec2_client = get_aws_client('ec2', region, profile_name)

        response = ec2_client.describe_flow_logs(
            Filters=[
                {'Name': 'resource-id', 'Values': [vpc_id]},
            ]
        )

        if response.get('FlowLogs') is None:
            raise ToolError(
                f'There are no flow logs for the VPC {vpc_id}. VALIDATE PARAMETERS BEFORE CONTINUING.'
            )

        log_group_name = None
        for flow_log in response['FlowLogs']:
            if flow_log.get('LogDestinationType') == 'cloud-watch-logs':
                log_group_name = flow_log.get('LogGroupName')
                break

        if not log_group_name:
            raise ToolError(
                f'The flow log for the VPC {vpc_id} is not stored in CloudWatch Logs. REQUIRED TO REMEDIATE BEFORE CONTINUING'
            )

        logs_client = get_aws_client('logs', region)

        time_period = time_period if time_period else 60

        if start_time:
            end_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            end_time = datetime.now(timezone.utc)

        start_time_dt = end_time - timedelta(minutes=time_period)

        query_string = 'fields @timestamp, @message | parse @message /(?<version>\\d+) (?<account_id>\\S+) (?<interface_id>\\S+) (?<srcaddr>\\S+) (?<dstaddr>\\S+) (?<srcport>\\d+) (?<dstport>\\d+) (?<protocol>\\d+) (?<packets>\\d+) (?<bytes>\\d+) (?<start>\\d+) (?<end>\\d+) (?<action>\\S+) (?<logstatus>\\S+)/'
        sort_string = ' | sort @timestamp desc'
        filter = ''
        if action:
            if filter != '':
                filter = filter + 'and '
            filter = filter + f"action = '{action}' "
        if srcaddr:
            if filter != '':
                filter = filter + 'and '
            filter = filter + f"srcaddr = '{srcaddr}' "
        if dstaddr:
            if filter != '':
                filter = filter + 'and '
            filter = filter + f"dstaddr = '{dstaddr}' "
        if srcport:
            if filter != '':
                filter = filter + 'and '
            filter = filter + f'srcport = {srcport} '
        if dstport:
            if filter != '':
                filter = filter + 'and '
            filter = filter + f"dstport = '{dstport}' "
        if interface_id:
            if filter != '':
                filter = filter + 'and '
            filter = filter + f"interface_id = '{interface_id}' "

        if filter != '':
            filter = f' | filter {filter}'

        response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=int(start_time_dt.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query_string + filter + sort_string,
            limit=entry_limit if entry_limit else 100,
        )

        query_id = response['queryId']

        while True:
            query_response = logs_client.get_query_results(queryId=query_id)
            if query_response['status'] == 'Complete':
                if query_response['results'] == []:
                    raise ToolError(
                        'No flow logs found for the VPC with given parameters. VALIDATE PARAMETERS BEFORE CONTINUING.'
                    )
                else:
                    break
            elif query_response['status'] == 'Failed' or query_response['status'] == 'Timeout':
                raise ToolError(
                    f'There was an error with the query. Query status: {query_response["status"]}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
                )
            else:
                time.sleep(1)

        logs_result = []
        for result in query_response['results']:
            for field in result:
                if field.get('field') == '@message':
                    message = field.get('value')
                    message = message.split(' ')
                    message = {
                        'version': message[0],
                        'account_id': message[1],
                        'interface_id': message[2],
                        'srcaddr': message[3],
                        'dstaddr': message[4],
                        'srcport': message[5],
                        'dstport': message[6],
                        'protocol': message[7],
                        'packets': message[8],
                        'bytes': message[9],
                        'start': message[10],
                        'end': message[11],
                        'action': message[12],
                        'logstatus': message[13],
                    }
                    logs_result.append(message)
                    break

        return logs_result
    except Exception as e:
        raise ToolError(
            f'Error getting VPC flow logs. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
