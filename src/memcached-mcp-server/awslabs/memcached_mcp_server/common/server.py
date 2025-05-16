"""Server initialization for Memcached MCP Server."""

from mcp.server.fastmcp import FastMCP


# Create MCP server instance
mcp = FastMCP(
    'awslabs.memcached-mcp-server',
    instructions='Instructions for using this memcached MCP server. This can be used by clients to improve the LLM'
    's understanding of available tools, resources, etc. It can be thought of like a '
    'hint'
    ' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.',
    dependencies=['pydantic', 'loguru', 'pymemcache', 'dotenv'],
)
