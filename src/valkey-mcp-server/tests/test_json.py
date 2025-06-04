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
    json_arrindex,
    json_arrlen,
    json_arrpop,
    json_arrtrim,
    json_clear,
    json_del,
    json_get,
    json_numincrby,
    json_nummultby,
    json_objkeys,
    json_objlen,
    json_set,
    json_strappend,
    json_strlen,
    json_toggle,
    json_type,
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
            yield mock_json

    @pytest.mark.asyncio
    async def test_json_set(self, mock_connection):
        """Test setting JSON values."""
        key = 'test_json'
        path = '$.name'
        value = 'test_value'

        # Test successful set
        mock_connection.set.return_value = True
        result = await json_set(key, path, value)
        assert f"Successfully set value at path '{path}' in '{key}'" in result
        mock_connection.set.assert_called_with(key, path, value)

        # Test failed set (path condition not met)
        mock_connection.set.return_value = False
        result = await json_set(key, path, value)
        assert 'Failed to set value' in result

        # Test error handling
        mock_connection.set.side_effect = ValkeyError('Test error')
        result = await json_set(key, path, value)
        assert f"Error setting JSON value in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_get(self, mock_connection):
        """Test getting JSON values."""
        key = 'test_json'
        path = '$.name'

        # Test successful get
        mock_connection.get.return_value = 'test_value'
        result = await json_get(key, path)
        assert 'test_value' in result
        mock_connection.get.assert_called_with(key, path)

        # Test value not found
        mock_connection.get.return_value = None
        result = await json_get(key, path)
        assert f"No value found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.get.side_effect = ValkeyError('Test error')
        result = await json_get(key, path)
        assert f"Error getting JSON value from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_type(self, mock_connection):
        """Test getting JSON value types."""
        key = 'test_json'
        path = '$.name'

        # Test successful type check
        mock_connection.type.return_value = 'string'
        result = await json_type(key, path)
        assert f"Type at path '{path}' in '{key}': string" in result
        mock_connection.type.assert_called_with(key, path)

        # Test value not found
        mock_connection.type.return_value = None
        result = await json_type(key, path)
        assert f"No value found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.type.side_effect = ValkeyError('Test error')
        result = await json_type(key, path)
        assert f"Error getting JSON type from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_numincrby(self, mock_connection):
        """Test incrementing numeric JSON values."""
        key = 'test_json'
        path = '$.count'
        value = 5

        # Test successful increment
        mock_connection.numincrby.return_value = 15
        result = await json_numincrby(key, path, value)
        assert f"Value at path '{path}' in '{key}' incremented to 15" in result
        mock_connection.numincrby.assert_called_with(key, path, value)

        # Test error handling
        mock_connection.numincrby.side_effect = ValkeyError('Test error')
        result = await json_numincrby(key, path, value)
        assert f"Error incrementing JSON value in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_nummultby(self, mock_connection):
        """Test multiplying numeric JSON values."""
        key = 'test_json'
        path = '$.count'
        value = 2

        # Test successful multiplication
        mock_connection.nummultby.return_value = 20
        result = await json_nummultby(key, path, value)
        assert f"Value at path '{path}' in '{key}' multiplied to 20" in result
        mock_connection.nummultby.assert_called_with(key, path, value)

        # Test error handling
        mock_connection.nummultby.side_effect = ValkeyError('Test error')
        result = await json_nummultby(key, path, value)
        assert f"Error multiplying JSON value in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_strappend(self, mock_connection):
        """Test appending to JSON strings."""
        key = 'test_json'
        path = '$.name'
        value = '_suffix'

        # Test successful append
        mock_connection.strappend.return_value = 15
        result = await json_strappend(key, path, value)
        assert f"String at path '{path}' in '{key}' appended, new length: 15" in result
        mock_connection.strappend.assert_called_with(key, path, value)

        # Test error handling
        mock_connection.strappend.side_effect = ValkeyError('Test error')
        result = await json_strappend(key, path, value)
        assert f"Error appending to JSON string in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_strlen(self, mock_connection):
        """Test getting JSON string lengths."""
        key = 'test_json'
        path = '$.name'

        # Test successful length check
        mock_connection.strlen.return_value = 10
        result = await json_strlen(key, path)
        assert f"Length of string at path '{path}' in '{key}': 10" in result
        mock_connection.strlen.assert_called_with(key, path)

        # Test string not found
        mock_connection.strlen.return_value = None
        result = await json_strlen(key, path)
        assert f"No string found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.strlen.side_effect = ValkeyError('Test error')
        result = await json_strlen(key, path)
        assert f"Error getting JSON string length from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_arrappend(self, mock_connection):
        """Test appending to JSON arrays."""
        key = 'test_json'
        path = '$.list'
        values = ['value1', 'value2']

        # Test successful append
        mock_connection.arrappend.return_value = 5
        result = await json_arrappend(key, path, *values)
        assert f"Array at path '{path}' in '{key}' appended, new length: 5" in result
        mock_connection.arrappend.assert_called_with(key, path, *values)

        # Test no values provided
        result = await json_arrappend(key, path)
        assert 'Error: at least one value is required' in result

        # Test error handling
        mock_connection.arrappend.side_effect = ValkeyError('Test error')
        result = await json_arrappend(key, path, *values)
        assert f"Error appending to JSON array in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_arrindex(self, mock_connection):
        """Test finding index in JSON arrays."""
        key = 'test_json'
        path = '$.list'
        value = 'test_value'

        # Test value found
        mock_connection.arrindex.return_value = 2
        result = await json_arrindex(key, path, value)
        assert f"Value found at index 2 in array at path '{path}' in '{key}'" in result
        mock_connection.arrindex.assert_called_with(key, path, value)

        # Test value not found
        mock_connection.arrindex.return_value = -1
        result = await json_arrindex(key, path, value)
        assert f"Value not found in array at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.arrindex.side_effect = ValkeyError('Test error')
        result = await json_arrindex(key, path, value)
        assert f"Error searching JSON array in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_arrlen(self, mock_connection):
        """Test getting JSON array lengths."""
        key = 'test_json'
        path = '$.list'

        # Test successful length check
        mock_connection.arrlen.return_value = 5
        result = await json_arrlen(key, path)
        assert f"Length of array at path '{path}' in '{key}': 5" in result
        mock_connection.arrlen.assert_called_with(key, path)

        # Test array not found
        mock_connection.arrlen.return_value = None
        result = await json_arrlen(key, path)
        assert f"No array found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.arrlen.side_effect = ValkeyError('Test error')
        result = await json_arrlen(key, path)
        assert f"Error getting JSON array length from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_arrpop(self, mock_connection):
        """Test popping from JSON arrays."""
        key = 'test_json'
        path = '$.list'
        index = -1

        # Test successful pop
        mock_connection.arrpop.return_value = 'popped_value'
        result = await json_arrpop(key, path, index)
        assert f"Popped value from index {index} in array at path '{path}' in '{key}'" in result
        mock_connection.arrpop.assert_called_with(key, path, index)

        # Test no value found
        mock_connection.arrpop.return_value = None
        result = await json_arrpop(key, path, index)
        assert f"No value found at index {index} in array at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.arrpop.side_effect = ValkeyError('Test error')
        result = await json_arrpop(key, path, index)
        assert f"Error popping from JSON array in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_arrtrim(self, mock_connection):
        """Test trimming JSON arrays."""
        key = 'test_json'
        path = '$.list'
        start = 0
        stop = 2

        # Test successful trim
        mock_connection.arrtrim.return_value = 3
        result = await json_arrtrim(key, path, start, stop)
        assert f"Array at path '{path}' in '{key}' trimmed to range [{start}, {stop}]" in result
        mock_connection.arrtrim.assert_called_with(key, path, start, stop)

        # Test error handling
        mock_connection.arrtrim.side_effect = ValkeyError('Test error')
        result = await json_arrtrim(key, path, start, stop)
        assert f"Error trimming JSON array in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_objkeys(self, mock_connection):
        """Test getting JSON object keys."""
        key = 'test_json'
        path = '$'

        # Test successful keys retrieval
        mock_connection.objkeys.return_value = ['key1', 'key2']
        result = await json_objkeys(key, path)
        assert f"Keys in object at path '{path}' in '{key}'" in result
        assert 'key1' in result and 'key2' in result
        mock_connection.objkeys.assert_called_with(key, path)

        # Test object not found
        mock_connection.objkeys.return_value = None
        result = await json_objkeys(key, path)
        assert f"No object found at path '{path}' in '{key}'" in result

        # Test empty object
        mock_connection.objkeys.return_value = []
        result = await json_objkeys(key, path)
        assert f"Object at path '{path}' in '{key}' has no keys" in result

        # Test error handling
        mock_connection.objkeys.side_effect = ValkeyError('Test error')
        result = await json_objkeys(key, path)
        assert f"Error getting JSON object keys from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_objlen(self, mock_connection):
        """Test getting JSON object lengths."""
        key = 'test_json'
        path = '$'

        # Test successful length check
        mock_connection.objlen.return_value = 5
        result = await json_objlen(key, path)
        assert f"Number of keys in object at path '{path}' in '{key}': 5" in result
        mock_connection.objlen.assert_called_with(key, path)

        # Test object not found
        mock_connection.objlen.return_value = None
        result = await json_objlen(key, path)
        assert f"No object found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.objlen.side_effect = ValkeyError('Test error')
        result = await json_objlen(key, path)
        assert f"Error getting JSON object length from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_toggle(self, mock_connection):
        """Test toggling JSON boolean values."""
        key = 'test_json'
        path = '$.flag'

        # Test successful toggle
        mock_connection.toggle.return_value = True
        result = await json_toggle(key, path)
        assert f"Boolean value at path '{path}' in '{key}' toggled to: true" in result
        mock_connection.toggle.assert_called_with(key, path)

        # Test value not found
        mock_connection.toggle.return_value = None
        result = await json_toggle(key, path)
        assert f"No boolean value found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.toggle.side_effect = ValkeyError('Test error')
        result = await json_toggle(key, path)
        assert f"Error toggling JSON boolean in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_clear(self, mock_connection):
        """Test clearing JSON containers."""
        key = 'test_json'
        path = '$'

        # Test successful clear
        mock_connection.clear.return_value = 1
        result = await json_clear(key, path)
        assert f"Successfully cleared container at path '{path}' in '{key}'" in result
        mock_connection.clear.assert_called_with(key, path)

        # Test container not found
        mock_connection.clear.return_value = 0
        result = await json_clear(key, path)
        assert f"No container found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.clear.side_effect = ValkeyError('Test error')
        result = await json_clear(key, path)
        assert f"Error clearing JSON container in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_del(self, mock_connection):
        """Test deleting JSON values."""
        key = 'test_json'
        path = '$.name'

        # Test successful delete
        mock_connection.delete.return_value = 1
        result = await json_del(key, path)
        assert f"Successfully deleted value at path '{path}' in '{key}'" in result
        mock_connection.delete.assert_called_with(key, path)

        # Test value not found
        mock_connection.delete.return_value = 0
        result = await json_del(key, path)
        assert f"No value found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_connection.delete.side_effect = ValkeyError('Test error')
        result = await json_del(key, path)
        assert f"Error deleting JSON value in '{key}'" in result
        assert 'Test error' in result
