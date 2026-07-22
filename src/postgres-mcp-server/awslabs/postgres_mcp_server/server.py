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
import json
import sys
import threading
from awslabs.postgres_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from awslabs.postgres_mcp_server.connection.cp_api_connection import (
    DEFAULT_POSTGRES_PORT,
    internal_create_express_cluster,
    internal_create_serverless_cluster,
    internal_get_cluster_properties,
    internal_get_cluster_valid_endpoints,
    internal_get_instance_properties,
    setup_aurora_iam_policy_for_current_user,
)
from awslabs.postgres_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
    DBConnectionMap,
)
from awslabs.postgres_mcp_server.connection.psycopg_pool_connection import (
    PsycopgPoolConnection,
    get_credentials_from_secret,
)
from awslabs.postgres_mcp_server.connection.rds_api_connection import RDSDataAPIConnection
from awslabs.postgres_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
)
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional, Tuple


# Max identifier length in bytes (NAMEDATALEN - 1, default compile-time constant)
MAX_IDENTIFIER_BYTES = 63

# Max number of parts: catalog.schema.table
MAX_PARTS = 3

db_connection_map = DBConnectionMap()
async_job_status: Dict[str, dict] = {}
async_job_status_lock = threading.Lock()
client_error_code_key = 'run_query ClientError code'
write_query_prohibited_key = 'Your MCP tool only allows readonly query. If you want to write, change the MCP configuration per README.md'
query_comment_prohibited_key = 'The comment in query is prohibited because of injection risk'
query_injection_risk_key = 'Your query contains risky injection patterns'
readonly_query = True

# Least-privilege guardrail policy for post-connect validation.
#   'enforce' (default): reject a connection whose Postgres role is a
#       superuser or a member of rds_superuser.
#   'warn': log a warning but allow the connection.
#   'off': skip the privilege check entirely (connectivity only).
# Set from the --privilege_check CLI arg in main().
PRIVILEGE_CHECK_ENFORCE = 'enforce'
PRIVILEGE_CHECK_WARN = 'warn'
PRIVILEGE_CHECK_OFF = 'off'
privilege_check_policy = PRIVILEGE_CHECK_ENFORCE

# Per-target Secrets Manager ARN overrides configured at server startup via
# repeatable --secret_arn flags. Lookups are by:
#   - Cluster identifier (e.g. 'mcp-prod-1') for Aurora / RDS-multi-AZ-cluster
#     deployments. Matches the ``cluster_identifier`` parameter resolved
#     from --db_cluster_arn or from the connect_to_database tool.
#   - Instance endpoint hostname (e.g.
#     'myinstance.abc123.us-west-2.rds.amazonaws.com') for the RPG single-
#     instance deployment. Matches the AWS-resolved Endpoint.Address that
#     describe_db_instances returns, NOT any caller-supplied alias.
# The keying is intentional: the LLM can never inject a target string
# that wasn't provided by the operator at startup. configured_default_secret_arn
# (a bare --secret_arn ARN with no key) is used when no per-target entry
# matches; cluster/instance MasterUserSecret is used as a final fallback.
configured_secret_arns: Dict[str, str] = {}
configured_default_secret_arn: Optional[str] = None


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


class ConnectionValidationError(Exception):
    """Raised when a freshly established connection fails post-connect validation.

    Currently signals a least-privilege violation (the connected Postgres
    role is a superuser or a member of rds_superuser) under the 'enforce'
    policy, or an inability to verify the role's privileges (fail-closed).
    """


# Determine whether the connected role is a superuser or a member of the
# managed rds_superuser role. current_user can always read its own row in
# the pg_roles view, and the EXISTS clause evaluates to false (rather than
# erroring) on clusters where rds_superuser does not exist (e.g. self-hosted
# PostgreSQL), so the query is safe across managed and unmanaged deployments.
POSTGRES_PRIVILEGE_QUERY = (
    'SELECT rolsuper AS is_superuser, '
    'EXISTS ('
    "SELECT 1 FROM pg_roles r WHERE r.rolname = 'rds_superuser' "
    "AND pg_has_role(current_user, r.oid, 'MEMBER')"
    ') AS is_rds_superuser '
    'FROM pg_roles WHERE rolname = current_user'
)


