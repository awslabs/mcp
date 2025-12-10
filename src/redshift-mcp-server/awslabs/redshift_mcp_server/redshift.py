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
import regex
import time
from awslabs.redshift_mcp_server import __version__
from awslabs.redshift_mcp_server.consts import (
    CLIENT_CONNECT_TIMEOUT,
    CLIENT_READ_TIMEOUT,
    CLIENT_RETRIES,
    CLIENT_USER_AGENT_NAME,
    PG_TABLES_SQL,
    QUERY_POLL_INTERVAL,
    QUERY_TIMEOUT,
    SESSION_KEEPALIVE,
    SUSPICIOUS_QUERY_REGEXP,
    SVV_ALL_COLUMNS_SQL,
    SVV_ALL_SCHEMAS_SQL,
    SVV_ALL_TABLES_SQL,
    SVV_REDSHIFT_DATABASES_SQL,
)
from botocore.config import Config
from loguru import logger


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
        self._session_keepalive = session_keepalive
        self._app_name = app_name

    async def session(
        self, cluster_identifier: str, database_name: str, cluster_info: dict
    ) -> str:
        """Get or create a session for the given cluster and database.

        Args:
            cluster_identifier: The cluster identifier to get session for.
            database_name: The database name to get session for.
            cluster_info: Cluster information dictionary from discover_clusters.

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
        self, cluster_identifier: str, database_name: str, cluster_info: dict
    ) -> str:
        """Create a new session by executing SET application_name.

        Args:
            cluster_identifier: The cluster identifier.
            database_name: The database name.
            cluster_info: Cluster information dictionary.

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

    The SQL is protected by wrapping it in a transaction block with READ ONLY or READ WRITE mode
    based on allow_read_write flag. Transaction breaker protection is implemented
    to prevent unauthorized modifications.

    The SQL execution takes the form:
    1. Get or create session (with SET application_name)
    2. BEGIN [READ ONLY|READ WRITE];
    3. <user sql>
    4. END;

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
    # Get cluster info
    clusters = await discover_clusters()
    cluster_info = None
    for cluster in clusters:
        if cluster['identifier'] == cluster_identifier:
            cluster_info = cluster
            break

    if not cluster_info:
        raise Exception(
            f'Cluster {cluster_identifier} not found. Please use list_clusters to get valid cluster identifiers.'
        )

    # Get session (creates if needed, sets app name automatically)
    session_id = await session_manager.session(cluster_identifier, database_name, cluster_info)

    # Check for suspicious patterns in read-only mode
    if not allow_read_write:
        if regex.compile(SUSPICIOUS_QUERY_REGEXP).search(sql):
            logger.error(f'SQL contains suspicious pattern, execution rejected: {sql}')
            raise Exception(f'SQL contains suspicious pattern, execution rejected: {sql}')

    # Execute BEGIN statement
    begin_sql = 'BEGIN READ WRITE;' if allow_read_write else 'BEGIN READ ONLY;'
    await _execute_statement(
        cluster_info=cluster_info,
        cluster_identifier=cluster_identifier,
        database_name=database_name,
        sql=begin_sql,
        session_id=session_id,
    )

    # Execute user SQL with parameters, ensuring transaction is always closed
    user_query_id = None
    user_sql_error = None

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

    # Always execute END statement to close transaction
    try:
        await _execute_statement(
            cluster_info=cluster_info,
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql='END;',
            session_id=session_id,
        )
    except Exception as end_error:
        logger.error(f'END statement execution failed: {end_error}')
        if user_sql_error:
            # Both failed - raise combined error
            raise Exception(
                f'User SQL failed: {user_sql_error}; END statement failed: {end_error}'
            )
        else:
            # Only END failed
            raise end_error

    # If user SQL failed but END succeeded, raise user SQL error
    if user_sql_error:
        raise user_sql_error

    # Get results from user query
    data_client = client_manager.redshift_data_client()
    assert user_query_id is not None, 'user_query_id should not be None at this point'
    results_response = data_client.get_statement_result(Id=user_query_id)
    return results_response, user_query_id


