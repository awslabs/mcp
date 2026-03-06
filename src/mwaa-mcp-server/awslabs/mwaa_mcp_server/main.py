"""Entry point for MWAA MCP Server."""

from .server import mcp


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
