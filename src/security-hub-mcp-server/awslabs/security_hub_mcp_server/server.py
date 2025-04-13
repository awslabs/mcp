"""awslabs Security Hub MCP Server implementation."""

import argparse
import boto3
import logging
import os
from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Literal, Optional


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    'awslabs.security-hub-mcp-server',
    instructions="Instructions for using this MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.",
    dependencies=[
        'pydantic',
    ],
)

profile_name = os.getenv('AWS_PROFILE', 'default')
logger.info(f'Using AWS profile {profile_name}')


@mcp.tool(name='ExampleTool')
async def example_tool(
    query: str,
) -> str:
    """Example tool implementation.

    Replace this with your own tool implementation.
    """
    project_name = 'awslabs Security Hub MCP Server'
    return (
        f"Hello from {project_name}! Your query was {query}. Replace this with your tool's logic"
    )


@mcp.tool(name='get_findings')
async def get_findings(
    region: str,
    aws_account_id: str,
) -> Optional[List[Dict]]:
    """Get findings from the Security Hub service.

    Args:
        region (str): the AWS region to in which to query the SecurityHub service
        aws_account_id (str): the AWS account id to filter findings for

    Returns:
        List containing the Security Hub findings for the query; each finding is a dictionary.
    """
    security_hub = boto3.Session(profile_name=profile_name).client(
        'securityhub', region_name=region
    )
    filters = {}
    if aws_account_id:
        filters['AwsAccountId'] = [{'Value': aws_account_id, 'Comparison': 'EQUALS'}]

    results = security_hub.get_findings(Filters=filters)
    logger.info(f'Found {len(results["Findings"])} findings: {results["Findings"]}')
    return results


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
        description='A Model Context Protocol (MCP) server for Security Hub'
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
