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

"""Redshift MCP Server implementation."""

import os
import sys
from awslabs.redshift_mcp_server.consts import (
    CLIENT_BEST_PRACTICES,
    DEFAULT_LOG_LEVEL,
    REDSHIFT_BEST_PRACTICES,
)
from awslabs.redshift_mcp_server.models import (
    QueryResult,
    RedshiftCluster,
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftSchema,
    RedshiftTable,
)
from awslabs.redshift_mcp_server.redshift import (
    discover_clusters,
    discover_columns,
    discover_databases,
    discover_schemas,
    discover_tables,
    execute_query,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field


# Remove default handler and add custom configuration
logger.remove()
logger.add(
    os.environ.get('LOG_FILE', sys.stderr),
    level=os.environ.get('FASTMCP_LOG_LEVEL', DEFAULT_LOG_LEVEL),
)


mcp = FastMCP(
    'awslabs.redshift-mcp-server',
    instructions=f"""
# Amazon Redshift MCP Server.

This MCP server provides comprehensive access to Amazon Redshift clusters and serverless workgroups.

## Available Tools

### list_clusters
Lists all available Redshift clusters and serverless workgroups in your AWS account.
This tool provides essential information needed to connect to and query your Redshift instances.

### list_databases
Lists all databases in a specified Redshift cluster.
This tool queries the SVV_REDSHIFT_DATABASES system view to discover available databases.

### list_schemas
Lists all schemas in a specified database within a Redshift cluster.
This tool queries the SVV_ALL_SCHEMAS system view to discover available schemas.

### list_tables
Lists all tables in a specified schema within a Redshift database.
This tool queries the SVV_ALL_TABLES system view to discover available tables.

### list_columns
Lists all columns in a specified table within a Redshift schema.
This tool queries the SVV_ALL_COLUMNS system view to discover available columns.

### execute_query
Executes SQL queries against a Redshift cluster or serverless workgroup.
This tool uses the Redshift Data API to run queries and return results.

## Getting Started

1. Ensure your AWS credentials are configured (via AWS_PROFILE or default credentials).
2. Use the list_clusters tool to discover available Redshift instances.
3. Note the cluster identifiers for use with other tools (coming in future milestones).

{CLIENT_BEST_PRACTICES}
{REDSHIFT_BEST_PRACTICES}
""",
    dependencies=['boto3', 'loguru', 'pydantic', 'regex'],
)


@mcp.tool(name='list_clusters')
async def list_clusters_tool(ctx: Context) -> list[RedshiftCluster]:
    """List all available Amazon Redshift clusters and serverless workgroups.

    This tool discovers and returns information about all Redshift clusters and serverless workgroups
    in your AWS account, including their current status, connection details, and configuration.

    ## Usage Requirements

    - Ensure your AWS credentials are properly configured (via AWS_PROFILE or default credentials).
    - Required IAM permissions: redshift:DescribeClusters, redshift-serverless:ListWorkgroups, redshift-serverless:GetWorkgroup.

    ## Response Structure

    Returns a list of RedshiftCluster objects with the following structure:

    - identifier: Unique identifier for the cluster/workgroup.
    - type: Type of cluster (provisioned or serverless).
    - status: Current status of the cluster.
    - database_name: Default database name.
    - endpoint: Connection endpoint information.
    - port: Connection port.
    - vpc_id: VPC ID where the cluster resides.
    - node_type: Node type (for provisioned clusters).
    - number_of_nodes: Number of nodes (for provisioned clusters).
    - creation_time: When the cluster was created.
    - master_username: Master username for the cluster.
    - publicly_accessible: Whether the cluster is publicly accessible.
    - encrypted: Whether the cluster is encrypted.
    - tags: Tags associated with the cluster.

    ## Usage Tips

    1. Use this tool to discover available Redshift instances before attempting connections.
    2. Note the cluster identifiers for use with other database tools.
    3. Check the status field to ensure clusters are 'available' before querying.
    4. Use the endpoint and port information for direct database connections if needed.
    5. Consider the cluster type (provisioned vs serverless) when planning your queries.

    ## Interpretation Best Practices

    1. Filter results by status to find only available clusters.
    2. Use cluster identifiers as input for other Redshift tools.
    3. Consider cluster configuration (node type, encryption) for performance planning.
    4. Check tags for environment or team information to select appropriate clusters.
    """
    try:
        logger.info('Discovering Redshift clusters and serverless workgroups')
        clusters_data = await discover_clusters()

        # Convert to RedshiftCluster models
        clusters = []
        for cluster_data in clusters_data:
            cluster = RedshiftCluster(**cluster_data)
            clusters.append(cluster)

        logger.info(f'Successfully retrieved {len(clusters)} clusters')
        return clusters

    except Exception as e:
        logger.error(f'Error in list_clusters_tool: {str(e)}')
        await ctx.error(f'Failed to list clusters: {str(e)}')
        raise


@mcp.tool(name='list_databases')
async def list_databases_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to query for databases. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    database_name: str = Field(
        'dev',
        description='The database to connect to for querying system views. Defaults to "dev".',
    ),
) -> list[RedshiftDatabase]:
    """List all databases in a specified Amazon Redshift cluster.

    This tool queries the SVV_REDSHIFT_DATABASES system view to discover all databases
    that the user has access to in the specified cluster, including local databases
    and databases created from datashares.

    ## Usage Requirements

    - Ensure your AWS credentials are properly configured (via AWS_PROFILE or default credentials).
    - The cluster must be available and accessible.
    - Required IAM permissions: redshift-data:ExecuteStatement, redshift-data:DescribeStatement, redshift-data:GetStatementResult.
    - The user must have access to the specified database to query system views.

    ## Parameters

    - cluster_identifier: The unique identifier of the Redshift cluster to query.
                         IMPORTANT: Use a valid cluster identifier from the list_clusters tool.
    - database_name: The database to connect to for querying system views (defaults to 'dev').

    ## Response Structure

    Returns a list of RedshiftDatabase objects with the following structure:

    - database_name: The name of the database.
    - database_owner: The database owner user ID.
    - database_type: The type of database (local or shared).
    - database_acl: Access control information (for internal use).
    - database_options: The properties of the database.
    - database_isolation_level: The isolation level (Snapshot Isolation or Serializable).

    ## Usage Tips

    1. First use list_clusters to get valid cluster identifiers.
    2. Ensure the cluster status is 'available' before querying databases.
    3. Use the default database name unless you know a specific database exists.
    4. Note database types to understand if they are local or shared from datashares.

    ## Interpretation Best Practices

    1. Focus on 'local' database types for cluster-native databases.
    2. 'shared' database types indicate databases from datashares.
    3. Use database names for subsequent schema and table discovery.
    4. Consider database isolation levels for transaction planning.
    """
    try:
        logger.info(f'Discovering databases on cluster: {cluster_identifier}')
        databases_data = await discover_databases(cluster_identifier, database_name)

        # Convert to RedshiftDatabase models
        databases = []
        for database_data in databases_data:
            database = RedshiftDatabase(**database_data)
            databases.append(database)

        logger.info(
            f'Successfully retrieved {len(databases)} databases from cluster {cluster_identifier}'
        )
        return databases

    except Exception as e:
        logger.error(f'Error in list_databases_tool: {str(e)}')
        await ctx.error(f'Failed to list databases on cluster {cluster_identifier}: {str(e)}')
        raise


