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
"""Tests for the PromQL tools."""

import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.promql_models import (
    PromQLInstantResult,
    PromQLLabelsResult,
    PromQLLabelValuesResult,
    PromQLRangeResult,
    PromQLSeriesResult,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from unittest.mock import AsyncMock, patch


@pytest_asyncio.fixture
async def ctx():
    """Fixture to provide mock context."""
    return AsyncMock()


@pytest_asyncio.fixture
async def tools():
    """Create CloudWatchMetricsTools instance."""
    return CloudWatchMetricsTools()


@pytest.mark.asyncio
class TestExecutePromQLQuery:
    """Tests for execute_promql_query tool."""

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_instant_query(self, mock_request, ctx, tools):
        """Test basic instant query."""
        mock_request.return_value = {
            'resultType': 'vector',
            'result': [
                {'metric': {'__name__': 'up'}, 'value': [1680307200, '1']},
            ],
        }

        result = await tools.execute_promql_query(ctx, query='up', region='us-east-1')

        assert isinstance(result, PromQLInstantResult)
        assert result.resultType == 'vector'
        assert len(result.result) == 1
        mock_request.assert_called_once_with(
            endpoint='query',
            params={'query': 'up'},
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_instant_query_with_time(self, mock_request, ctx, tools):
        """Test instant query with explicit time."""
        mock_request.return_value = {'resultType': 'vector', 'result': []}

        await tools.execute_promql_query(
            ctx, query='up', time='2024-01-01T00:00:00Z', region='us-east-1'
        )

        mock_request.assert_called_once_with(
            endpoint='query',
            params={'query': 'up', 'time': '2024-01-01T00:00:00Z'},
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_instant_query_error(self, mock_request, ctx, tools):
        """Test instant query propagates errors."""
        mock_request.side_effect = RuntimeError('PromQL API error: bad syntax')

        with pytest.raises(RuntimeError, match='bad syntax'):
            await tools.execute_promql_query(ctx, query='invalid{')


@pytest.mark.asyncio
class TestExecutePromQLRangeQuery:
    """Tests for execute_promql_range_query tool."""

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_range_query(self, mock_request, ctx, tools):
        """Test basic range query."""
        mock_request.return_value = {
            'resultType': 'matrix',
            'result': [
                {
                    'metric': {'__name__': 'up'},
                    'values': [[1680307200, '1'], [1680307260, '1']],
                },
            ],
        }

        result = await tools.execute_promql_range_query(
            ctx,
            query='up',
            start='2024-01-01T00:00:00Z',
            end='2024-01-01T01:00:00Z',
            step='60s',
            region='us-east-1',
        )

        assert isinstance(result, PromQLRangeResult)
        assert result.resultType == 'matrix'
        assert len(result.result) == 1
        mock_request.assert_called_once_with(
            endpoint='query_range',
            params={
                'query': 'up',
                'start': '2024-01-01T00:00:00Z',
                'end': '2024-01-01T01:00:00Z',
                'step': '60s',
            },
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_range_query_error(self, mock_request, ctx, tools):
        """Test range query propagates errors."""
        mock_request.side_effect = RuntimeError('PromQL API error: timeout')

        with pytest.raises(RuntimeError, match='timeout'):
            await tools.execute_promql_range_query(
                ctx,
                query='up',
                start='2024-01-01T00:00:00Z',
                end='2024-01-01T01:00:00Z',
                step='60s',
            )


@pytest.mark.asyncio
class TestGetPromQLLabelValues:
    """Tests for get_promql_label_values tool."""

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_label_values(self, mock_request, ctx, tools):
        """Test getting label values."""
        mock_request.return_value = ['metric_a', 'metric_b', 'metric_c']

        result = await tools.get_promql_label_values(
            ctx, label_name='__name__', region='us-east-1'
        )

        assert isinstance(result, PromQLLabelValuesResult)
        assert result.values == ['metric_a', 'metric_b', 'metric_c']
        mock_request.assert_called_once_with(
            endpoint='label/__name__/values',
            params={},
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_label_values_with_match(self, mock_request, ctx, tools):
        """Test getting label values with match filter."""
        mock_request.return_value = ['myservice']

        result = await tools.get_promql_label_values(
            ctx,
            label_name='@resource.service.name',
            match=['{"@instrumentation.@name"="cloudwatch.aws/ec2"}'],
            region='us-east-1',
        )

        assert result.values == ['myservice']
        mock_request.assert_called_once_with(
            endpoint='label/@resource.service.name/values',
            params={'match[]': '{"@instrumentation.@name"="cloudwatch.aws/ec2"}'},
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_label_values_with_time_range(self, mock_request, ctx, tools):
        """Test getting label values with start/end time."""
        mock_request.return_value = ['val1', 'val2']

        result = await tools.get_promql_label_values(
            ctx,
            label_name='__name__',
            start='2024-01-01T00:00:00Z',
            end='2024-01-02T00:00:00Z',
            region='us-east-1',
        )

        assert result.values == ['val1', 'val2']
        mock_request.assert_called_once_with(
            endpoint='label/__name__/values',
            params={'start': '2024-01-01T00:00:00Z', 'end': '2024-01-02T00:00:00Z'},
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_label_values_error(self, mock_request, ctx, tools):
        """Test label values propagates errors."""
        mock_request.side_effect = RuntimeError('PromQL API error: timeout')

        with pytest.raises(RuntimeError, match='timeout'):
            await tools.get_promql_label_values(ctx, label_name='__name__', region='us-east-1')


@pytest.mark.asyncio
class TestGetPromQLSeries:
    """Tests for get_promql_series tool."""

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_series(self, mock_request, ctx, tools):
        """Test getting series."""
        mock_request.return_value = [
            {'__name__': 'CPUUtilization', 'InstanceId': 'i-123'},
        ]

        result = await tools.get_promql_series(
            ctx,
            match=['{CPUUtilization, "@instrumentation.@name"="cloudwatch.aws/ec2"}'],
            region='us-east-1',
        )

        assert isinstance(result, PromQLSeriesResult)
        assert len(result.series) == 1
        assert result.series[0]['__name__'] == 'CPUUtilization'

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_series_with_time_range(self, mock_request, ctx, tools):
        """Test getting series with time range."""
        mock_request.return_value = []

        await tools.get_promql_series(
            ctx,
            match=['{up}'],
            start='2024-01-01T00:00:00Z',
            end='2024-01-02T00:00:00Z',
            region='us-east-1',
        )

        mock_request.assert_called_once_with(
            endpoint='series',
            params={
                'match[]': '{up}',
                'start': '2024-01-01T00:00:00Z',
                'end': '2024-01-02T00:00:00Z',
            },
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_series_error(self, mock_request, ctx, tools):
        """Test series propagates errors."""
        mock_request.side_effect = RuntimeError('PromQL API error: timeout')

        with pytest.raises(RuntimeError, match='timeout'):
            await tools.get_promql_series(ctx, match=['{up}'], region='us-east-1')


@pytest.mark.asyncio
class TestGetPromQLLabels:
    """Tests for get_promql_labels tool."""

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_labels(self, mock_request, ctx, tools):
        """Test getting all labels."""
        mock_request.return_value = ['__name__', '@resource.service.name', 'InstanceId']

        result = await tools.get_promql_labels(ctx, region='us-east-1')

        assert isinstance(result, PromQLLabelsResult)
        assert result.labels == ['@resource.service.name', 'InstanceId', '__name__']
        mock_request.assert_called_once_with(
            endpoint='labels',
            params={},
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_labels_with_match(self, mock_request, ctx, tools):
        """Test getting labels with match filter."""
        mock_request.return_value = ['__name__', 'FunctionName']

        result = await tools.get_promql_labels(
            ctx,
            match=['{"@instrumentation.@name"="cloudwatch.aws/lambda"}'],
            region='us-east-1',
        )

        assert result.labels == ['FunctionName', '__name__']
        mock_request.assert_called_once_with(
            endpoint='labels',
            params={'match[]': '{"@instrumentation.@name"="cloudwatch.aws/lambda"}'},
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_labels_with_time_range(self, mock_request, ctx, tools):
        """Test getting labels with start/end time."""
        mock_request.return_value = ['__name__']

        result = await tools.get_promql_labels(
            ctx,
            start='2024-01-01T00:00:00Z',
            end='2024-01-02T00:00:00Z',
            region='us-east-1',
        )

        assert result.labels == ['__name__']
        mock_request.assert_called_once_with(
            endpoint='labels',
            params={'start': '2024-01-01T00:00:00Z', 'end': '2024-01-02T00:00:00Z'},
            region='us-east-1',
            profile_name=None,
        )

    @patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.PromQLClient.make_request')
    async def test_labels_error(self, mock_request, ctx, tools):
        """Test labels propagates errors."""
        mock_request.side_effect = ValueError('AWS credentials not found')

        with pytest.raises(ValueError, match='AWS credentials not found'):
            await tools.get_promql_labels(ctx, region='us-east-1')
