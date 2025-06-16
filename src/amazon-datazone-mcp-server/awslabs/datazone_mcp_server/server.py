import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

# Import tool modules
from .tools import (  # bedrock
    data_management,
    domain_management,
    environment,
    glossary,
    project_management,
)

# initialize FastMCP server
mcp = FastMCP("datazone")

# configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Register all tools from modules
domain_management.register_tools(mcp)
project_management.register_tools(mcp)
data_management.register_tools(mcp)
glossary.register_tools(mcp)
environment.register_tools(mcp)


def main():
    """Entry point for console script."""
    try:
        mcp.run(transport="stdio")

        print("DEBUG: Server completed", file=sys.stderr)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Shutting down gracefully.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        # Ensure we return a proper JSON response even in case of errors
        error_response = {
            "error": str(e),
            "type": type(e).__name__,
            "message": "MCP server encountered an error",
        }
        print(json.dumps(error_response))
        sys.exit(1)


if __name__ == "__main__":
    # try:
    #     mcp.run(transport='stdio')
    # except Exception as e:
    #     # Ensure we return a proper JSON response even in case of errors
    #     error_response = {
    #         "error": str(e),
    #         "type": type(e).__name__,
    #         "message": "MCP server encountered an error"
    #     }
    #     print(json.dumps(error_response))
    #     sys.exit(1)
    main()
