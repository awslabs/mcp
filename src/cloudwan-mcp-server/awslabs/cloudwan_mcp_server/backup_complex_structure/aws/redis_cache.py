"""
Distributed Redis Cache Layer for CloudWAN MCP Server.

This module provides a high-performance, distributed caching layer using Redis
for sharing data across multiple MCP server instances. Features include:
- Multi-level caching (L1: memory, L2: Redis)
- TTL-based cache invalidation
- Performance analytics integration
- Encryption and security
- Cache warming and preloading
"""

import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass
from enum import Enum

try:
    import redis.asyncio as redis
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .client_manager import KMSDataEncryption

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels for different data types."""

    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_PERSISTENT = "l3_persistent"


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    total_requests: int = 0
    total_response_time: float = 0.0
    cache_size_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hit_count / self.total_requests

    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests


@dataclass
class CacheTTLConfig:
    """TTL configuration for different data types."""

    # CloudWAN Infrastructure (changes infrequently)
    core_network_policies: int = 1800  # 30 minutes
    global_networks: int = 3600  # 1 hour
    segments: int = 1800  # 30 minutes

    # Network Resources (moderate change frequency)
    vpc_resources: int = 600  # 10 minutes
    transit_gateways: int = 600  # 10 minutes
    route_tables: int = 300  # 5 minutes

    # Dynamic Data (changes frequently)
    ip_lookups: int = 120  # 2 minutes
    network_interfaces: int = 180  # 3 minutes
    security_groups: int = 300  # 5 minutes

    # Analytics and Metrics (short-lived)
    performance_metrics: int = 60  # 1 minute
    health_checks: int = 30  # 30 seconds

    def get_ttl(self, data_type: str) -> int:
        """Get TTL for specific data type."""
        return getattr(self, data_type, 300)  # Default 5 minutes


class DistributedCloudWANCache:
    """
    High-performance distributed cache for CloudWAN MCP Server.

    Provides multi-level caching with Redis as L2 cache and in-memory as L1 cache.
    Includes performance monitoring, encryption, and intelligent cache warming.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        enable_encryption: bool = True,
        ttl_config: Optional[CacheTTLConfig] = None,
        max_memory_cache_size: int = 1000,
        enable_analytics: bool = True,
        cache_prefix: str = "cloudwan_mcp",
    ):
        self.redis_url = redis_url
        self.enable_encryption = enable_encryption and REDIS_AVAILABLE
        self.ttl_config = ttl_config or CacheTTLConfig()
        self.max_memory_cache_size = max_memory_cache_size
        self.enable_analytics = enable_analytics
        self.cache_prefix = cache_prefix

        # Redis connection
        self._redis: Optional[redis.Redis] = None
        self._redis_available = False

        # L1 Memory cache
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._memory_access_times: Dict[str, float] = {}

        # Performance metrics
        self._metrics = CacheMetrics()
        self._analytics_data: List[Dict[str, Any]] = []

        # Encryption
        self._encryption = KMSDataEncryption(enable_encryption=enable_encryption)

        # Cache warming configuration
        self._warming_tasks: Set[str] = set()
        self._warming_callbacks: Dict[str, Callable] = {}

        logger.info(f"Initialized DistributedCloudWANCache with Redis: {redis_url}")

    async def initialize(self) -> bool:
        """Initialize Redis connection and validate configuration."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using memory-only cache")
            return False

        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            await self._redis.ping()
            self._redis_available = True

            logger.info("Successfully connected to Redis cache")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._redis_available = False
            return False

    def _generate_cache_key(self, operation: str, **kwargs) -> str:
        """Generate a consistent cache key for the operation and parameters."""
        # Sort kwargs to ensure consistent key generation
        key_parts = [f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None]
        key_string = f"{operation}|{','.join(key_parts)}"

        # Hash long keys to prevent Redis key length issues
        if len(key_string) > 200:
            key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
            key_string = f"{operation}_hash_{key_hash}"

        return f"{self.cache_prefix}:{key_string}"

    async def get(self, operation: str, data_type: str = "default", **kwargs) -> Optional[Any]:
        """
        Get data from cache with multi-level lookup.

        Args:
            operation: The operation being cached
            data_type: Type of data for TTL configuration
            **kwargs: Parameters for cache key generation

        Returns:
            Cached data or None if not found
        """
        start_time = time.time()
        cache_key = self._generate_cache_key(operation, **kwargs)

        try:
            # L1: Memory cache lookup
            cached_data = self._get_from_memory(cache_key)
            if cached_data is not None:
                self._record_hit(time.time() - start_time, "L1")
                return cached_data

            # L2: Redis cache lookup
            if self._redis_available:
                cached_data = await self._get_from_redis(cache_key)
                if cached_data is not None:
                    # Store in L1 for faster future access
                    self._store_in_memory(cache_key, cached_data, data_type)
                    self._record_hit(time.time() - start_time, "L2")
                    return cached_data

            # Cache miss
            self._record_miss(time.time() - start_time)
            return None

        except Exception as e:
            logger.error(f"Cache get error for {cache_key}: {e}")
            self._record_miss(time.time() - start_time)
            return None

    async def set(
        self,
        data: Any,
        operation: str,
        data_type: str = "default",
        ttl_override: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """
        Store data in cache at multiple levels.

        Args:
            data: Data to cache
            operation: The operation being cached
            data_type: Type of data for TTL configuration
            ttl_override: Override TTL for this specific cache entry
            **kwargs: Parameters for cache key generation

        Returns:
            True if successfully cached, False otherwise
        """
        cache_key = self._generate_cache_key(operation, **kwargs)
        ttl = ttl_override or self.ttl_config.get_ttl(data_type)

        try:
            # Store in L1 memory cache
            self._store_in_memory(cache_key, data, data_type, ttl)

            # Store in L2 Redis cache
            if self._redis_available:
                await self._store_in_redis(cache_key, data, ttl)

            return True

        except Exception as e:
            logger.error(f"Cache set error for {cache_key}: {e}")
            return False

    def _get_from_memory(self, cache_key: str) -> Optional[Any]:
        """Get data from L1 memory cache."""
        if cache_key not in self._memory_cache:
            return None

        entry = self._memory_cache[cache_key]

        # Check expiration
        if time.time() > entry.get("expires_at", 0):
            self._remove_from_memory(cache_key)
            return None

        # Update access time for LRU
        self._memory_access_times[cache_key] = time.time()

        return entry["data"]

    def _store_in_memory(
        self, cache_key: str, data: Any, data_type: str, ttl: Optional[int] = None
    ) -> None:
        """Store data in L1 memory cache."""
        if ttl is None:
            ttl = self.ttl_config.get_ttl(data_type)

        self._memory_cache[cache_key] = {
            "data": data,
            "expires_at": time.time() + ttl,
            "data_type": data_type,
        }

        self._memory_access_times[cache_key] = time.time()

        # Cleanup if cache is too large
        self._cleanup_memory_cache()

    async def _get_from_redis(self, cache_key: str) -> Optional[Any]:
        """Get data from L2 Redis cache."""
        if not self._redis:
            return None

        try:
            cached_data = await self._redis.get(cache_key)
            if cached_data is None:
                return None

            # Decrypt if encryption is enabled
            if self.enable_encryption:
                cached_data = self._encryption.decrypt(cached_data, cache_key)

            return json.loads(cached_data)

        except Exception as e:
            logger.error(f"Redis get error for {cache_key}: {e}")
            return None

    async def _store_in_redis(self, cache_key: str, data: Any, ttl: int) -> None:
        """Store data in L2 Redis cache."""
        if not self._redis:
            return

        try:
            # Serialize data
            serialized_data = json.dumps(data, default=str)

            # Encrypt if encryption is enabled
            if self.enable_encryption:
                serialized_data = self._encryption.encrypt(serialized_data, cache_key)

            # Store with TTL
            await self._redis.setex(cache_key, ttl, serialized_data)

        except Exception as e:
            logger.error(f"Redis set error for {cache_key}: {e}")

    def _remove_from_memory(self, cache_key: str) -> None:
        """Remove entry from memory cache."""
        self._memory_cache.pop(cache_key, None)
        self._memory_access_times.pop(cache_key, None)

    def _cleanup_memory_cache(self) -> None:
        """Cleanup memory cache using LRU eviction."""
        if len(self._memory_cache) <= self.max_memory_cache_size:
            return

        # Remove expired entries first
        now = time.time()
        expired_keys = [
            key for key, entry in self._memory_cache.items() if now > entry.get("expires_at", 0)
        ]

        for key in expired_keys:
            self._remove_from_memory(key)
            self._metrics.eviction_count += 1

        # If still over limit, remove LRU entries
        if len(self._memory_cache) > self.max_memory_cache_size:
            lru_keys = sorted(
                self._memory_access_times.keys(),
                key=lambda k: self._memory_access_times[k],
            )

            excess_count = len(self._memory_cache) - self.max_memory_cache_size
            for key in lru_keys[:excess_count]:
                self._remove_from_memory(key)
                self._metrics.eviction_count += 1

    def _record_hit(self, response_time: float, cache_level: str) -> None:
        """Record cache hit metrics."""
        self._metrics.hit_count += 1
        self._metrics.total_requests += 1
        self._metrics.total_response_time += response_time

        if self.enable_analytics:
            self._analytics_data.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "hit",
                    "cache_level": cache_level,
                    "response_time": response_time,
                }
            )

    def _record_miss(self, response_time: float) -> None:
        """Record cache miss metrics."""
        self._metrics.miss_count += 1
        self._metrics.total_requests += 1
        self._metrics.total_response_time += response_time

        if self.enable_analytics:
            self._analytics_data.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "miss",
                    "response_time": response_time,
                }
            )

    async def warm_cache(
        self,
        operations: List[str],
        data_fetcher: Callable,
        region: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Warm cache for common operations.

        Args:
            operations: List of operation names to warm
            data_fetcher: Function to fetch data for cache warming
            region: Specific region to warm cache for

        Returns:
            Dictionary of operation names and success status
        """
        results = {}

        for operation in operations:
            if operation in self._warming_tasks:
                continue  # Already warming

            self._warming_tasks.add(operation)

            try:
                # Fetch fresh data
                data = await data_fetcher(operation, region=region)

                # Cache the data
                success = await self.set(data, operation, data_type=operation, region=region)

                results[operation] = success
                logger.info(f"Cache warmed for {operation}: {success}")

            except Exception as e:
                logger.error(f"Cache warming failed for {operation}: {e}")
                results[operation] = False

            finally:
                self._warming_tasks.discard(operation)

        return results

    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Pattern to match cache keys

        Returns:
            Number of entries invalidated
        """
        invalidated_count = 0

        # Invalidate from memory cache
        keys_to_remove = [key for key in self._memory_cache.keys() if pattern in key]

        for key in keys_to_remove:
            self._remove_from_memory(key)
            invalidated_count += 1

        # Invalidate from Redis cache
        if self._redis_available and self._redis:
            try:
                redis_keys = await self._redis.keys(f"{self.cache_prefix}:*{pattern}*")
                if redis_keys:
                    await self._redis.delete(*redis_keys)
                    invalidated_count += len(redis_keys)
            except Exception as e:
                logger.error(f"Redis invalidation error: {e}")

        logger.info(f"Invalidated {invalidated_count} cache entries matching '{pattern}'")
        return invalidated_count

    def get_metrics(self) -> CacheMetrics:
        """Get current cache performance metrics."""
        # Update cache size
        self._metrics.cache_size_bytes = sum(
            len(str(entry)) for entry in self._memory_cache.values()
        )

        return self._metrics

    def get_analytics_data(self, last_n_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get analytics data for the last N minutes."""
        if not self.enable_analytics:
            return []

        cutoff_time = datetime.utcnow() - timedelta(minutes=last_n_minutes)

        return [
            entry
            for entry in self._analytics_data
            if datetime.fromisoformat(entry["timestamp"]) > cutoff_time
        ]

    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check."""
        health_status = {
            "memory_cache": {
                "status": "healthy",
                "size": len(self._memory_cache),
                "max_size": self.max_memory_cache_size,
            },
            "redis_cache": {
                "status": "healthy" if self._redis_available else "unavailable",
                "connected": self._redis_available,
            },
            "metrics": {
                "hit_rate": self._metrics.hit_rate,
                "total_requests": self._metrics.total_requests,
                "average_response_time": self._metrics.average_response_time,
            },
        }

        # Test Redis connection if available
        if self._redis_available and self._redis:
            try:
                await self._redis.ping()
                health_status["redis_cache"]["ping"] = True
            except Exception as e:
                health_status["redis_cache"]["status"] = "error"
                health_status["redis_cache"]["error"] = str(e)

        return health_status

    async def close(self) -> None:
        """Close cache connections and cleanup."""
        logger.info("Shutting down DistributedCloudWANCache")

        if self._redis:
            await self._redis.close()

        self._memory_cache.clear()
        self._memory_access_times.clear()
        self._analytics_data.clear()

        logger.info("Cache cleanup complete")


class CacheDecorator:
    """Decorator for automatic function result caching."""

    def __init__(
        self,
        cache: DistributedCloudWANCache,
        data_type: str = "default",
        ttl_override: Optional[int] = None,
    ):
        self.cache = cache
        self.data_type = data_type
        self.ttl_override = ttl_override

    def __call__(self, func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            operation = func.__name__

            # Try to get from cache first
            cached_result = await self.cache.get(
                operation=operation, data_type=self.data_type, **kwargs
            )

            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)

            await self.cache.set(
                data=result,
                operation=operation,
                data_type=self.data_type,
                ttl_override=self.ttl_override,
                **kwargs,
            )

            return result

        return wrapper


# Factory function for easy cache creation
def create_distributed_cache(
    redis_url: str = "redis://localhost:6379", **kwargs
) -> DistributedCloudWANCache:
    """Create and initialize a distributed cache instance."""
    cache = DistributedCloudWANCache(redis_url=redis_url, **kwargs)
    return cache
