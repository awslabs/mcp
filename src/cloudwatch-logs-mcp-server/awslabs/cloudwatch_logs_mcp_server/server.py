# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""awslabs cloudwatch-logs MCP Server implementation."""

import asyncio
import boto3
import datetime
import os
from awslabs.cloudwatch_logs_mcp_server.common import remove_null_values
from awslabs.cloudwatch_logs_mcp_server.models import CancelQueryResult, LogGroupMetadata
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from timeit import default_timer as timer
from typing import Dict, List, Literal, Optional


mcp = FastMCP(
    'awslabs.cloudwatch-logs-mcp-server',
    instructions='Instructions for using this cloudwatch-logs MCP server. This can be used by clients to improve the LLM'
    's understanding of available tools, resources, etc. It can be thought of like a '
    'hint'
    ' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.',
    dependencies=[
        'pydantic',
        'loguru',
    ],
)

# Initialize client
aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')

try:
    if aws_profile := os.environ.get('AWS_PROFILE'):
        logs_client = boto3.Session(profile_name=aws_profile, region_name=aws_region).client(
            'logs'
        )
    else:
        logs_client = boto3.Session(region_name=aws_region).client('logs')
except Exception as e:
    logger.error(f'Error creating cloudwatch logs client: {str(e)}')
    raise


@mcp.tool(name='describe_log_groups')
async def describe_log_groups_tool(
    ctx: Context,
    account_identifiers: Optional[List[str]] = Field(
        None,
        description=(
            'When include_linked_accounts is set to True, use this parameter to specify the list of accounts to search. IMPORTANT: Only has affect if include_linked_accounts is True'
        ),
    ),
    include_linked_accounts: Optional[bool] = Field(
        False,
        description=(
            """If the AWS account is a monitoring account, set this to True to have the tool return log groups in the accounts listed in account_identifiers.
            If this parameter is set to true and account_identifiers contains a null value, the tool returns all log groups in the monitoring account and all log groups in all source accounts that are linked to the monitoring account."""
        ),
    ),
    log_group_class: Optional[Literal['STANDARD', 'INFREQUENT_ACCESS']] = Field(
        None,
        description=('If specified, filters for only log groups of the specified class.'),
    ),
    log_group_name_prefix: Optional[str] = Field(
        None,
        description=(
            'A string to filter log groups by name. Only log groups with names starting with this prefix will be returned.'
        ),
    ),
    max_items: Optional[int] = Field(
        100,
        description=('The maximum number of log groups to return.'),
    ),
) -> List[LogGroupMetadata]:
    """Lists AWS CloudWatch log groups, optionally filtering by a name prefix.

    This tool retrieves information about log groups in the account, or log groups in accounts linked to this account as a monitoring account.
    If a prefix is provided, only log groups with names starting with the specified prefix are returned.

    Usage: Use this tool to discover log groups that you'd retrieve or query logs from.

    Returns:
    --------
    List of log group metadata dictionaries
        A list of log group metadata dictionaries, each containing details such as:
            - logGroupName: The name of the log group.
            - creationTime: Timestamp when the log group was created
            - retentionInDays: Retention period, if set
            - storedBytes: The number of bytes stored.
            - kmsKeyId: KMS Key Id used for data encryption, if set
            - dataProtectionStatus: Displays whether this log group has a protection policy, or whether it had one in the past, if set
            - logGroupClass: Type of log group class
            - logGroupArn: The Amazon Resource Name (ARN) of the log group. This version of the ARN doesn't include a trailing :* after the log group name.
    """
    try:
        paginator = logs_client.get_paginator('describe_log_groups')
        kwargs = {
            'accountIdentifiers': account_identifiers,
            'includeLinkedAccounts': include_linked_accounts,
            'logGroupNamePrefix': log_group_name_prefix,
            'logGroupClass': log_group_class,
        }

        if max_items:
            kwargs['PaginationConfig'] = {'MaxItems': max_items}

        log_groups = []
        for page in paginator.paginate(**remove_null_values(kwargs)):
            log_groups.extend(page.get('logGroups', []))

        logger.info(f'Log groups: {log_groups}')
        return [LogGroupMetadata.model_validate(lg) for lg in log_groups]
    except Exception as e:
        logger.error(f'Error in mcp_describe_log_groups: {str(e)}')
        await ctx.error(f'Error in describing log groups: {str(e)}')
        raise