@mcp.tool(name='list_schemas')
async def list_schemas_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to query for schemas. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    schema_database_name: str = Field(
        ...,
        description='The database name to list schemas for. Also used to connect to. Must be a valid database name from the list_databases tool.',
    ),
) -> list[RedshiftSchema]:
    """List all schemas in a specified database within a Redshift cluster.

    This tool queries the SVV_ALL_SCHEMAS system view to discover all schemas
    that the user has access to in the specified database, including local schemas,
    external schemas, and shared schemas from datashares.

    ## Usage Requirements

    - Ensure your AWS credentials are properly configured (via AWS_PROFILE or default credentials).
    - The cluster must be available and accessible.
    - Required IAM permissions: redshift-data:ExecuteStatement, redshift-data:DescribeStatement, redshift-data:GetStatementResult.
    - The user must have access to the database to query system views.

    ## Parameters

    - cluster_identifier: The unique identifier of the Redshift cluster to query.
                         IMPORTANT: Use a valid cluster identifier from the list_clusters tool.
    - schema_database_name: The database name to list schemas for. Also used to connect to.
                           IMPORTANT: Use a valid database name from the list_databases tool.

    ## Response Structure

    Returns a list of RedshiftSchema objects with the following structure:

    - database_name: The name of the database where the schema exists.
    - schema_name: The name of the schema.
    - schema_owner: The user ID of the schema owner.
    - schema_type: The type of the schema (external, local, or shared).
    - schema_acl: The permissions for the specified user or user group for the schema.
    - source_database: The name of the source database for external schema.
    - schema_option: The options of the schema (external schema attribute).

    ## Usage Tips

    1. First use list_clusters to get valid cluster identifiers.
    2. Then use list_databases to get valid database names for the cluster.
    3. Ensure the cluster status is 'available' before querying schemas.
    4. Note schema types to understand if they are local, external, or shared.
    5. External schemas connect to external data sources like S3 or other databases.

    ## Interpretation Best Practices

    1. Focus on 'local' schema types for cluster-native schemas.
    2. 'external' schema types indicate connections to external data sources.
    3. 'shared' schema types indicate schemas from datashares.
    4. Use schema names for subsequent table and column discovery.
    5. Consider schema permissions (schema_acl) for access planning.
    """
    try:
        logger.info(
            f'Discovering schemas in database {schema_database_name} on cluster {cluster_identifier}'
        )
        schemas_data = await discover_schemas(cluster_identifier, schema_database_name)

        # Convert to RedshiftSchema models
        schemas = []
        for schema_data in schemas_data:
            schema = RedshiftSchema(**schema_data)
            schemas.append(schema)

        logger.info(
            f'Successfully retrieved {len(schemas)} schemas from database {schema_database_name} on cluster {cluster_identifier}'
        )
        return schemas

    except Exception as e:
        logger.error(f'Error in list_schemas_tool: {str(e)}')
        await ctx.error(
            f'Failed to list schemas in database {schema_database_name} on cluster {cluster_identifier}: {str(e)}'
        )
        raise


