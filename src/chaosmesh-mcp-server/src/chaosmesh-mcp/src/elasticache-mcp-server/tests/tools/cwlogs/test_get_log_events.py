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

"""Tests for get_log_events tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cwlogs.get_log_events import get_log_events
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import patch


@pytest.fixture
def mock_logs_client():
    """Create a mock CloudWatch Logs client."""
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection'
    ) as mock:
        yield mock.return_value


@pytest.mark.asyncio
async def test_get_log_events_basic(mock_logs_client):
    """Test basic get_log_events functionality."""
    # Mock response from CloudWatch Logs
    mock_logs_client.get_log_events.return_value = {
        'events': [
            {
                'timestamp': 1622505600000,
                'message': 'Test log message 1',
                'ingestionTime': 1622505601000,
            },
            {
                'timestamp': 1622505700000,
                'message': 'Test log message 2',
                'ingestionTime': 1622505701000,
            },
        ],
        'nextForwardToken': 'f/12345',
        'nextBackwardToken': 'b/12345',
    }

    # Call the function
    result = await get_log_events(log_stream_name='test-stream', log_group_name='test-group')

    # Verify the client was called correctly
    mock_logs_client.get_log_events.assert_called_once_with(
        logStreamName='test-stream', logGroupName='test-group'
    )

    # Verify the response was formatted correctly
    assert len(result['events']) == 2
    assert result['events'][0]['timestamp'] == 1622505600000
    assert result['events'][0]['message'] == 'Test log message 1'
    assert result['events'][0]['ingestionTime'] == 1622505601000
    assert result['nextForwardToken'] == 'f/12345'
    assert result['nextBackwardToken'] == 'b/12345'


@pytest.mark.asyncio
async def test_get_log_events_with_all_params(mock_logs_client):
    """Test get_log_events with all optional parameters."""
    # Mock response
    mock_logs_client.get_log_events.return_value = {
        'events': [],
        'nextForwardToken': 'f/12345',
        'nextBackwardToken': 'b/12345',
    }

    # Call with all parameters
    start_time = datetime(2023, 1, 1)
    end_time = datetime(2023, 1, 2)

    await get_log_events(
        log_stream_name='test-stream',
        log_group_name='test-group',
        log_group_identifier='test-identifier',
        start_time=start_time,
        end_time=end_time,
        next_token='token123',
        limit=100,
        start_from_head=True,
        unmask=True,
    )

    # Verify all parameters were passed correctly
    mock_logs_client.get_log_events.assert_called_once_with(
        logStreamName='test-stream',
        logGroupName='test-group',
        logGroupIdentifier='test-identifier',
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000),
        nextToken='token123',
        limit=100,
        startFromHead=True,
        unmask=True,
    )


@pytest.mark.asyncio
async def test_get_log_events_error(mock_logs_client):
    """Test get_log_events error handling."""
    # Mock error response
    mock_logs_client.get_log_events.side_effect = ClientError(
        {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Log stream not found'}},
        'GetLogEvents',
    )

    # Call the function and verify error is handled
    result = await get_log_events(
        log_stream_name='nonexistent-stream', log_group_name='test-group'
    )

    assert 'error' in result
    assert 'Log stream not found' in result['error']
