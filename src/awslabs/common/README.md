# AWS MCP Common Utilities

Shared utilities.

## Selective Tool Disabling

### API

- `disabled_tools() -> Set[str]` - Get set of disabled tool names
- `tool_enabled(tool_name: str) -> bool` - Check if tool should be enabled

### Implementation

Add a conditional when calling `@mcp.tool`:

```python
from awslabs.common.config import tool_enabled

# Conditionally register tools
if tool_enabled('ExecuteTerragruntCommand'):
    @mcp.tool(name='ExecuteTerragruntCommand')
    async def ExecuteTerragruntCommand():
        ...
```

This allows disabling of the tool in the `DISABLED_TOOLS` environment variable:

```json
{
  "mcpServers": {
    "awslabs.terraform-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "awslabs/terraform-mcp-server:latest"
      ],
      "env": {
        "DISABLED_TOOLS": "ExecuteTerragruntCommand,RunCheckovScan"
      }
    }
  }
}
```
