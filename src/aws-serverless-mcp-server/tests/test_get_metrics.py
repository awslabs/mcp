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
"""Tests for the get_metrics module."""

import datetime
import pytest
from awslabs.aws_serverless_mcp_server.tools.webapps.get_metrics import (
    GetMetricsTool,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetMetrics:
    """Tests for the get_metrics function."""

    def test_get_unit_for_metric(self):
        """Test the get_unit_for_metric helper function."""
        assert GetMetricsTool.get_unit_for_metric('Lambda Duration') == 'Milliseconds'
        assert GetMetricsTool.get_unit_for_metric('API Gateway Latency') == 'Milliseconds'
        assert GetMetricsTool.get_unit_for_metric('CloudFront Bytes Downloaded') == 'Bytes'
        assert GetMetricsTool.get_unit_for_metric('CloudFront Error Rate') == 'Percent'
        assert GetMetricsTool.get_unit_for_metric('Lambda Invocations') == 'Count'

    @pytest.mark.asyncio
    async def test_get_metrics_success(self):
        """Test successful metrics retrieval."""
        # Mock the boto3 session and CloudWatch client
        mock_session = MagicMock()
        mock_cloudwatch = MagicMock()
        mock_session.client.return_value = mock_cloudwatch

        # Mock the CloudWatch get_metric_data response
        mock_cloudwatch.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'q0',
                    'Label': 'Lambda Invocations',
                    'Timestamps': [
                        datetime.datetime(2023, 5, 21, 12, 0, 0),
                        datetime.datetime(2023, 5, 21, 12, 5, 0),
                    ],
                    'Values': [10, 15],
                },
                {
                    'Id': 'q1',
                    'Label': 'Lambda Duration (Average)',
                    'Timestamps': [
                        datetime.datetime(2023, 5, 21, 12, 0, 0),
                        datetime.datetime(2023, 5, 21, 12, 5, 0),
                    ],
                    'Values': [120.5, 130.2],
                },
            ]
        }

        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            result = await GetMetricsTool(MagicMock()).get_metrics(
                AsyncMock(),
                project_name='test-project',
                start_time=None,
                end_time=None,
                period=60,
                resources=['lambda', 'apiGateway'],
                region=None,
                stage='prod',
            )

            # Verify the result
            assert result['success'] is True
            print(result)
            assert 'metrics' in result
            assert 'lambda' in result['metrics']
            assert 'invocations' in result['metrics']['lambda']
            assert 'duration (average)' in result['metrics']['lambda']

            # Check the data points
            invocations = result['metrics']['lambda']['invocations']
            assert len(invocations) == 2
            assert invocations[0]['value'] == 10
            assert invocations[0]['unit'] == 'Count'

            duration = result['metrics']['lambda']['duration (average)']
            assert len(duration) == 2
            assert duration[0]['value'] == 120.5
            assert duration[0]['unit'] == 'Milliseconds'

            # Verify boto3 session was created with the correct parameters
            mock_session.client.assert_called_once_with('cloudwatch')

            # Verify get_metric_data was called with the correct parameters
            mock_cloudwatch.get_metric_data.assert_called_once()
            _, kwargs = mock_cloudwatch.get_metric_data.call_args
            assert 'StartTime' in kwargs
            assert 'EndTime' in kwargs
            assert 'MetricDataQueries' in kwargs
            assert 'ScanBy' in kwargs
            assert kwargs['ScanBy'] == 'TimestampAscending'

    @pytest.mark.asyncio
    async def test_get_metrics_with_optional_params(self):
        """Test metrics retrieval with optional parameters."""
        # Mock the boto3 session and CloudWatch client
        mock_session = MagicMock()
        mock_cloudwatch = MagicMock()
        mock_session.client.return_value = mock_cloudwatch

        # Mock the CloudWatch get_metric_data response
        mock_cloudwatch.get_metric_data.return_value = {'MetricDataResults': []}

        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            result = await GetMetricsTool(MagicMock()).get_metrics(
                AsyncMock(),
                project_name='test-project',
                start_time='2023-05-20T00:00:00Z',
                end_time='2023-05-21T23:59:59Z',
                period=60,
                resources=['lambda', 'apiGateway'],
                region='us-west-2',
                stage='prod',
            )

            # Verify the result
            assert result['success'] is True

            # Verify boto3 session was created with the correct parameters
            mock_session.client.assert_called_once_with('cloudwatch')

            # Verify get_metric_data was called with the correct parameters
            mock_cloudwatch.get_metric_data.assert_called_once()
            _, kwargs = mock_cloudwatch.get_metric_data.call_args

            # Check that start_time and end_time were parsed correctly
            assert 'StartTime' in kwargs
            assert isinstance(kwargs['StartTime'], datetime.datetime)
            assert kwargs['StartTime'].year == 2023
            assert kwargs['StartTime'].month == 5
            assert kwargs['StartTime'].day == 20

            assert 'EndTime' in kwargs
            assert isinstance(kwargs['EndTime'], datetime.datetime)
            assert kwargs['EndTime'].year == 2023
            assert kwargs['EndTime'].month == 5
            assert kwargs['EndTime'].day == 21

    @pytest.mark.asyncio
    async def test_get_metrics_no_valid_metrics(self):
        """Test metrics retrieval with no valid metrics."""
        # Mock the boto3 session
        mock_session = MagicMock()

        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            result = await GetMetricsTool(MagicMock()).get_metrics(
                AsyncMock(),
                project_name='test-project',
                start_time=None,
                end_time=None,
                period=60,
                resources=[],  # Empty resources list
                region=None,
                stage='prod',
            )

            # Verify the result
            assert result['success'] is False
            assert 'No valid metrics found' in result['message']

    @pytest.mark.asyncio
    async def test_get_metrics_boto3_exception(self):
        """Test metrics retrieval with boto3 exception."""
        # Mock the boto3 session and CloudWatch client
        mock_session = MagicMock()
        mock_cloudwatch = MagicMock()
        mock_session.client.return_value = mock_cloudwatch

        # Mock the CloudWatch get_metric_data to raise an exception
        error_message = 'An error occurred (AccessDenied) when calling the GetMetricData operation'
        mock_cloudwatch.get_metric_data.side_effect = Exception(error_message)

        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            result = await GetMetricsTool(MagicMock()).get_metrics(
                AsyncMock(),
                project_name='test-project',
                start_time=None,
                end_time=None,
                period=60,
                resources=['lambda', 'apiGateway'],
                region=None,
                stage='prod',
            )

            # Verify the result
            assert result['success'] is False
            assert 'Failed to retrieve metrics' in result['message']
            assert error_message in result['error']

    @pytest.mark.asyncio
    async def test_get_metrics_invalid_time_format(self):
        """Test metrics retrieval with invalid time format."""
        # Mock the boto3 session and CloudWatch client
        mock_session = MagicMock()
        mock_cloudwatch = MagicMock()
        mock_session.client.return_value = mock_cloudwatch

        # Mock the CloudWatch get_metric_data response
        mock_cloudwatch.get_metric_data.return_value = {'MetricDataResults': []}

        with patch('boto3.Session', return_value=mock_session):
            # Call the function
            result = await GetMetricsTool(MagicMock()).get_metrics(
                AsyncMock(),
                project_name='test-project',
                start_time='invalid-start-time',
                end_time='invalid-end-time',
                period=60,
                resources=['lambda', 'apiGateway'],
                region=None,
                stage='prod',
            )

            # Verify the result
            assert result['success'] is True
