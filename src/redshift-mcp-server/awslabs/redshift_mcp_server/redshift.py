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
from awslabs.redshift_mcp_server.consts import (
    CLIENT_TIMEOUT,
    DEFAULT_AWS_REGION,
    QUERY_POLL_INTERVAL,
    QUERY_TIMEOUT,
    SUSPICIOUS_QUERY_REGEXP,
    SVV_ALL_COLUMNS_QUERY,
    SVV_ALL_SCHEMAS_QUERY,
    SVV_ALL_TABLES_QUERY,
    SVV_REDSHIFT_DATABASES_QUERY,
)
from botocore.config import Config
from loguru import logger
from typing import Any, Optional


class RedshiftClientManager:
    """Manages AWS clients for Redshift operations."""

    def __init__(self):
        """Initialize the client manager."""
        self.aws_region = os.environ.get('AWS_REGION', DEFAULT_AWS_REGION)
        self.aws_profile = os.environ.get('AWS_PROFILE')
        self._redshift_client: Optional[boto3.client] = None
        self._redshift_serverless_client: Optional[boto3.client] = None
        self._redshift_data_client: Optional[boto3.client] = None

        # Configure boto3 with timeouts
        self._config = Config(
            # region_name=self.aws_region,
            connect_timeout=CLIENT_TIMEOUT,
            read_timeout=CLIENT_TIMEOUT,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
        )

    def redshift_client(self) -> boto3.client:
        """Get or create the Redshift client for provisioned clusters."""
        if self._redshift_client is None:
            try:
                if self.aws_profile:
                    session = boto3.Session(profile_name=self.aws_profile)
                    self._redshift_client = session.client('redshift', config=self._config)
                    logger.info(f'Created Redshift client with profile: {self.aws_profile}')
                else:
                    self._redshift_client = boto3.client(
                        'redshift', config=self._config, region_name=self.aws_region
                    )
                    logger.info('Created Redshift client with default credentials')
            except Exception as e:
                logger.error(f'Error creating Redshift client: {str(e)}')
                raise

        return self._redshift_client

    def redshift_serverless_client(self) -> boto3.client:
        """Get or create the Redshift Serverless client."""
        if self._redshift_serverless_client is None:
            try:
                if self.aws_profile:
                    session = boto3.Session(profile_name=self.aws_profile)
                    self._redshift_serverless_client = session.client(
                        'redshift-serverless', config=self._config
                    )
                    logger.info(
                        f'Created Redshift Serverless client with profile: {self.aws_profile}'
                    )
                else:
                    self._redshift_serverless_client = boto3.client(
                        'redshift-serverless', config=self._config, region_name=self.aws_region
                    )
                    logger.info('Created Redshift Serverless client with default credentials')
            except Exception as e:
                logger.error(f'Error creating Redshift Serverless client: {str(e)}')
                raise

        return self._redshift_serverless_client

    def redshift_data_client(self) -> boto3.client:
        """Get or create the Redshift Data API client."""
        if self._redshift_data_client is None:
            try:
                if self.aws_profile:
                    session = boto3.Session(profile_name=self.aws_profile)
                    self._redshift_data_client = session.client(
                        'redshift-data', config=self._config
                    )
                    logger.info(
                        f'Created Redshift Data API client with profile: {self.aws_profile}'
                    )
                else:
                    self._redshift_data_client = boto3.client(
                        'redshift-data', config=self._config, region_name=self.aws_region
                    )
                    logger.info('Created Redshift Data API client with default credentials')
            except Exception as e:
                logger.error(f'Error creating Redshift Data API client: {str(e)}')
                raise

        return self._redshift_data_client


def quote_literal_string(value: Any) -> str:
    """Quote a value as a SQL literal.

    Args:
        value: The value to quote.
    """
    if value is None:
        return 'NULL'

    # TODO Reimplement a proper way.
    # A lazy hack for SQL literal quoting.
    return "'" + repr('"' + value)[2:]


