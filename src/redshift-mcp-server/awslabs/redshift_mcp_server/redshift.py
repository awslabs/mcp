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

"""AWS client management for Redshift MCP Server."""

import asyncio
import boto3
import os
import time
from awslabs.redshift_mcp_server import __version__
from awslabs.redshift_mcp_server.consts import (
    CLIENT_CONNECT_TIMEOUT,
    CLIENT_READ_TIMEOUT,
    CLIENT_RETRIES,
    CLIENT_USER_AGENT_NAME,
    COLUMNS_SQL,
    DATABASES_SQL,
    QUERY_LONG_POLL,
    QUERY_POLL_INTERVAL,
    QUERY_TIMEOUT,
    SCHEMAS_SQL,
    TABLES_SQL,
)
from awslabs.redshift_mcp_server.models import (
    RedshiftCluster,
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftDataModel,
    RedshiftSchema,
    RedshiftTable,
)
from awslabs.redshift_mcp_server.sql_guard import assert_executable
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.mcpserver.exceptions import ToolError
from sqlglot import exp


def _sql_identifier(value: str) -> str:
    """Render a value as a Redshift SQL identifier, safely quoted and escaped."""
    return exp.to_identifier(value, quoted=True).sql(dialect='redshift')


# ClientError codes that indicate missing IAM permissions.
_ACCESS_DENIED = {'AccessDeniedException', 'UnauthorizedAccess', 'AccessDenied'}

# Statement statuses the Data API does not move on from.
_TERMINAL_STATUSES = frozenset({'FINISHED', 'FAILED', 'ABORTED'})

# Tags the connection with an application name.
_APP_NAME_SQL = f"SET application_name TO '{CLIENT_USER_AGENT_NAME}/{__version__}'"


class RedshiftClientManager:
    """Manages AWS clients for Redshift operations."""

    def __init__(
        self, config: Config, aws_region: str | None = None, aws_profile: str | None = None
    ):
        """Initialize the client manager."""
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self._redshift_client = None
        self._redshift_serverless_client = None
        self._redshift_data_client = None
        self._config = config

    def redshift_client(self):
        """Get or create the Redshift client for provisioned clusters."""
        if self._redshift_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_client = session.client('redshift', config=self._config)
                logger.info(
                    f'Created Redshift client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift client: {str(e)}')
                raise

        return self._redshift_client

    def redshift_serverless_client(self):
        """Get or create the Redshift Serverless client."""
        if self._redshift_serverless_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_serverless_client = session.client(
                    'redshift-serverless', config=self._config
                )
                logger.info(
                    f'Created Redshift Serverless client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift Serverless client: {str(e)}')
                raise

        return self._redshift_serverless_client

    def redshift_data_client(self):
        """Get or create the Redshift Data API client."""
        if self._redshift_data_client is None:
            try:
                # Session works with None values - uses default credentials/region chain
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                self._redshift_data_client = session.client('redshift-data', config=self._config)
                logger.info(
                    f'Created Redshift Data API client with profile: {self.aws_profile or "default"}, region: {self.aws_region or "default"}'
                )
            except Exception as e:
                logger.error(f'Error creating Redshift Data API client: {str(e)}')
                raise

        return self._redshift_data_client


async def _resolve_cluster(cluster_identifier: str) -> RedshiftCluster:
    """Resolve a cluster identifier to its discovered cluster.

    Args:
        cluster_identifier: The cluster identifier to resolve.

    Returns:
        The matching RedshiftCluster model.

    Raises:
        ToolError: If no discovered cluster carries that identifier.
    """
    for cluster in await discover_clusters():
        if cluster.identifier == cluster_identifier:
            return cluster

    raise ToolError(
        f'Cluster {cluster_identifier} not found. Please use list_clusters to get valid cluster identifiers.'
    )


