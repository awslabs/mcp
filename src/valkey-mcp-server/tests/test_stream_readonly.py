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

"""Tests for readonly mode in Stream functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.stream import (
    stream_add,
    stream_delete,
    stream_group_create,
    stream_group_delete_consumer,
    stream_group_destroy,
    stream_group_set_id,
    stream_read_group,
    stream_trim,
)
from unittest.mock import Mock, patch


class TestStreamReadonly:
    """Tests for Stream operations in readonly mode."""

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
            mock_ctx.readonly_mode.return_value = True
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_stream_add_readonly(self, mock_connection, mock_context):
        """Test adding entry to stream in readonly mode."""
        key = 'test_stream'
        field_dict = {'field1': 'value1'}

        result = await stream_add(key, field_dict)
        assert 'Error: Cannot add to stream in readonly mode' in result
        mock_connection.xadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_delete_readonly(self, mock_connection, mock_context):
        """Test deleting from stream in readonly mode."""
        key = 'test_stream'
        id = '1234567890-0'

        result = await stream_delete(key, id)
        assert 'Error: Cannot delete from stream in readonly mode' in result
        mock_connection.xdel.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_trim_readonly(self, mock_connection, mock_context):
        """Test trimming stream in readonly mode."""
        key = 'test_stream'
        maxlen = 100

        result = await stream_trim(key, maxlen)
        assert 'Error: Cannot trim stream in readonly mode' in result
        mock_connection.xtrim.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_group_create_readonly(self, mock_connection, mock_context):
        """Test creating consumer group in readonly mode."""
        key = 'test_stream'
        group_name = 'test_group'

        result = await stream_group_create(key, group_name)
        assert 'Error: Cannot create consumer group in readonly mode' in result
        mock_connection.xgroup_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_group_destroy_readonly(self, mock_connection, mock_context):
        """Test destroying consumer group in readonly mode."""
        key = 'test_stream'
        group_name = 'test_group'

        result = await stream_group_destroy(key, group_name)
        assert 'Error: Cannot destroy consumer group in readonly mode' in result
        mock_connection.xgroup_destroy.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_group_set_id_readonly(self, mock_connection, mock_context):
        """Test setting consumer group ID in readonly mode."""
        key = 'test_stream'
        group_name = 'test_group'
        id = '1234567890-0'

        result = await stream_group_set_id(key, group_name, id)
        assert 'Error: Cannot set consumer group ID in readonly mode' in result
        mock_connection.xgroup_setid.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_group_delete_consumer_readonly(self, mock_connection, mock_context):
        """Test deleting consumer in readonly mode."""
        key = 'test_stream'
        group_name = 'test_group'
        consumer_name = 'test_consumer'

        result = await stream_group_delete_consumer(key, group_name, consumer_name)
        assert 'Error: Cannot delete consumer in readonly mode' in result
        mock_connection.xgroup_delconsumer.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_read_group_readonly(self, mock_connection, mock_context):
        """Test reading from consumer group in readonly mode."""
        key = 'test_stream'
        group_name = 'test_group'
        consumer_name = 'test_consumer'

        # Test with acknowledgment required (noack=False)
        result = await stream_read_group(key, group_name, consumer_name, noack=False)
        assert 'Error: Cannot read from stream with acknowledgment in readonly mode' in result
        mock_connection.xreadgroup.assert_not_called()

        # Test with no acknowledgment required (noack=True)
        mock_connection.xreadgroup.reset_mock()
        mock_connection.xreadgroup.return_value = [(key, [('1234567890-0', {'field1': 'value1'})])]
        result = await stream_read_group(key, group_name, consumer_name, noack=True)
        assert 'Error: Cannot read from stream with acknowledgment in readonly mode' not in result
        mock_connection.xreadgroup.assert_called_with(
            group_name, consumer_name, {key: '>'}, count=None, block=None, noack=True
        )
