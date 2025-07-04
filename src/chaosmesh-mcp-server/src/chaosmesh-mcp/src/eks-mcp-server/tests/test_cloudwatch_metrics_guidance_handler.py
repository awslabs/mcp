# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the CloudWatch metrics guidance handler."""

import json
import pytest
from awslabs.eks_mcp_server.cloudwatch_metrics_guidance_handler import CloudWatchMetricsHandler
from awslabs.eks_mcp_server.models import MetricsGuidanceResponse
from mcp.types import TextContent
from unittest.mock import MagicMock, mock_open, patch


@pytest.fixture
def mock_metrics_guidance():
    """Create a mock metrics guidance dictionary."""
    return {
        'cluster': {
            'metrics': [
                {
                    'name': 'cluster_failed_node_count',
                    'dimensions': ['ClusterName'],
                    'description': 'Number of failed worker nodes in cluster with node conditions',
                }
            ]
        },
        'node': {
            'metrics': [
                {
                    'name': 'node_cpu_limit',
                    'dimensions': ['ClusterName'],
                    'description': 'Maximum CPU units assignable to a single node',
                }
            ]
        },
    }


@pytest.fixture
def metrics_handler(mock_metrics_guidance):
    """Create a CloudWatch metrics guidance handler with a mock MCP server."""
    mock_mcp = MagicMock()
    with patch('builtins.open', mock_open(read_data=json.dumps({}))):
        handler = CloudWatchMetricsHandler(mock_mcp)
        handler.metrics_guidance = mock_metrics_guidance

        # Verify tool registration
        assert mock_mcp.tool.call_count == 1
        mock_mcp.tool.assert_called_once_with(name='get_eks_metrics_guidance')

        return handler


@pytest.mark.asyncio
async def test_get_eks_metrics_guidance_cluster(metrics_handler):
    """Test getting cluster metrics guidance."""
    mock_ctx = MagicMock()
    result = await metrics_handler.get_eks_metrics_guidance(mock_ctx, 'cluster')
    assert isinstance(result, MetricsGuidanceResponse)
    assert result.isError is False
    assert len(result.metrics) == 1
    assert result.resource_type == 'cluster'
    assert result.metrics[0]['name'] == 'cluster_failed_node_count'
    assert result.metrics[0]['dimensions'] == ['ClusterName']


@pytest.mark.asyncio
async def test_get_eks_metrics_guidance_node(metrics_handler):
    """Test getting node metrics guidance."""
    mock_ctx = MagicMock()
    result = await metrics_handler.get_eks_metrics_guidance(mock_ctx, 'node')
    assert isinstance(result, MetricsGuidanceResponse)
    assert result.isError is False
    assert len(result.metrics) == 1
    assert result.resource_type == 'node'
    assert result.metrics[0]['name'] == 'node_cpu_limit'
    assert result.metrics[0]['dimensions'] == ['ClusterName']


@pytest.mark.asyncio
async def test_get_eks_metrics_guidance_nonexistent(metrics_handler):
    """Test getting metrics guidance for a resource type that doesn't exist in the data."""
    mock_ctx = MagicMock()
    # Pod metrics aren't in our mock data, so this should return an empty list
    result = await metrics_handler.get_eks_metrics_guidance(mock_ctx, 'pod')
    assert isinstance(result, MetricsGuidanceResponse)
    assert result.isError is False
    assert result.resource_type == 'pod'
    assert result.metrics == []


@pytest.mark.asyncio
async def test_get_eks_metrics_guidance_invalid_type(metrics_handler):
    """Test getting metrics guidance for an invalid resource type."""
    mock_ctx = MagicMock()
    # Invalid resource type should return an error response
    result = await metrics_handler.get_eks_metrics_guidance(mock_ctx, 'invalid_type')
    assert isinstance(result, MetricsGuidanceResponse)
    assert result.isError is True
    assert result.resource_type == 'invalid_type'
    assert result.metrics == []
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert 'Invalid resource type' in result.content[0].text


def test_load_metrics_guidance():
    """Test loading metrics guidance from file."""
    mock_mcp = MagicMock()
    mock_data = {'test': 'data'}

    with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
        handler = CloudWatchMetricsHandler(mock_mcp)
        assert handler.metrics_guidance == mock_data


def test_load_metrics_guidance_error():
    """Test error handling when loading metrics guidance."""
    mock_mcp = MagicMock()

    with patch('builtins.open', side_effect=Exception('Test error')):
        with patch('loguru.logger.error') as mock_logger:
            handler = CloudWatchMetricsHandler(mock_mcp)
            assert handler.metrics_guidance == {}
            mock_logger.assert_called_once_with(
                'Failed to load EKS CloudWatch metrics guidance: Test error'
            )
