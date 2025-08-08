from dataclasses import dataclass, field
from typing import Dict, List, Callable, Awaitable
import time
import asyncio


@dataclass
class MetricSnapshot:
    timestamp: float = field(default_factory=time.time)
    pool_hits: int = 0
    pool_misses: int = 0
    circuit_breaker_trips: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    memory_usage_mb: float = 0.0
    active_connections: int = 0


class MetricsCollector:
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self._metrics: Dict[str, int] = {"errors": 0, "total_requests": 0}
        self._snapshots: List[MetricSnapshot] = []
        self._start_time = time.time()
        self._collection_task = None

    async def start_collection(self):
        self._collection_task = asyncio.create_task(self._metrics_loop())

    async def _metrics_loop(self):
        while True:
            await asyncio.sleep(self.collection_interval)
            self._snapshots.append(self._create_snapshot())

    def _create_snapshot(self) -> MetricSnapshot:
        return MetricSnapshot(
            pool_hits=self._metrics.get("pool_hits", 0),
            pool_misses=self._metrics.get("pool_misses", 0),
            circuit_breaker_trips=self._metrics.get("circuit_breakers", 0),
            error_rate=self._metrics["errors"] / self._metrics["total_requests"]
            if self._metrics["total_requests"]
            else 0,
            active_connections=len(self._client_pool._active) if self._client_pool else 0,
        )

    @asynccontextmanager
    async def measure_latency(self, operation: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = (time.perf_counter() - start) * 1000
            self._metrics[operation + "_latency"] = self._metrics.get(operation + "_latency", 0) + duration

    async def record_error(self, service: str):
        self._metrics["errors"] += 1
        self._metrics["total_requests"] += 1
