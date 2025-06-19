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

"""CloudWatch Metrics tools for MCP server."""

import boto3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from awslabs.cloudwatch_mcp_server import MCP_SERVER_VERSION
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    Dimension,
    MetricDataPoint,
    MetricDataResult,
    GetMetricDataResponse,
)
from botocore.config import Config
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Dict, Any, Optional, List, Union


class CloudWatchMetricsTools:
    """CloudWatch Metrics tools for MCP server."""
    
    def __init__(self):
        """Initialize the CloudWatch Metrics client"""
        # Initialize client
        aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')
        config = Config(user_agent_extra=f'awslabs/mcp/cloudwatch-mcp-server/{MCP_SERVER_VERSION}')

        try:
            if aws_profile := os.environ.get('AWS_PROFILE'):
                self.cloudwatch_client = boto3.Session(profile_name=aws_profile, region_name=aws_region).client(
                    'cloudwatch', config=config
                )
            else:
                self.cloudwatch_client = boto3.Session(region_name=aws_region).client('cloudwatch', config=config)
        except Exception as e:
            logger.error(f'Error creating cloudwatch client: {str(e)}')
            raise



    def register(self, mcp):
        """Register all CloudWatch Metrics tools with the MCP server."""
        # Register get_metric_data tool
        mcp.tool(
            name='get_metric_data'
        )(self.get_metric_data)
        
    async def get_metric_data(
        self,
        ctx: Context,
        namespace: str = Field(
            ...,
            description="The namespace of the metric (e.g., 'AWS/EC2', 'AWS/Lambda')"
        ),
        metric_name: str = Field(
            ...,
            description="The name of the metric (e.g., 'CPUUtilization', 'Duration')"
        ),
        dimensions: List[Dimension] = Field(
            default_factory=list,
            description="List of dimensions that identify the metric, each with name and value"
        ),
        start_time: Union[str, datetime] = Field(
            ...,
            description="The start time for the metric data query in ISO format (e.g., '2023-01-01T00:00:00Z') or as a datetime object"
        ),
        end_time: Optional[Union[str, datetime]] = Field(
            None,
            description="The end time for the metric data query in ISO format (e.g., '2023-01-01T00:00:00Z') or as a datetime object. Defaults to current time if not provided."
        ),
        statistic: str = Field(
            "Average",
            description="The statistic to use for the metric (e.g., 'Average', 'Sum', 'Maximum', 'Minimum', 'SampleCount', 'p99')"
        ),
        target_datapoints: int = Field(
            60,
            description="Target number of data points to return (default: 60). Controls the granularity of the returned data."
        ),
    ) -> GetMetricDataResponse:
        """Retrieves CloudWatch metric data for a specific metric.

        This tool retrieves metric data from CloudWatch for a specific metric identified by its
        namespace, metric name, and dimensions, within a specified time range.

        Usage: Use this tool to get actual metric data from CloudWatch for analysis or visualization.

        Args:
            namespace: The metric namespace (e.g., "AWS/EC2", "AWS/Lambda")
            metric_name: The name of the metric (e.g., "CPUUtilization", "Duration")
            dimensions: List of dimensions with name and value pairs
            start_time: The start time for the metric data query (ISO format or datetime)
            end_time: The end time for the metric data query (ISO format or datetime), defaults to current time
            statistic: The statistic to use for the metric (e.g., 'Average', 'Sum')
            target_datapoints: Target number of data points to return (default: 60). Controls the granularity of the returned data.

        Returns:
            GetMetricDataResponse: An object containing the metric data results

        Example:
            result = await get_metric_data(
                ctx,
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions=[
                    Dimension(name="InstanceId", value="i-1234567890abcdef0")
                ],
                start_time="2023-01-01T00:00:00Z",
                # period will be auto-calculated based on time window
                statistic="Average"
            )
            for metric_result in result.metricDataResults:
                print(f"Metric: {metric_result.label}")
                for datapoint in metric_result.datapoints:
                    print(f"  {datapoint.timestamp}: {datapoint.value}")
        """
        try:
            # Process start_time and end_time
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            if end_time is None:
                end_time = datetime.utcnow()
            elif isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Calculate period based on time window and target datapoints
            time_window_seconds = int((end_time - start_time).total_seconds())
            
            # Calculate period based on time window and target datapoints
            # Ensure period is at least 60 seconds and a multiple of 60
            calculated_period = max(60, int(time_window_seconds / target_datapoints))
            # Round up to the nearest multiple of 60
            period = calculated_period + (60 - calculated_period % 60) if calculated_period % 60 != 0 else calculated_period
            
            logger.info(f'Calculated period: {period} seconds for time window of {time_window_seconds} seconds with target of {target_datapoints} datapoints')
            
            logger.info(f'Getting metric data for {namespace}/{metric_name} from {start_time} to {end_time} with period {period}s (target: {target_datapoints} datapoints)')
            logger.info(f'Dimensions: {[f"{d.name}={d.value}" for d in dimensions]}')
            
            # Convert dimensions to CloudWatch format
            cw_dimensions = [{'Name': d.name, 'Value': d.value} for d in dimensions]
            
            # Create the metric data query
            metric_query = {
                'Id': 'm1',  # Using a simple ID for the single metric query
                'MetricStat': {
                    'Metric': {
                        'Namespace': namespace,
                        'MetricName': metric_name,
                        'Dimensions': cw_dimensions
                    },
                    'Period': period,
                    'Stat': statistic
                },
                'ReturnData': True
            }
            
            # Call the GetMetricData API
            response = self.cloudwatch_client.get_metric_data(
                MetricDataQueries=[metric_query],
                StartTime=start_time,
                EndTime=end_time
            )
            
            # Process the response
            metric_data_results = []
            for result in response.get('MetricDataResults', []):
                # Process timestamps and values into data points
                datapoints = []
                timestamps = result.get('Timestamps', [])
                values = result.get('Values', [])
                
                for ts, val in zip(timestamps, values):
                    datapoints.append(MetricDataPoint(
                        timestamp=ts,
                        value=val
                    ))
                
                # Sort datapoints by timestamp
                datapoints.sort(key=lambda x: x.timestamp)
                
                # Create the metric data result
                metric_result = MetricDataResult(
                    id=result.get('Id', ''),
                    label=result.get('Label', ''),
                    statusCode=result.get('StatusCode', 'Complete'),
                    datapoints=datapoints,
                    messages=result.get('Messages', [])
                )
                metric_data_results.append(metric_result)
            
            # Create and return the response
            return GetMetricDataResponse(
                metricDataResults=metric_data_results,
                messages=response.get('Messages', [])
            )
            
        except Exception as e:
            logger.error(f'Error in get_metric_data: {str(e)}')
            await ctx.error(f'Error getting metric data: {str(e)}')
            raise
