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

"""Tests for readonly mode in JSON functionality in the valkey MCP server."""

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


class TestJsonReadonly:
    """Tests for JSON operations in readonly mode."""

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
            mock_ctx.readonly_mode.return_value = True
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_json_set_readonly(self, mock_connection, mock_context):
        """Test setting JSON value in readonly mode."""
        key = 'test_json'
        path = '.'
        value = {'name': 'test'}

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_set(key, path, value)
        assert 'Error: Cannot set JSON value in readonly mode' in result
        mock_json.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_numincrby_readonly(self, mock_connection, mock_context):
        """Test incrementing number in JSON in readonly mode."""
        key = 'test_json'
        path = '.count'
        value = 5

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_numincrby(key, path, value)
        assert 'Error: Cannot increment JSON value in readonly mode' in result
        mock_json.numincrby.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_nummultby_readonly(self, mock_connection, mock_context):
        """Test multiplying number in JSON in readonly mode."""
        key = 'test_json'
        path = '.count'
        value = 2

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_nummultby(key, path, value)
        assert 'Error: Cannot multiply JSON value in readonly mode' in result
        mock_json.nummultby.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_strappend_readonly(self, mock_connection, mock_context):
        """Test appending to string in JSON in readonly mode."""
        key = 'test_json'
        path = '.name'
        value = '_suffix'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_strappend(key, path, value)
        assert 'Error: Cannot append to JSON string in readonly mode' in result
        mock_json.strappend.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_arrappend_readonly(self, mock_connection, mock_context):
        """Test appending to array in JSON in readonly mode."""
        key = 'test_json'
        path = '.items'
        values = ['item1', 'item2']

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_arrappend(key, path, *values)
        assert 'Error: Cannot append to JSON array in readonly mode' in result
        mock_json.arrappend.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_arrpop_readonly(self, mock_connection, mock_context):
        """Test popping from array in JSON in readonly mode."""
        key = 'test_json'
        path = '.items'
        index = -1

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_arrpop(key, path, index)
        assert 'Error: Cannot pop from JSON array in readonly mode' in result
        mock_json.arrpop.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_arrtrim_readonly(self, mock_connection, mock_context):
        """Test trimming array in JSON in readonly mode."""
        key = 'test_json'
        path = '.items'
        start = 0
        stop = 2

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_arrtrim(key, path, start, stop)
        assert 'Error: Cannot trim JSON array in readonly mode' in result
        mock_json.arrtrim.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_toggle_readonly(self, mock_connection, mock_context):
        """Test toggling boolean in JSON in readonly mode."""
        key = 'test_json'
        path = '.active'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_toggle(key, path)
        assert 'Error: Cannot toggle JSON boolean in readonly mode' in result
        mock_json.toggle.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_clear_readonly(self, mock_connection, mock_context):
        """Test clearing container in JSON in readonly mode."""
        key = 'test_json'
        path = '.items'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_clear(key, path)
        assert 'Error: Cannot clear JSON container in readonly mode' in result
        mock_json.clear.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_del_readonly(self, mock_connection, mock_context):
        """Test deleting value in JSON in readonly mode."""
        key = 'test_json'
        path = '.items[0]'

        # Unpack mock objects
        mock_conn, mock_json = mock_connection

        result = await json_del(key, path)
        assert 'Error: Cannot delete JSON value in readonly mode' in result
        mock_json.delete.assert_not_called()
