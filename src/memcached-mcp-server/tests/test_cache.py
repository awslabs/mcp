"""Unit tests for cache operations."""

import pytest
from awslabs.memcached_mcp_server.tools import cache
from pymemcache.exceptions import MemcacheError
from unittest.mock import Mock, patch


# Mock client for testing
@pytest.fixture
def mock_client():
    """Initialize mock client."""
    with patch(
        'awslabs.memcached_mcp_server.common.connection.MemcachedConnectionManager.get_connection'
    ) as mock:
        client = Mock()
        mock.return_value = client
        yield client


@pytest.mark.asyncio
async def test_cache_gets_success(mock_client):
    """Test successful gets operation."""
    mock_client.gets.return_value = (b'test_value', 123)
    result = await cache.cache_gets('test_key')
    assert result == "Value: b'test_value', CAS: 123"
    mock_client.gets.assert_called_once_with('test_key')


@pytest.mark.asyncio
async def test_cache_gets_not_found(mock_client):
    """Test gets operation when key doesn't exist."""
    mock_client.gets.return_value = None
    result = await cache.cache_gets('missing_key')
    assert result == "Key 'missing_key' not found"
    mock_client.gets.assert_called_once_with('missing_key')


@pytest.mark.asyncio
async def test_cache_gets_error(mock_client):
    """Test gets operation with error."""
    mock_client.gets.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_gets('test_key')
    assert result == "Error getting key 'test_key' with CAS: Connection failed"


@pytest.mark.asyncio
async def test_cache_get_success(mock_client):
    """Test successful get operation."""
    mock_client.get.return_value = b'test_value'
    result = await cache.cache_get('test_key')
    assert result == "b'test_value'"
    mock_client.get.assert_called_once_with('test_key')


@pytest.mark.asyncio
async def test_cache_get_not_found(mock_client):
    """Test get operation when key doesn't exist."""
    mock_client.get.return_value = None
    result = await cache.cache_get('missing_key')
    assert result == "Key 'missing_key' not found"
    mock_client.get.assert_called_once_with('missing_key')


@pytest.mark.asyncio
async def test_cache_get_error(mock_client):
    """Test get operation with error."""
    mock_client.get.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_get('test_key')
    assert result == "Error getting key 'test_key': Connection failed"


@pytest.mark.asyncio
async def test_cache_set_success(mock_client):
    """Test successful set operation."""
    mock_client.set.return_value = True
    result = await cache.cache_set('test_key', 'test_value')
    assert result == "Successfully set key 'test_key'"
    mock_client.set.assert_called_once_with('test_key', 'test_value', expire=None)


@pytest.mark.asyncio
async def test_cache_set_with_expiry(mock_client):
    """Test set operation with expiry."""
    mock_client.set.return_value = True
    result = await cache.cache_set('test_key', 'test_value', expire=60)
    assert result == "Successfully set key 'test_key' with 60s expiry"
    mock_client.set.assert_called_once_with('test_key', 'test_value', expire=60)


@pytest.mark.asyncio
async def test_cache_set_error(mock_client):
    """Test set operation with error."""
    mock_client.set.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_set('test_key', 'test_value')
    assert result == "Error setting key 'test_key': Connection failed"


@pytest.mark.asyncio
async def test_cache_delete_success(mock_client):
    """Test successful delete operation."""
    mock_client.delete.return_value = True
    result = await cache.cache_delete('test_key')
    assert result == "Successfully deleted key 'test_key'"
    mock_client.delete.assert_called_once_with('test_key')


@pytest.mark.asyncio
async def test_cache_delete_not_found(mock_client):
    """Test delete operation when key doesn't exist."""
    mock_client.delete.return_value = False
    result = await cache.cache_delete('missing_key')
    assert result == "Key 'missing_key' not found"
    mock_client.delete.assert_called_once_with('missing_key')


@pytest.mark.asyncio
async def test_cache_get_many_success(mock_client):
    """Test successful get_many operation."""
    mock_client.get_many.return_value = {'key1': 'value1', 'key2': 'value2'}
    result = await cache.cache_get_many(['key1', 'key2'])
    assert result == "{'key1': 'value1', 'key2': 'value2'}"
    mock_client.get_many.assert_called_once_with(['key1', 'key2'])


