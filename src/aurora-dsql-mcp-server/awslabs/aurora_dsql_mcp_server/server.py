import argparse
import asyncio
import sys
from typing import Annotated, List, Optional, Dict

import boto3
import psycopg
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, validator

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
    ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE,
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

# Pydantic model for AWS credentials + region
class AWSConfig(BaseModel):
    aws_access_key_id: str = Field(..., description="AWS access key ID")
    aws_secret_access_key: str = Field(..., description="AWS secret access key")
    region_name: str = Field(..., description="AWS region, e.g. 'us-east-1'")

    @validator("region_name")
    def validate_region(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("region_name must be non-empty")
        return v

# Global connection state
cluster_endpoint: str = ''
database_user: str = ''
read_only: bool = True
persistent_connection: Optional[psycopg.AsyncConnection] = None

# ----------------------------------------------------------------------------
# MCP server definition
# ----------------------------------------------------------------------------
mcp = FastMCP(
    'awslabs-aurora-dsql-mcp-server',
    instructions="""
    # Aurora DSQL MCP server.
    Provides tools to execute SQL queries on Aurora DSQL cluster.

    ## Available Tools

    ### readonly_query
    Runs a read-only SQL query.

    ### transact
    Executes SQL commands in a transaction.

    ### get_schema
    Returns the schema of a table.
    """,
    dependencies=['loguru'],
)

# ----------------------------------------------------------------------------
# AWS DSQL client helper
# ----------------------------------------------------------------------------

def create_dsql_client(aws_config: AWSConfig):
    session = boto3.Session(
        aws_access_key_id=aws_config.aws_access_key_id,
        aws_secret_access_key=aws_config.aws_secret_access_key,
        region_name=aws_config.region_name,
    )
    return session.client('dsql')

# ----------------------------------------------------------------------------
# Tool implementations
# ----------------------------------------------------------------------------
@mcp.tool(
    name='readonly_query',
    description='Run a read-only SQL query against Aurora DSQL cluster.',
)
async def readonly_query(
    sql: Annotated[str, Field(description='The SQL query to run')],
    aws_config: AWSConfig,
    ctx: Context,
) -> List[Dict]:
    logger.info(f'query: {sql}')

    if not sql:
        await ctx.error(ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY)
        raise ValueError(ERROR_EMPTY_SQL_PASSED_TO_READONLY_QUERY)

    # Security checks
    if detect_mutating_keywords(sql):
        await ctx.error(ERROR_WRITE_QUERY_PROHIBITED)
        raise Exception(ERROR_WRITE_QUERY_PROHIBITED)
    if check_sql_injection_risk(sql):
        await ctx.error(ERROR_QUERY_INJECTION_RISK)
        raise Exception(ERROR_QUERY_INJECTION_RISK)
    if detect_transaction_bypass_attempt(sql):
        logger.warning(f'readonly_query rejected due to transaction bypass attempt, SQL: {sql}')
        await ctx.error(ERROR_TRANSACTION_BYPASS_ATTEMPT)
        raise Exception(ERROR_TRANSACTION_BYPASS_ATTEMPT)

    try:
        conn = await get_connection(aws_config, ctx)
        try:
            await execute_query(ctx, conn, BEGIN_READ_ONLY_TRANSACTION_SQL)
        except Exception:
            await ctx.error(INTERNAL_ERROR)
            raise

        try:
            rows = await execute_query(ctx, conn, sql)
            await execute_query(ctx, conn, COMMIT_TRANSACTION_SQL)
            return rows
        except psycopg.errors.ReadOnlySqlTransaction:
            await ctx.error(READ_ONLY_QUERY_WRITE_ERROR)
            raise
        finally:
            try:
                await execute_query(ctx, conn, ROLLBACK_TRANSACTION_SQL)
            except Exception:
                logger.error(ERROR_ROLLBACK_TRANSACTION)
    except Exception as e:
        await ctx.error(f'{ERROR_READONLY_QUERY}: {e}')
        raise

@mcp.tool(
    name='transact',
    description='Execute SQL statements in a transaction.',
)
async def transact(
    sql_list: Annotated[
        List[str],
        Field(description='SQL statements to run in a transaction')
    ],
    aws_config: AWSConfig,
    ctx: Context,
) -> List[Dict]:
    logger.info(f'transact: {sql_list}')

    if read_only:
        await ctx.error(ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE)
        raise Exception(ERROR_TRANSACT_INVOKED_IN_READ_ONLY_MODE)

    if not sql_list:
        await ctx.error(ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT)
        raise ValueError(ERROR_EMPTY_SQL_LIST_PASSED_TO_TRANSACT)

    try:
        conn = await get_connection(aws_config, ctx)
        await execute_query(ctx, conn, BEGIN_TRANSACTION_SQL)
        rows = []
        for q in sql_list:
            rows = await execute_query(ctx, conn, q)
        await execute_query(ctx, conn, COMMIT_TRANSACTION_SQL)
        return rows
    except Exception as e:
        await execute_query(ctx, conn, ROLLBACK_TRANSACTION_SQL)
        await ctx.error(f'{ERROR_TRANSACT}: {e}')
        raise

@mcp.tool(
    name='get_schema',
    description='Get the schema of the given table',
)
async def get_schema(
    table_name: Annotated[str, Field(description='Name of the table')],
    aws_config: AWSConfig,
    ctx: Context,
) -> List[Dict]:
    logger.info(f'get_schema: {table_name}')

    if not table_name:
        await ctx.error(ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA)
        raise ValueError(ERROR_EMPTY_TABLE_NAME_PASSED_TO_SCHEMA)

    try:
        conn = await get_connection(aws_config, ctx)
        return await execute_query(ctx, conn, GET_SCHEMA_SQL, [table_name])
    except Exception as e:
        await ctx.error(f'{ERROR_GET_SCHEMA}: {e}')
        raise

class NoOpCtx:
    async def error(self, message: str):
        pass

# ----------------------------------------------------------------------------
# Connection and execution helpers
# ----------------------------------------------------------------------------
async def get_password_token(aws_config: AWSConfig) -> str:
    dsql_client = create_dsql_client(aws_config)
    if database_user == 'admin':
        return dsql_client.generate_db_connect_admin_auth_token(
            cluster_endpoint, aws_config.region_name
        )
    return dsql_client.generate_db_connect_auth_token(
        cluster_endpoint, aws_config.region_name
    )

async def get_connection(aws_config: AWSConfig, ctx: Context):
    global persistent_connection

    if persistent_connection:
        return persistent_connection

    token = await get_password_token(aws_config)
    conn_params = {
        'dbname': DSQL_DB_NAME,
        'user': database_user,
        'host': cluster_endpoint,
        'port': DSQL_DB_PORT,
        'password': token,
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
        logger.error(f'{ERROR_CREATE_CONNECTION}: {e}')
        await ctx.error(f'{ERROR_CREATE_CONNECTION}: {e}')
        raise

async def execute_query(
    ctx: Context,
    conn_to_use,
    query: str,
    params: Optional[List] = None,
) -> List[Dict]:
    if conn_to_use is None:
        conn = await get_connection(ctx)
    else:
        conn = conn_to_use

    try:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(query, params)
            if cur.rownumber is None:
                return []
            return await cur.fetchall()
    except (psycopg.OperationalError, psycopg.InterfaceError):
        # Reconnect on transient errors
        logger.warning('Connection error, reconnecting')
        global persistent_connection
        if persistent_connection:
            await persistent_connection.close()
        persistent_connection = None

        # Get a fresh connection and retry
        conn = await get_connection(ctx)
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(query, params)
            if cur.rownumber is None:
                return []
            return await cur.fetchall()
    except Exception as e:
        logger.error(f'{ERROR_EXECUTE_QUERY}: {e}')
        await ctx.error(f'{ERROR_EXECUTE_QUERY}: {e}')
        raise

# ----------------------------------------------------------------------------
# Server bootstrap
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='MCP server for Aurora DSQL'
    )
    parser.add_argument('--cluster_endpoint', required=True)
    parser.add_argument('--database_user', required=True)
    parser.add_argument('--allow-writes', action='store_true')
    parser.add_argument(
        '--aws_config',
        required=True,
        help='JSON string: {"aws_access_key_id":"...","aws_secret_access_key":"...","region_name":"..."}',
    )
    args = parser.parse_args()

    global cluster_endpoint, database_user, read_only
    cluster_endpoint = args.cluster_endpoint
    database_user = args.database_user
    read_only = not args.allow_writes

    # validate AWSConfig but do not create global client here
    aws_conf = AWSConfig.parse_raw(args.aws_config)

    # verify connectivity
    try:
        noop = NoOpCtx()
        asyncio.run(execute_query(noop, None, 'SELECT 1'))
    except Exception as e:
        logger.error(f'Connection validation failed: {e}')
        sys.exit(1)

    logger.success('Connection to Aurora DSQL validated')
    mcp.run()

if __name__ == '__main__':
    main()
