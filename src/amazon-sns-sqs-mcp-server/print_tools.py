"""Script to print out all registered tools and their signatures."""

from awslabs.amazon_sns_sqs_mcp_server.sns import register_sns_tools
from awslabs.amazon_sns_sqs_mcp_server.sqs import register_sqs_tools
from mcp.server.fastmcp import FastMCP


async def print_tool_info(mcp):
    """Print information about all tools registered with the MCP server."""
    print('\n=== Registered Tools ===\n')

    # Use the list_tools method to get all registered tools
    tools = await mcp.list_tools()

    for tool in tools:
        print(f'Tool: {tool.name}')
        print(f'  Description: {tool.description}')

        # Print input schema if available
        if tool.inputSchema:
            print('  Input Schema:')
            for prop_name, prop_info in tool.inputSchema.get('properties', {}).items():
                prop_type = prop_info.get('type', 'any')
                required = prop_name in tool.inputSchema.get('required', [])
                req_str = ' (required)' if required else ''
                print(f'    - {prop_name}: {prop_type}{req_str}')
                if 'description' in prop_info:
                    print(f'      {prop_info["description"]}')

        print()  # Empty line for readability


async def main():
    """Register tools and print their information."""
    # Create a FastMCP instance
    mcp = FastMCP()

    # Register tools
    print('Registering SNS tools...')
    register_sns_tools(mcp)

    print('Registering SQS tools...')
    register_sqs_tools(mcp)

    # Print tool information
    await print_tool_info(mcp)


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
