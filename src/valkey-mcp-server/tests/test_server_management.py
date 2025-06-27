import pytest
from awslabs.valkey_mcp_server.tools.server_management import client_list, dbsize, info
from unittest.mock import MagicMock, patch
from valkey.exceptions import ValkeyError


@pytest.mark.asyncio
async def test_dbsize_success():
    """Test successful dbsize call."""
    with patch(
        'awslabs.valkey_mcp_server.tools.server_management.ValkeyConnectionManager'
    ) as mock_manager:
        mock_conn = MagicMock()
        mock_conn.dbsize.return_value = 42
        mock_manager.get_connection.return_value = mock_conn

        result = await dbsize()
        assert result == '42'
        mock_conn.dbsize.assert_called_once()


@pytest.mark.asyncio
async def test_dbsize_error():
    """Test dbsize error handling."""
    with patch(
        'awslabs.valkey_mcp_server.tools.server_management.ValkeyConnectionManager'
    ) as mock_manager:
        mock_conn = MagicMock()
        mock_conn.dbsize.side_effect = ValkeyError('Connection failed')
        mock_manager.get_connection.return_value = mock_conn

        with pytest.raises(RuntimeError) as exc_info:
            await dbsize()
        assert 'Error getting database size: Connection failed' in str(exc_info.value)


@pytest.mark.asyncio
async def test_info_success():
    """Test successful info call."""
    with patch(
        'awslabs.valkey_mcp_server.tools.server_management.ValkeyConnectionManager'
    ) as mock_manager:
        mock_conn = MagicMock()
        mock_info = {'redis_version': '6.0.0', 'connected_clients': '1'}
        mock_conn.info.return_value = mock_info
        mock_manager.get_connection.return_value = mock_conn

        result = await info()
        assert result == str(mock_info)
        mock_conn.info.assert_called_once_with('default')

        # Test with custom section
        result = await info(section='memory')
        assert result == str(mock_info)
        mock_conn.info.assert_called_with('memory')


@pytest.mark.asyncio
async def test_info_error():
    """Test info error handling."""
    with patch(
        'awslabs.valkey_mcp_server.tools.server_management.ValkeyConnectionManager'
    ) as mock_manager:
        mock_conn = MagicMock()
        mock_conn.info.side_effect = ValkeyError('Info command failed')
        mock_manager.get_connection.return_value = mock_conn

        with pytest.raises(RuntimeError) as exc_info:
            await info()
        assert 'Error retrieving Redis info: Info command failed' in str(exc_info.value)


@pytest.mark.asyncio
async def test_client_list_success():
    """Test successful client_list call."""
    with patch(
        'awslabs.valkey_mcp_server.tools.server_management.ValkeyConnectionManager'
    ) as mock_manager:
        mock_conn = MagicMock()
        mock_clients = [
            {'id': '1', 'addr': '127.0.0.1:12345', 'age': '100'},
            {'id': '2', 'addr': '127.0.0.1:12346', 'age': '200'},
        ]
        mock_conn.client_list.return_value = mock_clients
        mock_manager.get_connection.return_value = mock_conn

        result = await client_list()
        assert result == str(mock_clients)
        mock_conn.client_list.assert_called_once()


@pytest.mark.asyncio
async def test_client_list_error():
    """Test client_list error handling."""
    with patch(
        'awslabs.valkey_mcp_server.tools.server_management.ValkeyConnectionManager'
    ) as mock_manager:
        mock_conn = MagicMock()
        mock_conn.client_list.side_effect = ValkeyError('Client list failed')
        mock_manager.get_connection.return_value = mock_conn

        with pytest.raises(RuntimeError) as exc_info:
            await client_list()
        assert 'Error retrieving client list: Client list failed' in str(exc_info.value)
