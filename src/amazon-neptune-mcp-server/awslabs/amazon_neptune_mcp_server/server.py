# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""awslabs neptune MCP Server implementation."""

import argparse
import os
import sys
from awslabs.amazon_neptune_mcp_server.models import GraphSchema
from awslabs.amazon_neptune_mcp_server.neptune import NeptuneServer
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Optional


# Remove all default handlers then add our own
logger.remove()
logger.add(sys.stderr, level='INFO')

# Initialize FastMCP
mcp = FastMCP(
    'awslabs.neptune-mcp-server',
    instructions='This server provides the ability to check connectivity, status and schema for working with Amazon Neptune.',
    dependencies=['pydantic', 'loguru', 'boto3'],
)

# Global variable to hold the graph instance
_graph = None


def get_graph():
    """Lazily initialize the Neptune graph connection.

    This function ensures the graph is only initialized when needed,
    not at import time, which helps with testing.

    Returns:
        NeptuneServer: The initialized Neptune server instance

    Raises:
        ValueError: If NEPTUNE_ENDPOINT environment variable is not set
    """
    global _graph
    if _graph is None:
        endpoint = os.environ.get('NEPTUNE_ENDPOINT', None)
        logger.info(f'NEPTUNE_ENDPOINT: {endpoint}')
        if endpoint is None:
            logger.exception('NEPTUNE_ENDPOINT environment variable is not set')
            raise ValueError('NEPTUNE_ENDPOINT environment variable is not set')

        use_https_value = os.environ.get('NEPTUNE_USE_HTTPS', 'True')
        use_https = use_https_value.lower() in (
            'true',
            '1',
            't',
        )

        _graph = NeptuneServer(endpoint, use_https=use_https)

    return _graph


@mcp.resource(uri='amazon-neptune://status', name='GraphStatus', mime_type='application/text')
def get_status_resource() -> str:
    """Get the status of the currently configured Amazon Neptune graph."""
    return get_graph().status()


@mcp.resource(uri='amazon-neptune://schema', name='GraphSchema', mime_type='application/text')
def get_schema_resource() -> GraphSchema:
    """Get the schema for the graph including the vertex and edge labels as well as the
    (vertex)-[edge]->(vertex) combinations.
    """
    return get_graph().schema()


@mcp.tool(name='get_graph_status')
def get_status() -> str:
    """Get the status of the currently configured Amazon Neptune graph."""
    return get_graph().status()


@mcp.tool(name='get_graph_schema')
def get_schema() -> GraphSchema:
    """Get the schema for the graph including the vertex and edge labels as well as the
    (vertex)-[edge]->(vertex) combinations.
    """
    return get_graph().schema()


@mcp.tool(name='run_opencypher_query')
def run_opencypher_query(query: str, parameters: Optional[dict] = None) -> dict:
    """Executes the provided openCypher against the graph."""
    return get_graph().query_opencypher(query, parameters)


@mcp.tool(name='run_gremlin_query')
def run_gremlin_query(query: str) -> dict:
    """Executes the provided Tinkerpop Gremlin against the graph."""
    return get_graph().query_gremlin(query)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs MCP server for interacting with Amazon Neptune'
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
