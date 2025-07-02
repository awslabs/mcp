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
import boto3
import sys
from awslabs.postgres_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
)
from awslabs.postgres_mcp_server.connection import DBConnectionSingleton
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
    'apg-mcp MCP server. This is the starting point for all solutions created',
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
    
    assert db_connection is not None, "db_connection should never be None"

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
    
    # Common arguments
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument(
        '--secret_arn',
        required=True,
        help='ARN of the Secrets Manager secret for database credentials',
    )
    parser.add_argument(
        '--readonly', required=True, help='Enforce NL to SQL to only allow readonly sql statement'
    )
    
    # Connection type arguments
    parser.add_argument('--resource_arn', help='ARN of the RDS cluster (for RDS Data API or fallback)')
    parser.add_argument('--hostname', help='Database host (for direct psycopg connection)')
    
    # Other arguments
    parser.add_argument('--region_name', help='AWS region for RDS Data API and Secrets Manager')
    parser.add_argument('--port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument('--user', help='Database user (for direct psycopg connection)')
    parser.add_argument('--password', help='Database password (for direct psycopg connection)')
    
    args = parser.parse_args()
    
    # Convert args to dict for easier handling
    connection_params = vars(args)
    
    # For backward compatibility, map region to region_name if region_name is not provided
    if 'region' in connection_params and not connection_params.get('region_name'):
        connection_params['region_name'] = connection_params['region']
    
    # Log connection information
    if args.resource_arn and not args.hostname:
        logger.info(
            'Postgres MCP init with RDS Data API: RESOURCE_ARN:{}, SECRET_ARN:{}, REGION:{}, DATABASE:{}, READONLY:{}',
            args.resource_arn,
            args.secret_arn,
            args.region_name,
            args.database,
            args.readonly,
        )
    elif args.hostname:
        logger.info(
            'Postgres MCP init with psycopg: HOST:{}, PORT:{}, DATABASE:{}, USER:{}, READONLY:{}',
            args.hostname,
            args.port,
            args.database,
            args.user,
            args.readonly,
        )
    else:
        logger.error('Either resource_arn or hostname must be provided')
        sys.exit(1)

    try:
        # Initialize the connection singleton with the new connection factory
        DBConnectionSingleton.initialize(**connection_params)
    except BotoCoreError:
        logger.exception('Failed to RDS API client object for Postgres. Exit the MCP server')
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
        logger.error('Failed to validate RDS API db connection to Postgres. Exit the MCP server')
        sys.exit(1)

    logger.success('Successfully validated RDS API db connection to Postgres')

    logger.info('Starting Postgres MCP server')
    mcp.run()


if __name__ == '__main__':
    main()
