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

"""Additional tests for the Sorted Set functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.sorted_set import (
    sorted_set_cardinality,
    sorted_set_popmax,
    sorted_set_range,
    sorted_set_range_by_lex,
    sorted_set_range_by_score,
    sorted_set_rank,
    sorted_set_remove_by_lex,
    sorted_set_remove_by_rank,
    sorted_set_remove_by_score,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestSortedSetAdditional:
    """Additional tests for Sorted Set operations."""

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
    async def test_sorted_set_remove_by_rank(self, mock_connection):
        """Test removing members by rank range."""
        key = 'test_sorted_set'
        start = 0
        stop = 2

        # Test successful remove
        mock_connection.zremrangebyrank.return_value = 3
        result = await sorted_set_remove_by_rank(key, start, stop)
        assert f"Successfully removed 3 member(s) by rank from sorted set '{key}'" in result
        mock_connection.zremrangebyrank.assert_called_with(key, start, stop)

        # Test error handling
        mock_connection.zremrangebyrank.side_effect = ValkeyError('Test error')
        result = await sorted_set_remove_by_rank(key, start, stop)
        assert f"Error removing by rank from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_remove_by_score(self, mock_connection):
        """Test removing members by score range."""
        key = 'test_sorted_set'
        min_score = 1.0
        max_score = 2.0

        # Test successful remove
        mock_connection.zremrangebyscore.return_value = 2
        result = await sorted_set_remove_by_score(key, min_score, max_score)
        assert f"Successfully removed 2 member(s) by score from sorted set '{key}'" in result
        mock_connection.zremrangebyscore.assert_called_with(key, min_score, max_score)

        # Test error handling
        mock_connection.zremrangebyscore.side_effect = ValkeyError('Test error')
        result = await sorted_set_remove_by_score(key, min_score, max_score)
        assert f"Error removing by score from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_remove_by_lex(self, mock_connection):
        """Test removing members by lexicographical range."""
        key = 'test_sorted_set'
        min_lex = '[a'
        max_lex = '[z'

        # Test successful remove
        mock_connection.zremrangebylex.return_value = 2
        result = await sorted_set_remove_by_lex(key, min_lex, max_lex)
        assert f"Successfully removed 2 member(s) by lex range from sorted set '{key}'" in result
        mock_connection.zremrangebylex.assert_called_with(key, min_lex, max_lex)

        # Test error handling
        mock_connection.zremrangebylex.side_effect = ValkeyError('Test error')
        result = await sorted_set_remove_by_lex(key, min_lex, max_lex)
        assert f"Error removing by lex range from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_cardinality_with_score_range(self, mock_connection):
        """Test getting cardinality with score range."""
        key = 'test_sorted_set'
        min_score = 1.0
        max_score = 2.0

        # Test successful cardinality with score range
        mock_connection.zcount.return_value = 2
        result = await sorted_set_cardinality(key, min_score, max_score)
        assert result == '2'
        mock_connection.zcount.assert_called_with(key, min_score, max_score)

        # Test error handling
        mock_connection.zcount.side_effect = ValkeyError('Test error')
        result = await sorted_set_cardinality(key, min_score, max_score)
        assert f"Error getting sorted set cardinality for '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_rank_reverse(self, mock_connection):
        """Test getting rank in reverse order."""
        key = 'test_sorted_set'
        member = 'test_member'

        # Test successful reverse rank
        mock_connection.zrevrank.return_value = 1
        result = await sorted_set_rank(key, member, reverse=True)
        assert result == '1'
        mock_connection.zrevrank.assert_called_with(key, member)

        # Test member not found
        mock_connection.zrevrank.return_value = None
        result = await sorted_set_rank(key, member, reverse=True)
        assert f"Member not found in sorted set '{key}'" in result

        # Test error handling
        mock_connection.zrevrank.side_effect = ValkeyError('Test error')
        result = await sorted_set_rank(key, member, reverse=True)
        assert f"Error getting rank from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_range_reverse(self, mock_connection):
        """Test getting range in reverse order."""
        key = 'test_sorted_set'
        start = 0
        stop = -1

        # Test successful reverse range
        mock_connection.zrevrange.return_value = ['member2', 'member1']
        result = await sorted_set_range(key, start, stop, reverse=True)
        assert 'member2' in result and 'member1' in result
        mock_connection.zrevrange.assert_called_with(key, start, stop, withscores=False)

    @pytest.mark.asyncio
    async def test_sorted_set_range_by_score_reverse(self, mock_connection):
        """Test getting score range in reverse order."""
        key = 'test_sorted_set'
        min_score = 1.0
        max_score = 2.0
        offset = 0
        count = 10

        # Test successful reverse score range
        mock_connection.zrevrangebyscore.return_value = ['member2', 'member1']
        result = await sorted_set_range_by_score(
            key, min_score, max_score, reverse=True, offset=offset, count=count
        )
        assert 'member2' in result and 'member1' in result
        mock_connection.zrevrangebyscore.assert_called_with(
            key, max_score, min_score, withscores=False, start=offset, num=count
        )

        # Test no members found
        mock_connection.zrevrangebyscore.return_value = []
        result = await sorted_set_range_by_score(key, min_score, max_score, reverse=True)
        assert f"No members found in score range for sorted set '{key}'" in result

    @pytest.mark.asyncio
    async def test_sorted_set_range_by_lex_reverse(self, mock_connection):
        """Test getting lexicographical range in reverse order."""
        key = 'test_sorted_set'
        min_lex = '[a'
        max_lex = '[z'
        offset = 0
        count = 10

        # Test successful reverse lex range
        mock_connection.zrevrangebylex.return_value = ['z', 'y', 'x']
        result = await sorted_set_range_by_lex(
            key, min_lex, max_lex, reverse=True, offset=offset, count=count
        )
        assert 'z' in result and 'y' in result and 'x' in result
        mock_connection.zrevrangebylex.assert_called_with(
            key, max_lex, min_lex, start=offset, num=count
        )

        # Test no members found
        mock_connection.zrevrangebylex.return_value = []
        result = await sorted_set_range_by_lex(key, min_lex, max_lex, reverse=True)
        assert f"No members found in lex range for sorted set '{key}'" in result

    @pytest.mark.asyncio
    async def test_sorted_set_popmax_with_count(self, mock_connection):
        """Test popping multiple maximum score members."""
        key = 'test_sorted_set'
        count = 2

        # Test successful pop with count
        mock_connection.zpopmax.return_value = [('member2', 2.0), ('member1', 1.0)]
        result = await sorted_set_popmax(key, count)
        assert 'member2' in result and 'member1' in result
        mock_connection.zpopmax.assert_called_with(key, count)

        # Test empty set
        mock_connection.zpopmax.return_value = []
        result = await sorted_set_popmax(key, count)
        assert f"Sorted set '{key}' is empty" in result
