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

"""Tests for readonly mode in Set functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.set import (
    set_add,
    set_move,
    set_pop,
    set_remove,
)
from unittest.mock import Mock, patch


class TestSetReadonly:
    """Tests for Set operations in readonly mode."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.set.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context."""
        with patch('awslabs.valkey_mcp_server.tools.set.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = True
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_set_add_readonly(self, mock_connection, mock_context):
        """Test adding member to set in readonly mode."""
        key = 'test_set'
        member = 'test_member'

        result = await set_add(key, member)
        assert 'Error: Cannot add to set in readonly mode' in result
        mock_connection.sadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_remove_readonly(self, mock_connection, mock_context):
        """Test removing member from set in readonly mode."""
        key = 'test_set'
        member = 'test_member'

        result = await set_remove(key, member)
        assert 'Error: Cannot remove from set in readonly mode' in result
        mock_connection.srem.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_pop_readonly(self, mock_connection, mock_context):
        """Test popping member from set in readonly mode."""
        key = 'test_set'

        result = await set_pop(key)
        assert 'Error: Cannot pop from set in readonly mode' in result
        mock_connection.spop.assert_not_called()

        # Also test with count parameter
        result = await set_pop(key, count=2)
        assert 'Error: Cannot pop from set in readonly mode' in result
        mock_connection.spop.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_move_readonly(self, mock_connection, mock_context):
        """Test moving member between sets in readonly mode."""
        source = 'source_set'
        destination = 'dest_set'
        member = 'test_member'

        result = await set_move(source, destination, member)
        assert 'Error: Cannot move set members in readonly mode' in result
        mock_connection.smove.assert_not_called()
