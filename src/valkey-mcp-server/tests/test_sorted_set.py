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

"""Tests for the Sorted Set functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.sorted_set import (
    sorted_set_add,
    sorted_set_add_incr,
    sorted_set_popmin,
    sorted_set_range,
    sorted_set_remove,
    sorted_set_score,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestSortedSet:
    """Tests for Sorted Set operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch(
            'awslabs.valkey_mcp_server.tools.sorted_set.ValkeyConnectionManager'
        ) as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_sorted_set_add(self, mock_connection):
        """Test adding members to sorted set."""
        key = 'test_sorted_set'
        mapping = {'member1': 1.0, 'member2': 2.0}

        # Test successful add
        mock_connection.zadd.return_value = 2
        result = await sorted_set_add(key, mapping)
        assert f"Successfully added {len(mapping)} new member(s) to sorted set '{key}'" in result
        mock_connection.zadd.assert_called_with(key, mapping)

        # Test error handling
        mock_connection.zadd.side_effect = ValkeyError('Test error')
        result = await sorted_set_add(key, mapping)
        assert f"Error adding to sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_add_incr(self, mock_connection):
        """Test incrementing score in sorted set."""
        key = 'test_sorted_set'
        member = 'test_member'
        score = 1.5

        # Test successful increment
        mock_connection.zincrby.return_value = 3.5
        result = await sorted_set_add_incr(key, member, score)
        assert f"Successfully set score for member in sorted set '{key}' to 3.5" in result
        mock_connection.zincrby.assert_called_with(key, score, member)

        # Test error handling
        mock_connection.zincrby.side_effect = ValkeyError('Test error')
        result = await sorted_set_add_incr(key, member, score)
        assert f"Error incrementing score in sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_remove(self, mock_connection):
        """Test removing members from sorted set."""
        key = 'test_sorted_set'
        members = ['member1', 'member2']

        # Test successful remove
        mock_connection.zrem.return_value = 2
        result = await sorted_set_remove(key, *members)
        assert f"Successfully removed {len(members)} member(s) from sorted set '{key}'" in result
        mock_connection.zrem.assert_called_with(key, *members)

        # Test error handling
        mock_connection.zrem.side_effect = ValkeyError('Test error')
        result = await sorted_set_remove(key, *members)
        assert f"Error removing from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_score(self, mock_connection):
        """Test getting score from sorted set."""
        key = 'test_sorted_set'
        member = 'test_member'

        # Test successful score retrieval
        mock_connection.zscore.return_value = 1.5
        result = await sorted_set_score(key, member)
        assert '1.5' in result
        mock_connection.zscore.assert_called_with(key, member)

        # Test member not found
        mock_connection.zscore.return_value = None
        result = await sorted_set_score(key, member)
        assert f"Member not found in sorted set '{key}'" in result

        # Test error handling
        mock_connection.zscore.side_effect = ValkeyError('Test error')
        result = await sorted_set_score(key, member)
        assert f"Error getting score from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_range(self, mock_connection):
        """Test getting range from sorted set."""
        key = 'test_sorted_set'
        start = 0
        stop = -1
        withscores = True

        # Test successful range retrieval
        mock_connection.zrange.return_value = [('member1', 1.0), ('member2', 2.0)]
        result = await sorted_set_range(key, start, stop, withscores=withscores)
        assert 'member1' in result and 'member2' in result
        mock_connection.zrange.assert_called_with(key, start, stop, withscores=withscores)

        # Test empty range
        mock_connection.zrange.return_value = []
        result = await sorted_set_range(key, start, stop)
        assert f"No members found in range for sorted set '{key}'" in result

        # Test error handling
        mock_connection.zrange.side_effect = ValkeyError('Test error')
        result = await sorted_set_range(key, start, stop)
        assert f"Error getting range from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_popmin(self, mock_connection):
        """Test popping minimum score members."""
        key = 'test_sorted_set'
        count = 2

        # Test successful pop single member
        mock_connection.zpopmin.return_value = [('member1', 1.0)]
        result = await sorted_set_popmin(key)
        assert 'member1' in result
        mock_connection.zpopmin.assert_called_with(key)

        # Test successful pop multiple members
        mock_connection.zpopmin.return_value = [('member1', 1.0), ('member2', 2.0)]
        result = await sorted_set_popmin(key, count)
        assert 'member1' in result and 'member2' in result
        mock_connection.zpopmin.assert_called_with(key, count)

        # Test empty set
        mock_connection.zpopmin.return_value = []
        result = await sorted_set_popmin(key)
        assert f"Sorted set '{key}' is empty" in result

        # Test error handling
        mock_connection.zpopmin.side_effect = ValkeyError('Test error')
        result = await sorted_set_popmin(key)
        assert f"Error popping min from sorted set '{key}'" in result
        assert 'Test error' in result
