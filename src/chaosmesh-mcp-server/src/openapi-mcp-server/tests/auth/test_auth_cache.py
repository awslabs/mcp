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
"""Tests for authentication caching."""

import time
import unittest
from awslabs.openapi_mcp_server.auth.auth_cache import (
    TokenCache,
    cached_auth_data,
    get_token_cache,
)


class TestTokenCache(unittest.TestCase):
    """Test cases for the token cache."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = TokenCache(max_size=3, ttl=1)  # Short TTL for testing

    def test_get_set(self):
        """Test getting and setting values in the cache."""
        # Set a value
        self.cache.set('test_key', 'test_value')

        # Get the value
        value = self.cache.get('test_key')
        self.assertEqual(value, 'test_value')

        # Get a non-existent key
        value = self.cache.get('non_existent')
        self.assertIsNone(value)

    def test_expiration(self):
        """Test that values expire after TTL."""
        # Set a value
        self.cache.set('test_key', 'test_value')

        # Value should be available immediately
        value = self.cache.get('test_key')
        self.assertEqual(value, 'test_value')

        # Wait for expiration
        time.sleep(1.1)

        # Value should be expired
        value = self.cache.get('test_key')
        self.assertIsNone(value)

    def test_custom_ttl(self):
        """Test setting a custom TTL for a value."""
        # Set a value with a longer TTL
        self.cache.set('long_ttl', 'long_value', ttl=2)

        # Set a value with the default TTL
        self.cache.set('short_ttl', 'short_value')

        # Wait for default TTL to expire
        time.sleep(1.1)

        # Short TTL value should be expired
        value = self.cache.get('short_ttl')
        self.assertIsNone(value)

        # Long TTL value should still be available
        value = self.cache.get('long_ttl')
        self.assertEqual(value, 'long_value')

    def test_max_size(self):
        """Test that the cache respects max size."""
        # Fill the cache
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')
        self.cache.set('key3', 'value3')

        # All values should be available
        self.assertEqual(self.cache.get('key1'), 'value1')
        self.assertEqual(self.cache.get('key2'), 'value2')
        self.assertEqual(self.cache.get('key3'), 'value3')

        # Add one more value, which should evict the oldest
        self.cache.set('key4', 'value4')

        # The oldest value should be evicted
        self.assertIsNone(self.cache.get('key1'))

        # The other values should still be available
        self.assertEqual(self.cache.get('key2'), 'value2')
        self.assertEqual(self.cache.get('key3'), 'value3')
        self.assertEqual(self.cache.get('key4'), 'value4')

    def test_delete(self):
        """Test deleting values from the cache."""
        # Set a value
        self.cache.set('test_key', 'test_value')

        # Delete the value
        result = self.cache.delete('test_key')
        self.assertTrue(result)

        # Value should be gone
        value = self.cache.get('test_key')
        self.assertIsNone(value)

        # Deleting a non-existent key should return False
        result = self.cache.delete('non_existent')
        self.assertFalse(result)

    def test_clear(self):
        """Test clearing the entire cache."""
        # Set some values
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')

        # Clear the cache
        self.cache.clear()

        # All values should be gone
        self.assertIsNone(self.cache.get('key1'))
        self.assertIsNone(self.cache.get('key2'))

    def test_cleanup(self):
        """Test cleaning up expired items."""
        # Set some values with different TTLs
        self.cache.set('key1', 'value1', ttl=0.5)
        self.cache.set('key2', 'value2', ttl=2)

        # Wait for the first value to expire
        time.sleep(0.6)

        # Cleanup should remove one item
        removed = self.cache.cleanup()
        self.assertEqual(removed, 1)

        # The expired value should be gone
        self.assertIsNone(self.cache.get('key1'))

        # The other value should still be available
        self.assertEqual(self.cache.get('key2'), 'value2')


class TestCachedAuthData(unittest.TestCase):
    """Test cases for the cached_auth_data decorator."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the global cache
        get_token_cache().clear()

        # Create a real function to decorate
        def test_func(*args, **kwargs):
            # Track calls
            test_func.call_count += 1
            return 'test_result'

        # Initialize call counter
        test_func.call_count = 0
        test_func.__name__ = 'test_func'

        # Decorate the function
        self.test_func = test_func
        self.decorated_func = cached_auth_data(ttl=1)(test_func)

    def test_caching(self):
        """Test that the decorator caches function results."""
        # Call the function twice
        result1 = self.decorated_func('arg1', kwarg1='kwarg1')
        result2 = self.decorated_func('arg1', kwarg1='kwarg1')

        # Both calls should return the same result
        self.assertEqual(result1, 'test_result')
        self.assertEqual(result2, 'test_result')

        # The function should only be called once
        self.assertEqual(self.test_func.call_count, 1)

    def test_different_args(self):
        """Test that different arguments result in different cache entries."""
        # Call the function with different arguments
        result1 = self.decorated_func('arg1')
        result2 = self.decorated_func('arg2')

        # Both calls should return the same result
        self.assertEqual(result1, 'test_result')
        self.assertEqual(result2, 'test_result')

        # The function should be called twice
        self.assertEqual(self.test_func.call_count, 2)

    def test_expiration(self):
        """Test that cached results expire after TTL."""
        # Call the function
        result1 = self.decorated_func('arg1')
        self.assertEqual(result1, 'test_result')

        # Wait for expiration
        time.sleep(1.1)

        # Call the function again
        result2 = self.decorated_func('arg1')
        self.assertEqual(result2, 'test_result')

        # The function should be called twice
        self.assertEqual(self.test_func.call_count, 2)


if __name__ == '__main__':
    unittest.main()
