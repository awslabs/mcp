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
"""Tests for the cache provider module."""

import time
from awslabs.openapi_mcp_server.utils.cache_provider import (
    InMemoryCacheProvider,
    cached,
    create_cache_provider,
)
from unittest.mock import patch


def test_in_memory_cache_provider_init():
    """Test initializing the InMemoryCacheProvider."""
    provider = InMemoryCacheProvider(ttl_seconds=60)
    assert provider._ttl_seconds == 60

    # Test with default values
    with patch('awslabs.openapi_mcp_server.utils.cache_provider.CACHE_TTL', 120):
        provider = InMemoryCacheProvider()
        assert provider._ttl_seconds == 120


def test_in_memory_cache_provider_get_set():
    """Test getting and setting values in the InMemoryCacheProvider."""
    provider = InMemoryCacheProvider(ttl_seconds=60)

    # Set a value
    provider.set('test_key', 'test_value')

    # Get the value
    value = provider.get('test_key')
    assert value == 'test_value'

    # Get a non-existent key
    value = provider.get('non_existent_key')
    assert value is None


def test_in_memory_cache_provider_invalidate():
    """Test invalidating cache entries in the InMemoryCacheProvider."""
    provider = InMemoryCacheProvider(ttl_seconds=60)

    # Set a value
    provider.set('test_key', 'test_value')

    # Invalidate the key
    result = provider.invalidate('test_key')
    assert result is True

    # Key should no longer exist
    value = provider.get('test_key')
    assert value is None

    # Invalidating a non-existent key should return False
    result = provider.invalidate('non_existent_key')
    assert result is False


def test_in_memory_cache_provider_clear():
    """Test clearing all cache entries in the InMemoryCacheProvider."""
    provider = InMemoryCacheProvider(ttl_seconds=60)

    # Set multiple values
    provider.set('key1', 'value1')
    provider.set('key2', 'value2')

    # Clear the cache
    provider.clear()

    # All keys should be gone
    assert provider.get('key1') is None
    assert provider.get('key2') is None


def test_in_memory_cache_provider_ttl():
    """Test time-to-live functionality in the InMemoryCacheProvider."""
    provider = InMemoryCacheProvider(ttl_seconds=1)  # Short TTL for testing

    # Set a value
    provider.set('test_key', 'test_value')

    # Get the value immediately (should exist)
    value = provider.get('test_key')
    assert value == 'test_value'

    # Wait for TTL to expire
    time.sleep(1.1)

    # Value should now be None
    value = provider.get('test_key')
    assert value is None


@patch('awslabs.openapi_mcp_server.utils.cache_provider.USE_CACHETOOLS', False)
def test_create_cache_provider():
    """Test creating the cache provider."""
    provider = create_cache_provider()
    assert isinstance(provider, InMemoryCacheProvider)


def test_cached_decorator():
    """Test the cached decorator."""
    # Create a test function
    call_count = 0

    @cached(ttl_seconds=60)
    def test_function(arg1, arg2=None):
        nonlocal call_count
        call_count += 1
        return f'{arg1}:{arg2}'

    # First call should call the function
    result = test_function('test', arg2='value')
    assert result == 'test:value'
    assert call_count == 1

    # Second call with same args should use cache
    result = test_function('test', arg2='value')
    assert result == 'test:value'
    assert call_count == 1  # Function not called again

    # Call with different args should call the function again
    result = test_function('different', arg2='value')
    assert result == 'different:value'
    assert call_count == 2  # Function called again


def test_cached_decorator_with_complex_args():
    """Test the cached decorator with complex arguments."""
    # Create a test function
    call_count = 0

    @cached(ttl_seconds=60)
    def test_function(arg1, arg2=None, **kwargs):
        nonlocal call_count
        call_count += 1
        return f'{arg1}:{arg2}:{kwargs.get("extra", "none")}'

    # Call with complex args
    result = test_function('test', arg2={'complex': 'value'}, extra=['a', 'b', 'c'])
    assert result == "test:{'complex': 'value'}:['a', 'b', 'c']"
    assert call_count == 1

    # Call again with same args
    result = test_function('test', arg2={'complex': 'value'}, extra=['a', 'b', 'c'])
    assert result == "test:{'complex': 'value'}:['a', 'b', 'c']"
    assert call_count == 1  # Function not called again
