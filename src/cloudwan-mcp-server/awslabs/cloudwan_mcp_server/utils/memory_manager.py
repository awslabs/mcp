"""Memory management utilities for async client pools."""

import gc
import psutil
import asyncio
import weakref
from typing import Set, Any
from dataclasses import dataclass


@dataclass
class MemoryStats:
    """Memory usage statistics."""

    total_mb: float
    used_mb: float
    available_mb: float
    gc_objects: int
    weak_refs: int


class MemoryManager:
    """Manages memory usage and cleanup for client pools."""

    def __init__(self, max_memory_mb: int = 512, client_pool: AsyncClientPool = None):
        self.max_memory_mb = max_memory_mb
        self._client_pool = client_pool
        self._tracked_objects: Set[Any] = weakref.WeakSet()
        self._cleanup_task = None

    async def start_monitoring(self, interval: int = 60):
        """Start memory monitoring task."""
        self._cleanup_task = asyncio.create_task(self._monitor_loop(interval))

    async def stop_monitoring(self):
        """Stop memory monitoring."""
        if self._cleanup_task:
            self._cleanup_task.cancel()

    def track_object(self, obj: Any):
        """Track an object for memory management."""
        self._tracked_objects.add(obj)

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        process = psutil.Process()
        memory_info = process.memory_info()

        return MemoryStats(
            total_mb=memory_info.rss / 1024 / 1024,
            used_mb=memory_info.rss / 1024 / 1024,
            available_mb=self.max_memory_mb - (memory_info.rss / 1024 / 1024),
            gc_objects=len(gc.get_objects()),
            weak_refs=len(self._tracked_objects),
        )

    async def _monitor_loop(self, interval: int):
        """Periodic memory monitoring and cleanup."""
        while True:
            try:
                await asyncio.sleep(interval)
                stats = self.get_memory_stats()

                # Trigger aggressive cleanup if memory usage is high
                if stats.used_mb > self.max_memory_mb * 0.8:
                    await self._aggressive_cleanup()

            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue monitoring
                pass

    async def _aggressive_cleanup(self):
        """Perform aggressive memory cleanup."""
        if self._client_pool:
            while self._client_pool._pool.qsize() > 20:
                client = self._client_pool._pool.get_nowait()
                await client.close()


# Global memory manager instance
memory_manager = MemoryManager()
