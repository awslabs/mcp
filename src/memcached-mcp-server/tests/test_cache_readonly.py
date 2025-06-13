"""Tests for readonly mode in Cache functionality in the memcached MCP server."""

import pytest
from awslabs.memcached_mcp_server.tools.cache import (
    cache_add,
    cache_append,
    cache_cas,
    cache_decr,
    cache_delete,
    cache_delete_many,
    cache_flush_all,
    cache_incr,
    cache_prepend,
    cache_replace,
    cache_set,
    cache_set_many,
    cache_touch,
)
from unittest.mock import Mock, patch


class TestCacheReadonly:
    """Tests for Cache operations in readonly mode."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Memcached client."""
        with patch(
            'awslabs.memcached_mcp_server.common.connection.MemcachedConnectionManager.get_connection'
        ) as mock:
            client = Mock()
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_context(self):
        """Create a mock Context."""
        with patch('awslabs.memcached_mcp_server.tools.cache.Context') as mock_ctx:
            mock_ctx.readonly_mode.return_value = True
            yield mock_ctx

    @pytest.mark.asyncio
    async def test_cache_set_readonly(self, mock_client, mock_context):
        """Test setting a value in readonly mode."""
        key = 'test_key'
        value = 'test_value'

        result = await cache_set(key, value)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_delete_readonly(self, mock_client, mock_context):
        """Test deleting a value in readonly mode."""
        key = 'test_key'

        result = await cache_delete(key)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_incr_readonly(self, mock_client, mock_context):
        """Test incrementing a counter in readonly mode."""
        key = 'counter'

        result = await cache_incr(key)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.incr.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_append_readonly(self, mock_client, mock_context):
        """Test appending to a value in readonly mode."""
        key = 'test_key'
        value = 'test_value'

        result = await cache_append(key, value)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.append.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_flush_all_readonly(self, mock_client, mock_context):
        """Test flushing all cache entries in readonly mode."""
        result = await cache_flush_all()
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.flush_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_cas_readonly(self, mock_client, mock_context):
        """Test CAS operation in readonly mode."""
        key = 'test_key'
        value = 'test_value'
        cas = 123

        result = await cache_cas(key, value, cas)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.cas.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_set_many_readonly(self, mock_client, mock_context):
        """Test setting multiple values in readonly mode."""
        mapping = {'key1': 'value1', 'key2': 'value2'}

        result = await cache_set_many(mapping)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.set_many.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_add_readonly(self, mock_client, mock_context):
        """Test adding a value in readonly mode."""
        key = 'test_key'
        value = 'test_value'

        result = await cache_add(key, value)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_replace_readonly(self, mock_client, mock_context):
        """Test replacing a value in readonly mode."""
        key = 'test_key'
        value = 'test_value'

        result = await cache_replace(key, value)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.replace.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_prepend_readonly(self, mock_client, mock_context):
        """Test prepending to a value in readonly mode."""
        key = 'test_key'
        value = 'test_value'

        result = await cache_prepend(key, value)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.prepend.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_delete_many_readonly(self, mock_client, mock_context):
        """Test deleting multiple values in readonly mode."""
        keys = ['key1', 'key2']

        result = await cache_delete_many(keys)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.delete_many.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_decr_readonly(self, mock_client, mock_context):
        """Test decrementing a counter in readonly mode."""
        key = 'counter'

        result = await cache_decr(key)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.decr.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_touch_readonly(self, mock_client, mock_context):
        """Test touching a key in readonly mode."""
        key = 'test_key'
        expire = 60

        result = await cache_touch(key, expire)
        assert 'Operation not permitted: Server is in readonly mode' in result
        mock_client.touch.assert_not_called()
