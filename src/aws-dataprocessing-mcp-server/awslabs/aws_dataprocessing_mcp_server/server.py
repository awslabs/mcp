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

"""awslabs Data Processing MCP Server implementation.

This module implements the DataProcessing MCP Server, which provides tools for managing Amazon Glue, EMR-EC2, Athena, Data Catalog and Crawler
resources through the Model Context Protocol (MCP).

Environment Variables:
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    FASTMCP_LOG_LEVEL: Log level (default: WARNING)
"""

import argparse
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_catalog_handler import (
    GlueDataCatalogHandler,
)
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = """
# AWS Data Processing MCP Server

This MCP server provides tools for managing AWS data processing services including Glue Data Catalog.
It enables you to create, manage, and monitor data processing workflows.

## Usage Notes

- By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write operations.
- Access to sensitive data requires the `--allow-sensitive-data-access` flag.
- When creating or updating resources, always check for existing resources first to avoid conflicts.
- IAM roles and permissions are critical for data processing services to access data sources and targets.

## Common Workflows

### Setting Up a Data Catalog
1. Create a database: `manage_aws_glue_databases(operation='create-database', database_name='my-database', description='My database')`
2. Create a connection: `manage_aws_glue_connections(operation='create-connection', connection_name='my-connection', connection_input={'ConnectionType': 'JDBC', 'ConnectionProperties': {'JDBC_CONNECTION_URL': 'jdbc:mysql://host:port/db', 'USERNAME': '...', 'PASSWORD': '...'}})`
3. Create a table: `manage_aws_glue_tables(operation='create-table', database_name='my-database', table_name='my-table', table_input={'StorageDescriptor': {'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}], 'Location': 's3://bucket/path'}})`
4. Create partitions: `manage_aws_glue_partitions(operation='create-partition', database_name='my-database', table_name='my-table', partition_values=['2023-01'], partition_input={'StorageDescriptor': {'Location': 's3://bucket/path/year=2023/month=01'}})`

### Exploring the Data Catalog
1. List databases: `manage_aws_glue_databases(operation='list-databases')`
2. List tables in a database: `manage_aws_glue_tables(operation='list-tables', database_name='my-database')`
3. Search for tables: `manage_aws_glue_tables(operation='search-tables', search_text='customer')`
4. Get table details: `manage_aws_glue_tables(operation='get-table', database_name='my-database', table_name='my-table')`
5. List partitions: `manage_aws_glue_partitions(operation='list-partitions', database_name='my-database', table_name='my-table')`

### Updating Data Catalog Resources
1. Update database properties: `manage_aws_glue_databases(operation='update-database', database_name='my-database', description='Updated description')`
2. Update table schema: `manage_aws_glue_tables(operation='update-table', database_name='my-database', table_name='my-table', table_input={'StorageDescriptor': {'Columns': [{'Name': 'id', 'Type': 'int'}, {'Name': 'name', 'Type': 'string'}, {'Name': 'email', 'Type': 'string'}]}})`
3. Update connection properties: `manage_aws_glue_connections(operation='update-connection', connection_name='my-connection', connection_input={'ConnectionProperties': {'JDBC_CONNECTION_URL': 'jdbc:mysql://new-host:port/db'}})`

### Cleaning Up Resources
1. Delete a partition: `manage_aws_glue_partitions(operation='delete-partition', database_name='my-database', table_name='my-table', partition_values=['2023-01'])`
2. Delete a table: `manage_aws_glue_tables(operation='delete-table', database_name='my-database', table_name='my-table')`
3. Delete a connection: `manage_aws_glue_connections(operation='delete-connection', connection_name='my-connection')`
4. Delete a database: `manage_aws_glue_databases(operation='delete-database', database_name='my-database')`

"""

SERVER_DEPENDENCIES = [
    'pydantic>=2.10.6',
    'loguru>=0.7.0',
    'boto3>=1.34.0',
    'requests>=2.31.0',
    'pyyaml>=6.0.0',
    'cachetools>=5.3.0',
]

# Global reference to the MCP server instance for testing purposes
mcp = None


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.aws-dataprocessing-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


def main():
    """Run the MCP server with CLI argument support."""
    global mcp

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for Data Processing'
    )
    parser.add_argument(
        '--allow-write',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable write access mode (allow mutating operations)',
    )
    parser.add_argument(
        '--allow-sensitive-data-access',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable sensitive data access (required for reading sensitive data like logs, query results, and session details)',
    )

    args = parser.parse_args()

    allow_write = args.allow_write
    allow_sensitive_data_access = args.allow_sensitive_data_access

    # Log startup mode
    mode_info = []
    if not allow_write:
        mode_info.append('read-only mode')
    if not allow_sensitive_data_access:
        mode_info.append('restricted sensitive data access mode')

    mode_str = ' in ' + ', '.join(mode_info) if mode_info else ''
    logger.info(f'Starting Data Processing MCP Server{mode_str}')

    # Create the MCP server instance
    mcp = create_server()

    # Initialize handlers - all tools are always registered, access control is handled within tools
    GlueDataCatalogHandler(
        mcp,
        allow_write=allow_write,
        allow_sensitive_data_access=allow_sensitive_data_access,
    )

    # Run server
    mcp.run()

    return mcp


if __name__ == '__main__':
    main()
