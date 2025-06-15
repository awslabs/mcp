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

"""Tests for readonly mode in Sorted Set functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.sorted_set import (
    sorted_set_add,
    sorted_set_add_incr,
    sorted_set_popmax,
    sorted_set_popmin,
    sorted_set_remove,
    sorted_set_remove_by_lex,
    sorted_set_remove_by_rank,
    sorted_set_remove_by_score,
)
from unittest.mock import Mock, patch


class TestSortedSetReadonly:
    """Tests for Sorted Set operations in readonly mode."""

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
            mock_ctx.readonly_mode.return_value = True
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_sorted_set_add_readonly(self, mock_connection, mock_context):
        """Test adding members to sorted set in readonly mode."""
        key = 'test_sorted_set'
        mapping = {'member1': 1.0, 'member2': 2.0}

        result = await sorted_set_add(key, mapping)
        assert 'Error: Cannot add to sorted set in readonly mode' in result
        mock_connection.zadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_add_incr_readonly(self, mock_connection, mock_context):
        """Test incrementing score in sorted set in readonly mode."""
        key = 'test_sorted_set'
        member = 'test_member'
        score = 1.5

        result = await sorted_set_add_incr(key, member, score)
        assert 'Error: Cannot increment score in sorted set in readonly mode' in result
        mock_connection.zincrby.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_remove_readonly(self, mock_connection, mock_context):
        """Test removing members from sorted set in readonly mode."""
        key = 'test_sorted_set'
        members = ['member1', 'member2']

        result = await sorted_set_remove(key, *members)
        assert 'Error: Cannot remove from sorted set in readonly mode' in result
        mock_connection.zrem.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_remove_by_rank_readonly(self, mock_connection, mock_context):
        """Test removing members by rank in readonly mode."""
        key = 'test_sorted_set'
        start = 0
        stop = 2

        result = await sorted_set_remove_by_rank(key, start, stop)
        assert 'Error: Cannot remove from sorted set in readonly mode' in result
        mock_connection.zremrangebyrank.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_remove_by_score_readonly(self, mock_connection, mock_context):
        """Test removing members by score in readonly mode."""
        key = 'test_sorted_set'
        min_score = 1.0
        max_score = 5.0

        result = await sorted_set_remove_by_score(key, min_score, max_score)
        assert 'Error: Cannot remove from sorted set in readonly mode' in result
        mock_connection.zremrangebyscore.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_remove_by_lex_readonly(self, mock_connection, mock_context):
        """Test removing members by lexicographical range in readonly mode."""
        key = 'test_sorted_set'
        min_lex = '[a'
        max_lex = '[c'

        result = await sorted_set_remove_by_lex(key, min_lex, max_lex)
        assert 'Error: Cannot remove from sorted set in readonly mode' in result
        mock_connection.zremrangebylex.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_popmin_readonly(self, mock_connection, mock_context):
        """Test popping minimum score members in readonly mode."""
        key = 'test_sorted_set'

        result = await sorted_set_popmin(key)
        assert 'Error: Cannot pop from sorted set in readonly mode' in result
        mock_connection.zpopmin.assert_not_called()

    @pytest.mark.asyncio
    async def test_sorted_set_popmax_readonly(self, mock_connection, mock_context):
        """Test popping maximum score members in readonly mode."""
        key = 'test_sorted_set'

        result = await sorted_set_popmax(key)
        assert 'Error: Cannot pop from sorted set in readonly mode' in result
        mock_connection.zpopmax.assert_not_called()
