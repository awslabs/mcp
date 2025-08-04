"""
Resource caching for CloudWAN MCP with TTL support.

This module provides caching functionality for AWS resources to improve
performance and reduce API calls for repeated operations.
"""

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

T = TypeVar("T")


class CacheKeyStrategy(Enum):
    """Strategy for generating cache keys."""

    DEFAULT = "default"  # Default strategy uses str() representation
    HASH = "hash"  # Hash-based strategy for complex objects
    CUSTOM = "custom"  # Custom strategy provided by caller


@dataclass
class CacheConfig:
    """Configuration for resource cache."""

    ttl: int = 300  # Time-to-live in seconds
    max_size: int = 1000  # Maximum number of entries
    enabled: bool = True  # Whether cache is enabled


class ResourceCache:
    """Thread-safe cache for AWS resources with TTL support."""

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        key_strategy: CacheKeyStrategy = CacheKeyStrategy.DEFAULT,
        custom_key_generator: Optional[Callable[[Any], str]] = None,
        name: str = "resource_cache",
    ):
        """
        Initialize resource cache.

        Args:
            config: Cache configuration
            key_strategy: Strategy for key generation
            custom_key_generator: Custom function for key generation
            name: Cache name for identification
        """
        self.config = config or CacheConfig()
        self.key_strategy = key_strategy
        self.custom_key_generator = custom_key_generator
        self.name = name

        # Thread-safe cache storage
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()

        # Access tracking for LRU-like behavior
        self._access_times: Dict[str, float] = {}

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if it exists and is not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if not self.config.enabled:
            self._misses += 1
            return None

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, timestamp = self._cache[key]
            if time.time() - timestamp > self.config.ttl:
                # Expired
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
                self._misses += 1
                return None

            # Update access time for LRU tracking
            self._access_times[key] = time.time()
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        """
        Store value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to store
        """
        if not self.config.enabled:
            return

        with self._lock:
            # Check if we need to evict entries due to size limit
            if len(self._cache) >= self.config.max_size and key not in self._cache:
                self._evict_oldest()

            self._cache[key] = (value, time.time())
            self._access_times[key] = time.time()

    def get_or_set(self, key: str, value_func: Callable[[], T]) -> T:
        """
        Get value from cache or compute and store it if not present.

        Args:
            key: Cache key
            value_func: Function to compute value if not in cache

        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value

        # Not in cache or expired, compute new value
        value = value_func()
        self.set(key, value)
        return value

    def _evict_oldest(self) -> None:
        """Evict least recently used entry."""
        if not self._access_times:
            return

        # Find oldest entry
        oldest_key = min(self._access_times.items(), key=lambda x: x[1])[0]

        # Remove it
        if oldest_key in self._cache:
            del self._cache[oldest_key]
        del self._access_times[oldest_key]
        self._evictions += 1

    def contains(self, key: str) -> bool:
        """
        Check if key exists in cache and is not expired.

        Args:
            key: Cache key

        Returns:
            True if key exists and is not expired
        """
        if not self.config.enabled:
            return False

        with self._lock:
            if key not in self._cache:
                return False

            _, timestamp = self._cache[key]
            return time.time() - timestamp <= self.config.ttl

    def invalidate(self, key: str) -> None:
        """
        Remove entry from cache.

        Args:
            key: Cache key to remove
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]

    def clear(self) -> None:
        """Remove all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "name": self.name,
                "size": len(self._cache),
                "max_size": self.config.max_size,
                "ttl": self.config.ttl,
                "enabled": self.config.enabled,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
                "active_entries": len(self._cache),
            }

    def _generate_key(self, obj: Any) -> str:
        """
        Generate cache key based on strategy.

        Args:
            obj: Object to generate key for

        Returns:
            Cache key string
        """
        if self.key_strategy == CacheKeyStrategy.HASH:
            return str(hash(str(obj)))
        elif self.key_strategy == CacheKeyStrategy.CUSTOM and self.custom_key_generator:
            return self.custom_key_generator(obj)
        else:
            # Default strategy
            return str(obj)
