from abc import ABC, abstractmethod
from typing import Dict, Any


class HealthCheckStrategy(ABC):
    @abstractmethod
    async def check_health(self, client: Any) -> bool:
        pass

    def get_timeout(self) -> float:
        return 5.0


class NetworkManagerHealthCheck(HealthCheckStrategy):
    async def check_health(self, client: Any) -> bool:
        try:
            await asyncio.wait_for(client.describe_global_networks(MaxResults=1), timeout=self.get_timeout())
            return True
        except Exception:
            return False


class HealthCheckRegistry:
    def __init__(self):
        self._strategies: Dict[str, HealthCheckStrategy] = {"networkmanager": NetworkManagerHealthCheck()}

    def register_strategy(self, service: str, strategy: HealthCheckStrategy):
        self._strategies[service] = strategy

    def get_strategy(self, service: str) -> HealthCheckStrategy:
        return self._strategies.get(service, NullHealthCheck())


class NullHealthCheck(HealthCheckStrategy):
    async def check_health(self, client: Any) -> bool:
        return True
