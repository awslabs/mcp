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

"""Additional tests for the Stream functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.stream import (
    stream_info,
    stream_info_consumers,
    stream_info_groups,
    stream_length,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestStreamAdditional:
    """Additional tests for Stream operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch(
            'awslabs.valkey_mcp_server.tools.stream.ValkeyConnectionManager'
        ) as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context."""
        with patch('awslabs.valkey_mcp_server.tools.stream.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = False
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_stream_length(self, mock_connection):
        """Test getting stream length."""
        key = 'test_stream'

        # Test successful length retrieval
        mock_connection.xlen.return_value = 5
        result = await stream_length(key)
        assert '5' in result
        mock_connection.xlen.assert_called_with(key)

        # Test error handling
        mock_connection.xlen.side_effect = ValkeyError('Test error')
        result = await stream_length(key)
        assert f"Error getting stream length for '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_stream_info(self, mock_connection):
        """Test getting stream information."""
        key = 'test_stream'

        # Test successful info retrieval
        mock_info = {
            'length': 5,
            'radix-tree-keys': 1,
            'radix-tree-nodes': 2,
            'last-generated-id': '1234567890-0',
            'first-entry': ('1234567890-0', {'field1': 'value1'}),
            'last-entry': ('1234567890-1', {'field2': 'value2'}),
        }
        mock_connection.xinfo_stream.return_value = mock_info
        result = await stream_info(key)
        assert str(mock_info) in result
        mock_connection.xinfo_stream.assert_called_with(key)

        # Test error handling
        mock_connection.xinfo_stream.side_effect = ValkeyError('Test error')
        result = await stream_info(key)
        assert f"Error getting stream info for '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_stream_info_groups(self, mock_connection):
        """Test getting consumer groups information."""
        key = 'test_stream'

        # Test successful groups info retrieval
        mock_groups = [
            {
                'name': 'group1',
                'consumers': 2,
                'pending': 5,
                'last-delivered-id': '1234567890-0',
            },
            {
                'name': 'group2',
                'consumers': 1,
                'pending': 0,
                'last-delivered-id': '1234567890-1',
            },
        ]
        mock_connection.xinfo_groups.return_value = mock_groups
        result = await stream_info_groups(key)
        assert str(mock_groups) in result
        mock_connection.xinfo_groups.assert_called_with(key)

        # Test no groups
        mock_connection.xinfo_groups.return_value = []
        result = await stream_info_groups(key)
        assert f"No consumer groups found for stream '{key}'" in result

        # Test error handling
        mock_connection.xinfo_groups.side_effect = ValkeyError('Test error')
        result = await stream_info_groups(key)
        assert f"Error getting consumer groups info for '{key}'" in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_stream_info_consumers(self, mock_connection):
        """Test getting consumers information."""
        key = 'test_stream'
        group = 'test_group'

        # Test successful consumers info retrieval
        mock_consumers = [
            {
                'name': 'consumer1',
                'pending': 3,
                'idle': 10000,
            },
            {
                'name': 'consumer2',
                'pending': 2,
                'idle': 5000,
            },
        ]
        mock_connection.xinfo_consumers.return_value = mock_consumers
        result = await stream_info_consumers(key, group)
        assert str(mock_consumers) in result
        mock_connection.xinfo_consumers.assert_called_with(key, group)

        # Test no consumers
        mock_connection.xinfo_consumers.return_value = []
        result = await stream_info_consumers(key, group)
        assert f"No consumers found in group '{group}'" in result

        # Test error handling
        mock_connection.xinfo_consumers.side_effect = ValkeyError('Test error')
        result = await stream_info_consumers(key, group)
        assert 'Error getting consumers info' in result
        assert 'Test error' in result