async def _execute_protected_statement(
    cluster_identifier: str,
    database_name: str,
    sql: str,
    parameters: list[dict] | None = None,
    enforce_read_only: bool = True,
) -> tuple[dict, str]:
    """Execute one SQL statement against a Redshift cluster in a protected fashion.

    The statement is validated by the SQL guard, then sent as a single batch whose
    surrounding statements depend on `enforce_read_only`:

    Enforced (`enforce_read_only=True`):
        `SET application_name` -> `BEGIN READ ONLY` -> caller SQL -> `ROLLBACK`

    Not enforced (`enforce_read_only=False`):
        `SET application_name` -> caller SQL

    The batch runs with `ExecutionMode=AUTO_COMMIT`, so the Data API adds no transaction of
    its own and the wrapper, where applied, is the only transaction in play. Statements in a
    batch run serially on one connection, so `SET application_name` applies to the statements
    after it and no session is needed to carry it.

    The wrapper is what actually blocks a write: the engine rejects writes the guard's
    deny-list does not enumerate, and the closing `ROLLBACK` discards anything uncommitted.
    It also runs when the caller's statement fails, so a failure cannot leave a transaction
    open.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the statement against.
        sql: The single SQL statement to execute.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
            Only the caller's statement carries placeholders, which the Data API accepts.
        enforce_read_only: Whether to apply read-only protection: the guard's statement-type
            deny-list and the transaction wrapper. Clear it for a caller permitted to write,
            and for this server's own SQL, which it authors and so does not police.
            Single-statement enforcement applies either way.

    Returns:
        Tuple containing:
        - Dictionary with the raw results_response from get_statement_result.
        - String with the query_id of the caller's statement.

    Raises:
        ToolError: If the cluster is unknown, a statement fails, or the batch times out.
    """
    # Validate the statement with the SQL guard before doing any work.
    assert_executable(sql, enforce_read_only=enforce_read_only)

    cluster_info = await _resolve_cluster(cluster_identifier)

    sqls = [_APP_NAME_SQL]
    if enforce_read_only:
        sqls.append('BEGIN READ ONLY')
    caller_index = len(sqls)
    sqls.append(sql)
    if enforce_read_only:
        sqls.append('ROLLBACK')

    batch = await _execute_batch(
        cluster_info=cluster_info,
        cluster_identifier=cluster_identifier,
        database_name=database_name,
        sqls=sqls,
        parameters=parameters,
    )

    sub_statements = batch['SubStatements']

    # One failed statement fails the batch, so a healthy batch means the caller's statement
    # and everything around it ran. A surrounding failure matters as much as the caller's
    # own: a failed BEGIN means the statement was never read-only, and a failed ROLLBACK
    # means what it did may not have been discarded.
    if batch['Status'] != 'FINISHED':
        # A statement that ran and failed carries the engine's message. When the connection
        # itself was refused nothing ran, every statement is ABORTED with a placeholder, and
        # only the batch carries the reason.
        failed = next((sub for sub in sub_statements if sub['Status'] == 'FAILED'), None)
        error = (failed or batch).get('Error', 'Unknown error')
        logger.error(f'Statement failed: {error}')
        raise ToolError(f'Statement failed: {error}')

    caller_statement = sub_statements[caller_index]
    query_id = caller_statement['Id']

    # Only fetch results when the statement produced a result set. SET and DDL do not, and
    # GetStatementResult answers ResourceNotFoundException for them.
    if caller_statement.get('HasResultSet'):
        data_client = client_manager.redshift_data_client()
        results_response = await asyncio.to_thread(data_client.get_statement_result, Id=query_id)
    else:
        results_response = {'Records': [], 'ColumnMetadata': []}

    return results_response, query_id


