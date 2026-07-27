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
    QUERY_POLL_INTERVAL,
    QUERY_TIMEOUT,
    SCHEMAS_SQL,
    SESSION_KEEPALIVE,
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
from sqlglot import exp


def _sql_identifier(value: str) -> str:
    """Render a value as a Redshift SQL identifier, safely quoted and escaped."""
    return exp.to_identifier(value, quoted=True).sql(dialect='redshift')


# ClientError codes that indicate missing IAM permissions.
_ACCESS_DENIED = {'AccessDeniedException', 'UnauthorizedAccess', 'AccessDenied'}


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


class RedshiftSessionManager:
    """Manages Redshift Data API sessions for connection reuse."""

    def __init__(self, session_keepalive: int, app_name: str):
        """Initialize the session manager.

        Args:
            session_keepalive: Session keepalive timeout in seconds.
            app_name: Application name to set in sessions.
        """
        self._sessions = {}  # {cluster:database -> session_info}
        self._locks: dict[str, asyncio.Lock] = {}  # {cluster:database -> asyncio.Lock}
        self._session_keepalive = session_keepalive
        self._app_name = app_name

    def lock(self, cluster_identifier: str, database_name: str) -> asyncio.Lock:
        """Get or create the per cluster:database lock that serializes session use.

        Args:
            cluster_identifier: The cluster identifier to lock on.
            database_name: The database name to lock on.

        Returns:
            The asyncio.Lock for the cluster:database, created lazily on first use.
        """
        key = f'{cluster_identifier}:{database_name}'
        # No await between the get and set, so lazy creation is race-free on the event loop.
        existing = self._locks.get(key)
        if existing is None:
            existing = asyncio.Lock()
            self._locks[key] = existing
        return existing

    async def session(
        self, cluster_identifier: str, database_name: str, cluster_info: RedshiftCluster
    ) -> str:
        """Get or create a session for the given cluster and database.

        Args:
            cluster_identifier: The cluster identifier to get session for.
            database_name: The database name to get session for.
            cluster_info: Cluster information model from discover_clusters.

        Returns:
            Session ID for use in ExecuteStatement calls.
        """
        # Check existing session
        session_key = f'{cluster_identifier}:{database_name}'
        if session_key in self._sessions:
            session_info = self._sessions[session_key]
            if not self._is_session_expired(session_info):
                logger.debug(f'Reusing existing session: {session_info["session_id"]}')
                return session_info['session_id']
            else:
                logger.debug(f'Session expired, removing: {session_info["session_id"]}')
                del self._sessions[session_key]

        # Create new session with application name
        session_id = await self._create_session_with_app_name(
            cluster_identifier, database_name, cluster_info
        )

        # Store session
        self._sessions[session_key] = {'session_id': session_id, 'created_at': time.time()}

        logger.info(f'Created new session: {session_id} for {cluster_identifier}:{database_name}')
        return session_id

    async def _create_session_with_app_name(
        self, cluster_identifier: str, database_name: str, cluster_info: RedshiftCluster
    ) -> str:
        """Create a new session by executing SET application_name.

        Args:
            cluster_identifier: The cluster identifier.
            database_name: The database name.
            cluster_info: Cluster information model.

        Returns:
            Session ID from the ExecuteStatement response.
        """
        # Set application name to create session
        app_name_sql = f"SET application_name TO '{self._app_name}';"

        # Execute statement to create session
        statement_id = await _execute_statement(
            cluster_info=cluster_info,
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=app_name_sql,
            session_keepalive=self._session_keepalive,
        )

        # Get session ID from the response
        data_client = client_manager.redshift_data_client()
        status_response = data_client.describe_statement(Id=statement_id)
        session_id = status_response['SessionId']

        logger.debug(f'Created session with application name: {session_id}')
        return session_id

    def _is_session_expired(self, session_info: dict) -> bool:
        """Check if a session has expired based on keepalive timeout.

        Args:
            session_info: Session information dictionary.

        Returns:
            True if session is expired, False otherwise.
        """
        return (time.time() - session_info['created_at']) > self._session_keepalive


