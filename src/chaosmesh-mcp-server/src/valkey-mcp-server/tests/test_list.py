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

"""Tests for the List functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.list import (
    list_append,
    list_append_multiple,
    list_get,
    list_insert_after,
    list_insert_before,
    list_length,
    list_move,
    list_pop_left,
    list_pop_right,
    list_position,
    list_prepend_multiple,
    list_range,
    list_remove,
    list_set,
    list_trim,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestList:
    """Tests for List operations."""

    @pytest.mark.asyncio
    async def test_list_append(self, mock_connection):
        """Test appending value to list."""
        key = 'test_list'
        value = 'test_value'

        # Test successful append
        mock_connection.rpush.return_value = 1
        result = await list_append(key, value)
        assert f"Successfully appended value to list '{key}'" in result
        mock_connection.rpush.assert_called_with(key, value)

        # Test error handling
        mock_connection.rpush.side_effect = ValkeyError('Test error')
        result = await list_append(key, value)
        assert f"Error appending to list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_append_multiple(self, mock_connection):
        """Test appending multiple values to list."""
        key = 'test_list'
        values = ['value1', 'value2']

        # Test successful append
        mock_connection.rpush.return_value = 2
        result = await list_append_multiple(key, values)
        assert f"Successfully appended {len(values)} values to list '{key}'" in result
        mock_connection.rpush.assert_called_with(key, *values)

        # Test error handling
        mock_connection.rpush.side_effect = ValkeyError('Test error')
        result = await list_append_multiple(key, values)
        assert f"Error appending multiple values to list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_get(self, mock_connection):
        """Test getting value at index from list."""
        key = 'test_list'
        index = 1

        # Test successful get
        mock_connection.lindex.return_value = 'test_value'
        result = await list_get(key, index)
        assert 'test_value' in result
        mock_connection.lindex.assert_called_with(key, index)

        # Test value not found
        mock_connection.lindex.return_value = None
        result = await list_get(key, index)
        assert f"No value found at index {index} in list '{key}'" in result

        # Test error handling
        mock_connection.lindex.side_effect = ValkeyError('Test error')
        result = await list_get(key, index)
        assert f"Error getting value from list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_set(self, mock_connection):
        """Test setting value at index in list."""
        key = 'test_list'
        index = 1
        value = 'test_value'

        # Test successful set
        result = await list_set(key, index, value)
        assert f"Successfully set value at index {index} in list '{key}'" in result
        mock_connection.lset.assert_called_with(key, index, value)

        # Test error handling
        mock_connection.lset.side_effect = ValkeyError('Test error')
        result = await list_set(key, index, value)
        assert f"Error setting value in list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_range(self, mock_connection):
        """Test getting range of values from list."""
        key = 'test_list'
        start = 0
        stop = -1

        # Test successful range
        mock_connection.lrange.return_value = ['value1', 'value2']
        result = await list_range(key, start, stop)
        assert "['value1', 'value2']" in result
        mock_connection.lrange.assert_called_with(key, start, stop)

        # Test empty range
        mock_connection.lrange.return_value = []
        result = await list_range(key, start, stop)
        assert f"No values found in range [{start}, {stop}] in list '{key}'" in result

        # Test error handling
        mock_connection.lrange.side_effect = ValkeyError('Test error')
        result = await list_range(key, start, stop)
        assert f"Error getting range from list '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_list_move(self, mock_connection):
        """Test moving element between lists."""
        source = 'source_list'
        destination = 'dest_list'

        # Test successful move
        mock_connection.lmove.return_value = 'moved_value'
        result = await list_move(source, destination)
        assert "Successfully moved value 'moved_value'" in result
        mock_connection.lmove.assert_called_with(source, destination, 'LEFT', 'RIGHT')

        # Test with custom directions
        result = await list_move(source, destination, 'RIGHT', 'LEFT')
        mock_connection.lmove.assert_called_with(source, destination, 'RIGHT', 'LEFT')

        # Test invalid direction
        result = await list_move(source, destination, 'INVALID', 'RIGHT')
        assert "Error: wherefrom and whereto must be either 'LEFT' or 'RIGHT'" in result

        # Test empty source list
        mock_connection.lmove.return_value = None
        result = await list_move(source, destination)
        assert f"Source list '{source}' is empty" in result

        # Test error handling
        mock_connection.lmove.side_effect = ValkeyError('Test error')
        result = await list_move(source, destination)
        assert 'Error moving value between lists' in result
        assert 'Test error' in result

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
