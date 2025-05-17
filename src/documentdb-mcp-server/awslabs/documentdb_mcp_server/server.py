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

"""AWS Labs DocumentDB MCP Server implementation for querying AWS DocumentDB."""

import argparse
from awslabs.documentdb_mcp_server.analytic_tools import (
    analyze_schema,
    count_documents,
    explain_operation,
    get_collection_stats,
    get_database_stats,
)
from awslabs.documentdb_mcp_server.config import serverConfig
from awslabs.documentdb_mcp_server.connection_tools import (
    DocumentDBConnection,
    connect,
    disconnect,
)
from awslabs.documentdb_mcp_server.db_management_tools import (
    create_collection,
    drop_collection,
    list_collections,
    list_databases,
)
from awslabs.documentdb_mcp_server.query_tools import aggregate, find
from awslabs.documentdb_mcp_server.write_tools import delete, insert, update
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Create the FastMCP server
mcp = FastMCP(
    'awslabs.documentdb-mcp-server',
    instructions="""DocumentDB MCP Server provides tools to connect to and query AWS DocumentDB databases.

    Usage pattern:
    1. First use the `connect` tool to establish a connection and get a connection_id
    2. Use the connection_id with other tools to perform operations
    3. When finished, use the `disconnect` tool to release resources

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

# Connection tools
mcp.tool(name='connect')(connect)
mcp.tool(name='disconnect')(disconnect)

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
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind the server to')
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level',
    )
    parser.add_argument(
        '--connection-timeout',
        type=int,
        default=30,
        help='Idle connection timeout in minutes (default: 30)',
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

    logger.info(f'Starting DocumentDB MCP Server on {args.host}:{args.port}')
    logger.info(f'Log level: {args.log_level}')

    # Set connection timeout
    DocumentDBConnection._idle_timeout = args.connection_timeout
    logger.info(f'Idle connection timeout: {args.connection_timeout} minutes')

    # Configure read-only mode
    serverConfig.read_only_mode = not args.allow_write
    if serverConfig.read_only_mode:
        logger.warning('Server is running in READ-ONLY mode. Write operations will be blocked.')
    else:
        logger.info('Server is running with WRITE operations ENABLED. Database can be modified.')

    try:
        # Run server with appropriate transport
        if args.sse:
            mcp.settings.port = args.port
            mcp.settings.host = args.host
            mcp.run(transport='sse')
        else:
            mcp.settings.port = args.port
            mcp.settings.host = args.host
            mcp.run()
    except Exception as e:
        logger.critical(f'Failed to start server: {str(e)}')
    finally:
        # Close all DB connections
        DocumentDBConnection.close_all_connections()


if __name__ == '__main__':
    main()
