#!/usr/bin/env python3

"""Run the Bedrock Advisor MCP Server directly."""

import os
import sys


def main():
    """Run the Bedrock Advisor MCP Server."""
    print('Starting Bedrock Advisor MCP Server...')

    # Set environment variables
    os.environ['AWS_REGION'] = 'us-east-1'
    os.environ['FASTMCP_LOG_LEVEL'] = 'DEBUG'

    # Import and run the server
    from awslabs.bedrock_advisor_mcp_server.server import main as server_main
    
    print('Server starting...')
    server_main()


if __name__ == '__main__':
    sys.exit(main())