@pytest.mark.asyncio
async def test_cache_get_many_empty(mock_client):
    """Test get_many operation with no results."""
    mock_client.get_many.return_value = {}
    result = await cache.cache_get_many(['key1', 'key2'])
    assert result == 'No keys found'


@pytest.mark.asyncio
async def test_cache_incr_success(mock_client):
    """Test successful increment operation."""
    mock_client.incr.return_value = 2
    result = await cache.cache_incr('counter')
    assert result == '2'
    mock_client.incr.assert_called_once_with('counter', 1)


@pytest.mark.asyncio
async def test_cache_incr_not_found(mock_client):
    """Test increment operation when key doesn't exist."""
    mock_client.incr.return_value = None
    result = await cache.cache_incr('missing_counter')
    assert result == "Key 'missing_counter' not found or not a counter"


@pytest.mark.asyncio
async def test_cache_flush_all_success(mock_client):
    """Test successful flush_all operation."""
    result = await cache.cache_flush_all()
    assert result == 'Successfully flushed all cache entries'
    mock_client.flush_all.assert_called_once_with(delay=0)


@pytest.mark.asyncio
async def test_cache_flush_all_with_delay(mock_client):
    """Test flush_all operation with delay."""
    result = await cache.cache_flush_all(delay=5)
    assert result == 'Successfully flushed all cache entries with 5s delay'
    mock_client.flush_all.assert_called_once_with(delay=5)


@pytest.mark.asyncio
async def test_cache_cas_success(mock_client):
    """Test successful CAS operation."""
    mock_client.cas.return_value = True
    result = await cache.cache_cas('test_key', 'test_value', 123)
    assert result == "Successfully set key 'test_key' using CAS"
    mock_client.cas.assert_called_once_with('test_key', 'test_value', 123, expire=None)


@pytest.mark.asyncio
async def test_cache_cas_with_expiry(mock_client):
    """Test CAS operation with expiry."""
    mock_client.cas.return_value = True
    result = await cache.cache_cas('test_key', 'test_value', 123, expire=60)
    assert result == "Successfully set key 'test_key' using CAS with 60s expiry"
    mock_client.cas.assert_called_once_with('test_key', 'test_value', 123, expire=60)


@pytest.mark.asyncio
async def test_cache_cas_failed(mock_client):
    """Test failed CAS operation (value changed)."""
    mock_client.cas.return_value = False
    result = await cache.cache_cas('test_key', 'test_value', 123)
    assert result == "CAS operation failed for key 'test_key' (value changed)"


@pytest.mark.asyncio
async def test_cache_cas_error(mock_client):
    """Test CAS operation with error."""
    mock_client.cas.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_cas('test_key', 'test_value', 123)
    assert result == "Error setting key 'test_key' with CAS: Connection failed"


@pytest.mark.asyncio
async def test_cache_set_many_error(mock_client):
    """Test set_many operation with error."""
    mock_client.set_many.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_set_many({'key1': 'value1', 'key2': 'value2'})
    assert result == 'Error setting multiple keys: Connection failed'


@pytest.mark.asyncio
async def test_cache_set_many_partial_failure(mock_client):
    """Test set_many operation with partial failure."""
    mock_client.set_many.return_value = ['key2']
    result = await cache.cache_set_many({'key1': 'value1', 'key2': 'value2'})
    assert result == "Failed to set keys: ['key2']"


@pytest.mark.asyncio
async def test_cache_add_success(mock_client):
    """Test successful add operation."""
    mock_client.add.return_value = True
    result = await cache.cache_add('test_key', 'test_value')
    assert result == "Successfully added key 'test_key'"
    mock_client.add.assert_called_once_with('test_key', 'test_value', expire=None)


@pytest.mark.asyncio
async def test_cache_add_exists(mock_client):
    """Test add operation when key exists."""
    mock_client.add.return_value = False
    result = await cache.cache_add('test_key', 'test_value')
    assert result == "Key 'test_key' already exists"


