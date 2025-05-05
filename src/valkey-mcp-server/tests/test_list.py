# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the List functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.list import (
    list_insert_after,
    list_insert_before,
    list_length,
    list_move_blocking,
    list_pop_blocking,
    list_pop_left,
    list_pop_push_blocking,
    list_pop_right,
    list_position,
    list_prepend_multiple,
    list_remove,
    list_trim,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestList:
    """Tests for List operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.list.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_list_prepend_multiple(self, mock_connection):
        """Test prepending multiple values to list."""
        key = 'test_list'
        values = ['value1', 'value2']

        # Test successful prepend
        mock_connection.lpush.return_value = 2
        result = await list_prepend_multiple(key, values)
        assert f"Successfully prepended {len(values)} values to list '{key}'" in result
        mock_connection.lpush.assert_called_with(key, *values)

        # Test error handling
        mock_connection.lpush.side_effect = ValkeyError('Test error')
        result = await list_prepend_multiple(key, values)
        assert f"Error prepending multiple values to list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_trim(self, mock_connection):
        """Test trimming list."""
        key = 'test_list'
        start = 0
        stop = 5

        # Test successful trim
        result = await list_trim(key, start, stop)
        assert f"Successfully trimmed list '{key}' to range [{start}, {stop}]" in result
        mock_connection.ltrim.assert_called_with(key, start, stop)

        # Test error handling
        mock_connection.ltrim.side_effect = ValkeyError('Test error')
        result = await list_trim(key, start, stop)
        assert f"Error trimming list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_length(self, mock_connection):
        """Test getting list length."""
        key = 'test_list'

        # Test successful length retrieval
        mock_connection.llen.return_value = 5
        result = await list_length(key)
        assert result == '5'
        mock_connection.llen.assert_called_with(key)

        # Test error handling
        mock_connection.llen.side_effect = ValkeyError('Test error')
        result = await list_length(key)
        assert f"Error getting list length for '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_pop_left_with_count(self, mock_connection):
        """Test popping multiple values from left of list."""
        key = 'test_list'
        count = 2

        # Test successful pop with count
        mock_connection.lpop.return_value = ['value1', 'value2']
        result = await list_pop_left(key, count)
        assert 'value1' in result and 'value2' in result
        mock_connection.lpop.assert_called_with(key, count)

    @pytest.mark.asyncio
    async def test_list_pop_right(self, mock_connection):
        """Test popping from right of list."""
        key = 'test_list'

        # Test successful pop
        mock_connection.rpop.return_value = 'test_value'
        result = await list_pop_right(key)
        assert 'test_value' in result
        mock_connection.rpop.assert_called_with(key)

        # Test pop with count
        count = 2
        mock_connection.rpop.return_value = ['value1', 'value2']
        result = await list_pop_right(key, count)
        assert 'value1' in result and 'value2' in result
        mock_connection.rpop.assert_called_with(key, count)

        # Test empty list
        mock_connection.rpop.return_value = None
        result = await list_pop_right(key)
        assert f"List '{key}' is empty" in result

        # Test error handling
        mock_connection.rpop.side_effect = ValkeyError('Test error')
        result = await list_pop_right(key)
        assert f"Error popping from right of list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_position_with_options(self, mock_connection):
        """Test finding position with various options."""
        key = 'test_list'
        value = 'test_value'

        # Test with rank
        mock_connection.lpos.return_value = 2
        result = await list_position(key, value, rank=1)
        assert '2' in result
        mock_connection.lpos.assert_called_with(key, value, rank=1)

        # Test with count
        mock_connection.lpos.return_value = [0, 2, 4]
        result = await list_position(key, value, count=3)
        assert '[0, 2, 4]' in result
        mock_connection.lpos.assert_called_with(key, value, count=3)

        # Test with maxlen
        mock_connection.lpos.return_value = 0
        result = await list_position(key, value, maxlen=10)
        assert '0' in result
        mock_connection.lpos.assert_called_with(key, value, maxlen=10)

        # Test value not found
        mock_connection.lpos.return_value = None
        result = await list_position(key, value)
        assert f"Value not found in list '{key}'" in result

        # Test error handling
        mock_connection.lpos.side_effect = ValkeyError('Test error')
        result = await list_position(key, value)
        assert f"Error finding position in list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_move_blocking(self, mock_connection):
        """Test blocking move between lists."""
        source = 'source_list'
        destination = 'dest_list'
        wherefrom = 'LEFT'
        whereto = 'RIGHT'
        timeout = 1.0

        # Test successful move
        mock_connection.blmove.return_value = 'test_value'
        result = await list_move_blocking(source, destination, wherefrom, whereto, timeout)
        assert "Successfully moved value 'test_value'" in result
        mock_connection.blmove.assert_called_with(source, destination, wherefrom, whereto, timeout)

        # Test timeout
        mock_connection.blmove.return_value = None
        result = await list_move_blocking(source, destination, wherefrom, whereto, timeout)
        assert f"Timeout waiting for value in source list '{source}'" in result

        # Test invalid direction
        result = await list_move_blocking(source, destination, 'INVALID', whereto, timeout)
        assert "Error: wherefrom and whereto must be either 'LEFT' or 'RIGHT'" in result

        # Test error handling
        mock_connection.blmove.side_effect = ValkeyError('Test error')
        result = await list_move_blocking(source, destination, wherefrom, whereto, timeout)
        assert 'Error moving value between lists' in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_pop_blocking_right(self, mock_connection):
        """Test blocking pop from right side."""
        key = 'test_list'
        timeout = 1.0

        # Test successful pop from right
        mock_connection.brpop.return_value = (key, 'test_value')
        result = await list_pop_blocking(key, timeout, 'RIGHT')
        assert "Successfully popped value 'test_value'" in result
        mock_connection.brpop.assert_called_with(key, timeout)

        # Test invalid side
        result = await list_pop_blocking(key, timeout, 'INVALID')
        assert "Error: side must be either 'LEFT' or 'RIGHT'" in result

    @pytest.mark.asyncio
    async def test_list_pop_push_blocking(self, mock_connection):
        """Test blocking pop and push between lists."""
        source = 'source_list'
        destination = 'dest_list'
        timeout = 1.0

        # Test successful move
        mock_connection.brpoplpush.return_value = 'test_value'
        result = await list_pop_push_blocking(source, destination, timeout)
        assert (
            f"Successfully moved value 'test_value' from '{source}' to '{destination}'" in result
        )
        mock_connection.brpoplpush.assert_called_with(source, destination, timeout)

        # Test timeout
        mock_connection.brpoplpush.return_value = None
        result = await list_pop_push_blocking(source, destination, timeout)
        assert f"Timeout waiting for value in source list '{source}'" in result

        # Test error handling
        mock_connection.brpoplpush.side_effect = ValkeyError('Test error')
        result = await list_pop_push_blocking(source, destination, timeout)
        assert 'Error moving value between lists' in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_insert_before(self, mock_connection):
        """Test inserting value before pivot."""
        key = 'test_list'
        pivot = 'pivot_value'
        value = 'test_value'

        # Test successful insert
        mock_connection.linsert.return_value = 3
        result = await list_insert_before(key, pivot, value)
        assert f"Successfully inserted value before pivot in list '{key}'" in result
        mock_connection.linsert.assert_called_with(key, 'BEFORE', pivot, value)

        # Test pivot not found
        mock_connection.linsert.return_value = -1
        result = await list_insert_before(key, pivot, value)
        assert f"Pivot value not found in list '{key}'" in result

        # Test error handling
        mock_connection.linsert.side_effect = ValkeyError('Test error')
        result = await list_insert_before(key, pivot, value)
        assert f"Error inserting before pivot in list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_insert_after(self, mock_connection):
        """Test inserting value after pivot."""
        key = 'test_list'
        pivot = 'pivot_value'
        value = 'test_value'

        # Test successful insert
        mock_connection.linsert.return_value = 3
        result = await list_insert_after(key, pivot, value)
        assert f"Successfully inserted value after pivot in list '{key}'" in result
        mock_connection.linsert.assert_called_with(key, 'AFTER', pivot, value)

        # Test pivot not found
        mock_connection.linsert.return_value = -1
        result = await list_insert_after(key, pivot, value)
        assert f"Pivot value not found in list '{key}'" in result

        # Test error handling
        mock_connection.linsert.side_effect = ValkeyError('Test error')
        result = await list_insert_after(key, pivot, value)
        assert f"Error inserting after pivot in list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_remove(self, mock_connection):
        """Test removing values from list."""
        key = 'test_list'
        value = 'test_value'
        count = 2

        # Test successful remove
        mock_connection.lrem.return_value = 2
        result = await list_remove(key, value, count)
        assert f"Successfully removed 2 occurrence(s) of value from list '{key}'" in result
        mock_connection.lrem.assert_called_with(key, count, value)

        # Test error handling
        mock_connection.lrem.side_effect = ValkeyError('Test error')
        result = await list_remove(key, value, count)
        assert f"Error removing value from list '{key}'" in result
        assert 'Test error' in result
