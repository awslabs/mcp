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
"""Cache provider for the OpenAPI MCP Server.

This module provides a pluggable caching system with different backends.
The default is a simple in-memory implementation, but it can be switched
to use external caching systems via environment variables.
"""

import time
from abc import ABC, abstractmethod
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.utils.config import CACHE_MAXSIZE, CACHE_TTL, USE_CACHETOOLS
from typing import Any, Callable, Dict, Generic, Optional, TypeVar


# Type variable for generic cache implementation
T = TypeVar('T')

# Try to import cachetools if enabled
CACHETOOLS_AVAILABLE = False
cachetools = None
if USE_CACHETOOLS:
    try:
        import cachetools

        CACHETOOLS_AVAILABLE = True
        logger.info('cachetools caching enabled')
    except ImportError:
        logger.warning(
            'cachetools requested but not installed. Install with: pip install cachetools'
        )


class CacheProvider(Generic[T], ABC):
    """Abstract base class for cache providers."""

    @abstractmethod
    def get(self, key: str) -> Optional[T]:
        """Get a value from the cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: T) -> None:
        """Set a value in the cache."""
        pass

    @abstractmethod
    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from the cache."""
        pass


class InMemoryCacheProvider(CacheProvider[T]):
    """Simple in-memory cache provider with TTL support."""

    def __init__(self, ttl_seconds: Optional[int] = None):
        """Initialize the cache provider.

        Args:
            ttl_seconds: Time-to-live in seconds for cache entries (defaults to config value)

        """
        self._cache: Dict[str, tuple[T, float]] = {}
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else CACHE_TTL
        logger.debug(f'Created in-memory cache provider with TTL of {self._ttl_seconds} seconds')

    def get(self, key: str) -> Optional[T]:
        """Get a value from the cache."""
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]
        if time.time() > expiry:
            # Entry has expired
            del self._cache[key]
            logger.debug(f'Cache entry expired: {key}')
            return None

        logger.debug(f'Cache hit: {key}')
        return value

    def set(self, key: str, value: T) -> None:
        """Set a value in the cache."""
        expiry = time.time() + self._ttl_seconds
        self._cache[key] = (value, expiry)
        logger.debug(f'Cache set: {key} (expires in {self._ttl_seconds} seconds)')

    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f'Cache invalidated: {key}')
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        count = len(self._cache)
        self._cache.clear()
        logger.debug(f'Cache cleared ({count} entries removed)')

    def cleanup(self) -> int:
        """Remove all expired entries from the cache.

        Returns:
            int: Number of entries removed

        """
        now = time.time()
        expired_keys = [key for key, (_, expiry) in self._cache.items() if now > expiry]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f'Cache cleanup: removed {len(expired_keys)} expired entries')

        return len(expired_keys)


class CachetoolsProvider(CacheProvider[T]):
    """Cache provider using the cachetools library."""

    def __init__(self, ttl_seconds: Optional[int] = None, maxsize: Optional[int] = None):
        """Initialize the cache provider.

        Args:
            ttl_seconds: Time-to-live in seconds for cache entries (defaults to config value)
            maxsize: Maximum number of entries in the cache (defaults to config value)

        """
        if not CACHETOOLS_AVAILABLE or cachetools is None:
            raise ImportError('cachetools not available')

        # Use configuration values if not explicitly provided
        ttl_seconds = ttl_seconds if ttl_seconds is not None else CACHE_TTL
        maxsize = maxsize if maxsize is not None else CACHE_MAXSIZE

        self._cache = cachetools.TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        logger.debug(
            f'Created cachetools cache provider with TTL of {ttl_seconds} seconds and maxsize of {maxsize}'
        )

    def get(self, key: str) -> Optional[T]:
        """Get a value from the cache."""
        try:
            value = self._cache[key]
            logger.debug(f'Cache hit: {key}')
            return value
        except KeyError:
            logger.debug(f'Cache miss: {key}')
            return None

    def set(self, key: str, value: T) -> None:
        """Set a value in the cache."""
        self._cache[key] = value
        logger.debug(f'Cache set: {key}')

    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        try:
            del self._cache[key]
            logger.debug(f'Cache invalidated: {key}')
            return True
        except KeyError:
            return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        count = len(self._cache)
        self._cache.clear()
        logger.debug(f'Cache cleared ({count} entries removed)')


# Create the appropriate cache provider based on configuration
def create_cache_provider(ttl_seconds: Optional[int] = None) -> CacheProvider:
    """Create a cache provider based on configuration.

    Args:
        ttl_seconds: Time-to-live in seconds for cache entries (defaults to config value)

    Returns:
        CacheProvider: The cache provider

    """
    # Use configuration value if not explicitly provided
    ttl_seconds = ttl_seconds if ttl_seconds is not None else CACHE_TTL

    if USE_CACHETOOLS and CACHETOOLS_AVAILABLE:
        try:
            return CachetoolsProvider(ttl_seconds=ttl_seconds, maxsize=CACHE_MAXSIZE)
        except Exception as e:
            logger.error(f'Failed to create cachetools cache provider: {e}')
            logger.info('Falling back to in-memory cache provider')

    # Default to in-memory provider
    return InMemoryCacheProvider(ttl_seconds=ttl_seconds)


def cached(ttl_seconds: Optional[int] = None) -> Callable:
    """Cache function results.

    Args:
        ttl_seconds: Time-to-live in seconds for cache entries (defaults to config value)

    Returns:
        Callable: Decorated function with caching

    """
    cache = create_cache_provider(ttl_seconds=ttl_seconds)

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create a cache key from the function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f'{k}={v}' for k, v in sorted(kwargs.items()))
            cache_key = ':'.join(key_parts)

            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result

        return wrapper

    return decorator
