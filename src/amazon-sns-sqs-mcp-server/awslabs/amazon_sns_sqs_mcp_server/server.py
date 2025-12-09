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

"""Main server module for Amazon SNS and SQS MCP server."""

import argparse
from awslabs.amazon_sns_sqs_mcp_server.sns import register_sns_tools
from awslabs.amazon_sns_sqs_mcp_server.sqs import register_sqs_tools
from mcp.server.fastmcp import FastMCP


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = (
    """Manage Amazon SNS topics, subscriptions, and Amazon SQS queues for messaging."""
)

SERVER_DEPENDENCIES = ['pydantic', 'boto3']


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.amazon-sns-sqs-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


mcp = create_server()


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Model Context Protocol (MCP) server for Amazon SNS and SQS'
    )

    parser.add_argument(
        '--allow-resource-creation',
        action='store_true',
        help='Allow tools that create resources on user AWS account',
    )

    args = parser.parse_args()

    disallow_resource_creation = False if args.allow_resource_creation else True

    register_sns_tools(mcp, disallow_resource_creation)
    register_sqs_tools(mcp, disallow_resource_creation)

    mcp.run()


if __name__ == '__main__':
    main()
