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

"""Tests for readonly mode in List functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.list import (
    list_append,
    list_append_multiple,
    list_insert_after,
    list_insert_before,
    list_move,
    list_pop_left,
    list_pop_right,
    list_prepend,
    list_prepend_multiple,
    list_remove,
    list_set,
    list_trim,
)
from unittest.mock import Mock, patch


class TestListReadonly:
    """Tests for List operations in readonly mode."""

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
            mock_ctx.readonly_mode.return_value = True
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_list_append_readonly(self, mock_connection, mock_context):
        """Test appending to list in readonly mode."""
        key = 'test_list'
        value = 'test_value'

        result = await list_append(key, value)
        assert 'Error: Cannot append to list in readonly mode' in result
        mock_connection.rpush.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_prepend_readonly(self, mock_connection, mock_context):
        """Test prepending to list in readonly mode."""
        key = 'test_list'
        value = 'test_value'

        result = await list_prepend(key, value)
        assert 'Error: Cannot prepend to list in readonly mode' in result
        mock_connection.lpush.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_append_multiple_readonly(self, mock_connection, mock_context):
        """Test appending multiple values to list in readonly mode."""
        key = 'test_list'
        values = ['value1', 'value2']

        result = await list_append_multiple(key, values)
        assert 'Error: Cannot append to list in readonly mode' in result
        mock_connection.rpush.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_prepend_multiple_readonly(self, mock_connection, mock_context):
        """Test prepending multiple values to list in readonly mode."""
        key = 'test_list'
        values = ['value1', 'value2']

        result = await list_prepend_multiple(key, values)
        assert 'Error: Cannot prepend to list in readonly mode' in result
        mock_connection.lpush.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_set_readonly(self, mock_connection, mock_context):
        """Test setting value at index in list in readonly mode."""
        key = 'test_list'
        index = 1
        value = 'test_value'

        result = await list_set(key, index, value)
        assert 'Error: Cannot set list value in readonly mode' in result
        mock_connection.lset.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_trim_readonly(self, mock_connection, mock_context):
        """Test trimming list in readonly mode."""
        key = 'test_list'
        start = 0
        stop = 5

        result = await list_trim(key, start, stop)
        assert 'Error: Cannot trim list in readonly mode' in result
        mock_connection.ltrim.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_pop_left_readonly(self, mock_connection, mock_context):
        """Test popping from left of list in readonly mode."""
        key = 'test_list'

        result = await list_pop_left(key)
        assert 'Error: Cannot pop from list in readonly mode' in result
        mock_connection.lpop.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_pop_right_readonly(self, mock_connection, mock_context):
        """Test popping from right of list in readonly mode."""
        key = 'test_list'

        result = await list_pop_right(key)
        assert 'Error: Cannot pop from list in readonly mode' in result
        mock_connection.rpop.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_move_readonly(self, mock_connection, mock_context):
        """Test moving element between lists in readonly mode."""
        source = 'source_list'
        destination = 'dest_list'

        result = await list_move(source, destination)
        assert 'Error: Cannot move list elements in readonly mode' in result
        mock_connection.lmove.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_insert_before_readonly(self, mock_connection, mock_context):
        """Test inserting before pivot in list in readonly mode."""
        key = 'test_list'
        pivot = 'pivot_value'
        value = 'test_value'

        result = await list_insert_before(key, pivot, value)
        assert 'Error: Cannot insert into list in readonly mode' in result
        mock_connection.linsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_insert_after_readonly(self, mock_connection, mock_context):
        """Test inserting after pivot in list in readonly mode."""
        key = 'test_list'
        pivot = 'pivot_value'
        value = 'test_value'

        result = await list_insert_after(key, pivot, value)
        assert 'Error: Cannot insert into list in readonly mode' in result
        mock_connection.linsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_remove_readonly(self, mock_connection, mock_context):
        """Test removing value from list in readonly mode."""
        key = 'test_list'
        value = 'test_value'

        result = await list_remove(key, value)
        assert 'Error: Cannot remove from list in readonly mode' in result
        mock_connection.lrem.assert_not_called()