async def validate_connection(db_connection: AbstractDBConnection, policy: str) -> None:
    """Post-connect validation: connectivity plus a least-privilege guardrail.

    Runs once when a connection is established (at startup and via the
    connect_to_database tool). The privilege query doubles as a connectivity
    check. Behaviour by policy:

      - 'off':     connectivity only (SELECT 1); no privilege check.
      - 'warn':    run the privilege check. If the role is over-privileged or
                   its privileges can't be determined, log a warning but still
                   ALLOW the connection. However, if the check query cannot run
                   at all (database unreachable or authentication failed), that
                   error is raised, not suppressed: 'warn' only softens the
                   privilege check, it does not waive the need for a working
                   connection.
      - 'enforce': run the privilege check; raise ConnectionValidationError
                   on a violation, or if the check could not be performed
                   (fail-closed).

    The primary security boundary is a least-privilege database role; this
    guardrail simply refuses to operate as superuser / rds_superuser so the
    MCP is not silently running with cluster-wide privileges.

    Args:
        db_connection: the freshly established data-plane connection.
        policy: one of 'enforce', 'warn', 'off'.

    Raises:
        ConnectionValidationError: under 'enforce', on a privilege violation
            or when privileges cannot be verified.
    """
    if policy == PRIVILEGE_CHECK_OFF:
        # Connectivity only — prove the connection can execute a trivial query.
        await db_connection.execute_query('SELECT 1')
        return

    try:
        response = await db_connection.execute_query(POSTGRES_PRIVILEGE_QUERY)
        rows = parse_execute_response(response)
    except Exception as e:
        # A thrown error here means the probe query did not execute at all —
        # a genuine connectivity/auth failure, not merely an "unverifiable
        # privilege". Connectivity is required under every policy: 'warn'
        # relaxes the privilege guardrail, not the requirement that the
        # connection works. Fail closed under enforce; propagate the
        # underlying error under warn (previously this was swallowed, which
        # let an unreachable/mis-authenticated connection start up as if
        # healthy).
        message = f'Could not verify connection role privileges: {type(e).__name__}: {e}'
        if policy == PRIVILEGE_CHECK_ENFORCE:
            raise ConnectionValidationError(f'{message}. Rejecting connection (fail-closed).')
        logger.warning(f'{message}. Connectivity check failed; rejecting connection.')
        raise

    # Treat both an empty result set and a result missing the expected
    # columns as "unverifiable" — we control the query, so this should not
    # happen, but a guardrail must not silently pass a role it could not
    # actually inspect.
    if not rows or 'is_superuser' not in rows[0] or 'is_rds_superuser' not in rows[0]:
        message = 'Could not determine connection role privileges (unexpected result shape).'
        if policy == PRIVILEGE_CHECK_ENFORCE:
            raise ConnectionValidationError(f'{message} Rejecting connection (fail-closed).')
        logger.warning(f'{message} Allowing connection (privilege_check=warn).')
        return

    is_superuser = bool(rows[0].get('is_superuser'))
    is_rds_superuser = bool(rows[0].get('is_rds_superuser'))

    if is_superuser or is_rds_superuser:
        flags = []
        if is_superuser:
            flags.append('a superuser')
        if is_rds_superuser:
            flags.append('a member of rds_superuser')
        message = (
            f'The MCP server is connecting as an over-privileged Postgres role '
            f'({" and ".join(flags)}). A superuser / rds_superuser role bypasses '
            f'row-level security, can read credential catalogs, and can terminate '
            f'other sessions. Connect using a dedicated least-privilege role '
            f'instead (see the Security Consideration section of README.md).'
        )
        if policy == PRIVILEGE_CHECK_ENFORCE:
            raise ConnectionValidationError(message)
        logger.warning(f'{message} Allowing connection (privilege_check=warn).')
        return

    logger.debug('Connection role privilege check passed (not superuser / rds_superuser).')


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
    connection_method: Annotated[ConnectionMethod, Field(description='connection method')],
    cluster_identifier: Annotated[str, Field(description='Cluster identifier')],
    db_endpoint: Annotated[str, Field(description='database endpoint')],
    database: Annotated[str, Field(description='database name')],
    query_parameters: Annotated[
        Optional[List[Dict[str, Any]]], Field(description='Parameters for the SQL query')
    ] = None,
) -> list[dict]:  # type: ignore
    """Run a SQL query against PostgreSQL.

    Args:
        sql: The sql statement to run
        ctx: MCP context for logging and state management
        connection_method: connection method
        cluster_identifier: Cluster identifier
        db_endpoint: database endpoint
        database: database name
        query_parameters: Parameters for the SQL query

    Returns:
        List of dictionary that contains query response rows
    """
    global client_error_code_key
    global write_query_prohibited_key
    global db_connection_map

    logger.info(
        f'Entered run_query with '
        f'method:{connection_method}, cluster_identifier:{cluster_identifier}, '
        f'db_endpoint:{db_endpoint}, database:{database}, '
        f'sql:{sql}'
    )

    db_connection = db_connection_map.get(
        method=connection_method,
        cluster_identifier=cluster_identifier,
        db_endpoint=db_endpoint,
        database=database,
    )
    if not db_connection:
        err = (
            f'No database connection available for method:{connection_method}, '
            f'cluster_identifier:{cluster_identifier}, db_endpoint:{db_endpoint}, database:{database}'
        )
        logger.error(err)
        await ctx.error(err)
        return [{'error': err}]

    if db_connection.readonly_query:
        matches = detect_mutating_keywords(sql)
        if (bool)(matches):
            logger.info(
                (
                    f'query is rejected because current setting only allows readonly query.'
                    f'detected keywords: {matches}, SQL query: {sql}'
                )
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
        logger.debug(
            (
                f'run_query: sql:{sql} method:{connection_method}, '
                f'cluster_identifier:{cluster_identifier} database:{database} '
                f'db_endpoint:{db_endpoint} '
                f'readonly:{db_connection.readonly_query} query_parameters:{query_parameters}'
            )
        )

        response = await db_connection.execute_query(sql, query_parameters)

        logger.success(f'run_query successfully executed query:{sql}')
        return parse_execute_response(response)
    except ClientError as e:
        logger.exception(f'run_query ClientError: {e.response["Error"]["Code"]}')
        await ctx.error(
            str({'code': e.response['Error']['Code'], 'message': e.response['Error']['Message']})
        )
        return [{'error': client_error_code_key}]
    except Exception as e:
        logger.exception(f'run_query failed: {type(e).__name__}')
        error_details = f'{type(e).__name__}: {str(e)}'
        await ctx.error(str({'message': error_details}))
        return [{'error': error_details}]


@mcp.tool(name='get_table_schema', description='Fetch table columns and comments from Postgres')
async def get_table_schema(
    connection_method: Annotated[ConnectionMethod, Field(description='connection method')],
    cluster_identifier: Annotated[str, Field(description='Cluster identifier')],
    db_endpoint: Annotated[str, Field(description='database endpoint')],
    database: Annotated[str, Field(description='database name')],
    table_name: Annotated[str, Field(description='name of the table')],
    ctx: Context,
) -> list[dict]:
    """Get a table's schema information given the table name.

    Args:
        connection_method: connection method
        cluster_identifier: Cluster identifier
        db_endpoint: database endpoint
        database: database name
        table_name: name of the table
        ctx: MCP context for logging and state management

    Returns:
        List of dictionary that contains query response rows
    """
    logger.info(
        (
            f'Entered get_table_schema: table_name:{table_name} connection_method:{connection_method}, '
            f'cluster_identifier:{cluster_identifier}, db_endpoint:{db_endpoint}, database:{database}'
        )
    )

    if not validate_table_name(table_name):
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=(f"Invalid table name: '{table_name}'. "))
        )

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

    return await run_query(
        sql=sql,
        ctx=ctx,
        connection_method=connection_method,
        cluster_identifier=cluster_identifier,
        db_endpoint=db_endpoint,
        database=database,
        query_parameters=params,
    )


