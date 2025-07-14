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


class DBConnection:
    """Class that wraps DB connection client by RDS API or direct PostgreSQL connection."""

    def __init__(
        self,
        auth_mode='secrets-manager',
        cluster_arn=None,
        secret_arn=None,
        db_user=None,
        db_host=None,
        db_port=5432,
        database=None,
        region=None,
        readonly=False,
        is_test=False,
    ):
        """Initialize a new DB connection.

        Args:
            auth_mode: Authentication mode ('secrets-manager' or 'iam-db-auth')
            cluster_arn: The ARN of the RDS cluster (secrets-manager mode)
            secret_arn: The ARN of the secret containing credentials (secrets-manager mode)
            db_user: Database username (iam-db-auth mode)
            db_host: Database host/endpoint (iam-db-auth mode)
            db_port: Database port (iam-db-auth mode)
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only
            is_test: Whether this is a test connection
        """
        self.auth_mode = auth_mode
        self.cluster_arn = cluster_arn
        self.secret_arn = secret_arn
        self.db_user = db_user
        self.db_host = db_host
        self.db_port = db_port
        self.database = database
        self.region = region
        self.readonly = readonly

        if not is_test:
            if auth_mode == 'secrets-manager':
                self.data_client = boto3.client('rds-data', region_name=region)
            else:  # iam-db-auth
                self.rds_client = boto3.client('rds', region_name=region)

    @property
    def readonly_query(self):
        """Get whether this connection is read-only.

        Returns:
            bool: True if the connection is read-only, False otherwise
        """
        return self.readonly

    async def generate_auth_token(self):
        """Generate IAM authentication token for database connection.

        Returns:
            str: Authentication token valid for 15 minutes
        """
        return await asyncio.to_thread(
            self.rds_client.generate_db_auth_token,
            DBHostname=self.db_host,
            Port=self.db_port,
            DBUsername=self.db_user,
            Region=self.region,
        )

    async def get_direct_connection(self):
        """Get a direct PostgreSQL connection using IAM authentication.

        Returns:
            psycopg2 connection object
        """
        import psycopg2

        auth_token = await self.generate_auth_token()

        connection_params = {
            'host': self.db_host,
            'port': self.db_port,
            'database': self.database,
            'user': self.db_user,
            'password': auth_token,
            'sslmode': 'require',
        }

        return await asyncio.to_thread(psycopg2.connect, **connection_params)


