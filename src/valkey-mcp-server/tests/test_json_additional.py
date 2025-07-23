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

"""Additional tests for the JSON functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.json import (
    json_arrindex,
    json_arrlen,
    json_get,
    json_objkeys,
    json_objlen,
    json_strlen,
    json_type,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestJsonAdditional:
    """Additional tests for JSON operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.json.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_json = Mock()
            mock_conn.json.return_value = mock_json
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn, mock_json

    @pytest.mark.asyncio
    async def test_json_get(self, mock_connection):
        """Test getting JSON value."""
        key = 'test_json'
        path = '.'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful get with path
        mock_json.get.return_value = {'name': 'test'}
        result = await json_get(key, path)
        assert "{'name': 'test'}" in result
        mock_json.get.assert_called_with(key, path)

        # Test successful get without path
        mock_json.get.return_value = {'name': 'test'}
        result = await json_get(key)
        assert "{'name': 'test'}" in result
        mock_json.get.assert_called_with(key)

        # Test with formatting options
        mock_json.get.reset_mock()
        result = await json_get(key, path, indent=2, newline=True, space=True)
        mock_json.get.assert_called_with(key, path, indent=2, newline=True, space=True)

        # Test value not found
        mock_json.get.return_value = None
        result = await json_get(key, path)
        assert f"No value found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_json.get.side_effect = ValkeyError('Test error')
        result = await json_get(key, path)
        assert f"Error getting JSON value from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_type(self, mock_connection):
        """Test getting JSON type."""
        key = 'test_json'
        path = '.name'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful type with path
        mock_json.type.return_value = 'string'
        result = await json_type(key, path)
        assert f"Type at path '{path}' in '{key}': string" in result
        mock_json.type.assert_called_with(key, path)

        # Test successful type without path
        mock_json.type.return_value = 'object'
        result = await json_type(key)
        assert f"Type at path '.' in '{key}': object" in result
        mock_json.type.assert_called_with(key)

        # Test value not found
        mock_json.type.return_value = None
        result = await json_type(key, path)
        assert f"No value found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_json.type.side_effect = ValkeyError('Test error')
        result = await json_type(key, path)
        assert f"Error getting JSON type from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_strlen(self, mock_connection):
        """Test getting JSON string length."""
        key = 'test_json'
        path = '.name'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful strlen
        mock_json.strlen.return_value = 10
        result = await json_strlen(key, path)
        assert f"Length of string at path '{path}' in '{key}': 10" in result
        mock_json.strlen.assert_called_with(key, path)

        # Test value not found
        mock_json.strlen.return_value = None
        result = await json_strlen(key, path)
        assert f"No string found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_json.strlen.side_effect = ValkeyError('Test error')
        result = await json_strlen(key, path)
        assert f"Error getting JSON string length from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_arrindex(self, mock_connection):
        """Test finding index in JSON array."""
        key = 'test_json'
        path = '.items'
        value = 'test_value'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful index search
        mock_json.arrindex.return_value = 2
        result = await json_arrindex(key, path, value)
        assert f"Value found at index 2 in array at path '{path}' in '{key}'" in result
        mock_json.arrindex.assert_called_with(key, path, value)

        # Test with start
        mock_json.arrindex.reset_mock()
        result = await json_arrindex(key, path, value, start=1)
        mock_json.arrindex.assert_called_with(key, path, value, 1)

        # Test with start and stop
        mock_json.arrindex.reset_mock()
        result = await json_arrindex(key, path, value, start=1, stop=5)
        mock_json.arrindex.assert_called_with(key, path, value, 1, 5)

        # Test value not found
        mock_json.arrindex.return_value = -1
        result = await json_arrindex(key, path, value)
        assert f"Value not found in array at path '{path}' in '{key}'" in result

        # Test value not found with range
        mock_json.arrindex.return_value = -1
        result = await json_arrindex(key, path, value, start=1, stop=5)
        assert f"Value not found in array at path '{path}' in '{key}' in range [1, 5]" in result

        # Test error handling
        mock_json.arrindex.side_effect = ValkeyError('Test error')
        result = await json_arrindex(key, path, value)
        assert f"Error searching JSON array in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_arrlen(self, mock_connection):
        """Test getting JSON array length."""
        key = 'test_json'
        path = '.items'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful arrlen
        mock_json.arrlen.return_value = 5
        result = await json_arrlen(key, path)
        assert f"Length of array at path '{path}' in '{key}': 5" in result
        mock_json.arrlen.assert_called_with(key, path)

        # Test value not found
        mock_json.arrlen.return_value = None
        result = await json_arrlen(key, path)
        assert f"No array found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_json.arrlen.side_effect = ValkeyError('Test error')
        result = await json_arrlen(key, path)
        assert f"Error getting JSON array length from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_objkeys(self, mock_connection):
        """Test getting JSON object keys."""
        key = 'test_json'
        path = '.'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful objkeys
        mock_json.objkeys.return_value = ['name', 'age', 'city']
        result = await json_objkeys(key, path)
        assert f"Keys in object at path '{path}' in '{key}': name, age, city" in result
        mock_json.objkeys.assert_called_with(key, path)

        # Test empty object
        mock_json.objkeys.return_value = []
        result = await json_objkeys(key, path)
        assert f"Object at path '{path}' in '{key}' has no keys" in result

        # Test value not found
        mock_json.objkeys.return_value = None
        result = await json_objkeys(key, path)
        assert f"No object found at path '{path}' in '{key}'" in result

        # Test with None values in keys (should be filtered out)
        mock_json.objkeys.return_value = ['name', None, 'city']
        result = await json_objkeys(key, path)
        assert f"Keys in object at path '{path}' in '{key}': name, city" in result

        # Test error handling
        mock_json.objkeys.side_effect = ValkeyError('Test error')
        result = await json_objkeys(key, path)
        assert f"Error getting JSON object keys from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_json_objlen(self, mock_connection):
        """Test getting JSON object length."""
        key = 'test_json'
        path = '.'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        # Test successful objlen
        mock_json.objlen.return_value = 3
        result = await json_objlen(key, path)
        assert f"Number of keys in object at path '{path}' in '{key}': 3" in result
        mock_json.objlen.assert_called_with(key, path)

        # Test value not found
        mock_json.objlen.return_value = None
        result = await json_objlen(key, path)
        assert f"No object found at path '{path}' in '{key}'" in result

        # Test error handling
        mock_json.objlen.side_effect = ValkeyError('Test error')
        result = await json_objlen(key, path)
        assert f"Error getting JSON object length from '{key}'" in result
        assert 'Test error' in result