async def _execute_batch(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    sqls: list[str],
    parameters: list[dict] | None = None,
    query_poll_interval: float = QUERY_POLL_INTERVAL,
    query_timeout: float = QUERY_TIMEOUT,
    query_long_poll: int = QUERY_LONG_POLL,
) -> dict:
    """Run a batch of statements and wait for it to settle.

    Returns the terminal response whatever the outcome, including a failure: only the caller
    knows which statement was its own, so only the caller can turn a failed one into a
    useful message.

    Args:
        cluster_info: Cluster information model.
        cluster_identifier: The cluster identifier.
        database_name: The database name.
        sqls: The statements to run, in order, on one connection.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        query_poll_interval: Polling interval in seconds for checking batch status.
        query_timeout: Maximum time in seconds to wait for the batch to settle.
        query_long_poll: Data API WaitTimeSeconds, 1-30, or 0 to disable long polling.

    Returns:
        The terminal DescribeStatement response, carrying Status and SubStatements.

    Raises:
        ToolError: If the batch does not settle within query_timeout.
    """
    data_client = client_manager.redshift_data_client()

    request_params: dict[str, str | int | list] = {
        'Sqls': sqls,
        'Database': database_name,
        # The Data API's default TRANSACTION mode wraps the whole batch and commits at its
        # end, which would defeat BEGIN READ ONLY and let a write persist. This server runs
        # its own transactions, so it opts out of that wrapper.
        'ExecutionMode': 'AUTO_COMMIT',
    }

    if cluster_info.type == 'provisioned':
        request_params['ClusterIdentifier'] = cluster_identifier
    elif cluster_info.type == 'serverless':
        request_params['WorkgroupName'] = cluster_identifier
    else:
        # Discovery only ever sets 'provisioned' or 'serverless', so reaching this is our
        # bug, not something the caller can act on. Left as a bare exception so the SDK
        # reports it as a crash and logs the traceback.
        raise Exception(f'Unknown cluster type: {cluster_info.type}')

    if parameters:
        request_params['Parameters'] = parameters

    long_poll_params = {'WaitTimeSeconds': query_long_poll} if query_long_poll else {}

    # boto3 is synchronous and a long poll holds the caller for up to query_long_poll
    # seconds, so every Data API call here runs off the event loop.
    response = await asyncio.to_thread(
        data_client.batch_execute_statement, **request_params, **long_poll_params
    )
    statement_id = response['Id']

    logger.debug(f'Executed batch {statement_id} of {len(sqls)} statements')

    # BatchExecuteStatement and DescribeStatement report status alike, so one loop settles
    # the long-polled submit and every later poll. Wall clock, since a long poll blocks
    # server-side.
    deadline = time.monotonic() + query_timeout
    while True:
        if response.get('Status') in _TERMINAL_STATUSES:
            if 'SubStatements' not in response:
                # Only DescribeStatement carries the sub-statement ids, and those ids are
                # the only way to reach one statement's result, so a submit that settled
                # under its own long poll still needs a describe.
                response = await asyncio.to_thread(data_client.describe_statement, Id=statement_id)
            logger.debug(f'Batch settled: {statement_id} ({response["Status"]})')
            return response

        if time.monotonic() >= deadline:
            logger.error(f'Batch timed out: {statement_id}')
            raise ToolError(f'Statement timed out after {query_timeout} seconds')

        await asyncio.sleep(query_poll_interval)

        try:
            response = await asyncio.to_thread(
                data_client.describe_statement, Id=statement_id, **long_poll_params
            )
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') != 'ActiveWaitingRequestsExceededException':
                raise
            logger.warning(f'Long polling limit reached, polling instead: {statement_id}')
            long_poll_params = {}