async def _execute_statement(
    cluster_info: dict,
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
        cluster_info: Cluster information dictionary.
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
        if cluster_info['type'] == 'provisioned':
            request_params['ClusterIdentifier'] = cluster_identifier
        elif cluster_info['type'] == 'serverless':
            request_params['WorkgroupName'] = cluster_identifier
        else:
            raise Exception(f'Unknown cluster type: {cluster_info["type"]}')

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


async def discover_clusters() -> list[dict]:
    """Discover all Redshift clusters and serverless workgroups.

    Returns:
        List of cluster information dictionaries.
    """
    clusters = []

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
                    'database_name': cluster['DBName'],
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
                clusters.append(cluster_info)

        logger.info(f'Found {len(clusters)} provisioned clusters')

    except Exception as e:
        logger.error(f'Error discovering provisioned clusters: {str(e)}')
        raise

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
                    'database_name': workgroup_detail.get('configParameters', [{}])[0].get(
                        'parameterValue', 'dev'
                    ),
                    'endpoint': workgroup_detail.get('endpoint', {}).get('address'),
                    'port': workgroup_detail.get('endpoint', {}).get('port'),
                    'vpc_id': workgroup_detail.get('subnetIds', [None])[
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
                clusters.append(cluster_info)

        serverless_count = len([c for c in clusters if c['type'] == 'serverless'])
        logger.info(f'Found {serverless_count} serverless workgroups')

    except Exception as e:
        logger.error(f'Error discovering serverless workgroups: {str(e)}')
        raise

    logger.info(f'Total clusters discovered: {len(clusters)}')
    return clusters


async def discover_databases(cluster_identifier: str, database_name: str = 'dev') -> list[dict]:
    """Discover databases in a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to connect to for querying system views.

    Returns:
        List of database information dictionaries.
    """
    try:
        logger.info(f'Discovering databases in cluster {cluster_identifier}')

        # Execute the query using the common function
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=SVV_REDSHIFT_DATABASES_SQL,
        )

        databases = []
        records = results_response.get('Records', [])

        for record in records:
            # Extract values from the record
            database_info = {
                'database_name': record[0].get('stringValue'),
                'database_owner': record[1].get('longValue'),
                'database_type': record[2].get('stringValue'),
                'database_acl': record[3].get('stringValue'),
                'database_options': record[4].get('stringValue'),
                'database_isolation_level': record[5].get('stringValue'),
            }
            databases.append(database_info)

        logger.info(f'Found {len(databases)} databases in cluster {cluster_identifier}')
        return databases

    except Exception as e:
        logger.error(f'Error discovering databases in cluster {cluster_identifier}: {str(e)}')
        raise


async def discover_schemas(cluster_identifier: str, schema_database_name: str) -> list[dict]:
    """Discover schemas in a Redshift database using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        schema_database_name: The database name to filter schemas for. Also used to connect to.

    Returns:
        List of schema information dictionaries.
    """
    try:
        logger.info(
            f'Discovering schemas in database {schema_database_name} in cluster {cluster_identifier}'
        )

        # Execute the query using the common function
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=schema_database_name,
            sql=SVV_ALL_SCHEMAS_SQL,
            parameters=[{'name': 'database_name', 'value': schema_database_name}],
        )

        schemas = []
        records = results_response.get('Records', [])

        for record in records:
            # Extract values from the record
            schema_info = {
                'database_name': record[0].get('stringValue'),
                'schema_name': record[1].get('stringValue'),
                'schema_owner': record[2].get('longValue'),
                'schema_type': record[3].get('stringValue'),
                'schema_acl': record[4].get('stringValue'),
                'source_database': record[5].get('stringValue'),
                'schema_option': record[6].get('stringValue'),
            }
            schemas.append(schema_info)

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
) -> list[dict]:
    """Discover tables in a Redshift schema using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        table_database_name: The database name to filter tables for. Also used to connect to.
        table_schema_name: The schema name to filter tables for.

    Returns:
        List of table information dictionaries.
    """
    try:
        logger.info(
            f'Discovering tables in schema {table_schema_name} in database {table_database_name} in cluster {cluster_identifier}'
        )

        # Execute the main tables query
        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=table_database_name,
            sql=SVV_ALL_TABLES_SQL,
            parameters=[
                {'name': 'database_name', 'value': table_database_name},
                {'name': 'schema_name', 'value': table_schema_name},
            ],
        )

        tables = []
        records = results_response.get('Records', [])

        for record in records:
            table_info = {
                'database_name': record[0].get('stringValue'),
                'schema_name': record[1].get('stringValue'),
                'table_name': record[2].get('stringValue'),
                'table_acl': record[3].get('stringValue'),
                'table_type': record[4].get('stringValue'),
                'remarks': record[5].get('stringValue'),
                'external_location': record[6].get('stringValue'),
                'external_parameters': record[7].get('stringValue'),
                # Initialize Redshift-specific fields as None
                'redshift_diststyle': None,
                'redshift_sortkey1': None,
                'redshift_encoded': None,
                'redshift_tbl_rows': None,
                'redshift_size': None,
                'redshift_pct_used': None,
                'redshift_stats_off': None,
                'redshift_skew_rows': None,
            }
            tables.append(table_info)

        # Try to fetch table info separately (may fail on serverless)
        try:
            table_info_response, _ = await _execute_protected_statement(
                cluster_identifier=cluster_identifier,
                database_name=table_database_name,
                sql=PG_TABLES_SQL,
                parameters=[
                    {'name': 'schema_name', 'value': table_schema_name},
                ],
            )

            # Create a lookup dictionary for table info
            # PG_TABLES_SQL returns: schema_name(0), table_name(1), diststyle(2), sortkey1(3),
            # encoded(4), tbl_rows(5), size(6), pct_used(7), stats_off(8), skew_rows(9)
            table_info_map: dict[str, dict[str, str | int | float | None]] = {}
            for record in table_info_response.get('Records', []):
                table_name = record[1].get('stringValue')  # table_name at index 1
                table_info_map[table_name] = {
                    'redshift_diststyle': record[2].get('stringValue'),
                    'redshift_sortkey1': record[3].get('stringValue'),
                    'redshift_encoded': record[4].get('stringValue'),
                    'redshift_tbl_rows': record[5].get('longValue'),
                    'redshift_size': record[6].get('longValue'),
                    'redshift_pct_used': record[7].get('doubleValue'),
                    'redshift_stats_off': record[8].get('doubleValue'),
                    'redshift_skew_rows': record[9].get('doubleValue'),
                }

            # Merge table info into tables
            for table in tables:
                table_name = table['table_name']
                if table_name in table_info_map:
                    table.update(table_info_map[table_name])

            logger.debug(f'Successfully enriched {len(table_info_map)} tables with pg_tables data')

        except Exception as table_info_error:
            logger.warning(
                f'Could not fetch pg_tables (may not be supported on serverless): {table_info_error}'
            )
            # Continue without table info - tables already have None values

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
) -> list[dict]:
    """Discover columns in a Redshift table using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        column_database_name: The database name to filter columns for. Also used to connect to.
        column_schema_name: The schema name to filter columns for.
        column_table_name: The table name to filter columns for.

    Returns:
        List of column information dictionaries.
    """
    try:
        logger.info(
            f'Discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )

        results_response, _ = await _execute_protected_statement(
            cluster_identifier=cluster_identifier,
            database_name=column_database_name,
            sql=SVV_ALL_COLUMNS_SQL,
            parameters=[
                {'name': 'database_name', 'value': column_database_name},
                {'name': 'schema_name', 'value': column_schema_name},
                {'name': 'table_name', 'value': column_table_name},
            ],
        )

        columns = []
        records = results_response.get('Records', [])

        for record in records:
            column_info = {
                'database_name': record[0].get('stringValue'),
                'schema_name': record[1].get('stringValue'),
                'table_name': record[2].get('stringValue'),
                'column_name': record[3].get('stringValue'),
                'ordinal_position': record[4].get('longValue'),
                'column_default': record[5].get('stringValue'),
                'is_nullable': record[6].get('stringValue'),
                'data_type': record[7].get('stringValue'),
                'character_maximum_length': record[8].get('longValue'),
                'numeric_precision': record[9].get('longValue'),
                'numeric_scale': record[10].get('longValue'),
                'remarks': record[11].get('stringValue'),
                'redshift_encoding': record[12].get('stringValue'),
                'redshift_distkey': record[13].get('booleanValue'),
                'redshift_sortkey': record[14].get('longValue'),
                'external_type': record[15].get('stringValue'),
                'external_part_key': record[16].get('longValue'),
            }
            columns.append(column_info)

        logger.info(
            f'Found {len(columns)} columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}'
        )
        return columns

    except Exception as e:
        logger.error(
            f'Error discovering columns in table {column_table_name} in schema {column_schema_name} in database {column_database_name} in cluster {cluster_identifier}: {str(e)}'
        )
        raise


async def execute_query(cluster_identifier: str, database_name: str, sql: str) -> dict:
    """Execute a SQL query against a Redshift cluster using the Data API.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to execute.

    Returns:
        Dictionary with query results including columns, rows, and metadata.
    """
    try:
        logger.info(f'Executing query on cluster {cluster_identifier} in database {database_name}')
        logger.debug(f'SQL: {sql}')

        # Record start time for execution time calculation
        import time

        start_time = time.time()

        # Execute the query using the common function
        results_response, query_id = await _execute_protected_statement(
            cluster_identifier=cluster_identifier, database_name=database_name, sql=sql
        )

        # Calculate execution time
        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)

        # Extract column names
        columns = []
        column_metadata = results_response.get('ColumnMetadata', [])
        for col_meta in column_metadata:
            columns.append(col_meta.get('name'))

        # Extract rows
        rows = []
        records = results_response.get('Records', [])

        for record in records:
            row = []
            for field in record:
                # Extract the actual value from the field based on its type
                if 'stringValue' in field:
                    row.append(field['stringValue'])
                elif 'longValue' in field:
                    row.append(field['longValue'])
                elif 'doubleValue' in field:
                    row.append(field['doubleValue'])
                elif 'booleanValue' in field:
                    row.append(field['booleanValue'])
                elif 'isNull' in field and field['isNull']:
                    row.append(None)
                else:
                    # Fallback for unknown field types
                    row.append(str(field))
            rows.append(row)

        query_result = {
            'columns': columns,
            'rows': rows,
            'row_count': len(rows),
            'execution_time_ms': execution_time_ms,
            'query_id': query_id,
        }

        logger.info(
            f'Query executed successfully: {query_id}, returned {len(rows)} rows in {execution_time_ms}ms'
        )
        return query_result

    except Exception as e:
        logger.error(f'Error executing query on cluster {cluster_identifier}: {str(e)}')
        raise


