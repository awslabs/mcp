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

"""CloudWatch Logs tools for MCP server."""

import asyncio
import boto3
import datetime
import os
from pathlib import Path
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudwatch_mcp_server.common import (
    clean_up_pattern,
    filter_by_prefixes,
    remove_null_values,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.models import (
    LogAnomalyDetector,
    LogsQueryCancelResult,
    LogsAnalysisResult,
    LogAnomaly,
    LogAnomalyResults,
    LogGroupMetadata,
    LogsMetadata,
    SavedLogsInsightsQuery,
)
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from timeit import default_timer as timer
from typing import Dict, List, Literal, Optional, Union


class CloudWatchLogsTools:
    """CloudWatch Logs tools for MCP server."""
    
    def __init__(self):
        """Initialize the CloudWatch Logs client."""
        # Initialize client
        aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')
        config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')

        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                self.logs_client = boto3.Session(profile_name=aws_profile, region_name=aws_region).client(
                    'logs', config=config
                )
            else:
                self.logs_client = boto3.Session(region_name=aws_region).client('logs', config=config)
        except Exception as e:
            logger.error(f'Error creating cloudwatch logs client: {str(e)}')
            raise

    def _validate_log_group_parameters(self, log_group_names: Optional[List[str]], log_group_identifiers: Optional[List[str]]) -> None:
        """Validate that exactly one of log_group_names or log_group_identifiers is provided.
        
        Args:
            log_group_names: List of log group names
            log_group_identifiers: List of log group identifiers
            
        Raises:
            ValueError: If both or neither parameters are provided
        """
        if bool(log_group_names) == bool(log_group_identifiers):
            raise ValueError('Exactly one of log_group_names or log_group_identifiers must be provided')

    def _convert_time_to_timestamp(self, time_str: str) -> int:
        """Convert ISO 8601 time string to Unix timestamp.
        
        Args:
            time_str: ISO 8601 formatted time string
            
        Returns:
            Unix timestamp as integer
        """
        return int(datetime.datetime.fromisoformat(time_str).timestamp())

    def _build_logs_query_params(self, 
                                 log_group_names: Optional[List[str]],
                                 log_group_identifiers: Optional[List[str]], 
                                 start_time: str,
                                 end_time: str,
                                 query_string: str,
                                 limit: Optional[int]) -> Dict:
        """Build parameters for CloudWatch Logs Insights query.
        
        Args:
            log_group_names: List of log group names
            log_group_identifiers: List of log group identifiers
            start_time: Start time in ISO 8601 format
            end_time: End time in ISO 8601 format
            query_string: CloudWatch Logs Insights query string
            limit: Maximum number of results to return
            
        Returns:
            Dictionary of parameters for the start_query API call
        """
        return {
            'startTime': self._convert_time_to_timestamp(start_time),
            'endTime': self._convert_time_to_timestamp(end_time),
            'queryString': query_string,
            'logGroupIdentifiers': log_group_identifiers,
            'logGroupNames': log_group_names,
            'limit': limit,
        }

    def _process_query_results(self, response: Dict, query_id: str = '') -> Dict:
        """Process query results response into standardized format.
        
        Args:
            response: Raw response from get_query_results API
            query_id: The query ID to include in the response
            
        Returns:
            Processed query results dictionary
        """
        return {
            'queryId': query_id or response.get('queryId', ''),
            'status': response['status'], 
            'statistics': response.get('statistics', {}),
            'results': [
                {field['field']: field['value'] for field in line}
                for line in response.get('results', [])
            ],
        }

    async def _poll_for_query_completion(self, query_id: str, max_timeout: int, ctx: Context) -> Dict:
        """Poll for query completion within the specified timeout.
        
        Args:
            query_id: The query ID to poll for
            max_timeout: Maximum time to wait in seconds
            ctx: MCP context for warnings
            
        Returns:
            Query results dictionary or timeout message
        """
        poll_start = timer()
        while poll_start + max_timeout > timer():
            response = self.logs_client.get_query_results(queryId=query_id)
            status = response['status']

            if status in {'Complete', 'Failed', 'Cancelled'}:
                logger.info(f'Query {query_id} finished with status {status}')
                return self._process_query_results(response, query_id)

            await asyncio.sleep(1)

        msg = f'Query {query_id} did not complete within {max_timeout} seconds. Use get_logs_insight_query_results with the returned queryId to try again to retrieve query results.'
        logger.warning(msg)
        await ctx.warning(msg)
        return {
            'queryId': query_id,
            'status': 'Polling Timeout',
            'message': msg,
        }

    def register(self, mcp):
        """Register all CloudWatch Logs tools with the MCP server."""
        
        # Register describe_log_groups tool
        mcp.tool(
            name='describe_log_groups'
        )(self.describe_log_groups)

        # Register analyze_log_group tool  
        mcp.tool(
            name='analyze_log_group'
        )(self.analyze_log_group)

        # Register execute_log_insights_query tool
        mcp.tool(
            name='execute_log_insights_query'
        )(self.execute_log_insights_query)

        # Register get_logs_insight_query_results tool
        mcp.tool(
            name='get_logs_insight_query_results'
        )(self.get_logs_insight_query_results)

        # Register cancel_logs_insight_query tool
        mcp.tool(
            name='cancel_logs_insight_query'
        )(self.cancel_logs_insight_query)

    async def describe_log_groups(
        self,
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
    ) -> LogsMetadata:
        """Lists AWS CloudWatch log groups and saved queries associated with them, optionally filtering by a name prefix.

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
            paginator = self.logs_client.get_paginator('describe_log_groups')
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

        def get_filtered_saved_queries(log_groups: List[LogGroupMetadata]) -> List[SavedLogsInsightsQuery]:
            saved_queries = []
            next_token = None

            # No paginator for this API
            while True:
                # TODO: Support other query language types
                kwargs = {'nextToken': next_token, 'queryLanguage': 'CWLI'}
                response = self.logs_client.describe_query_definitions(**remove_null_values(kwargs))
                saved_queries.extend(response.get('queryDefinitions', []))

                next_token = response.get('nextToken')
                if not next_token:
                    break

            logger.info(f'Saved queries: {saved_queries}')
            modeled_queries = [SavedLogsInsightsQuery.model_validate(saved_query) for saved_query in saved_queries]

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
            return LogsMetadata(log_group_metadata=log_groups, saved_queries=filtered_saved_queries)

        except Exception as e:
            logger.error(f'Error in describe_log_groups_tool: {str(e)}')
            await ctx.error(f'Error in describing log groups: {str(e)}')
            raise

    async def analyze_log_group(
        self,
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
    ) -> LogsAnalysisResult:
        """Analyzes a CloudWatch log group for anomalies, message patterns, and error patterns within a specified time window.

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
        A LogsAnalysisResult object containing:
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
            detectors: List[LogAnomalyDetector] = []
            paginator = self.logs_client.get_paginator('list_log_anomaly_detectors')
            for page in paginator.paginate(filterLogGroupArn=log_group_arn):
                detectors.extend(
                    [LogAnomalyDetector.model_validate(d) for d in page.get('anomalyDetectors', [])]
                )

            logger.info(f'Found {len(detectors)} anomaly detectors for log group')

            # 2 & 3. Get and filter anomalies for each detector
            anomalies: List[LogAnomaly] = []
            for detector in detectors:
                paginator = self.logs_client.get_paginator('list_anomalies')

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
                self.execute_log_insights_query(
                    ctx,
                    log_group_names=None,
                    log_group_identifiers=[log_group_arn],
                    start_time=start_time,
                    end_time=end_time,
                    query_string='pattern @message | sort @sampleCount desc | limit 5',
                    limit=5,
                    max_timeout=30,
                ),
                self.execute_log_insights_query(
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

            return LogsAnalysisResult(
                log_anomaly_results=log_anomaly_results,
                top_patterns=pattern_query_result,
                top_patterns_containing_errors=error_pattern_result,
            )

        except Exception as e:
            logger.error(f'Error in analyze_log_group_tool: {str(e)}')
            await ctx.error(f'Error analyzing log group: {str(e)}')
            raise

    async def execute_log_insights_query(
        self,
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
        """Executes a CloudWatch Logs Insights query and waits for the results to be available.

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
            # Validate parameters
            self._validate_log_group_parameters(log_group_names, log_group_identifiers)
            
            # Build query parameters
            kwargs = self._build_logs_query_params(
                log_group_names, log_group_identifiers, start_time, end_time, query_string, limit
            )

            # Start the query
            start_response = self.logs_client.start_query(**remove_null_values(kwargs))
            query_id = start_response['queryId']
            logger.info(f'Started query with ID: {query_id}')

            # Poll for completion
            return await self._poll_for_query_completion(query_id, max_timeout, ctx)

        except Exception as e:
            logger.error(f'Error in execute_log_insights_query_tool: {str(e)}')
            await ctx.error(f'Error executing CloudWatch Logs Insights query: {str(e)}')
            raise

    async def get_logs_insight_query_results(
        self, 
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
            response = self.logs_client.get_query_results(queryId=query_id)

            logger.info(f'Retrieved results for query ID {query_id}')

            return self._process_query_results(response, query_id)
        except Exception as e:
            logger.error(f'Error in get_query_results_tool: {str(e)}')
            await ctx.error(f'Error retrieving CloudWatch Logs Insights query results: {str(e)}')
            raise

    async def cancel_logs_insight_query(
        self, 
        ctx: Context, 
        query_id: str = Field(
            ...,
            description='The unique ID of the ongoing query to cancel. CRITICAL: This ID is returned by the execute_log_insights_query tool.',
        ),
    ) -> LogsQueryCancelResult:
        """Cancels an ongoing CloudWatch Logs Insights query. If the query has already ended, returns an error that the given query is not running.

        Usage: If a log query is started by execute_log_insights_query tool and has a polling time out, this tool can be used to cancel
        it prematurely to avoid incurring additional costs.

        Returns:
        --------
            A LogsQueryCancelResult with a "success" key, which is True if the query was successfully cancelled.
        """
        try:
            response = self.logs_client.stop_query(queryId=query_id)
            return LogsQueryCancelResult.model_validate(response)
        except Exception as e:
            logger.error(f'Error in cancel_query_tool: {str(e)}')
            await ctx.error(f'Error cancelling CloudWatch Logs Insights query: {str(e)}')
            raise
