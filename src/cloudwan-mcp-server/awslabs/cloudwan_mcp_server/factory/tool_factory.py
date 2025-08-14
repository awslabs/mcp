# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Factory implementation for extensible CloudWAN tool management."""

import importlib
import inspect
from pathlib import Path
from typing import Dict, Type, List, Optional, Any
from collections import defaultdict
import yaml
import json

from ..tools.base import ToolInterface, ToolCategory, ToolMetadata
from ..utils.logger import get_logger
from ..utils.metrics import metrics

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for managing tool metadata and instances."""

    def __init__(self):
        self._tools: Dict[str, Type[ToolInterface]] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._categories: Dict[ToolCategory, List[str]] = defaultdict(list)
        self._instances: Dict[str, ToolInterface] = {}  # Singleton instances

    def register(self, tool_class: Type[ToolInterface]) -> None:
        """Register a tool class."""
        try:
            # Create temporary instance to get metadata
            instance = tool_class()
            metadata = instance.metadata

            # Validate metadata
            if not metadata.name:
                raise ValueError(f"Tool {tool_class.__name__} missing required name in metadata")

            # Check for name conflicts
            if metadata.name in self._tools:
                logger.warning(f"Overwriting existing tool: {metadata.name}")

            self._tools[metadata.name] = tool_class
            self._metadata[metadata.name] = metadata
            self._categories[metadata.category].append(metadata.name)

            logger.info(f"Registered tool: {metadata.name} v{metadata.version} ({metadata.category})")

            # Record metrics
            metrics.record_count(
                "tool_registry.registrations",
                dimensions={"category": metadata.category.value, "version": metadata.version},
            )

        except Exception as e:
            logger.error(f"Failed to register tool {tool_class.__name__}: {str(e)}")
            raise

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool by name."""
        if tool_name in self._tools:
            metadata = self._metadata[tool_name]

            # Remove from registry
            del self._tools[tool_name]
            del self._metadata[tool_name]

            # Remove from category list
            if tool_name in self._categories[metadata.category]:
                self._categories[metadata.category].remove(tool_name)

            # Remove cached instance if exists
            if tool_name in self._instances:
                del self._instances[tool_name]

            logger.info(f"Unregistered tool: {tool_name}")

    def get_tool_class(self, name: str) -> Optional[Type[ToolInterface]]:
        """Get tool class by name."""
        return self._tools.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """Get all tools in a category."""
        return self._categories.get(category, []).copy()

    def get_all_metadata(self) -> Dict[str, ToolMetadata]:
        """Get metadata for all registered tools."""
        return self._metadata.copy()

    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        return len(self._tools)

    def search_tools(
        self,
        query: str = None,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
        enterprise_only: bool = False,
    ) -> List[str]:
        """Search for tools based on criteria."""
        results = []

        for name, metadata in self._metadata.items():
            # Category filter
            if category and metadata.category != category:
                continue

            # Enterprise filter
            if enterprise_only and not metadata.enterprise_tier:
                continue

            # Tag filter
            if tags and not any(tag in metadata.tags for tag in tags):
                continue

            # Query filter (search name and description)
            if query:
                search_text = f"{metadata.name} {metadata.description}".lower()
                if query.lower() not in search_text:
                    continue

            results.append(name)

        return results


