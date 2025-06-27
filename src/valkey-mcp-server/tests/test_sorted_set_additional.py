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

"""Additional tests for the Sorted Set functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.sorted_set import (
    sorted_set_cardinality,
    sorted_set_popmax,
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

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context."""
        with patch('awslabs.valkey_mcp_server.tools.sorted_set.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = False
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_sorted_set_remove_by_rank(self, mock_connection, mock_context):
        """Test removing members by rank range."""
        key = 'test_sorted_set'
        start = 0
        stop = 2

        # Test successful remove
        mock_context.readonly_mode.return_value = False
        mock_connection.zremrangebyrank.return_value = 3
        result = await sorted_set_remove_by_rank(key, start, stop)
        assert f"Successfully removed 3 member(s) by rank from sorted set '{key}'" in result
        mock_connection.zremrangebyrank.assert_called_with(key, start, stop)

        # Test error handling
        mock_connection.zremrangebyrank.side_effect = ValkeyError('Test error')
        result = await sorted_set_remove_by_rank(key, start, stop)
        assert f"Error removing by rank from sorted set '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_connection.zremrangebyrank.reset_mock()
        mock_connection.zremrangebyrank.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await sorted_set_remove_by_rank(key, start, stop)
        assert 'Error: Cannot remove from sorted set in readonly mode' in result
        mock_connection.zremrangebyrank.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_remove_by_score(self, mock_connection, mock_context):
        """Test removing members by score range."""
        key = 'test_sorted_set'
        min_score = 1.0
        max_score = 5.0

        # Test successful remove
        mock_context.readonly_mode.return_value = False
        mock_connection.zremrangebyscore.return_value = 3
        result = await sorted_set_remove_by_score(key, min_score, max_score)
        assert f"Successfully removed 3 member(s) by score from sorted set '{key}'" in result
        mock_connection.zremrangebyscore.assert_called_with(key, min_score, max_score)

        # Test error handling
        mock_connection.zremrangebyscore.side_effect = ValkeyError('Test error')
        result = await sorted_set_remove_by_score(key, min_score, max_score)
        assert f"Error removing by score from sorted set '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_connection.zremrangebyscore.reset_mock()
        mock_connection.zremrangebyscore.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await sorted_set_remove_by_score(key, min_score, max_score)
        assert 'Error: Cannot remove from sorted set in readonly mode' in result
        mock_connection.zremrangebyscore.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_remove_by_lex(self, mock_connection, mock_context):
        """Test removing members by lexicographical range."""
        key = 'test_sorted_set'
        min_lex = '[a'
        max_lex = '[c'

        # Test successful remove
        mock_context.readonly_mode.return_value = False
        mock_connection.zremrangebylex.return_value = 3
        result = await sorted_set_remove_by_lex(key, min_lex, max_lex)
        assert f"Successfully removed 3 member(s) by lex range from sorted set '{key}'" in result
        mock_connection.zremrangebylex.assert_called_with(key, min_lex, max_lex)

        # Test error handling
        mock_connection.zremrangebylex.side_effect = ValkeyError('Test error')
        result = await sorted_set_remove_by_lex(key, min_lex, max_lex)
        assert f"Error removing by lex range from sorted set '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_connection.zremrangebylex.reset_mock()
        mock_connection.zremrangebylex.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await sorted_set_remove_by_lex(key, min_lex, max_lex)
        assert 'Error: Cannot remove from sorted set in readonly mode' in result
        mock_connection.zremrangebylex.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_cardinality(self, mock_connection):
        """Test getting cardinality of sorted set."""
        key = 'test_sorted_set'

        # Test cardinality without score range
        mock_connection.zcard.return_value = 5
        result = await sorted_set_cardinality(key)
        assert '5' in result
        mock_connection.zcard.assert_called_with(key)

        # Test cardinality with score range
        mock_connection.zcount.return_value = 3
        min_score = 1.0
        max_score = 5.0
        result = await sorted_set_cardinality(key, min_score, max_score)
        assert '3' in result
        mock_connection.zcount.assert_called_with(key, min_score, max_score)

        # Test error handling
        mock_connection.zcard.side_effect = ValkeyError('Test error')
        result = await sorted_set_cardinality(key)
        assert f"Error getting sorted set cardinality for '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_rank(self, mock_connection):
        """Test getting rank of member in sorted set."""
        key = 'test_sorted_set'
        member = 'test_member'

        # Test rank in ascending order
        mock_connection.zrank.return_value = 2
        result = await sorted_set_rank(key, member)
        assert '2' in result
        mock_connection.zrank.assert_called_with(key, member)

        # Test rank in descending order
        mock_connection.zrevrank.return_value = 1
        result = await sorted_set_rank(key, member, reverse=True)
        assert '1' in result
        mock_connection.zrevrank.assert_called_with(key, member)

        # Test member not found
        mock_connection.zrank.return_value = None
        result = await sorted_set_rank(key, member)
        assert f"Member not found in sorted set '{key}'" in result

        # Test error handling
        mock_connection.zrank.side_effect = ValkeyError('Test error')
        result = await sorted_set_rank(key, member)
        assert f"Error getting rank from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_range_by_score(self, mock_connection):
        """Test getting range by score from sorted set."""
        key = 'test_sorted_set'
        min_score = 1.0
        max_score = 5.0

        # Test range by score
        mock_connection.zrangebyscore.return_value = ['member1', 'member2', 'member3']
        result = await sorted_set_range_by_score(key, min_score, max_score)
        assert "['member1', 'member2', 'member3']" in result
        mock_connection.zrangebyscore.assert_called_with(
            key, min_score, max_score, withscores=False, start=None, num=None
        )

        # Test range by score with scores
        mock_connection.zrangebyscore.return_value = [('member1', 1.0), ('member2', 2.0)]
        result = await sorted_set_range_by_score(key, min_score, max_score, withscores=True)
        assert "[('member1', 1.0), ('member2', 2.0)]" in result
        mock_connection.zrangebyscore.assert_called_with(
            key, min_score, max_score, withscores=True, start=None, num=None
        )

        # Test range by score in reverse order
        mock_connection.zrevrangebyscore.return_value = ['member3', 'member2', 'member1']
        result = await sorted_set_range_by_score(key, min_score, max_score, reverse=True)
        assert "['member3', 'member2', 'member1']" in result
        mock_connection.zrevrangebyscore.assert_called_with(
            key, max_score, min_score, withscores=False, start=None, num=None
        )

        # Test range by score with pagination
        offset = 1
        count = 2
        mock_connection.zrangebyscore.return_value = ['member2', 'member3']
        result = await sorted_set_range_by_score(
            key, min_score, max_score, offset=offset, count=count
        )
        assert "['member2', 'member3']" in result
        mock_connection.zrangebyscore.assert_called_with(
            key, min_score, max_score, withscores=False, start=offset, num=count
        )

        # Test empty result
        mock_connection.zrangebyscore.return_value = []
        result = await sorted_set_range_by_score(key, min_score, max_score)
        assert f"No members found in score range for sorted set '{key}'" in result

        # Test error handling
        mock_connection.zrangebyscore.side_effect = ValkeyError('Test error')
        result = await sorted_set_range_by_score(key, min_score, max_score)
        assert f"Error getting score range from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_range_by_lex(self, mock_connection):
        """Test getting range by lexicographical order from sorted set."""
        key = 'test_sorted_set'
        min_lex = '[a'
        max_lex = '[c'

        # Test range by lex
        mock_connection.zrangebylex.return_value = ['apple', 'banana', 'cherry']
        result = await sorted_set_range_by_lex(key, min_lex, max_lex)
        assert "['apple', 'banana', 'cherry']" in result
        mock_connection.zrangebylex.assert_called_with(key, min_lex, max_lex, start=None, num=None)

        # Test range by lex in reverse order
        mock_connection.zrevrangebylex.return_value = ['cherry', 'banana', 'apple']
        result = await sorted_set_range_by_lex(key, min_lex, max_lex, reverse=True)
        assert "['cherry', 'banana', 'apple']" in result
        mock_connection.zrevrangebylex.assert_called_with(
            key, max_lex, min_lex, start=None, num=None
        )

        # Test range by lex with pagination
        offset = 1
        count = 2
        mock_connection.zrangebylex.return_value = ['banana', 'cherry']
        result = await sorted_set_range_by_lex(key, min_lex, max_lex, offset=offset, count=count)
        assert "['banana', 'cherry']" in result
        mock_connection.zrangebylex.assert_called_with(
            key, min_lex, max_lex, start=offset, num=count
        )

        # Test empty result
        mock_connection.zrangebylex.return_value = []
        result = await sorted_set_range_by_lex(key, min_lex, max_lex)
        assert f"No members found in lex range for sorted set '{key}'" in result

        # Test error handling
        mock_connection.zrangebylex.side_effect = ValkeyError('Test error')
        result = await sorted_set_range_by_lex(key, min_lex, max_lex)
        assert f"Error getting lex range from sorted set '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_sorted_set_popmax(self, mock_connection, mock_context):
        """Test popping maximum score members."""
        key = 'test_sorted_set'
        count = 2

        # Test successful pop single member
        mock_context.readonly_mode.return_value = False
        mock_connection.zpopmax.return_value = [('member3', 3.0)]
        result = await sorted_set_popmax(key)
        assert 'member3' in result
        mock_connection.zpopmax.assert_called_with(key)

        # Test successful pop multiple members
        mock_connection.zpopmax.return_value = [('member3', 3.0), ('member2', 2.0)]
        result = await sorted_set_popmax(key, count)
        assert 'member3' in result and 'member2' in result
        mock_connection.zpopmax.assert_called_with(key, count)

        # Test empty set
        mock_connection.zpopmax.return_value = []
        result = await sorted_set_popmax(key)
        assert f"Sorted set '{key}' is empty" in result

        # Test error handling
        mock_connection.zpopmax.side_effect = ValkeyError('Test error')
        result = await sorted_set_popmax(key)
        assert f"Error popping max from sorted set '{key}'" in result
        assert 'Test error' in result

        # Test readonly mode
        mock_connection.zpopmax.reset_mock()
        mock_connection.zpopmax.side_effect = None
        mock_context.readonly_mode.return_value = True
        result = await sorted_set_popmax(key)
        assert 'Error: Cannot pop from sorted set in readonly mode' in result
        mock_connection.zpopmax.assert_not_called()
