"""Tests for analyze_metric tool."""

import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import (
    DEFAULT_ANALYSIS_PERIOD_MINUTES,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    Dimension,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch


class TestAnalyzeMetric:
    """Test cases for analyze_metric tool."""

    @pytest.fixture
    def cloudwatch_metrics_tools(self):
        """Create CloudWatchMetricsTools instance."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            return CloudWatchMetricsTools()

    @pytest.fixture
    def ctx(self):
        """Create mock context."""
        ctx = AsyncMock()
        ctx.error = AsyncMock()
        return ctx

    @pytest.mark.asyncio
    async def test_analyze_metric_no_data(self, ctx, cloudwatch_metrics_tools):
        """Test analyze_metric with no data returned."""
        with patch.object(cloudwatch_metrics_tools, '_get_cloudwatch_client') as mock_client:
            mock_cloudwatch = Mock()
            mock_client.return_value = mock_cloudwatch
            mock_cloudwatch.get_metric_data.return_value = {
                'MetricDataResults': [{'Values': [], 'Timestamps': []}]
            }

            result = await cloudwatch_metrics_tools.analyze_metric(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                dimensions=[Dimension(name='InstanceId', value='i-test123')],
            )

            assert result['message'] == 'No metric data available for analysis'

    @pytest.mark.asyncio
    async def test_analyze_metric_with_data(self, ctx, cloudwatch_metrics_tools):
        """Test analyze_metric with valid data."""
        from datetime import datetime

        with patch.object(cloudwatch_metrics_tools, '_get_cloudwatch_client') as mock_client:
            mock_cloudwatch = Mock()
            mock_client.return_value = mock_cloudwatch

            # Mock response with data
            mock_timestamps = [datetime(2023, 1, 1, i) for i in range(5)]
            mock_values = [10.0 + i for i in range(5)]

            mock_cloudwatch.get_metric_data.return_value = {
                'MetricDataResults': [{'Values': mock_values, 'Timestamps': mock_timestamps}]
            }

            result = await cloudwatch_metrics_tools.analyze_metric(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                dimensions=[Dimension(name='InstanceId', value='i-test123')],
            )

            assert result['data_points_found'] == 5
            assert 'seasonality_seconds' in result
            assert 'trend' in result
            assert 'data_quality' in result
            assert 'density_ratio' in result['data_quality']
            assert 'statistics' in result
            assert 'data_quality' in result

    @pytest.mark.asyncio
    async def test_analyze_metric_aws_error(self, ctx, cloudwatch_metrics_tools):
        """Test analyze_metric with AWS API error."""
        with patch.object(cloudwatch_metrics_tools, '_get_cloudwatch_client') as mock_client:
            mock_cloudwatch = Mock()
            mock_client.return_value = mock_cloudwatch
            mock_cloudwatch.get_metric_data.side_effect = Exception('AWS API Error')

            with pytest.raises(Exception, match='AWS API Error'):
                await cloudwatch_metrics_tools.analyze_metric(
                    ctx, namespace='AWS/EC2', metric_name='CPUUtilization', dimensions=[]
                )

            assert ctx.error.call_count >= 1

    @pytest.mark.asyncio
    async def test_analyze_metric_custom_period(self, ctx, cloudwatch_metrics_tools):
        """Test analyze_metric with default analysis period."""
        with patch.object(cloudwatch_metrics_tools, '_get_cloudwatch_client') as mock_client:
            mock_cloudwatch = Mock()
            mock_client.return_value = mock_cloudwatch
            mock_cloudwatch.get_metric_data.return_value = {
                'MetricDataResults': [{'Values': [], 'Timestamps': []}]
            }

            result = await cloudwatch_metrics_tools.analyze_metric(
                ctx,
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                dimensions=[],
            )

            assert (
                result['metric_info']['analysis_period_minutes'] == DEFAULT_ANALYSIS_PERIOD_MINUTES
            )

    @pytest.mark.asyncio
    async def test_analyze_metric_empty_response(self, ctx, cloudwatch_metrics_tools):
        """Test analyze_metric with empty CloudWatch response."""
        with patch.object(cloudwatch_metrics_tools, '_get_cloudwatch_client') as mock_client:
            mock_cloudwatch = Mock()
            mock_client.return_value = mock_cloudwatch
            mock_cloudwatch.get_metric_data.return_value = {'MetricDataResults': []}

            result = await cloudwatch_metrics_tools.analyze_metric(
                ctx, namespace='AWS/EC2', metric_name='CPUUtilization', dimensions=[]
            )

            assert result['message'] == 'No metric data available for analysis'

    @pytest.mark.asyncio
    async def test_analyze_metric_mismatched_timestamps_values(
        self, cloudwatch_metrics_tools, ctx
    ):
        """Test analyze_metric with mismatched timestamps and values lengths."""
        with patch.object(cloudwatch_metrics_tools, '_get_cloudwatch_client') as mock_client:
            mock_cloudwatch = Mock()
            mock_client.return_value = mock_cloudwatch

            # Mock mismatched lengths - CloudWatch should handle this gracefully
            mock_cloudwatch.get_metric_data.return_value = {
                'MetricDataResults': [
                    {
                        'Id': 'm1',
                        'Label': 'CPUUtilization',
                        'Timestamps': [
                            datetime(2023, 1, 1, 12, 0),
                            datetime(2023, 1, 1, 12, 5),
                        ],  # 2 timestamps
                        'Values': [50.0, 60.0, 70.0],  # 3 values - mismatch!
                        'StatusCode': 'Complete',
                    }
                ]
            }

            result = await cloudwatch_metrics_tools.analyze_metric(
                ctx, namespace='AWS/EC2', metric_name='CPUUtilization', dimensions=[]
            )

            # Should handle gracefully - takes min(timestamps, values) = 2
            assert result['data_points_found'] == 2

    @pytest.mark.asyncio
    async def test_analyze_metric_with_nan_values(self, cloudwatch_metrics_tools, ctx):
        """Test analyze_metric with NaN values in metric data."""
        with patch.object(cloudwatch_metrics_tools, '_get_cloudwatch_client') as mock_client:
            mock_cloudwatch = Mock()
            mock_client.return_value = mock_cloudwatch

            mock_cloudwatch.get_metric_data.return_value = {
                'MetricDataResults': [
                    {
                        'Id': 'm1',
                        'Label': 'CPUUtilization',
                        'Timestamps': [datetime(2023, 1, 1, 12, 0), datetime(2023, 1, 1, 12, 5)],
                        'Values': [50.0, float('nan')],
                        'StatusCode': 'Complete',
                    }
                ]
            }

            result = await cloudwatch_metrics_tools.analyze_metric(
                ctx, namespace='AWS/EC2', metric_name='CPUUtilization', dimensions=[]
            )

            # Only 1 valid value after filtering NaN - insufficient for analysis
            assert result['message'] == 'Insufficient valid data points for analysis'
            assert 'metric_info' in result

    @pytest.mark.asyncio
    async def test_analyze_metric_get_metric_data_returns_empty(
        self, cloudwatch_metrics_tools, ctx
    ):
        """Test analyze_metric when get_metric_data returns empty results."""
        with patch.object(cloudwatch_metrics_tools, '_get_cloudwatch_client') as mock_client:
            mock_cloudwatch = Mock()
            mock_client.return_value = mock_cloudwatch

            mock_cloudwatch.get_metric_data.return_value = {'MetricDataResults': []}

            result = await cloudwatch_metrics_tools.analyze_metric(
                ctx, namespace='AWS/EC2', metric_name='CPUUtilization', dimensions=[]
            )

            # Should handle empty results gracefully
            assert result['message'] == 'No metric data available for analysis'