@mcp.tool(
    name='connect_to_database',
    description='Connect to a specific database and save the connection internally',
)
async def connect_to_database(
    region: Annotated[str, Field(description='region')],
    database_type: Annotated[DatabaseType, Field(description='database type')],
    connection_method: Annotated[ConnectionMethod, Field(description='connection method')],
    cluster_identifier: Annotated[str, Field(description='cluster identifier')],
    db_endpoint: Annotated[str, Field(description='database endpoint')],
    port: Annotated[int, Field(description='Postgres port')],
    database: Annotated[str, Field(description='database name')],
) -> str:
    """Connect to a specific database save the connection internally.

    Args:
        region: region of the database. Required parametere.
        database_type: Either APG for Aurora Postgres or RPG for RDS Postgres cluster. Required parameter
        connection_method: Either RDS_API, PG_WIRE_PROTOCOL, or PG_WIRE_IAM_PROTOCOL. Required parameter
        cluster_identifier: Either Aurora Postgres cluster identifier or RDS Postgres cluster identifier
        db_endpoint: database endpoint
        port: database port
        database: database name. Required parameter

        Supported scenario:
        1. Aurora Postgres database with RDS_API + Credential Manager:
            cluster_identifier must be set
            db_endpoint and port will be ignored
        2. Aurora Postgres database with direct connection + IAM:
            cluster_identifier must be set
            db_endpoint must be set
        3. Aurora Postgres database with direct connection + PG_AUTH (Credential Manager):
            cluster_identifier must be set
            db_endpoint must be set
        4. RDS Postgres database with direct connection + PG_AUTH (Credential Manager):
            credential manager setting is either on instance or cluster
            db_endpoint must be set
    """
    try:
        db_connection, llm_response = internal_create_connection(
            region=region,
            database_type=database_type,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=db_endpoint,
            port=port,
            database=database,
        )

        # Eagerly initialize the connection pool so it's ready for queries
        # and created_time is set at connect time, not at first query time
        if isinstance(db_connection, PsycopgPoolConnection):
            try:
                await db_connection.initialize_pool()
            except Exception:
                # Pool failed to open — remove the broken connection from the map
                # so the next connect attempt creates a fresh one. Evict by
                # object identity: internal_create_connection stored it under the
                # AWS-resolved endpoint/port, which may not match the
                # caller-supplied db_endpoint/port here (e.g. empty db_endpoint
                # or non-5432 port), so a key-based remove() could silently
                # no-op and leave the broken connection cached.
                db_connection_map.remove_connection(db_connection)
                raise

        # Post-connect validation: connectivity + least-privilege guardrail.
        # A superuser / rds_superuser connection is rejected under the default
        # 'enforce' policy. Remove the connection from the map on failure so it
        # cannot be reached later via run_query. Evict by object identity:
        # internal_create_connection stored the connection under the
        # AWS-resolved endpoint/port, which may differ from the caller-supplied
        # db_endpoint/port here (empty db_endpoint, non-5432 port, host casing).
        # A key-based remove() rebuilt from the caller args could miss the
        # actual key, leave the rejected connection cached, and defeat the
        # guardrail. See the connection-map key-normalization follow-up.
        try:
            await validate_connection(db_connection, privilege_check_policy)
        except Exception:
            db_connection_map.remove_connection(db_connection)
            raise

        return str(llm_response)

    except Exception as e:
        logger.exception(f'connect_to_database failed with error: {str(e)}')
        llm_response = {'status': 'Failed', 'error': str(e)}
        return json.dumps(llm_response, indent=2)


@mcp.tool(name='is_database_connected', description='Check if a connection has been established')
def is_database_connected(
    cluster_identifier: Annotated[str, Field(description='cluster identifier')],
    db_endpoint: Annotated[str, Field(description='database endpoint')] = '',
    database: Annotated[str, Field(description='database name')] = 'postgres',
) -> bool:
    """Check if a connection has been established.

    Args:
        cluster_identifier: cluster identifier
        db_endpoint: database endpoint
        database: database name

    Returns:
        result in boolean
    """
    global db_connection_map
    if db_connection_map.get(ConnectionMethod.RDS_API, cluster_identifier, db_endpoint, database):
        return True

    if db_connection_map.get(
        ConnectionMethod.PG_WIRE_PROTOCOL, cluster_identifier, db_endpoint, database
    ):
        return True

    if db_connection_map.get(
        ConnectionMethod.PG_WIRE_IAM_PROTOCOL, cluster_identifier, db_endpoint, database
    ):
        return True

    return False


@mcp.tool(
    name='get_database_connection_info',
    description='Get all cached database connection information',
)
def get_database_connection_info() -> str:
    """Get all cached database connection information.

    Return:
        A list of cached connection information.
    """
    global db_connection_map
    return db_connection_map.get_keys_json()


