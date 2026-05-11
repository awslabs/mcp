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

"""CloudWatch handler for the ROSA MCP Server.

Uses boto3 directly for CloudWatch Logs and Metrics operations.
Does NOT require the OCM client.
"""

import boto3
import datetime
import json
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from typing import Optional


class CloudWatchHandler:
    """Handler for CloudWatch log and metric operations for ROSA clusters."""

    def __init__(self, mcp, allow_sensitive_data_access: bool = False):
        """Initialize the CloudWatch handler.

        Args:
            mcp: The FastMCP server instance.
            allow_sensitive_data_access: Whether sensitive data access is permitted.
        """
        self.mcp = mcp
        self.allow_sensitive_data_access = allow_sensitive_data_access

        self.mcp.tool(name='rosa_get_cloudwatch_logs')(self.rosa_get_cloudwatch_logs)
        self.mcp.tool(name='rosa_get_cloudwatch_metrics')(self.rosa_get_cloudwatch_metrics)

    def _resolve_time_range(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        minutes: int = 15,
    ) -> tuple[datetime.datetime, datetime.datetime]:
        """Resolve start and end times for CloudWatch queries."""
        if end_time:
            end_dt = datetime.datetime.fromisoformat(end_time)
        else:
            end_dt = datetime.datetime.now(tz=datetime.timezone.utc)

        if start_time:
            start_dt = datetime.datetime.fromisoformat(start_time)
        else:
            start_dt = end_dt - datetime.timedelta(minutes=minutes)

        return start_dt, end_dt

    async def rosa_get_cloudwatch_logs(
        self,
        ctx: Context,
        log_group_name: str,
        filter_pattern: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """Get CloudWatch logs for a ROSA cluster.

        Retrieves log events from ROSA-related log groups (rosa-* pattern).

        Args:
            ctx: MCP context.
            log_group_name: CloudWatch log group name (e.g., /aws/rosa/my-cluster/worker).
            filter_pattern: CloudWatch filter pattern to match log events.
            start_time: Start time in ISO format. Defaults to 15 minutes ago.
            end_time: End time in ISO format. Defaults to now.
            limit: Maximum number of log events to return.
            region: AWS region. If omitted, uses default from environment.
        """
        if not self.allow_sensitive_data_access:
            raise ValueError(
                'Sensitive data access is not allowed. '
                'Start the server with --allow-sensitive-data-access to enable log retrieval.'
            )

        start_dt, end_dt = self._resolve_time_range(start_time, end_time)

        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region

            logs_client = boto3.client('logs', **kwargs)

            params = {
                'logGroupName': log_group_name,
                'startTime': int(start_dt.timestamp() * 1000),
                'endTime': int(end_dt.timestamp() * 1000),
                'limit': limit,
                'interleaved': True,
            }
            if filter_pattern:
                params['filterPattern'] = filter_pattern

            response = logs_client.filter_log_events(**params)

            events = []
            for event in response.get('events', []):
                events.append({
                    'timestamp': event.get('timestamp'),
                    'message': event.get('message'),
                    'logStreamName': event.get('logStreamName'),
                })

            return [TextContent(
                type='text',
                text=json.dumps({
                    'log_group': log_group_name,
                    'event_count': len(events),
                    'events': events,
                }, default=str),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error retrieving CloudWatch logs: {str(e)}',
            )]

    async def rosa_get_cloudwatch_metrics(
        self,
        ctx: Context,
        namespace: str,
        metric_name: str,
        dimensions: Optional[str] = None,
        stat: str = 'Average',
        period: int = 300,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[TextContent]:
        """Get CloudWatch metrics for a ROSA cluster.

        Retrieves metric data from the ContainerInsights namespace or other
        ROSA-related metric namespaces.

        Args:
            ctx: MCP context.
            namespace: CloudWatch metric namespace (e.g., "ContainerInsights", "AWS/EC2").
            metric_name: Name of the metric (e.g., "node_cpu_utilization").
            dimensions: JSON string of dimensions (e.g., '{"ClusterName": "my-cluster"}').
            stat: Statistic: Average, Sum, Minimum, Maximum, SampleCount.
            period: Period in seconds for each data point (minimum 60).
            start_time: Start time in ISO format. Defaults to 1 hour ago.
            end_time: End time in ISO format. Defaults to now.
            region: AWS region. If omitted, uses default from environment.
        """
        start_dt, end_dt = self._resolve_time_range(start_time, end_time, minutes=60)

        try:
            kwargs = {}
            if region:
                kwargs['region_name'] = region

            cw_client = boto3.client('cloudwatch', **kwargs)

            cw_dimensions = []
            if dimensions:
                dims = json.loads(dimensions)
                for key, value in dims.items():
                    cw_dimensions.append({'Name': key, 'Value': value})

            params = {
                'Namespace': namespace,
                'MetricName': metric_name,
                'StartTime': start_dt,
                'EndTime': end_dt,
                'Period': period,
                'Statistics': [stat],
            }
            if cw_dimensions:
                params['Dimensions'] = cw_dimensions

            response = cw_client.get_metric_statistics(**params)

            datapoints = sorted(
                response.get('Datapoints', []),
                key=lambda x: x.get('Timestamp', datetime.datetime.min),
            )

            formatted_points = []
            for dp in datapoints:
                ts = dp.get('Timestamp', '')
                formatted_points.append({
                    'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                    'value': dp.get(stat),
                    'unit': dp.get('Unit'),
                })

            return [TextContent(
                type='text',
                text=json.dumps({
                    'namespace': namespace,
                    'metric_name': metric_name,
                    'statistic': stat,
                    'period_seconds': period,
                    'datapoint_count': len(formatted_points),
                    'datapoints': formatted_points,
                }, default=str),
            )]

        except Exception as e:
            return [TextContent(
                type='text',
                text=f'Error retrieving CloudWatch metrics: {str(e)}',
            )]