class DBConnectionSingleton:
    """Manages a single DBConnection instance across the application.

    This singleton ensures that only one DBConnection is created and reused.
    """

    _instance = None

    def __init__(
        self,
        auth_mode='secrets-manager',
        cluster_arn=None,
        secret_arn=None,
        db_user=None,
        db_host=None,
        db_port=5432,
        database=None,
        region=None,
        readonly=False,
        is_test=False,
    ):
        """Initialize a new DB connection singleton.

        Args:
            auth_mode: Authentication mode ('secrets-manager' or 'iam-db-auth')
            cluster_arn: The ARN of the RDS cluster (secrets-manager mode)
            secret_arn: The ARN of the secret containing credentials (secrets-manager mode)
            db_user: Database username (iam-db-auth mode)
            db_host: Database host/endpoint (iam-db-auth mode)
            db_port: Database port (iam-db-auth mode)
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only
            is_test: Whether this is a test connection
        """
        if auth_mode == 'secrets-manager':
            if not all([cluster_arn, secret_arn, database, region]):
                raise ValueError(
                    'Missing required connection parameters for secrets-manager mode. '
                    'Please provide cluster_arn, secret_arn, database, and region.'
                )
        elif auth_mode == 'iam-db-auth':
            if not all([db_user, db_host, database, region]):
                raise ValueError(
                    'Missing required connection parameters for iam-db-auth mode. '
                    'Please provide db_user, db_host, database, and region.'
                )

        self._db_connection = DBConnection(
            auth_mode=auth_mode,
            cluster_arn=cluster_arn,
            secret_arn=secret_arn,
            db_user=db_user,
            db_host=db_host,
            db_port=db_port,
            database=database,
            region=region,
            readonly=readonly,
            is_test=is_test,
        )

    @classmethod
    def initialize(
        cls,
        auth_mode='secrets-manager',
        cluster_arn=None,
        secret_arn=None,
        db_user=None,
        db_host=None,
        db_port=5432,
        database=None,
        region=None,
        readonly=False,
        is_test=False,
    ):
        """Initialize the singleton instance if it doesn't exist.

        Args:
            auth_mode: Authentication mode ('secrets-manager' or 'iam-db-auth')
            cluster_arn: The ARN of the RDS cluster (secrets-manager mode)
            secret_arn: The ARN of the secret containing credentials (secrets-manager mode)
            db_user: Database username (iam-db-auth mode)
            db_host: Database host/endpoint (iam-db-auth mode)
            db_port: Database port (iam-db-auth mode)
            database: The name of the database to connect to
            region: The AWS region where the RDS instance is located
            readonly: Whether the connection should be read-only
            is_test: Whether this is a test connection
        """
        if cls._instance is None:
            cls._instance = cls(
                auth_mode=auth_mode,
                cluster_arn=cluster_arn,
                secret_arn=secret_arn,
                db_user=db_user,
                db_host=db_host,
                db_port=db_port,
                database=database,
                region=region,
                readonly=readonly,
                is_test=is_test,
            )

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
            a.attrelid = to_regclass(:table_name)
            AND a.attnum > 0
            AND NOT a.attisdropped
        ORDER BY a.attnum
    """

    params = [{'name': 'table_name', 'value': {'stringValue': table_name}}]

    return await run_query(sql=sql, ctx=ctx, query_parameters=params)


@mcp.tool(
    name='run_query_iam',
    description='Run SQL query using direct PostgreSQL connection with IAM authentication',
)
async def run_query_iam(
    sql: Annotated[str, Field(description='The SQL query to run with %(param)s syntax')],
    ctx: Context,
    db_connection=None,
    parameters: Annotated[
        Optional[Dict[str, Any]], Field(description='Native Python dict parameters')
    ] = None,
) -> list[dict]:  # type: ignore
    """Run a SQL query using direct PostgreSQL connection with IAM authentication.

    Args:
        sql: The sql statement to run with %(param)s syntax
        ctx: MCP context for logging and state management
        db_connection: DB connection object passed by unit test. It should be None if called by MCP server.
        parameters: Native Python dict parameters

    Returns:
        List of dictionary that contains query response rows
    """
    global client_error_code_key
    global unexpected_error_key
    global write_query_prohibited_key

    if db_connection is None:
        db_connection = DBConnectionSingleton.get().db_connection

    # Ensure we're in IAM auth mode
    if db_connection.auth_mode != 'iam-db-auth':
        await ctx.error('run_query_iam can only be used with IAM database authentication mode')
        return [{'error': 'IAM authentication mode required'}]

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
        logger.info(f'run_query_iam: readonly:{db_connection.readonly_query}, SQL:{sql}')

        if db_connection.readonly_query:
            response = await execute_direct_readonly_query(db_connection, sql, parameters)
        else:
            response = await execute_direct_query(db_connection, sql, parameters)

        logger.success('run_query_iam successfully executed query:{}', sql)
        return response
    except Exception as e:
        logger.exception('run_query_iam unexpected error')
        error_details = f'{type(e).__name__}: {str(e)}'
        await ctx.error(str({'message': error_details}))
        return [{'error': 'run_query_iam unexpected error'}]


@mcp.tool(
    name='get_table_schema_iam',
    description='Fetch table columns and comments from Postgres using direct connection with IAM auth',
)
async def get_table_schema_iam(
    table_name: Annotated[str, Field(description='name of the table')], ctx: Context
) -> list[dict]:
    """Get a table's schema information using direct PostgreSQL connection with IAM auth.

    Args:
        table_name: name of the table
        ctx: MCP context for logging and state management

    Returns:
        List of dictionary that contains query response rows
    """
    logger.info(f'get_table_schema_iam: {table_name}')

    sql = """
        SELECT
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
            col_description(a.attrelid, a.attnum) AS column_comment
        FROM
            pg_attribute a
        WHERE
            a.attrelid = to_regclass(%(table_name)s)
            AND a.attnum > 0
            AND NOT a.attisdropped
        ORDER BY a.attnum
    """

    params = {'table_name': table_name}

    return await run_query_iam(sql=sql, ctx=ctx, parameters=params)


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


async def execute_direct_query(
    db_connection: DBConnection, sql: str, parameters: Optional[Dict[str, Any]] = None
) -> list[dict]:
    """Execute query using direct PostgreSQL connection with IAM auth.

    Args:
        db_connection: connection object
        sql: SQL query with %(param)s syntax
        parameters: Native Python dict parameters

    Returns:
        List of simple dictionaries with column names as keys
    """
    conn = None
    try:
        conn = await db_connection.get_direct_connection()
        cursor = conn.cursor()

        # Execute query with native parameters
        cursor.execute(sql, parameters)

        # Fetch results and column metadata
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            # Convert directly to simple dictionaries
            records = []
            for row in rows:
                row_dict = {columns[i]: value for i, value in enumerate(row)}
                records.append(row_dict)

            return records
        else:
            # No results (e.g., INSERT/UPDATE/DELETE)
            return []

    finally:
        if conn:
            await asyncio.to_thread(conn.close)


async def execute_direct_readonly_query(
    db_connection: DBConnection, sql: str, parameters: Optional[Dict[str, Any]] = None
) -> list[dict]:
    """Execute readonly query using direct PostgreSQL connection with IAM auth.

    Args:
        db_connection: connection object
        sql: SQL query with %(param)s syntax
        parameters: Native Python dict parameters

    Returns:
        List of simple dictionaries with column names as keys
    """
    conn = None
    try:
        conn = await db_connection.get_direct_connection()
        conn.set_session(readonly=True)
        cursor = conn.cursor()

        # Execute query with native parameters
        cursor.execute(sql, parameters)

        # Fetch results and column metadata
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            # Convert directly to simple dictionaries
            records = []
            for row in rows:
                row_dict = {columns[i]: value for i, value in enumerate(row)}
                records.append(row_dict)

            return records
        else:
            # No results (e.g., INSERT/UPDATE/DELETE)
            return []

    finally:
        if conn:
            await asyncio.to_thread(conn.close)


def main():
    """Main entry point for the MCP server application."""
    global client_error_code_key

    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for postgres'
    )

    # Authentication mode
    parser.add_argument(
        '--auth-mode',
        choices=['secrets-manager', 'iam-db-auth'],
        default='secrets-manager',
        help='Authentication mode (default: secrets-manager)',
    )

    # Secrets Manager arguments (backward compatibility)
    parser.add_argument('--resource_arn', help='ARN of the RDS cluster (secrets-manager mode)')
    parser.add_argument(
        '--secret_arn',
        help='ARN of the Secrets Manager secret for database credentials (secrets-manager mode)',
    )

    # IAM Database Authentication arguments
    parser.add_argument('--db-user', help='Database username (iam-db-auth mode)')
    parser.add_argument('--db-host', help='Database host/endpoint (iam-db-auth mode)')
    parser.add_argument('--db-port', type=int, default=5432, help='Database port (default: 5432)')

    # Common arguments
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument(
        '--readonly', required=True, help='Enforce NL to SQL to only allow readonly sql statement'
    )

    args = parser.parse_args()

    # Validate arguments based on authentication mode
    if args.auth_mode == 'secrets-manager':
        if not args.resource_arn or not args.secret_arn:
            parser.error('secrets-manager mode requires --resource_arn and --secret_arn arguments')
        logger.info(
            'Postgres MCP init with AUTH_MODE:{}, CLUSTER_ARN:{}, SECRET_ARN:{}, REGION:{}, DATABASE:{}, READONLY:{}',
            args.auth_mode,
            args.resource_arn,
            args.secret_arn,
            args.region,
            args.database,
            args.readonly,
        )
    elif args.auth_mode == 'iam-db-auth':
        if not args.db_user or not args.db_host:
            parser.error('iam-db-auth mode requires --db-user and --db-host arguments')
        logger.info(
            'Postgres MCP init with AUTH_MODE:{}, DB_USER:{}, DB_HOST:{}, DB_PORT:{}, REGION:{}, DATABASE:{}, READONLY:{}',
            args.auth_mode,
            args.db_user,
            args.db_host,
            args.db_port,
            args.region,
            args.database,
            args.readonly,
        )

    try:
        DBConnectionSingleton.initialize(
            auth_mode=args.auth_mode,
            cluster_arn=getattr(args, 'resource_arn', None),
            secret_arn=getattr(args, 'secret_arn', None),
            db_user=getattr(args, 'db_user', None),
            db_host=getattr(args, 'db_host', None),
            db_port=getattr(args, 'db_port', 5432),
            database=args.database,
            region=args.region,
            readonly=args.readonly,
        )
    except (BotoCoreError, ValueError) as e:
        logger.exception(f'Failed to initialize DB connection: {e}')
        sys.exit(1)

    # Test connection based on authentication mode
    ctx = DummyCtx()
    if args.auth_mode == 'secrets-manager':
        test_response = asyncio.run(run_query('SELECT 1', ctx))
        test_tool = 'run_query'
    else:  # iam-db-auth
        test_response = asyncio.run(run_query_iam('SELECT 1', ctx))
        test_tool = 'run_query_iam'

    if (
        isinstance(test_response, list)
        and len(test_response) == 1
        and isinstance(test_response[0], dict)
        and 'error' in test_response[0]
    ):
        logger.error(
            f'Failed to validate {args.auth_mode} db connection to Postgres using {test_tool}. Exit the MCP server'
        )
        sys.exit(1)

    logger.success(
        f'Successfully validated {args.auth_mode} db connection to Postgres using {test_tool}'
    )

    logger.info('Starting Postgres MCP server')
    mcp.run()


if __name__ == '__main__':
    main()