@mcp.tool(name='list_tables')
async def list_tables_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to query for tables. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    table_database_name: str = Field(
        ...,
        description='The database name to list tables for. Must be a valid database name from the list_databases tool.',
    ),
    table_schema_name: str = Field(
        ...,
        description='The schema name to list tables for. Also used to connect to. Must be a valid schema name from the list_schemas tool.',
    ),
) -> list[RedshiftTable]:
    """List all tables in a specified schema within a Redshift database.

    This tool queries the SVV_ALL_TABLES system view to discover all tables
    that the user has access to in the specified schema, including base tables,
    views, external tables, and shared tables.

    ## Usage Requirements

    - Ensure your AWS credentials are properly configured (via AWS_PROFILE or default credentials).
    - The cluster must be available and accessible.
    - Required IAM permissions: redshift-data:ExecuteStatement, redshift-data:DescribeStatement, redshift-data:GetStatementResult.
    - The user must have access to the database to query system views.

    ## Parameters

    - cluster_identifier: The unique identifier of the Redshift cluster to query.
                         IMPORTANT: Use a valid cluster identifier from the list_clusters tool.
    - table_database_name: The database name to list tables for.
                          IMPORTANT: Use a valid database name from the list_databases tool.
    - table_schema_name: The schema name to list tables for.
                        IMPORTANT: Use a valid schema name from the list_schemas tool.

    ## Response Structure

    Returns a list of RedshiftTable objects with the following structure:

    - database_name: The name of the database where the table exists.
    - schema_name: The schema name for the table.
    - table_name: The name of the table.
    - table_acl: The permissions for the specified user or user group for the table.
    - table_type: The type of the table (views, base tables, external tables, shared tables).
    - remarks: Remarks about the table.

    ## Usage Tips

    1. First use list_clusters to get valid cluster identifiers.
    2. Then use list_databases to get valid database names for the cluster.
    3. Then use list_schemas to get valid schema names for the database.
    4. Ensure the cluster status is 'available' before querying tables.
    5. Note table types to understand if they are base tables, views, external tables, or shared tables.

    ## Interpretation Best Practices

    1. Focus on 'TABLE' table types for regular database tables.
    2. 'VIEW' table types indicate database views.
    3. 'EXTERNAL TABLE' types indicate connections to external data sources.
    4. 'SHARED TABLE' types indicate tables from datashares.
    5. Use table names for subsequent column discovery and query operations.
    6. Consider table permissions (table_acl) for access planning.
    """
    try:
        logger.info(
            f'Discovering tables in schema {table_schema_name} in database {table_database_name} on cluster {cluster_identifier}'
        )
        tables_data = await discover_tables(
            cluster_identifier, table_database_name, table_schema_name
        )

        # Convert to RedshiftTable models
        tables = []
        for table_data in tables_data:
            table = RedshiftTable(**table_data)
            tables.append(table)

        logger.info(
            f'Successfully retrieved {len(tables)} tables from schema {table_schema_name} in database {table_database_name} on cluster {cluster_identifier}'
        )
        return tables

    except Exception as e:
        logger.error(f'Error in list_tables_tool: {str(e)}')
        await ctx.error(
            f'Failed to list tables in schema {table_schema_name} in database {table_database_name} on cluster {cluster_identifier}: {str(e)}'
        )
        raise


