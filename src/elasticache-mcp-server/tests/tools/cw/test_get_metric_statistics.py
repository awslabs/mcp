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

"""Tests for get-metric-statistics tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cw.get_metric_statistics import get_metric_statistics
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_get_metric_statistics_basic():
    """Test basic get metric statistics functionality."""
    mock_client = MagicMock()

    # Mock response
    mock_response = {
        'Label': 'EngineCPUUtilization',
        'Datapoints': [{'Timestamp': '2025-06-07T11:04:00Z', 'Average': 45.6, 'Unit': 'Percent'}],
    }
    mock_client.get_metric_statistics.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call function
        result = await get_metric_statistics(
            metric_name='EngineCPUUtilization',
            start_time='2025-06-07T11:04:00Z',
            end_time='2025-06-07T12:04:00Z',
            period=3600,
            dimensions=[{'CacheClusterId': 'test-0001-001', 'CacheNodeId': '0001'}],
            statistics=['Average'],
        )

        # Verify client call
        mock_client.get_metric_statistics.assert_called_once()
        call_args = mock_client.get_metric_statistics.call_args[1]
        assert call_args['Namespace'] == 'AWS/ElastiCache'
        assert call_args['MetricName'] == 'EngineCPUUtilization'
        assert call_args['Period'] == 3600
        assert call_args['Statistics'] == ['Average']
        assert len(call_args['Dimensions']) == 2

        # Verify response
        assert result == {
            'Label': 'EngineCPUUtilization',
            'Datapoints': mock_response['Datapoints'],
        }


@pytest.mark.asyncio
async def test_get_metric_statistics_minimal_params():
    """Test get metric statistics with minimal parameters."""
    mock_client = MagicMock()
    # Mock response
    mock_response = {'Label': 'TestMetric', 'Datapoints': []}
    mock_client.get_metric_statistics.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call function
        result = await get_metric_statistics(
            metric_name='TestMetric',
            start_time='2025-06-07T11:04:00Z',
            end_time='2025-06-07T12:04:00Z',
            period=3600,
        )

        # Verify client call
        mock_client.get_metric_statistics.assert_called_once()
        call_args = mock_client.get_metric_statistics.call_args[1]
        assert call_args['Namespace'] == 'AWS/ElastiCache'
        assert call_args['MetricName'] == 'TestMetric'
        assert call_args['Period'] == 3600
        assert 'Statistics' not in call_args
        assert 'Dimensions' not in call_args

        # Verify response
        assert result == {'Label': 'TestMetric', 'Datapoints': []}


@pytest.mark.asyncio
async def test_get_metric_statistics_with_extended_stats():
    """Test get metric statistics with extended statistics."""
    mock_client = MagicMock()
    # Mock response
    mock_response = {
        'Label': 'TestMetric',
        'Datapoints': [{'ExtendedStatistics': {'p95': 123.45}}],
    }
    mock_client.get_metric_statistics.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call function
        result = await get_metric_statistics(
            metric_name='TestMetric',
            start_time='2025-06-07T11:04:00Z',
            end_time='2025-06-07T12:04:00Z',
            period=3600,
            extended_statistics=['p95'],
        )

        # Verify client call
        mock_client.get_metric_statistics.assert_called_once()
        call_args = mock_client.get_metric_statistics.call_args[1]
        assert call_args['ExtendedStatistics'] == ['p95']

        # Verify response
        assert result == {'Label': 'TestMetric', 'Datapoints': mock_response['Datapoints']}


@pytest.mark.asyncio
async def test_get_metric_statistics_error():
    """Test get metric statistics error handling."""
    mock_client = MagicMock()
    # Mock error response
    mock_client.get_metric_statistics.side_effect = Exception('Test error')

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call function
        result = await get_metric_statistics(
            metric_name='TestMetric',
            start_time='2025-06-07T11:04:00Z',
            end_time='2025-06-07T12:04:00Z',
            period=3600,
        )

        # Verify client call
        mock_client.get_metric_statistics.assert_called_once()

        # Verify error response
        assert result == {'error': 'Test error'}
