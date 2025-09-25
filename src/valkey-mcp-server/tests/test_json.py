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

"""Tests for the JSON functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.json import (
    json_arrappend,
    json_arrpop,
    json_arrtrim,
    json_clear,
    json_del,
    json_numincrby,
    json_nummultby,
    json_set,
    json_strappend,
    json_toggle,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestJson:
    """Tests for JSON operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.json.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_json = Mock()
            mock_conn.json.return_value = mock_json
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn, mock_json

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context."""
        with patch('awslabs.valkey_mcp_server.tools.json.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = False
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_json_set(self, mock_connection, mock_context):
        """Test setting JSON value."""
        key = 'test_json'
        path = '.'
        value = {'name': 'test'}

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful set
        mock_context.readonly_mode.return_value = False
        mock_json.set.return_value = True
        result = await json_set(key, path, value)
        assert f"Successfully set value at path '{path}' in '{key}'" in result
        mock_json.set.assert_called_with(key, path, value, nx=False, xx=False)

        # Test condition not met
        mock_json.set.return_value = None
        result = await json_set(key, path, value)
        assert f"Failed to set value at path '{path}' in '{key}'" in result

        # Test error handling
        mock_json.set.side_effect = ValkeyError('Test error')
        result = await json_set(key, path, value)
        assert f"Error setting JSON value in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.set.reset_mock()
        mock_json.set.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_set(key, path, value)
        assert 'Error: Cannot set JSON value in readonly mode' in result
        mock_json.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_numincrby(self, mock_connection, mock_context):
        """Test incrementing number in JSON."""
        key = 'test_json'
        path = '.count'
        value = 5

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful increment
        mock_context.readonly_mode.return_value = False
        mock_json.numincrby.return_value = 15
        result = await json_numincrby(key, path, value)
        assert f"Value at path '{path}' in '{key}' incremented to 15" in result
        mock_json.numincrby.assert_called_with(key, path, value)

        # Test error handling
        mock_json.numincrby.side_effect = ValkeyError('Test error')
        result = await json_numincrby(key, path, value)
        assert f"Error incrementing JSON value in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.numincrby.reset_mock()
        mock_json.numincrby.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_numincrby(key, path, value)
        assert 'Error: Cannot increment JSON value in readonly mode' in result
        mock_json.numincrby.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_nummultby(self, mock_connection, mock_context):
        """Test multiplying number in JSON."""
        key = 'test_json'
        path = '.count'
        value = 2

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful multiply
        mock_context.readonly_mode.return_value = False
        mock_json.nummultby.return_value = 10
        result = await json_nummultby(key, path, value)
        assert f"Value at path '{path}' in '{key}' multiplied to 10" in result
        mock_json.nummultby.assert_called_with(key, path, value)

        # Test error handling
        mock_json.nummultby.side_effect = ValkeyError('Test error')
        result = await json_nummultby(key, path, value)
        assert f"Error multiplying JSON value in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.nummultby.reset_mock()
        mock_json.nummultby.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_nummultby(key, path, value)
        assert 'Error: Cannot multiply JSON value in readonly mode' in result
        mock_json.nummultby.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_strappend(self, mock_connection, mock_context):
        """Test appending to string in JSON."""
        key = 'test_json'
        path = '.name'
        value = '_suffix'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful append
        mock_context.readonly_mode.return_value = False
        mock_json.strappend.return_value = 10
        result = await json_strappend(key, path, value)
        assert f"String at path '{path}' in '{key}' appended, new length: 10" in result
        mock_json.strappend.assert_called_with(key, path, value)

        # Test error handling
        mock_json.strappend.side_effect = ValkeyError('Test error')
        result = await json_strappend(key, path, value)
        assert f"Error appending to JSON string in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.strappend.reset_mock()
        mock_json.strappend.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_strappend(key, path, value)
        assert 'Error: Cannot append to JSON string in readonly mode' in result
        mock_json.strappend.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_arrappend(self, mock_connection, mock_context):
        """Test appending to array in JSON."""
        key = 'test_json'
        path = '.items'
        values = ['item1', 'item2']

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful append
        mock_context.readonly_mode.return_value = False
        mock_json.arrappend.return_value = 3
        result = await json_arrappend(key, path, *values)
        assert f"Array at path '{path}' in '{key}' appended, new length: 3" in result
        mock_json.arrappend.assert_called_with(key, path, *values)

        # Test error handling
        mock_json.arrappend.side_effect = ValkeyError('Test error')
        result = await json_arrappend(key, path, *values)
        assert f"Error appending to JSON array in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.arrappend.reset_mock()
        mock_json.arrappend.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_arrappend(key, path, *values)
        assert 'Error: Cannot append to JSON array in readonly mode' in result
        mock_json.arrappend.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_arrpop(self, mock_connection, mock_context):
        """Test popping from array in JSON."""
        key = 'test_json'
        path = '.items'
        index = -1

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful pop
        mock_context.readonly_mode.return_value = False
        mock_json.arrpop.return_value = 'item1'
        result = await json_arrpop(key, path, index)
        assert f"Popped value from index {index} in array at path '{path}' in '{key}'" in result
        mock_json.arrpop.assert_called_with(key, path, index)

        # Test error handling
        mock_json.arrpop.side_effect = ValkeyError('Test error')
        result = await json_arrpop(key, path, index)
        assert f"Error popping from JSON array in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.arrpop.reset_mock()
        mock_json.arrpop.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_arrpop(key, path, index)
        assert 'Error: Cannot pop from JSON array in readonly mode' in result
        mock_json.arrpop.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_arrtrim(self, mock_connection, mock_context):
        """Test trimming array in JSON."""
        key = 'test_json'
        path = '.items'
        start = 0
        stop = 2

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful trim
        mock_context.readonly_mode.return_value = False
        mock_json.arrtrim.return_value = 3
        result = await json_arrtrim(key, path, start, stop)
        assert f"Array at path '{path}' in '{key}' trimmed to range [{start}, {stop}]" in result
        mock_json.arrtrim.assert_called_with(key, path, start, stop)

        # Test error handling
        mock_json.arrtrim.side_effect = ValkeyError('Test error')
        result = await json_arrtrim(key, path, start, stop)
        assert f"Error trimming JSON array in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.arrtrim.reset_mock()
        mock_json.arrtrim.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_arrtrim(key, path, start, stop)
        assert 'Error: Cannot trim JSON array in readonly mode' in result
        mock_json.arrtrim.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_toggle(self, mock_connection, mock_context):
        """Test toggling boolean in JSON."""
        key = 'test_json'
        path = '.active'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful toggle
        mock_context.readonly_mode.return_value = False
        mock_json.toggle.return_value = True
        result = await json_toggle(key, path)
        assert f"Boolean value at path '{path}' in '{key}' toggled to: true" in result
        mock_json.toggle.assert_called_with(key, path)

        # Test error handling
        mock_json.toggle.side_effect = ValkeyError('Test error')
        result = await json_toggle(key, path)
        assert f"Error toggling JSON boolean in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.toggle.reset_mock()
        mock_json.toggle.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_toggle(key, path)
        assert 'Error: Cannot toggle JSON boolean in readonly mode' in result
        mock_json.toggle.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_clear(self, mock_connection, mock_context):
        """Test clearing container in JSON."""
        key = 'test_json'
        path = '.items'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful clear
        mock_context.readonly_mode.return_value = False
        mock_json.clear.return_value = 1
        result = await json_clear(key, path)
        assert f"Successfully cleared container at path '{path}' in '{key}'" in result
        mock_json.clear.assert_called_with(key, path)

        # Test error handling
        mock_json.clear.side_effect = ValkeyError('Test error')
        result = await json_clear(key, path)
        assert f"Error clearing JSON container in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.clear.reset_mock()
        mock_json.clear.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_clear(key, path)
        assert 'Error: Cannot clear JSON container in readonly mode' in result
        mock_json.clear.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_del(self, mock_connection, mock_context):
        """Test deleting value in JSON."""
        key = 'test_json'
        path = '.items[0]'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful delete
        mock_context.readonly_mode.return_value = False
        mock_json.delete.return_value = 1
        result = await json_del(key, path)
        assert f"Successfully deleted value at path '{path}' in '{key}'" in result
        mock_json.delete.assert_called_with(key, path)

        # Test error handling
        mock_json.delete.side_effect = ValkeyError('Test error')
        result = await json_del(key, path)
        assert f"Error deleting JSON value in '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_json.delete.reset_mock()
        mock_json.delete.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await json_del(key, path)
        assert 'Error: Cannot delete JSON value in readonly mode' in result
        mock_json.delete.assert_not_called()
