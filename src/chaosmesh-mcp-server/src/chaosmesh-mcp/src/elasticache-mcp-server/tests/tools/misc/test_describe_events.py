"""Tests for the describe events tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.misc.describe_events import describe_events
from datetime import datetime
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_describe_events_basic():
    """Test basic describe events functionality."""
    mock_client = MagicMock()
    mock_client.describe_events.return_value = {
        'Events': [
            {
                'SourceIdentifier': 'my-cluster',
                'SourceType': 'cache-cluster',
                'Message': 'Cache cluster created',
                'Date': datetime(2025, 1, 1, 12, 0, 0),
            },
            {
                'SourceIdentifier': 'my-group',
                'SourceType': 'replication-group',
                'Message': 'Replication group modified',
                'Date': datetime(2025, 1, 1, 13, 0, 0),
            },
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_events()
        mock_client.describe_events.assert_called_once_with()
        assert 'Events' in result
        assert len(result['Events']) == 2
        source_types = {event['SourceType'] for event in result['Events']}
        assert source_types == {'cache-cluster', 'replication-group'}


@pytest.mark.asyncio
async def test_describe_events_with_source_type():
    """Test describe events with source type filter."""
    mock_client = MagicMock()
    mock_client.describe_events.return_value = {
        'Events': [
            {
                'SourceIdentifier': 'my-cluster',
                'SourceType': 'cache-cluster',
                'Message': 'Cache cluster created',
                'Date': datetime(2025, 1, 1, 12, 0, 0),
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_events(source_type='cache-cluster')
        mock_client.describe_events.assert_called_once_with(SourceType='cache-cluster')
        assert result['Events'][0]['SourceType'] == 'cache-cluster'


@pytest.mark.asyncio
async def test_describe_events_with_source_identifier():
    """Test describe events with source identifier filter."""
    mock_client = MagicMock()
    mock_client.describe_events.return_value = {
        'Events': [
            {
                'SourceIdentifier': 'my-cluster',
                'SourceType': 'cache-cluster',
                'Message': 'Cache cluster created',
                'Date': datetime(2025, 1, 1, 12, 0, 0),
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_events(source_identifier='my-cluster')
        mock_client.describe_events.assert_called_once_with(SourceIdentifier='my-cluster')
        assert result['Events'][0]['SourceIdentifier'] == 'my-cluster'


@pytest.mark.asyncio
async def test_describe_events_with_time_range():
    """Test describe events with time range filters."""
    mock_client = MagicMock()
    start_time = datetime(2025, 1, 1, 12, 0, 0)
    end_time = datetime(2025, 1, 1, 14, 0, 0)

    mock_client.describe_events.return_value = {
        'Events': [
            {
                'SourceIdentifier': 'my-cluster',
                'SourceType': 'cache-cluster',
                'Message': 'Cache cluster created',
                'Date': datetime(2025, 1, 1, 13, 0, 0),
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_events(start_time=start_time, end_time=end_time)
        mock_client.describe_events.assert_called_once_with(StartTime=start_time, EndTime=end_time)
        assert len(result['Events']) == 1


@pytest.mark.asyncio
async def test_describe_events_with_duration():
    """Test describe events with duration filter."""
    mock_client = MagicMock()
    mock_client.describe_events.return_value = {
        'Events': [
            {
                'SourceIdentifier': 'my-cluster',
                'SourceType': 'cache-cluster',
                'Message': 'Cache cluster created',
                'Date': datetime(2025, 1, 1, 12, 0, 0),
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_events(duration=60)
        mock_client.describe_events.assert_called_once_with(Duration=60)
        assert len(result['Events']) == 1


@pytest.mark.asyncio
async def test_describe_events_with_pagination():
    """Test describe events with pagination parameters."""
    mock_client = MagicMock()
    mock_client.describe_events.return_value = {
        'Events': [
            {
                'SourceIdentifier': 'my-cluster',
                'SourceType': 'cache-cluster',
                'Message': 'Cache cluster created',
                'Date': datetime(2025, 1, 1, 12, 0, 0),
            }
        ],
        'Marker': 'next-page',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_events(max_records=20, marker='current-page')
        mock_client.describe_events.assert_called_once_with(MaxRecords=20, Marker='current-page')
        assert 'Marker' in result
        assert result['Marker'] == 'next-page'


@pytest.mark.asyncio
async def test_describe_events_invalid_parameter():
    """Test describe events with invalid parameter."""
    mock_client = MagicMock()
    exception_class = 'InvalidParameterValueException'
    error_message = 'Invalid parameter value'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_events.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_events(source_type='invalid-type')
        assert 'error' in result
        assert error_message in result['error']


@pytest.mark.asyncio
async def test_describe_events_invalid_parameter_combination():
    """Test describe events with invalid parameter combination."""
    mock_client = MagicMock()

    exception_class = 'InvalidParameterCombinationException'
    error_message = 'Invalid parameter combination'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_events.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_events(duration=60, start_time=datetime(2025, 1, 1, 12, 0, 0))
        assert 'error' in result
        assert error_message in result['error']
