from typing import Protocol, Any
from abc import ABC, abstractmethod


class AsyncAWSClientFactory(Protocol):
    @abstractmethod
    async def create_client(self, service_name: str, region: str) -> Any:
        """Create async service client"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Cleanup async resources"""
        pass


class McpTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """Execute tool operation asynchronously"""
        pass