@mcp.tool(name='list_columns')
async def list_columns_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to query for columns. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    column_database_name: str = Field(
        ...,
        description='The database name to list columns for. Must be a valid database name from the list_databases tool.',
    ),
    column_schema_name: str = Field(
        ...,
        description='The schema name to list columns for. Must be a valid schema name from the list_schemas tool.',
    ),
    column_table_name: str = Field(
        ...,
        description='The table name to list columns for. Must be a valid table name from the list_tables tool.',
    ),
) -> list[RedshiftColumn]:
    """List all columns in a specified table within a Redshift schema.

    This tool queries the SVV_ALL_COLUMNS system view to discover all columns
    that the user has access to in the specified table, including detailed information
    about data types, constraints, and column properties.

    ## Usage Requirements

    - Ensure your AWS credentials are properly configured (via AWS_PROFILE or default credentials).
    - The cluster must be available and accessible.
    - Required IAM permissions: redshift-data:ExecuteStatement, redshift-data:DescribeStatement, redshift-data:GetStatementResult.
    - The user must have access to the database to query system views.

    ## Parameters

    - cluster_identifier: The unique identifier of the Redshift cluster to query.
                         IMPORTANT: Use a valid cluster identifier from the list_clusters tool.
    - column_database_name: The database name to list columns for.
                           IMPORTANT: Use a valid database name from the list_databases tool.
    - column_schema_name: The schema name to list columns for.
                         IMPORTANT: Use a valid schema name from the list_schemas tool.
    - column_table_name: The table name to list columns for.
                        IMPORTANT: Use a valid table name from the list_tables tool.

    ## Response Structure

    Returns a list of RedshiftColumn objects with the following structure:

    - database_name: The name of the database.
    - schema_name: The name of the schema.
    - table_name: The name of the table.
    - column_name: The name of the column.
    - ordinal_position: The position of the column in the table.
    - column_default: The default value of the column.
    - is_nullable: Whether the column is nullable (yes or no).
    - data_type: The data type of the column.
    - character_maximum_length: The maximum number of characters in the column.
    - numeric_precision: The numeric precision.
    - numeric_scale: The numeric scale.
    - remarks: Remarks about the column.

    ## Usage Tips

    1. First use list_clusters to get valid cluster identifiers.
    2. Then use list_databases to get valid database names for the cluster.
    3. Then use list_schemas to get valid schema names for the database.
    4. Then use list_tables to get valid table names for the schema.
    5. Ensure the cluster status is 'available' before querying columns.
    6. Note data types and constraints for query planning and data validation.

    ## Interpretation Best Practices

    1. Use ordinal_position to understand column order in the table.
    2. Check is_nullable for required vs optional fields.
    3. Use data_type information for proper data handling in queries.
    4. Consider character_maximum_length for string field validation.
    5. Use numeric_precision and numeric_scale for numeric field handling.
    6. Use column names for SELECT statements and query construction.
    """
    try:
        logger.info(
            f'Discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} on cluster {cluster_identifier}'
        )
        columns_data = await discover_columns(
            cluster_identifier, column_database_name, column_schema_name, column_table_name
        )

        # Convert to RedshiftColumn models
        columns = []
        for column_data in columns_data:
            column = RedshiftColumn(**column_data)
            columns.append(column)

        logger.info(
            f'Successfully retrieved {len(columns)} columns from table {column_table_name} in schema {column_schema_name} in database {column_database_name} on cluster {cluster_identifier}'
        )
        return columns

    except Exception as e:
        logger.error(f'Error in list_columns_tool: {str(e)}')
        await ctx.error(
            f'Failed to list columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} on cluster {cluster_identifier}: {str(e)}'
        )
        raise


