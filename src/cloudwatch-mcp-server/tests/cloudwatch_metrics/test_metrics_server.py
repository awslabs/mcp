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
    StaticAlarmThreshold,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from datetime import datetime
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
    with patch(
        'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'
    ) as mock_session:
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
            assert call_args['StartTime'] == start_time
            assert call_args['EndTime'] == end_time
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
        with patch.object(
            cloudwatch_metrics_tools, '_get_cloudwatch_client', return_value=mock_client
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
