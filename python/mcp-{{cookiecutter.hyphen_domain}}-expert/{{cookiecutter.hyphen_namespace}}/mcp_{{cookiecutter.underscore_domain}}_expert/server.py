"""{{ cookiecutter.project_namespace }} MCP {{cookiecutter.project_domain}} expert server implementation."""

import argparse
from typing import Literal

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "{{cookiecutter.hyphen_namespace}}.mcp-{{cookiecutter.hyphen_domain}}-expert",
    instructions="{{cookiecutter.instructions}}",
    dependencies=[
        "pydantic",
    ],
)


@mcp.tool(name="ExampleTool")
async def example_tool(
    query: str,
) -> str:
    """Example tool implementation.

    Replace this with your own tool implementation.
    """
    project_name = "{{cookiecutter.project_namespace}} {{cookiecutter.project_domain}}"
    return f"Hello from {project_name} expert! Your query was {query}. Replace this with your tool's logic"


@mcp.tool(name="MathTool")
async def math_tool(
    operation: Literal["add", "subtract", "multiply", "divide"],
    a: int | float,
    b: int | float,
) -> int | float:
    """Math tool implementation.

    This tool supports the following operations:
    - add
    - subtract
    - multiply
    - divide

    Parameters:
        operation (Literal["add", "subtract", "multiply", "divide"]): The operation to perform.
        a (int): The first number.
        b (int): The second number.

    Returns:
        The result of the operation.
    """
    match operation:
        case "add":
            return a + b
        case "subtract":
            return a - b
        case "multiply":
            return a * b
        case "divide":
            try:
                return a / b
            except ZeroDivisionError:
                raise ValueError(f"The denominator {b} cannot be zero.")
        case _:
            raise ValueError(
                f"Invalid operation: {operation} (must be one of: add, subtract, multiply, divide)"
            )


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description="{{cookiecutter.description}}")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument(
        "--port", type=int, default=8888, help="Port to run the server on"
    )

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
