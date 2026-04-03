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
from awslabs.aws_network_mcp_server.utils.aws_common import get_account_id, get_aws_client
from datetime import datetime, timedelta, timezone
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, List, Optional


async def get_firewall_flow_logs(
    firewall_name: Annotated[
        str, Field(..., description='AWS Network Firewall name to search flow logs for.')
    ],
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the AWS Network Firewall is located.'),
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
            description='How many minutes in to the past to search logs from. By default searching for past 1 hour',
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
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> List[str]:
    """Retrieve AWS Network Firewall flow logs from CloudWatch Logs for traffic analysis and troubleshooting.

    Use this tool when:
    - Investigating traffic patterns through AWS Network Firewall
    - Troubleshooting connectivity issues involving firewall inspection
    - Verifying that traffic is being processed by the firewall
    - Analyzing blocked or allowed traffic flows
    - Correlating firewall activity with network incidents

    Workflow:
    1. Start with basic query (firewall_name only) to see recent traffic
    2. Add filters (srcaddr, dstaddr, ports) to narrow down specific flows
    3. Adjust time_period if looking for historical patterns
    4. Increase entry_limit if more log entries are needed

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
    - Source/destination IP addresses (IPv4 or IPv6)
    - Source/destination ports
    - Entry limit (default: 100 logs)

    Prerequisites:
    - Network Firewall must have flow logging enabled to CloudWatch Logs
    - If logs are not found, verify logging configuration in AWS Console

    Returns:
        List of flow log entries (most recent first), each containing:
        - Timestamp, source/destination IPs and ports
        - Protocol, packet/byte counts
        - VPC and subnet information
        - Log status and packet loss metrics

    Common troubleshooting scenarios:
    - "Is traffic reaching the firewall?" - Check for matching srcaddr/dstaddr
    - "Why is connection failing?" - Look for log_status and packet loss fields
    - "What traffic is the firewall seeing?" - Query without filters for overview
    """
    try:
        fw_client = get_aws_client('network-firewall', region, profile_name)

        response = fw_client.describe_logging_configuration(
            FirewallArn=f'arn:aws:network-firewall:{region if region else "us-east-1"}:{get_account_id()}:firewall/{firewall_name}'
        )

        log_group_name = None
        for log_config in response.get('LoggingConfiguration', {}).get(
            'LogDestinationConfigs', []
        ):
            if (
                log_config['LogType'] == 'FLOW'
                and log_config['LogDestinationType'] == 'CloudWatchLogs'
            ):
                log_group_name = log_config['LogDestination']['logGroup']
                break

        if not log_group_name:
            raise ToolError(
                f'Instruction for the LLM that need validation before you can move forward. The flow log for the AWS Network Firewall named {firewall_name} are not stored in CloudWatch Logs. Request user to validate if the logs are stored in CloudWatch logs. Then try again with validated values.'
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
                        'No flow logs found for the AWS Network Firewall with given parameters. VALIDATE PARAMETERS BEFORE CONTINUING'
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
                    logs_result.append(field.get('value'))

        return logs_result
    except Exception as e:
        raise ToolError(
            f'Error getting AWS Network Firewall flow logs. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
