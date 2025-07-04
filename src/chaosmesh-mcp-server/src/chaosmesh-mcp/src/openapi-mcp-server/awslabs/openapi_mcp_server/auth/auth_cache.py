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
"""Authentication caching utilities.

This module provides caching mechanisms for authentication tokens and other data.
"""

import time
from typing import Any, Callable, Dict, Optional, TypeVar, cast


# Type variable for cached function return types
T = TypeVar('T')


class TokenCache:
    """Cache for authentication tokens and related data.

    This class provides a simple time-based cache for authentication tokens
    and other authentication-related data.
    """

    def __init__(self, max_size: int = 100, ttl: int = 300):
        """Initialize the token cache.

        Args:
            max_size: Maximum number of items to store in the cache
            ttl: Time-to-live in seconds for cached items

        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Any: Cached value or None if not found or expired

        """
        if key not in self._cache:
            return None

        item = self._cache[key]
        if time.time() > item['expires_at']:
            # Item has expired
            del self._cache[key]
            return None

        return item['value']

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (overrides default)

        """
        # Ensure we don't exceed max size
        if len(self._cache) >= self._max_size and key not in self._cache:
            # Remove oldest item (simple LRU implementation)
            oldest_key = min(self._cache.items(), key=lambda x: x[1]['expires_at'])[0]
            del self._cache[oldest_key]

        # Calculate expiration time
        expires_at = time.time() + (ttl if ttl is not None else self._ttl)

        # Store the item
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at,
        }

    def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            bool: True if the key was found and deleted, False otherwise

        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()

    def cleanup(self) -> int:
        """Remove expired items from the cache.

        Returns:
            int: Number of items removed

        """
        now = time.time()
        expired_keys = [k for k, v in self._cache.items() if now > v['expires_at']]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


# Global token cache instance
_TOKEN_CACHE = TokenCache()


def get_token_cache() -> TokenCache:
    """Get the global token cache instance.

    Returns:
        TokenCache: Global token cache instance

    """
    return _TOKEN_CACHE


def cached_auth_data(ttl: int = 300) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Cache authentication data.

    Args:
        ttl: Time-to-live in seconds for cached items

    Returns:
        Callable: Decorator function

    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Decorate function with caching.

        Args:
            func: Function to decorate

        Returns:
            Callable: Wrapped function

        """
        cache = get_token_cache()

        def wrapper(*args: Any, **kwargs: Any) -> T:
            """Wrap function with caching logic.

            Args:
                *args: Positional arguments
                **kwargs: Keyword arguments

            Returns:
                T: Function result

            """
            # Create a cache key from the function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f'{k}={v}' for k, v in sorted(kwargs.items()))
            cache_key = ':'.join(key_parts)

            # Check if we have a cached result
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cast(T, cached_result)

            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator
