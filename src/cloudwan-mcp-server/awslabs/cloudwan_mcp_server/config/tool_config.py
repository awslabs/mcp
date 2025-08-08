"""Tool configuration management for CloudWAN MCP server."""

from typing import Any

from pydantic import BaseModel


class ToolConfiguration(BaseModel):
    """Configuration for individual tools."""
    enabled: bool = True
    timeout_seconds: int = 30
    max_retries: int = 3
    rate_limit: int = 1000
    health_interval: int = 60
    circuit_threshold: int = 5
    priority: int = 100
    services: list[str] = []
    custom_config: dict[str, Any] = {}


class ToolConfigManager:
    """Manager for tool configurations."""

    def __init__(self):
        """Initialize the tool configuration manager."""
        self._configs: dict[str, ToolConfiguration] = {}

    def get_config(self, tool_name: str) -> ToolConfiguration:
        """Get configuration for a specific tool."""
        return self._configs.get(tool_name, ToolConfiguration())

    def update_config(self, tool_name: str, **kwargs) -> None:
        """Update configuration for a specific tool."""
        if tool_name not in self._configs:
            self._configs[tool_name] = ToolConfiguration()
        self._configs[tool_name] = self._configs[tool_name].model_copy(update=kwargs)
