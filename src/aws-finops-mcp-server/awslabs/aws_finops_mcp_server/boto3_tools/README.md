# boto3_tools

This directory contains the core components for wrapping boto3 SDK functions as MCP tools.

## Components

- `boto3_registry.py`: Implements the registry for boto3 tools and handles the dynamic creation of tool functions
- `boto3_docstrings.py`: Contains comprehensive docstrings for all supported AWS services and methods
- `__init__.py`: Exports the key components for use in the main application

## Usage

The `Boto3ToolRegistry` class is the main entry point for registering boto3 methods as MCP tools. It:

1. Maintains a registry of all available tools
2. Handles parameter transformation between MCP and boto3
3. Provides a generic handler for all boto3 method calls
4. Manages error handling and logging

Example usage:

```python
from boto3_tools import Boto3ToolRegistry

# Create a registry
registry = Boto3ToolRegistry()

# Register all tools from boto3_docstrings
registry.register_all_tools()

# Access the tools
for tool_name, tool_info in registry.tools.items():
    print(f"Tool: {tool_name}")
    print(f"  Service: {tool_info['service']}")
    print(f"  Method: {tool_info['method']}")
```

## Adding New Services

To add support for a new AWS service:

1. Add the service and method docstrings to `boto3_docstrings.py`
2. If needed, add a service name mapping in `boto3_registry.py`
3. The registry will automatically register the new methods as tools
