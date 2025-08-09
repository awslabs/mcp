from ..factory import AsyncAWSClientFactory
from ..config.tool_config import ToolConfiguration


class ToolFactory:
    def __init__(self, client_factory: AsyncAWSClientFactory, metrics_collector: Any, health_registry: Any):
        self._client_factory = client_factory
        self._metrics = metrics_collector
        self._health_registry = health_registry
        self._tool_classes: Dict[str, Type] = {}

    def register_tool_class(self, name: str, tool_class: Type):
        self._tool_classes[name] = tool_class

    def create_tool(self, name: str, config: ToolConfiguration) -> Any:
        if name not in self._tool_classes:
            raise ValueError(f"Tool {name} not registered")

        health_strategy = self._health_registry.get_strategy(config.service_types[0])
        return self._tool_classes[name](self._client_factory, config, health_strategy)

    def get_available_tools(self) -> List[str]:
        return list(self._tool_classes.keys())
