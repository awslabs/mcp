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

"""Tests for the misc functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.misc import (
    delete,
    expire,
    rename,
    type,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError as RedisError


class TestMisc:
    """Tests for misc operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.misc.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context."""
        with patch('awslabs.valkey_mcp_server.tools.misc.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = False
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_delete(self, mock_connection, mock_context):
        """Test deleting a key."""
        key = 'test_key'

        # Test successful delete
        mock_context.readonly_mode.return_value = False
        mock_connection.delete.return_value = 1
        result = await delete(key)
        assert f'Successfully deleted {key}' in result
        mock_connection.delete.assert_called_with(key)

        # Test key not found
        mock_connection.delete.return_value = 0
        result = await delete(key)
        assert f'Key {key} not found' in result

        # Test error handling
        mock_connection.delete.side_effect = RedisError('Test error')
        result = await delete(key)
        assert f'Error deleting key {key}' in result
        assert 'Test error' in result

        # Test readonly mode
        mock_connection.delete.reset_mock()
        mock_connection.delete.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await delete(key)
        assert 'Error: Cannot delete key in readonly mode' in result
        mock_connection.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_type(self, mock_connection):
        """Test getting key type."""
        key = 'test_key'

        # Test successful type check
        mock_connection.type.return_value = 'string'
        mock_connection.ttl.return_value = 100
        result = await type(key)
        assert result['type'] == 'string'
        assert result['ttl'] == 100
        mock_connection.type.assert_called_with(key)
        mock_connection.ttl.assert_called_with(key)

        # Test error handling
        mock_connection.type.side_effect = RedisError('Test error')
        result = await type(key)
        assert 'error' in result
        assert 'Test error' in result['error']

    @pytest.mark.asyncio
    async def test_expire(self, mock_connection, mock_context):
        """Test setting expiration time."""
        key = 'test_key'
        expire_seconds = 60

        # Test successful expire
        mock_context.readonly_mode.return_value = False
        mock_connection.expire.return_value = True
        result = await expire(key, expire_seconds)
        assert f'Expiration set to {expire_seconds} seconds' in result
        mock_connection.expire.assert_called_with(key, expire_seconds)

        # Test key not found
        mock_connection.expire.return_value = False
        result = await expire(key, expire_seconds)
        assert f"Key '{key}' does not exist" in result

        # Test error handling
        mock_connection.expire.side_effect = RedisError('Test error')
        result = await expire(key, expire_seconds)
        assert f"Error setting expiration for key '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_connection.expire.reset_mock()
        mock_connection.expire.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await expire(key, expire_seconds)
        assert 'Error: Cannot set expiration in readonly mode' in result
        mock_connection.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_rename(self, mock_connection, mock_context):
        """Test renaming a key."""
        old_key = 'old_key'
        new_key = 'new_key'

        # Test successful rename
        mock_context.readonly_mode.return_value = False
        mock_connection.exists.return_value = True
        result = await rename(old_key, new_key)
        assert 'status' in result
        assert result['status'] == 'success'
        assert f"Renamed key '{old_key}' to '{new_key}'" in result['message']
        mock_connection.rename.assert_called_with(old_key, new_key)

        # Test old key not found
        mock_connection.exists.return_value = False
        result = await rename(old_key, new_key)
        assert 'error' in result
        assert f"Key '{old_key}' does not exist" in result['error']

        # Test error handling
        mock_connection.exists.return_value = True
        mock_connection.rename.side_effect = RedisError('Test error')
        result = await rename(old_key, new_key)
        assert 'error' in result
        assert 'Test error' in result['error']

        # Test readonly mode
        mock_connection.rename.reset_mock()
        mock_connection.rename.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await rename(old_key, new_key)
        assert 'error' in result
        assert 'Cannot rename key in readonly mode' in result['error']
        mock_connection.rename.assert_not_called()
