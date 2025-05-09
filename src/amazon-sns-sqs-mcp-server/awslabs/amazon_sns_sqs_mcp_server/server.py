"""Main server module for Amazon SNS and SQS MCP server."""
import argparse
from awslabs.amazon_sns_sqs_mcp_server.consts import MCP_SERVER_VERSION
from awslabs.amazon_sns_sqs_mcp_server.sns import register_sns_tools
from awslabs.amazon_sns_sqs_mcp_server.sqs import register_sqs_tools
from mcp.server.fastmcp import FastMCP


# instantiate base server
mcp = FastMCP(
    'awslabs.amazon-sns-sqs-mcp-server',
    instructions="""Manage Amazon SNS topics, subscriptions, and Amazon SQS queues for messaging.""",
    dependencies=['pydantic', 'boto3'],
    version=MCP_SERVER_VERSION,
)

# Register SNS and SQS tools
register_sns_tools(mcp)
register_sqs_tools(mcp)

def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Model Context Protocol (MCP) server for Amazon SNS and SQS'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
