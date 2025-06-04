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

"""Tests for the Set functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.set import (
    set_add,
    set_cardinality,
    set_contains,
    set_members,
    set_move,
    set_pop,
    set_random_member,
    set_remove,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestSet:
    """Tests for Set operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch('awslabs.valkey_mcp_server.tools.set.ValkeyConnectionManager') as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_set_add(self, mock_connection):
        """Test adding member to set."""
        key = 'test_set'
        member = 'test_member'

        # Test successful add
        mock_connection.sadd.return_value = 1
        result = await set_add(key, member)
        assert f"Successfully added 1 new member to set '{key}'" in result
        mock_connection.sadd.assert_called_with(key, member)

        # Test error handling
        mock_connection.sadd.side_effect = ValkeyError('Test error')
        result = await set_add(key, member)
        assert f"Error adding to set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_set_remove(self, mock_connection):
        """Test removing member from set."""
        key = 'test_set'
        member = 'test_member'

        # Test successful remove
        mock_connection.srem.return_value = 1
        result = await set_remove(key, member)
        assert f"Successfully removed 1 member from set '{key}'" in result
        mock_connection.srem.assert_called_with(key, member)

        # Test error handling
        mock_connection.srem.side_effect = ValkeyError('Test error')
        result = await set_remove(key, member)
        assert f"Error removing from set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_set_pop(self, mock_connection):
        """Test popping member from set."""
        key = 'test_set'

        # Test successful pop
        mock_connection.spop.return_value = 'test_member'
        result = await set_pop(key)
        assert 'test_member' in result
        mock_connection.spop.assert_called_with(key)

        # Test empty set
        mock_connection.spop.return_value = None
        result = await set_pop(key)
        assert f"Set '{key}' is empty" in result

        # Test error handling
        mock_connection.spop.side_effect = ValkeyError('Test error')
        result = await set_pop(key)
        assert f"Error popping from set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_set_move(self, mock_connection):
        """Test moving member between sets."""
        source = 'source_set'
        destination = 'dest_set'
        member = 'test_member'

        # Test successful move
        mock_connection.smove.return_value = True
        result = await set_move(source, destination, member)
        assert f"Successfully moved member from set '{source}' to '{destination}'" in result
        mock_connection.smove.assert_called_with(source, destination, member)

        # Test member not found
        mock_connection.smove.return_value = False
        result = await set_move(source, destination, member)
        assert f"Member not found in source set '{source}'" in result

        # Test error handling
        mock_connection.smove.side_effect = ValkeyError('Test error')
        result = await set_move(source, destination, member)
        assert 'Error moving between sets' in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_set_cardinality(self, mock_connection):
        """Test getting set cardinality."""
        key = 'test_set'

        # Test successful get
        mock_connection.scard.return_value = 3
        result = await set_cardinality(key)
        assert '3' in result
        mock_connection.scard.assert_called_with(key)

        # Test error handling
        mock_connection.scard.side_effect = ValkeyError('Test error')
        result = await set_cardinality(key)
        assert f"Error getting set cardinality for '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_set_members(self, mock_connection):
        """Test getting set members."""
        key = 'test_set'

        # Test successful get
        mock_connection.smembers.return_value = {'member1', 'member2'}
        result = await set_members(key)
        assert 'member1' in result and 'member2' in result
        mock_connection.smembers.assert_called_with(key)

        # Test empty set
        mock_connection.smembers.return_value = set()
        result = await set_members(key)
        assert f"Set '{key}' is empty" in result

        # Test error handling
        mock_connection.smembers.side_effect = ValkeyError('Test error')
        result = await set_members(key)
        assert f"Error getting set members from '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_set_random_member(self, mock_connection):
        """Test getting random set member."""
        key = 'test_set'

        # Test successful get
        mock_connection.srandmember.return_value = 'test_member'
        result = await set_random_member(key)
        assert 'test_member' in result
        mock_connection.srandmember.assert_called_with(key)

        # Test empty set
        mock_connection.srandmember.return_value = None
        result = await set_random_member(key)
        assert f"Set '{key}' is empty" in result

        # Test error handling
        mock_connection.srandmember.side_effect = ValkeyError('Test error')
        result = await set_random_member(key)
        assert f"Error getting random member from set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_set_contains(self, mock_connection):
        """Test checking set membership."""
        key = 'test_set'
        member = 'test_member'

        # Test member exists
        mock_connection.sismember.return_value = True
        result = await set_contains(key, member)
        assert 'true' in result
        mock_connection.sismember.assert_called_with(key, member)

        # Test member does not exist
        mock_connection.sismember.return_value = False
        result = await set_contains(key, member)
        assert 'false' in result

        # Test error handling
        mock_connection.sismember.side_effect = ValkeyError('Test error')
        result = await set_contains(key, member)
        assert f"Error checking set membership in '{key}'" in result
        assert 'Test error' in result