async def discover_clusters() -> list[RedshiftCluster]:
    """Discover all Redshift clusters and serverless workgroups.

    Discovery is best-effort for each type: if either provisioned or serverless
    discovery succeeds, the function returns whatever was found. It only raises
    if both fail (i.e., no clusters could be discovered at all).

    Returns:
        List of RedshiftCluster models.

    Raises:
        ToolError: If both provisioned and serverless discovery fail.
    """
    clusters = []
    provisioned_error = None
    serverless_error = None

    # Attempt provisioned cluster discovery
    try:
        # Get provisioned clusters
        logger.debug('Discovering provisioned Redshift clusters')
        redshift_client = client_manager.redshift_client()

        paginator = redshift_client.get_paginator('describe_clusters')
        for page in paginator.paginate():
            for cluster in page.get('Clusters', []):
                cluster_info = {
                    'identifier': cluster['ClusterIdentifier'],
                    'type': 'provisioned',
                    'status': cluster['ClusterStatus'],
                    'database_name': cluster.get('DBName', 'dev'),
                    'endpoint': cluster.get('Endpoint', {}).get('Address'),
                    'port': cluster.get('Endpoint', {}).get('Port'),
                    'vpc_id': cluster.get('VpcId'),
                    'node_type': cluster.get('NodeType'),
                    'number_of_nodes': cluster.get('NumberOfNodes'),
                    'creation_time': cluster.get('ClusterCreateTime'),
                    'master_username': cluster.get('MasterUsername'),
                    'publicly_accessible': cluster.get('PubliclyAccessible'),
                    'encrypted': cluster.get('Encrypted'),
                    'tags': {tag['Key']: tag['Value'] for tag in cluster.get('Tags', [])},
                }
                clusters.append(RedshiftCluster(**cluster_info))

        logger.info(f'Found {len(clusters)} provisioned clusters')

    except ClientError as e:
        if e.response.get('Error', {}).get('Code') not in _ACCESS_DENIED:
            raise
        provisioned_error = e
        logger.warning(f'Skipping provisioned; IAM lacks permission: {e}')

    # Attempt serverless workgroup discovery
    try:
        # Get serverless workgroups
        logger.debug('Discovering Redshift Serverless workgroups')
        serverless_client = client_manager.redshift_serverless_client()

        paginator = serverless_client.get_paginator('list_workgroups')
        for page in paginator.paginate():
            for workgroup in page.get('workgroups', []):
                # Get detailed workgroup information
                workgroup_detail = serverless_client.get_workgroup(
                    workgroupName=workgroup['workgroupName']
                )['workgroup']

                cluster_info = {
                    'identifier': workgroup['workgroupName'],
                    'type': 'serverless',
                    'status': workgroup['status'],
                    # Serverless always exposes the built-in 'dev' database. Reporting the
                    # namespace's configured default would require redshift-serverless:GetNamespace;
                    # callers can pass an explicit database_name to the other tools instead.
                    'database_name': 'dev',
                    'endpoint': workgroup_detail.get('endpoint', {}).get('address'),
                    'port': workgroup_detail.get('endpoint', {}).get('port'),
                    'vpc_id': (workgroup_detail.get('subnetIds') or [None])[
                        0
                    ],  # Approximate VPC from subnet
                    'node_type': None,  # Not applicable for serverless
                    'number_of_nodes': None,  # Not applicable for serverless
                    'creation_time': workgroup.get('creationDate'),
                    'master_username': None,  # Serverless uses IAM
                    'publicly_accessible': workgroup_detail.get('publiclyAccessible'),
                    'encrypted': True,  # Serverless is always encrypted
                    'tags': {tag['key']: tag['value'] for tag in workgroup_detail.get('tags', [])},
                }
                clusters.append(RedshiftCluster(**cluster_info))

        serverless_count = len([c for c in clusters if c.type == 'serverless'])
        logger.info(f'Found {serverless_count} serverless workgroups')

    except ClientError as e:
        if e.response.get('Error', {}).get('Code') not in _ACCESS_DENIED:
            raise
        serverless_error = e
        logger.warning(f'Skipping serverless; IAM lacks permission: {e}')

    # If both discovery methods failed, raise an error
    if provisioned_error and serverless_error:
        msg = (
            'Unable to discover any Redshift clusters: IAM lacks both redshift and '
            f'redshift-serverless permissions. Provisioned: {provisioned_error}; '
            f'Serverless: {serverless_error}'
        )
        logger.error(msg)
        raise ToolError(msg)

    logger.info(f'Total clusters discovered: {len(clusters)}')
    return clusters


async def discover_databases(
    cluster_identifier: str, database_name: str = 'dev'
) -> list[RedshiftDatabase]:
    """Discover databases in a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to connect to for querying system views.

    Returns:
        List of RedshiftDatabase models.
    """
    try:
        logger.info(f'Discovering databases in cluster {cluster_identifier}')

        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=DATABASES_SQL,
            # This server's own SQL, so it does not police itself.
            enforce_read_only=False,
        )

        databases = RedshiftDatabase.from_redshift_response(results_response)
        logger.info(f'Found {len(databases)} databases in cluster {cluster_identifier}')
        return databases

    except Exception as e:
        logger.error(f'Error discovering databases in cluster {cluster_identifier}: {str(e)}')
        raise


