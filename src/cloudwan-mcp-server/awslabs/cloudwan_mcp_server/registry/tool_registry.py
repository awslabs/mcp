from typing import Dict, List, Type, Optional, Any, Callable, Set
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
from dataclasses import dataclass


class ToolState(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class ToolMetadata:
    name: str
    version: str
    description: str
    service_types: List[str]
    health_check_strategy: str
    timeout_seconds: int
    retry_policy: Dict[str, Any]
    dependencies: List[str]
    tags: Dict[str, str]


class ToolLifecycleHooks(ABC):
    @abstractmethod
    async def on_initialize(self, tool: Any, context: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def on_health_check(self, tool: Any) -> bool:
        pass

    @abstractmethod
    async def on_shutdown(self, tool: Any) -> None:
        pass


class ToolRegistry:
    def __init__(self, metrics_collector: Any, health_registry: Any):
        self._tools: Dict[str, weakref.WeakReference] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._states: Dict[str, ToolState] = {}
        self._lifecycle_hooks: Dict[str, ToolLifecycleHooks] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._metrics = metrics_collector
        self._health_registry = health_registry

    async def register_tool(self, tool: Any, metadata: ToolMetadata) -> bool:
        if metadata.name in self._tools:
            return False
        self._tools[metadata.name] = weakref.WeakReference(tool)
        self._metadata[metadata.name] = metadata
        self._states[metadata.name] = ToolState.UNINITIALIZED
        await self._initialize_tool(metadata.name)
        return True

    async def _initialize_tool(self, tool_name: str) -> None:
        tool = self._tools[tool_name]()
        if hasattr(tool, "initialize"):
            self._states[tool_name] = ToolState.INITIALIZING
            if await tool.initialize():
                self._states[tool_name] = ToolState.READY
            else:
                self._states[tool_name] = ToolState.FAILED

    def get_all_tools_info(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {"state": self._states[name].value, "metadata": self._metadata[name]} for name in self._tools.keys()
        }

    async def check_tool_health(self, tool_name: str) -> Dict[str, Any]:
        tool = self._tools.get(tool_name)()
        if not tool:
            return {"status": "not_found"}
        if hasattr(tool, "health_check"):
            return {"healthy": await tool.health_check()}
        return {"status": "no_health_check"}
