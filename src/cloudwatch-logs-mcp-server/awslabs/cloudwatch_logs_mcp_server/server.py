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

"""awslabs cloudwatch-logs MCP Server implementation."""

import asyncio
import boto3
import datetime
import os
from awslabs.cloudwatch_logs_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudwatch_logs_mcp_server.common import (
    clean_up_pattern,
    filter_by_prefixes,
    remove_null_values,
)
from awslabs.cloudwatch_logs_mcp_server.models import (
    AnomalyDetector,
    CancelQueryResult,
    LogAnalysisResult,
    LogAnomaly,
    LogAnomalyResults,
    LogGroupMetadata,
    LogMetadata,
    SavedQuery,
)
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from timeit import default_timer as timer
from typing import Dict, List, Literal, Optional


mcp = FastMCP(
    'awslabs.cloudwatch-logs-mcp-server',
    instructions='Use this MCP server to run read-only commands and analyze CloudWatchLogs. Supports discovering logs groups as well as running CloudWatch Log Insight Queries. With CloudWatch Logs Insights, you can interactively search and analyze your log data in Amazon CloudWatch Logs and perform queries to help you more efficiently and effectively respond to operational issues.',
    dependencies=[
        'pydantic',
        'loguru',
    ],
)

# Initialize client
aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')
config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-logs-mcp-server/{MCP_SERVER_VERSION}')

try:
    if aws_profile := os.environ.get('AWS_PROFILE'):
        logs_client = boto3.Session(profile_name=aws_profile, region_name=aws_region).client(
            'logs', config=config
        )
    else:
        logs_client = boto3.Session(region_name=aws_region).client('logs', config=config)
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
            'An exact prefix to filter log groups by name. IMPORTANT: Only log groups with names starting with this prefix will be returned.'
        ),
    ),
    max_items: Optional[int] = Field(
        None,
        description=('The maximum number of log groups to return.'),
    ),
) -> LogMetadata:
    """IMPORTANT: This tool is deprecated. Please use the describe_log_groups tool in the cloudwatch MCP server instead.

    Lists AWS CloudWatch log groups and saved queries associated with them, optionally filtering by a name prefix.

    This tool retrieves information about log groups in the account, or log groups in accounts linked to this account as a monitoring account.
    If a prefix is provided, only log groups with names starting with the specified prefix are returned.

    Additionally returns any user saved queries that are associated with any of the returned log groups.

    Usage: Use this tool to discover log groups that you'd retrieve or query logs from and queries that have been saved by the user.

    Returns:
    --------
    List of log group metadata dictionaries and saved queries associated with them
       Each log group metadata contains details such as:
            - logGroupName: The name of the log group.
            - creationTime: Timestamp when the log group was created
            - retentionInDays: Retention period, if set
            - storedBytes: The number of bytes stored.
            - kmsKeyId: KMS Key Id used for data encryption, if set
            - dataProtectionStatus: Displays whether this log group has a protection policy, or whether it had one in the past, if set
            - logGroupClass: Type of log group class
            - logGroupArn: The Amazon Resource Name (ARN) of the log group. This version of the ARN doesn't include a trailing :* after the log group name.
        Any saved queries that are applicable to the returned log groups are also included.
    """

    def describe_log_groups() -> List[LogGroupMetadata]:
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

    def get_filtered_saved_queries(log_groups: List[LogGroupMetadata]) -> List[SavedQuery]:
        saved_queries = []
        next_token = None

        # No paginator for this API
        while True:
            # TODO: Support other query language types
            kwargs = {'nextToken': next_token, 'queryLanguage': 'CWLI'}
            response = logs_client.describe_query_definitions(**remove_null_values(kwargs))
            saved_queries.extend(response.get('queryDefinitions', []))

            next_token = response.get('nextToken')
            if not next_token:
                break

        logger.info(f'Saved queries: {saved_queries}')
        modeled_queries = [SavedQuery.model_validate(saved_query) for saved_query in saved_queries]

        log_group_targets = {lg.logGroupName for lg in log_groups}
        # filter to only saved queries applicable to log groups we're looking at
        return [
            query
            for query in modeled_queries
            if (query.logGroupNames & log_group_targets)
            or filter_by_prefixes(log_group_targets, query.logGroupPrefixes)
        ]

    try:
        log_groups = describe_log_groups()
        filtered_saved_queries = get_filtered_saved_queries(log_groups)
        return LogMetadata(log_group_metadata=log_groups, saved_queries=filtered_saved_queries)

    except Exception as e:
        logger.error(f'Error in describe_log_groups_tool: {str(e)}')
        await ctx.error(f'Error in describing log groups: {str(e)}')
        raise