@mcp.tool(name='create_cluster', description='Create an Aurora Postgres cluster')
def create_cluster(
    region: Annotated[str, Field(description='region')],
    cluster_identifier: Annotated[str, Field(description='cluster identifier')],
    database: Annotated[str, Field(description='default database name')] = 'postgres',
    engine_version: Annotated[str, Field(description='engine version')] = '17.5',
    with_express_configuration: Annotated[
        bool, Field(description='with express configuration')
    ] = False,
) -> str:
    """Create an RDS/Aurora cluster.

    Args:
        region: region
        cluster_identifier: cluster identifier
        database: database name, ignored when with_express_configuration is set to true
        engine_version: engine version, ignored when with_express_configuration is set to true
        with_express_configuration: create the cluster with express configuration

    Returns:
        result
    """
    logger.info(
        f'Entered create_cluster with region:{region}, '
        f'cluster_identifier:{cluster_identifier} '
        f'database:{database} '
        f'engine_version:{engine_version} '
        f'with_express_configuration:{with_express_configuration}'
    )

    database_type = DatabaseType.APG
    if with_express_configuration:
        connection_method = ConnectionMethod.PG_WIRE_IAM_PROTOCOL
    else:
        connection_method = ConnectionMethod.RDS_API

    if with_express_configuration:
        internal_create_express_cluster(cluster_identifier, region)

        properties = internal_get_cluster_properties(
            cluster_identifier=cluster_identifier, region=region
        )

        setup_aurora_iam_policy_for_current_user(
            db_user=properties['MasterUsername'],
            cluster_resource_id=properties['DbClusterResourceId'],
            cluster_region=region,
        )

        internal_create_connection(
            region=region,
            database_type=database_type,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=properties['Endpoint'],
            port=properties.get('Port', 5432),
            database=database,
        )

        result = {
            'status': 'Completed',
            'cluster_identifier': cluster_identifier,
            'db_endpoint': properties['Endpoint'],
            'message': 'Express cluster creation completed successfully',
        }

        return json.dumps(result, indent=2)

    job_id = (
        f'create-cluster-{cluster_identifier}-{datetime.now().isoformat(timespec="milliseconds")}'
    )

    try:
        async_job_status_lock.acquire()
        async_job_status[job_id] = {'state': 'pending', 'result': None}
    finally:
        async_job_status_lock.release()

    t = threading.Thread(
        target=create_cluster_worker,
        args=(
            job_id,
            region,
            database_type,
            connection_method,
            cluster_identifier,
            engine_version,
            database,
        ),
        daemon=False,
    )
    t.start()

    logger.info(
        f'start_create_cluster_job return with job_id:{job_id}'
        f'region:{region} cluster_identifier:{cluster_identifier} database:{database} '
        f'engine_version:{engine_version}'
    )

    result = {
        'status': 'Pending',
        'message': 'cluster creation started',
        'job_id': job_id,
        'cluster_identifier': cluster_identifier,
        'check_status_tool': 'get_job_status',
        'next_action': f"Use get_job_status(job_id='{job_id}') to get results",
    }

    return json.dumps(result, indent=2)


@mcp.tool(name='get_job_status', description='get background job status')
def get_job_status(job_id: str) -> dict:
    """Get background job status.

    Args:
        job_id: job id
    Returns:
        job status
    """
    global async_job_status
    global async_job_status_lock

    try:
        async_job_status_lock.acquire()
        return async_job_status.get(job_id, {'state': 'not_found'})
    finally:
        async_job_status_lock.release()


def create_cluster_worker(
    job_id: str,
    region: str,
    database_type: DatabaseType,
    connection_method: ConnectionMethod,
    cluster_identifier: str,
    engine_version: str,
    database: str,
):
    """Background worker for cluster creation.

    Args:
        job_id: Unique job identifier
        region: AWS region
        database_type: Database type (APG or RPG)
        connection_method: Connection method
        cluster_identifier: Cluster identifier
        engine_version: Engine version
        database: Database name
    """
    global db_connection_map
    global async_job_status
    global async_job_status_lock
    global readonly_query

    try:
        cluster_result = internal_create_serverless_cluster(
            region=region,
            cluster_identifier=cluster_identifier,
            engine_version=engine_version,
            database_name=database,
        )

        setup_aurora_iam_policy_for_current_user(
            db_user=cluster_result['MasterUsername'],
            cluster_resource_id=cluster_result['DbClusterResourceId'],
            cluster_region=region,
        )

        # Connect to the freshly-created cluster. internal_create_connection
        # falls back to the cluster's MasterUserSecret.SecretArn (sourced
        # from describe_db_clusters) when no per-target or default
        # --secret_arn override is configured, so this works regardless of
        # whether the operator started the MCP server with --secret_arn.
        internal_create_connection(
            region=region,
            database_type=database_type,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=cluster_result['Endpoint'],
            port=5432,
            database=database,
        )

        try:
            async_job_status_lock.acquire()
            async_job_status[job_id]['state'] = 'succeeded'
        finally:
            async_job_status_lock.release()
    except Exception as e:
        logger.exception(f'create_cluster_worker failed with {e}')
        try:
            async_job_status_lock.acquire()
            async_job_status[job_id]['state'] = 'failed'
            async_job_status[job_id]['result'] = str(e)
        finally:
            async_job_status_lock.release()


