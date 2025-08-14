from typing import Any
import asyncio
from contextlib import asynccontextmanager
from aiobotocore.session import get_session
from aiobotocore.config import AioConfig
from ..factory import AsyncAWSClientFactory
from .client_pool import AsyncClientPool
from ..monitoring.service_monitor import ServiceMonitor
from .connection_optimizer import connection_optimizer
from ..validation.input_validator import validator_instance


class AsyncAWSClientFactoryImpl(AsyncAWSClientFactory):
    """Production-optimized async AWS client factory with advanced performance features"""

    def __init__(self, max_pool: int = 100, metrics_collector=None):
        from ..monitoring.metrics import MetricsCollector

        self._metrics = metrics_collector or MetricsCollector()
        self._service_monitor = ServiceMonitor(self._metrics)
        self._client_pool = AsyncClientPool(self, max_pool)
        self._session = None
        self._warmup_enabled = True

    async def create_client(self, service_name: str, region: str) -> Any:
        """Create optimized client with validation and connection optimization"""

        # Input validation with caching
        validation_result = validator_instance.validate_aws_resource_id(region, "aws_region")
        if not validation_result.is_valid:
            raise ValueError(f"Invalid region: {region}")

        # Use connection optimizer for advanced pooling
        async with self._metrics.measure_latency(f"{service_name}_acquire"):
            client = await connection_optimizer.acquire_optimized_connection(service_name, region, self, priority=5)

            # Circuit breaker protection
            return await self._service_monitor.execute_with_circuit_breaker(
                service_name, self._get_validated_client, client
            )

    async def _get_validated_client(self, client: Any) -> Any:
        """Internal method to return validated client"""
        return client

    async def _create_raw_client(self, service_name: str, region: str) -> Any:
        """Create raw aiobotocore client"""
        if not self._session:
            self._session = get_session()

        config = AioConfig(region_name=region, retries={"max_attempts": 3, "mode": "adaptive"}, max_pool_connections=50)

        return self._session.create_client(service_name, config=config)

    async def warmup_service(self, service_name: str, region: str, connections: int = 5) -> None:
        """Pre-warm connections for optimal performance"""
        if self._warmup_enabled:
            await connection_optimizer.warmup_connections(service_name, region, self, connections)

    async def get_performance_stats(self) -> dict:
        """Get comprehensive performance statistics"""
        pool_stats = connection_optimizer.get_pool_summary()
        validation_stats = validator_instance.get_cache_stats()

        return {
            "connection_optimization": pool_stats,
            "validation_performance": validation_stats,
            "circuit_breakers": {
                service: breaker.state.value for service, breaker in self._service_monitor._circuit_breakers.items()
            },
        }

    async def close(self) -> None:
        """Graceful shutdown with connection draining"""
        await connection_optimizer.drain_all_pools()
        await self._client_pool.cleanup()

        if self._session:
            await self._session.close()
