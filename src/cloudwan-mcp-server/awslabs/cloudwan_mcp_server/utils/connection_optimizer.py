"""
Advanced connection optimization and pooling strategies
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from weakref import WeakKeyDictionary
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection performance statistics"""

    total_connections: int = 0
    active_connections: int = 0
    pool_hits: int = 0
    pool_misses: int = 0
    connection_errors: int = 0
    avg_connection_time_ms: float = 0.0
    peak_connections: int = 0
    last_reset_time: float = 0.0

    @property
    def hit_rate(self) -> float:
        total = self.pool_hits + self.pool_misses
        return self.pool_hits / total if total > 0 else 0.0


class AdvancedConnectionOptimizer:
    """Enterprise-grade connection optimization and resource management"""

    def __init__(self, max_connections_per_service: int = 50, idle_timeout: int = 300):
        self.max_connections_per_service = max_connections_per_service
        self.idle_timeout = idle_timeout

        # Connection pools per service/region combination
        self._connection_pools: Dict[str, asyncio.Queue] = {}
        self._pool_locks: Dict[str, asyncio.Lock] = {}

        # Connection tracking and statistics
        self._active_connections: WeakKeyDictionary = WeakKeyDictionary()
        self._connection_stats: Dict[str, ConnectionStats] = {}
        self._connection_creation_times: Dict[str, float] = {}

        # Optimization strategies
        self._warmup_tasks: Dict[str, asyncio.Task] = {}
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self._stats_task = asyncio.create_task(self._update_stats())

    def _get_pool_key(self, service: str, region: str) -> str:
        """Generate unique pool identifier"""
        return f"{service}:{region}"

    async def _ensure_pool_exists(self, pool_key: str) -> None:
        """Lazily create connection pool and lock"""
        if pool_key not in self._connection_pools:
            self._connection_pools[pool_key] = asyncio.Queue(maxsize=self.max_connections_per_service)
            self._pool_locks[pool_key] = asyncio.Lock()
            self._connection_stats[pool_key] = ConnectionStats(last_reset_time=time.time())

    async def acquire_optimized_connection(self, service: str, region: str, client_factory, priority: int = 5) -> Any:
        """Acquire connection with advanced optimization strategies"""
        pool_key = self._get_pool_key(service, region)
        await self._ensure_pool_exists(pool_key)

        stats = self._connection_stats[pool_key]
        connection_start_time = time.perf_counter()

        async with self._pool_locks[pool_key]:
            # Try to get from pool first
            try:
                if not self._connection_pools[pool_key].empty():
                    client = self._connection_pools[pool_key].get_nowait()

                    # Validate connection is still healthy
                    if await self._validate_connection_health(client, service):
                        stats.pool_hits += 1
                        stats.active_connections += 1

                        connection_time = (time.perf_counter() - connection_start_time) * 1000
                        self._update_avg_connection_time(pool_key, connection_time)

                        return client
                    else:
                        # Connection unhealthy, close and create new
                        try:
                            await client.close()
                        except:
                            pass

            except asyncio.QueueEmpty:
                pass

            # Create new connection
            stats.pool_misses += 1
            stats.total_connections += 1

            try:
                client = await client_factory._create_raw_client(service, region)
                stats.active_connections += 1
                stats.peak_connections = max(stats.peak_connections, stats.active_connections)

                # Track connection for cleanup
                self._active_connections[client] = {
                    "pool_key": pool_key,
                    "created_at": time.time(),
                    "last_used": time.time(),
                }

                connection_time = (time.perf_counter() - connection_start_time) * 1000
                self._update_avg_connection_time(pool_key, connection_time)

                return client

            except Exception as e:
                stats.connection_errors += 1
                logger.error(f"Failed to create connection for {pool_key}: {e}")
                raise

    async def release_connection(self, client: Any, service: str, region: str) -> None:
        """Release connection back to pool with optimization"""
        pool_key = self._get_pool_key(service, region)

        if pool_key not in self._connection_stats:
            # Connection not tracked, close immediately
            try:
                await client.close()
            except:
                pass
            return

        stats = self._connection_stats[pool_key]

        try:
            # Update connection tracking
            if client in self._active_connections:
                self._active_connections[client]["last_used"] = time.time()
                stats.active_connections -= 1

            # Validate connection health before returning to pool
            if await self._validate_connection_health(client, service):
                # Return to pool if space available
                try:
                    self._connection_pools[pool_key].put_nowait(client)
                    return
                except asyncio.QueueFull:
                    # Pool full, close the connection
                    pass

            # Close connection if not returned to pool
            await client.close()

        except Exception as e:
            logger.warning(f"Error releasing connection for {pool_key}: {e}")
            try:
                await client.close()
            except:
                pass

    async def _validate_connection_health(self, client: Any, service: str) -> bool:
        """Fast connection health validation"""
        try:
            # Service-specific lightweight health checks
            if hasattr(client, "_service_model"):
                service_name = client._service_model.service_name

                if service_name == "networkmanager":
                    # Quick API call to test connectivity
                    await client.describe_global_networks(MaxResults=1)
                elif service_name == "ec2":
                    await client.describe_regions(MaxResults=1)
                elif service_name == "sts":
                    await client.get_caller_identity()
                else:
                    # Generic connectivity test
                    return True

            return True

        except Exception:
            return False

    def _update_avg_connection_time(self, pool_key: str, new_time_ms: float) -> None:
        """Update rolling average connection time"""
        stats = self._connection_stats[pool_key]

        if stats.avg_connection_time_ms == 0:
            stats.avg_connection_time_ms = new_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            stats.avg_connection_time_ms = alpha * new_time_ms + (1 - alpha) * stats.avg_connection_time_ms

    async def warmup_connections(self, service: str, region: str, client_factory, target_connections: int = 5) -> None:
        """Pre-warm connection pool for better performance"""
        pool_key = self._get_pool_key(service, region)
        await self._ensure_pool_exists(pool_key)

        logger.info(f"Warming up {target_connections} connections for {pool_key}")

        warmup_tasks = []
        for i in range(target_connections):
            task = asyncio.create_task(self._create_warmup_connection(service, region, client_factory, pool_key))
            warmup_tasks.append(task)

        # Wait for warmup to complete
        results = await asyncio.gather(*warmup_tasks, return_exceptions=True)

        successful_warmups = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Successfully warmed up {successful_warmups}/{target_connections} connections for {pool_key}")

    async def _create_warmup_connection(self, service: str, region: str, client_factory, pool_key: str) -> None:
        """Create and pool a warmup connection"""
        try:
            client = await client_factory._create_raw_client(service, region)

            # Validate connection works
            if await self._validate_connection_health(client, service):
                self._connection_pools[pool_key].put_nowait(client)
            else:
                await client.close()

        except Exception as e:
            logger.warning(f"Warmup connection failed for {pool_key}: {e}")

    async def _periodic_cleanup(self) -> None:
        """Clean up idle and stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                current_time = time.time()

                for client, info in list(self._active_connections.items()):
                    if current_time - info["last_used"] > self.idle_timeout:
                        try:
                            await client.close()
                            pool_key = info["pool_key"]
                            if pool_key in self._connection_stats:
                                self._connection_stats[pool_key].active_connections -= 1
                        except:
                            pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")

    async def _update_stats(self) -> None:
        """Periodically update connection statistics"""
        while True:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds

                for pool_key, stats in self._connection_stats.items():
                    # Update active connection counts from actual tracking
                    actual_active = sum(1 for info in self._active_connections.values() if info["pool_key"] == pool_key)
                    stats.active_connections = actual_active

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating connection stats: {e}")

    def get_connection_stats(self) -> Dict[str, ConnectionStats]:
        """Get current connection statistics for all pools"""
        return self._connection_stats.copy()

    def get_pool_summary(self) -> Dict[str, Any]:
        """Get high-level connection pool summary"""
        total_pools = len(self._connection_pools)
        total_active = sum(stats.active_connections for stats in self._connection_stats.values())
        total_pool_size = sum(pool.qsize() for pool in self._connection_pools.values())
        avg_hit_rate = (
            sum(stats.hit_rate for stats in self._connection_stats.values()) / total_pools if total_pools > 0 else 0
        )

        return {
            "total_pools": total_pools,
            "total_active_connections": total_active,
            "total_pooled_connections": total_pool_size,
            "average_hit_rate": avg_hit_rate,
            "pools": {
                pool_key: {
                    "active": stats.active_connections,
                    "pooled": self._connection_pools[pool_key].qsize() if pool_key in self._connection_pools else 0,
                    "hit_rate": stats.hit_rate,
                    "avg_connection_time_ms": stats.avg_connection_time_ms,
                }
                for pool_key, stats in self._connection_stats.items()
            },
        }

    async def drain_all_pools(self) -> None:
        """Gracefully drain all connection pools"""
        logger.info("Draining all connection pools...")

        # Cancel cleanup tasks
        if hasattr(self, "_cleanup_task"):
            self._cleanup_task.cancel()
        if hasattr(self, "_stats_task"):
            self._stats_task.cancel()

        # Close all pooled connections
        for pool_key, pool in self._connection_pools.items():
            while not pool.empty():
                try:
                    client = pool.get_nowait()
                    await client.close()
                except:
                    pass

        # Close all active connections
        for client in list(self._active_connections.keys()):
            try:
                await client.close()
            except:
                pass

        logger.info("All connection pools drained successfully")


# Global connection optimizer instance
connection_optimizer = AdvancedConnectionOptimizer()
