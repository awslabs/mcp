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

"""awslabs MySQL MCP Server implementation."""

import argparse
import asyncio
import json
import sys
import threading
from awslabs.mysql_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from awslabs.mysql_mcp_server.connection.asyncmy_pool_connection import AsyncmyPoolConnection
from awslabs.mysql_mcp_server.connection.cp_api_connection import (
    internal_create_aurora_cluster,
    internal_get_cluster_properties,
    internal_get_instance_properties,
    setup_aurora_iam_policy_for_current_user,
)
from awslabs.mysql_mcp_server.connection.db_connection_map import (
    ConnectionMethod,
    DatabaseType,
    DBConnectionMap,
    is_connection_method_supported,
)
from awslabs.mysql_mcp_server.connection.rds_api_connection import RDSDataAPIConnection
from awslabs.mysql_mcp_server.mutable_sql_detector import (
    check_sql_injection_risk,
    detect_mutating_keywords,
)
from botocore.exceptions import ClientError
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional, Tuple


db_connection_map = DBConnectionMap()
async_job_status: Dict[str, dict] = {}
async_job_status_lock = threading.Lock()
client_error_code_key = 'run_query ClientError code'
unexpected_error_key = 'run_query unexpected error'
write_query_prohibited_key = 'Your MCP tool only allows readonly query. If you want to write, change the MCP configuration per README.md'
query_comment_prohibited_key = 'The comment in query is prohibited because of injection risk'
query_injection_risk_key = 'Your query contains risky injection patterns'
readonly_query = True
# Optional path to a CA bundle trusted for IAM-auth SSL verification. Set by
# the CLI flag --ca_bundle on server start. When None, the package's bundled
# Amazon RDS global bundle (verified against a pinned hash) is used.
ca_bundle_path: Optional[str] = None


class DummyCtx:
    """A dummy context class for error handling in MCP tools."""

    async def error(self, message):
        """Raise a runtime error with the given message."""
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
    columns = [col.get('label') or col['name'] for col in response.get('columnMetadata', [])]
    records = []

    for row in response.get('records', []):
        row_data = {col: extract_cell(cell) for col, cell in zip(columns, row)}
        records.append(row_data)

    return records


mcp = FastMCP(
    'mysql-mcp MCP server. This is the starting point for all solutions created',
    dependencies=[
        'loguru',
    ],
)