async def _execute_protected_statement(
    cluster_identifier: str,
    database_name: str,
    sql: str,
    parameters: list[dict] | None = None,
    allow_read_write: bool = False,
) -> tuple[dict, str]:
    """Execute a SQL statement against a Redshift cluster in a protected fashion.

    The SQL is first validated by the read-only guard (single-statement enforcement,
    plus the statement-type deny-list in read-only mode), then executed per the
    allow_read_write flag:

    Read-only (allow_read_write=False):
    1. Get or create session (with SET application_name).
    2. BEGIN READ ONLY;
    3. <user sql>
    4. ROLLBACK;  (always, so nothing is persisted and non-deny-listed writes are blocked)

    Read-write (allow_read_write=True):
    1. Get or create session (with SET application_name).
    2. <user sql>  (run directly/autocommit, with no transaction wrapper so that
       non-transactional statements such as VACUUM or CREATE DATABASE are not broken)

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to execute.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        allow_read_write: Indicates if read-write mode should be activated.

    Returns:
        Tuple containing:
        - Dictionary with the raw results_response from get_statement_result.
        - String with the query_id.

    Raises:
        Exception: If cluster not found, query fails, or times out.
    """
    # Validate the statement with the read-only guard before doing any work.
    assert_executable(sql, allow_read_write=allow_read_write)

    # Get cluster info
    clusters = await discover_clusters()
    cluster_info = None
    for cluster in clusters:
        if cluster.identifier == cluster_identifier:
            cluster_info = cluster
            break

    if not cluster_info:
        raise Exception(
            f'Cluster {cluster_identifier} not found. Please use list_clusters to get valid cluster identifiers.'
        )

    # Serialize work on the shared per cluster:database session.
    async with session_manager.lock(cluster_identifier, database_name):
        session_id = await session_manager.session(cluster_identifier, database_name, cluster_info)

        if allow_read_write:
            # Read-write: run the single guarded statement directly (autocommit). No
            # transaction wrapper. Any error propagates.
            user_query_id = await _execute_statement(
                cluster_info=cluster_info,
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                sql=sql,
                parameters=parameters,
                session_id=session_id,
            )
        else:
            # Read-only: BEGIN READ ONLY ... ROLLBACK. The engine rejects data writes
            # the deny-list does not enumerate; ROLLBACK discards anything uncommitted.
            await _execute_statement(
                cluster_info=cluster_info,
                cluster_identifier=cluster_identifier,
                database_name=database_name,
                sql='BEGIN READ ONLY;',
                session_id=session_id,
            )

            # Execute user SQL with parameters, ensuring the transaction is always closed.
            user_query_id = None
            user_sql_error: Exception | None = None

            try:
                user_query_id = await _execute_statement(
                    cluster_info=cluster_info,
                    cluster_identifier=cluster_identifier,
                    database_name=database_name,
                    sql=sql,
                    parameters=parameters,
                    session_id=session_id,
                )
            except Exception as e:
                user_sql_error = e
                logger.error(f'User SQL execution failed: {e}')
            finally:
                # Always close the read-only transaction with ROLLBACK, even on
                # CancelledError / BaseException.
                try:
                    await _execute_statement(
                        cluster_info=cluster_info,
                        cluster_identifier=cluster_identifier,
                        database_name=database_name,
                        sql='ROLLBACK;',
                        session_id=session_id,
                    )
                except Exception as close_error:
                    logger.error(f'ROLLBACK statement execution failed: {close_error}')
                    if user_sql_error is not None:
                        # Both failed - raise combined error
                        raise Exception(
                            f'User SQL failed: {user_sql_error}; '
                            f'ROLLBACK statement failed: {close_error}'
                        ) from close_error
                    raise

            # If user SQL failed but the ROLLBACK succeeded, raise the user SQL error.
            if user_sql_error is not None:
                raise user_sql_error

    # Get results from user query (shared by both modes); runs outside the lock.
    # describe_statement / get_statement_result are keyed by query_id, not session-bound,
    # so the lock is not held during the (potentially unbounded) results wait.
    data_client = client_manager.redshift_data_client()
    assert user_query_id is not None, 'user_query_id should not be None at this point'

    # Only fetch results when the statement produced a result set (e.g. SET does not).
    describe_response = data_client.describe_statement(Id=user_query_id)
    if describe_response.get('HasResultSet'):
        results_response = data_client.get_statement_result(Id=user_query_id)
    else:
        results_response = {'Records': [], 'ColumnMetadata': []}
    return results_response, user_query_id


