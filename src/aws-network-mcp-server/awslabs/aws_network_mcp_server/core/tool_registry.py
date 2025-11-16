#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Tool Registry Pattern for MCP Server - Provides abstraction over FastMCP."""

from typing import Dict, Any, Callable, Optional, Protocol, TypeVar
from dataclasses import dataclass, field
import inspect
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ToolMetadata:
    """Metadata for registered tools."""
    
    def __init__(self,
                 name: str,
                 func: Callable,
                 category: str,
                 service: str,
                 description: str = None,
                 parameters: Dict[str, Any] = None):
        self.name = name
        self.func = func
        self.category = category
        self.service = service
        self.description = description or func.__doc__
        self.parameters = parameters or self._extract_parameters(func)
    
    def _extract_parameters(self, func: Callable) -> Dict[str, Any]:
        """Extract parameter information from function signature."""
        sig = inspect.signature(func)
        params = {}
        for name, param in sig.parameters.items():
            if name not in ['self', 'cls']:
                params[name] = {
                    'type': param.annotation if param.annotation != inspect.Parameter.empty else Any,
                    'required': param.default == inspect.Parameter.empty,
                    'default': param.default if param.default != inspect.Parameter.empty else None
                }
        return params


class MCPFrameworkAdapter(Protocol):
    """Protocol for MCP framework adapters."""
    
    def register_tool(self, func: Callable) -> None:
        """Register a tool with the MCP framework."""
        ...
    
    def get_registered_tools(self) -> Dict[str, Any]:
        """Get all registered tools."""
        ...


class FastMCPAdapter:
    """Adapter for FastMCP framework."""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        self._tools_cache = {}
    
    def register_tool(self, func: Callable) -> None:
        """Register a tool with FastMCP."""
        self.mcp.tool(func)
        self._tools_cache[func.__name__] = func
    
    def get_registered_tools(self) -> Dict[str, Any]:
        """Get registered tools from cache (avoids accessing _tools)."""
        return self._tools_cache.copy()


@dataclass
class ToolRegistry:
    """Central registry for all MCP tools with metadata and categorization."""
    
    adapter: MCPFrameworkAdapter
    tools: Dict[str, ToolMetadata] = field(default_factory=dict)
    categories: Dict[str, list] = field(default_factory=dict)
    services: Dict[str, list] = field(default_factory=dict)
    
    def register(self, category: str, service: str, **kwargs):
        """Decorator to register tools with metadata."""
        def decorator(func: Callable) -> Callable:
            tool_name = func.__name__
            
            # Create metadata
            metadata = ToolMetadata(
                name=tool_name,
                func=func,
                category=category,
                service=service,
                **kwargs
            )
            
            # Store in registry
            self.tools[tool_name] = metadata
            
            # Organize by category and service
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(tool_name)
            
            if service not in self.services:
                self.services[service] = []
            self.services[service].append(tool_name)
            
            # Register with MCP framework
            self.adapter.register_tool(func)
            
            logger.debug(f"Registered tool: {tool_name} (category={category}, service={service})")
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name."""
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: str) -> list:
        """Get all tools in a category."""
        return [self.tools[name] for name in self.categories.get(category, [])]
    
    def get_tools_by_service(self, service: str) -> list:
        """Get all tools for a service."""
        return [self.tools[name] for name in self.services.get(service, [])]
    
    def list_tools(self) -> list:
        """List all registered tool names."""
        return list(self.tools.keys())
    
    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        return len(self.tools)
    
    def validate_tools(self) -> Dict[str, list]:
        """Validate all registered tools for consistency."""
        issues = {
            'missing_docs': [],
            'missing_params': [],
            'naming_violations': []
        }
        
        for name, metadata in self.tools.items():
            # Check documentation
            if not metadata.description or len(metadata.description.strip()) < 10:
                issues['missing_docs'].append(name)
            
            # Check parameters
            if not metadata.parameters:
                issues['missing_params'].append(name)
            
            # Check naming conventions
            if not name.islower() or not name.replace('_', '').isalnum():
                issues['naming_violations'].append(name)
        
        return {k: v for k, v in issues.items() if v}


# Singleton instance
_registry: Optional[ToolRegistry] = None


def get_registry(adapter: Optional[MCPFrameworkAdapter] = None) -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        if adapter is None:
            raise ValueError("Registry not initialized. Provide an adapter on first call.")
        _registry = ToolRegistry(adapter=adapter)
    return _registry


def initialize_registry(mcp_instance) -> ToolRegistry:
    """Initialize the registry with an MCP instance."""
    adapter = FastMCPAdapter(mcp_instance)
    return get_registry(adapter)