async def execute_statement(
    cluster_identifier: str, database_name: str, sql: str, allow_read_write: bool = False
) -> tuple[dict, str]:
    """Execute a SQL statement against a Redshift cluster using the Data API.

    This is a common function used by other functions in this module.

    The SQL is wrapped in a transaction block with READ ONLY or READ WRITE mode
    based on allow_read_write flag. Transaction breaker protection is implemented
    to prevent unauthorized modifications.

    The executed SQL takes the form:
    BEGIN [READ ONLY|READ WRITE];
    <sql>
    END;

    Args:
        cluster_identifier: The cluster identifier to query.
        database_name: The database to execute the query against.
        sql: The SQL statement to execute.
        allow_read_write: Indicates if read-write mode should be activated.

    Returns:
        Tuple containing:
        - Dictionary with the raw results_response from get_statement_result.
        - String with the query_id.

    Raises:
        Exception: If cluster not found, query fails, or times out.
    """
    data_client = client_manager.redshift_data_client()

    # First, check if this is a provisioned cluster or serverless workgroup
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

    # Guard from executing read-write statements if not allowed
    if allow_read_write:
        protected_sqls = ['BEGIN READ WRITE;', sql, 'END;']
    else:
        # Check if SQL contains suspicious patterns trying to break the transaction context
        if regex.compile(SUSPICIOUS_QUERY_REGEXP).search(sql):
            logger.error(f'SQL contains suspicious pattern, execution rejected: {sql}')
            raise Exception(f'SQL contains suspicious pattern, execution rejected: {sql}')

        protected_sqls = ['BEGIN READ ONLY;', sql, 'END;']
        logger.debug(f'Protected SQL: {" ".join(protected_sqls)}')

    # Execute the query using Data API
    if cluster_info['type'] == 'provisioned':
        logger.debug(f'Using ClusterIdentifier for provisioned cluster: {cluster_identifier}')
        response = data_client.batch_execute_statement(
            ClusterIdentifier=cluster_identifier, Database=database_name, Sqls=protected_sqls
        )
    elif cluster_info['type'] == 'serverless':
        logger.debug(f'Using WorkgroupName for serverless workgroup: {cluster_identifier}')
        response = data_client.batch_execute_statement(
            WorkgroupName=cluster_identifier, Database=database_name, Sqls=protected_sqls
        )
    else:
        raise Exception(f'Unknown cluster type: {cluster_info["type"]}')

    query_id = response['Id']
    logger.debug(f'Started query execution: {query_id}')

    # Wait for query completion
    wait_time = 0
    while wait_time < QUERY_TIMEOUT:
        status_response = data_client.describe_statement(Id=query_id)
        status = status_response['Status']

        if status == 'FINISHED':
            logger.debug(f'Query execution completed: {query_id}')
            break
        elif status in ['FAILED', 'ABORTED']:
            error_msg = status_response.get('Error', 'Unknown error')
            logger.error(f'Query execution failed: {error_msg}')
            raise Exception(f'Query failed: {error_msg}')

        # Wait before polling again
        await asyncio.sleep(QUERY_POLL_INTERVAL)
        wait_time += QUERY_POLL_INTERVAL

    if wait_time >= QUERY_TIMEOUT:
        logger.error(f'Query execution timed out: {query_id}')
        raise Exception(f'Query timed out after {QUERY_TIMEOUT} seconds')

    # Get user query results
    subquery1_id = status_response['SubStatements'][1]['Id']
    results_response = data_client.get_statement_result(Id=subquery1_id)
    return results_response, subquery1_id


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
        results_response, _ = await execute_statement(
            cluster_identifier=cluster_identifier,
            database_name=database_name,
            sql=SVV_REDSHIFT_DATABASES_QUERY,
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
        results_response, _ = await execute_statement(
            cluster_identifier=cluster_identifier,
            database_name=schema_database_name,
            sql=SVV_ALL_SCHEMAS_QUERY.format(quote_literal_string(schema_database_name)),
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

        # Execute the query using the common function
        results_response, _ = await execute_statement(
            cluster_identifier=cluster_identifier,
            database_name=table_database_name,
            sql=SVV_ALL_TABLES_QUERY.format(
                quote_literal_string(table_database_name), quote_literal_string(table_schema_name)
            ),
        )

        tables = []
        records = results_response.get('Records', [])

        for record in records:
            # Extract values from the record
            table_info = {
                'database_name': record[0].get('stringValue'),
                'schema_name': record[1].get('stringValue'),
                'table_name': record[2].get('stringValue'),
                'table_acl': record[3].get('stringValue'),
                'table_type': record[4].get('stringValue'),
                'remarks': record[5].get('stringValue'),
            }
            tables.append(table_info)

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

        # Execute the query using the common function
        results_response, _ = await execute_statement(
            cluster_identifier=cluster_identifier,
            database_name=column_database_name,
            sql=SVV_ALL_COLUMNS_QUERY.format(
                quote_literal_string(column_database_name),
                quote_literal_string(column_schema_name),
                quote_literal_string(column_table_name),
            ),
        )

        columns = []
        records = results_response.get('Records', [])

        for record in records:
            # Extract values from the record
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
        results_response, query_id = await execute_statement(
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


# Global client manager instance
client_manager = RedshiftClientManager()