@mcp.tool(name='execute_log_insights_query')
async def execute_log_insights_query_tool(
    ctx: Context,
    log_group_names: Optional[List[str]] = Field(
        None,
        max_length=50,
        description='The list of up to 50 log group names to be queried. CRITICAL: Exactly one of [log_group_names, log_group_identifiers] should be non-null.',
    ),
    log_group_identifiers: Optional[List[str]] = Field(
        None,
        max_length=50,
        description="The list of up to 50 logGroupIdentifiers to query. You can specify them by the log group name or ARN. If a log group that you're querying is in a source account and you're using a monitoring account, you must use the ARN. CRITICAL: Exactly one of [log_group_names, log_group_identifiers] should be non-null.",
    ),
    start_time: str = Field(
        ...,
        description=(
            'ISO 8601 formatted start time for the CloudWatch Logs Insights query window (e.g., "2025-04-19T20:00:00").'
        ),
    ),
    end_time: str = Field(
        ...,
        description=(
            'ISO 8601 formatted end time for the CloudWatch Logs Insights query window (e.g., "2025-04-19T21:00:00").'
        ),
    ),
    query_string: str = Field(
        ...,
        description='The query string in the Cloudwatch Log Insights Query Language. See https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html.',
    ),
    limit: Optional[int] = Field(None, description='The maximum number of log events to return.'),
    max_timeout: int = Field(
        30,
        description='Maximum time in second to poll for complete results before giving up',
    ),
) -> Dict:
    """Executes a CloudWatch Logs Insights query and waits for the results to be available.

    CRITICAL: The operation must include exactly one of the following parameters: log_group_names, or log_group_identifiers.

    Usage: Use to query, filter, collect statistics, or find patterns in one or more log groups. For example, the following
    query lists exceptions per hour.

    ```
    filter @message like /Exception/
    | stats count(*) as exceptionCount by bin(1h)
    | sort exceptionCount desc
    ```

    Returns:
    --------
        A dictionary containing the final query results, including:
            - status: The current status of the query (e.g., Scheduled, Running, Complete, Failed, etc.)
            - results: A list of the actual query results if the status is Complete.
            - statistics: Query performance statistics
            - messages: Any informational messages about the query
    """
    try:
        # Start query
        kwargs = {
            'startTime': int(datetime.datetime.fromisoformat(start_time).timestamp()),
            'endTime': int(datetime.datetime.fromisoformat(end_time).timestamp()),
            'queryString': query_string,
            'logGroupIdentifiers': log_group_identifiers,
            'logGroupNames': log_group_names,
            'limit': limit,
        }

        # TODO: Not true for open search sql style queries
        if bool(log_group_names) == bool(log_group_identifiers):
            await ctx.error(
                'Exactly one of log_group_names or log_group_identifiers must be provided'
            )
            raise

        start_response = logs_client.start_query(**remove_null_values(kwargs))
        query_id = start_response['queryId']
        logger.info(f'Started query with ID: {query_id}')

        # Seconds
        poll_start = timer()
        while poll_start + max_timeout > timer():
            response = logs_client.get_query_results(queryId=query_id)
            status = response['status']

            if status in {'Complete', 'Failed', 'Cancelled'}:
                logger.info(f'Query {query_id} finished with status {status}')
                del response['ResponseMetadata']
                response['queryId'] = query_id
                return response

            await asyncio.sleep(1)

        msg = f'Query {query_id} did not complete within {max_timeout} seconds. Use get_query_results with the returned queryId to try again to retrieve query results.'
        logger.warning(msg)
        await ctx.warning(msg)
        return {
            'queryId': query_id,
            'status': 'Polling Timeout',
            'message': msg,
        }

    except Exception as e:
        logger.error(f'Error in mcp_get_log_insights: {str(e)}')
        await ctx.error(f'Error executing CloudWatch Logs Insights query: {str(e)}')
        raise


@mcp.tool(name='get_query_results')
async def get_query_results_tool(
    ctx: Context,
    query_id: str = Field(
        ...,
        description='The unique ID of the query to retrieve the results for. CRITICAL: This ID is returned by the execute_log_insights_query tool.',
    ),
) -> Dict:
    """Retrieves the results of a previously started CloudWatch Logs Insights query.

    Usage: If a log query is started by execute_log_insights_query tool and has a polling time out, this tool can be used to try to retrieve
    the query results again.

    Returns:
    --------
        A dictionary containing the final query results, including:
            - status: The current status of the query (e.g., Scheduled, Running, Complete, Failed, etc.)
            - results: A list of the actual query results if the status is Complete.
            - statistics: Query performance statistics
            - messages: Any informational messages about the query
    """
    try:
        response = logs_client.get_query_results(queryId=query_id)

        logger.info(f'Retrieved results for query ID {query_id}')
        return response
    except Exception as e:
        logger.error(f'Error in mcp_get_query_results: {str(e)}')
        await ctx.error(f'Error retrieving CloudWatch Logs Insights query results: {str(e)}')
        raise


@mcp.tool(name='cancel_query')
async def cancel_query_tool(
    ctx: Context,
    query_id: str = Field(
        ...,
        description='The unique ID of the ongoing query to cancel. CRITICAL: This ID is returned by the execute_log_insights_query tool.',
    ),
) -> CancelQueryResult:
    """Cancels an ongoing CloudWatch Logs Insights query. If the query has already ended, returns an error that the given query is not running.

    Usage: If a log query is started by execute_log_insights_query tool and has a polling time out, this tool can be used to cancel
    it prematurely to avoid incurring additional costs.

    Returns:
    --------
        A CancelQueryResult with a "success" key, which is True if the query was successfully cancelled.
    """
    try:
        response = logs_client.stop_query(queryId=query_id)
        return CancelQueryResult.model_validate(response)
    except Exception as e:
        logger.error(f'Error in mcp_get_query_results: {str(e)}')
        await ctx.error(f'Error retrieving CloudWatch Logs Insights query results: {str(e)}')
        raise


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()

    logger.info('CloudWatch Logs MCP server started')


if __name__ == '__main__':
    main()