def _parse_explain_verbose(explain_lines: list[str]) -> tuple[list[dict], str]:
    """Parse EXPLAIN VERBOSE output tree structure into structured plan nodes.

    Parses the verbose tree format with :node_id, :parent_id, :startup_cost, etc.
    Also extracts the human-readable plan text at the end.

    Args:
        explain_lines: List of text lines from EXPLAIN VERBOSE output

    Returns:
        Tuple of (list of node dictionaries, human-readable plan text)
    """
    import re

    nodes = {}
    current_node: dict[str, str | int | float | None] | None = None
    human_readable_lines = []
    in_human_readable = False

    # Operation type mapping from verbose format
    operation_map = {
        'LIMIT': 'Limit',
        'MERGE': 'Merge',
        'NETWORK': 'Network',
        'SORT': 'Sort',
        'AGG': 'Aggregate',
        'HASHJOIN': 'Hash Join',
        'MERGEJOIN': 'Merge Join',
        'NESTLOOP': 'Nested Loop',
        'SEQSCAN': 'Seq Scan',
        'HASH': 'Hash',
        'SUBQUERYSCAN': 'Subquery Scan',
        'APPEND': 'Append',
        'RESULT': 'Result',
        'UNIQUE': 'Unique',
        'SETOP': 'SetOp',
        'WINDOW': 'Window',
        'MATERIALIZE': 'Materialize',
        'CTESCAN': 'CTE Scan',
        'FUNCTIONSCAN': 'Function Scan',
        'GROUP': 'Group',
        'INDEXSCAN': 'Index Scan',
        'METADATAHASH': 'Metadata Hash',
        'METADATALOOP': 'Metadata Loop',
        'PADBTBLUDFSOURCESCAN': 'Table Function Data Source',
        'PADBTBLUDFXFORMSCAN': 'Table Function Data Transform',
        'PARTITIONLOOP': 'Partition Loop',
        'TIDSCAN': 'Tid Scan',
        'UNNEST': 'Unnest',
    }

    for line in explain_lines:
        # Detect empty line separator between verbose tree and human-readable plan
        if not line.strip():
            if not in_human_readable and nodes:
                in_human_readable = True
            continue

        if in_human_readable:
            human_readable_lines.append(line)
            continue

        stripped = line.strip()

        # Parse verbose tree structure
        op_match = re.match(r'\{\s*(\w+)\s*$', stripped)
        if op_match:
            op_type = op_match.group(1)
            current_node = {
                'operation': operation_map.get(op_type, op_type.title()),
            }
            continue

        if current_node is None:
            continue

        # Parse node properties
        if stripped.startswith(':node_id'):
            match = re.search(r':node_id\s+(\d+)', stripped)
            if match:
                current_node['node_id'] = int(match.group(1))

        elif stripped.startswith(':parent_id'):
            match = re.search(r':parent_id\s+(\d+)', stripped)
            if match:
                parent_id = int(match.group(1))
                current_node['parent_node_id'] = parent_id if parent_id > 0 else None

        elif stripped.startswith(':startup_cost'):
            match = re.search(r':startup_cost\s+([\d.]+)', stripped)
            if match:
                current_node['cost_startup'] = float(match.group(1))

        elif stripped.startswith(':total_cost'):
            match = re.search(r':total_cost\s+([\d.]+)', stripped)
            if match:
                current_node['cost_total'] = float(match.group(1))

        elif stripped.startswith(':plan_rows'):
            match = re.search(r':plan_rows\s+(\d+)', stripped)
            if match:
                current_node['rows'] = int(match.group(1))

        elif stripped.startswith(':plan_width'):
            match = re.search(r':plan_width\s+(\d+)', stripped)
            if match:
                current_node['width'] = int(match.group(1))

        elif stripped.startswith(':dist_info.dist_strategy'):
            match = re.search(r':dist_info\.dist_strategy\s+(\S+)', stripped)
            if match:
                dist_strategy = match.group(1)
                if dist_strategy not in ('DS_DIST_ERR', '<>'):
                    current_node['distribution_type'] = dist_strategy

        elif stripped.startswith(':scanrelid'):
            match = re.search(r':scanrelid\s+(\d+)', stripped)
            if match:
                current_node['scan_relid'] = int(match.group(1))

        elif stripped.startswith(':jointype'):
            match = re.search(r':jointype\s+(\d+)', stripped)
            if match:
                join_types = {0: 'Inner', 1: 'Left', 2: 'Full', 3: 'Right', 4: 'Semi', 5: 'Anti'}
                current_node['join_type'] = join_types.get(int(match.group(1)), 'Unknown')

        elif stripped.startswith(':aggstrategy'):
            match = re.search(r':aggstrategy\s+(\d+)', stripped)
            if match:
                agg_strategies = {0: 'Plain', 1: 'Sorted', 2: 'Hashed'}
                current_node['agg_strategy'] = agg_strategies.get(int(match.group(1)), 'Unknown')

        elif stripped.startswith(':dataMovement'):
            match = re.search(r':dataMovement\s+(.+)', stripped)
            if match:
                current_node['data_movement'] = match.group(1).strip()

        elif stripped.startswith(':table'):
            match = re.search(r':table\s+"?([^"\s]+)"?', stripped)
            if match:
                current_node['relation_name'] = match.group(1).strip()

        if 'node_id' in current_node and current_node['node_id'] not in nodes:
            nodes[current_node['node_id']] = current_node

    result_nodes = []
    for node_id in sorted(nodes.keys()):
        node = nodes[node_id]
        # Calculate level based on parent chain
        level = 0
        parent_id = node.get('parent_node_id')
        visited = set()
        while parent_id is not None and parent_id in nodes and parent_id not in visited:
            visited.add(parent_id)
            level += 1
            parent_id = nodes[parent_id].get('parent_node_id')
        node['level'] = level
        result_nodes.append(node)

    human_readable_plan = '\n'.join(human_readable_lines)
    return result_nodes, human_readable_plan


