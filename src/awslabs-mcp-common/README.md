# awslabs.mcp-common

Shared building blocks for AWS Labs Model Context Protocol (MCP) servers.

## `LazyServer`

A thin wrapper around `mcp.server.fastmcp.FastMCP` that defers heavy imports
(`mcp.server.fastmcp`, `pydantic`, `FastMCP` construction) from module load
to `run()` time. On an M1 MacBook Pro this typically shaves 400–600ms off
server startup for each MCP server.

Authors register tools at module level with no FastMCP or pydantic imports:

```python
from awslabs.mcp_common import Field, LazyServer

mcp = LazyServer(
    'my-server',
    instructions='...',
    dependencies=['pydantic', 'httpx'],
)

@mcp.tool()
async def my_tool(
    ctx,
    url: str = Field(description='URL to fetch'),
    max_length: int = Field(default=5000, gt=0, lt=1_000_000),
) -> str:
    """Fetch the URL and return up to max_length characters."""
    import httpx  # deferred by the author
    ...

def main():
    mcp.run()
```

At `mcp.run()`, the shim imports `FastMCP` + `pydantic`, walks each
registered tool's signature, resolves `Field(...)` placeholders to real
`pydantic.Field(...)` defaults, auto-annotates `ctx` with `Context`, then
registers each tool and delegates to `FastMCP.run`.

### Accessing the underlying server

`LazyServer.build()` materializes and returns the underlying `FastMCP`
instance without running the server. Useful for tests. Attribute access on
a `LazyServer` (e.g. `mcp.name`) delegates to the built server after
`run()` or `build()`; before that, accessing an unknown attribute raises
`RuntimeError` with a clear message.
