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

"""CloudWatch handler for the ROSA MCP Server."""

import json
from datetime import datetime, timedelta, timezone
from awslabs.rosa_mcp_server.aws_helper import AwsHelper
from awslabs.rosa_mcp_server.logging_helper import LogLevel, log_with_request_id
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import CallToolResult
from pydantic import Field
from typing import Dict, List, Optional


class CloudWatchHandler:
    """Handler for CloudWatch operations related to ROSA."""

    def __init__(self, mcp: FastMCP, allow_sensitive_data_access: bool = False):
        """Initialize the CloudWatch handler."""
        self.mcp = mcp
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self._register_tools()

    def _register_tools(self):
        """Register CloudWatch tools with the MCP server."""
        
        # Get CloudWatch metrics
        @self.mcp.tool()
        async def get_rosa_metrics(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            metric_name: str = Field(..., description='CloudWatch metric name'),
            namespace: str = Field('ContainerInsights', description='CloudWatch namespace'),
            start_time: Optional[str] = Field(None, description='Start time (ISO format or relative like -1h)'),
            end_time: Optional[str] = Field(None, description='End time (ISO format or relative like now)'),
            period: int = Field(300, description='Period in seconds (must be multiple of 60)'),
            stat: str = Field('Average', description='Statistic (Average, Sum, Maximum, Minimum, SampleCount)'),
            dimensions: Optional[Dict[str, str]] = Field(None, description='Metric dimensions'),
        ) -> CallToolResult:
            """Get CloudWatch metrics for a ROSA cluster.

            This tool retrieves metrics from CloudWatch for monitoring ROSA cluster performance.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                metric_name: Name of the metric to retrieve
                namespace: CloudWatch namespace
                start_time: Start time for metrics
                end_time: End time for metrics
                period: Aggregation period in seconds
                stat: Statistic to retrieve
                dimensions: Additional dimensions for filtering

            Returns:
                CallToolResult with metric data

            Example:
                get_rosa_metrics(
                    cluster_name="my-cluster",
                    metric_name="node_cpu_utilization",
                    start_time="-1h",
                    stat="Average"
                )
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Getting CloudWatch metrics', 
                              cluster_name=cluster_name, metric_name=metric_name)
            
            try:
                cloudwatch_client = AwsHelper.create_boto3_client('cloudwatch')
                
                # Parse time parameters
                now = datetime.now(timezone.utc)
                if start_time:
                    if start_time.startswith('-'):
                        # Relative time like -1h
                        hours = int(start_time[1:-1])
                        start_dt = now - timedelta(hours=hours)
                    else:
                        start_dt = datetime.fromisoformat(start_time)
                else:
                    start_dt = now - timedelta(hours=1)
                
                if end_time and end_time != 'now':
                    end_dt = datetime.fromisoformat(end_time)
                else:
                    end_dt = now
                
                # Build dimensions
                metric_dimensions = [
                    {'Name': 'ClusterName', 'Value': cluster_name}
                ]
                if dimensions:
                    for name, value in dimensions.items():
                        metric_dimensions.append({'Name': name, 'Value': value})
                
                # Get metric statistics
                response = cloudwatch_client.get_metric_statistics(
                    Namespace=namespace,
                    MetricName=metric_name,
                    Dimensions=metric_dimensions,
                    StartTime=start_dt,
                    EndTime=end_dt,
                    Period=period,
                    Statistics=[stat]
                )
                
                # Format datapoints
                datapoints = []
                for dp in sorted(response['Datapoints'], key=lambda x: x['Timestamp']):
                    datapoints.append({
                        'Timestamp': dp['Timestamp'].isoformat(),
                        'Value': dp.get(stat, 0),
                        'Unit': dp.get('Unit', 'None')
                    })
                
                result = {
                    'MetricName': metric_name,
                    'ClusterName': cluster_name,
                    'Statistic': stat,
                    'Period': period,
                    'DatapointCount': len(datapoints),
                    'Datapoints': datapoints
                }
                
                return CallToolResult(
                    success=True,
                    content=json.dumps(result, indent=2)
                )
                
            except Exception as e:
                error_msg = f'Failed to get metrics: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # List available metrics
        @self.mcp.tool()
        async def list_rosa_metrics(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            namespace: str = Field('ContainerInsights', description='CloudWatch namespace'),
        ) -> CallToolResult:
            """List available CloudWatch metrics for a ROSA cluster.

            This tool lists all metrics available for monitoring a ROSA cluster.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                namespace: CloudWatch namespace to search

            Returns:
                CallToolResult with metric list

            Example:
                list_rosa_metrics(cluster_name="my-cluster")
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Listing available metrics', 
                              cluster_name=cluster_name)
            
            try:
                cloudwatch_client = AwsHelper.create_boto3_client('cloudwatch')
                
                # List metrics with cluster dimension
                paginator = cloudwatch_client.get_paginator('list_metrics')
                metrics = []
                
                for page in paginator.paginate(
                    Namespace=namespace,
                    Dimensions=[
                        {'Name': 'ClusterName', 'Value': cluster_name}
                    ]
                ):
                    for metric in page['Metrics']:
                        metric_info = {
                            'MetricName': metric['MetricName'],
                            'Dimensions': {d['Name']: d['Value'] for d in metric['Dimensions']}
                        }
                        metrics.append(metric_info)
                
                # Group by metric name
                grouped_metrics = {}
                for metric in metrics:
                    name = metric['MetricName']
                    if name not in grouped_metrics:
                        grouped_metrics[name] = []
                    grouped_metrics[name].append(metric['Dimensions'])
                
                return CallToolResult(
                    success=True,
                    content=json.dumps({
                        'ClusterName': cluster_name,
                        'Namespace': namespace,
                        'MetricCount': len(grouped_metrics),
                        'Metrics': grouped_metrics
                    }, indent=2)
                )
                
            except Exception as e:
                error_msg = f'Failed to list metrics: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Get CloudWatch logs
        @self.mcp.tool()
        async def get_rosa_cloudwatch_logs(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            log_group: str = Field(..., description='CloudWatch log group name'),
            log_stream: Optional[str] = Field(None, description='Specific log stream name'),
            start_time: Optional[str] = Field(None, description='Start time (ISO format or relative like -1h)'),
            end_time: Optional[str] = Field(None, description='End time (ISO format or relative like now)'),
            filter_pattern: Optional[str] = Field(None, description='CloudWatch filter pattern'),
            limit: int = Field(100, description='Maximum number of log events to return'),
        ) -> CallToolResult:
            """Get CloudWatch logs for a ROSA cluster.

            This tool retrieves logs from CloudWatch Logs for ROSA cluster components.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                log_group: CloudWatch log group name
                log_stream: Optional specific log stream
                start_time: Start time for logs
                end_time: End time for logs
                filter_pattern: CloudWatch filter pattern
                limit: Maximum number of events

            Returns:
                CallToolResult with log events

            Example:
                get_rosa_cloudwatch_logs(
                    cluster_name="my-cluster",
                    log_group="/aws/containerinsights/my-cluster/application",
                    start_time="-1h",
                    filter_pattern="ERROR"
                )
            """
            if not self.allow_sensitive_data_access:
                return CallToolResult(
                    success=False,
                    content='Sensitive data access is required to read logs. Run with --allow-sensitive-data-access flag.'
                )
            
            log_with_request_id(ctx, LogLevel.INFO, 'Getting CloudWatch logs', 
                              cluster_name=cluster_name, log_group=log_group)
            
            try:
                logs_client = AwsHelper.create_boto3_client('logs')
                
                # Parse time parameters
                now = datetime.now(timezone.utc)
                if start_time:
                    if start_time.startswith('-'):
                        hours = int(start_time[1:-1])
                        start_dt = now - timedelta(hours=hours)
                    else:
                        start_dt = datetime.fromisoformat(start_time)
                else:
                    start_dt = now - timedelta(hours=1)
                
                if end_time and end_time != 'now':
                    end_dt = datetime.fromisoformat(end_time)
                else:
                    end_dt = now
                
                # Convert to timestamps
                start_ts = int(start_dt.timestamp() * 1000)
                end_ts = int(end_dt.timestamp() * 1000)
                
                # Build query parameters
                query_params = {
                    'logGroupName': log_group,
                    'startTime': start_ts,
                    'endTime': end_ts,
                    'limit': limit
                }
                
                if log_stream:
                    query_params['logStreamName'] = log_stream
                
                if filter_pattern:
                    query_params['filterPattern'] = filter_pattern
                
                # Get log events
                if log_stream:
                    response = logs_client.filter_log_events(**query_params)
                else:
                    # For multiple streams, use filter_log_events
                    response = logs_client.filter_log_events(**query_params)
                
                # Format events
                events = []
                for event in response.get('events', []):
                    events.append({
                        'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                        'message': event['message'],
                        'logStreamName': event.get('logStreamName', '')
                    })
                
                result = {
                    'ClusterName': cluster_name,
                    'LogGroup': log_group,
                    'EventCount': len(events),
                    'Events': events
                }
                
                return CallToolResult(
                    success=True,
                    content=json.dumps(result, indent=2)
                )
                
            except Exception as e:
                error_msg = f'Failed to get logs: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)

        # Create CloudWatch alarm
        @self.mcp.tool()
        async def create_rosa_cloudwatch_alarm(
            ctx: Context,
            cluster_name: str = Field(..., description='Name of the ROSA cluster'),
            alarm_name: str = Field(..., description='Name for the alarm'),
            metric_name: str = Field(..., description='Metric name to monitor'),
            namespace: str = Field('ContainerInsights', description='CloudWatch namespace'),
            statistic: str = Field('Average', description='Statistic to use'),
            period: int = Field(300, description='Period in seconds'),
            evaluation_periods: int = Field(2, description='Number of periods to evaluate'),
            threshold: float = Field(..., description='Threshold value'),
            comparison_operator: str = Field('GreaterThanThreshold', 
                                           description='Comparison operator (GreaterThanThreshold, LessThanThreshold, etc.)'),
            alarm_description: Optional[str] = Field(None, description='Alarm description'),
            dimensions: Optional[Dict[str, str]] = Field(None, description='Additional dimensions'),
        ) -> CallToolResult:
            """Create a CloudWatch alarm for a ROSA cluster.

            This tool creates an alarm to monitor ROSA cluster metrics and alert on issues.

            Args:
                ctx: MCP context
                cluster_name: Name of the ROSA cluster
                alarm_name: Name for the alarm
                metric_name: Metric to monitor
                namespace: CloudWatch namespace
                statistic: Statistic to use
                period: Evaluation period
                evaluation_periods: Number of periods
                threshold: Threshold value
                comparison_operator: How to compare metric to threshold
                alarm_description: Optional description
                dimensions: Additional metric dimensions

            Returns:
                CallToolResult indicating success or failure

            Example:
                create_rosa_cloudwatch_alarm(
                    cluster_name="my-cluster",
                    alarm_name="high-cpu-alarm",
                    metric_name="node_cpu_utilization",
                    threshold=80.0,
                    comparison_operator="GreaterThanThreshold",
                    alarm_description="Alert when CPU usage exceeds 80%"
                )
            """
            log_with_request_id(ctx, LogLevel.INFO, 'Creating CloudWatch alarm', 
                              cluster_name=cluster_name, alarm_name=alarm_name)
            
            try:
                cloudwatch_client = AwsHelper.create_boto3_client('cloudwatch')
                
                # Build dimensions
                metric_dimensions = [
                    {'Name': 'ClusterName', 'Value': cluster_name}
                ]
                if dimensions:
                    for name, value in dimensions.items():
                        metric_dimensions.append({'Name': name, 'Value': value})
                
                # Create alarm
                cloudwatch_client.put_metric_alarm(
                    AlarmName=alarm_name,
                    ComparisonOperator=comparison_operator,
                    EvaluationPeriods=evaluation_periods,
                    MetricName=metric_name,
                    Namespace=namespace,
                    Period=period,
                    Statistic=statistic,
                    Threshold=threshold,
                    AlarmDescription=alarm_description or f'Alarm for ROSA cluster {cluster_name}',
                    Dimensions=metric_dimensions,
                    Tags=[
                        {'Key': 'rosa-cluster', 'Value': cluster_name},
                        {'Key': 'managed-by', 'Value': 'rosa-mcp-server'}
                    ]
                )
                
                return CallToolResult(
                    success=True,
                    content=f'Successfully created alarm {alarm_name} for cluster {cluster_name}'
                )
                
            except Exception as e:
                error_msg = f'Failed to create alarm: {str(e)}'
                log_with_request_id(ctx, LogLevel.ERROR, error_msg)
                return CallToolResult(success=False, content=error_msg)