def internal_create_connection(
    region: Annotated[str, Field(description='region')],
    database_type: Annotated[DatabaseType, Field(description='database type')],
    connection_method: Annotated[ConnectionMethod, Field(description='connection method')],
    cluster_identifier: Annotated[str, Field(description='cluster identifier')],
    db_endpoint: Annotated[str, Field(description='database endpoint')],
    port: Annotated[int, Field(description='Postgres port')],
    database: Annotated[str, Field(description='database name')] = 'postgres',
) -> Tuple:
    """Connect to a specific database save the connection internally.

    Secrets Manager ARN resolution priority (each step falls through if
    nothing matches):

      1. ``configured_secret_arns[cluster_identifier]`` if cluster path,
         else ``configured_secret_arns[db_endpoint]`` for the RPG instance
         path. The instance lookup uses the AWS-resolved endpoint
         hostname, not the caller-supplied input — operator must register
         the hostname exactly as RDS reports it.
      2. ``configured_default_secret_arn`` — the bare ``--secret_arn`` ARN
         with no key, intended as a default for any target the operator
         didn't pin explicitly.
      3. Cluster's / instance's ``MasterUserSecret.SecretArn`` from RDS
         describe_* responses. This is the natural default for clusters
         whose master user is managed by Secrets Manager
         (ManageMasterUserPassword=True).
      4. If none of the above yields a value, raise ``ValueError``.

    Note: the LLM cannot influence steps 1–2. The map keys are facts
    about the target derived from RDS metadata or operator configuration.

    Args:
        region: region
        database_type: database type (APG or RPG)
        connection_method: connection method (RDS_API, PG_WIRE_PROTOCOL, or PG_WIRE_IAM_PROTOCOL)
        cluster_identifier: cluster identifier
        db_endpoint: database endpoint
        port: database port
        database: database name
    """
    global db_connection_map
    global readonly_query
    global configured_secret_arns
    global configured_default_secret_arn

    logger.debug(
        f'Enter internal_create_connection\n'
        f'region:{region}\n'
        f'database_type:{database_type}\n'
        f'connection_method:{connection_method}\n'
        f'cluster_identifier:{cluster_identifier}\n'
        f'db_endpoint:{db_endpoint}\n'
        f'database:{database}\n'
        f'readonly_query:{readonly_query}'
    )

    if not region:
        raise ValueError("region can't be none or empty")

    if not connection_method:
        raise ValueError("connection_method can't be none or empty")

    if not database_type:
        raise ValueError("database_type can't be none or empty")

    if database_type == DatabaseType.APG and not cluster_identifier:
        raise ValueError("cluster_identifier can't be none or empty for Aurora Postgres Database")

    existing_conn = db_connection_map.get(
        connection_method, cluster_identifier, db_endpoint, database, port
    )
    if existing_conn:
        llm_response = json.dumps(
            {
                'connection_method': connection_method,
                'cluster_identifier': cluster_identifier,
                'db_endpoint': db_endpoint,
                'database': database,
                'port': port,
            },
            indent=2,
            default=str,
        )
        return (existing_conn, llm_response)

    # Resolve the Secrets Manager ARN and master-username candidate from
    # cluster / instance metadata. Both feed the resolution below: the
    # operator-supplied --secret_arn override (per-target or default) wins
    # when set; otherwise we fall back to whatever AWS advertises. Express
    # clusters have no MasterUserSecret (IAM-only auth, no shared password)
    # but always populate MasterUsername.
    # always populate MasterUsername.
    metadata_secret_arn: str = ''
    metadata_master_username: str = ''

    enable_data_api: bool = False
    cluster_arn: str = ''

    if cluster_identifier:
        # Can be either APG (APG always requires cluster) or RPG multi-AZ cluster deployment case
        cluster_properties = internal_get_cluster_properties(
            cluster_identifier=cluster_identifier, region=region
        )

        enable_data_api = cluster_properties.get('HttpEndpointEnabled', False)
        cluster_arn = cluster_properties.get('DBClusterArn', '')
        metadata_secret_arn = cluster_properties.get('MasterUserSecret', {}).get('SecretArn', '')
        metadata_master_username = cluster_properties.get('MasterUsername', '') or ''

        cluster_writer_endpoint = cluster_properties.get('Endpoint', '')
        try:
            cluster_port = int(cluster_properties.get('Port') or 0)
        except (TypeError, ValueError):
            cluster_port = DEFAULT_POSTGRES_PORT

        if not db_endpoint:
            # No endpoint supplied: default to the cluster's writer endpoint/port
            # sourced directly from AWS. Caller never influences the host string.
            db_endpoint = cluster_writer_endpoint
            port = cluster_port
        else:
            # Endpoint supplied: validate (host, port) against the cluster's
            # advertised endpoints (writer, reader, custom, members). If the
            # caller-supplied pair does not match any legitimate endpoint,
            # refuse the connection — this prevents directing credentials or
            # IAM auth tokens at an attacker-controlled host.
            #
            # On match, we overwrite the local db_endpoint/port with the
            # AWS-sourced strings so the connection string is never built
            # from caller input.
            valid_endpoints = internal_get_cluster_valid_endpoints(
                cluster_properties=cluster_properties, region=region
            )

            requested_host = db_endpoint.strip().lower()
            matched: Optional[Tuple[str, int]] = None
            for valid_host, valid_port in valid_endpoints:
                if valid_host.lower() == requested_host and valid_port == port:
                    matched = (valid_host, valid_port)
                    break

            if matched is None:
                valid_repr = ', '.join(f'{h}:{p}' for h, p in valid_endpoints) or '<none>'
                err = (
                    f"db_endpoint '{db_endpoint}:{port}' does not match any endpoint of "
                    f"cluster '{cluster_identifier}'. Valid endpoints: {valid_repr}"
                )
                logger.error(err)
                raise ValueError(err)

            db_endpoint, port = matched
    else:
        # Must be RPG instance only deployment case (i.e. without cluster).
        # internal_get_instance_properties already verifies that the supplied
        # endpoint matches an actual RDS instance endpoint in the account.
        # We still overwrite db_endpoint/port with the AWS-sourced values so
        # the connection string never comes from the caller-supplied string.
        instance_properties = internal_get_instance_properties(db_endpoint, region)
        metadata_secret_arn = instance_properties.get('MasterUserSecret', {}).get('SecretArn', '')
        metadata_master_username = instance_properties.get('MasterUsername', '') or ''
        instance_endpoint = instance_properties.get('Endpoint', {}) or {}
        resolved_host = instance_endpoint.get('Address', '')
        try:
            resolved_port = int(instance_endpoint.get('Port') or 0)
        except (TypeError, ValueError):
            resolved_port = DEFAULT_POSTGRES_PORT
        if resolved_host:
            db_endpoint = resolved_host
        if resolved_port:
            port = resolved_port

    # Resolve the Secrets Manager ARN. Per-target override map wins,
    # then the bare default ARN, then the cluster/instance MasterUserSecret.
    # IAM-only clusters (Aurora express) advertise no MasterUserSecret,
    # which is fine — the IAM branch below doesn't need one.
    #
    # The lookup key is the cluster identifier on the cluster path, and
    # the AWS-resolved Endpoint.Address on the RPG instance-only path.
    # The LLM cannot influence either key.
    if cluster_identifier:
        target_key = cluster_identifier
    else:
        target_key = db_endpoint  # already overwritten with the AWS-resolved host above
    per_target_secret_arn = configured_secret_arns.get(target_key, '')
    effective_secret_arn = (
        per_target_secret_arn or configured_default_secret_arn or metadata_secret_arn or ''
    )

    # Whether a secret is mandatory depends on the connection method.
    # RDS_API and PG_WIRE_PROTOCOL need a password from Secrets Manager.
    # PG_WIRE_IAM_PROTOCOL does not — it uses an IAM auth token; only the
    # username matters, and it can come from the secret OR from the
    # cluster's MasterUsername metadata.
    if connection_method in (ConnectionMethod.RDS_API, ConnectionMethod.PG_WIRE_PROTOCOL):
        if not effective_secret_arn:
            raise ValueError(
                f'Connection method {connection_method} requires a Secrets '
                f'Manager ARN. Start the MCP server with --secret_arn <arn>, '
                f'or point at a cluster/instance whose master user is managed '
                f'by Secrets Manager (ManageMasterUserPassword=True).'
            )

    logger.debug(
        f'About to create internal DB connections with:'
        f'enable_data_api:{enable_data_api}\n'
        f'cluster_arn:{cluster_arn}\n'
        f'effective_secret_arn:{effective_secret_arn}\n'
        f'metadata_master_username:{metadata_master_username}\n'
        f'db_endpoint:{db_endpoint}\n'
        f'port:{port}\n'
        f'region:{region}\n'
        f'readonly:{readonly_query}'
    )

    db_connection = None
    if connection_method == ConnectionMethod.PG_WIRE_IAM_PROTOCOL:
        # IAM auth uses a generated token as the password and only needs a
        # username. Resolution priority for the username:
        #   1. The operator-configured secret (when --secret_arn is set,
        #      we read 'username' from it). This lets the operator bind
        #      the MCP to a non-master role.
        #   2. The cluster/instance MasterUsername advertised by AWS.
        #      This is the only path that works for Aurora express
        #      clusters, which never have a Secrets Manager secret.
        if effective_secret_arn:
            iam_username, _ = get_credentials_from_secret(
                secret_arn=effective_secret_arn, region=region
            )
        elif metadata_master_username:
            iam_username = metadata_master_username
        else:
            raise ValueError(
                'IAM authentication requires a username. Either supply '
                '--secret_arn pointing at a secret with a "username" field, '
                'or use a cluster/instance whose MasterUsername is reported '
                'by AWS.'
            )

        db_connection = PsycopgPoolConnection(
            host=db_endpoint,
            port=port,
            database=database,
            readonly=readonly_query,
            secret_arn='',
            db_user=iam_username,
            region=region,
            is_iam_auth=True,
        )

    elif connection_method == ConnectionMethod.RDS_API:
        db_connection = RDSDataAPIConnection(
            cluster_arn=cluster_arn,
            secret_arn=effective_secret_arn,
            database=database,
            region=region,
            readonly=readonly_query,
        )
    else:
        # must be connection_method == ConnectionMethod.PG_WIRE_PROTOCOL
        db_connection = PsycopgPoolConnection(
            host=db_endpoint,
            port=port,
            database=database,
            readonly=readonly_query,
            secret_arn=effective_secret_arn,
            db_user='',
            region=region,
            is_iam_auth=False,
        )

    if db_connection:
        # NOTE: the key here uses the AWS-resolved db_endpoint (overwritten
        # above) and omits port, so it is stored as the 5432 default. This is
        # NOT the same key callers reconstruct in get()/remove() from their
        # own (pre-resolution) db_endpoint/port. Do not rely on rebuilding this
        # key to evict a specific connection — use
        # db_connection_map.remove_connection(conn) instead. Tracked for a
        # broader key-normalization fix (see connection-map follow-up issue).
        db_connection_map.set(
            connection_method, cluster_identifier, db_endpoint, database, db_connection
        )
        llm_response = json.dumps(
            {
                'connection_method': connection_method,
                'cluster_identifier': cluster_identifier,
                'db_endpoint': db_endpoint,
                'database': database,
                'port': port,
            },
            indent=2,
            default=str,
        )
        return (db_connection, llm_response)

    raise ValueError("Can't create connection because invalid input parameter combination")


