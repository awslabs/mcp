import asyncio
from weakref import WeakSet
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..factory import AsyncAWSClientFactory


class PoolMetrics:
    """Tracks client pool performance metrics"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.active_connections = 0
        self.healthy_releases = 0
        self.unhealthy_releases = 0
        self.release_errors = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class AsyncClientPool:
    """Connection pool with health checks and eviction"""

    def __init__(self, factory: "AsyncAWSClientFactory", max_size: int = 100):
        self._factory = factory
        self._pool = asyncio.Queue(maxsize=max_size)
        self._active = WeakSet()
        self._metrics = PoolMetrics()
        self._lock = asyncio.Lock()
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup(60))

    async def acquire(self, service: str, region: str) -> Any:
        """Get client from pool or create new"""
        async with self._lock:
            self._metrics.active_connections += 1

        # Check pool first
        if not self._pool.empty():
            self._metrics.hits += 1
            return self._pool.get_nowait()

        self._metrics.misses += 1
        return await self._factory.create_client(service, region)

    async def release(self, client: Any) -> None:
        """Return client to pool with actual health check"""
        try:
            if await self._is_healthy(client):
                self._pool.put_nowait(client)
                self._metrics.healthy_releases += 1
            else:
                await client.close()
                self._metrics.unhealthy_releases += 1
        except Exception:
            self._metrics.release_errors += 1
            try:
                await client.close()
            except:
                pass

    async def _is_healthy(self, client: Any) -> bool:
        """Test client health without destroying it"""
        try:
            service_name = getattr(client, "_service_model", {}).get("service_name", "unknown")
            if service_name == "networkmanager":
                await client.describe_global_networks(MaxResults=1)
            elif service_name == "ec2":
                await client.describe_regions(MaxResults=1)
            else:
                await client.list_tags(ResourceArn="arn:aws:cloudwan:us-east-1:123456789012:test")
            return True
        except:
            return False

    async def _periodic_cleanup(self, interval: int):
        """Evict idle connections"""
        while True:
            await asyncio.sleep(interval)
            async with self._lock:
                while self._pool.qsize() > 50:
                    self._pool.get_nowait()
                    self._metrics.evictions += 1

    async def cleanup(self):
        """Cleanup pool resources"""
        if hasattr(self, "_cleanup_task"):
            self._cleanup_task.cancel()

        # Close all pooled clients
        while not self._pool.empty():
            client = self._pool.get_nowait()
            try:
                await client.close()
            except:
                pass