@pytest.mark.asyncio
async def test_cache_add_error(mock_client):
    """Test add operation with error."""
    mock_client.add.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_add('test_key', 'test_value')
    assert result == "Error adding key 'test_key': Connection failed"


@pytest.mark.asyncio
async def test_cache_replace_success(mock_client):
    """Test successful replace operation."""
    mock_client.replace.return_value = True
    result = await cache.cache_replace('test_key', 'test_value')
    assert result == "Successfully replaced key 'test_key'"
    mock_client.replace.assert_called_once_with('test_key', 'test_value', expire=None)


@pytest.mark.asyncio
async def test_cache_replace_not_found(mock_client):
    """Test replace operation when key doesn't exist."""
    mock_client.replace.return_value = False
    result = await cache.cache_replace('test_key', 'test_value')
    assert result == "Key 'test_key' not found"


@pytest.mark.asyncio
async def test_cache_replace_error(mock_client):
    """Test replace operation with error."""
    mock_client.replace.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_replace('test_key', 'test_value')
    assert result == "Error replacing key 'test_key': Connection failed"


@pytest.mark.asyncio
async def test_cache_append_success(mock_client):
    """Test successful append operation."""
    mock_client.append.return_value = True
    result = await cache.cache_append('test_key', 'test_value')
    assert result == "Successfully appended to key 'test_key'"
    mock_client.append.assert_called_once_with('test_key', 'test_value')


@pytest.mark.asyncio
async def test_cache_append_not_found(mock_client):
    """Test append operation when key doesn't exist."""
    mock_client.append.return_value = False
    result = await cache.cache_append('test_key', 'test_value')
    assert result == "Key 'test_key' not found or not a string"


@pytest.mark.asyncio
async def test_cache_append_error(mock_client):
    """Test append operation with error."""
    mock_client.append.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_append('test_key', 'test_value')
    assert result == "Error appending to key 'test_key': Connection failed"


@pytest.mark.asyncio
async def test_cache_prepend_success(mock_client):
    """Test successful prepend operation."""
    mock_client.prepend.return_value = True
    result = await cache.cache_prepend('test_key', 'test_value')
    assert result == "Successfully prepended to key 'test_key'"
    mock_client.prepend.assert_called_once_with('test_key', 'test_value')


@pytest.mark.asyncio
async def test_cache_prepend_not_found(mock_client):
    """Test prepend operation when key doesn't exist."""
    mock_client.prepend.return_value = False
    result = await cache.cache_prepend('test_key', 'test_value')
    assert result == "Key 'test_key' not found or not a string"


@pytest.mark.asyncio
async def test_cache_prepend_error(mock_client):
    """Test prepend operation with error."""
    mock_client.prepend.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_prepend('test_key', 'test_value')
    assert result == "Error prepending to key 'test_key': Connection failed"


@pytest.mark.asyncio
async def test_cache_delete_error(mock_client):
    """Test delete operation with error."""
    mock_client.delete.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_delete('test_key')
    assert result == "Error deleting key 'test_key': Connection failed"


@pytest.mark.asyncio
async def test_cache_delete_many_success(mock_client):
    """Test successful delete_many operation."""
    mock_client.delete_many.return_value = []
    result = await cache.cache_delete_many(['key1', 'key2'])
    assert result == 'Successfully deleted 2 keys'
    mock_client.delete_many.assert_called_once_with(['key1', 'key2'])


@pytest.mark.asyncio
async def test_cache_delete_many_partial_failure(mock_client):
    """Test delete_many operation with partial failure."""
    mock_client.delete_many.return_value = ['key2']
    result = await cache.cache_delete_many(['key1', 'key2'])
    assert result == "Failed to delete keys: ['key2']"


@pytest.mark.asyncio
async def test_cache_delete_many_error(mock_client):
    """Test delete_many operation with error."""
    mock_client.delete_many.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_delete_many(['key1', 'key2'])
    assert result == 'Error deleting multiple keys: Connection failed'