async def discover_schemas(
    cluster_identifier: str, schema_database_name: str
) -> list[RedshiftSchema]:
    """Discover schemas in a Redshift database using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        schema_database_name: The database name to filter schemas for. Also used to connect to.

    Returns:
        List of RedshiftSchema models.
    """
    try:
        logger.info(
            f'Discovering schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=schema_database_name,
            sql=SCHEMAS_SQL.format(database=_sql_identifier(schema_database_name)),
            enforce_read_only=False,
        )

        schemas = RedshiftSchema.from_redshift_response(results_response)
        logger.info(
            f'Found {len(schemas)} schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )
        return schemas

    except Exception as e:
        logger.error(
            f'Error discovering schemas in database {schema_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def discover_tables(
    cluster_identifier: str, table_database_name: str, table_schema_name: str
) -> list[RedshiftTable]:
    """Discover tables in a Redshift schema using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        table_database_name: The database name to filter tables for. Also used to connect to.
        table_schema_name: The schema name to filter tables for.

    Returns:
        List of RedshiftTable models.
    """
    try:
        logger.info(
            f'Discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=table_database_name,
            sql=TABLES_SQL.format(
                database=_sql_identifier(table_database_name),
                schema=_sql_identifier(table_schema_name),
            ),
            enforce_read_only=False,
        )

        tables = RedshiftTable.from_redshift_response(results_response)
        logger.info(
            f'Found {len(tables)} tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )
        return tables

    except Exception as e:
        logger.error(
            f'Error discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def discover_columns(
    cluster_identifier: str,
    column_database_name: str,
    column_schema_name: str,
    column_table_name: str,
) -> list[RedshiftColumn]:
    """Discover columns in a Redshift table using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        column_database_name: The database name to filter columns for. Also used to connect to.
        column_schema_name: The schema name to filter columns for.
        column_table_name: The table name to filter columns for.

    Returns:
        List of RedshiftColumn models.
    """
    try:
        logger.info(
            f'Discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=column_database_name,
            sql=COLUMNS_SQL.format(
                database=_sql_identifier(column_database_name),
                schema=_sql_identifier(column_schema_name),
                table=_sql_identifier(column_table_name),
            ),
            enforce_read_only=False,
        )

        columns = RedshiftColumn.from_redshift_response(results_response)
        logger.info(
            f'Found {len(columns)} columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )
        return columns

    except Exception as e:
        logger.error(
            f'Error discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def execute_query(
    cluster_identifier: str, database_name: str, sql: str, enforce_read_only: bool = True
) -> dict:
    """Execute a SQL query against a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to execute.
        enforce_read_only: Whether to apply read-only protection. Defaults to True.

    Returns:
        Dictionary with query results including columns, rows, and metadata.
    """
    try:
        logger.info(f'Executing query on cluster {cluster_identifier} in database {database_name}')
        logger.debug(f'SQL: {sql}')

        # Execute the query using the common function
        results_response, query_id = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=sql,
            enforce_read_only=enforce_read_only,
        )

        # Extract column names
        columns = [col.get('name') for col in results_response.get('ColumnMetadata', [])]

        # Extract rows
        rows = [
            [RedshiftDataModel.cell_value(cell) for cell in record]
            for record in results_response.get('Records', [])
        ]

        query_result = {
            'columns': columns,
            'rows': rows,
            'row_count': len(rows),
            'query_id': query_id,
        }

        logger.info(f'Query executed successfully: {query_id}, returned {len(rows)} rows')
        return query_result

    except Exception as e:
        logger.error(f'Error executing query on cluster {cluster_identifier}: {str(e)}')
        raise


# Global client manager instance
client_manager = RedshiftClientManager(
    config=Config(
        connect_timeout=CLIENT_CONNECT_TIMEOUT,
        read_timeout=CLIENT_READ_TIMEOUT,
        retries=CLIENT_RETRIES,
        user_agent_extra=f'md/awslabs#mcp#redshift-mcp-server#{__version__}',
    ),
    aws_region=os.environ.get('AWS_REGION'),
    aws_profile=os.environ.get('AWS_PROFILE'),
)
