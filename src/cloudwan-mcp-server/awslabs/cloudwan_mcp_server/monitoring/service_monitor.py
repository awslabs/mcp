from typing import Dict, Callable, Awaitable, TypeVar
from ..utils.circuit_breaker import AsyncCircuitBreaker, CircuitState
from .metrics import MetricsCollector

T = TypeVar("T")


class ServiceMonitor:
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics = metrics_collector
        self._circuit_breakers: Dict[str, AsyncCircuitBreaker] = {}

    def _get_circuit_breaker(self, service: str) -> AsyncCircuitBreaker:
        if service not in self._circuit_breakers:
            self._circuit_breakers[service] = AsyncCircuitBreaker()
        return self._circuit_breakers[service]

    async def execute_with_circuit_breaker(
        self, service: str, operation: Callable[..., Awaitable[T]], *args, **kwargs
    ) -> T:
        breaker = self._get_circuit_breaker(service)

        if breaker.state == CircuitState.OPEN:
            raise RuntimeError(f"{service} circuit breaker open")

        try:
            async with breaker.call():
                return await operation(*args, **kwargs)
        except Exception as e:
            await self._metrics.record_error(service)
            raise
