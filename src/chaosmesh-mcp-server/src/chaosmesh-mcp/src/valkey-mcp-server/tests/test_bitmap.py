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

"""Tests for the bitmap functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.bitmap import (
    bitmap_count,
    bitmap_get,
    bitmap_pos,
    bitmap_set,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestBitmap:
    """Tests for bitmap operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch(
            'awslabs.valkey_mcp_server.tools.bitmap.ValkeyConnectionManager'
        ) as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context."""
        with patch('awslabs.valkey_mcp_server.tools.bitmap.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = False
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_bitmap_set(self, mock_connection, mock_context):
        """Test setting bits in a bitmap."""
        key = 'test_bitmap'

        # Mock the setbit response
        mock_connection.setbit.return_value = 0
        mock_context.readonly_mode.return_value = False

        # Test setting individual bits
        result = await bitmap_set(key, 0, 1)
        assert 'set to 1' in result
        mock_connection.setbit.assert_called_with(key, 0, 1)

        # Test invalid bit value
        result = await bitmap_set(key, 0, 2)
        assert 'Error: value must be 0 or 1' in result

        # Test negative offset
        result = await bitmap_set(key, -1, 1)
        assert 'Error: offset must be non-negative' in result

        # Test readonly mode
        mock_connection.setbit.reset_mock()
        mock_context.readonly_mode.return_value = True
        result = await bitmap_set(key, 0, 1)
        assert 'Error: Cannot set bitmap bit in readonly mode' in result
        mock_connection.setbit.assert_not_called()

        # Test error handling
        mock_context.readonly_mode.return_value = False
        mock_connection.setbit.side_effect = ValkeyError('Test error')
        result = await bitmap_set(key, 0, 1)
        assert f"Error setting bit in '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_bitmap_get(self, mock_connection):
        """Test getting bits from a bitmap."""
        key = 'test_bitmap_get'

        # Mock the getbit response
        mock_connection.getbit.return_value = 1

        # Test getting a bit
        result = await bitmap_get(key, 5)
        assert 'is 1' in result
        mock_connection.getbit.assert_called_with(key, 5)

        # Test negative offset
        result = await bitmap_get(key, -1)
        assert 'Error: offset must be non-negative' in result

    @pytest.mark.asyncio
    async def test_bitmap_count(self, mock_connection):
        """Test counting set bits in a bitmap."""
        key = 'test_bitmap_count'

        # Mock the bitcount response
        mock_connection.bitcount.return_value = 4

        # Test counting all bits
        result = await bitmap_count(key)
        assert '4' in result
        mock_connection.bitcount.assert_called_with(key)

        # Test counting bits in range
        result = await bitmap_count(key, 0, 1)
        assert '4' in result
        mock_connection.bitcount.assert_called_with(key, 0, 1)

        # Test invalid range
        result = await bitmap_count(key, -1, 1)
        assert 'Error: start and end must be non-negative' in result

        result = await bitmap_count(key, 2, 1)
        assert 'Error: start must be less than or equal to end' in result

    @pytest.mark.asyncio
    async def test_bitmap_pos(self, mock_connection):
        """Test finding positions of bits."""
        key = 'test_bitmap_pos'

        # Mock the bitpos response
        mock_connection.bitpos.return_value = 3

        # Test finding position
        result = await bitmap_pos(key, 1)
        assert '3' in result
        mock_connection.bitpos.assert_called_with(key, 1)

        # Test with range
        result = await bitmap_pos(key, 1, start=1, end=10)
        assert '3' in result
        mock_connection.bitpos.assert_called_with(key, 1, 'START', 1, 'END', 10)

        # Test with count
        result = await bitmap_pos(key, 1, count=5)
        assert '3' in result
        mock_connection.bitpos.assert_called_with(key, 1, 'COUNT', 5)

        # Test invalid bit value
        result = await bitmap_pos(key, 2)
        assert 'Error: bit must be 0 or 1' in result

        # Test negative start
        result = await bitmap_pos(key, 1, start=-1)
        assert 'Error: start must be non-negative' in result

        # Test negative end
        result = await bitmap_pos(key, 1, end=-1)
        assert 'Error: end must be non-negative' in result

        # Test invalid range
        result = await bitmap_pos(key, 1, start=10, end=5)
        assert 'Error: start must be less than or equal to end' in result

        # Test invalid count
        result = await bitmap_pos(key, 1, count=0)
        assert 'Error: count must be positive' in result

        # Test no positions found
        mock_connection.bitpos.return_value = None
        result = await bitmap_pos(key, 1)
        assert 'No bits set to 1 found' in result
