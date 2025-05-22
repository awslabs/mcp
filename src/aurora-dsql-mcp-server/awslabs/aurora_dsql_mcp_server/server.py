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

"""awslabs Aurora DSQL MCP Server implementation."""

import argparse
import asyncio
import boto3
import psycopg
import sys
from awslabs.aurora_dsql_mcp_server.consts import (
    BEGIN_READ_ONLY_TRANSACTION_SQL,
    BEGIN_TRANSACTION_SQL,
    COMMIT_TRANSACTION_SQL,
    DSQL_DB_NAME,
    DSQL_DB_PORT,
    DSQL_MCP_SERVER_APPLICATION_NAME,
    ERROR_BEGIN_READ_ONLY_TRANSACTION,
    ERROR_BEGIN_TRANSACTION,
    ERROR_CREATE_CONNECTION,
    ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT,
    ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY,
    ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA,
    ERROR_EXECUTE_QUERY,
    ERROR_GET_SCHEMA,
    ERROR_READONLY_QUERY,
    ERROR_ROLLBACK_TRANSACTION,
    ERROR_TRANSACT,
    ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE,
    GET_SCHEMA_SQL,
    INTERNAL_ERROR,
    READ_ONLY_QUERY_WRITE_ERROR,
    ROLLBACK_TRANSACTION_SQL,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Annotated, List


# Global variables
cluster_endpoint = None
database_user = None
region = None
read_only = False
dsql_client = None
persistent_connection = None

mcp = FastMCP(
    'awslabs-aurora-dsql-mcp-server',
    instructions="""
    # Aurora DSQL MCP server.
    Provides tools to execute SQL queries on Aurora DSQL cluster'

    ## Available Tools

    ### readonly_query
    Runs a read-only SQL query.

    ### transact
    Executes one or more SQL commands in a transaction.

    ### get_schema
    Returns the schema of a table.
    """,
    dependencies=[
        'loguru',
    ],
)


@mcp.tool(
    name='readonly_query',
    description="""Run a read-only SQL query against the configured Aurora DSQL cluster.

Aurora DSQL is distributed SQL database with Postgres compatibility. The following table
summarizes `SELECT` functionality that is expected to work. Items not in this table may
also be supported, as this is a point in time snapshot.
| Primary clause                  | Supported clauses     |
|---------------------------------|-----------------------|
| FROM                            |                       |
| GROUP BY                        | ALL, DISTINCT         |
| ORDER BY                        | ASC, DESC, NULLS      |
| LIMIT                           |                       |
| DISTINCT                        |                       |
| HAVING                          |                       |
| USING                           |                       |
| WITH (common table expressions) |                       |
| INNER JOIN                      | ON                    |
| OUTER JOIN                      | LEFT, RIGHT, FULL, ON |
| CROSS JOIN                      | ON                    |
| UNION                           | ALL                   |
| INTERSECT                       | ALL                   |
| EXCEPT                          | ALL                   |
| OVER                            | RANK (), PARTITION BY |
| FOR UPDATE                      |                       |
""",
)
async def readonly_query(
    sql: Annotated[str, Field(description='The SQL query to run')], ctx: Context
) -> List[dict]:
    """Runs a read-only SQL query.

    Args:
        sql: The sql statement to run
        ctx: MCP context for logging and state management

    Returns:
        List of rows. Each row is a dictionary with column name as the key and column value as the value.
        Empty list if the SQL execution did not return any results
    """
    logger.info(f'query: {sql}')

    if not sql:
        await ctx.error(ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY)
        raise ValueError(ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY)

    try:
        conn = await get_connection(ctx)

        try:
            await execute_query(ctx, conn, BEGIN_READ_ONLY_TRANSACTION_SQL)
        except Exception as e:
            logger.error(f'{ERROR_BEGIN_READ_ONLY_TRANSACTION}: {str(e)}')
            await ctx.error(INTERNAL_ERROR)
            raise Exception(INTERNAL_ERROR)

        try:
            rows = await execute_query(ctx, conn, sql)
            await execute_query(ctx, conn, COMMIT_TRANSACTION_SQL)
            return rows
        except psycopg.errors.ReadOnlySqlTransaction:
            await ctx.error(READ_ONLY_QUERY_WRITE_ERROR)
            raise Exception(READ_ONLY_QUERY_WRITE_ERROR)
        except Exception as e:
            raise e
        finally:
            try:
                await execute_query(ctx, conn, ROLLBACK_TRANSACTION_SQL)
            except Exception as e:
                logger.error(f'{ERROR_ROLLBACK_TRANSACTION}: {str(e)}')

    except Exception as e:
        await ctx.error(f'{ERROR_READONLY_QUERY}: {str(e)}')
        raise Exception(f'{ERROR_READONLY_QUERY}: {str(e)}')


@mcp.tool(
    name='transact',
    description="""Write or modify data using SQL, in a transaction against the configured Aurora DSQL cluster.

Aurora DSQL is a distributed SQL database with Postgres compatibility. This tool will automatically
insert `BEGIN` and `COMMIT` statements; you only need to provide the statements to run
within the transaction scope.

In addition to the `SELECT` functionality described on the `readonly_query` tool, DSQL supports
common DDL statements such as `CREATE TABLE`. Note that it is a best practice to use UUIDs
for new tables in DSQL as this will spread your workload out over as many nodes as possible.

Some DDL commands are async (like `CREATE INDEX ASYNC`), and return a job id. Jobs can
be viewed by running `SELECT * FROM sys.jobs`.
""",
)
async def transact(
    sql_list: Annotated[
        List[str],
        Field(description='List of one or more SQL statements to execute in a transaction'),
    ],
    ctx: Context,
) -> List[dict]:
    """Executes one or more SQL commands in a transaction.

    Args:
        sql_list: List of SQL statements to run
        ctx: MCP context for logging and state management

    Returns:
        List of rows. Each row is a dictionary with column name as the key and column value as
        the value. Empty list if the execution of the last SQL did not return any results
    """
    logger.info(f'transact: {sql_list}')

    if read_only:
        await ctx.error(ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE)
        raise Exception(ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE)

    if not sql_list:
        await ctx.error(ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT)
        raise ValueError(ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT)

    try:
        conn = await get_connection(ctx)

        try:
            await execute_query(ctx, conn, BEGIN_TRANSACTION_SQL)
        except Exception as e:
            logger.error(f'{ERROR_BEGIN_TRANSACTION}: {str(e)}')
            await ctx.error(f'{ERROR_BEGIN_TRANSACTION}: {str(e)}')
            raise Exception(f'{ERROR_BEGIN_TRANSACTION}: {str(e)}')

        try:
            rows = []
            for query in sql_list:
                rows = await execute_query(ctx, conn, query)
            await execute_query(ctx, conn, COMMIT_TRANSACTION_SQL)
            return rows
        except Exception as e:
            try:
                await execute_query(ctx, conn, ROLLBACK_TRANSACTION_SQL)
            except Exception as re:
                logger.error(f'{ERROR_ROLLBACK_TRANSACTION}: {str(re)}')
            raise e

    except Exception as e:
        await ctx.error(f'{ERROR_TRANSACT}: {str(e)}')
        raise Exception(f'{ERROR_TRANSACT}: {str(e)}')


@mcp.tool(name='get_schema', description='Get the schema of the given table')
async def get_schema(
    table_name: Annotated[str, Field(description='name of the table')], ctx: Context
) -> List[dict]:
    """Returns the schema of a table.

    Args:
        table_name: Name of the table whose schema will be returned
        ctx: MCP context for logging and state management

    Returns:
        List of rows. Each row contains column name and type information for a column in the
        table provided in a dictionary form. Empty list is returned if table is not found.
    """
    logger.info(f'get_schema: {table_name}')

    if not table_name:
        await ctx.error(ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA)
        raise ValueError(ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA)

    try:
        conn = await get_connection(ctx)
        return await execute_query(ctx, conn, GET_SCHEMA_SQL, [table_name])
    except Exception as e:
        await ctx.error(f'{ERROR_GET_SCHEMA}: {str(e)}')
        raise Exception(f'{ERROR_GET_SCHEMA}: {str(e)}')


class NoOpCtx:
    """A No-op context class for error handling in MCP tools."""

    async def error(self, message):
        """Do nothing.

        Args:
            message: The error message
        """


async def get_password_token():  # noqa: D103
    # Generate a fresh password token for each connection, to ensure the token is not expired
    # when the connection is established
    if database_user == 'admin':
        return dsql_client.generate_db_connect_admin_auth_token(cluster_endpoint, region)  # pyright: ignore[reportOptionalMemberAccess]
    else:
        return dsql_client.generate_db_connect_auth_token(cluster_endpoint, region)  # pyright: ignore[reportOptionalMemberAccess]


async def get_connection(ctx):  # noqa: D103
    """Get a connection to the database, creating one if needed or reusing the existing one.

    Args:
        ctx: MCP context for logging and state management

    Returns:
        A database connection
    """
    global persistent_connection

    # Check if we have a valid connection
    if persistent_connection is not None:
        try:
            # Test if the connection is still valid
            async with persistent_connection.cursor() as cur:
                await cur.execute('SELECT 1')
                await cur.fetchone()
            logger.debug('Reusing existing database connection')
            return persistent_connection
        except Exception as e:
            logger.warning(f'Existing connection is no longer valid, creating a new one: {e}')
            try:
                await persistent_connection.close()
            except Exception:
                pass  # Ignore errors when closing an already broken connection
            persistent_connection = None

    password_token = await get_password_token()

    conn_params = {
        'dbname': DSQL_DB_NAME,
        'user': database_user,
        'host': cluster_endpoint,
        'port': DSQL_DB_PORT,
        'password': password_token,
        'application_name': DSQL_MCP_SERVER_APPLICATION_NAME,
        'sslmode': 'require',
    }

    logger.info(f'Creating new connection to {cluster_endpoint} as user {database_user}')
    try:
        persistent_connection = await psycopg.AsyncConnection.connect(
            **conn_params, autocommit=True
        )
        return persistent_connection
    except Exception as e:
        logger.error(f'{ERROR_CREATE_CONNECTION} : {e}')
        await ctx.error(f'{ERROR_CREATE_CONNECTION} : {e}')
        raise e


async def execute_query(ctx, conn_to_use, query: str, params=None) -> List[dict]:  # noqa: D103
    if conn_to_use is None:
        conn = await get_connection(ctx)
    else:
        conn = conn_to_use

    try:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:  # pyright: ignore[reportAttributeAccessIssue]
            await cur.execute(query, params)  # pyright: ignore[reportArgumentType]
            if cur.rownumber is None:
                return []
            else:
                return await cur.fetchall()
    except Exception as e:
        logger.error(f'{ERROR_EXECUTE_QUERY} : {e}')
        await ctx.error(f'{ERROR_EXECUTE_QUERY} : {e}')
        raise e


def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for Aurora DSQL'
    )
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    parser.add_argument(
        '--cluster_endpoint', required=True, help='Endpoint for your Aurora DSQL cluster'
    )
    parser.add_argument('--database_user', required=True, help='Database username')
    parser.add_argument('--region', required=True)
    parser.add_argument(
        '--allow-writes',
        action='store_true',
        help='Allow use of tools that may perform write operations such as transact',
    )
    args = parser.parse_args()

    global cluster_endpoint
    cluster_endpoint = args.cluster_endpoint

    global region
    region = args.region

    global database_user
    database_user = args.database_user

    global read_only
    read_only = not args.allow_writes

    logger.info(
        'Aurora DSQL MCP init with CLUSTER_ENDPOINT:{}, REGION: {}, DATABASE_USER:{}, ALLOW-WRITES:{}',
        cluster_endpoint,
        region,
        database_user,
        args.allow_writes,
    )

    global dsql_client
    dsql_client = boto3.client('dsql', region_name=region)

    try:
        logger.info('Validating connection to cluster')
        ctx = NoOpCtx()
        asyncio.run(execute_query(ctx, None, 'SELECT 1'))
    except Exception as e:
        logger.error(
            f'Failed to create and validate db connection to Aurora DSQL. Exit the MCP server. error: {e}'
        )
        sys.exit(1)

    logger.success('Successfully validated connection to Aurora DSQL Cluster')

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        logger.info('Starting Aurora DSQL MCP server')
        mcp.run()


if __name__ == '__main__':
    main()
