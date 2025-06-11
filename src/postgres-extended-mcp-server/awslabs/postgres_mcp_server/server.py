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
from awslabs.postgres_mcp_server.connection_factory import ConnectionFactory
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional, Union


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
    """Manages a single database connection instance across the application.

    This singleton ensures that only one connection is created and reused.
    The connection can be either a direct psycopg3 connection or an RDS Data API connection.
    """

    _instance = None
    _connection = None

    def __init__(self, **kwargs):
        """Initialize a new DB connection singleton.

        Args:
            **kwargs: Connection parameters that will be passed to ConnectionFactory
        """
        self._connection_params = kwargs

    @classmethod
    async def initialize(cls, **kwargs):
        """Initialize the singleton instance if it doesn't exist.

        Args:
            **kwargs: Connection parameters that will be passed to ConnectionFactory
        """
        if cls._instance is None:
            cls._instance = cls(**kwargs)
            cls._instance._connection = await ConnectionFactory.create_connection(kwargs)

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
            Union[DBConnection, PostgresDirectConnection]: The database connection instance
        """
        return self._connection


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


@mcp.tool(name='run_query', description='Run a SQL query using boto3 execute_statement')
async def run_query(
    sql: Annotated[str, Field(description='The SQL query to run')],
    ctx: Context,
    db_connection=None,
    query_parameters: Annotated[
        Optional[List[Dict[str, Any]]], Field(description='Parameters for the SQL query')
    ] = None,
) -> list[dict]:  # type: ignore
    """Run a SQL query using boto3 execute_statement.

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

        # Check if the connection is a direct psycopg3 connection
        if hasattr(db_connection, 'execute_query'):
            # Use the psycopg3 connection's execute_query method
            if db_connection.readonly_query:
                response = await db_connection.execute_readonly_query(sql, 'mcp_session', query_parameters)
            else:
                response = await db_connection.execute_query(sql, 'mcp_session', query_parameters)
            
            # The response is already in the correct format
            logger.success('run_query successfully executed query using psycopg3:{}', sql)
            return response
        else:
            # Use the RDS Data API connection
            if db_connection.readonly_query:
                response = await asyncio.to_thread(
                    execute_readonly_query, db_connection, sql, query_parameters
                )
            else:
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

            logger.success('run_query successfully executed query using RDS Data API:{}', sql)
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
    description='Fetch table columns and comments from Postgres using RDS Data API',
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
            a.attrelid = :table_name::regclass
            AND a.attnum > 0
            AND NOT a.attisdropped
        ORDER BY a.attnum
    """

    params = [{'name': 'table_name', 'value': {'stringValue': table_name}}]

    return await run_query(sql=sql, ctx=ctx, query_parameters=params)


def execute_readonly_query(
    db_connection: DBConnection, query: str, parameters: Optional[List[Dict[str, Any]]] = None
) -> dict:
    """Execute a query under readonly transaction.

    Args:
        db_connection: connection object
        query: query to run
        parameters: parameters

    Returns:
        List of dictionary that contains query response rows
    """
    tx_id = ''
    try:
        # Begin read-only transaction
        tx = db_connection.data_client.begin_transaction(
            resourceArn=db_connection.cluster_arn,
            secretArn=db_connection.secret_arn,
            database=db_connection.database,
        )

        tx_id = tx['transactionId']

        db_connection.data_client.execute_statement(
            resourceArn=db_connection.cluster_arn,
            secretArn=db_connection.secret_arn,
            database=db_connection.database,
            sql='SET TRANSACTION READ ONLY',
            transactionId=tx_id,
        )

        execute_params = {
            'resourceArn': db_connection.cluster_arn,
            'secretArn': db_connection.secret_arn,
            'database': db_connection.database,
            'sql': query,
            'includeResultMetadata': True,
            'transactionId': tx_id,
        }

        if parameters is not None:
            execute_params['parameters'] = parameters

        result = db_connection.data_client.execute_statement(**execute_params)

        db_connection.data_client.commit_transaction(
            resourceArn=db_connection.cluster_arn,
            secretArn=db_connection.secret_arn,
            transactionId=tx_id,
        )
        return result
    except Exception as e:
        if tx_id:
            db_connection.data_client.rollback_transaction(
                resourceArn=db_connection.cluster_arn,
                secretArn=db_connection.secret_arn,
                transactionId=tx_id,
            )
        raise e


def main():
    """Main entry point for the MCP server application."""
    global client_error_code_key

    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for postgres'
    )
    # RDS Data API connection parameters
    parser.add_argument('--resource_arn', help='ARN of the RDS cluster')
    parser.add_argument(
        '--secret_arn',
        help='ARN of the Secrets Manager secret for database credentials',
    )
    parser.add_argument(
        '--region', help='AWS region for RDS Data API'
    )
    
    # Direct connection parameters
    parser.add_argument('--reader_endpoint', help='PostgreSQL reader endpoint')
    parser.add_argument('--writer_endpoint', help='PostgreSQL writer endpoint')
    parser.add_argument('--port', type=int, default=5432, help='PostgreSQL port')
    
    # Common parameters
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument(
        '--readonly', default='True', help='Enforce NL to SQL to only allow readonly sql statement'
    )
    parser.add_argument('--min_connections', type=int, default=1, help='Minimum connections in pool')
    parser.add_argument('--max_connections', type=int, default=10, help='Maximum connections in pool')
    
    args = parser.parse_args()
    
    # Convert readonly string to boolean
    readonly = args.readonly.lower() == 'true'
    
    # Validate arguments
    if not args.database:
        logger.error('Database name is required')
        sys.exit(1)
        
    # Validate arguments based on readonly flag
    if readonly:
        if not ((args.resource_arn and args.secret_arn and args.region) or 
                (args.reader_endpoint and args.secret_arn and args.region)):
            logger.error('For readonly operations, provide either RDS Data API parameters (resource_arn, secret_arn, region) or '
                        'direct connection parameters (reader_endpoint, secret_arn, region)')
            sys.exit(1)
    else:
        if not ((args.resource_arn and args.secret_arn and args.region) or 
                (args.writer_endpoint and args.secret_arn and args.region)):
            logger.error('For write operations, provide either RDS Data API parameters (resource_arn, secret_arn, region) or '
                        'direct connection parameters (writer_endpoint, secret_arn, region)')
            sys.exit(1)
    
    # Log connection parameters
    if args.reader_endpoint or args.writer_endpoint:
        logger.info(
            'Postgres MCP init with READER_ENDPOINT:{}, WRITER_ENDPOINT:{}, PORT:{}, DATABASE:{}, READONLY:{}',
            args.reader_endpoint or "Not provided",
            args.writer_endpoint or "Not provided",
            args.port,
            args.database,
            readonly,
        )
    else:
        logger.info(
            'Postgres MCP init with CLUSTER_ARN:{}, SECRET_ARN:{}, REGION:{}, DATABASE:{}, READONLY:{}',
            args.resource_arn,
            args.secret_arn,
            args.region,
            args.database,
            readonly,
        )

    # Initialize connection
    try:
        # Create a dictionary of connection parameters
        connection_params = {
            'resource_arn': args.resource_arn,
            'secret_arn': args.secret_arn,
            'region': args.region,
            'reader_endpoint': args.reader_endpoint,
            'writer_endpoint': args.writer_endpoint,
            'port': args.port,
            'database': args.database,
            'readonly': readonly,
            'min_connections': args.min_connections,
            'max_connections': args.max_connections
        }
        
        # Initialize the connection
        asyncio.run(DBConnectionSingleton.initialize(**connection_params))
    except Exception as e:
        logger.exception(f'Failed to initialize database connection: {str(e)}')
        sys.exit(1)

    # Test connection
    ctx = DummyCtx()
    response = asyncio.run(run_query('SELECT 1', ctx))
    if (
        isinstance(response, list)
        and len(response) == 1
        and isinstance(response[0], dict)
        and 'error' in response[0]
    ):
        logger.error('Failed to validate database connection. Exit the MCP server')
        sys.exit(1)

    logger.success('Successfully validated database connection')

    logger.info('Starting Postgres MCP server')
    mcp.run()


if __name__ == '__main__':
    main()
