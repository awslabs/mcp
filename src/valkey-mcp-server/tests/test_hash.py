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

"""Tests for the Hash functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.hash import (
    hash_exists,
    hash_get,
    hash_get_all,
    hash_increment,
    hash_keys,
    hash_length,
    hash_random_field,
    hash_random_field_with_values,
    hash_set,
    hash_set_if_not_exists,
    hash_set_multiple,
    hash_strlen,
    hash_values,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestHash:
    """Tests for Hash operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.hash.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_hash_set(self, mock_connection):
        """Test setting hash field."""
        key = 'test_hash'
        field = 'test_field'
        value = 'test_value'

        # Test successful set
        result = await hash_set(key, field, value)
        assert f"Successfully set field '{field}' in hash '{key}'" in result
        mock_connection.hset.assert_called_with(key, field, value)

        # Test error handling
        mock_connection.hset.side_effect = ValkeyError('Test error')
        result = await hash_set(key, field, value)
        assert f"Error setting hash field in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_set_multiple(self, mock_connection):
        """Test setting multiple hash fields."""
        key = 'test_hash'
        mapping = {'field1': 'value1', 'field2': 'value2'}

        # Test successful set
        mock_connection.hset.return_value = 2
        result = await hash_set_multiple(key, mapping)
        assert f"Successfully set 2 fields in hash '{key}'" in result
        mock_connection.hset.assert_called_with(key, mapping=mapping)

        # Test error handling
        mock_connection.hset.side_effect = ValkeyError('Test error')
        result = await hash_set_multiple(key, mapping)
        assert f"Error setting multiple hash fields in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_set_if_not_exists(self, mock_connection):
        """Test setting hash field if not exists."""
        key = 'test_hash'
        field = 'test_field'
        value = 'test_value'

        # Test successful set
        mock_connection.hsetnx.return_value = True
        result = await hash_set_if_not_exists(key, field, value)
        assert f"Successfully set field '{field}' in hash '{key}'" in result
        mock_connection.hsetnx.assert_called_with(key, field, value)

        # Test field already exists
        mock_connection.hsetnx.return_value = False
        result = await hash_set_if_not_exists(key, field, value)
        assert f"Field '{field}' already exists in hash '{key}'" in result

        # Test error handling
        mock_connection.hsetnx.side_effect = ValkeyError('Test error')
        result = await hash_set_if_not_exists(key, field, value)
        assert f"Error setting hash field in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_get(self, mock_connection):
        """Test getting hash field."""
        key = 'test_hash'
        field = 'test_field'

        # Test successful get
        mock_connection.hget.return_value = 'test_value'
        result = await hash_get(key, field)
        assert 'test_value' in result
        mock_connection.hget.assert_called_with(key, field)

        # Test field not found
        mock_connection.hget.return_value = None
        result = await hash_get(key, field)
        assert f"Field '{field}' not found in hash '{key}'" in result

        # Test error handling
        mock_connection.hget.side_effect = ValkeyError('Test error')
        result = await hash_get(key, field)
        assert f"Error getting hash field from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_get_all(self, mock_connection):
        """Test getting all hash fields."""
        key = 'test_hash'

        # Test successful get
        mock_connection.hgetall.return_value = {'field1': 'value1', 'field2': 'value2'}
        result = await hash_get_all(key)
        assert 'field1' in result and 'value1' in result
        mock_connection.hgetall.assert_called_with(key)

        # Test empty hash
        mock_connection.hgetall.return_value = {}
        result = await hash_get_all(key)
        assert f"No fields found in hash '{key}'" in result

        # Test error handling
        mock_connection.hgetall.side_effect = ValkeyError('Test error')
        result = await hash_get_all(key)
        assert f"Error getting all hash fields from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_exists(self, mock_connection):
        """Test checking hash field existence."""
        key = 'test_hash'
        field = 'test_field'

        # Test field exists
        mock_connection.hexists.return_value = True
        result = await hash_exists(key, field)
        assert 'true' in result
        mock_connection.hexists.assert_called_with(key, field)

        # Test field does not exist
        mock_connection.hexists.return_value = False
        result = await hash_exists(key, field)
        assert 'false' in result

        # Test error handling
        mock_connection.hexists.side_effect = ValkeyError('Test error')
        result = await hash_exists(key, field)
        assert f"Error checking hash field existence in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_increment(self, mock_connection):
        """Test incrementing hash field."""
        key = 'test_hash'
        field = 'test_field'

        # Test integer increment
        mock_connection.hincrby.return_value = 2
        result = await hash_increment(key, field, 1)
        assert '2' in result
        mock_connection.hincrby.assert_called_with(key, field, 1)

        # Test float increment
        mock_connection.hincrbyfloat.return_value = 2.5
        result = await hash_increment(key, field, 1.5)
        assert '2.5' in result
        mock_connection.hincrbyfloat.assert_called_with(key, field, 1.5)

        # Test error handling
        mock_connection.hincrby.side_effect = ValkeyError('Test error')
        result = await hash_increment(key, field)
        assert f"Error incrementing hash field in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_keys(self, mock_connection):
        """Test getting hash keys."""
        key = 'test_hash'

        # Test successful get
        mock_connection.hkeys.return_value = ['field1', 'field2']
        result = await hash_keys(key)
        assert 'field1' in result and 'field2' in result
        mock_connection.hkeys.assert_called_with(key)

        # Test no fields
        mock_connection.hkeys.return_value = []
        result = await hash_keys(key)
        assert f"No fields found in hash '{key}'" in result

        # Test error handling
        mock_connection.hkeys.side_effect = ValkeyError('Test error')
        result = await hash_keys(key)
        assert f"Error getting hash field names from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_length(self, mock_connection):
        """Test getting hash length."""
        key = 'test_hash'

        # Test successful get
        mock_connection.hlen.return_value = 2
        result = await hash_length(key)
        assert '2' in result
        mock_connection.hlen.assert_called_with(key)

        # Test error handling
        mock_connection.hlen.side_effect = ValkeyError('Test error')
        result = await hash_length(key)
        assert f"Error getting hash length from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_random_field(self, mock_connection):
        """Test getting random hash field."""
        key = 'test_hash'

        # Test single field
        mock_connection.hrandfield.return_value = 'field1'
        result = await hash_random_field(key)
        assert 'field1' in result
        mock_connection.hrandfield.assert_called_with(key)

        # Test multiple fields
        mock_connection.hrandfield.return_value = ['field1', 'field2']
        result = await hash_random_field(key, 2)
        assert 'field1' in result and 'field2' in result
        mock_connection.hrandfield.assert_called_with(key, 2)

        # Test no fields
        mock_connection.hrandfield.return_value = None
        result = await hash_random_field(key)
        assert f"No fields found in hash '{key}'" in result

        # Test error handling
        mock_connection.hrandfield.side_effect = ValkeyError('Test error')
        result = await hash_random_field(key)
        assert f"Error getting random hash field from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_random_field_with_values(self, mock_connection):
        """Test getting random hash field with values."""
        key = 'test_hash'
        count = 2

        # Test successful get
        mock_connection.hrandfield.return_value = {'field1': 'value1', 'field2': 'value2'}
        result = await hash_random_field_with_values(key, count)
        assert 'field1' in result and 'value1' in result
        mock_connection.hrandfield.assert_called_with(key, count, withvalues=True)

        # Test no fields
        mock_connection.hrandfield.return_value = {}
        result = await hash_random_field_with_values(key, count)
        assert f"No fields found in hash '{key}'" in result

        # Test error handling
        mock_connection.hrandfield.side_effect = ValkeyError('Test error')
        result = await hash_random_field_with_values(key, count)
        assert f"Error getting random hash field-value pairs from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_strlen(self, mock_connection):
        """Test getting hash field value length."""
        key = 'test_hash'
        field = 'test_field'

        # Test successful get
        mock_connection.hstrlen.return_value = 10
        result = await hash_strlen(key, field)
        assert '10' in result
        mock_connection.hstrlen.assert_called_with(key, field)

        # Test error handling
        mock_connection.hstrlen.side_effect = ValkeyError('Test error')
        result = await hash_strlen(key, field)
        assert f"Error getting hash field value length from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_hash_values(self, mock_connection):
        """Test getting hash values."""
        key = 'test_hash'

        # Test successful get
        mock_connection.hvals.return_value = ['value1', 'value2']
        result = await hash_values(key)
        assert 'value1' in result and 'value2' in result
        mock_connection.hvals.assert_called_with(key)

        # Test no values
        mock_connection.hvals.return_value = []
        result = await hash_values(key)
        assert f"No values found in hash '{key}'" in result

        # Test error handling
        mock_connection.hvals.side_effect = ValkeyError('Test error')
        result = await hash_values(key)
        assert f"Error getting hash values from '{key}'" in result
        assert 'Test error' in result
