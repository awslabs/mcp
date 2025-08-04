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

"""awslabs postgres MCP Server implementation."""

import argparse
import asyncio
import sys
from awslabs.postgres_mcp_server.connection import DBConnectionSingleton
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import PsycopgPoolConnection
from awslabs.postgres_mcp_server.mutable_sql_detector import (
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
query_comment_prohibited_key = 'The comment in query is prohibited because of injection risk'
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
    'pg-mcp MCP server. This is the starting point for all solutions created',
    dependencies=[
        'loguru',
    ],
)


@mcp.tool(name='run_query', description='Run a SQL query against PostgreSQL')
async def run_query(
    sql: Annotated[str, Field(description='The SQL query to run')],
    ctx: Context,
    db_connection=None,
    query_parameters: Annotated[
        Optional[List[Dict[str, Any]]], Field(description='Parameters for the SQL query')
    ] = None,
) -> list[dict]:  # type: ignore
    """Run a SQL query against PostgreSQL.

    Args:
        sql: The sql statement to run
        ctx: MCP context for logging and state management
        db_connection: DB connection object passed by unit test. It should be None if called by MCP server.
        query_parameters: Parameters for the SQL query

    Returns:
        List of dictionary that contains query response rows
    """
    global client_error_code_key
    global unexpected_error_key
    global write_query_prohibited_key

    if db_connection is None:
        try:
            # Try to get the connection from the singleton
            db_connection = DBConnectionSingleton.get().db_connection
        except RuntimeError:
            # If the singleton is not initialized, this might be a direct connection
            logger.error('No database connection available')
            await ctx.error('No database connection available')
            return [{'error': 'No database connection available'}]

    if db_connection is None:
        raise AssertionError('db_connection should never be None')

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

        # Execute the query using the abstract connection interface
        response = await db_connection.execute_query(sql, query_parameters)

        logger.success(f'run_query successfully executed query:{sql}')
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
    description='Fetch table columns and comments from Postgres',
)
async def get_table_schema(
    table_name: Annotated[str, Field(description='name of the table')], ctx: Context
) -> list[dict]:
    """Get a table's schema information given the table name.

    Args:
        table_name: name of the table
        ctx: MCP context for logging and state management

    Returns:
        List of dictionary that contains query response rows
    """
    logger.info(f'get_table_schema: {table_name}')

    sql = """
        SELECT
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            col_description(a.attrelid, a.attnum) AS column_comment
        FROM
            pg_attribute a
        WHERE
            a.attrelid = to_regclass(:table_name)
            AND a.attnum > 0
            AND NOT a.attisdropped
        ORDER BY a.attnum
    """

    params = [{'name': 'table_name', 'value': {'stringValue': table_name}}]

    return await run_query(sql=sql, ctx=ctx, query_parameters=params)


def main():
    """Main entry point for the MCP server application."""
    global client_error_code_key

    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for postgres'
    )

    # Connection method 1: RDS Data API
    parser.add_argument('--resource_arn', help='ARN of the RDS cluster (for RDS Data API)')

    # Connection method 2: Psycopg Direct Connection
    parser.add_argument('--hostname', help='Database hostname (for direct PostgreSQL connection)')
    parser.add_argument('--port', type=int, default=5432, help='Database port (default: 5432)')

    # Common parameters
    parser.add_argument(
        '--secret_arn',
        required=True,
        help='ARN of the Secrets Manager secret for database credentials',
    )
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument('--readonly', required=True, help='Enforce readonly SQL statements')

    args = parser.parse_args()

    # Validate connection parameters
    if not args.resource_arn and not args.hostname:
        parser.error(
            'Either --resource_arn (for RDS Data API) or '
            '--hostname (for direct PostgreSQL) must be provided'
        )

    if args.resource_arn and args.hostname:
        parser.error(
            'Cannot specify both --resource_arn and --hostname. Choose one connection method.'
        )

    # Convert args to dict for easier handling
    connection_params = vars(args)

    # Convert readonly string to boolean
    connection_params['readonly'] = args.readonly.lower() == 'true'

    # Log connection information
    connection_target = args.resource_arn if args.resource_arn else f'{args.hostname}:{args.port}'

    if args.resource_arn:
        logger.info(
            f'Postgres MCP init with RDS Data API: CONNECTION_TARGET:{connection_target}, SECRET_ARN:{args.secret_arn}, REGION:{args.region}, DATABASE:{args.database}, READONLY:{args.readonly}'
        )
    else:
        logger.info(
            f'Postgres MCP init with psycopg: CONNECTION_TARGET:{connection_target}, PORT:{args.port}, DATABASE:{args.database}, READONLY:{args.readonly}'
        )

    # Create the appropriate database connection based on the provided parameters
    db_connection = None

    try:
        if args.resource_arn:
            # Use RDS Data API with singleton pattern
            try:
                # Initialize the RDS Data API connection singleton
                DBConnectionSingleton.initialize(
                    resource_arn=args.resource_arn,
                    secret_arn=args.secret_arn,
                    database=args.database,
                    region=args.region,
                    readonly=connection_params['readonly'],
                )

                # Get the connection from the singleton
                db_connection = DBConnectionSingleton.get().db_connection
            except Exception as e:
                logger.exception(f'Failed to create RDS Data API connection: {str(e)}')
                sys.exit(1)

        else:
            # Use Direct PostgreSQL connection using psycopg connection pool
            try:
                # Create a direct PostgreSQL connection pool
                db_connection = PsycopgPoolConnection(
                    host=args.hostname,
                    port=args.port,
                    database=args.database,
                    readonly=connection_params['readonly'],
                    secret_arn=args.secret_arn,
                    region=args.region,
                )
            except Exception as e:
                logger.exception(f'Failed to create PostgreSQL connection: {str(e)}')
                sys.exit(1)

    except BotoCoreError as e:
        logger.exception(f'Failed to create database connection: {str(e)}')
        sys.exit(1)

    # Test database connection
    ctx = DummyCtx()
    response = asyncio.run(run_query('SELECT 1', ctx, db_connection))
    if (
        isinstance(response, list)
        and len(response) == 1
        and isinstance(response[0], dict)
        and 'error' in response[0]
    ):
        logger.error('Failed to validate database connection to Postgres. Exit the MCP server')
        sys.exit(1)

    logger.success('Successfully validated database connection to Postgres')

    logger.info('Starting Postgres MCP server')
    mcp.run()


if __name__ == '__main__':
    main()