@pytest.mark.asyncio
async def test_cache_incr_error(mock_client):
    """Test increment operation with error."""
    mock_client.incr.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_incr('counter')
    assert result == "Error incrementing key 'counter': Connection failed"


@pytest.mark.asyncio
async def test_cache_decr_success(mock_client):
    """Test successful decrement operation."""
    mock_client.decr.return_value = 1
    result = await cache.cache_decr('counter')
    assert result == '1'
    mock_client.decr.assert_called_once_with('counter', 1)


@pytest.mark.asyncio
async def test_cache_decr_not_found(mock_client):
    """Test decrement operation when key doesn't exist."""
    mock_client.decr.return_value = None
    result = await cache.cache_decr('missing_counter')
    assert result == "Key 'missing_counter' not found or not a counter"


@pytest.mark.asyncio
async def test_cache_decr_error(mock_client):
    """Test decrement operation with error."""
    mock_client.decr.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_decr('counter')
    assert result == "Error decrementing key 'counter': Connection failed"


@pytest.mark.asyncio
async def test_cache_touch_success(mock_client):
    """Test successful touch operation."""
    mock_client.touch.return_value = True
    result = await cache.cache_touch('test_key', 60)
    assert result == "Successfully updated expiry for key 'test_key' to 60s"
    mock_client.touch.assert_called_once_with('test_key', 60)


@pytest.mark.asyncio
async def test_cache_touch_not_found(mock_client):
    """Test touch operation when key doesn't exist."""
    mock_client.touch.return_value = False
    result = await cache.cache_touch('test_key', 60)
    assert result == "Key 'test_key' not found"


@pytest.mark.asyncio
async def test_cache_touch_error(mock_client):
    """Test touch operation with error."""
    mock_client.touch.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_touch('test_key', 60)
    assert result == "Error touching key 'test_key': Connection failed"


@pytest.mark.asyncio
async def test_cache_stats_success(mock_client):
    """Test successful stats operation."""
    mock_client.stats.return_value = {'hits': 100, 'misses': 10}
    result = await cache.cache_stats()
    assert result == "{'hits': 100, 'misses': 10}"
    mock_client.stats.assert_called_once_with()


@pytest.mark.asyncio
async def test_cache_stats_with_args(mock_client):
    """Test stats operation with specific args."""
    mock_client.stats.return_value = {'items': {'1': {'number': 100}}}
    result = await cache.cache_stats(['items'])
    assert result == "{'items': {'1': {'number': 100}}}"
    mock_client.stats.assert_called_once_with('items')


@pytest.mark.asyncio
async def test_cache_stats_error(mock_client):
    """Test stats operation with error."""
    mock_client.stats.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_stats()
    assert result == 'Error getting stats: Connection failed'


@pytest.mark.asyncio
async def test_cache_flush_all_error(mock_client):
    """Test flush_all operation with error."""
    mock_client.flush_all.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_flush_all()
    assert result == 'Error flushing cache: Connection failed'


@pytest.mark.asyncio
async def test_cache_quit_success(mock_client):
    """Test successful quit operation."""
    with patch(
        'awslabs.memcached_mcp_server.common.connection.MemcachedConnectionManager.close_connection'
    ) as mock_close:
        result = await cache.cache_quit()
        assert result == 'Successfully closed connection'
        mock_client.quit.assert_called_once()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_cache_quit_error(mock_client):
    """Test quit operation with error."""
    mock_client.quit.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_quit()
    assert result == 'Error closing connection: Connection failed'


@pytest.mark.asyncio
async def test_cache_version_error(mock_client):
    """Test version operation with error."""
    mock_client.version.side_effect = MemcacheError('Connection failed')
    result = await cache.cache_version()
    assert result == 'Error getting version: Connection failed'


@pytest.mark.asyncio
async def test_cache_version_success(mock_client):
    """Test successful version operation."""
    mock_client.version.return_value = '1.6.9'
    result = await cache.cache_version()
    assert result == '1.6.9'
    mock_client.version.assert_called_once()
