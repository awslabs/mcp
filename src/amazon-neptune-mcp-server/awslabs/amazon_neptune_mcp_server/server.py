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
from loguru import logger
from awslabs.amazon_neptune_mcp_server.neptune import NeptuneServer
from awslabs.amazon_neptune_mcp_server.models import GraphSchema
from mcp.server.fastmcp import FastMCP
from typing import Optional


# Remove all default handlers then add our own
logger.remove()
logger.add(sys.stderr, level='INFO')

endpoint = os.environ.get("NEPTUNE_ENDPOINT", None)
use_https = os.environ.get("NEPTUNE_USE_HTTPS", "True").lower() in (
    "true",
    "1",
    "t",
)
logger.info(f"NEPTUNE_ENDPOINT: {endpoint}")
if endpoint is None:
    logger.exception("NEPTUNE_ENDPOINT environment variable is not set")
    raise ValueError("NEPTUNE_ENDPOINT environment variable is not set")

graph = NeptuneServer(endpoint, use_https=use_https)


mcp = FastMCP(
    "awslabs.neptune-mcp-server",
    instructions='This server provides the ability to check connectivity, status and schema for working with Amazon Neptune.',
    dependencies=[
        'pydantic',
        'loguru',
        'boto3'
    ],
)


@mcp.resource(
    uri="amazon-neptune://status", name="GraphStatus", mime_type="application/text"
)
def get_status_resource() -> str:
    """Get the status of the currently configured Amazon Neptune graph"""
    return graph.status()


@mcp.resource(
    uri="amazon-neptune://schema", name="GraphSchema", mime_type="application/text"
)
def get_schema_resource() -> GraphSchema:
    """Get the schema for the graph including the vertex and edge labels as well as the
    (vertex)-[edge]->(vertex) combinations.
    """
    return graph.schema()


@mcp.tool(name="get_graph_status")
def get_status() -> str:
    """Get the status of the currently configured Amazon Neptune graph"""
    return graph.status()


@mcp.tool(name="get_graph_schema")
def get_schema() -> GraphSchema:
    """Get the schema for the graph including the vertex and edge labels as well as the
    (vertex)-[edge]->(vertex) combinations.
    """
    return graph.schema()


@mcp.tool(name="run_opencypher_query")
def run_opencypher_query(query: str, parameters: Optional[dict] = None) -> dict:
    """Executes the provided openCypher against the graph"""
    return graph.query_opencypher(query, parameters)


@mcp.tool(name="run_gremlin_query")
def run_gremlin_query(query: str) -> dict:
    """Executes the provided Tinkerpop Gremlin against the graph"""
    return graph.query_gremlin(query)

@mcp.tool(name="run_sparql_query")
def run_sparql_query(query: str) -> dict:
    """Executes the provided SPARQL against the graph"""
    return graph.query_sparql(query)

def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description='An AWS Labs MCP server for interacting with Amazon Neptune')
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    logger.trace('A trace message.')
    logger.debug('A debug message.')
    logger.info('An info message.')
    logger.success('A success message.')
    logger.warning('A warning message.')
    logger.error('An error message.')
    logger.critical('A critical message.')

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
