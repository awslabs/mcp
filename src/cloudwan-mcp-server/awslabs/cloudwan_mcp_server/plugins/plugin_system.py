import os
from typing import Dict, List


class PluginManager:
    def __init__(self, tool_registry: Any):
        self._registry = tool_registry
        self._loaded_plugins: Dict[str, Any] = {}

    async def load_plugin(self, plugin_path: str) -> bool:
        try:
            spec = importlib.util.spec_from_file_location(plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "register_plugin"):
                await module.register_plugin(self._registry)
                self._loaded_plugins[plugin_path] = module
                return True
        except Exception as e:
            logger.error(f"Plugin load failed: {e}")
        return False

    async def unload_plugin(self, plugin_path: str) -> bool:
        if plugin_path in self._loaded_plugins:
            del self._loaded_plugins[plugin_path]
            return True
        return False