@mcp.tool(name='analyze_log_group')
async def analyze_log_group_tool(
    ctx: Context,
    log_group_arn: str = Field(
        ...,
        description='The log group arn to look for anomalies in, as returned by the describe_log_groups tools',
    ),
    start_time: str = Field(
        ...,
        description=(
            'ISO 8601 formatted start time for the CloudWatch Logs Insights query window (e.g., "2025-04-19T20:00:00+00:00").'
        ),
    ),
    end_time: str = Field(
        ...,
        description=(
            'ISO 8601 formatted end time for the CloudWatch Logs Insights query window (e.g., "2025-04-19T21:00:00+00:00").'
        ),
    ),
) -> LogAnalysisResult:
    """IMPORTANT: This tool is deprecated. Please use the analyze_log_group tool in the cloudwatch MCP server instead.

    Analyzes a CloudWatch log group for anomalies, message patterns, and error patterns within a specified time window.

    This tool performs an analysis of the specified log group by:
    1. Discovering and checking log anomaly detectors associated with the log group
    2. Retrieving anomalies from those detectors that fall within the specified time range
    3. Identifying the top 5 most common message patterns
    4. Finding the top 5 patterns containing error-related terms

    Usage: Use this tool to detect anomalies and understand common patterns in your log data, particularly
    focusing on error patterns that might indicate issues. This can help identify potential problems and
    understand the typical behavior of your application.

    Returns:
    --------
    A LogAnalysisResult object containing:
        - log_anomaly_results: Information about anomaly detectors and their findings
            * anomaly_detectors: List of anomaly detectors for the log group
            * anomalies: List of anomalies that fall within the specified time range
        - top_patterns: Results of the query for most common message patterns
        - top_patterns_containing_errors: Results of the query for patterns containing error-related terms
            (error, exception, fail, timeout, fatal)
    """

    def is_applicable_anomaly(anomaly: LogAnomaly) -> bool:
        # Must have overlap
        if anomaly.firstSeen > end_time or anomaly.lastSeen < start_time:
            return False
        # Must be for this log group
        return log_group_arn in anomaly.logGroupArnList

    async def get_applicable_anomalies() -> LogAnomalyResults:
        detectors: List[AnomalyDetector] = []
        paginator = logs_client.get_paginator('list_log_anomaly_detectors')
        for page in paginator.paginate(filterLogGroupArn=log_group_arn):
            detectors.extend(
                [AnomalyDetector.model_validate(d) for d in page.get('anomalyDetectors', [])]
            )

        logger.info(f'Found {len(detectors)} anomaly detectors for log group')

        # 2 & 3. Get and filter anomalies for each detector
        anomalies: List[LogAnomaly] = []
        for detector in detectors:
            paginator = logs_client.get_paginator('list_anomalies')

            for page in paginator.paginate(
                anomalyDetectorArn=detector.anomalyDetectorArn, suppressionState='UNSUPPRESSED'
            ):
                anomalies.extend(
                    LogAnomaly.model_validate(anomaly) for anomaly in page.get('anomalies', [])
                )

        applicable_anomalies = [anomaly for anomaly in anomalies if is_applicable_anomaly(anomaly)]
        logger.info(
            f'Found {len(anomalies)} anomaly detectors for log group, {len(applicable_anomalies)} of which are applicable'
        )

        return LogAnomalyResults(anomaly_detectors=detectors, anomalies=applicable_anomalies)

    try:
        # Convert input times to timestamps for comparison
        # 1. Get anomaly detectors for this log group

        log_anomaly_results, pattern_query_result, error_pattern_result = await asyncio.gather(
            get_applicable_anomalies(),
            execute_log_insights_query_tool(
                ctx,
                log_group_names=None,
                log_group_identifiers=[log_group_arn],
                start_time=start_time,
                end_time=end_time,
                query_string='pattern @message | sort @sampleCount desc | limit 5',
                limit=5,
                max_timeout=30,
            ),
            execute_log_insights_query_tool(
                ctx,
                log_group_names=None,
                log_group_identifiers=[log_group_arn],
                start_time=start_time,
                end_time=end_time,
                query_string='fields @timestamp, @message | filter @message like /(?i)(error|exception|fail|timeout|fatal)/ | pattern @message | limit 5',
                limit=5,
                max_timeout=30,
            ),
        )

        clean_up_pattern(pattern_query_result.get('results', []))
        clean_up_pattern(error_pattern_result.get('results', []))

        return LogAnalysisResult(
            log_anomaly_results=log_anomaly_results,
            top_patterns=pattern_query_result,
            top_patterns_containing_errors=error_pattern_result,
        )

    except Exception as e:
        logger.error(f'Error in analyze_log_group_tool: {str(e)}')
        await ctx.error(f'Error analyzing log group: {str(e)}')
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
            'ISO 8601 formatted start time for the CloudWatch Logs Insights query window (e.g., "2025-04-19T20:00:00+00:00").'
        ),
    ),
    end_time: str = Field(
        ...,
        description=(
            'ISO 8601 formatted end time for the CloudWatch Logs Insights query window (e.g., "2025-04-19T21:00:00+00:00").'
        ),
    ),
    query_string: str = Field(
        ...,
        description='The query string in the Cloudwatch Log Insights Query Language. See https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html.',
    ),
    limit: Optional[int] = Field(
        None,
        description='The maximum number of log events to return. It is critical to use either this parameter or a `| limit <int>` operator in the query to avoid consuming too many tokens of the agent.',
    ),
    max_timeout: int = Field(
        30,
        description='Maximum time in second to poll for complete results before giving up',
    ),
) -> Dict:
    """IMPORTANT: This tool is deprecated. Please use the execute_log_insights_query tool in the cloudwatch MCP server instead.

    Executes a CloudWatch Logs Insights query and waits for the results to be available.

    IMPORTANT: The operation must include exactly one of the following parameters: log_group_names, or log_group_identifiers.

    CRITICAL: The volume of returned logs can easily overwhelm the agent context window. Always include a limit in the query
    (| limit 50) or using the limit parameter.

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
                return {
                    'queryId': query_id,
                    'status': status,
                    'statistics': response.get('statistics', {}),
                    'results': [
                        {field['field']: field['value'] for field in line}
                        for line in response.get('results', [])
                    ],
                }

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
        logger.error(f'Error in execute_log_insights_query_tool: {str(e)}')
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
    """IMPORTANT: This tool is deprecated. Please use the get_logs_insight_query_results tool in the cloudwatch MCP server instead.

    Retrieves the results of a previously started CloudWatch Logs Insights query.

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

        return {
            'queryId': query_id,
            'status': response['status'],
            'statistics': response.get('statistics', {}),
            'results': [
                {field['field']: field['value'] for field in line}
                for line in response.get('results', [])
            ],
        }
    except Exception as e:
        logger.error(f'Error in get_query_results_tool: {str(e)}')
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
    """IMPORTANT: This tool is deprecated. Please use the cancel_logs_insight_query tool in the cloudwatch MCP server instead.

    Cancels an ongoing CloudWatch Logs Insights query. If the query has already ended, returns an error that the given query is not running.

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
        logger.error(f'Error in get_query_results_tool: {str(e)}')
        await ctx.error(f'Error retrieving CloudWatch Logs Insights query results: {str(e)}')
        raise


def main():
    """Run the MCP server."""
    mcp.run()

    logger.info('CloudWatch Logs MCP server started')


if __name__ == '__main__':
    main()
