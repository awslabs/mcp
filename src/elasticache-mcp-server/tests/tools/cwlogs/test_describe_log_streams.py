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

"""Tests for describe-log-streams tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cwlogs.describe_log_streams import describe_log_streams
from unittest.mock import MagicMock, call, patch


@pytest.mark.asyncio
async def test_describe_log_streams_with_max_items():
    """Test describe log streams with max_items pagination."""
    mock_client = MagicMock()

    # Mock responses for pagination
    mock_responses = [
        {
            'logStreams': [
                {'logStreamName': f'stream{i}', 'creationTime': 1234567890 + i}
                for i in range(1, 4)
            ],
            'nextToken': 'token1',
        },
        {
            'logStreams': [
                {'logStreamName': f'stream{i}', 'creationTime': 1234567890 + i}
                for i in range(4, 6)
            ],
            'nextToken': 'token2',
        },
    ]
    mock_client.describe_log_streams.side_effect = mock_responses

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Request 4 items total (should need 2 API calls)
        result = await describe_log_streams(
            log_group_name='test-group',
            max_items=4,
            page_size=3,
        )

        # Verify API calls
        assert mock_client.describe_log_streams.call_count == 2
        mock_client.describe_log_streams.assert_has_calls(
            [
                call(logGroupName='test-group', limit=3),
                call(logGroupName='test-group', limit=1, nextToken='token1'),
            ]
        )

        # Verify response
        assert len(result['logStreams']) == 4
        assert [s['logStreamName'] for s in result['logStreams']] == [
            'stream1',
            'stream2',
            'stream3',
            'stream4',
        ]
        assert result['nextToken'] == 'token2'


@pytest.mark.asyncio
async def test_describe_log_streams_max_items_exact():
    """Test describe log streams when max_items exactly matches available items."""
    mock_client = MagicMock()

    # Mock response with exactly the number of items requested
    mock_response = {
        'logStreams': [
            {'logStreamName': f'stream{i}', 'creationTime': 1234567890 + i} for i in range(1, 4)
        ],
        'nextToken': 'next-token',
    }
    mock_client.describe_log_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_log_streams(
            log_group_name='test-group',
            max_items=3,
        )

        # Verify single API call
        mock_client.describe_log_streams.assert_called_once_with(logGroupName='test-group')

        # Verify response
        assert len(result['logStreams']) == 3
        assert result['nextToken'] == 'next-token'


@pytest.mark.asyncio
async def test_describe_log_streams_max_items_less():
    """Test describe log streams when max_items is less than available items."""
    mock_client = MagicMock()

    # Mock response with more items than requested
    mock_response = {
        'logStreams': [
            {'logStreamName': f'stream{i}', 'creationTime': 1234567890 + i} for i in range(1, 6)
        ],
        'nextToken': 'next-token',
    }
    mock_client.describe_log_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_log_streams(
            log_group_name='test-group',
            max_items=3,
        )

        # Verify response is truncated
        assert len(result['logStreams']) == 3
        assert [s['logStreamName'] for s in result['logStreams']] == [
            'stream1',
            'stream2',
            'stream3',
        ]
        assert result['nextToken'] == 'next-token'


@pytest.mark.asyncio
async def test_describe_log_streams_with_page_size():
    """Test describe log streams with page_size parameter."""
    mock_client = MagicMock()

    # Mock response
    mock_response = {
        'logStreams': [{'logStreamName': 'stream1', 'creationTime': 1234567890}],
    }
    mock_client.describe_log_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_log_streams(
            log_group_name='test-group',
            page_size=10,
        )

        # Verify client call includes limit parameter
        mock_client.describe_log_streams.assert_called_once_with(
            logGroupName='test-group',
            limit=10,
        )

        # Verify response
        assert result == {'logStreams': mock_response['logStreams']}


@pytest.mark.asyncio
async def test_describe_log_streams_with_starting_token():
    """Test describe log streams with starting_token parameter."""
    mock_client = MagicMock()

    # Mock response
    mock_response = {
        'logStreams': [{'logStreamName': 'stream2', 'creationTime': 1234567890}],
        'nextToken': 'next-token',
    }
    mock_client.describe_log_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_log_streams(
            log_group_name='test-group',
            starting_token='current-token',
        )

        # Verify client call includes nextToken parameter
        mock_client.describe_log_streams.assert_called_once_with(
            logGroupName='test-group',
            nextToken='current-token',
        )

        # Verify response
        assert result == {
            'logStreams': mock_response['logStreams'],
            'nextToken': 'next-token',
        }


@pytest.mark.asyncio
async def test_describe_log_streams_basic():
    """Test basic describe log streams functionality."""
    mock_client = MagicMock()

    # Mock response
    mock_response = {
        'logStreams': [
            {
                'logStreamName': 'stream1',
                'creationTime': 1234567890,
                'firstEventTimestamp': 1234567890,
                'lastEventTimestamp': 1234567899,
                'lastIngestionTime': 1234567899,
                'uploadSequenceToken': 'token1',
                'arn': 'arn:aws:logs:region:account:log-group:name:log-stream:stream1',
                'storedBytes': 1234,
            }
        ],
        'nextToken': 'next-token',
    }
    mock_client.describe_log_streams.return_value = mock_response

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call function
        result = await describe_log_streams(
            log_group_name='test-group',
            log_stream_name_prefix='stream',
            order_by='LogStreamName',
            descending=True,
        )

        # Verify client call
        mock_client.describe_log_streams.assert_called_once_with(
            logGroupName='test-group',
            logStreamNamePrefix='stream',
            orderBy='LogStreamName',
            descending=True,
        )

        # Verify response
        assert result == {'logStreams': mock_response['logStreams'], 'nextToken': 'next-token'}


@pytest.mark.asyncio
async def test_describe_log_streams_minimal_params():
    """Test describe log streams with minimal parameters."""
    mock_client = MagicMock()
    # Mock response
    mock_response = {
        'logStreams': [],
    }
    mock_client.describe_log_streams.return_value = mock_response
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call function
        result = await describe_log_streams()

        # Verify client call
        mock_client.describe_log_streams.assert_called_once_with()

        # Verify response
        assert result == {'logStreams': []}


@pytest.mark.asyncio
async def test_describe_log_streams_with_identifier():
    """Test describe log streams with log group identifier."""
    mock_client = MagicMock()
    # Mock response
    mock_response = {'logStreams': [{'logStreamName': 'stream1', 'creationTime': 1234567890}]}
    mock_client.describe_log_streams.return_value = mock_response
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call function
        result = await describe_log_streams(log_group_identifier='test-identifier')

        # Verify client call
        mock_client.describe_log_streams.assert_called_once_with(
            logGroupIdentifier='test-identifier'
        )

        # Verify response
        assert result == {'logStreams': mock_response['logStreams']}


@pytest.mark.asyncio
async def test_describe_log_streams_error():
    """Test describe log streams error handling."""
    mock_client = MagicMock()
    # Mock error response
    mock_client.describe_log_streams.side_effect = Exception('Test error')
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call function
        result = await describe_log_streams(log_group_name='test-group')

        # Verify client call
        mock_client.describe_log_streams.assert_called_once_with(logGroupName='test-group')

        # Verify error response
        assert result == {'error': 'Test error'}