def _parse_identifier_parts(table_name: str) -> Optional[list[str]]:
    """Parse a possibly-qualified PostgreSQL table name into its identifier parts.

    Uses a character-by-character parser rather than regex because quoted
    identifiers can contain nearly any character, making regex fragile.

    Returns a list of unescaped identifier strings, or None if invalid.
    """
    parts = []
    pos = 0
    length = len(table_name)

    while pos < length:
        if table_name[pos] == '"':
            # ── Quoted identifier ──
            pos += 1  # skip opening quote
            content = []

            while pos < length:
                ch = table_name[pos]

                if ch == '\0':
                    return None  # NUL not allowed

                if ch == '"':
                    # Check for escaped double quote ""
                    if pos + 1 < length and table_name[pos + 1] == '"':
                        content.append('"')
                        pos += 2
                    else:
                        # Closing quote
                        pos += 1
                        break
                else:
                    content.append(ch)
                    pos += 1
            else:
                # Reached end of string without closing quote
                return None

            identifier = ''.join(content)
            if not identifier:
                return None  # zero-length delimited identifier is invalid

            parts.append(identifier)

        else:
            # ── Unquoted identifier ──
            # First character: letter or underscore
            # (Unicode letters: \u0080-\uFFFF covers Latin-1 supplement through BMP)
            ch = table_name[pos]
            if not (ch.isalpha() or ch == '_'):
                return None  # must start with letter or underscore

            start = pos
            pos += 1

            # Subsequent characters: letter, digit, underscore, dollar sign
            while pos < length:
                ch = table_name[pos]
                if ch.isalpha() or ch.isdigit() or ch in ('_', '$'):
                    pos += 1
                else:
                    break

            parts.append(table_name[start:pos])

        # After each identifier, expect '.' separator or end of string
        if pos < length:
            if table_name[pos] == '.':
                pos += 1
                if pos >= length:
                    return None  # trailing dot, no identifier after
            else:
                return None  # unexpected character between identifiers

    return parts if parts else None


