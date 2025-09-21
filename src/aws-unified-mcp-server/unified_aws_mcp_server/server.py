from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Annotated, Any

try:
    from mcp.server.fastmcp import FastMCP, Context
except ModuleNotFoundError as exc:
    missing = exc.name or "mcp"
    raise ModuleNotFoundError(
        f"The '{missing}' package is required. Install the MCP dependencies (fastmcp>=2.11, mcp[cli]>=1.11) "
        "or launch this server via 'uvx --with fastmcp --with mcp[cli] python -m unified_aws_mcp_server.server'."
    ) from exc

try:
    from fastmcp import Client
except ModuleNotFoundError as exc:
    missing = exc.name or "fastmcp"
    raise ModuleNotFoundError(
        f"The '{missing}' package is required. Install fastmcp>=2.11 or use 'uvx --with fastmcp --with mcp[cli]' "
        "when starting the unified MCP server."
    ) from exc

from mcp.types import ToolAnnotations
from pydantic import Field

from .configy import (
    API_MCP_ARGS,
    API_MCP_COMMAND,
    FASTMCP_LOG_LEVEL,
    KNOWLEDGE_MCP_URL,
    LOG_FILE,
    api_environment,
)
from .models import ToolPayload, UnifiedMcpErrorResponse

logger = logging.getLogger("aws_unified_mcp")
log_level = getattr(logging, FASTMCP_LOG_LEVEL, logging.INFO)
logger.setLevel(log_level)
logger.propagate = False
if not logger.handlers:
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setLevel(log_level)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=7)
    file_handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

server = FastMCP(name="AWS-UNIFIED-PROXY", log_level=FASTMCP_LOG_LEVEL)


def _normalize_tool_response(result: Any) -> Any:
    """Convert MCP Client responses into JSON-serializable payloads."""
    if result is None:
        return None
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "data"):
        data = getattr(result, "data")
        if callable(data):
            try:
                data = data()
            except TypeError:
                pass
        if data is not None:
            return _normalize_tool_response(data)
    if hasattr(result, "content"):
        content = getattr(result, "content")
        if hasattr(content, "model_dump"):
            return content.model_dump()
        return _normalize_tool_response(content)
    if isinstance(result, dict):
        return {key: _normalize_tool_response(value) for key, value in result.items()}
    if isinstance(result, list):
        return [_normalize_tool_response(item) for item in result]
    if hasattr(result, "__dict__"):
        plain = {
            key: _normalize_tool_response(value)
            for key, value in vars(result).items()
            if not key.startswith("_")
        }
        if plain:
            if len(plain) == 1 and "result" in plain:
                return plain["result"]
            return plain
    if isinstance(result, (str, int, float, bool)):
        return result
    return str(result)


async def _call_api_tool(tool_name: str, args: dict[str, Any]) -> Any:
    client_cfg = {
        "mcpServers": {
            "api": {
                "transport": "stdio",
                "command": API_MCP_COMMAND,
                "args": list(API_MCP_ARGS),
                "env": api_environment(),
            }
        }
    }
    client = Client(client_cfg)
    async with client:
        logger.info("Proxying API tool %s with args %s", tool_name, args)
        try:
            result = await client.call_tool(tool_name, args)
        except Exception:
            logger.exception("API tool %s failed", tool_name)
            raise
        payload = _normalize_tool_response(result)
        if not isinstance(payload, dict):
            payload = {"result": payload}
        logger.info(
            "API tool %s returned payload %s",
            tool_name,
            list(payload.keys()) if isinstance(payload, dict) else type(payload),
        )
        return payload


async def _call_knowledge_tool(tool_name: str, args: dict[str, Any]) -> Any:
    client = Client(KNOWLEDGE_MCP_URL)
    async with client:
        logger.info("Proxying knowledge tool %s with args %s", tool_name, args)
        try:
            result = await client.call_tool(tool_name, args)
        except Exception:
            logger.exception("Knowledge tool %s failed", tool_name)
            raise
        payload = _normalize_tool_response(result)
        if not isinstance(payload, dict):
            payload = {"result": payload}
        logger.info("Knowledge tool %s returned payload type %s", tool_name, type(payload))
        return payload

