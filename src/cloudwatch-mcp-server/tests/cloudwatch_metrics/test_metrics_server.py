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

import os
import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    AnomalyDetectionAlarmThreshold,
    Dimension,
    GetMetricDataResponse,
    MetricDataQueryInput,
    MetricStatInput,
    StaticAlarmThreshold,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from datetime import datetime, timedelta, timezone
from moto import mock_aws
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


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
    with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
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
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
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
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            start_time = datetime(2023, 1, 1, 0, 0, 0)
            end_time = datetime(2023, 1, 1, 1, 0, 0)
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=start_time,
                dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                end_time=end_time,
                statistic='AVG',
                target_datapoints=60,
            )
            mock_client.get_metric_data.assert_called_once()
            call_args = mock_client.get_metric_data.call_args[1]
            assert len(call_args['MetricDataQueries']) == 1
            assert 'MetricStat' in call_args['MetricDataQueries'][0]
            assert (
                call_args['MetricDataQueries'][0]['MetricStat']['Metric']['Namespace'] == 'AWS/EC2'
            )
            assert (
                call_args['MetricDataQueries'][0]['MetricStat']['Metric']['MetricName']
                == 'CPUUtilization'
            )
            assert call_args['MetricDataQueries'][0]['MetricStat']['Stat'] == 'Average'

            assert call_args['StartTime'] == start_time.replace(tzinfo=timezone.utc)
            assert call_args['EndTime'] == end_time.replace(tzinfo=timezone.utc)
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].label == 'CPUUtilization'
            assert len(result.metricDataResults[0].datapoints) == 2
            assert result.metricDataResults[0].datapoints[0].value == 10.5
            assert result.metricDataResults[0].datapoints[1].value == 15.2

    async def test_get_metric_data_with_string_dates(self, ctx, cloudwatch_metrics_tools):
        """Test metric data retrieval with string dates."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
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
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time='2023-01-01T00:00:00Z',
                dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                end_time='2023-01-01T01:00:00Z',
                statistic='AVG',
                target_datapoints=60,
            )
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert len(result.metricDataResults[0].datapoints) == 1

    async def test_get_metric_data_period_calculation(self, ctx, cloudwatch_metrics_tools):
        """Test that period is calculated correctly based on time window and target datapoints."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'Test',
                    'StatusCode': 'Complete',
                    'Timestamps': [],
                    'Values': [],
                }
            ],
        }
        start_time = datetime(2023, 1, 1, 0, 0, 0)
        end_time = datetime(2023, 1, 1, 2, 0, 0)  # 2 hours = 7200 seconds
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=start_time,
                dimensions=[],
                end_time=end_time,
                statistic='AVG',
                target_datapoints=30,  # 7200 / 30 = 240 seconds
            )
            call_args = mock_client.get_metric_data.call_args[1]
            calculated_period = call_args['MetricDataQueries'][0]['MetricStat']['Period']
            assert calculated_period == 240

    async def test_get_metric_data_with_metrics_insights_group_by(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test metric data retrieval using Metrics Insights with group by."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'Average(CPUUtilization)',
                    'StatusCode': 'Complete',
                    'Timestamps': [
                        datetime(2023, 1, 1, 0, 0, 0),
                        datetime(2023, 1, 1, 0, 5, 0),
                    ],
                    'Values': [10.5, 15.2],
                }
            ],
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            start_time = datetime(2023, 1, 1, 0, 0, 0)
            end_time = datetime(2023, 1, 1, 1, 0, 0)
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=start_time,
                end_time=end_time,
                group_by_dimension='InstanceId',
                schema_dimension_keys=['InstanceId'],
                statistic='AVG',
                target_datapoints=60,
            )
            mock_client.get_metric_data.assert_called_once()
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].label == 'Average(CPUUtilization)'
            assert len(result.metricDataResults[0].datapoints) == 2
            assert result.metricDataResults[0].datapoints[0].value == 10.5
            assert result.metricDataResults[0].datapoints[1].value == 15.2

    async def test_get_metric_data_with_metrics_insights_dimension_keys(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test metric data retrieval using Metrics Insights with schema dimension keys specified."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'Average(CPUUtilization)',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2023, 1, 1, 0, 0, 0)],
                    'Values': [10.5],
                }
            ],
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=datetime(2023, 1, 1, 0, 0, 0),
                end_time=datetime(2023, 1, 1, 1, 0, 0),
                schema_dimension_keys=['InstanceId', 'InstanceType'],
                statistic='AVG',
                target_datapoints=60,
            )
            mock_client.get_metric_data.assert_called_once()
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].label == 'Average(CPUUtilization)'
            assert len(result.metricDataResults[0].datapoints) == 1
            assert result.metricDataResults[0].datapoints[0].value == 10.5

    async def test_get_metric_data_with_metrics_insights_limit_and_order(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test metric data retrieval using Metrics Insights with ORDER BY and LIMIT."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'Average(CPUUtilization)',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2023, 1, 1, 0, 0, 0)],
                    'Values': [10.5],
                }
            ],
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=datetime(2023, 1, 1, 0, 0, 0),
                end_time=datetime(2023, 1, 1, 1, 0, 0),
                schema_dimension_keys=['InstanceId'],
                group_by_dimension='InstanceId',
                order_by_statistic='MAX',
                sort_order='DESC',
                limit=5,
                statistic='AVG',
                target_datapoints=60,
            )
            mock_client.get_metric_data.assert_called_once()
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].label == 'Average(CPUUtilization)'
            assert len(result.metricDataResults[0].datapoints) == 1
            assert result.metricDataResults[0].datapoints[0].value == 10.5

    async def test_get_metric_data_with_different_order_by_statistic(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test metric data retrieval using Metrics Insights with a different ORDER BY statistic."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'Average(CPUUtilization)',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2023, 1, 1, 0, 0, 0)],
                    'Values': [10.5],
                }
            ],
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=datetime(2023, 1, 1, 0, 0, 0),
                end_time=datetime(2023, 1, 1, 1, 0, 0),
                schema_dimension_keys=['InstanceId'],
                group_by_dimension='InstanceId',
                order_by_statistic='SUM',
                sort_order='DESC',
                limit=5,
                statistic='AVG',
                target_datapoints=60,
            )
            mock_client.get_metric_data.assert_called_once()
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].label == 'Average(CPUUtilization)'
            assert len(result.metricDataResults[0].datapoints) == 1
            assert result.metricDataResults[0].datapoints[0].value == 10.5

    async def test_get_metric_data_with_metrics_insights_and_dimensions(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test metric data retrieval using Metrics Insights with both specific dimensions and schema dimension keys."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'Average(CPUUtilization)',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2023, 1, 1, 0, 0, 0)],
                    'Values': [10.5],
                }
            ],
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=datetime(2023, 1, 1, 0, 0, 0),
                end_time=datetime(2023, 1, 1, 1, 0, 0),
                dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                schema_dimension_keys=['InstanceId'],
                group_by_dimension='InstanceId',
                statistic='AVG',
                target_datapoints=60,
            )
            mock_client.get_metric_data.assert_called_once()
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].label == 'Average(CPUUtilization)'
            assert len(result.metricDataResults[0].datapoints) == 1
            assert result.metricDataResults[0].datapoints[0].value == 10.5

    async def test_order_by_statistic_without_sort_order(self, ctx, cloudwatch_metrics_tools):
        """Test that ORDER BY clause is added when order_by_statistic is specified but sort_order is not."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'Average(CPUUtilization)',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2023, 1, 1, 0, 0, 0)],
                    'Values': [10.5],
                }
            ],
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=datetime(2023, 1, 1, 0, 0, 0),
                end_time=datetime(2023, 1, 1, 1, 0, 0),
                schema_dimension_keys=['InstanceId'],
                group_by_dimension='InstanceId',
                order_by_statistic='MAX',
                statistic='AVG',
                target_datapoints=60,
            )
            mock_client.get_metric_data.assert_called_once()
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].label == 'Average(CPUUtilization)'
            assert len(result.metricDataResults[0].datapoints) == 1
            assert result.metricDataResults[0].datapoints[0].value == 10.5

    async def test_no_order_by_when_neither_specified(self, ctx, cloudwatch_metrics_tools):
        """Test that ORDER BY clause is not added when neither order_by_statistic nor sort_order is specified."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'Average(CPUUtilization)',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2023, 1, 1, 0, 0, 0)],
                    'Values': [10.5],
                }
            ],
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=datetime(2023, 1, 1, 0, 0, 0),
                end_time=datetime(2023, 1, 1, 1, 0, 0),
                schema_dimension_keys=['InstanceId'],
                group_by_dimension='InstanceId',
                statistic='AVG',
                target_datapoints=60,
            )
            mock_client.get_metric_data.assert_called_once()
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].label == 'Average(CPUUtilization)'
            assert len(result.metricDataResults[0].datapoints) == 1
            assert result.metricDataResults[0].datapoints[0].value == 10.5

    async def test_error_when_sort_order_without_order_by_statistic(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test that an error is raised when sort_order is specified but order_by_statistic is not."""
        # Call the tool with sort_order but without order_by_statistic
        with pytest.raises(ValueError) as excinfo:
            await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time='2023-01-01T00:00:00Z',
                end_time='2023-01-01T01:00:00Z',
                statistic='AVG',
                group_by_dimension='InstanceId',
                schema_dimension_keys=['InstanceId'],
                sort_order='DESC',  # Specify sort_order but not order_by_statistic
            )

        # Verify the error message
        assert 'If sort_order is specified, order_by_statistic must also be specified' in str(
            excinfo.value
        )

    async def test_get_metric_data_error_handling(self, ctx, cloudwatch_metrics_tools):
        """Test error handling in get_metric_data."""
        mock_client = MagicMock()
        mock_client.get_metric_data.side_effect = Exception('Test exception')
        ctx.error = AsyncMock()
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception):
                await cloudwatch_metrics_tools.get_metric_data(
                    ctx,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    start_time='2023-01-01T00:00:00Z',
                    dimensions=[],
                    end_time='2023-01-01T01:00:00Z',
                    statistic='AVG',
                    target_datapoints=60,
                )
            ctx.error.assert_called_once()
            assert 'Test exception' in ctx.error.call_args[0][0]

    @pytest.mark.parametrize(
        'start_time,end_time,test_description',
        [
            # Timezone-aware start, no end (defaults to now)
            (
                '2023-01-01T00:00:00+00:00',
                None,
                'timezone-aware start_time with None end_time (defaults to now)',
            ),
            # Both timezone-aware
            (
                '2023-01-01T00:00:00+00:00',
                '2023-01-01T01:00:00+00:00',
                'both timezone-aware (ISO strings)',
            ),
            # Both naive datetime objects
            (
                datetime(2023, 1, 1, 0, 0, 0),
                datetime(2023, 1, 1, 1, 0, 0),
                'both naive datetime objects',
            ),
            # Timezone-aware datetime objects
            (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=__import__('datetime').timezone.utc),
                datetime(2023, 1, 1, 1, 0, 0, tzinfo=__import__('datetime').timezone.utc),
                'both timezone-aware datetime objects',
            ),
            # Mixed: naive start, timezone-aware end (ISO string)
            (
                datetime(2023, 1, 1, 0, 0, 0),
                '2023-01-01T01:00:00+00:00',
                'naive datetime start with timezone-aware ISO string end',
            ),
            # Mixed: timezone-aware start (ISO string), naive end
            (
                '2023-01-01T00:00:00+00:00',
                datetime(2023, 1, 1, 1, 0, 0),
                'timezone-aware ISO string start with naive datetime end',
            ),
            # Naive start, no end
            (
                datetime(2023, 1, 1, 0, 0, 0),
                None,
                'naive datetime start with None end_time',
            ),
            # Different timezone offsets
            (
                '2023-01-01T00:00:00-05:00',
                '2023-01-01T06:00:00+00:00',
                'different timezone offsets (EST and UTC)',
            ),
            # ISO string with Z notation
            (
                '2023-01-01T00:00:00Z',
                '2023-01-01T01:00:00Z',
                'ISO strings with Z notation',
            ),
        ],
    )
    async def test_get_metric_data_with_various_datetime_formats(
        self, ctx, cloudwatch_metrics_tools, start_time, end_time, test_description
    ):
        """Parametrized test for various datetime format combinations.

        Tests all combinations of:
        - Timezone-aware vs naive datetimes
        - ISO strings vs datetime objects
        - With and without end_time (None defaults to now)
        - Different timezone offsets

        This ensures the fix for timezone handling works correctly in all scenarios.
        """
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'CPUUtilization',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)],
                    'Values': [10.5],
                }
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                start_time=start_time,
                end_time=end_time,
                dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                statistic='AVG',
                target_datapoints=60,
            )

            # Should not raise an error and should return valid response
            assert isinstance(result, GetMetricDataResponse), f'Failed for: {test_description}'
            assert len(result.metricDataResults) == 1, f'Failed for: {test_description}'

    async def test_get_metric_metadata_found(self, ctx, cloudwatch_metrics_tools):
        """Test getting metric metadata for existing metric."""
        result = await cloudwatch_metrics_tools.get_metric_metadata(
            ctx, namespace='AWS/EC2', metric_name='CPUUtilization'
        )

        # Should return MetricDescription or None
        if result is not None:
            from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import MetricMetadata

            assert isinstance(result, MetricMetadata)
            assert hasattr(result, 'description')
            assert hasattr(result, 'recommendedStatistics')
            assert hasattr(result, 'unit')

    async def test_get_metric_metadata_not_found(self, ctx, cloudwatch_metrics_tools):
        """Test getting metric metadata for non-existent metric."""
        result = await cloudwatch_metrics_tools.get_metric_metadata(
            ctx, namespace='NonExistent/Namespace', metric_name='NonExistentMetric'
        )

        # Should return None for non-existent metrics
        assert result is None

    async def test_get_recommended_metric_alarms_found(self, ctx, cloudwatch_metrics_tools):
        """Test getting alarm recommendations for metric with alarms."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Dimension

        result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
            ctx,
            namespace='AWS/EC2',
            metric_name='CPUUtilization',
            dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
        )

        # Should return an AlarmRecommendationResult
        assert hasattr(result, 'recommendations')
        assert hasattr(result, 'message')

        # If recommendations are found, verify structure
        if result.recommendations:
            from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import AlarmRecommendation

            for alarm in result.recommendations:
                assert isinstance(alarm, AlarmRecommendation)
                assert hasattr(alarm, 'alarmDescription')
                assert hasattr(alarm, 'threshold')
                assert hasattr(alarm, 'dimensions')

    async def test_get_recommended_metric_alarms_not_found(self, ctx, cloudwatch_metrics_tools):
        """Test getting alarm recommendations for metric without alarms."""
        result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
            ctx, namespace='NonExistent/Namespace', metric_name='NonExistentMetric', dimensions=[]
        )

        # Should return empty recommendations with message for non-existent metrics
        assert len(result.recommendations) == 0
        assert result.message is not None
        assert 'No alarm recommendations available' in result.message

    async def test_get_recommended_metric_alarms_dimension_matching(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test alarm recommendations with dimension matching."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Dimension

        # Test with ElastiCache metric that requires specific dimensions
        result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
            ctx,
            namespace='AWS/ElastiCache',
            metric_name='CPUUtilization',
            dimensions=[
                Dimension(name='CacheClusterId', value='test-cluster'),
                Dimension(name='CacheNodeId', value='0001'),
            ],
        )

        # Verify it returns an AlarmRecommendationResult
        assert hasattr(result, 'recommendations')
        assert hasattr(result, 'message')

        # Verify the expected ElastiCache CPUUtilization alarm recommendation is present
        if result.recommendations:
            # Find the matching alarm recommendation
            cpu_alarm = None
            for alarm in result.recommendations:
                if (
                    alarm.alarmDescription.startswith(
                        'This alarm helps to monitor the CPU utilization'
                    )
                    and alarm.statistic == 'Average'
                    and alarm.period == 60
                    and alarm.comparisonOperator == 'GreaterThanThreshold'
                    and alarm.evaluationPeriods == 5
                    and alarm.datapointsToAlarm == 5
                    and alarm.treatMissingData == 'missing'
                ):
                    cpu_alarm = alarm
                    break

            # Assert we found the alarm
            assert cpu_alarm is not None, 'Expected ElastiCache CPU alarm recommendation not found'

            # Verify alarm dimensions
            dim_names = [dim.name for dim in cpu_alarm.dimensions]
            assert 'CacheClusterId' in dim_names
            assert 'CacheNodeId' in dim_names
            assert len(cpu_alarm.dimensions) == 2

            # Verify alarm intent
            assert 'detect high CPU utilization of ElastiCache hosts' in cpu_alarm.intent

    async def test_get_recommended_metric_alarms_anomaly_detection_based_on_seasonality(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test that anomaly detection is selected when seasonality is detected."""
        with patch.object(cloudwatch_metrics_tools, '_lookup_metadata') as mock_lookup:
            mock_lookup.return_value = None  # No metadata found, force anomaly detection path

            with patch.object(cloudwatch_metrics_tools, 'analyze_metric') as mock_analyze:
                mock_analyze.return_value = {
                    'seasonality_seconds': 86400,  # ONE_DAY in seconds
                    'trend': {'trend_direction': 'stable'},
                    'statistics': {'mean': 50.0, 'std_deviation': 10.0},
                    'data_quality': {'quality_score': 0.9},
                }

                result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
                    ctx,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                )

                assert len(result.recommendations) == 1
                assert 'Anomaly detection' in result.recommendations[0].alarmDescription
                assert isinstance(
                    result.recommendations[0].threshold, AnomalyDetectionAlarmThreshold
                )

    async def test_get_recommended_metric_alarms_metadata_takes_precedence(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test that metadata recommendations take precedence over generated ones."""
        with patch.object(cloudwatch_metrics_tools, '_lookup_metadata') as mock_lookup:
            mock_lookup.return_value = {
                'alarmRecommendations': [
                    {
                        'alarmName': 'CPUUtilizationHigh',
                        'alarmDescription': 'CPU utilization is high',
                        'metricName': 'CPUUtilization',
                        'namespace': 'AWS/EC2',
                        'statistic': 'Average',
                        'threshold': {'type': 'static', 'value': 80.0},
                        'comparisonOperator': 'GreaterThanThreshold',
                        'evaluationPeriods': 2,
                        'period': 300,
                        'treatMissingData': 'breaching',
                        'dimensions': [{'name': 'InstanceId', 'value': 'i-1234567890abcdef0'}],
                    }
                ]
            }

            with patch.object(cloudwatch_metrics_tools, 'analyze_metric') as mock_analyze:
                mock_analyze.return_value = {
                    'seasonality_seconds': 86400,  # ONE_DAY in seconds - would normally trigger anomaly detection
                    'trend': {'trend_direction': 'stable'},
                    'statistics': {'mean': 50.0, 'std_deviation': 10.0},
                    'data_quality': {'quality_score': 0.9},
                }

                result = await cloudwatch_metrics_tools.get_recommended_metric_alarms(
                    ctx,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                )

                assert len(result.recommendations) == 1
                assert result.recommendations[0].alarmDescription == 'CPU utilization is high'
                assert isinstance(
                    result.recommendations[0].threshold, StaticAlarmThreshold
                )  # Metadata overrides seasonality-based generation

            # Verify alarm dimensions
            dim_names = [dim.name for dim in result.recommendations[0].dimensions]
            assert 'InstanceId' in dim_names
            assert len(result.recommendations[0].dimensions) == 1

    async def test_get_recommended_metric_alarms_runtime_error(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test RuntimeError handling in get_recommended_metric_alarms."""
        from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Dimension

        with patch.object(
            cloudwatch_metrics_tools,
            'analyze_metric',
            side_effect=RuntimeError('Test runtime error'),
        ):
            with pytest.raises(RuntimeError, match='Test runtime error'):
                await cloudwatch_metrics_tools.get_recommended_metric_alarms(
                    ctx,
                    namespace='NonExistent/Namespace',
                    metric_name='NonExistentMetric',
                    dimensions=[Dimension(name='TestDim', value='test-value')],
                )

    # Tests for get_metric_data with queries parameter (advanced queries support)

    async def test_get_metric_data_queries_single_metric(self, ctx, cloudwatch_metrics_tools):
        """Test basic single metric query using queries parameter."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'CPUUtilization',
                    'StatusCode': 'Complete',
                    'Timestamps': [
                        datetime(2026, 4, 5, 10, 0, 0),
                        datetime(2026, 4, 5, 10, 5, 0),
                    ],
                    'Values': [23.7, 31.2],
                }
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            queries = [
                MetricDataQueryInput(
                    id='m1',
                    period=120,
                    metric_stat=MetricStatInput(
                        namespace='AWS/EC2',
                        metric_name='CPUUtilization',
                        dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                        statistic='Average',
                    ),
                )
            ]

            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                start_time='2026-04-05T10:00:00Z',
                end_time='2026-04-05T11:00:00Z',
                queries=queries,
            )

            mock_client.get_metric_data.assert_called_once()
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].id == 'm1'
            assert result.metricDataResults[0].label == 'CPUUtilization'
            assert len(result.metricDataResults[0].datapoints) == 2
            assert result.metricDataResults[0].datapoints[0].value == 23.7
            assert result.metricDataResults[0].datapoints[1].value == 31.2

    async def test_get_metric_data_queries_multiple_metrics(self, ctx, cloudwatch_metrics_tools):
        """Test querying multiple metrics including percentiles in a single call using queries parameter."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'cpu',
                    'Label': 'CPUUtilization',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2026, 4, 5, 11, 30, 0)],
                    'Values': [42.8],
                },
                {
                    'Id': 'memory',
                    'Label': 'MemoryUtilization',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2026, 4, 5, 11, 30, 0)],
                    'Values': [67.5],
                },
                {
                    'Id': 'p50',
                    'Label': 'Duration p50',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2026, 4, 5, 11, 30, 0)],
                    'Values': [142.3],
                },
                {
                    'Id': 'p99',
                    'Label': 'Duration p99',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2026, 4, 5, 11, 30, 0)],
                    'Values': [1387.9],
                },
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            queries = [
                MetricDataQueryInput(
                    id='cpu',
                    metric_stat=MetricStatInput(
                        namespace='AWS/EC2',
                        metric_name='CPUUtilization',
                        dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                        statistic='Average',
                    ),
                ),
                MetricDataQueryInput(
                    id='memory',
                    metric_stat=MetricStatInput(
                        namespace='CWAgent',
                        metric_name='MemoryUtilization',
                        dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                        statistic='Average',
                    ),
                ),
                MetricDataQueryInput(
                    id='p50',
                    metric_stat=MetricStatInput(
                        namespace='AWS/Lambda',
                        metric_name='Duration',
                        dimensions=[Dimension(name='FunctionName', value='my-function')],
                        statistic='p50',
                    ),
                    label='Duration p50',
                ),
                MetricDataQueryInput(
                    id='p99',
                    metric_stat=MetricStatInput(
                        namespace='AWS/Lambda',
                        metric_name='Duration',
                        dimensions=[Dimension(name='FunctionName', value='my-function')],
                        statistic='p99',
                    ),
                    label='Duration p99',
                ),
            ]

            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                start_time='2026-04-05T11:00:00Z',
                end_time='2026-04-05T12:00:00Z',
                queries=queries,
            )

            # Verify all four metrics returned (including percentiles)
            assert len(result.metricDataResults) == 4
            assert result.metricDataResults[0].id == 'cpu'
            assert result.metricDataResults[0].datapoints[0].value == 42.8
            assert result.metricDataResults[1].id == 'memory'
            assert result.metricDataResults[1].datapoints[0].value == 67.5
            assert result.metricDataResults[2].id == 'p50'
            assert result.metricDataResults[2].label == 'Duration p50'
            assert result.metricDataResults[2].datapoints[0].value == 142.3
            assert result.metricDataResults[3].id == 'p99'
            assert result.metricDataResults[3].label == 'Duration p99'
            assert result.metricDataResults[3].datapoints[0].value == 1387.9

            # Verify the API call used percentile statistics
            call_args = mock_client.get_metric_data.call_args[1]
            queries_sent = call_args['MetricDataQueries']
            assert len(queries_sent) == 4
            assert queries_sent[2]['MetricStat']['Stat'] == 'p50'
            assert queries_sent[3]['MetricStat']['Stat'] == 'p99'

    async def test_get_metric_data_queries_math_expression(self, ctx, cloudwatch_metrics_tools):
        """Test using math expressions to calculate derived metrics (error rate)."""
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'error_rate',
                    'Label': 'Error Rate %',
                    'StatusCode': 'Complete',
                    'Timestamps': [
                        datetime(2026, 4, 5, 14, 30, 0),
                        datetime(2026, 4, 5, 14, 35, 0),
                        datetime(2026, 4, 5, 14, 40, 0),
                    ],
                    'Values': [1.8, 2.3, 4.1],
                },
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            queries = [
                MetricDataQueryInput(
                    id='errors',
                    metric_stat=MetricStatInput(
                        namespace='AWS/Lambda',
                        metric_name='Errors',
                        dimensions=[Dimension(name='FunctionName', value='my-function')],
                        statistic='Sum',
                    ),
                    return_data=False,
                ),
                MetricDataQueryInput(
                    id='invocations',
                    metric_stat=MetricStatInput(
                        namespace='AWS/Lambda',
                        metric_name='Invocations',
                        dimensions=[Dimension(name='FunctionName', value='my-function')],
                        statistic='Sum',
                    ),
                    return_data=False,
                ),
                MetricDataQueryInput(
                    id='error_rate',
                    expression='(errors / invocations) * 100',
                    label='Error Rate %',
                ),
            ]

            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                start_time='2026-04-05T14:00:00Z',
                end_time='2026-04-05T15:00:00Z',
                queries=queries,
            )

            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].id == 'error_rate'
            assert result.metricDataResults[0].label == 'Error Rate %'
            assert len(result.metricDataResults[0].datapoints) == 3
            assert result.metricDataResults[0].datapoints[0].value == 1.8

            # Verify the API call structure
            call_args = mock_client.get_metric_data.call_args[1]
            queries_sent = call_args['MetricDataQueries']
            assert len(queries_sent) == 3
            assert queries_sent[0]['Id'] == 'errors'
            assert queries_sent[0]['ReturnData'] is False
            assert queries_sent[2]['Id'] == 'error_rate'
            assert queries_sent[2]['Expression'] == '(errors / invocations) * 100'
            assert queries_sent[2]['ReturnData'] is True

    async def test_get_metric_data_queries_validation_no_metric_or_expression(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test validation error when neither metric_stat nor expression is provided."""
        with pytest.raises(ValueError) as excinfo:
            MetricDataQueryInput(id='test')

        assert 'Either metric_stat or expression must be provided' in str(excinfo.value)

    async def test_get_metric_data_queries_validation_both_metric_and_expression(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test validation error when both metric_stat and expression are provided."""
        with pytest.raises(ValueError) as excinfo:
            MetricDataQueryInput(
                id='test',
                metric_stat=MetricStatInput(
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    dimensions=[],
                    statistic='Average',
                ),
                expression='m1 * 100',
            )

        assert 'Cannot specify both metric_stat and expression' in str(excinfo.value)

    async def test_get_metric_data_queries_error_handling(self, ctx, cloudwatch_metrics_tools):
        """Test error handling when using queries parameter."""
        mock_client = MagicMock()
        mock_client.get_metric_data.side_effect = Exception('AWS API Error')
        ctx.error = AsyncMock()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            queries = [
                MetricDataQueryInput(
                    id='m1',
                    metric_stat=MetricStatInput(
                        namespace='AWS/EC2',
                        metric_name='CPUUtilization',
                        dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                        statistic='Average',
                    ),
                )
            ]

            with pytest.raises(Exception):
                await cloudwatch_metrics_tools.get_metric_data(
                    ctx,
                    start_time='2026-04-05T15:00:00Z',
                    end_time='2026-04-05T16:00:00Z',
                    queries=queries,
                )

            ctx.error.assert_called_once()
            assert 'AWS API Error' in ctx.error.call_args[0][0]

    async def test_get_metric_data_requires_namespace_without_queries(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test that namespace and metric_name are required when queries is not provided."""
        with pytest.raises(ValueError) as excinfo:
            await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                start_time='2026-04-05T15:00:00Z',
                end_time='2026-04-05T16:00:00Z',
            )

        assert 'namespace and metric_name are required' in str(excinfo.value)

    async def test_get_metric_data_queries_pagination(self, ctx, cloudwatch_metrics_tools):
        """Test that _execute_queries_batch paginates through NextToken responses.

        CloudWatch GetMetricData returns a NextToken when results exceed ~100,800
        datapoints or 500 queries. The batch-queries path is particularly exposed
        because it can request many metrics at once — without pagination handling,
        results would be silently truncated.

        This test also verifies:
        - The "new Id appears only on later page" branch: page 2 carries an extra
          result (``m2``) that wasn't on page 1, ensuring that the paginator
          appends unseen Ids rather than only merging known ones.
        - The ``start_time`` default: when omitted, it resolves to 3 hours before
          ``end_time`` (exercised by pinning ``end_time`` and asserting ``StartTime``
          on the AWS call).
        """
        mock_client = MagicMock()
        # Page 1: m1 with 2 datapoints + NextToken
        # Page 2: m1 with 2 more datapoints (merge case) + m2 as a NEW Id (append case)
        mock_client.get_metric_data.side_effect = [
            {
                'MetricDataResults': [
                    {
                        'Id': 'm1',
                        'Label': 'CPUUtilization',
                        'StatusCode': 'Complete',
                        'Timestamps': [
                            datetime(2026, 4, 5, 10, 0, 0),
                            datetime(2026, 4, 5, 10, 1, 0),
                        ],
                        'Values': [10.0, 20.0],
                    }
                ],
                'NextToken': 'page2-token',
            },
            {
                'MetricDataResults': [
                    {
                        'Id': 'm1',
                        'Label': 'CPUUtilization',
                        'StatusCode': 'Complete',
                        'Timestamps': [
                            datetime(2026, 4, 5, 10, 2, 0),
                            datetime(2026, 4, 5, 10, 3, 0),
                        ],
                        'Values': [30.0, 40.0],
                    },
                    {
                        'Id': 'm2',
                        'Label': 'MemoryUtilization',
                        'StatusCode': 'Complete',
                        'Timestamps': [datetime(2026, 4, 5, 10, 3, 0)],
                        'Values': [55.5],
                    },
                ],
                # no NextToken — pagination complete
            },
        ]

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            queries = [
                MetricDataQueryInput(
                    id='m1',
                    metric_stat=MetricStatInput(
                        namespace='AWS/EC2',
                        metric_name='CPUUtilization',
                        dimensions=[Dimension(name='InstanceId', value='i-1234567890abcdef0')],
                        statistic='Average',
                    ),
                )
            ]

            result = await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                # start_time intentionally omitted — should default to 3h before end_time
                end_time=datetime(2026, 4, 5, 11, 0, 0, tzinfo=timezone.utc),
                queries=queries,
            )

            # Called exactly twice — once per page
            assert mock_client.get_metric_data.call_count == 2

            # start_time defaulted to 3 hours before end_time
            pinned_end = datetime(2026, 4, 5, 11, 0, 0, tzinfo=timezone.utc)
            first_call_kwargs = mock_client.get_metric_data.call_args_list[0].kwargs
            assert first_call_kwargs['EndTime'] == pinned_end
            assert first_call_kwargs['StartTime'] == pinned_end - timedelta(hours=3)

            # Second call must have carried the NextToken forward
            second_call_kwargs = mock_client.get_metric_data.call_args_list[1].kwargs
            assert second_call_kwargs.get('NextToken') == 'page2-token'

            # Merged result: two distinct results
            assert isinstance(result, GetMetricDataResponse)
            assert len(result.metricDataResults) == 2

            # m1 — merged (4 datapoints from both pages)
            m1 = next(r for r in result.metricDataResults if r.id == 'm1')
            assert len(m1.datapoints) == 4
            assert [dp.value for dp in m1.datapoints] == [10.0, 20.0, 30.0, 40.0]

            # m2 — appended (only appeared on page 2)
            m2 = next(r for r in result.metricDataResults if r.id == 'm2')
            assert len(m2.datapoints) == 1
            assert m2.datapoints[0].value == 55.5

    async def test_get_metric_data_queries_metric_stat_period_fallback(
        self, ctx, cloudwatch_metrics_tools
    ):
        """Test period precedence: when query.period is unset, metric_stat.period wins over default.

        Covers the ``elif query.metric_stat and query.metric_stat.period is not None`` branch
        of ``_convert_query_input_to_aws``.
        """
        mock_client = MagicMock()
        mock_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'CPUUtilization',
                    'StatusCode': 'Complete',
                    'Timestamps': [datetime(2026, 4, 5, 10, 0, 0)],
                    'Values': [50.0],
                }
            ],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.get_aws_client',
            return_value=mock_client,
        ):
            queries = [
                MetricDataQueryInput(
                    id='m1',
                    # No period here — forcing fallback to metric_stat.period
                    metric_stat=MetricStatInput(
                        namespace='AWS/EC2',
                        metric_name='CPUUtilization',
                        dimensions=[Dimension(name='InstanceId', value='i-abc')],
                        statistic='Average',
                        period=300,  # 5-minute period — should end up in the AWS call
                    ),
                )
            ]

            await cloudwatch_metrics_tools.get_metric_data(
                ctx,
                start_time='2026-04-05T10:00:00Z',
                end_time='2026-04-05T11:00:00Z',
                queries=queries,
            )

            # The AWS MetricStat must carry Period=300 (from metric_stat), not the default
            aws_query = mock_client.get_metric_data.call_args.kwargs['MetricDataQueries'][0]
            assert aws_query['MetricStat']['Period'] == 300
