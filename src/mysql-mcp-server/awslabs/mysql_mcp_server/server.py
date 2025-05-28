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

"""awslabs mysql MCP Server implementation."""

import argparse
import asyncio
import boto3
import sys
from awslabs.mysql_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
)
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


client_error_code_key = 'run_query ClientError code'
unexpected_error_key = 'run_query unexpected error'
write_query_prohibited_key = 'Your MCP tool only allows readonly query. If you want to write, change the MCP configuration per README.md'
query_injection_risk_key = 'Your query contains risky injection patterns'


class DummyCtx:
    """A dummy context class for error handling in MCP tools."""

    async def error(self, message):
        """Raise a runtime error with the given message.

        Args:
            message: The error message to include in the runtime error
        """
        # Do nothing
        pass


class DBConnection:
    """Class that wraps DB connection client by RDS API."""

    def __init__(self, cluster_arn, secret_arn, database, region, readonly, is_test=False):
        """Initialize a new DB connection.

        Args:
            cluster_arn: The ARN of the RDS cluster
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only
            is_test: Whether this is a test connection
        """
        self.cluster_arn = cluster_arn
        self.secret_arn = secret_arn
        self.database = database
        self.readonly = readonly
        if not is_test:
            self.data_client = boto3.client('rds-data', region_name=region)

    @property
    def readonly_query(self):
        """Get whether this connection is read-only.

        Returns:
            bool: True if the connection is read-only, False otherwise
        """
        return self.readonly


class DBConnectionSingleton:
    """Manages a single DBConnection instance across the application.

    This singleton ensures that only one DBConnection is created and reused.
    """

    _instance = None

    def __init__(self, resource_arn, secret_arn, database, region, readonly, is_test=False):
        """Initialize a new DB connection singleton.

        Args:
            resource_arn: The ARN of the RDS resource
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only
            is_test: Whether this is a test connection
        """
        if not all([resource_arn, secret_arn, database, region]):
            raise ValueError(
                'Missing required connection parameters. '
                'Please provide resource_arn, secret_arn, database, and region.'
            )
        self._db_connection = DBConnection(
            resource_arn, secret_arn, database, region, readonly, is_test
        )

    @classmethod
    def initialize(cls, resource_arn, secret_arn, database, region, readonly, is_test=False):
        """Initialize the singleton instance if it doesn't exist.

        Args:
            resource_arn: The ARN of the RDS resource
            secret_arn: The ARN of the secret containing credentials
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only
            is_test: Whether this is a test connection
        """
        if cls._instance is None:
            cls._instance = cls(resource_arn, secret_arn, database, region, readonly, is_test)

    @classmethod
    def get(cls):
        """Get the singleton instance.

        Returns:
            DBConnectionSingleton: The singleton instance

        Raises:
            RuntimeError: If the singleton has not been initialized
        """
        if cls._instance is None:
            raise RuntimeError('DBConnectionSingleton is not initialized.')
        return cls._instance

    @property
    def db_connection(self):
        """Get the database connection.

        Returns:
            DBConnection: The database connection instance
        """
        return self._db_connection


def extract_cell(cell: dict):
    """Extracts the scalar or array value from a single cell."""
    if cell.get('isNull'):
        return None
    for key in (
        'stringValue',
        'longValue',
        'doubleValue',
        'booleanValue',
        'blobValue',
        'arrayValue',
    ):
        if key in cell:
            return cell[key]
    return None


def parse_execute_response(response: dict) -> list[dict]:
    """Convert RDS Data API execute_statement response to list of rows."""
    columns = [col['name'] for col in response.get('columnMetadata', [])]
    records = []

    for row in response.get('records', []):
        row_data = {col: extract_cell(cell) for col, cell in zip(columns, row)}
        records.append(row_data)

    return records


mcp = FastMCP(
    'awslabs.mysql-mcp-server',
    instructions='You are an expert MySQL assistant. Use run_query and get_table_schema to interfact with the database.',
    dependencies=['loguru', 'boto3', 'pydantic'],
)