def _generate_performance_suggestions(
    parsed_nodes: list[dict], table_designs: list[dict]
) -> list[str]:
    """Generate performance optimization suggestions based on execution plan analysis.

    Args:
        parsed_nodes: List of parsed execution plan nodes.
        table_designs: List of table design information dictionaries.

    Returns:
        List of performance suggestion strings.
    """
    suggestions = []

    # Analyze distribution strategies in plan nodes
    for node in parsed_nodes:
        dist_type = node.get('distribution_type')
        operation = node.get('operation', '')

        # Check for data redistribution (expensive operations)
        if dist_type == 'DS_BCAST_INNER':
            suggestions.append(
                f'Data broadcast detected in {operation}. Consider using a common DISTKEY '
                'on join columns to co-locate data and avoid broadcasting.'
            )
        elif dist_type == 'DS_DIST_INNER':
            suggestions.append(
                f'Data redistribution detected in {operation}. Review DISTKEY choices '
                'to ensure joined tables are distributed on the join column.'
            )
        elif dist_type == 'DS_DIST_ALL_INNER':
            suggestions.append(
                f'Full table redistribution in {operation}. Consider DISTSTYLE ALL '
                'for small dimension tables or align DISTKEYs for large tables.'
            )

        # Check for nested loops (often indicates missing join condition or small table)
        if 'Nested Loop' in operation:
            suggestions.append(
                'Nested Loop join detected. Verify join conditions are correct. '
                'For large tables, Hash Join or Merge Join are typically more efficient.'
            )

    # Analyze table designs
    for table in table_designs:
        schema_name = table.get('schema_name', '')
        table_name = table.get('table_name', '')
        redshift_diststyle = table.get('redshift_diststyle', '')
        columns = table.get('columns', [])

        full_name = f'{schema_name}.{table_name}' if schema_name else table_name

        # Check for EVEN distribution on large tables (may cause redistribution)
        if redshift_diststyle == 'EVEN':
            suggestions.append(
                f'Table {full_name} uses EVEN distribution. If this table is frequently '
                'joined, consider using DISTKEY on the join column to improve performance.'
            )

        # Check for missing sort keys
        has_sortkey = any(col.get('redshift_sortkey', 0) > 0 for col in columns)
        if not has_sortkey and columns:
            suggestions.append(
                f'Table {full_name} has no SORTKEY defined. Adding a SORTKEY on '
                'frequently filtered or joined columns can improve query performance.'
            )

        # Check for RAW encoding (no compression)
        raw_columns = [
            col['column_name'] for col in columns if col.get('redshift_encoding') == 'none'
        ]
        if raw_columns and len(raw_columns) <= 3:
            suggestions.append(
                f'Columns {", ".join(raw_columns)} in {full_name} have no compression. '
                'Consider using ENCODE AUTO or specific encodings to reduce storage and improve I/O.'
            )
        elif raw_columns:
            suggestions.append(
                f'{len(raw_columns)} columns in {full_name} have no compression. '
                'Consider using ENCODE AUTO to improve storage efficiency.'
            )

    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique_suggestions.append(s)

    return unique_suggestions


