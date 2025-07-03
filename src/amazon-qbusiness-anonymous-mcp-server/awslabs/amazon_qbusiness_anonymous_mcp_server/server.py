# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""awslabs amazon-qbusiness-anonymous MCP Server implementation."""

from awslabs.amazon_qbusiness_anonymous_mcp_server.clients import get_qbiz_client, make_query
from mcp.server.fastmcp import FastMCP


"""
Amazon Q Business anonymous mode MCP Server

This module provides a Model Context Protocol (MCP) server for interacting with Amazon Q Business created using anonymous mode.

Required Environment Variables:
    AWS_REGION: The AWS region where your Q Business application is deployed
    QBUSINESS_APPLICATION_ID: The unique identifier for your Q Business application

AWS Credentials:
    This module requires valid AWS credentials to be configured. Credentials can be provided via:
    - AWS CLI configuration (~/.aws/credentials)
    - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
    - IAM roles (when running on EC2 or other AWS services)

"""

mcp = FastMCP(
    'awslabs.amazon-qbusiness-anonymous-mcp-server',
    instructions='Use this MCP server to query the Amazon Q Business application created using anonymous mode to get responses based on the content you have ingested in it.',
    dependencies=['pydantic', 'loguru', 'boto3'],
)


@mcp.tool(name='QBusinessQueryTool')
async def qbiz_local_query(query: str) -> str:
    """MCP tool to query Amazon Q Business and return a formatted response.

    This tool provides a Model Context Protocol interface for querying Amazon Q Business.
    It handles client initialization, query execution, and error handling automatically.

    Args:
        query (str): The question or query to send to Q Business

    Returns:
        str: Formatted response from Q Business or error message if the query fails

    Examples:
        >>> qbiz_local_query('What is our company policy on remote work?')
        "Qbiz response: According to company policy..."

        >>> qbiz_local_query('')
        "Error: Query cannot be empty"

    Note:
        Requires the following environment variables to be set:
        - AWS_REGION: AWS region where Q Business is deployed
        - QBUSINESS_APPLICATION_ID: ID of the Q Business application
        - AWS credentials must be configured (via AWS CLI, IAM roles, etc.)
    """
    try:
        if not query or not query.strip():
            return 'Error: Query cannot be empty'

        client = get_qbiz_client()
        resp = make_query(client, query)

        # Check if response has the expected structure
        if 'systemMessage' not in resp:
            return f'Error: Unexpected response format from Q Business: {resp}'

        return f'Qbiz response: {resp["systemMessage"]}'
    except Exception as e:
        return f'Error: {str(e)}'


def main():
    """Main function to run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
