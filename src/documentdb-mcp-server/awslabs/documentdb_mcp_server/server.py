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

"""AWS Labs DocumentDB MCP Server implementation for querying AWS DocumentDB."""

import argparse
import os
import sys
from awslabs.documentdb_mcp_server.analytic_tools import (
    analyze_schema,
    count_documents,
    explain_operation,
    get_collection_stats,
    get_database_stats,
)
from awslabs.documentdb_mcp_server.config import serverConfig
from awslabs.documentdb_mcp_server.connection_tools import DocumentDBConnection
from awslabs.documentdb_mcp_server.db_management_tools import (
    create_collection,
    drop_collection,
    list_collections,
    list_databases,
)
from awslabs.documentdb_mcp_server.query_tools import aggregate, find
from awslabs.documentdb_mcp_server.write_tools import delete, insert, update
from loguru import logger
from mcp.server.mcpserver import MCPServer


# Create the MCPServer server
mcp = MCPServer(
    'awslabs.documentdb-mcp-server',
    instructions="""DocumentDB MCP Server provides tools to query a single AWS DocumentDB cluster.

    The cluster is configured by the operator at server startup (via the
    --connection-string CLI argument or the DOCUMENTDB_CONNECTION_STRING
    environment variable). Tools operate on that configured cluster directly and
    take only database/collection/query arguments.

    Server Configuration:
    - The server can be configured in read-only mode, which blocks write operations
      while still allowing read operations.""",
    dependencies=[
        'pydantic',
        'loguru',
        'pymongo',
    ],
)


# Register all tools

# Query tools
mcp.tool(name='find')(find)
mcp.tool(name='aggregate')(aggregate)

# Write tools
mcp.tool(name='insert')(insert)
mcp.tool(name='update')(update)
mcp.tool(name='delete')(delete)

# Database management tools
mcp.tool(name='listDatabases')(list_databases)
mcp.tool(name='createCollection')(create_collection)
mcp.tool(name='listCollections')(list_collections)
mcp.tool(name='dropCollection')(drop_collection)

# Analytic tools
mcp.tool(name='countDocuments')(count_documents)
mcp.tool(name='getDatabaseStats')(get_database_stats)
mcp.tool(name='getCollectionStats')(get_collection_stats)
mcp.tool(name='analyzeSchema')(analyze_schema)
mcp.tool(name='explainOperation')(explain_operation)


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for DocumentDB'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level',
    )
    parser.add_argument(
        '--connection-string',
        type=str,
        default=None,
        help=(
            'DocumentDB connection string for the cluster this server connects to. '
            'May also be set via the DOCUMENTDB_CONNECTION_STRING environment '
            'variable. Required for database operations; if omitted, database '
            'tools will fail until it is configured.'
        ),
    )
    parser.add_argument(
        '--allow-write',
        action='store_true',
        help='Allow write operations (insert, update, delete). By default, the server runs in read-only mode.',
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg),
        level=args.log_level,
        format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
    )

    logger.info('Starting DocumentDB MCP Server')
    logger.info(f'Log level: {args.log_level}')

    # Configure the connection string from the operator (CLI arg takes precedence
    # over the environment variable).
    serverConfig.connection_string = args.connection_string or os.environ.get(
        'DOCUMENTDB_CONNECTION_STRING'
    )
    if serverConfig.connection_string:
        try:
            DocumentDBConnection.validate_retry_writes_false(serverConfig.connection_string)
        except ValueError as e:
            # Fail fast on a misconfigured connection string, but surface a clear
            # operator-facing message rather than a raw traceback.
            logger.critical(f'Invalid DocumentDB connection string: {str(e)}')
            sys.exit(1)
        logger.info('DocumentDB connection string configured')
    else:
        logger.warning(
            'No DocumentDB connection string configured. Database tools will fail '
            'until --connection-string (or DOCUMENTDB_CONNECTION_STRING) is set.'
        )

    # Configure read-only mode
    serverConfig.read_only_mode = not args.allow_write
    if serverConfig.read_only_mode:
        logger.warning('Server is running in READ-ONLY mode. Write operations will be blocked.')
    else:
        logger.info('Server is running with WRITE operations ENABLED. Database can be modified.')

    try:
        mcp.run()
    except Exception as e:
        logger.critical(f'Failed to start server: {str(e)}')
    finally:
        # Close the DB connection
        DocumentDBConnection.close()


if __name__ == '__main__':
    main()