@mcp.tool(name='run_query', description='Run a SQL query against a MySQL database')
async def run_query(
    sql: Annotated[str, Field(description='The SQL query to run')],
    ctx: Context,
    db_connection=None,
    query_parameters: Annotated[
        Optional[List[Dict[str, Any]]], Field(description='Parameters for the SQL query')
    ] = None,
) -> list[dict]:  # type: ignore
    """Run a SQL query against a MySQL database.

    Args:
        sql: The sql statement to run
        ctx: MCP context for logging and state management
        db_connection: DB connection object passed by unit test. It should be None if if called by MCP server.
        query_parameters: Parameters for the SQL query

    Returns:
        List of dictionary that contains query response rows
    """
    global client_error_code_key
    global unexpected_error_key
    global write_query_prohibited_key

    if db_connection is None:
        db_connection = DBConnectionSingleton.get().db_connection

    if db_connection.readonly_query:
        matches = detect_mutating_keywords(sql)
        if (bool)(matches):
            logger.info(
                f'query is rejected because current setting only allows readonly query. detected keywords: {matches}, SQL query: {sql}'
            )

            await ctx.error(write_query_prohibited_key)
            return [{'error': write_query_prohibited_key}]

    issues = check_sql_injection_risk(sql)
    if issues:
        logger.info(
            f'query is rejected because it contains risky SQL pattern, SQL query: {sql}, reasons: {issues}'
        )
        await ctx.error(
            str({'message': 'Query parameter contains suspicious pattern', 'details': issues})
        )
        return [{'error': query_injection_risk_key}]

    try:
        logger.info(f'run_query: readonly:{db_connection.readonly_query}, SQL:{sql}')

        execute_params = {
            'resourceArn': db_connection.cluster_arn,
            'secretArn': db_connection.secret_arn,
            'database': db_connection.database,
            'sql': sql,
            'includeResultMetadata': True,
        }

        if query_parameters:
            execute_params['parameters'] = query_parameters

        response = await asyncio.to_thread(
            db_connection.data_client.execute_statement, **execute_params
        )

        logger.success('run_query successfully executed query:{}', sql)
        return parse_execute_response(response)
    except ClientError as e:
        logger.exception(client_error_code_key)
        await ctx.error(
            str({'code': e.response['Error']['Code'], 'message': e.response['Error']['Message']})
        )
        return [{'error': client_error_code_key}]
    except Exception as e:
        logger.exception(unexpected_error_key)
        error_details = f'{type(e).__name__}: {str(e)}'
        await ctx.error(str({'message': error_details}))
        return [{'error': unexpected_error_key}]


@mcp.tool(
    name='get_table_schema',
    description='Fetch table schema from the MySQL database',
)
async def get_table_schema(
    table_name: Annotated[str, Field(description='name of the table')],
    database_name: Annotated[str, Field(description='name of the database')],
    ctx: Context,
) -> list[dict]:
    """Get a table's schema information given the table name.

    Args:
        table_name: name of the table
        database_name: name of the database
        ctx: MCP context for logging and state management

    Returns:
        List of dictionary that contains query response rows
    """
    logger.info(f'get_table_schema: {table_name}')

    sql = """
        SELECT
            COLUMN_NAME,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            EXTRA,
            COLUMN_KEY,
            COLUMN_COMMENT
        FROM
            information_schema.columns
        WHERE
            table_schema = :database_name
            AND table_name = :table_name
        ORDER BY
            ORDINAL_POSITION
    """
    params = [
        {'name': 'table_name', 'value': {'stringValue': table_name}},
        {'name': 'database_name', 'value': {'stringValue': database_name}},
    ]

    return await run_query(sql=sql, ctx=ctx, query_parameters=params)


def main():
    """Main entry point for the MCP server application."""
    global client_error_code_key

    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for MySQL'
    )
    parser.add_argument('--resource_arn', required=True, help='ARN of the RDS cluster')
    parser.add_argument(
        '--secret_arn',
        required=True,
        help='ARN of the Secrets Manager secret for database credentials',
    )
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument(
        '--region', required=True, help='AWS region for RDS Data API (default: us-west-2)'
    )
    parser.add_argument(
        '--readonly', required=True, help='Enforce NL to SQL to only allow readonly sql statement'
    )
    args = parser.parse_args()

    logger.info(
        'MySQL MCP init with CLUSTER_ARN:{}, SECRET_ARN:{}, REGION:{}, DATABASE:{}, READONLY:{}',
        args.resource_arn,
        args.secret_arn,
        args.region,
        args.database,
        args.readonly,
    )

    try:
        DBConnectionSingleton.initialize(
            args.resource_arn, args.secret_arn, args.database, args.region, args.readonly
        )
    except BotoCoreError:
        logger.exception('Failed to RDS API client object for MySQL. Exit the MCP server')
        sys.exit(1)

    # Test RDS API connection
    ctx = DummyCtx()
    response = asyncio.run(run_query('SELECT 1', ctx))
    if (
        isinstance(response, list)
        and len(response) == 1
        and isinstance(response[0], dict)
        and 'error' in response[0]
    ):
        logger.error('Failed to validate RDS API db connection to MySQL. Exit the MCP server')
        sys.exit(1)

    logger.success('Successfully validated RDS API db connection to MySQL')

    # Run server with appropriate transport
    logger.info('Starting MySQL MCP server')
    mcp.run()


if __name__ == '__main__':
    main()
