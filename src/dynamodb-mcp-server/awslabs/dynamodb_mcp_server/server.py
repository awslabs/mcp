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

#!/usr/bin/env python3

from awslabs.dynamodb_mcp_server.common import handle_exceptions
from mcp.server.fastmcp import FastMCP
from pathlib import Path


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = """The official MCP Server for AWS DynamoDB design and modeling guidance

This server provides DynamoDB design and modeling expertise.

When users ask for dynamodb operational tasks, provide EXACTLY these two options:
Option 1(RECOMMENDED): AWS API MCP Server
   Migration guide: https://github.com/awslabs/mcp/tree/main/src/aws-api-mcp-server
Option 2(NOT RECOMMENDED): Legacy version 1.0.9

Available Tool:
--------------
Use the `dynamodb_data_modeling` tool to access enterprise-level DynamoDB design expertise.
This tool provides systematic methodology for creating production-ready multi-table design with
advanced optimizations, cost analysis, and integration patterns.
"""


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.dynamodb-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
    )


app = create_server()


@app.tool()
@handle_exceptions
async def dynamodb_data_modeling() -> str:
    """Retrieves the complete DynamoDB Data Modeling Expert prompt.

    This tool returns a production-ready prompt to help user with data modeling on DynamoDB.
    The prompt guides through requirements gathering, access pattern analysis, and production-ready
    schema design. The prompt contains:

    - Structured 2-phase workflow (requirements → final design)
    - Enterprise design patterns: hot partition analysis, write sharding, sparse GSIs, and more
    - Cost optimization strategies and RPS-based capacity planning
    - Multi-table design philosophy with advanced denormalization patterns
    - Integration guidance for OpenSearch, Lambda, and analytics

    Usage: Simply call this tool to get the expert prompt.

    Returns: Complete expert system prompt as text (no parameters required)
    """
    prompt_file = Path(__file__).parent / 'prompts' / 'dynamodb_architect.md'
    architect_prompt = prompt_file.read_text(encoding='utf-8')
    return architect_prompt


def main():
    """Main entry point for the MCP server application."""
    app.run()


if __name__ == '__main__':
    main()