class ToolFactory:
    """Factory for creating and managing CloudWAN tools with enterprise features."""

    def __init__(self, config_path: Optional[Path] = None):
        self.registry = ToolRegistry()
        self.config_path = config_path
        self._tool_configs: Dict[str, Dict[str, Any]] = {}
        self._load_configurations()

    def _load_configurations(self) -> None:
        """Load tool configurations from YAML/JSON files."""
        if not self.config_path or not self.config_path.exists():
            logger.debug("No tool configuration path provided or path doesn't exist")
            return

        try:
            for config_file in self.config_path.glob("*.yaml"):
                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)
                    self._validate_and_store_config(config, config_file.name)

            for config_file in self.config_path.glob("*.json"):
                with open(config_file, "r") as f:
                    config = json.load(f)
                    self._validate_and_store_config(config, config_file.name)

        except Exception as e:
            logger.error(f"Failed to load tool configurations: {str(e)}")

    def _validate_and_store_config(self, config: Dict[str, Any], filename: str) -> None:
        """Validate and store tool configuration."""
        if not isinstance(config, dict):
            logger.warning(f"Invalid configuration format in {filename}")
            return

        if "tools" in config:
            # Multiple tool definitions in one file
            for tool_config in config["tools"]:
                if "name" in tool_config:
                    self._tool_configs[tool_config["name"]] = tool_config
        elif "name" in config:
            # Single tool definition
            self._tool_configs[config["name"]] = config
        else:
            logger.warning(f"Configuration file {filename} missing tool name")

    def load_tool_modules(self, modules_path: Path) -> None:
        """Dynamically load all tool modules from directory."""
        if not modules_path.exists():
            logger.error(f"Tools module path does not exist: {modules_path}")
            return

        loaded_count = 0
        failed_count = 0

        for module_file in modules_path.glob("*.py"):
            # Skip private modules and __init__.py
            if module_file.name.startswith("_"):
                continue

            module_name = f"awslabs.cloudwan_mcp_server.tools.{module_file.stem}"

            try:
                module = importlib.import_module(module_name)
                tools_found = self._scan_and_register_module(module)
                loaded_count += tools_found
                logger.debug(f"Loaded {tools_found} tools from {module_name}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to load module {module_name}: {str(e)}")

        logger.info(f"Tool loading complete: {loaded_count} tools loaded, {failed_count} failures")

        # Record metrics
        metrics.record_gauge("tool_factory.loaded_tools", loaded_count)
        metrics.record_gauge("tool_factory.failed_loads", failed_count)

    def _scan_and_register_module(self, module) -> int:
        """Scan module for tool classes and register them."""
        tools_found = 0

        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, ToolInterface)
                and obj != ToolInterface
                and not inspect.isabstract(obj)
            ):
                try:
                    self.registry.register(obj)
                    tools_found += 1
                except Exception as e:
                    logger.error(f"Failed to register tool {name}: {str(e)}")

        return tools_found

    def create_tool(self, tool_name: str, config_overrides: Optional[Dict[str, Any]] = None) -> ToolInterface:
        """Create a tool instance with configuration."""
        tool_class = self.registry.get_tool_class(tool_name)
        if not tool_class:
            raise ValueError(
                f"Tool '{tool_name}' not found in registry. Available tools: {list(self.registry._tools.keys())}"
            )

        # Merge configurations
        config = self._tool_configs.get(tool_name, {}).copy()
        if config_overrides:
            config.update(config_overrides)

        # Create instance
        try:
            instance = tool_class()

            # Apply configuration if tool supports it
            if hasattr(instance, "configure"):
                instance.configure(config)

            # Record creation metrics
            metrics.record_count("tool_factory.creations", dimensions={"tool_name": tool_name})

            logger.debug(f"Created tool instance: {tool_name}")
            return instance

        except Exception as e:
            logger.error(f"Failed to create tool {tool_name}: {str(e)}")
            raise

    def get_or_create_singleton(self, tool_name: str) -> ToolInterface:
        """Get or create a singleton instance of a tool."""
        if tool_name not in self.registry._instances:
            self.registry._instances[tool_name] = self.create_tool(tool_name)
        return self.registry._instances[tool_name]

    def get_tool_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive capability information for all registered tools."""
        capabilities = {
            "total_tools": self.registry.get_tool_count(),
            "categories": {},
            "permissions_required": set(),
            "supported_regions": set(),
            "enterprise_tools": [],
            "tool_versions": {},
        }

        for category in ToolCategory:
            tools = self.registry.get_tools_by_category(category)
            capabilities["categories"][category.value] = {"count": len(tools), "tools": tools}

        for tool_name, metadata in self.registry.get_all_metadata().items():
            # Collect permissions
            capabilities["permissions_required"].update(metadata.required_permissions)

            # Collect regions
            if metadata.supported_regions:
                capabilities["supported_regions"].update(metadata.supported_regions)

            # Mark enterprise tools
            if metadata.enterprise_tier:
                capabilities["enterprise_tools"].append(tool_name)

            # Version tracking
            capabilities["tool_versions"][tool_name] = metadata.version

        # Convert sets to lists for JSON serialization
        capabilities["permissions_required"] = list(capabilities["permissions_required"])
        capabilities["supported_regions"] = list(capabilities["supported_regions"])

        return capabilities

    def validate_tool_dependencies(self, tool_name: str) -> Dict[str, bool]:
        """Validate that a tool's dependencies and prerequisites are met."""
        metadata = self.registry._metadata.get(tool_name)
        if not metadata:
            return {"valid": False, "error": f"Tool {tool_name} not found"}

        validation_results = {"valid": True, "checks": {}}

        # Check AWS permissions (simplified - would integrate with AWS IAM in production)
        if metadata.required_permissions:
            validation_results["checks"]["permissions"] = {
                "required": metadata.required_permissions,
                "validated": False,  # Would check actual IAM permissions
                "message": "Permission validation not implemented",
            }

        # Check regional availability
        if metadata.supported_regions:
            validation_results["checks"]["regions"] = {"supported": metadata.supported_regions, "validated": True}

        # Check CloudWAN dependency
        if metadata.requires_cloudwan:
            validation_results["checks"]["cloudwan"] = {
                "required": True,
                "validated": False,  # Would check CloudWAN configuration
                "message": "CloudWAN dependency validation not implemented",
            }

        return validation_results

    def get_factory_stats(self) -> Dict[str, Any]:
        """Get factory performance and usage statistics."""
        return {
            "registered_tools": self.registry.get_tool_count(),
            "active_instances": len(self.registry._instances),
            "configurations_loaded": len(self._tool_configs),
            "categories": len([cat for cat in ToolCategory if self.registry.get_tools_by_category(cat)]),
            "metrics": metrics.get_metrics_summary(),
        }


# Global factory instance
_tool_factory: Optional[ToolFactory] = None


def get_tool_factory(config_path: Optional[Path] = None) -> ToolFactory:
    """Get the global tool factory instance."""
    global _tool_factory
    if _tool_factory is None:
        _tool_factory = ToolFactory(config_path)
    return _tool_factory


def initialize_factory(tools_path: Path, config_path: Optional[Path] = None) -> ToolFactory:
    """Initialize the global factory with tools and configuration."""
    factory = get_tool_factory(config_path)
    factory.load_tool_modules(tools_path)
    return factory
