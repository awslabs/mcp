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

"""Additional tests for the List functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.list import (
    list_pop_left,
    list_prepend,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestListAdditional:
    """Additional tests for List operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.list.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context."""
        with patch('awslabs.valkey_mcp_server.tools.list.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = False
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_list_prepend(self, mock_connection, mock_context):
        """Test prepending value to list."""
        key = 'test_list'
        value = 'test_value'

        # Test successful prepend
        mock_context.readonly_mode.return_value = False
        mock_connection.lpush.return_value = 1
        result = await list_prepend(key, value)
        assert f"Successfully prepended value to list '{key}'" in result
        mock_connection.lpush.assert_called_with(key, value)

        # Test error handling
        mock_connection.lpush.side_effect = ValkeyError('Test error')
        result = await list_prepend(key, value)
        assert f"Error prepending to list '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_connection.lpush.reset_mock()
        mock_connection.lpush.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await list_prepend(key, value)
        assert 'Error: Cannot prepend to list in readonly mode' in result
        mock_connection.lpush.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_pop_left(self, mock_connection, mock_context):
        """Test popping from left of list."""
        key = 'test_list'

        # Test successful pop
        mock_context.readonly_mode.return_value = False
        mock_connection.lpop.return_value = 'test_value'
        result = await list_pop_left(key)
        assert 'test_value' in result
        mock_connection.lpop.assert_called_with(key)

        # Test empty list
        mock_connection.lpop.return_value = None
        result = await list_pop_left(key)
        assert f"List '{key}' is empty" in result

        # Test error handling
        mock_connection.lpop.side_effect = ValkeyError('Test error')
        result = await list_pop_left(key)
        assert f"Error popping from left of list '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_connection.lpop.reset_mock()
        mock_connection.lpop.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await list_pop_left(key)
        assert 'Error: Cannot pop from list in readonly mode' in result
        mock_connection.lpop.assert_not_called()
