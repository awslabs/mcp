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
from typing import Annotated, Any, Dict, List, Optional


async def get_tgw_flow_logs(
    tgw_id: Annotated[str, Field(..., description='Transit Gateway ID to search flow logs for.')],
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region to search the Transit Gateway and Logs from'),
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
    tgw_attachment_id: Annotated[
        Optional[str],
        Field(..., description='Transit Gateway Attachment ID to filter the flow logs.'),
    ] = None,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> List[Dict[str, Any]]:
    """Retrieve Transit Gateway flow logs from CloudWatch Logs for traffic analysis and troubleshooting.

    Use this tool when:
    - Investigating connectivity issues through a Transit Gateway
    - Analyzing traffic patterns between VPCs or attachments
    - Verifying if traffic is reaching the Transit Gateway
    - Troubleshooting packet loss or routing issues
    - Confirming source/destination IP addresses and ports

    Prerequisites:
    - Flow logs must be enabled on the Transit Gateway
    - Flow logs must be configured to send to CloudWatch Logs (not S3)
    - Sufficient time must have passed for logs to be generated

    Time range configuration:
    - time_period: Minutes to look back in history (default: 60)
    - start_time: Optional end point for the time window (ISO 8601 format)
    - If start_time is provided: Query from (start_time - time_period) to start_time
    - If start_time is NOT provided: Query from (now - time_period) to now
    - Examples:
      * time_period=30 → Last 30 minutes from now
      * start_time='2024-01-15T10:00:00Z', time_period=30 → 09:30 to 10:00
      * start_time='2024-01-15T10:00:00Z' → 09:00 to 10:00 (default 60 min)

    Common troubleshooting workflow:
    1. Start with broad search (just tgw_id)
    2. Add filters (srcaddr, dstaddr, ports) to narrow results
    3. Check log_status field: 'OK' = successful, 'NODATA' = no traffic
    4. Examine packets_lost_* fields to identify packet loss causes

    Returns:
    List of flow log entries with fields including:
    - srcaddr/dstaddr: Source and destination IP addresses
    - srcport/dstport: Source and destination ports
    - tgw_attachment_id: Which attachment handled the traffic
    - packets/bytes: Traffic volume
    - log_status: 'OK', 'NODATA', 'SKIPDATA'
    - packets_lost_*: Packet loss reasons (no_route, blackhole, mtu_exceeded, ttl_expired)

    Limitations:
    - Returns maximum 100 entries by default (use entry_limit to adjust)
    - Searches last 60 minutes by default (use time_period to adjust)
    - Requires flow logs to be stored in CloudWatch Logs
    - Flow logs have ~5-15 minute delay from actual traffic
    """
    try:
        ec2_client = get_aws_client('ec2', region, profile_name)

        response = ec2_client.describe_flow_logs(
            Filters=[
                {'Name': 'resource-id', 'Values': [tgw_id]},
            ]
        )

        if response.get('FlowLogs') is None:
            raise ToolError(
                f'There are no flow logs for the Transit Gateway {tgw_id}. VALIDATE PARAMETERS BEFORE CONTINUING.'
            )

        log_group_name = None
        for flow_log in response['FlowLogs']:
            if flow_log.get('LogDestinationType') == 'cloud-watch-logs':
                log_group_name = flow_log.get('LogGroupName')
                break

        if not log_group_name:
            raise ToolError(
                f'The flow log for the Transit Gateway {tgw_id} is not stored in CloudWatch Logs. VALIDATE PARAMETERS BEFORE CONTINUING.'
            )

        logs_client = get_aws_client('logs', region)

        time_period = time_period if time_period else 60

        if start_time:
            end_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            end_time = datetime.now(timezone.utc)

        start_time_dt = end_time - timedelta(minutes=time_period)

        query_string = 'fields @timestamp, @message | parse @message /(?<version>\\d+) (?<resource_type>\\S+) (?<account_id>\\S+) (?<tgw_id>\\S+) (?<tgw_attachment_id>\\S+) (?<tgw_src_vpc_account_id>\\S+) (?<tgw_dst_vpc_account_id>\\S+) (?<tgw_src_vpc_id>\\S+) (?<tgw_dst_vpc_id>\\S+) (?<tgw_src_subnet_id>\\S+) (?<tgw_dst_subnet_id>\\S+) (?<tgw_src_eni>\\S+) (?<tgw_dst_eni>\\S+) (?<tgw_src_az_id>\\S+) (?<tgw_dst_az_id>\\S+) (?<tgw_pair_attachment_id>\\S+) (?<srcaddr>\\S+) (?<dstaddr>\\S+) (?<srcport>\\d+) (?<dstport>\\d+) (?<protocol>\\d+) (?<packets>\\d+) (?<bytes>\\d+) (?<start>\\d+) (?<end>\\d+) (?<log_status>\\S+) (?<type>\\S+) (?<packets_lost_no_route>\\d+) (?<packets_lost_blackhole>\\d+) (?<packets_lost_mtu_exceeded>\\d+) (?<packets_lost_ttl_expired>\\d+)/'

        filter = ''
        if srcaddr:
            filter += f"{'and ' if filter else ''}srcaddr = '{srcaddr}' "
        if dstaddr:
            filter += f"{'and ' if filter else ''}dstaddr = '{dstaddr}' "
        if srcport:
            filter += f'{"and " if filter else ""}srcport = {srcport} '
        if dstport:
            filter += f'{"and " if filter else ""}dstport = {dstport} '
        if tgw_attachment_id:
            filter += f"{'and ' if filter else ''}tgw_attachment_id = '{tgw_attachment_id}' "

        if filter:
            query_string += f' | filter {filter}'

        query_string += ' | sort @timestamp desc'

        response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=int(start_time_dt.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query_string,
            limit=entry_limit if entry_limit else 100,
        )

        query_id = response['queryId']

        while True:
            query_response = logs_client.get_query_results(queryId=query_id)
            if query_response['status'] == 'Complete':
                if query_response['results'] == []:
                    raise ToolError(
                        'No flow logs found for the Transit Gateway with given parameters. VALIDATE PARAMETERS BEFORE CONTINUING.'
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
                        'resource_type': message[1],
                        'account_id': message[2],
                        'tgw_id': message[3],
                        'tgw_attachment_id': message[4],
                        'tgw_src_vpc_account_id': message[5],
                        'tgw_dst_vpc_account_id': message[6],
                        'tgw_src_vpc_id': message[7],
                        'tgw_dst_vpc_id': message[8],
                        'tgw_src_subnet_id': message[9],
                        'tgw_dst_subnet_id': message[10],
                        'tgw_src_eni': message[11],
                        'tgw_dst_eni': message[12],
                        'tgw_src_az_id': message[13],
                        'tgw_dst_az_id': message[14],
                        'tgw_pair_attachment_id': message[15],
                        'srcaddr': message[16],
                        'dstaddr': message[17],
                        'srcport': message[18],
                        'dstport': message[19],
                        'protocol': message[20],
                        'packets': message[21],
                        'bytes': message[22],
                        'start': message[23],
                        'end': message[24],
                        'log_status': message[25],
                        'type': message[26],
                        'packets_lost_no_route': message[27],
                        'packets_lost_blackhole': message[28],
                        'packets_lost_mtu_exceeded': message[29],
                        'packets_lost_ttl_expired': message[30],
                    }
                    logs_result.append(message)
                    break

        return logs_result
    except Exception as e:
        raise ToolError(
            f'Error getting Transit Gateway flow logs. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