@mcp.tool(name='run_query', description='Run a SQL query against MySQL')
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
    """Run a SQL query against MySQL.

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
    global unexpected_error_key
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
        logger.info(
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
        # AWS ClientError has a structured Error.Code we can safely surface;
        # the message can include identity strings, so we keep that out of
        # the LLM response and rely on logger.exception for operator visibility.
        logger.exception(client_error_code_key)
        await ctx.error(str({'code': e.response['Error']['Code']}))
        return [{'error': client_error_code_key}]
    except Exception as e:
        # Full traceback is logged locally; only the exception type name is
        # surfaced to the LLM so identity-revealing strings from asyncmy /
        # botocore exceptions never leave the server.
        logger.exception(unexpected_error_key)
        await ctx.error(str({'error_type': type(e).__name__}))
        return [{'error': unexpected_error_key}]


@mcp.tool(name='get_table_schema', description='Fetch table columns and comments from MySQL')
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

    sql = """
        SELECT
            COLUMN_NAME AS column_name,
            COLUMN_TYPE AS data_type,
            IS_NULLABLE AS is_nullable,
            COLUMN_DEFAULT AS column_default,
            COLUMN_KEY AS column_key,
            EXTRA AS extra,
            COLUMN_COMMENT AS column_comment
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :table_schema
            AND TABLE_NAME = :table_name
        ORDER BY ORDINAL_POSITION
    """

    params = [
        {'name': 'table_schema', 'value': {'stringValue': database}},
        {'name': 'table_name', 'value': {'stringValue': table_name}},
    ]

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
def connect_to_database(
    region: Annotated[str, Field(description='region')],
    database_type: Annotated[DatabaseType, Field(description='database type')],
    connection_method: Annotated[ConnectionMethod, Field(description='connection method')],
    cluster_identifier: Annotated[str, Field(description='cluster identifier')],
    db_endpoint: Annotated[str, Field(description='database endpoint')],
    port: Annotated[int, Field(description='MySQL port')],
    database: Annotated[str, Field(description='database name')],
) -> str:
    """Connect to a specific database save the connection internally.

    Args:
        region: region of the database. Required parameter.
        database_type: One of 'aurora-mysql' (Aurora MySQL), 'mysql' (RDS MySQL),
            or 'mariadb' (RDS MariaDB). Required parameter.
        connection_method: Either RDS_API, MYSQL_WIRE_PROTOCOL, or MYSQL_WIRE_IAM_PROTOCOL. Required parameter
        cluster_identifier: Either Aurora MySQL cluster identifier or RDS MySQL cluster identifier
        db_endpoint: database endpoint
        port: database port
        database: database name. Required parameter

        Supported scenario:
        1. Aurora MySQL database with RDS_API + Credential Manager:
            cluster_identifier must be set
            db_endpoint and port will be ignored
        2. Aurora MySQL database with direct connection + IAM:
            cluster_identifier must be set
            db_endpoint must be set
        3. Aurora MySQL database with direct connection + MYSQL_AUTH (Credential Manager):
            cluster_identifier must be set
            db_endpoint must be set
        4. RDS MySQL database with direct connection + MYSQL_AUTH (Credential Manager):
            credential manager setting is either on instance or cluster
            db_endpoint must be set
    """
    try:
        db_connection, llm_response = internal_connect_to_database(
            region=region,
            database_type=database_type,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=db_endpoint,
            port=port,
            database=database,
        )

        return str(llm_response)

    except Exception as e:
        # Log full traceback locally for the operator (cluster ARNs, secret
        # ARNs, hostnames, etc. are useful for debugging on the host running
        # the server). Return only the exception class name to the LLM client
        # so identity-revealing strings from boto3 / asyncmy / Secrets Manager
        # exceptions never leave the server.
        logger.exception('connect_to_database failed')
        llm_response = {
            'status': 'Failed',
            'error_type': type(e).__name__,
            'error_message': 'connect_to_database failed; see server logs for details',
        }
        return json.dumps(llm_response, indent=2)


@mcp.tool(name='is_database_connected', description='Check if a connection has been established')
def is_database_connected(
    cluster_identifier: Annotated[str, Field(description='cluster identifier')],
) -> bool:
    """Check if any connection has been established for the given cluster.

    Scans all cached connections by ``cluster_identifier`` across every
    connection method, endpoint, database, and port. Returns True as long
    as at least one connection for that cluster is cached.

    This is the "is the cluster reachable from this server?" check. To
    verify a specific (cluster, database) pair, call
    ``get_database_connection_info`` and inspect the returned entries.

    Args:
        cluster_identifier: cluster identifier

    Returns:
        True if any connection exists for the cluster, False otherwise.
    """
    global db_connection_map
    return db_connection_map.has_connection_for_cluster(cluster_identifier)


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


@mcp.tool(name='create_cluster', description='Create an Aurora MySQL cluster')
def create_cluster(
    region: Annotated[str, Field(description='region')],
    cluster_identifier: Annotated[str, Field(description='cluster identifier')],
    database: Annotated[str, Field(description='default database name')] = 'app',
    engine_version: Annotated[str, Field(description='engine version')] = '8.0',
    db_subnet_group_name: Annotated[
        Optional[str],
        Field(
            description=(
                'Optional DB subnet group name. Required when the AWS account '
                'does not have default VPC subnets (most production accounts). '
                'When omitted, RDS tries to use default subnets, which fails '
                'with InvalidSubnet in custom-VPC accounts.'
            )
        ),
    ] = None,
    vpc_security_group_ids: Annotated[
        Optional[List[str]],
        Field(
            description=(
                'Optional list of VPC security group IDs to attach to the '
                'cluster. When omitted, RDS uses the default security group '
                'of the chosen subnet group.'
            )
        ),
    ] = None,
    cluster_type: Annotated[
        str,
        Field(
            description=(
                "Aurora cluster topology. 'serverless_v2' (default) creates a "
                'Serverless v2 cluster with auto-scaling ACU — recommended for '
                'variable, bursty, or cost-sensitive workloads. '
                "'provisioned' creates a fixed-capacity cluster with a chosen "
                'instance class — recommended for steady-state production '
                'workloads with predictable load. The agent SHOULD ask the user '
                'to choose between these explicitly when the workload pattern '
                'is unclear.'
            )
        ),
    ] = 'serverless_v2',
    db_instance_class: Annotated[
        str,
        Field(
            description=(
                "Writer instance class. 'db.serverless' (default) for "
                "cluster_type='serverless_v2'. For cluster_type='provisioned', "
                'choose a non-serverless class such as db.r6g.large, '
                'db.r6g.xlarge, db.r7g.large, etc. The agent SHOULD ask the '
                'user for an explicit choice when the workload signals '
                '(steady-state vs spiky) are unclear.'
            )
        ),
    ] = 'db.serverless',
) -> str:
    """Create an RDS/Aurora cluster.

    Args:
        region: region
        cluster_identifier: cluster identifier
        database: database name
        engine_version: engine version
        db_subnet_group_name: optional DB subnet group name (for custom VPC accounts)
        vpc_security_group_ids: optional list of VPC security group IDs
        cluster_type: 'serverless_v2' (default) or 'provisioned'
        db_instance_class: writer instance class. Must be 'db.serverless' when
            cluster_type='serverless_v2'; must be a non-serverless class
            (e.g. db.r6g.large) when cluster_type='provisioned'.

    Returns:
        result
    """
    logger.info(
        f'Entered create_cluster with region:{region}, '
        f'cluster_identifier:{cluster_identifier} '
        f'database:{database} '
        f'engine_version:{engine_version} '
        f'cluster_type:{cluster_type} '
        f'db_instance_class:{db_instance_class} '
        f'db_subnet_group_name:{db_subnet_group_name} '
        f'vpc_security_group_ids:{vpc_security_group_ids}'
    )

    database_type = DatabaseType.AURORA_MYSQL
    connection_method = ConnectionMethod.RDS_API

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
            db_subnet_group_name,
            vpc_security_group_ids,
            cluster_type,
            db_instance_class,
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
    db_subnet_group_name: Optional[str] = None,
    vpc_security_group_ids: Optional[List[str]] = None,
    cluster_type: str = 'serverless_v2',
    db_instance_class: str = 'db.serverless',
):
    """Background worker to create a cluster asynchronously."""
    global db_connection_map
    global async_job_status
    global async_job_status_lock
    global readonly_query

    try:
        cluster_result = internal_create_aurora_cluster(
            region=region,
            cluster_identifier=cluster_identifier,
            engine_version=engine_version,
            database_name=database,
            db_subnet_group_name=db_subnet_group_name,
            vpc_security_group_ids=vpc_security_group_ids,
            cluster_type=cluster_type,
            db_instance_class=db_instance_class,
        )

        setup_aurora_iam_policy_for_current_user(
            db_user=cluster_result['MasterUsername'],
            cluster_resource_id=cluster_result['DbClusterResourceId'],
            cluster_region=region,
        )

        internal_connect_to_database(
            region=region,
            database_type=database_type,
            connection_method=connection_method,
            cluster_identifier=cluster_identifier,
            db_endpoint=cluster_result['Endpoint'],
            port=3306,
            database=database,
        )

        try:
            async_job_status_lock.acquire()
            async_job_status[job_id]['state'] = 'succeeded'
        finally:
            async_job_status_lock.release()
    except Exception as e:
        # Log full traceback locally for the operator. The async_job_status
        # entry is read by the LLM via get_job_status, so we surface only the
        # exception type name there to avoid leaking identity-revealing
        # strings from boto3 / RDS / IAM exceptions.
        logger.exception('create_cluster_worker failed')
        try:
            async_job_status_lock.acquire()
            async_job_status[job_id]['state'] = 'failed'
            async_job_status[job_id]['result'] = (
                f'cluster creation failed ({type(e).__name__}); see server logs for details'
            )
        finally:
            async_job_status_lock.release()


def internal_connect_to_database(
    region: Annotated[str, Field(description='region')],
    database_type: Annotated[DatabaseType, Field(description='database type')],
    connection_method: Annotated[ConnectionMethod, Field(description='connection method')],
    cluster_identifier: Annotated[str, Field(description='cluster identifier')],
    db_endpoint: Annotated[str, Field(description='database endpoint')],
    port: Annotated[int, Field(description='MySQL port')],
    database: Annotated[str, Field(description='database name')] = 'app',
) -> Tuple:
    """Connect to a specific database save the connection internally.

    Args:
        region: region
        database_type: database type (one of 'aurora-mysql', 'mysql', 'mariadb')
        connection_method: connection method (RDS_API, MYSQL_WIRE_PROTOCOL, or MYSQL_WIRE_IAM_PROTOCOL)
        cluster_identifier: cluster identifier
        db_endpoint: database endpoint
        port: database port
        database: database name
    """
    global db_connection_map
    global readonly_query
    global ca_bundle_path

    logger.info(
        f'Enter internal_connect_to_database\n'
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

    # The (engine, method) pair must be one we know how to route. Reject
    # unsupported combinations early with a clear message rather than
    # letting them fail downstream with a confusing error (e.g., trying
    # to use Data API against RDS MariaDB).
    if not is_connection_method_supported(database_type, connection_method):
        raise ValueError(
            f'Connection method {connection_method.value!r} is not supported '
            f'for database type {database_type.value!r}. '
            'Supported pairs: aurora-mysql + (rdsapi | mysqlwire | mysqlwire_iam); '
            'mysql + (mysqlwire | mysqlwire_iam); '
            'mariadb + mysqlwire.'
        )

    # Aurora MySQL is always a cluster; cluster_identifier is required.
    # RDS MySQL / RDS MariaDB can be standalone instances reached by
    # endpoint, so either cluster_identifier or db_endpoint is sufficient.
    if database_type == DatabaseType.AURORA_MYSQL and not cluster_identifier:
        raise ValueError("cluster_identifier can't be none or empty for Aurora MySQL Database")
    if not cluster_identifier and not db_endpoint:
        raise ValueError(
            f'Either cluster_identifier or db_endpoint must be provided '
            f'for database_type={database_type.value!r}'
        )

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

    enable_data_api: bool = False
    masteruser: str = ''
    cluster_arn: str = ''
    secret_arn: str = ''

    if cluster_identifier:
        cluster_properties = internal_get_cluster_properties(
            cluster_identifier=cluster_identifier, region=region
        )

        enable_data_api = cluster_properties.get('HttpEndpointEnabled', False)
        masteruser = cluster_properties.get('MasterUsername', '')
        cluster_arn = cluster_properties.get('DBClusterArn', '')
        secret_arn = cluster_properties.get('MasterUserSecret', {}).get('SecretArn')

        if not db_endpoint:
            db_endpoint = cluster_properties.get('Endpoint', '')
            port = int(cluster_properties.get('Port', ''))
    else:
        instance_properties = internal_get_instance_properties(db_endpoint, region)
        masteruser = instance_properties.get('MasterUsername', '')
        secret_arn = instance_properties.get('MasterUserSecret', {}).get('SecretArn')
        port = int(instance_properties.get('Endpoint', {}).get('Port'))

    logger.info(
        f'About to create internal DB connections with:'
        f'enable_data_api:{enable_data_api}\n'
        f'masteruser:{masteruser}\n'
        f'cluster_arn:{cluster_arn}\n'
        f'secret_arn:{secret_arn}\n'
        f'db_endpoint:{db_endpoint}\n'
        f'port:{port}\n'
        f'region:{region}\n'
        f'readonly:{readonly_query}'
    )

    db_connection = None
    if connection_method == ConnectionMethod.MYSQL_WIRE_IAM_PROTOCOL:
        db_connection = AsyncmyPoolConnection(
            host=db_endpoint,
            port=port,
            database=database,
            readonly=readonly_query,
            # IAM auth flow does not use a Secrets Manager secret; the empty
            # string here disables the secret_arn lookup path inside the
            # connection class. Bandit B106 (hardcoded password) is a false
            # positive: this is an explicit "no secret" sentinel, not a
            # credential value.
            secret_arn='',  # nosec B106
            db_user=masteruser,
            region=region,
            is_iam_auth=True,
            ca_bundle_path=ca_bundle_path,
        )

    elif connection_method == ConnectionMethod.RDS_API:
        db_connection = RDSDataAPIConnection(
            cluster_arn=cluster_arn,
            secret_arn=str(secret_arn),
            database=database,
            region=region,
            readonly=readonly_query,
        )
    else:
        # must be connection_method == ConnectionMethod.MYSQL_WIRE_PROTOCOL
        db_connection = AsyncmyPoolConnection(
            host=db_endpoint,
            port=port,
            database=database,
            readonly=readonly_query,
            secret_arn=secret_arn,
            db_user='',
            region=region,
            is_iam_auth=False,
        )

    if db_connection:
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


def main():
    """Main entry point for the MCP server application.

    Runs the MCP server with CLI argument support for MySQL connections.
    """
    global db_connection_map
    global readonly_query
    global ca_bundle_path

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for MySQL'
    )

    parser.add_argument(
        '--connection_method',
        help='Connection method to the database. It can be RDS_API, MYSQL_WIRE_PROTOCOL OR MYSQL_WIRE_IAM_PROTOCOL)',
    )
    parser.add_argument('--db_cluster_arn', help='ARN of the RDS or Aurora MySQL cluster')
    parser.add_argument(
        '--db_type',
        help=(
            "Database engine. One of 'aurora-mysql' (Aurora MySQL), "
            "'mysql' (RDS MySQL), or 'mariadb' (RDS MariaDB). "
            'Self-hosted MySQL/MariaDB does not require this flag.'
        ),
    )
    parser.add_argument('--db_endpoint', help='Instance endpoint address')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument(
        '--allow_write_query', action='store_true', help='Enforce readonly SQL statements'
    )
    parser.add_argument('--database', help='Database name')
    parser.add_argument('--port', type=int, default=3306, help='Database port (default: 3306)')
    parser.add_argument(
        '--ca_bundle',
        default=None,
        help=(
            'Path to an alternate CA bundle (PEM) for IAM-auth SSL verification. '
            'Overrides the bundled Amazon RDS global bundle shipped with the '
            'package. Use this if you maintain your own trust store or if AWS '
            'rotates CAs faster than the package release cadence.'
        ),
    )
    args = parser.parse_args()

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
    )

    readonly_query = not args.allow_write_query
    ca_bundle_path = args.ca_bundle

    try:
        if args.db_type:
            db_connection: Optional[AbstractDBConnection] = None

            try:
                # Lookup by value, not by member name: users pass
                # 'aurora-mysql' / 'mysql' / 'mariadb', not 'AURORA_MYSQL'.
                parsed_db_type = DatabaseType(args.db_type)
            except ValueError:
                logger.error(
                    f'Invalid --db_type {args.db_type!r}. Expected one of: '
                    f'{", ".join(t.value for t in DatabaseType)}'
                )
                sys.exit(1)

            cluster_identifier = args.db_cluster_arn.split(':')[-1]
            db_connection, llm_response = internal_connect_to_database(
                region=args.region,
                database_type=parsed_db_type,
                connection_method=ConnectionMethod[args.connection_method],
                cluster_identifier=cluster_identifier,
                db_endpoint=args.db_endpoint,
                port=args.port,
                database=args.database,
            )

            if db_connection:
                ctx = DummyCtx()
                response = asyncio.run(
                    run_query(
                        'SELECT 1',
                        ctx,
                        ConnectionMethod[args.connection_method],
                        cluster_identifier,
                        args.db_endpoint,
                        args.database,
                    )
                )
                if (
                    isinstance(response, list)
                    and len(response) == 1
                    and isinstance(response[0], dict)
                    and 'error' in response[0]
                ):
                    logger.error(
                        'Failed to validate database connection to MySQL. Exit the MCP server'
                    )
                    sys.exit(1)
                else:
                    logger.success('Successfully validated database connection to MySQL')

        logger.info('MySQL MCP server started')
        mcp.run()
        logger.info('MySQL MCP server stopped')
    finally:
        db_connection_map.close_all_sync()


if __name__ == '__main__':
    main()
