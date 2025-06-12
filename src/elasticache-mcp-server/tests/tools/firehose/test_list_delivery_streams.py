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

"""Tests for list-delivery-streams tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.firehose.list_delivery_streams import (
    list_delivery_streams,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_list_delivery_streams_basic():
    """Test basic delivery stream listing functionality."""
    mock_client = MagicMock()
    mock_response = {
        'DeliveryStreamNames': ['stream1', 'stream2'],
        'HasMoreDeliveryStreams': False,
    }
    mock_client.list_delivery_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.FirehoseConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_delivery_streams()

        # Verify client call
        mock_client.list_delivery_streams.assert_called_once_with()

        # Verify response
        assert result['DeliveryStreamNames'] == ['stream1', 'stream2']
        assert result['HasMoreDeliveryStreams'] is False


@pytest.mark.asyncio
async def test_list_delivery_streams_with_params():
    """Test delivery stream listing with all parameters."""
    mock_client = MagicMock()
    mock_response = {
        'DeliveryStreamNames': ['stream3'],
        'HasMoreDeliveryStreams': True,
    }
    mock_client.list_delivery_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.FirehoseConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_delivery_streams(
            limit=1,
            delivery_stream_type='DirectPut',
            exclusive_start_delivery_stream_name='stream2',
        )

        # Verify client call with parameters
        mock_client.list_delivery_streams.assert_called_once_with(
            Limit=1,
            DeliveryStreamType='DirectPut',
            ExclusiveStartDeliveryStreamName='stream2',
        )

        # Verify response
        assert result['DeliveryStreamNames'] == ['stream3']
        assert result['HasMoreDeliveryStreams'] is True


@pytest.mark.asyncio
async def test_list_delivery_streams_empty():
    """Test delivery stream listing with empty response."""
    mock_client = MagicMock()
    mock_response = {
        'DeliveryStreamNames': [],
        'HasMoreDeliveryStreams': False,
    }
    mock_client.list_delivery_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.FirehoseConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_delivery_streams()

        # Verify client call
        mock_client.list_delivery_streams.assert_called_once_with()

        # Verify response
        assert result['DeliveryStreamNames'] == []
        assert result['HasMoreDeliveryStreams'] is False


@pytest.mark.asyncio
async def test_list_delivery_streams_partial_params():
    """Test delivery stream listing with some parameters."""
    mock_client = MagicMock()
    mock_response = {
        'DeliveryStreamNames': ['stream1'],
        'HasMoreDeliveryStreams': False,
    }
    mock_client.list_delivery_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.FirehoseConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test with only limit
        result = await list_delivery_streams(limit=1)
        mock_client.list_delivery_streams.assert_called_with(Limit=1)
        assert result['DeliveryStreamNames'] == ['stream1']

        # Test with only delivery_stream_type
        result = await list_delivery_streams(delivery_stream_type='KinesisStreamAsSource')
        mock_client.list_delivery_streams.assert_called_with(
            DeliveryStreamType='KinesisStreamAsSource'
        )
        assert result['DeliveryStreamNames'] == ['stream1']


@pytest.mark.asyncio
async def test_list_delivery_streams_error():
    """Test delivery stream listing error handling."""
    mock_client = MagicMock()
    mock_client.list_delivery_streams.side_effect = Exception('Test error')

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.FirehoseConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_delivery_streams()

        # Verify client call
        mock_client.list_delivery_streams.assert_called_once_with()

        # Verify error response
        assert result == {'error': 'Test error'}


@pytest.mark.asyncio
async def test_list_delivery_streams_missing_fields():
    """Test delivery stream listing with missing response fields."""
    mock_client = MagicMock()
    mock_response = {}  # Empty response missing all fields
    mock_client.list_delivery_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.FirehoseConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await list_delivery_streams()

        # Verify client call
        mock_client.list_delivery_streams.assert_called_once_with()

        # Verify response with default values
        assert result['DeliveryStreamNames'] == []
        assert result['HasMoreDeliveryStreams'] is False