async def describe_execution_plan(cluster_identifier: str, database_name: str, sql: str) -> dict:
    """Get the execution plan for a SQL query using EXPLAIN VERBOSE.

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to explain.

    Returns:
        Dictionary with execution plan details including structured nodes.
    """
    try:
        logger.info(
            f'Getting execution plan for query on cluster {cluster_identifier} in database {database_name}'
        )
        logger.debug(f'SQL to explain: {sql}')

        # Check if SQL already starts with EXPLAIN
        sql_trimmed = sql.strip().upper()
        if sql_trimmed.startswith('EXPLAIN'):
            raise Exception(
                'SQL already contains EXPLAIN. Please provide the query without EXPLAIN.'
            )

        explain_sql = f'EXPLAIN VERBOSE {sql}'

        start_time = time.time()

        results_response, query_id = await _execute_protected_statement(
            cluster_identifier=cluster_identifier, database_name=database_name, sql=explain_sql
        )

        end_time = time.time()
        planning_time_ms = int((end_time - start_time) * 1000)

        plan_lines = []
        records = results_response.get('Records', [])

        for record in records:
            if record and len(record) > 0:
                line = record[0].get('stringValue', '')
                plan_lines.append(line)

        parsed_nodes, human_readable_plan = _parse_explain_verbose(plan_lines)

        # Extract unique table references from parsed nodes (verbose tree)
        table_refs = set()

        # Method 1: Extract from parsed nodes (verbose tree has :table attribute)
        for node in parsed_nodes:
            relation_name = node.get('relation_name')
            if relation_name:
                # Verbose output only includes table name, not schema
                # Check if it's schema.table format
                if '.' in relation_name:
                    parts = relation_name.split('.', 1)
                    schema_name, table_name = parts[0], parts[1]
                else:
                    # Default to public schema if not specified
                    schema_name, table_name = 'public', relation_name
                table_refs.add((schema_name, table_name))

        # Method 2: Fallback - extract from human-readable plan for schema.table references
        # This catches cases where schema is explicitly mentioned
        import re

        for match in re.finditer(
            r'\bon\s+([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)', human_readable_plan
        ):
            relation_name = match.group(1)
            parts = relation_name.split('.', 1)
            schema_name, table_name = parts[0], parts[1]
            table_refs.add((schema_name, table_name))

        table_designs = []
        for schema_name, table_name in table_refs:
            try:
                tables = await discover_tables(
                    cluster_identifier=cluster_identifier,
                    table_database_name=database_name,
                    table_schema_name=schema_name,
                )

                # Find the specific table
                table_info = next((t for t in tables if t['table_name'] == table_name), None)
                if not table_info:
                    logger.warning(
                        f'Table {schema_name}.{table_name} not found in discover_tables'
                    )
                    continue

                # Get column info including design properties
                columns = await discover_columns(
                    cluster_identifier=cluster_identifier,
                    column_database_name=database_name,
                    column_schema_name=schema_name,
                    column_table_name=table_name,
                )

                table_design = {
                    'database_name': database_name,
                    'schema_name': schema_name,
                    'table_name': table_name,
                    'redshift_diststyle': table_info.get('redshift_diststyle'),
                    'redshift_sortkey1': table_info.get('redshift_sortkey1'),
                    'external_location': table_info.get('external_location'),
                    'external_parameters': table_info.get('external_parameters'),
                    'columns': columns,
                }
                table_designs.append(table_design)

                logger.debug(
                    f'Fetched design for {schema_name}.{table_name}: '
                    f'{table_info.get("redshift_diststyle")} with {len(columns)} columns'
                )

            except Exception as e:
                logger.warning(f'Error fetching design for {schema_name}.{table_name}: {str(e)}')
                continue

        suggestions = _generate_performance_suggestions(parsed_nodes, table_designs)

        plan_lines_list = [line for line in human_readable_plan.split('\n') if line.strip()]
        plan_line_count = len(plan_lines_list)

        # If plan is small, include it directly; otherwise, add a prompt
        if plan_line_count < 30:
            final_human_readable_plan = human_readable_plan
        else:
            final_human_readable_plan = (
                f'[Plan has {plan_line_count} lines - too large to display inline]\n\n'
                f'The execution plan is large. Would you like to see the full human-readable plan?\n'
                f'If yes, I can show you the complete {plan_line_count}-line execution plan.'
            )

        execution_plan = {
            'query_id': query_id,
            'explained_query': sql,
            'planning_time_ms': planning_time_ms,
            'plan_nodes': parsed_nodes,
            'table_designs': table_designs,
            'human_readable_plan': final_human_readable_plan,
            'suggestions': suggestions,
        }

        logger.info(
            f'Execution plan generated successfully: {query_id}, '
            f'{len(parsed_nodes)} nodes, {len(table_designs)} table designs, '
            f'{len(suggestions)} suggestions in {planning_time_ms}ms'
        )
        return execution_plan

    except Exception as e:
        logger.error(f'Error getting execution plan for cluster {cluster_identifier}: {str(e)}')
        raise


# Global client manager instance
client_manager = RedshiftClientManager(
    config=Config(
        connect_timeout=CLIENT_CONNECT_TIMEOUT,
        read_timeout=CLIENT_READ_TIMEOUT,
        retries=CLIENT_RETRIES,
        user_agent_extra=f'{CLIENT_USER_AGENT_NAME}/{__version__}',
    ),
    aws_region=os.environ.get('AWS_REGION'),
    aws_profile=os.environ.get('AWS_PROFILE'),
)

# Global session manager instance
session_manager = RedshiftSessionManager(
    session_keepalive=SESSION_KEEPALIVE, app_name=f'{CLIENT_USER_AGENT_NAME}/{__version__}'
)
