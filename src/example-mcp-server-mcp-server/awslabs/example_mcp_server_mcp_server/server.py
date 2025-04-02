"""awslabs example-mcp-server MCP Server implementation."""

import argparse
from mcp.server.fastmcp import FastMCP
from typing import Literal


mcp = FastMCP(
    'awslabs.example-mcp-server-mcp-server',
    instructions="Instructions for using this MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.",
    dependencies=[
        'pydantic',
    ],
)


@mcp.tool(name='ExampleTool')
async def example_tool(
    query: str,
) -> str:
    """Example tool implementation.

    Replace this with your own tool implementation.
    """
    project_name = 'awslabs example-mcp-server MCP Server'
    return (
        f"Hello from {project_name}! Your query was {query}. Replace this with your tool's logic"
    )


@mcp.tool(name='MathTool')
async def math_tool(
    operation: Literal['add', 'subtract', 'multiply', 'divide'],
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
        case 'add':
            return a + b
        case 'subtract':
            return a - b
        case 'multiply':
            return a * b
        case 'divide':
            try:
                return a / b
            except ZeroDivisionError:
                raise ValueError(f'The denominator {b} cannot be zero.')
        case _:
            raise ValueError(
                f'Invalid operation: {operation} (must be one of: add, subtract, multiply, divide)'
            )


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for example-mcp-server'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
