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

"""Tests for filter_log_events tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cwlogs.filter_log_events import filter_log_events
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
async def test_filter_log_events_basic(mock_logs_client):
    """Test basic filter_log_events functionality."""
    # Mock response from CloudWatch Logs
    mock_logs_client.filter_log_events.return_value = {
        'events': [
            {
                'timestamp': 1622505600000,
                'message': 'Test log message 1',
                'ingestionTime': 1622505601000,
                'eventId': 'event1',
                'logStreamName': 'stream1',
            },
            {
                'timestamp': 1622505700000,
                'message': 'Test log message 2',
                'ingestionTime': 1622505701000,
                'eventId': 'event2',
                'logStreamName': 'stream2',
            },
        ],
        'searchedLogStreams': [
            {'logStreamName': 'stream1', 'searchedCompletely': True},
            {'logStreamName': 'stream2', 'searchedCompletely': False},
        ],
        'nextToken': 'token123',
    }

    # Call the function
    result = await filter_log_events(log_group_name='test-group')

    # Verify the client was called correctly
    mock_logs_client.filter_log_events.assert_called_once_with(logGroupName='test-group')

    # Verify the response was formatted correctly
    assert len(result['events']) == 2
    assert result['events'][0]['timestamp'] == 1622505600000
    assert result['events'][0]['message'] == 'Test log message 1'
    assert result['events'][0]['ingestionTime'] == 1622505601000
    assert result['events'][0]['eventId'] == 'event1'
    assert result['events'][0]['logStreamName'] == 'stream1'

    assert len(result['searchedLogStreams']) == 2
    assert result['searchedLogStreams'][0]['logStreamName'] == 'stream1'
    assert result['searchedLogStreams'][0]['searchedCompletely'] is True
    assert result['nextToken'] == 'token123'


@pytest.mark.asyncio
async def test_filter_log_events_with_all_params(mock_logs_client):
    """Test filter_log_events with all optional parameters."""
    # Mock response
    mock_logs_client.filter_log_events.return_value = {
        'events': [],
        'searchedLogStreams': [],
        'nextToken': 'token123',
    }

    # Call with all parameters
    start_time = datetime(2023, 1, 1)
    end_time = datetime(2023, 1, 2)

    await filter_log_events(
        log_group_name='test-group',
        log_group_identifier='test-identifier',
        log_stream_names=['stream1', 'stream2'],
        log_stream_name_prefix='test-',
        start_time=start_time,
        end_time=end_time,
        filter_pattern='ERROR',
        interleaved=True,
        unmask=True,
        starting_token='token123',
        page_size=50,
        max_items=100,
    )

    # Verify all parameters were passed correctly
    mock_logs_client.filter_log_events.assert_called_once_with(
        logGroupName='test-group',
        logGroupIdentifier='test-identifier',
        logStreamNames=['stream1', 'stream2'],
        logStreamNamePrefix='test-',
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000),
        filterPattern='ERROR',
        interleaved=True,
        unmask=True,
        nextToken='token123',
        limit=50,
    )


@pytest.mark.asyncio
async def test_filter_log_events_error(mock_logs_client):
    """Test filter_log_events error handling."""
    # Mock error response
    mock_logs_client.filter_log_events.side_effect = ClientError(
        {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Log group not found'}},
        'FilterLogEvents',
    )

    # Call the function and verify error is handled
    result = await filter_log_events(log_group_name='nonexistent-group')

    assert 'error' in result
    assert 'Log group not found' in result['error']


@pytest.mark.asyncio
async def test_filter_log_events_pagination(mock_logs_client):
    """Test filter_log_events pagination parameters."""
    # Mock response
    mock_logs_client.filter_log_events.return_value = {
        'events': [
            {
                'timestamp': 1622505600000,
                'message': 'Test log message',
                'ingestionTime': 1622505601000,
                'eventId': 'event1',
                'logStreamName': 'stream1',
            }
        ],
        'searchedLogStreams': [{'logStreamName': 'stream1', 'searchedCompletely': True}],
        'nextToken': 'next-page-token',
    }

    # Call with pagination parameters
    result = await filter_log_events(
        log_group_name='test-group',
        starting_token='current-page-token',
        page_size=25,
        max_items=100,
    )

    # Verify pagination parameters were passed correctly
    mock_logs_client.filter_log_events.assert_called_once_with(
        logGroupName='test-group', nextToken='current-page-token', limit=25
    )

    # Verify response includes pagination token
    assert result['nextToken'] == 'next-page-token'
