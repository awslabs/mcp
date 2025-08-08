from enum import Enum
import time
import asyncio
from typing import Callable, Awaitable, TypeVar, Dict
from contextlib import asynccontextmanager

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AsyncCircuitBreaker:
    """Production-grade circuit breaker with async support"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60, success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @asynccontextmanager
    async def call(self) -> None:
        """Context manager for circuit breaker protection"""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise RuntimeError("Circuit open")

        try:
            yield
        except Exception:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
            raise
        else:
            if self._state == CircuitState.HALF_OPEN:
                self._failure_count = max(0, self._failure_count - 1)
                if self._failure_count <= self.success_threshold:
                    self._state = CircuitState.CLOSED
