"""Tests for the connection reuse mechanism in server.py."""

import pytest
import psycopg
from unittest.mock import AsyncMock, patch, MagicMock
from awslabs.aurora_dsql_mcp_server.server import execute_query, get_connection

ctx = AsyncMock()

@pytest.fixture
async def reset_persistent_connection():
    """Reset the persistent connection before and after each test."""
    import awslabs.aurora_dsql_mcp_server.server as server
    server.persistent_connection = None
    yield
    server.persistent_connection = None

def create_mock_connection():
    """Create a mock connection with cursor context manager."""
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)
    mock_cursor.execute = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.closed = False
    return mock_conn, mock_cursor

@pytest.mark.asyncio
@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'admin')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_connection_reuse(mocker, reset_persistent_connection):
    """Test that connections are reused when possible."""
    mock_auth = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_password_token')
    mock_auth.return_value = 'auth_token'
    mock_connect = mocker.patch('psycopg.AsyncConnection.connect')

    # Create mock connection with working cursor
    mock_conn, mock_cursor = create_mock_connection()
    mock_connect.return_value = mock_conn

    # First connection attempt should create a new connection
    result1 = await get_connection(ctx)
    assert mock_connect.call_count == 1
    assert result1 is mock_conn

    # Second connection attempt should reuse the existing connection
    result2 = await get_connection(ctx)
    assert mock_connect.call_count == 1  # Connection count should not increase
    assert result2 is mock_conn  # Should be the same connection object
    assert result1 is result2  # Should be the exact same object


@pytest.mark.asyncio
@patch('awslabs.aurora_dsql_mcp_server.server.database_user', 'admin')
@patch('awslabs.aurora_dsql_mcp_server.server.cluster_endpoint', 'test_ce')
async def test_connection_reuse_with_broken_connection(mocker, reset_persistent_connection):
    """Test handling of broken connections during reuse attempts."""
    mock_auth = mocker.patch('awslabs.aurora_dsql_mcp_server.server.get_password_token')
    mock_auth.return_value = 'auth_token'
    mock_connect = mocker.patch('psycopg.AsyncConnection.connect')

    # Create two mock connections
    mock_conn1, mock_cursor1 = create_mock_connection()
    mock_conn2, mock_cursor2 = create_mock_connection()
    mock_connect.side_effect = [mock_conn1, mock_conn2]

    # Simulate a broken connection that appears open but fails on use
    mock_cursor1.execute.side_effect = psycopg.InterfaceError("Connection broken")

    await execute_query(ctx, None, "SELECT 1;")
    assert mock_connect.call_count == 2
