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

"""awslabs AWS Bedrock AgentCore MCP Server implementation."""

import argparse
from .tools import docs, gateway, memory, runtime
from .utils import cache
from fastmcp import FastMCP


APP_NAME = 'amazon-bedrock-agentcore-mcp-server'
mcp = FastMCP(APP_NAME)

mcp.tool()(docs.search_agentcore_docs)
mcp.tool()(docs.fetch_agentcore_doc)

mcp.tool()(runtime.manage_agentcore_runtime)
mcp.tool()(memory.manage_agentcore_memory)
mcp.tool()(gateway.manage_agentcore_gateway)


def main() -> None:
    """Main entry point for the MCP server.

    Initializes the document cache and starts the FastMCP server.
    The cache is loaded with document titles only for fast startup,
    with full content fetched on-demand.
    """
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server'
    )
    parser.add_argument(
        '--transport',
        choices=['stdio', 'sse', 'streamable-http'],
        default='stdio',
        help='Transport protocol to use (default: stdio)',
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to for HTTP transports (default: 127.0.0.1)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to bind to for HTTP transports (default: 8000)',
    )
    args = parser.parse_args()
    cache.ensure_ready()
    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
