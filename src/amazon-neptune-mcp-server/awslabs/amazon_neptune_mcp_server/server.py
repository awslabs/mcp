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

"""awslabs neptune MCP Server implementation."""

import os
import sys
from awslabs.amazon_neptune_mcp_server.models import GraphSchema, RDFGraphSchema
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
        port = int(os.environ.get('NEPTUNE_PORT', 8182))
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

        _graph = NeptuneServer(endpoint, port=port, use_https=use_https)

    return _graph


@mcp.resource(uri='amazon-neptune://status', name='GraphStatus', mime_type='application/text')
def get_status_resource() -> str:
    """Get the status of the currently configured Amazon Neptune graph."""
    return get_graph().status()


@mcp.resource(
    uri='amazon-neptune://schema',
    name='GraphSchema',
    mime_type='application/text',
)
def get_propertygraph_schema_resource() -> GraphSchema:
    """Get the schema for the labeled property graph including the vertex and edge labels as well as the
    (vertex)-[edge]->(vertex) combinations.
    """
    return get_graph().propertygraph_schema()


@mcp.resource(
    uri='amazon-neptune://schema/rdf', name='RDFGraphSchema', mime_type='application/text'
)
def get_rdf_schema_resource() -> RDFGraphSchema:
    """Get the schema for the graph including the classes , relations, and data type combinations."""
    return get_graph().rdf_schema()


@mcp.tool(name='get_graph_status')
def get_status() -> str:
    """Get the status of the currently configured Amazon Neptune graph."""
    return get_graph().status()


@mcp.tool(name='get_graph_schema')
def get_graph_schema() -> GraphSchema:
    """Get the schema for the property graph including the vertex and edge labels as well as the
    (vertex)-[edge]->(vertex) combinations.
    """
    return get_graph().propertygraph_schema()


@mcp.tool(name='get_rdf_schema')
def get_rdf_schema() -> RDFGraphSchema:
    """Get the schema for the graph including the classes, relations, and data type combinations."""
    return get_graph().rdf_schema()


@mcp.tool(name='run_opencypher_query')
def run_opencypher_query(query: str, parameters: Optional[dict] = None) -> dict:
    """Executes the provided openCypher against the graph."""
    return get_graph().query_opencypher(query, parameters)


@mcp.tool(name='run_gremlin_query')
def run_gremlin_query(query: str) -> dict:
    """Executes the provided Tinkerpop Gremlin against the graph."""
    return get_graph().query_gremlin(query)


@mcp.tool(name='run_sparql_query')
def run_sparql_query(query: str) -> dict:
    """Executes the provided SPARQL against the RDF graph."""
    logger.info(f'query: {query}')
    return get_graph().query_sparql(query)


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
