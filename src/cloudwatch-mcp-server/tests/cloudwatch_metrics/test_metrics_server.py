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
"""Tests for the CloudWatch Metrics functionality in the MCP Server."""

import boto3
import os
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    Dimension,
    MetricDataPoint,
    MetricDataResult,
    GetMetricDataResponse,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from awslabs.cloudwatch_mcp_server.server import mcp
from moto import mock_aws
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch


@pytest_asyncio.fixture
async def ctx():
    """Fixture to provide mock context."""
    return AsyncMock()


@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_REGION'] = 'us-west-2'


@pytest_asyncio.fixture
async def cloudwatch_client(aws_credentials):
    """Create mocked AWS client for any service."""
    with mock_aws():
        # Mock any AWS service, not just CloudWatch
        client: Any = MagicMock()
        yield client


@pytest_asyncio.fixture
async def cloudwatch_metrics_tools(cloudwatch_client):
    """Create CloudWatchMetricsTools instance with mocked client."""
    with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session') as mock_session:
        mock_session.return_value.client.return_value = cloudwatch_client
        tools = CloudWatchMetricsTools()
        yield tools


@pytest.mark.asyncio
class TestCloudWatchMetricsServer:
    """Tests for CloudWatch Metrics server integration."""


@pytest.mark.asyncio
class TestGetMetricData:
    """Tests for get_metric_data tool."""

    async def test_get_metric_data_basic(self, ctx, cloudwatch_metrics_tools):
        """Test basic metric data retrieval."""
        # Mock the CloudWatch client's get_metric_data method
        cloudwatch_metrics_tools.cloudwatch_client.get_metric_data = MagicMock(
            return_value={
                'MetricDataResults': [
                    {
                        'Id': 'm1',
                        'Label': 'CPUUtilization',
                        'StatusCode': 'Complete',
                        'Timestamps': [
                            datetime(2023, 1, 1, 0, 0, 0),
                            datetime(2023, 1, 1, 0, 5, 0),
                        ],
                        'Values': [10.5, 15.2],
                    }
                ],
            }
        )

        # Call the tool
        start_time = datetime(2023, 1, 1, 0, 0, 0)
        end_time = datetime(2023, 1, 1, 1, 0, 0)
        
        result = await cloudwatch_metrics_tools.get_metric_data(
            ctx,
            namespace='AWS/EC2',
            metric_name='CPUUtilization',
            dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
            start_time=start_time,
            end_time=end_time,
            statistic='Average',
            target_datapoints=60,
        )

        # Verify the CloudWatch client was called with correct parameters
        cloudwatch_metrics_tools.cloudwatch_client.get_metric_data.assert_called_once()
        call_args = cloudwatch_metrics_tools.cloudwatch_client.get_metric_data.call_args[1]
        
        assert len(call_args['MetricDataQueries']) == 1
        assert call_args['MetricDataQueries'][0]['MetricStat']['Metric']['Namespace'] == 'AWS/EC2'
        assert call_args['MetricDataQueries'][0]['MetricStat']['Metric']['MetricName'] == 'CPUUtilization'
        assert call_args['MetricDataQueries'][0]['MetricStat']['Stat'] == 'Average'
        assert call_args['StartTime'] == start_time
        assert call_args['EndTime'] == end_time

        # Verify the result structure
        assert isinstance(result, GetMetricDataResponse)
        assert len(result.metricDataResults) == 1
        assert result.metricDataResults[0].label == 'CPUUtilization'
        assert len(result.metricDataResults[0].datapoints) == 2
        assert result.metricDataResults[0].datapoints[0].value == 10.5
        assert result.metricDataResults[0].datapoints[1].value == 15.2

    async def test_get_metric_data_with_string_dates(self, ctx, cloudwatch_metrics_tools):
        """Test metric data retrieval with string dates."""
        # Mock the CloudWatch client's get_metric_data method
        cloudwatch_metrics_tools.cloudwatch_client.get_metric_data = MagicMock(
            return_value={
                'MetricDataResults': [
                    {
                        'Id': 'm1',
                        'Label': 'CPUUtilization',
                        'StatusCode': 'Complete',
                        'Timestamps': [
                            datetime(2023, 1, 1, 0, 0, 0),
                        ],
                        'Values': [10.5],
                    }
                ],
            }
        )

        # Call the tool with string dates
        result = await cloudwatch_metrics_tools.get_metric_data(
            ctx,
            namespace='AWS/EC2',
            metric_name='CPUUtilization',
            dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
            start_time='2023-01-01T00:00:00Z',
            end_time='2023-01-01T01:00:00Z',
            statistic='Average',
            target_datapoints=60,
        )

        # Verify the result
        assert isinstance(result, GetMetricDataResponse)
        assert len(result.metricDataResults) == 1
        assert len(result.metricDataResults[0].datapoints) == 1

    async def test_get_metric_data_period_calculation(self, ctx, cloudwatch_metrics_tools):
        """Test that period is calculated correctly based on time window and target datapoints."""
        # Mock the CloudWatch client's get_metric_data method
        cloudwatch_metrics_tools.cloudwatch_client.get_metric_data = MagicMock(
            return_value={
                'MetricDataResults': [{'Id': 'm1', 'Label': 'Test', 'StatusCode': 'Complete', 'Timestamps': [], 'Values': []}],
            }
        )

        # Call the tool with a 2-hour time window and 30 target datapoints
        # This should result in a period of 240 seconds (4 minutes)
        start_time = datetime(2023, 1, 1, 0, 0, 0)
        end_time = datetime(2023, 1, 1, 2, 0, 0)  # 2 hours = 7200 seconds
        
        await cloudwatch_metrics_tools.get_metric_data(
            ctx,
            namespace='AWS/EC2',
            metric_name='CPUUtilization',
            dimensions=[],
            start_time=start_time,
            end_time=end_time,
            statistic='Average',
            target_datapoints=30,  # 7200 / 30 = 240 seconds
        )

        # Verify the period calculation
        call_args = cloudwatch_metrics_tools.cloudwatch_client.get_metric_data.call_args[1]
        calculated_period = call_args['MetricDataQueries'][0]['MetricStat']['Period']
        
        # Period should be 240 seconds (rounded to nearest multiple of 60)
        assert calculated_period == 240

    async def test_get_metric_data_error_handling(self, ctx, cloudwatch_metrics_tools):
        """Test error handling in get_metric_data."""
        # Mock an exception in the CloudWatch client
        cloudwatch_metrics_tools.cloudwatch_client.get_metric_data = MagicMock(
            side_effect=Exception('Test exception')
        )

        # Set up the context's error method
        ctx.error = AsyncMock()

        # Call the tool and expect an exception
        with pytest.raises(Exception):
            await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                dimensions=[],
                start_time='2023-01-01T00:00:00Z',
                end_time='2023-01-01T01:00:00Z',
                statistic='Average',
                target_datapoints=60,
            )

        # Verify error was reported to context
        ctx.error.assert_called_once()
        assert 'Test exception' in ctx.error.call_args[0][0]