async def _execute_statement(
    cluster_info: RedshiftCluster,
    cluster_identifier: str,
    database_name: str,
    sql: str,
    parameters: list[dict] | None = None,
    session_id: str | None = None,
    session_keepalive: int | None = None,
    query_poll_interval: float = QUERY_POLL_INTERVAL,
    query_timeout: float = QUERY_TIMEOUT,
) -> str:
    """Execute a single statement with optional session support and parameters.

    Args:
        cluster_info: Cluster information model.
        cluster_identifier: The cluster identifier.
        database_name: The database name.
        sql: The SQL statement to execute.
        parameters: Optional list of parameter dictionaries with 'name' and 'value' keys.
        session_id: Optional session ID to use.
        session_keepalive: Optional session keepalive seconds (only used when session_id is None).
        query_poll_interval: Polling interval in seconds for checking query status.
        query_timeout: Maximum time in seconds to wait for query completion.

    Returns:
        Statement ID from the ExecuteStatement response.
    """
    data_client = client_manager.redshift_data_client()

    # Build request parameters
    request_params: dict[str, str | int | list[dict]] = {'Sql': sql}

    # Add database and cluster/workgroup identifier only if not using session
    if not session_id:
        request_params['Database'] = database_name
        if cluster_info.type == 'provisioned':
            request_params['ClusterIdentifier'] = cluster_identifier
        elif cluster_info.type == 'serverless':
            request_params['WorkgroupName'] = cluster_identifier
        else:
            raise Exception(f'Unknown cluster type: {cluster_info.type}')

    # Add parameters if provided
    if parameters:
        request_params['Parameters'] = parameters

    # Add session ID if provided, otherwise add session keepalive
    if session_id:
        request_params['SessionId'] = session_id
    elif session_keepalive is not None:
        request_params['SessionKeepAliveSeconds'] = session_keepalive

    response = data_client.execute_statement(**request_params)
    statement_id = response['Id']

    logger.debug(
        f'Executed statement: {statement_id}' + (f' in session {session_id}' if session_id else '')
    )

    # Wait for statement completion
    wait_time = 0
    while wait_time < query_timeout:
        status_response = data_client.describe_statement(Id=statement_id)
        status = status_response['Status']

        if status == 'FINISHED':
            logger.debug(f'Statement completed: {statement_id}')
            break
        elif status in ['FAILED', 'ABORTED']:
            error_msg = status_response.get('Error', 'Unknown error')
            logger.error(f'Statement failed: {error_msg}')
            raise Exception(f'Statement failed: {error_msg}')

        await asyncio.sleep(query_poll_interval)
        wait_time += query_poll_interval

    if wait_time >= query_timeout:
        logger.error(f'Statement timed out: {statement_id}')
        raise Exception(f'Statement timed out after {wait_time} seconds')

    return statement_id


async def discover_clusters() -> list[RedshiftCluster]:
    """Discover all Redshift clusters and serverless workgroups.

    Discovery is best-effort for each type: if either provisioned or serverless
    discovery succeeds, the function returns whatever was found. It only raises
    if both fail (i.e., no clusters could be discovered at all).

    Returns:
        List of RedshiftCluster models.

    Raises:
        Exception: If both provisioned and serverless discovery fail.
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
        raise PermissionError(msg)

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
    cluster_identifier: str, database_name: str, sql: str, allow_read_write: bool = False
) -> dict:
    """Execute a SQL query against a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to execute.
        allow_read_write: Whether to use a read-write transaction. Defaults to False (read-only).

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
            allow_read_write=allow_read_write,
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

# Global session manager instance
session_manager = RedshiftSessionManager(
    session_keepalive=SESSION_KEEPALIVE, app_name=f'{CLIENT_USER_AGENT_NAME}/{__version__}'
)