@server.tool(
    name="suggest_aws_commands",
    description="Proxy to API MCP: suggest AWS CLI commands for a natural language task.",
    annotations=ToolAnnotations(title="Suggest AWS CLI commands", readOnlyHint=True),
)
async def suggest_aws_commands(
    query: Annotated[str, Field(description="Natural language request")],
    ctx: Context,
) -> ToolPayload:
    if not query.strip():
        detail = "Empty query provided"
        await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    result = await _call_api_tool("suggest_aws_commands", {"query": query})
    if isinstance(result, dict) and result.get("error"):
        detail = str(result.get("detail") or "Suggestion service unavailable")
        await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    return result


@server.tool(
    name="call_aws",
    description="Proxy to API MCP: execute validated AWS CLI commands (respecting read-only and consent).",
    annotations=ToolAnnotations(title="Execute AWS CLI commands", openWorldHint=True),
)
async def call_aws(
    cli_command: Annotated[str, Field(description='Complete AWS CLI command, must start with "aws"')],
    ctx: Context,
    max_results: Annotated[int | None, Field(description="Optional limit for results")] = None,
) -> ToolPayload:
    command = cli_command.strip()
    if not command:
        detail = "CLI command must not be empty"
        await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    if not command.startswith("aws"):
        detail = "CLI command must start with 'aws'"
        await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    if max_results is not None and max_results <= 0:
        detail = "max_results must be positive when provided"
        await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    args: dict[str, Any] = {"cli_command": command}
    if max_results is not None:
        args["max_results"] = max_results
    return await _call_api_tool("call_aws", args)


@server.tool(
    name="search_documentation",
    description="Proxy to Knowledge MCP: search AWS documentation.",
    annotations=ToolAnnotations(title="Search AWS docs", readOnlyHint=True),
)
async def search_documentation(
    phrase: Annotated[str, Field(description="Search phrase")],
    limit: Annotated[int | None, Field(description="Max results")] = 10,
    ctx: Context | None = None,
) -> ToolPayload:
    if not phrase.strip():
        detail = "Search phrase must not be empty"
        if ctx:
            await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    if limit is not None and limit <= 0:
        detail = "limit must be positive when provided"
        if ctx:
            await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    args: dict[str, Any] = {"search_phrase": phrase}
    if limit is not None:
        args["limit"] = limit
    return await _call_knowledge_tool("aws___search_documentation", args)


@server.tool(
    name="read_documentation",
    description="Proxy to Knowledge MCP: read a documentation page.",
    annotations=ToolAnnotations(title="Read AWS doc", readOnlyHint=True),
)
async def read_documentation(
    url: Annotated[str, Field(description="AWS docs URL")],
    start_index: Annotated[int | None, Field(description="Start index for pagination")] = None,
    max_length: Annotated[int | None, Field(description="Max characters to return")] = None,
    ctx: Context | None = None,
) -> ToolPayload:
    if not url.strip():
        detail = "URL must not be empty"
        if ctx:
            await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    if start_index is not None and start_index < 0:
        detail = "start_index cannot be negative"
        if ctx:
            await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    if max_length is not None and max_length <= 0:
        detail = "max_length must be positive when provided"
        if ctx:
            await ctx.error(detail)
        return UnifiedMcpErrorResponse(detail=detail)
    args: dict[str, Any] = {"url": url}
    if start_index is not None:
        args["start_index"] = start_index
    if max_length is not None:
        args["max_length"] = max_length
    return await _call_knowledge_tool("aws___read_documentation", args)

def main():
    logger.info("Unified proxy starting. Knowledge URL: %s", KNOWLEDGE_MCP_URL)
    server.run()


if __name__ == "__main__":
    main()