def validate_table_name(table_name: str | None) -> bool:
    """Validate a PostgreSQL table name reference.

    Follows PostgreSQL lexical rules from:
    https://www.postgresql.org/docs/current/sql-syntax-lexical.html#SQL-SYNTAX-IDENTIFIERS

    Accepts:
        users                          simple unquoted
        _my_table                      leading underscore
        public.users                   schema-qualified
        mydb.public.users              fully qualified (catalog.schema.table)
        "my-table"                     quoted with special chars
        "column with spaces"           quoted with spaces
        public."My-Table"              mixed quoting
        "My Schema"."My-Table"         both quoted
        "has""quote"                   escaped double quote inside

    Rejects:
        users'; DROP TABLE foo --      injection attempt
        ""                             zero-length identifier
        .users / users.                leading or trailing dot
        a.b.c.d                        more than 3 parts
        123table                       starts with digit (unquoted)
        my-table                       hyphen in unquoted identifier
        (empty string)                 empty input
        (identifiers > 63 bytes)       exceeds NAMEDATALEN - 1
    """
    if not table_name:
        return False

    parts = _parse_identifier_parts(table_name)

    if parts is None:
        return False

    if len(parts) > MAX_PARTS:
        return False

    # Each identifier must fit within NAMEDATALEN - 1 (63 bytes)
    for part in parts:
        if len(part.encode('utf-8')) > MAX_IDENTIFIER_BYTES:
            return False

    return True


def validate_secret_arn_at_startup(secret_arn: str, region: str) -> None:
    """Verify the configured Secrets Manager ARN is readable at startup.

    Calls Secrets Manager once with GetSecretValue against the given ARN.
    Exits the process with a clear error message if the call fails, so the
    operator learns about misconfiguration (missing IAM permission, typo in
    ARN, wrong region, KMS Decrypt denied, deleted secret) at start time
    rather than at first query.

    The fetched credentials are discarded immediately. The connection pool
    will re-fetch them during its own initialize_pool call.

    Args:
        secret_arn: The ARN from --secret_arn.
        region: AWS region for Secrets Manager.

    Raises:
        SystemExit: If the secret cannot be read. Exit code 1.
    """
    try:
        get_credentials_from_secret(secret_arn, region)
    except Exception as e:
        logger.error(
            f'MCP server cannot start: unable to read Secrets Manager ARN '
            f'{secret_arn!r} in region {region!r}. '
            f'Verify the ARN exists, the region is correct, and the AWS '
            f'principal has secretsmanager:GetSecretValue (and kms:Decrypt '
            f'on the secret CMK if non-default). '
            f'Underlying error: {type(e).__name__}: {e}'
        )
        sys.exit(1)

    logger.success(f'Verified Secrets Manager access for {secret_arn} in region {region}')


