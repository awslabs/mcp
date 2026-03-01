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

"""awslabs Aurora DSQL MCP Server implementation."""

import argparse
import boto3
import httpx
import json
import psycopg
import psycopg.rows
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
    ERROR_QUERY_INJECTION_RISK,
    ERROR_READONLY_QUERY,
    ERROR_ROLLBACK_TRANSACTION,
    ERROR_TRANSACT,
    ERROR_TRANSACTION_BYPASS_ATTEMPT,
    ERROR_WRITE_QUERY_PROHIBITED,
    GET_SCHEMA_SQL,
    INTERNAL_ERROR,
    READ_ONLY_QUERY_WRITE_ERROR,
    ROLLBACK_TRANSACTION_SQL,
)
from awslabs.aurora_dsql_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
    detect_transaction_bypass_attempt,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Annotated, Any, List
from urllib.parse import urlparse


# Global variables
cluster_endpoint = None
database_user = None
region = None
read_only = False
dsql_client: Any = None
persistent_connection = None
aws_profile = None
knowledge_server = 'https://d38p8g9d7yc7ms.cloudfront.net'
knowledge_timeout = 30.0

mcp = FastMCP(
    'awslabs-aurora-dsql-mcp-server',
    instructions="""
    # Aurora DSQL MCP server.
    Provides tools to execute SQL queries on Aurora DSQL cluster.

    ## Available Tools

    ### readonly_query
    Runs a read-only SQL query.

    ### transact
    Executes one or more SQL commands in a transaction.
    - In READ-ONLY mode: Use for consistent multi-query reads. Statements are best-effort read-only validated.
    - In READ-WRITE mode: Use for any transactions including mutation. Supports all DDL and DML statements.

    ### get_schema
    Returns the schema of a table.

    ### dsql_search_documentation
    Search Aurora DSQL documentation.

    ### dsql_read_documentation
    Read specific DSQL documentation pages.

    ### dsql_recommend
    Get recommendations for DSQL best practices.
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
    if not cluster_endpoint:
        error_msg = 'Database not configured. Please configure --cluster_endpoint, --database_user, and --region.'
        await ctx.error(error_msg)
        raise Exception(error_msg)

    logger.info(f'query: {sql}')

    if not sql:
        await ctx.error(ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY)
        raise ValueError(ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY)

    # Security checks for read-only mode
    # Check for mutating keywords that shouldn't be allowed in read-only queries
    mutating_matches = detect_mutating_keywords(sql)
    if mutating_matches:
        logger.warning(
            f'readonly_query rejected due to mutating keywords: {mutating_matches}, SQL: {sql}'
        )
        await ctx.error(ERROR_WRITE_QUERY_PROHIBITED)
        raise Exception(ERROR_WRITE_QUERY_PROHIBITED)

    # Check for SQL injection risks
    injection_issues = check_sql_injection_risk(sql)
    if injection_issues:
        logger.warning(
            f'readonly_query rejected due to injection risks: {injection_issues}, SQL: {sql}'
        )
        await ctx.error(f'{ERROR_QUERY_INJECTION_RISK}: {injection_issues}')
        raise Exception(f'{ERROR_QUERY_INJECTION_RISK}: {injection_issues}')

    # Check for transaction bypass attempts (the main vulnerability)
    if detect_transaction_bypass_attempt(sql):
        logger.warning(f'readonly_query rejected due to transaction bypass attempt, SQL: {sql}')
        await ctx.error(ERROR_TRANSACTION_BYPASS_ATTEMPT)
        raise Exception(ERROR_TRANSACTION_BYPASS_ATTEMPT)

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
    description="""Execute SQL statements in a transaction against the configured Aurora DSQL cluster.

Aurora DSQL is a distributed SQL database with Postgres compatibility. This tool will automatically
insert `BEGIN` and `COMMIT` statements; you only need to provide the statements to run
within the transaction scope.

## Behavior by Mode

**READ-ONLY MODE:**
- Use this tool for read operations that require transactional consistency (point-in-time snapshots)
- Multiple SELECT queries will see data as it existed at transaction start time
- All statements are validated before execution - NO write operations allowed
- Prohibited operations: mutating queries ie. INSERT, UPDATE, DELETE, CREATE, DROP etc.
- Allowed operations: SELECT, SHOW, EXPLAIN (read-only queries only)

**READ-WRITE MODE:**
- Use this tool for any write or modify operations
- Supports all DDL statements (CREATE TABLE, CREATE INDEX, etc.)
- Supports all DML statements (INSERT, UPDATE, DELETE)
- Best practice: Use UUIDs for new tables to spread workload across nodes
- Async DDL commands (like CREATE INDEX ASYNC) return a job id
- View jobs with: SELECT * FROM sys.jobs

## When to Use Transact vs readonly_query

- Use `transact` when you need multiple queries to see consistent data (same point in time)
- Use `readonly_query` for single read queries that don't need transactional isolation
- In read-only mode, both tools validate against write operations

## Examples

Read-only mode - consistent multi-query read:
```
transact(["SELECT COUNT(*) FROM orders", "SELECT SUM(total) FROM orders"])
```

Read-write mode - create and populate table:
```
transact([
  "CREATE TABLE users (id UUID PRIMARY KEY, name TEXT)",
  "INSERT INTO users VALUES (gen_random_uuid(), 'Alice')"
])
```
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
    if not cluster_endpoint:
        error_msg = 'Database not configured. Please configure --cluster_endpoint, --database_user, and --region.'
        await ctx.error(error_msg)
        raise Exception(error_msg)

    logger.info(f'transact: {sql_list}')

    if not sql_list:
        await ctx.error(ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT)
        raise ValueError(ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT)

    # In read-only mode, validate all statements before executing
    if read_only:
        for idx, sql in enumerate(sql_list):
            # Apply the same security checks as readonly_query
            mutating_matches = detect_mutating_keywords(sql)
            if mutating_matches:
                logger.warning(
                    f'transact rejected due to mutating keywords: {mutating_matches}, SQL: {sql}'
                )
                await ctx.error(ERROR_WRITE_QUERY_PROHIBITED)
                raise Exception(ERROR_WRITE_QUERY_PROHIBITED)

            injection_issues = check_sql_injection_risk(sql)
            if injection_issues:
                logger.warning(
                    f'transact rejected due to injection risks: {injection_issues}, SQL: {sql}'
                )
                await ctx.error(f'{ERROR_QUERY_INJECTION_RISK}: {injection_issues}')
                raise Exception(f'{ERROR_QUERY_INJECTION_RISK}: {injection_issues}')

            if detect_transaction_bypass_attempt(sql):
                logger.warning(f'transact rejected due to transaction bypass attempt, SQL: {sql}')
                await ctx.error(ERROR_TRANSACTION_BYPASS_ATTEMPT)
                raise Exception(ERROR_TRANSACTION_BYPASS_ATTEMPT)

    try:
        conn = await get_connection(ctx)

        # Use read-only transaction in read-only mode, regular transaction otherwise
        begin_sql = BEGIN_READ_ONLY_TRANSACTION_SQL if read_only else BEGIN_TRANSACTION_SQL

        try:
            await execute_query(ctx, conn, begin_sql)
        except Exception as e:
            error_msg = ERROR_BEGIN_READ_ONLY_TRANSACTION if read_only else ERROR_BEGIN_TRANSACTION
            logger.error(f'{error_msg}: {str(e)}')
            await ctx.error(f'{error_msg}: {str(e)}')
            raise Exception(f'{error_msg}: {str(e)}')

        try:
            rows = []
            for query in sql_list:
                rows = await execute_query(ctx, conn, query)
            await execute_query(ctx, conn, COMMIT_TRANSACTION_SQL)
            return rows
        except psycopg.errors.ReadOnlySqlTransaction:
            await ctx.error(READ_ONLY_QUERY_WRITE_ERROR)
            raise Exception(READ_ONLY_QUERY_WRITE_ERROR)
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
    if not cluster_endpoint:
        error_msg = 'Database not configured. Please configure --cluster_endpoint, --database_user, and --region.'
        await ctx.error(error_msg)
        raise Exception(error_msg)

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


@mcp.tool(
    name='dsql_search_documentation',
    description='Search Aurora DSQL documentation',
)
async def dsql_search_documentation(
    search_phrase: Annotated[str, Field(description='Search phrase to use')],
    limit: Annotated[int | None, Field(description='Maximum number of results to return')] = None,
    ctx: Context | None = None,
) -> dict:
    """Search Aurora DSQL documentation.

    Args:
        search_phrase: Search phrase to use
        limit: Maximum number of results to return (optional)
        ctx: MCP context for logging and state management

    Returns:
        Search results from the remote knowledge server
    """
    params: dict[str, Any] = {'search_phrase': search_phrase}
    if limit is not None:
        params['limit'] = limit
    return await _proxy_to_knowledge_server('dsql_search_documentation', params, ctx)


@mcp.tool(
    name='dsql_read_documentation',
    description='Read specific DSQL documentation pages',
)
async def dsql_read_documentation(
    url: Annotated[str, Field(description='Specific url to read')],
    start_index: Annotated[int | None, Field(description='Starting character index')] = None,
    max_length: Annotated[
        int | None, Field(description='Maximum number of characters to return')
    ] = None,
    ctx: Context | None = None,
) -> dict:
    """Read specific DSQL documentation pages.

    Args:
        url: URL of the documentation page to read
        start_index: Starting character index (optional)
        max_length: Maximum number of characters to return (optional)
        ctx: MCP context for logging and state management

    Returns:
        Documentation content from the remote knowledge server
    """
    params: dict[str, Any] = {'url': url}
    if start_index is not None:
        params['start_index'] = start_index
    if max_length is not None:
        params['max_length'] = max_length
    return await _proxy_to_knowledge_server('dsql_read_documentation', params, ctx)


@mcp.tool(
    name='dsql_recommend',
    description='Get recommendations for DSQL best practices',
)
async def dsql_recommend(
    url: Annotated[
        str,
        Field(description='URL of the documentation page to get recommendations for'),
    ],
    ctx: Context,
) -> dict:
    """Get recommendations for DSQL best practices.

    Args:
        url: URL of the documentation page to get recommendations for
        ctx: MCP context for logging and state management

    Returns:
        Recommendations from the remote knowledge server
    """
    return await _proxy_to_knowledge_server('dsql_recommend', {'url': url}, ctx)


async def _proxy_to_knowledge_server(
    method: str, params: dict[str, Any], ctx: Context | None
) -> dict:
    """Proxy a request to the remote knowledge MCP server.

    Args:
        method: The MCP tool method name to call
        params: Parameters to pass to the remote tool
        ctx: MCP context for logging and state management

    Returns:
        Response from the remote server

    Raises:
        Exception: If the remote server is unavailable or returns an error
    """
    logger.info(f'Proxying to knowledge server: {method} with params: {params}')

    payload = {
        'jsonrpc': '2.0',
        'method': 'tools/call',
        'params': {
            'name': method,
            'arguments': params,
        },
        'id': 1,
    }

    try:
        async with httpx.AsyncClient(timeout=knowledge_timeout) as client:
            response = await client.post(knowledge_server, json=payload)
            response.raise_for_status()
            result = response.json()

            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error from knowledge server')
                if ctx:
                    await ctx.error(error_msg)
                raise Exception(error_msg)

            res = result.get('result', {})
            if not res:
                content = result.get('content', [])
                if content and isinstance(content, list) and content[0].get('type') == 'text':
                    return json.loads(content[0]['text'])
                return {'content': content}
            return res

    except httpx.HTTPError as e:
        error_msg = 'The DSQL knowledge server is currently unavailable. Please try again later.'
        logger.error(f'Knowledge server error: {e}')
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


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
        return dsql_client.generate_db_connect_admin_auth_token(cluster_endpoint, region)
    else:
        return dsql_client.generate_db_connect_auth_token(cluster_endpoint, region)


async def get_connection(ctx):  # noqa: D103
    """Get a connection to the database, creating one if needed or reusing the existing one.

    Args:
        ctx: MCP context for logging and state management

    Returns:
        A database connection
    """
    global persistent_connection

    # Return the existing connection without health check
    # The caller will handle reconnection if needed
    if persistent_connection is not None:
        return persistent_connection

    # Create a new connection
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


async def execute_query(ctx, conn_to_use, query: str, params=None) -> List[dict]:
    """Execute a SQL query against the database.

    Args:
        ctx: MCP context for error handling
        conn_to_use: Database connection to use, or None to get a new one
        query: SQL query string to execute
        params: Optional query parameters

    Returns:
        List of result rows as dictionaries
    """
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
    except (psycopg.OperationalError, psycopg.InterfaceError) as e:
        # Connection issue - reconnect and retry
        logger.warning(f'Connection error, reconnecting: {e}')
        global persistent_connection
        try:
            if persistent_connection:
                await persistent_connection.close()
        except Exception:
            pass  # Ignore errors when closing an already broken connection
        persistent_connection = None

        # Get a fresh connection and retry
        conn = await get_connection(ctx)
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
    parser.add_argument(
        '--cluster_endpoint',
        help='Endpoint for your Aurora DSQL cluster',
    )
    parser.add_argument('--database_user', help='Database username')
    parser.add_argument('--region')
    parser.add_argument(
        '--allow-writes',
        action='store_true',
        help='Allow use of tools that may perform write operations such as transact',
    )
    parser.add_argument(
        '--profile',
        help='AWS profile to use for credentials',
    )
    parser.add_argument(
        '--knowledge-server',
        default='https://xmfe3hc3pk.execute-api.us-east-2.amazonaws.com',
        help='Remote MCP server endpoint for DSQL knowledge tools',
    )
    parser.add_argument(
        '--knowledge-timeout',
        type=float,
        default=30.0,
        help='Timeout in seconds for knowledge server requests (default: 30.0)',
    )
    args = parser.parse_args()

    # Validate knowledge server URL
    try:
        parsed_url = urlparse(args.knowledge_server)
        if parsed_url.scheme != 'https':
            logger.error(
                f'Knowledge server URL must use HTTPS protocol. Got: {args.knowledge_server}. '
                f'Example: https://xmfe3hc3pk.execute-api.us-east-2.amazonaws.com'
            )
            sys.exit(1)
        if not parsed_url.netloc:
            logger.error(
                f'Knowledge server URL is malformed. Got: {args.knowledge_server}. '
                f'Example: https://xmfe3hc3pk.execute-api.us-east-2.amazonaws.com'
            )
            sys.exit(1)
    except Exception as e:
        logger.error(f'Invalid knowledge server URL: {e}')
        sys.exit(1)

    # Validate timeout value
    if args.knowledge_timeout <= 0:
        logger.error(
            f'Knowledge timeout must be positive. Got: {args.knowledge_timeout}. '
            f'Example: --knowledge-timeout 30.0'
        )
        sys.exit(1)

    global cluster_endpoint
    cluster_endpoint = args.cluster_endpoint

    global region
    region = args.region

    global database_user
    database_user = args.database_user

    global read_only
    read_only = not args.allow_writes

    global aws_profile
    aws_profile = args.profile

    global knowledge_server
    knowledge_server = args.knowledge_server

    global knowledge_timeout
    knowledge_timeout = args.knowledge_timeout

    # Check if cluster is configured
    if not cluster_endpoint or not database_user or not region:
        logger.warning(
            'Aurora DSQL MCP server starting without cluster configuration. '
            'Database tools will not be available. '
            'Please configure --cluster_endpoint, --database_user, and --region to enable database operations.'
        )
        logger.info('Starting Aurora DSQL MCP server (documentation tools only)')
        mcp.run()
        return

    mode_description = 'READ-WRITE' if args.allow_writes else 'READ-ONLY'
    logger.info(
        'Aurora DSQL MCP init with CLUSTER_ENDPOINT:{}, REGION: {}, DATABASE_USER:{}, MODE:{}, AWS_PROFILE:{}, KNOWLEDGE_SERVER:{}, KNOWLEDGE_TIMEOUT:{}',
        cluster_endpoint,
        region,
        database_user,
        mode_description,
        aws_profile or 'default',
        knowledge_server,
        knowledge_timeout,
    )

    global dsql_client
    session = boto3.Session(profile_name=aws_profile) if aws_profile else boto3.Session()
    dsql_client = session.client('dsql', region_name=region)

    logger.info('Starting Aurora DSQL MCP server')
    mcp.run()


if __name__ == '__main__':
    main()
