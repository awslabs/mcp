"""
Caching models for CloudWAN MCP Server.

This module provides caching utilities for CloudWAN MCP tools, including:
- Memory-efficient caching with TTL
- Type-safe cache keys
- Cache invalidation policies
"""

import time
import logging
import hashlib
import threading
from enum import Enum
from typing import Any, Dict, Optional, TypeVar, Generic, Union
from functools import lru_cache

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheKey(str, Enum):
    """Enumeration of cache key types."""

    CORE_NETWORK_POLICY = "core_network_policy"
    CORE_NETWORK_EXISTS = "core_network_exists"
    SEGMENT_LIST = "segment_list"
    ATTACHMENTS = "attachments"
    CORE_NETWORKS = "core_networks"
    GLOBAL_NETWORKS = "global_networks"
    VPC_TOPOLOGY = "vpc_topology"
    IP_RESOURCES = "ip_resources"
    ROUTE_TABLES = "route_tables"


class CacheEntry(BaseModel, Generic[T]):
    """Generic cache entry with TTL."""

    key: str
    value: T
    created_at: float = Field(default_factory=time.time)
    expires_at: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        return time.time() > self.expires_at

    @property
    def ttl_remaining(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0.0, self.expires_at - time.time())

    @property
    def age(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.created_at


class MemoryCache:
    """Thread-safe memory-efficient cache with TTL."""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize memory cache.

        Args:
            default_ttl: Default TTL in seconds (default: 300)
            max_size: Maximum cache size (default: 1000)
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry[Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._hit_count = 0
        self._miss_count = 0
        logger.info(f"Initialized MemoryCache (TTL: {default_ttl}s, max_size: {max_size})")

    @staticmethod
    def generate_key(category: Union[str, CacheKey], **kwargs) -> str:
        """
        Generate cache key from parameters.

        Args:
            category: Cache category (use CacheKey enum)
            **kwargs: Key parameters

        Returns:
            Cache key string
        """
        key_parts = [f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None]
        return f"{category}:{hashlib.sha256('|'.join(key_parts).encode()).hexdigest()[:16]}"

    def get(self, category: Union[str, CacheKey], **kwargs) -> Optional[Any]:
        """
        Get value from cache. Thread-safe.

        Args:
            category: Cache category
            **kwargs: Key parameters

        Returns:
            Cached value if found and not expired, None otherwise
        """
        key = self.generate_key(category, **kwargs)

        with self._lock:
            if key not in self._cache:
                logger.debug(f"Cache miss: {key}")
                self._miss_count += 1
                return None

            entry = self._cache[key]
            if entry.is_expired:
                logger.debug(f"Cache expired: {key}")
                self._remove_entry(key)
                self._miss_count += 1
                return None

            self._access_times[key] = time.time()
            self._hit_count += 1
            logger.debug(f"Cache hit: {key} (TTL remaining: {entry.ttl_remaining:.1f}s)")
            return entry.value

    def set(
        self,
        value: Any,
        ttl: Optional[int] = None,
        category: Union[str, CacheKey] = "default",
        **kwargs,
    ) -> None:
        """
        Set value in cache. Thread-safe.

        Args:
            value: Value to cache
            ttl: Time-to-live in seconds (default: class default_ttl)
            category: Cache category
            **kwargs: Key parameters
        """
        key = self.generate_key(category, **kwargs)
        ttl_value = ttl or self.default_ttl

        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=time.time() + ttl_value,
            metadata={"category": str(category)},
        )

        with self._lock:
            self._cache[key] = entry
            self._access_times[key] = time.time()
            logger.debug(f"Cache set: {key} (TTL: {ttl_value}s)")
            self._cleanup()

    def _remove_entry(self, key: str) -> None:
        """
        Remove entry from cache.

        Args:
            key: Cache key
        """
        self._cache.pop(key, None)
        self._access_times.pop(key, None)

    def _cleanup(self) -> None:
        """Clean up expired entries and enforce max size."""
        # Remove expired entries
        now = time.time()
        expired = [k for k, v in self._cache.items() if now > v.expires_at]
        for k in expired:
            self._remove_entry(k)

        # Enforce max size by removing least recently used
        if len(self._cache) > self.max_size:
            lru_keys = sorted(self._access_times, key=self._access_times.get)
            for k in lru_keys[: len(self._cache) - self.max_size]:
                self._remove_entry(k)
                logger.debug(f"Cache eviction (LRU): {k}")

    def invalidate(self, category: Union[str, CacheKey], **kwargs) -> int:
        """
        Invalidate cache entries by category and parameters. Thread-safe.

        Args:
            category: Cache category
            **kwargs: Key parameters (if empty, all entries in category are invalidated)

        Returns:
            Number of invalidated entries
        """
        with self._lock:
            if not kwargs:
                # Invalidate all entries in category
                count = 0
                for k in list(self._cache.keys()):
                    entry = self._cache.get(k)
                    if entry and entry.metadata.get("category") == str(category):
                        self._remove_entry(k)
                        count += 1
                logger.debug(f"Cache invalidated: {count} entries in category {category}")
                return count

            # Invalidate specific entry
            key = self.generate_key(category, **kwargs)
            if key in self._cache:
                self._remove_entry(key)
                logger.debug(f"Cache invalidated: {key}")
                return 1

            return 0

    def clear(self) -> int:
        """
        Clear all cache entries. Thread-safe.

        Returns:
            Number of cleared entries
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_times.clear()
            # Reset metrics
            self._hit_count = 0
            self._miss_count = 0
            logger.info(f"Cache cleared: {count} entries")
            return count

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics. Thread-safe.

        Returns:
            Cache statistics including hit/miss ratio and memory usage
        """
        with self._lock:
            now = time.time()
            categories = {}
            memory_usage = 0

            # Calculate memory usage more accurately using sys.getsizeof when possible
            import sys

            for entry in self._cache.values():
                category = entry.metadata.get("category", "unknown")
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1

                # More accurate memory estimation
                try:
                    # For simple types
                    memory_usage += sys.getsizeof(entry.value)
                except Exception:
                    # Fallback for complex objects
                    memory_usage += len(str(entry.value))

            # Calculate hit ratio
            total_requests = self._hit_count + self._miss_count
            hit_ratio = self._hit_count / total_requests if total_requests > 0 else 0

            return {
                "total_entries": len(self._cache),
                "expired_entries": sum(1 for v in self._cache.values() if v.is_expired),
                "categories": categories,
                "memory_usage": memory_usage,
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "hit_ratio": hit_ratio,
                "requests": total_requests,
            }


# Create global cache instance for module-level caching
memory_cache = MemoryCache()


# Add a module-level lru_cache wrapper that uses the memory cache
def cache(ttl: int = 300, max_size: int = 128, category: Union[str, CacheKey] = "function"):
    """
    Cache decorator for functions.

    Args:
        ttl: Time-to-live in seconds
        max_size: Maximum number of cached function results
        category: Cache category

    Returns:
        Decorated function
    """

    def decorator(func):
        cache_key = f"{func.__module__}.{func.__name__}"

        @lru_cache(maxsize=max_size)
        def _get_key(*args, **kwargs):
            # Create a unique key for the function arguments
            args_key = str(args)
            kwargs_key = str(sorted(kwargs.items()))
            return hashlib.sha256(f"{cache_key}:{args_key}:{kwargs_key}".encode()).hexdigest()

        async def wrapper(*args, **kwargs):
            key = _get_key(*args, **kwargs)
            result = memory_cache.get(category, function_key=cache_key, call_key=key)
            if result is not None:
                return result

            result = await func(*args, **kwargs)
            memory_cache.set(
                result, ttl=ttl, category=category, function_key=cache_key, call_key=key
            )
            return result

        return wrapper

    return decorator


# Utility function for cached AWS requests
async def cached_aws_request(
    client: Any, method_name: str, cache_ttl: int = 300, **kwargs
) -> Dict[str, Any]:
    """
    Execute AWS API request with caching.

    Args:
        client: AWS client
        method_name: Client method to call
        cache_ttl: Cache TTL in seconds
        **kwargs: Method arguments

    Returns:
        API response
    """
    # Generate cache key
    service = client.__class__.__name__.replace("Client", "").lower()
    category = f"aws.{service}.{method_name}"

    # Check cache
    result = memory_cache.get(category, **kwargs)
    if result is not None:
        return result

    # Execute request
    method = getattr(client, method_name)
    response = await method(**kwargs)

    # Cache result
    memory_cache.set(response, ttl=cache_ttl, category=category, **kwargs)

    return response
