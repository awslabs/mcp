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

"""CloudWatch handler for the EKS MCP Server."""

import datetime
import json
import time
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.logging_helper import LogLevel, log_with_request_id
from awslabs.eks_mcp_server.models import CloudWatchLogsResponse, CloudWatchMetricsResponse
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Optional, Union


class CloudWatchHandler:
    """Handler for CloudWatch operations in the EKS MCP Server.

    This class provides tools for retrieving and analyzing CloudWatch logs and metrics
    from EKS clusters, enabling effective monitoring and troubleshooting.
    """

    def __init__(self, mcp, allow_sensitive_data_access=False):
        """Initialize the CloudWatch handler.

        Args:
            mcp: The MCP server instance
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_sensitive_data_access = allow_sensitive_data_access

        # Register tools
        self.mcp.tool(name='get_cloudwatch_logs')(self.get_cloudwatch_logs)
        self.mcp.tool(name='get_cloudwatch_metrics')(self.get_cloudwatch_metrics)

    def resolve_time_range(
        self,
        start_time: Optional[Union[str, datetime.datetime]] = None,
        end_time: Optional[Union[str, datetime.datetime]] = None,
        minutes: int = 15,
    ) -> tuple:
        """Resolve start and end times for CloudWatch queries.

        This function is public for unit testing purposes.

        Args:
            start_time: Start time as string (ISO format) or datetime object
            end_time: End time as string (ISO format) or datetime object
            minutes: Number of minutes to look back if start_time is not provided

        Returns:
            Tuple of (start_datetime, end_datetime)
        """
        # Handle end_time
        if end_time is None:
            end_dt = datetime.datetime.now()
        elif isinstance(end_time, str):
            end_dt = datetime.datetime.fromisoformat(end_time)
        else:
            end_dt = end_time

        # Handle start_time
        if start_time is None:
            start_dt = end_dt - datetime.timedelta(minutes=minutes)
        elif isinstance(start_time, str):
            start_dt = datetime.datetime.fromisoformat(start_time)
        else:
            start_dt = start_time

        return start_dt, end_dt

    async def get_cloudwatch_logs(
        self,
        ctx: Context,
        resource_type: str = Field(
            ...,
            description='Resource type to search logs for. Valid values: "pod", "node", "container". This determines how logs are filtered.',
        ),
        resource_name: str = Field(
            ...,
            description='Resource name to search for in log messages (e.g., pod name, node name, container name). Used to filter logs for the specific resource.',
        ),
        cluster_name: str = Field(
            ...,
            description='Name of the EKS cluster where the resource is located. Used to construct the CloudWatch log group name.',
        ),
        log_type: str = Field(
            ...,
            description="""Log type to query. Options:
            - "application": Container/application logs
            - "host": Node-level system logs
            - "performance": Performance metrics logs
            - "control-plane": EKS control plane logs
            - Or provide a custom CloudWatch log group name directly""",
        ),
        minutes: int = Field(
            15,
            description='Number of minutes to look back for logs. Default: 15. Ignored if start_time is provided. Use smaller values for recent issues, larger values for historical analysis.',
        ),
        start_time: Optional[str] = Field(
            None,
            description='Start time in ISO format (e.g., "2023-01-01T00:00:00Z"). If provided, overrides the minutes parameter. IMPORTANT: Use this for precise time ranges.',
        ),
        end_time: Optional[str] = Field(
            None,
            description='End time in ISO format (e.g., "2023-01-01T01:00:00Z"). If not provided, defaults to current time. IMPORTANT: Use with start_time for precise time ranges.',
        ),
        limit: int = Field(
            50,
            description='Maximum number of log entries to return. Use lower values (10-50) for faster queries, higher values (100-1000) for more comprehensive results. IMPORTANT: Higher values may impact performance.',
        ),
        filter_pattern: Optional[str] = Field(
            None,
            description='Additional CloudWatch Logs filter pattern to apply. Uses CloudWatch Logs Insights syntax (e.g., "ERROR", "field=value"). IMPORTANT: Use this to narrow down results for specific issues.',
        ),
        fields: Optional[str] = Field(
            None,
            description='Custom fields to include in the query results (defaults to "@timestamp, @message"). Use CloudWatch Logs Insights field syntax. IMPORTANT: Only specify if you need fields beyond the default timestamp and message.',
        ),
    ) -> CloudWatchLogsResponse:
        """Get logs from CloudWatch for a specific resource.

        This tool retrieves logs from CloudWatch for Kubernetes resources in an EKS cluster,
        allowing you to analyze application behavior, troubleshoot issues, and monitor system
        health. It supports filtering by resource type, time range, and content for troubleshooting
        application errors, investigating security incidents, and analyzing startup configuration issues.

        ## Requirements
        - The server must be run with the `--allow-sensitive-data-access` flag
        - The EKS cluster must have CloudWatch logging enabled
        - The resource must exist in the specified cluster

        ## Response Information
        The response includes resource details (type, name, cluster), log group information,
        time range queried, and formatted log entries with timestamps and messages.

        ## Usage Tips
        - Start with a small time range (15-30 minutes) and expand if needed
        - Use filter_pattern to narrow down results (e.g., "ERROR", "exception")
        - For JSON logs, the tool automatically parses nested structures
        - Combine with get_k8s_events for comprehensive troubleshooting

        Args:
            ctx: MCP context
            resource_type: Resource type (pod, node, container)
            resource_name: Resource name to search for in log messages
            cluster_name: Name of the EKS cluster
            log_type: Log type (application, host, performance, control-plane, or custom)
            minutes: Number of minutes to look back
            start_time: Start time in ISO format (overrides minutes)
            end_time: End time in ISO format (defaults to now)
            limit: Maximum number of log entries to return
            filter_pattern: Additional CloudWatch Logs filter pattern
            fields: Custom fields to include in the query results

        Returns:
            CloudWatchLogsResponse with log entries and resource information
        """
        try:
            # Check if sensitive data access is allowed
            if not self.allow_sensitive_data_access:
                error_message = (
                    'Access to CloudWatch logs requires --allow-sensitive-data-access flag'
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return CloudWatchLogsResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    resource_type=resource_type,
                    resource_name=resource_name,
                    cluster_name=cluster_name,
                    log_type=log_type,
                    log_group='',
                    start_time='',
                    end_time='',
                    log_entries=[],
                )

            start_dt, end_dt = self.resolve_time_range(start_time, end_time, minutes)

            # Create CloudWatch Logs client
            logs = AwsHelper.create_boto3_client('logs')

            # Determine the log group based on log_type
            known_types = {'application', 'host', 'performance', 'dataplane'}
            if log_type in known_types:
                log_group = f'/aws/containerinsights/{cluster_name}/{log_type}'
            elif log_type == 'control-plane':
                log_group = f'/aws/eks/{cluster_name}/cluster'
            else:
                log_group = log_type  # Assume user passed full log group name

            # Determine fields to include
            query_fields = fields if fields else '@timestamp, @message'

            # Construct the base query
            query = f"""
            fields {query_fields}
            | filter @message like '{resource_name}'
            """

            # Add additional filter pattern if provided
            if filter_pattern:
                query += f'\n| {filter_pattern}'

            # Add sorting and limit
            query += f'\n| sort @timestamp desc\n| limit {limit}'

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Starting CloudWatch Logs query for {resource_type} {resource_name} in cluster {cluster_name}',
                log_group=log_group,
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
            )

            # Start the query
            start_query_response = logs.start_query(
                logGroupName=log_group,
                startTime=int(start_dt.timestamp()),
                endTime=int(end_dt.timestamp()),
                queryString=query,
            )

            query_id = start_query_response['queryId']

            # Poll for results
            query_response = self._poll_query_results(
                ctx, logs, query_id, resource_type, resource_name
            )

            # Process results
            results = query_response['results']
            log_entries = []

            for result in results:
                entry = self._build_log_entry(result)
                log_entries.append(entry)

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Retrieved {len(log_entries)} log entries for {resource_type} {resource_name}',
            )

            # Return the results
            return CloudWatchLogsResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved {len(log_entries)} log entries for {resource_type} {resource_name} in cluster {cluster_name}',
                    )
                ],
                resource_type=resource_type,
                resource_name=resource_name,
                cluster_name=cluster_name,
                log_type=log_type,
                log_group=log_group,
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
                log_entries=log_entries,
            )

        except Exception as e:
            error_message = f'Failed to get logs for {resource_type} {resource_name}: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CloudWatchLogsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                resource_type=resource_type,
                resource_name=resource_name,
                cluster_name=cluster_name,
                log_type=log_type,
                log_group='',
                start_time='',
                end_time='',
                log_entries=[],
            )

    async def get_cloudwatch_metrics(
        self,
        ctx: Context,
        resource_type: str = Field(
            ...,
            description='Resource type to retrieve metrics for. Valid values: "pod", "node", "container", "cluster", "service". Determines the CloudWatch dimensions.',
        ),
        resource_name: str = Field(
            ...,
            description='Name of the resource to retrieve metrics for (e.g., pod name, node name). Used as a dimension value in CloudWatch.',
        ),
        cluster_name: str = Field(
            ...,
            description='Name of the EKS cluster where the resource is located. Used as the ClusterName dimension in CloudWatch.',
        ),
        metric_name: str = Field(
            ...,
            description="""Metric name to retrieve. Common examples:
            - cpu_usage_total: Total CPU usage
            - memory_rss: Resident Set Size memory usage
            - network_rx_bytes: Network bytes received
            - network_tx_bytes: Network bytes transmitted""",
        ),
        namespace: str = Field(
            ...,
            description="""CloudWatch namespace where the metric is stored. Common values:
            - "ContainerInsights": For container metrics
            - "AWS/EC2": For EC2 instance metrics
            - "AWS/EKS": For EKS control plane metrics""",
        ),
        k8s_namespace: str = Field(
            'default',
            description='Kubernetes namespace for the resource. Used as the Namespace dimension in CloudWatch. Default: "default"',
        ),
        minutes: int = Field(
            15,
            description='Number of minutes to look back for metrics. Default: 15. Ignored if start_time is provided. IMPORTANT: Choose a time range appropriate for the metric resolution.',
        ),
        start_time: Optional[str] = Field(
            None,
            description='Start time in ISO format (e.g., "2023-01-01T00:00:00Z"). If provided, overrides the minutes parameter. IMPORTANT: Use this for precise historical analysis.',
        ),
        end_time: Optional[str] = Field(
            None,
            description='End time in ISO format (e.g., "2023-01-01T01:00:00Z"). If not provided, defaults to current time. IMPORTANT: Use with start_time for precise time ranges.',
        ),
        limit: int = Field(
            50,
            description='Maximum number of data points to return. Higher values (100-1000) provide more granular data but may impact performance. IMPORTANT: Balance between granularity and performance.',
        ),
        period: int = Field(
            60,
            description='Period in seconds for the metric data points. Default: 60 (1 minute). Lower values (1-60) provide higher resolution but may be less available. IMPORTANT: Match to your monitoring needs.',
        ),
        stat: str = Field(
            'Average',
            description="""Statistic to use for the metric aggregation:
            - Average: Mean value during the period
            - Sum: Total value during the period
            - Maximum: Highest value during the period
            - Minimum: Lowest value during the period
            - SampleCount: Number of samples during the period""",
        ),
        custom_dimensions: Optional[dict] = Field(
            None,
            description='Custom dimensions to use instead of the default ones. Provide as a dictionary of dimension name-value pairs. IMPORTANT: Only use this if you need to override the standard dimensions.',
        ),
    ) -> CloudWatchMetricsResponse:
        """Get metrics from CloudWatch for a specific resource.

        This tool retrieves metrics from CloudWatch for Kubernetes resources in an EKS cluster,
        allowing you to monitor performance, resource utilization, and system health. It supports
        various resource types and metrics with flexible time ranges and aggregation options for
        monitoring CPU/memory usage, analyzing network traffic, and identifying performance bottlenecks.

        ## Requirements
        - The EKS cluster must have CloudWatch Container Insights enabled
        - The resource must exist in the specified cluster
        - The metric must be available in the specified namespace

        ## Response Information
        The response includes resource details (type, name, cluster), metric information (name, namespace),
        time range queried, and data points with timestamps and values.

        ## Usage Tips
        - Use appropriate statistics for different metrics (e.g., Average for CPU, Maximum for memory spikes)
        - Match the period to your analysis needs (smaller for detailed graphs, larger for trends)
        - For rate metrics like network traffic, Sum is often more useful than Average
        - Combine with get_cloudwatch_logs to correlate metrics with log events

        Args:
            ctx: MCP context
            resource_type: Resource type (pod, node, container, cluster)
            resource_name: Resource name
            cluster_name: Name of the EKS cluster
            metric_name: Metric name (e.g., cpu_usage_total, memory_rss)
            namespace: CloudWatch namespace
            k8s_namespace: Kubernetes namespace for the resource
            minutes: Number of minutes to look back
            start_time: Start time in ISO format (overrides minutes)
            end_time: End time in ISO format (defaults to now)
            limit: Maximum number of data points to return
            period: Period in seconds for the metric data points
            stat: Statistic to use for the metric
            custom_dimensions: Custom dimensions to use instead of defaults

        Returns:
            CloudWatchMetricsResponse with metric data points and resource information
        """
        try:
            start_dt, end_dt = self.resolve_time_range(start_time, end_time, minutes)

            # Create CloudWatch client
            cloudwatch = AwsHelper.create_boto3_client('cloudwatch')

            # Use custom dimensions if provided, otherwise determine based on resource_type
            dimensions = {}

            if isinstance(custom_dimensions, dict):
                # Use the provided custom dimensions directly
                dimensions = custom_dimensions
            elif custom_dimensions is not None and not hasattr(custom_dimensions, 'default'):
                # Try to convert to dict if possible
                try:
                    dimensions = dict(custom_dimensions)
                except (TypeError, ValueError):
                    # If conversion fails, use default dimensions
                    dimensions = {'ClusterName': cluster_name}
            else:
                # Set default dimensions based on resource type
                dimensions['ClusterName'] = cluster_name
                dimensions['Namespace'] = k8s_namespace

                if resource_type == 'pod':
                    dimensions['PodName'] = resource_name
                elif resource_type == 'node':
                    dimensions['NodeName'] = resource_name
                elif resource_type == 'container':
                    dimensions['ContainerName'] = resource_name
                elif resource_type == 'service':
                    dimensions['Service'] = resource_name

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Getting CloudWatch metrics for {resource_type} {resource_name} in cluster {cluster_name}',
                metric_name=metric_name,
                namespace=namespace,
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
            )

            # Create the metric data query
            metric_data_query = {
                'Id': 'm1',
                'ReturnData': True,
            }

            # Convert dimensions to the format expected by CloudWatch
            dimension_list = [{'Name': k, 'Value': v} for k, v in dimensions.items()]

            # Create the metric definition
            metric_def = {
                'Namespace': namespace,
                'MetricName': metric_name,
                'Dimensions': dimension_list,
            }

            # Create the metric stat with the appropriate statistics
            # Handle the case where period/stat is a Field object
            period_value = period if isinstance(period, int) else period.default
            stat_value = stat if isinstance(stat, str) else stat.default

            # Create the metric stat
            metric_stat = {'Metric': metric_def, 'Period': period_value, 'Stat': stat_value}

            # Add the metric stat to the query
            metric_data_query['MetricStat'] = metric_stat

            # Get metric data
            response = cloudwatch.get_metric_data(
                MetricDataQueries=[metric_data_query],
                StartTime=start_dt,
                EndTime=end_dt,
                MaxDatapoints=limit,
            )

            # Process results
            metric_data = response['MetricDataResults'][0]
            timestamps = [ts.isoformat() for ts in metric_data.get('Timestamps', [])]
            values = metric_data.get('Values', [])

            # Create data points
            data_points = []
            for i in range(len(timestamps)):
                if i < len(values):
                    data_points.append({'timestamp': timestamps[i], 'value': values[i]})

            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Retrieved {len(data_points)} metric data points for {resource_type} {resource_name}',
            )

            # Return the results
            return CloudWatchMetricsResponse(
                isError=False,
                content=[
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved {len(data_points)} metric data points for {resource_type} {resource_name} in cluster {cluster_name}',
                    )
                ],
                resource_type=resource_type,
                resource_name=resource_name,
                cluster_name=cluster_name,
                metric_name=metric_name,
                namespace=namespace,
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
                data_points=data_points,
            )

        except Exception as e:
            error_message = f'Failed to get metrics for {resource_type} {resource_name}: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)

            return CloudWatchMetricsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                resource_type=resource_type,
                resource_name=resource_name,
                cluster_name=cluster_name,
                metric_name=metric_name,
                namespace=namespace,
                start_time='',
                end_time='',
                data_points=[],
            )

    def _poll_query_results(
        self,
        ctx,
        logs_client,
        query_id,
        resource_type,
        resource_name,
        max_attempts=60,
        initial_delay=1,
    ):
        """Poll for CloudWatch Logs query results with exponential backoff.

        Args:
            ctx: MCP context
            logs_client: Boto3 CloudWatch Logs client
            query_id: ID of the query to poll for
            resource_type: Resource type for logging
            resource_name: Resource name for logging
            max_attempts: Maximum number of polling attempts before timing out
            initial_delay: Initial delay between polling attempts in seconds

        Returns:
            Query response when complete

        Raises:
            TimeoutError: If the query does not complete within the maximum number of attempts
        """
        attempts = 0
        delay = initial_delay

        log_with_request_id(
            ctx,
            LogLevel.INFO,
            f'Polling for CloudWatch Logs query results (query_id: {query_id})',
        )

        while attempts < max_attempts:
            query_response = logs_client.get_query_results(queryId=query_id)
            status = query_response.get('status')

            if status == 'Complete':
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'CloudWatch Logs query completed successfully after {attempts + 1} attempts',
                )
                return query_response
            elif status == 'Failed':
                error_message = f'CloudWatch Logs query failed for {resource_type} {resource_name}'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                raise Exception(error_message)
            elif status == 'Cancelled':
                error_message = (
                    f'CloudWatch Logs query was cancelled for {resource_type} {resource_name}'
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                raise Exception(error_message)

            # Log progress periodically
            if attempts % 5 == 0:
                log_with_request_id(
                    ctx,
                    LogLevel.INFO,
                    f'Waiting for CloudWatch Logs query to complete (attempt {attempts + 1}/{max_attempts})',
                )

            # Sleep with exponential backoff (capped at 5 seconds)
            time.sleep(min(delay, 5))
            delay = min(delay * 1.5, 5)  # Exponential backoff with a cap
            attempts += 1

        # If we've exhausted all attempts, raise a timeout error
        error_message = f'CloudWatch Logs query timed out after {max_attempts} attempts for {resource_type} {resource_name}'
        log_with_request_id(ctx, LogLevel.ERROR, error_message)
        raise TimeoutError(error_message)

    def _build_log_entry(self, result):
        """Build a log entry from CloudWatch Logs query result.

        Args:
            result: A single result from CloudWatch Logs query

        Returns:
            Formatted log entry dictionary
        """
        entry = {}
        for field in result:
            if field['field'] == '@timestamp':
                entry['timestamp'] = field['value']
            elif field['field'] == '@message':
                message = field['value']

                # Clean up the message to make it more human-readable
                message = message.replace('\n', '')
                message = message.replace('"', '"')

                # Try to parse JSON if the message appears to be JSON
                if message.startswith('{') and message.endswith('}'):
                    try:
                        parsed_json = json.loads(message)

                        # Format any nested JSON structures
                        parsed_json = self._format_nested_json(parsed_json)

                        entry['message'] = parsed_json
                    except json.JSONDecodeError:
                        # If it's not valid JSON, just use the cleaned message
                        entry['message'] = message
                else:
                    # For non-JSON messages, use the cleaned message
                    entry['message'] = message
            else:
                entry[field['field']] = field['value']
        return entry

    def _format_nested_json(self, obj):
        """Format nested JSON objects for better readability.

        Args:
            obj: The JSON object to format

        Returns:
            The formatted JSON object
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    obj[key] = self._format_nested_json(value)
                elif isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                    try:
                        obj[key] = json.loads(value)
                    except json.JSONDecodeError:
                        pass
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = self._format_nested_json(item)
        return obj
