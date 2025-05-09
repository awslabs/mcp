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

"""Tests for the String functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.string import (
    string_append,
    string_decrement,
    string_get,
    string_increment,
    string_increment_float,
    string_length,
    string_set,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestString:
    """Tests for String operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch(
            'awslabs.valkey_mcp_server.tools.string.ValkeyConnectionManager'
        ) as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_string_set(self, mock_connection):
        """Test setting string value."""
        key = 'test_string'
        value = 'test_value'
        ex = 60
        px = None
        nx = True
        xx = False
        keepttl = False

        # Test successful set
        mock_connection.set.return_value = True
        result = await string_set(key, value, ex=ex, px=px, nx=nx, xx=xx, keepttl=keepttl)
        assert f"Successfully set value for key '{key}'" in result
        mock_connection.set.assert_called_with(
            key, value, ex=ex, px=px, nx=nx, xx=xx, keepttl=keepttl
        )

        # Test condition not met
        mock_connection.set.return_value = None
        result = await string_set(key, value)
        assert f"Failed to set value for key '{key}' (condition not met)" in result

        # Test error handling
        mock_connection.set.side_effect = ValkeyError('Test error')
        result = await string_set(key, value)
        assert f"Error setting string value for '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_string_get(self, mock_connection):
        """Test getting string value."""
        key = 'test_string'

        # Test successful get
        mock_connection.get.return_value = 'test_value'
        result = await string_get(key)
        assert 'test_value' in result
        mock_connection.get.assert_called_with(key)

        # Test key not found
        mock_connection.get.return_value = None
        result = await string_get(key)
        assert f"Key '{key}' not found" in result

        # Test error handling
        mock_connection.get.side_effect = ValkeyError('Test error')
        result = await string_get(key)
        assert f"Error getting string value from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_string_append(self, mock_connection):
        """Test appending to string."""
        key = 'test_string'
        value = '_suffix'

        # Test successful append
        mock_connection.append.return_value = 15
        result = await string_append(key, value)
        assert f"Successfully appended to key '{key}', new length: 15" in result
        mock_connection.append.assert_called_with(key, value)

        # Test error handling
        mock_connection.append.side_effect = ValkeyError('Test error')
        result = await string_append(key, value)
        assert f"Error appending to string '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_string_increment(self, mock_connection):
        """Test incrementing integer value."""
        key = 'test_string'
        amount = 5

        # Test successful increment
        mock_connection.incrby.return_value = 15
        result = await string_increment(key, amount)
        assert '15' in result
        mock_connection.incrby.assert_called_with(key, amount)

        # Test error handling
        mock_connection.incrby.side_effect = ValkeyError('Test error')
        result = await string_increment(key, amount)
        assert f"Error incrementing string '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_string_increment_float(self, mock_connection):
        """Test incrementing float value."""
        key = 'test_string'
        amount = 1.5

        # Test successful increment
        mock_connection.incrbyfloat.return_value = 3.5
        result = await string_increment_float(key, amount)
        assert '3.5' in result
        mock_connection.incrbyfloat.assert_called_with(key, amount)

        # Test error handling
        mock_connection.incrbyfloat.side_effect = ValkeyError('Test error')
        result = await string_increment_float(key, amount)
        assert f"Error incrementing float string '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_string_decrement(self, mock_connection):
        """Test decrementing integer value."""
        key = 'test_string'
        amount = 5

        # Test successful decrement
        mock_connection.decrby.return_value = 5
        result = await string_decrement(key, amount)
        assert '5' in result
        mock_connection.decrby.assert_called_with(key, amount)

        # Test error handling
        mock_connection.decrby.side_effect = ValkeyError('Test error')
        result = await string_decrement(key, amount)
        assert f"Error decrementing string '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_string_length(self, mock_connection):
        """Test getting string length."""
        key = 'test_string'

        # Test successful length retrieval
        mock_connection.strlen.return_value = 10
        result = await string_length(key)
        assert '10' in result
        mock_connection.strlen.assert_called_with(key)

        # Test error handling
        mock_connection.strlen.side_effect = ValkeyError('Test error')
        result = await string_length(key)
        assert f"Error getting string length for '{key}'" in result
        assert 'Test error' in result