@mcp.tool(name='execute_query')
async def execute_query_tool(
    ctx: Context,
    cluster_identifier: str = Field(
        ...,
        description='The cluster identifier to execute the query on. Must be a valid cluster identifier from the list_clusters tool.',
    ),
    database_name: str = Field(
        ...,
        description='The database name to execute the query against. Must be a valid database name from the list_databases tool.',
    ),
    sql: str = Field(
        ..., description='The SQL statement to execute. Should be a single SQL statement.'
    ),
) -> QueryResult:
    """Execute a SQL query against a Redshift cluster or serverless workgroup.

    This tool uses the Redshift Data API to execute SQL queries and return results.
    It supports both provisioned clusters and serverless workgroups, and handles
    various data types in the result set.

    ## Usage Requirements

    - Ensure your AWS credentials are properly configured (via AWS_PROFILE or default credentials).
    - The cluster must be available and accessible.
    - Required IAM permissions: redshift-data:ExecuteStatement, redshift-data:DescribeStatement, redshift-data:GetStatementResult.
    - The user must have appropriate permissions to execute queries in the specified database.

    ## Parameters

    - cluster_identifier: The unique identifier of the Redshift cluster to query.
                         IMPORTANT: Use a valid cluster identifier from the list_clusters tool.
    - database_name: The database name to execute the query against.
                    IMPORTANT: Use a valid database name from the list_databases tool.
    - sql: The SQL statement to execute. Should be a single SQL statement.

    ## Response Structure

    Returns a QueryResult object with the following structure:

    - columns: List of column names in the result set.
    - rows: List of rows, where each row is a list of values.
    - row_count: Number of rows returned.
    - execution_time_ms: Query execution time in milliseconds.
    - query_id: Unique identifier for the query execution.

    ## Usage Tips

    1. First use list_clusters to get valid cluster identifiers.
    2. Then use list_databases to get valid database names for the cluster.
    3. Ensure the cluster status is 'available' before executing queries.
    4. Use LIMIT clauses for exploratory queries to avoid large result sets.
    5. Consider using the metadata discovery tools to understand table structures before querying.

    ## Data Type Handling

    The tool automatically handles various Redshift data types:
    - String values (VARCHAR, CHAR, TEXT).
    - Numeric values (INTEGER, BIGINT, DECIMAL, FLOAT).
    - Boolean values.
    - NULL values.
    - Date and timestamp values (returned as strings).

    ## Security Considerations

    - Avoid dynamic SQL construction with user input.
    - Consider database object permissions.
    - Currently, the execute_query tool runs the query in a READ ONLY transaction to prevent unintentional modifications.
    - The READ WRITE mode will be added in the future versions with additional protection mechanisms.
    """
    try:
        logger.info(f'Executing query on cluster {cluster_identifier} in database {database_name}')
        query_result_data = await execute_query(cluster_identifier, database_name, sql)

        # Convert to QueryResult model
        query_result = QueryResult(**query_result_data)

        logger.info(
            f'Successfully executed query on cluster {cluster_identifier}: {query_result.row_count} rows returned in {query_result.execution_time_ms}ms'
        )
        return query_result

    except Exception as e:
        logger.error(f'Error in execute_query_tool: {str(e)}')
        await ctx.error(
            f'Failed to execute query on cluster {cluster_identifier} in database {database_name}: {str(e)}'
        )
        raise


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
