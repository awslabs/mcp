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

"""Tests for the Stream functionality in the valkey MCP server."""

import pytest
from awslabs.valkey_mcp_server.tools.stream import (
    stream_add,
    stream_delete,
    stream_group_create,
    stream_group_delete_consumer,
    stream_group_destroy,
    stream_group_set_id,
    stream_range,
    stream_read,
    stream_read_group,
    stream_trim,
)
from unittest.mock import Mock, patch
from valkey.exceptions import ValkeyError


class TestStream:
    """Tests for Stream operations."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock Valkey connection."""
        with patch(
            'awslabs.valkey_mcp_server.tools.stream.ValkeyConnectionManager'
        ) as mock_manager:
            mock_conn = Mock()
            mock_manager.get_connection.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_stream_add_with_options(self, mock_connection):
        """Test adding entry to stream with various options."""
        key = 'test_stream'
        field_dict = {'field1': 'value1', 'field2': 'value2'}
        entry_id = '1234567890-0'

        # Test with auto-generated ID
        mock_connection.xadd.return_value = entry_id
        result = await stream_add(key, field_dict)
        assert f"Successfully added entry with ID '{entry_id}'" in result
        mock_connection.xadd.assert_called_with(key, field_dict, id='*')

        # Test with specific ID
        result = await stream_add(key, field_dict, id=entry_id)
        mock_connection.xadd.assert_called_with(key, field_dict, id=entry_id)

        # Test with approximate maxlen
        result = await stream_add(key, field_dict, maxlen=1000)
        mock_connection.xadd.assert_called_with(key, field_dict, id='*', maxlen='~1000')

        # Test with exact maxlen
        result = await stream_add(key, field_dict, maxlen=1000, approximate=False)
        mock_connection.xadd.assert_called_with(key, field_dict, id='*', maxlen=1000)

        # Test error handling
        mock_connection.xadd.side_effect = ValkeyError('Test error')
        result = await stream_add(key, field_dict)
        assert 'Error adding to stream' in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_stream_delete(self, mock_connection):
        """Test deleting a single entry from stream."""
        key = 'test_stream'
        id = '1234567890-0'

        # Test successful delete
        mock_connection.xdel.return_value = 1
        result = await stream_delete(key, id)
        assert 'Successfully deleted 1 entries from stream' in result
        mock_connection.xdel.assert_called_with(key, id)

        # Test error handling
        mock_connection.xdel.side_effect = ValkeyError('Test error')
        result = await stream_delete(key, id)
        assert 'Error deleting from stream' in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_stream_trim_options(self, mock_connection):
        """Test trimming stream with different options."""
        key = 'test_stream'
        maxlen = 1000

        # Test approximate trim
        mock_connection.xtrim.return_value = 5
        result = await stream_trim(key, maxlen)
        assert 'Successfully trimmed stream' in result
        assert 'removed 5 entries' in result
        mock_connection.xtrim.assert_called_with(key, maxlen=maxlen, approximate=True)

        # Test exact trim
        result = await stream_trim(key, maxlen, approximate=False)
        mock_connection.xtrim.assert_called_with(key, maxlen=maxlen, approximate=False)

        # Test error handling
        mock_connection.xtrim.side_effect = ValkeyError('Test error')
        result = await stream_trim(key, maxlen)
        assert 'Error trimming stream' in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_stream_range_options(self, mock_connection):
        """Test getting range with different options."""
        key = 'test_stream'
        entries = [
            ('1234567890-0', {'field1': 'value1'}),
            ('1234567890-1', {'field2': 'value2'}),
        ]

        # Test forward range
        mock_connection.xrange.return_value = entries
        result = await stream_range(key, start='0', end='9999999999')
        assert str(entries) in result
        mock_connection.xrange.assert_called_with(key, '0', '9999999999', count=None)

        # Test reverse range
        mock_connection.xrevrange.return_value = list(reversed(entries))
        result = await stream_range(key, start='0', end='9999999999', reverse=True)
        assert str(list(reversed(entries))) in result
        mock_connection.xrevrange.assert_called_with(key, '9999999999', '0', count=None)

        # Test with count
        result = await stream_range(key, count=5)
        mock_connection.xrange.assert_called_with(key, '-', '+', count=5)

        # Test empty result
        mock_connection.xrange.return_value = []
        result = await stream_range(key)
        assert 'No entries found in range' in result

        # Test error handling
        mock_connection.xrange.side_effect = ValkeyError('Test error')
        result = await stream_range(key)
        assert 'Error getting range from stream' in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_stream_read_options(self, mock_connection):
        """Test reading stream with different options."""
        key = 'test_stream'
        entries = [(key, [('1234567890-0', {'field1': 'value1'})])]

        # Test basic read
        mock_connection.xread.return_value = entries
        result = await stream_read(key)
        assert str(entries) in result
        mock_connection.xread.assert_called_with({key: '$'}, count=None, block=None)

        # Test with count and block
        result = await stream_read(key, count=5, block=1000)
        mock_connection.xread.assert_called_with({key: '$'}, count=5, block=1000)

        # Test with custom last_id
        result = await stream_read(key, last_id='1234567890-0')
        mock_connection.xread.assert_called_with({key: '1234567890-0'}, count=None, block=None)

        # Test no new entries
        mock_connection.xread.return_value = None
        result = await stream_read(key)
        assert 'No new entries in stream' in result

        # Test error handling
        mock_connection.xread.side_effect = ValkeyError('Test error')
        result = await stream_read(key)
        assert 'Error reading from stream' in result
        assert 'Test error' in result

    @pytest.mark.asyncio
    async def test_stream_group_operations(self, mock_connection):
        """Test consumer group operations."""
        key = 'test_stream'
        group = 'test_group'
        consumer = 'test_consumer'

        # Test group create
        result = await stream_group_create(key, group)
        assert 'Successfully created consumer group' in result
        mock_connection.xgroup_create.assert_called_with(key, group, id='$', mkstream=False)

        # Test group create with mkstream
        result = await stream_group_create(key, group, mkstream=True)
        mock_connection.xgroup_create.assert_called_with(key, group, id='$', mkstream=True)

        # Test group create with custom ID
        result = await stream_group_create(key, group, id='0-0')
        mock_connection.xgroup_create.assert_called_with(key, group, id='0-0', mkstream=False)

        # Test group destroy
        mock_connection.xgroup_destroy.return_value = True
        result = await stream_group_destroy(key, group)
        assert 'Successfully destroyed consumer group' in result
        mock_connection.xgroup_destroy.assert_called_with(key, group)

        # Test group destroy - not found
        mock_connection.xgroup_destroy.return_value = False
        result = await stream_group_destroy(key, group)
        assert 'not found' in result

        # Test set ID
        result = await stream_group_set_id(key, group, '1234567890-0')
        assert 'Successfully set last delivered ID' in result
        mock_connection.xgroup_setid.assert_called_with(key, group, '1234567890-0')

        # Test delete consumer
        mock_connection.xgroup_delconsumer.return_value = 5
        result = await stream_group_delete_consumer(key, group, consumer)
        assert 'Successfully deleted consumer' in result
        assert '5 pending entries' in result
        mock_connection.xgroup_delconsumer.assert_called_with(key, group, consumer)

    @pytest.mark.asyncio
    async def test_stream_read_group_options(self, mock_connection):
        """Test reading from consumer group with different options."""
        key = 'test_stream'
        group = 'test_group'
        consumer = 'test_consumer'
        entries = [(key, [('1234567890-0', {'field1': 'value1'})])]

        # Test basic read
        mock_connection.xreadgroup.return_value = entries
        result = await stream_read_group(key, group, consumer)
        assert str(entries) in result
        mock_connection.xreadgroup.assert_called_with(
            group, consumer, {key: '>'}, count=None, block=None, noack=False
        )

        # Test with count, block, and noack
        result = await stream_read_group(key, group, consumer, count=5, block=1000, noack=True)
        mock_connection.xreadgroup.assert_called_with(
            group, consumer, {key: '>'}, count=5, block=1000, noack=True
        )

        # Test no new entries
        mock_connection.xreadgroup.return_value = None
        result = await stream_read_group(key, group, consumer)
        assert 'No new entries for consumer' in result

        # Test error handling
        mock_connection.xreadgroup.side_effect = ValkeyError('Test error')
        result = await stream_read_group(key, group, consumer)
        assert 'Error reading from group' in result
        assert 'Test error' in result