def main():
    """Main entry point for the MCP server application.

    Runs the MCP server with CLI argument support for PostgreSQL connections.
    """
    global db_connection_map
    global readonly_query
    global configured_secret_arns
    global configured_default_secret_arn
    global privilege_check_policy

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for postgres'
    )

    parser.add_argument(
        '--connection_method',
        help='Connection method to the database. It can be RDS_API, PG_WIRE_PROTOCOL OR PG_WIRE_IAM_PROTOCOL)',
    )
    parser.add_argument('--db_cluster_arn', help='ARN of the RDS or Aurora Postgres cluster')
    parser.add_argument('--db_type', help='APG for Aurora Postgres or RPG for RDS Postgres')
    parser.add_argument('--db_endpoint', help='Instance endpoint address')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument(
        '--privilege_check',
        choices=[PRIVILEGE_CHECK_ENFORCE, PRIVILEGE_CHECK_WARN, PRIVILEGE_CHECK_OFF],
        default=PRIVILEGE_CHECK_ENFORCE,
        help=(
            'Least-privilege guardrail applied when a database connection is established. '
            "'enforce' (default) rejects a connection whose Postgres role is a superuser or "
            "a member of rds_superuser; 'warn' logs a warning but allows it; 'off' skips the "
            'check. Use a dedicated least-privilege role (see README) rather than relaxing this.'
        ),
    )
    parser.add_argument(
        '--allow_write_query', action='store_true', help='Enforce readonly SQL statements'
    )
    parser.add_argument('--database', help='Database name')
    parser.add_argument('--port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument(
        '--secret_arn',
        required=False,
        action='append',
        default=None,
        help=(
            'Optional Secrets Manager ARN override. May be repeated. Each '
            'value is either:\n'
            '  - "<cluster_identifier>=<arn>" — bind the ARN to a specific '
            'Aurora / RDS-multi-AZ-cluster (matched against the cluster '
            'identifier from --db_cluster_arn or the connect_to_database tool).\n'
            '  - "<instance_endpoint>=<arn>" — bind the ARN to a specific '
            'RDS instance endpoint hostname (matched against the AWS-resolved '
            'Endpoint.Address from describe_db_instances).\n'
            '  - "<arn>" without "=" — bare ARN used as the default for any '
            'target the operator did not pin explicitly (at most one allowed).\n'
            'When unspecified, the MCP server falls back to the cluster / '
            'instance MasterUserSecret advertised by AWS. Used by RDS_API and '
            'PG_WIRE_PROTOCOL connection methods, and by PG_WIRE_IAM_PROTOCOL '
            'to source the username (the password is a generated IAM auth token). '
            'The LLM cannot pick a secret ARN — it can only target a cluster or '
            'instance the operator has registered here.'
        ),
    )
    args = parser.parse_args()

    # Parse --secret_arn entries into the per-target map and the optional
    # default. Each --secret_arn value is either "key=arn" (per-target)
    # or a bare ARN (default).
    secret_arn_map: Dict[str, str] = {}
    default_secret_arn: Optional[str] = None
    for raw in args.secret_arn or []:
        if '=' in raw:
            key, _, arn = raw.partition('=')
            key = key.strip()
            arn = arn.strip()
            if not key or not arn:
                logger.error(
                    f'Invalid --secret_arn value {raw!r}: both key and ARN '
                    'must be non-empty when using key=arn syntax.'
                )
                sys.exit(2)
            if key in secret_arn_map:
                logger.error(
                    f'Duplicate --secret_arn key {key!r} (already mapped to '
                    f'{secret_arn_map[key]!r}).'
                )
                sys.exit(2)
            secret_arn_map[key] = arn
        else:
            arn = raw.strip()
            if not arn:
                continue
            if default_secret_arn is not None:
                logger.error(
                    'At most one bare --secret_arn (no "=" separator) is '
                    'allowed; got at least two default ARNs.'
                )
                sys.exit(2)
            default_secret_arn = arn

    logger.info(
        f'MCP configuration:\n'
        f'db_type:{args.db_type}\n'
        f'db_cluster_arn:{args.db_cluster_arn}\n'
        f'connection_method:{args.connection_method}\n'
        f'db_endpoint:{args.db_endpoint}\n'
        f'region:{args.region}\n'
        f'allow_write_query:{args.allow_write_query}\n'
        f'database:{args.database}\n'
        f'port:{args.port}\n'
        f'secret_arn entries: {len(secret_arn_map)} per-target, '
        f'default={"set" if default_secret_arn else "unset"}\n'
    )

    readonly_query = not args.allow_write_query
    privilege_check_policy = args.privilege_check
    configured_secret_arns.clear()
    configured_secret_arns.update(secret_arn_map)
    configured_default_secret_arn = default_secret_arn

    # Probe every configured ARN at startup so misconfiguration surfaces
    # before any query is attempted. The probe is skipped only when no
    # ARNs are configured at all — the cluster's managed secret will be
    # discovered (and validated) lazily on the first connection attempt.
    for target, arn in configured_secret_arns.items():
        try:
            validate_secret_arn_at_startup(arn, args.region)
        except SystemExit:
            logger.error(f'Configured --secret_arn entry for target {target!r} is unreadable.')
            raise
    if configured_default_secret_arn:
        try:
            validate_secret_arn_at_startup(configured_default_secret_arn, args.region)
        except SystemExit:
            logger.error('Configured default --secret_arn is unreadable.')
            raise

    try:
        if args.db_type:
            # Create the appropriate database connection based on the provided parameters
            db_connection: Optional[AbstractDBConnection] = None

            cluster_identifier = args.db_cluster_arn.split(':')[-1]
            db_connection, llm_response = internal_create_connection(
                region=args.region,
                database_type=DatabaseType[args.db_type],
                connection_method=ConnectionMethod[args.connection_method],
                cluster_identifier=cluster_identifier,
                db_endpoint=args.db_endpoint,
                port=args.port,
                database=args.database,
            )

            # Validate the database connection: connectivity plus the
            # least-privilege guardrail. Under the default 'enforce' policy a
            # superuser / rds_superuser connection aborts startup.
            if db_connection:
                try:
                    asyncio.run(validate_connection(db_connection, privilege_check_policy))
                    logger.success('Successfully validated database connection to Postgres')
                except ConnectionValidationError as e:
                    logger.error(
                        f'Refusing to start: {e} '
                        '(set --privilege_check to warn/off to override, not recommended)'
                    )
                    sys.exit(1)
                except Exception as e:
                    logger.error(
                        f'Failed to validate database connection to Postgres: {e}. '
                        'Exit the MCP server'
                    )
                    sys.exit(1)

        logger.info('Postgres MCP server started')
        mcp.run()
        logger.info('Postgres MCP server stopped')
    finally:
        db_connection_map.close_all()


if __name__ == '__main__':
    main()
