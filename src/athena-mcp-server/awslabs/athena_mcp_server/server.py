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

"""awslabs Athena MCP Server implementation."""

from __future__ import annotations

import asyncio
import boto3
import functools
import time
from . import __version__
from .models import (
    ColumnInfo,
    DatabaseInfo,
    DataCatalogSummary,
    DataCatalogType,
    ErrorResponse,
    ListDatabasesResponse,
    ListDataCatalogsResponse,
    ListTablesResponse,
    ListWorkgroupsResponse,
    QueryResults,
    TableInfo,
    TableSummary,
    TableType,
    WorkgroupDetailsResponse,
    WorkgroupState,
    WorkgroupSummary,
)
from .validation import validate_query
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from sqlglot import exp, parse
from typing import Annotated, Any


DEFAULT_QUERY_TIMEOUT_SECONDS = 60


mcp = FastMCP(
    'awslabs.athena-mcp-server',
    instructions="""AWS Athena MCP Server provides tools to execute read-only SQL queries via AWS Athena.

Supports complex analytical queries, joins, aggregations, and window functions.

## Example Workflows

### Data Discovery
1. List available databases and data catalogs with `list_databases` and `list_data_catalogs`
2. Explore tables within databases using `list_tables`
3. Get detailed table metadata including columns and partitions with `get_table_metadata`
4. Use DESCRIBE or SHOW statements via `execute_query` to explore data structure
5. Use EXPLAIN to understand query execution

### Query Execution
1. Execute queries with `execute_query`
2. For large result sets, use pagination via `get_query_results`
3. Monitor query execution time and data scanned from `execute_query` response
""",
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
        'sqlglot',
    ],
)


@functools.lru_cache
def _get_athena_client(region: str = ''):
    """Get configured Athena client."""
    try:
        config = Config(user_agent_extra=f'awslabs/mcp/athena-mcp-server/{__version__}')
        if region.strip():
            return boto3.client('athena', region_name=region, config=config)
        else:
            return boto3.client('athena', config=config)
    except Exception as e:
        logger.error(f'Error creating Athena client: {e}')
        raise


def _extract_columns_and_rows(
    response: dict[str, Any], query_string: str, has_header_row: bool = True
) -> tuple[list[ColumnInfo], list[dict[str, str | None]]]:
    """Parse AWS Athena query results response into column info and rows.

    Args:
        response: Raw AWS Athena get_query_results response
        query_string: SQL query
        has_header_row: Whether first row contains column headers (True for first page, False for subsequent pages)

    Returns:
        Tuple of (column_info, rows) where rows are dicts with column names as keys
    """
    # Skip query parsing if query_string is empty (e.g., pagination calls)
    if query_string.strip():
        # Parse query to determine formatting approach
        [statement] = parse(query_string, read='athena')
        # DESCRIBE, EXPLAIN, and SHOW output human-readable strings that aren't necessarily columnar, so
        # just shove the text from all the rows into a single cell
        if isinstance(statement, exp.Describe) or (
            isinstance(statement, exp.Command)
            and statement.name.upper().startswith(('EXPLAIN', 'SHOW'))
        ):
            return _extract_as_text_cell(response)
    return _extract_as_tabular_data(response, has_header_row)


def _extract_as_text_cell(
    response: dict[str, Any],
) -> tuple[list[ColumnInfo], list[dict[str, str | None]]]:
    """Extract query results as a single column and single row with formatted text.

    Useful for utility commands like DESCRIBE, EXPLAIN, and SHOW that return human-readable
    report-like text rather than tabular data.
    """
    result_set = response.get('ResultSet', {})
    metadata = result_set.get('ResultSetMetadata', {})
    rows = result_set.get('Rows', [])
    # Get column name from metadata (use first column)
    column_name = 'Result'  # Default fallback
    if metadata.get('ColumnInfo'):
        first_col = metadata['ColumnInfo'][0]
        column_name = first_col['Name']
    text_lines = []
    for row in rows:
        line = row['Data'][0].get('VarCharValue', '') if row.get('Data') else ''
        text_lines.append(line)
    formatted_text = '\n'.join(text_lines)

    # Return as single column, single row
    column_info = [ColumnInfo(name=column_name, type='varchar', nullable=True)]
    result_rows: list[dict[str, str | None]] = [{column_name: formatted_text}]
    return column_info, result_rows


def _extract_as_tabular_data(
    response: dict[str, Any], has_header_row: bool = True
) -> tuple[list[ColumnInfo], list[dict[str, str | None]]]:
    """Extract tabular data."""
    column_info = []
    result_set = response.get('ResultSet', {})
    metadata = result_set.get('ResultSetMetadata', {})
    if 'ColumnInfo' in metadata:
        for col in metadata['ColumnInfo']:
            # Handle nullable field - AWS returns 'UNKNOWN', 'NULLABLE', 'NOT_NULL' as strings
            nullable_str = col.get('Nullable')
            nullable = None
            if nullable_str == 'NULLABLE':
                nullable = True
            elif nullable_str == 'NOT_NULL':
                nullable = False
            # For 'UNKNOWN' or any other value, leave as None
            column_info.append(
                ColumnInfo(
                    name=col['Name'],
                    type=col['Type'],
                    nullable=nullable,
                    precision=col.get('Precision'),
                    scale=col.get('Scale'),
                )
            )
    rows = []
    all_rows = result_set.get('Rows', [])
    if not all_rows:
        return column_info, rows
    column_names = [col.name for col in column_info]
    for row in all_rows[1:] if has_header_row else all_rows:
        row_data = []
        for col in row['Data']:
            if not col:  # Empty dict {} from boto3 means NULL
                row_data.append(None)
            else:
                row_data.append(col.get('VarCharValue', ''))
        if column_names:
            row_dict = dict(zip(column_names, row_data))
            rows.append(row_dict)
        else:
            row_dict = {f'column_{i}': val for i, val in enumerate(row_data)}
            rows.append(row_dict)
    return column_info, rows


def _handle_athena_error(error: Exception) -> ErrorResponse:
    """Handle and format Athena errors."""
    if isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        return ErrorResponse(
            error_code=error_code,
            error_message=error_message,
            error_type='ClientError',
        )
    else:
        return ErrorResponse(
            error_code='InternalError',
            error_message=str(error),
            error_type=type(error).__name__,
        )


@mcp.tool()
async def execute_query(
    query_string: Annotated[
        str,
        Field(
            min_length=1,
            max_length=262144,
            description='SQL query to execute. Only allows read-only SQL commands such as SELECT, VALUES, DESCRIBE, and SHOW. EXPLAIN is allowed if the query is read-only.',
        ),
    ],
    workgroup: Annotated[
        str,
        Field(
            max_length=128,
            description='Athena workgroup to use for query execution. If not specified, uses default workgroup.',
        ),
    ] = '',
    database: Annotated[
        str,
        Field(
            max_length=255,
            description='Default database for the query context. If not specified, queries must include fully qualified table names.',
        ),
    ] = '',
    output_location: Annotated[
        str,
        Field(
            description='S3 location for query results. If not specified, uses workgroup default location.'
        ),
    ] = '',
    timeout_seconds: Annotated[
        int,
        Field(
            ge=0,
            description='Maximum time to wait for query completion in seconds. Use 0 for no timeout.',
        ),
    ] = DEFAULT_QUERY_TIMEOUT_SECONDS,
    region: Annotated[
        str,
        Field(
            description='AWS region to use for the query. If not specified, uses boto3 default region resolution.',
        ),
    ] = '',
) -> QueryResults:
    """Execute a read-only SQL query in Athena and return the results.

    - Only allows read-only SQL commands such as SELECT, VALUES, DESCRIBE, and SHOW. EXPLAIN is allowed if the query is read-only.
    - Non-read-only operations such as INSERT, UPDATE, DELETE, CREATE, DROP, and ALTER are not allowed
    - When appropriate, use LIMIT clauses, WHERE filters, and select specific columns
    - Leverage partitioning when appropriate
    - Results are automatically paginated with a maximum of ~1000 rows per page

    Args:
        query_string: SQL query to execute
        workgroup: Athena workgroup to use
        database: Database to use
        output_location: S3 location for query results
        timeout_seconds: Maximum time to wait for query completion (0 for no timeout)
        region: AWS region to use

    Returns:
        Query results data containing:
        - column_info: List of column metadata with name, type, nullable status, precision, scale
        - rows: List of dictionaries where each dict represents a row with column names as keys
        - total_rows: Number of data rows returned in this page
        - query_execution_id: AWS Athena execution ID for reference or pagination
        - next_token: Pagination token if more results are available. If None, this is the last page. Use with get_query_results to retrieve additional pages.
        - data_scanned_in_bytes: Amount of data scanned by the query
        - execution_time_in_millis: Query execution time in milliseconds
    """
    validate_query(query_string)

    try:
        client = _get_athena_client(region)
        params: dict[str, Any] = {'QueryString': query_string}
        if workgroup.strip():
            params['WorkGroup'] = workgroup
        if output_location.strip():
            params['ResultConfiguration'] = {'OutputLocation': output_location}
        if database.strip():
            params['QueryExecutionContext'] = {'Database': database}
        response = client.start_query_execution(**params)
        query_execution_id = response['QueryExecutionId']

        # Poll for completion
        start_time = time.time()
        while True:
            execution_response = client.get_query_execution(QueryExecutionId=query_execution_id)
            execution = execution_response['QueryExecution']
            state = execution['Status']['State']
            if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            # Check timeout (skip if timeout_seconds is 0)
            if timeout_seconds > 0 and time.time() - start_time > timeout_seconds:
                try:
                    client.stop_query_execution(QueryExecutionId=query_execution_id)
                except Exception:
                    pass  # Ignore errors when cancelling
                raise TimeoutError(f'Query timed out after {timeout_seconds} seconds')
            await asyncio.sleep(2)
        if state == 'FAILED':
            error_reason = execution['Status'].get('StateChangeReason', 'Query failed')
            raise RuntimeError(f'Query failed: {error_reason}')
        elif state == 'CANCELLED':
            raise RuntimeError('Query was cancelled')
        results_response = client.get_query_results(
            QueryExecutionId=query_execution_id, MaxResults=1000
        )
        column_info, rows = _extract_columns_and_rows(
            results_response, query_string, has_header_row=True
        )
        statistics = execution.get('Statistics', {})
        return QueryResults(
            column_info=column_info,
            rows=rows,
            total_rows=len(rows),
            next_token=results_response.get('NextToken'),
            query_execution_id=query_execution_id,
            data_scanned_in_bytes=statistics.get('DataScannedInBytes'),
            execution_time_in_millis=statistics.get('EngineExecutionTimeInMillis'),
        )
    except Exception as e:
        logger.error(f'Error executing query: {e}')
        error_response = _handle_athena_error(e)
        raise RuntimeError(f'{error_response.error_code}: {error_response.error_message}')


@mcp.tool()
async def get_query_results(
    query_execution_id: Annotated[
        str,
        Field(
            description='Query execution ID from execute_query. Used to retrieve additional results from a completed query (mainly for pagination).'
        ),
    ],
    next_token: Annotated[
        str,
        Field(
            description='Token for pagination. Use this to get additional result pages if more results are available.'
        ),
    ] = '',
    region: Annotated[
        str,
        Field(
            description='AWS region to use for the query. If not specified, uses boto3 default region resolution.',
        ),
    ] = '',
) -> QueryResults:
    """Get results from a completed query execution.

    This is mainly used for pagination of large result sets since execute_query returns results
    directly. Each page contains a maximum of 1000 rows.

    Args:
        query_execution_id: Query execution ID from execute_query
        next_token: Token for pagination (from previous execute_query or get_query_results call)
        region: AWS region to use for the query

    Returns:
        Paginated query results containing:
        - column_info: List of column metadata with name, type, nullable status, precision, scale
        - rows: List of dictionaries where each dict represents a row with column names as keys (max 1000 per page)
        - total_rows: Number of data rows returned in this page
        - query_execution_id: Same execution ID passed in
        - next_token: Token for next page if more results available. If None, this is the last page.
        - data_scanned_in_bytes: Amount of data scanned by the original query
        - execution_time_in_millis: Original query execution time in milliseconds
    """
    try:
        client = _get_athena_client(region)
        params = {
            'QueryExecutionId': query_execution_id,
            'MaxResults': 1000,
        }
        if next_token.strip():
            params['NextToken'] = next_token
        response = client.get_query_results(**params)
        column_info, rows = _extract_columns_and_rows(
            response, '', has_header_row=not next_token.strip()
        )
        return QueryResults(
            column_info=column_info,
            rows=rows,
            total_rows=len(rows),
            next_token=response.get('NextToken'),
            query_execution_id=query_execution_id,
            data_scanned_in_bytes=None,  # Not available in get_query_results
            execution_time_in_millis=None,  # Not available in get_query_results
        )
    except Exception as e:
        logger.error(f'Error getting query results: {e}')
        error_response = _handle_athena_error(e)
        raise RuntimeError(f'{error_response.error_code}: {error_response.error_message}')


@mcp.tool()
async def list_databases(
    catalog_name: Annotated[
        str,
        Field(
            description='Data catalog name to list databases from. Use "AwsDataCatalog" for AWS Glue Data Catalog.'
        ),
    ] = 'AwsDataCatalog',
    next_token: Annotated[
        str, Field(description='Token for pagination to get additional database pages.')
    ] = '',
    region: Annotated[
        str,
        Field(
            description='AWS region to use for the query. If not specified, uses boto3 default region resolution.',
        ),
    ] = '',
) -> ListDatabasesResponse:
    """List databases in the specified data catalog.

    Results are paginated with a maximum of 50 databases per page.

    Args:
        catalog_name: Data catalog name
        next_token: Token for pagination (from previous list_databases call)
        region: AWS region to use for the query

    Returns:
        Database listing containing:
        - databases: List of database dictionaries with 'name', 'description', and 'parameters' (max 50 per page)
        - next_token: Pagination token for retrieving additional databases. If None, this is the last page.
    """
    try:
        client = _get_athena_client(region)
        params = {
            'CatalogName': catalog_name,
            'MaxResults': 50,
        }
        if next_token.strip():
            params['NextToken'] = next_token
        response = client.list_databases(**params)
        databases = []
        for db in response.get('DatabaseList', []):
            databases.append(
                DatabaseInfo(
                    name=db['Name'],
                    description=db.get('Description'),
                    parameters=db.get('Parameters'),
                ).model_dump()
            )
        return ListDatabasesResponse(
            databases=databases,
            next_token=response.get('NextToken'),
        )
    except Exception as e:
        logger.error(f'Error listing databases: {e}')
        error_response = _handle_athena_error(e)
        raise RuntimeError(f'{error_response.error_code}: {error_response.error_message}')


@mcp.tool()
async def list_tables(
    database_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=255,
            description='Name of database to list tables from.',
        ),
    ],
    catalog_name: Annotated[
        str, Field(description='Data catalog name. Use AwsDataCatalog for AWS Glue Data Catalog.')
    ] = 'AwsDataCatalog',
    expression: Annotated[
        str,
        Field(
            max_length=256,
            description='Regular expression to filter table names. Only tables matching this pattern will be returned. If not specified, returns all tables.',
        ),
    ] = '',
    next_token: Annotated[
        str, Field(description='Token for pagination to get additional table pages.')
    ] = '',
    region: Annotated[
        str,
        Field(
            description='AWS region to use for the query. If not specified, uses boto3 default region resolution.',
        ),
    ] = '',
) -> ListTablesResponse:
    """List tables in the specified database.

    Results are paginated with a maximum of 50 tables per page.

    Args:
        database_name: Database name
        catalog_name: Data catalog name
        expression: Regular expression to filter table names
        next_token: Token for pagination (from previous list_tables call)
        region: AWS region to use for the query

    Returns:
        Table listing containing:
        - tables: List of table summaries with name, table_type, create_time, last_access_time, columns_count, partition_keys_count (max 50 per page)
        - next_token: Pagination token for retrieving additional tables. If None, this is the last page.
    """
    try:
        client = _get_athena_client(region)
        params = {
            'CatalogName': catalog_name,
            'DatabaseName': database_name,
            'MaxResults': 50,
        }
        if expression.strip():
            params['Expression'] = expression
        if next_token.strip():
            params['NextToken'] = next_token
        response = client.list_table_metadata(**params)
        tables = []
        for table in response.get('TableMetadataList', []):
            tables.append(
                TableSummary(
                    name=table['Name'],
                    table_type=TableType(table['TableType']) if table.get('TableType') else None,
                    create_time=table.get('CreateTime'),
                    last_access_time=table.get('LastAccessTime'),
                    columns_count=len(table.get('Columns', [])),
                    partition_keys_count=len(table.get('PartitionKeys', [])),
                )
            )
        return ListTablesResponse(
            tables=tables,
            next_token=response.get('NextToken'),
        )
    except Exception as e:
        logger.error(f'Error listing tables: {e}')
        error_response = _handle_athena_error(e)
        raise RuntimeError(f'{error_response.error_code}: {error_response.error_message}')


@mcp.tool()
async def get_table_metadata(
    database_name: Annotated[
        str,
        Field(
            min_length=1,
            description='Name of database containing the table.',
        ),
    ],
    table_name: Annotated[
        str,
        Field(
            min_length=1,
            description='Table name to get metadata for.',
        ),
    ],
    catalog_name: Annotated[
        str,
        Field(
            min_length=1,
            description='Data catalog name. Use "AwsDataCatalog" for AWS Glue Data Catalog.',
        ),
    ] = 'AwsDataCatalog',
    region: Annotated[
        str,
        Field(
            description='AWS region to use for the query. If not specified, uses boto3 default region resolution.',
        ),
    ] = '',
) -> TableInfo:
    """Get detailed metadata for a specific table.

    Args:
        database_name: Database name
        table_name: Table name
        catalog_name: Data catalog name
        region: AWS region to use for the query

    Returns:
        Detailed table metadata containing:
        - name: Table name
        - table_type: Type (EXTERNAL_TABLE, MANAGED_TABLE, VIRTUAL_VIEW)
        - create_time, last_access_time: Timestamps for table lifecycle
        - columns: List of column definitions with detailed schema information
        - partition_keys: List of partition column definitions
        - location: S3 path where table data is stored
        - input_format, output_format: Hadoop input/output format classes
        - serde_info: Serialization/deserialization configuration
        - parameters: Additional table properties and metadata
    """
    try:
        client = _get_athena_client(region)
        response = client.get_table_metadata(
            CatalogName=catalog_name,
            DatabaseName=database_name,
            TableName=table_name,
        )
        table = response['TableMetadata']
        columns = []
        for col in table.get('Columns', []):
            columns.append(
                ColumnInfo(
                    name=col['Name'],
                    type=col['Type'],
                    nullable=col.get('Nullable'),
                )
            )
        partition_keys = []
        for pk in table.get('PartitionKeys', []):
            partition_keys.append(
                ColumnInfo(
                    name=pk['Name'],
                    type=pk['Type'],
                )
            )
        return TableInfo(
            name=table['Name'],
            table_type=table.get('TableType'),
            create_time=table.get('CreateTime'),
            last_access_time=table.get('LastAccessTime'),
            columns=columns,
            partition_keys=partition_keys,
            location=table.get('StorageDescriptor', {}).get('Location'),
            input_format=table.get('StorageDescriptor', {}).get('InputFormat'),
            output_format=table.get('StorageDescriptor', {}).get('OutputFormat'),
            serde_info=table.get('StorageDescriptor', {}).get('SerdeInfo'),
            parameters=table.get('Parameters'),
        )
    except Exception as e:
        logger.error(f'Error getting table metadata: {e}')
        error_response = _handle_athena_error(e)
        raise RuntimeError(f'{error_response.error_code}: {error_response.error_message}')


@mcp.tool()
async def list_work_groups(
    next_token: Annotated[
        str, Field(description='Token for pagination to get additional workgroup pages.')
    ] = '',
    region: Annotated[
        str,
        Field(
            description='AWS region to use for the query. If not specified, uses boto3 default region resolution.',
        ),
    ] = '',
) -> ListWorkgroupsResponse:
    """List available Athena workgroups.

    Results are paginated with a maximum of 50 workgroups per page.

    Args:
        next_token: Token for pagination (from previous list_work_groups call)
        region: AWS region to use for the query

    Returns:
        Workgroup listing containing:
        - workgroups: List of workgroup summaries with name, state, description, creation_time (max 50 per page)
        - next_token: Pagination token for retrieving additional workgroups. If None, this is the last page.
    """
    try:
        client = _get_athena_client(region)
        params: dict[str, Any] = {'MaxResults': 50}
        if next_token.strip():
            params['NextToken'] = next_token
        response = client.list_work_groups(**params)
        workgroups = []
        for wg in response.get('WorkGroups', []):
            workgroups.append(
                WorkgroupSummary(
                    name=wg['Name'],
                    state=WorkgroupState(wg['State']),
                    description=wg.get('Description'),
                    creation_time=wg.get('CreationTime'),
                )
            )
        return ListWorkgroupsResponse(
            workgroups=workgroups,
            next_token=response.get('NextToken'),
        )
    except Exception as e:
        logger.error(f'Error listing workgroups: {e}')
        error_response = _handle_athena_error(e)
        raise RuntimeError(f'{error_response.error_code}: {error_response.error_message}')


@mcp.tool()
async def get_work_group(
    workgroup_name: Annotated[
        str,
        Field(description='Name of the workgroup to get details for.'),
    ],
    region: Annotated[
        str,
        Field(
            description='AWS region to use for the query. If not specified, uses boto3 default region resolution.',
        ),
    ] = '',
) -> WorkgroupDetailsResponse:
    """Get detailed workgroup configuration and settings.

    Args:
        workgroup_name: Name of the workgroup
        region: AWS region to use for the query

    Returns:
        Detailed workgroup information containing:
        - name: Workgroup name
        - state: Current state (ENABLED/DISABLED)
        - description: Optional workgroup description
        - creation_time: When the workgroup was created
        - configuration: Complete workgroup settings including result location, encryption, cost controls
    """
    try:
        client = _get_athena_client(region)

        response = client.get_work_group(WorkGroup=workgroup_name)
        workgroup = response['WorkGroup']
        config = workgroup.get('Configuration', {})
        result_config = config.get('ResultConfiguration', {})
        return WorkgroupDetailsResponse(
            name=workgroup['Name'],
            state=WorkgroupState(workgroup['State']),
            description=workgroup.get('Description'),
            creation_time=workgroup.get('CreationTime'),
            configuration={
                'result_configuration': {
                    'output_location': result_config.get('OutputLocation'),
                    'encryption_configuration': result_config.get('EncryptionConfiguration'),
                },
                'enforce_work_group_configuration': config.get('EnforceWorkGroupConfiguration'),
                'publish_cloud_watch_metrics': config.get('PublishCloudWatchMetrics'),
                'bytes_scanned_cutoff_per_query': config.get('BytesScannedCutoffPerQuery'),
                'requester_pays_enabled': config.get('RequesterPaysEnabled'),
                'engine_version': config.get('EngineVersion'),
            },
        )
    except Exception as e:
        logger.error(f'Error getting workgroup details: {e}')
        error_response = _handle_athena_error(e)
        raise RuntimeError(f'{error_response.error_code}: {error_response.error_message}')


@mcp.tool()
async def list_data_catalogs(
    next_token: Annotated[
        str,
        Field(description='Token for pagination to get additional data catalog pages.'),
    ] = '',
    region: Annotated[
        str,
        Field(
            description='AWS region to use for the query. If not specified, uses boto3 default region resolution.',
        ),
    ] = '',
) -> ListDataCatalogsResponse:
    """List available data catalogs.

    Results are paginated with a maximum of 50 data catalogs per page.

    Args:
        next_token: Token for pagination (from previous list_data_catalogs call)
        region: AWS region to use for the query

    Returns:
        Data catalog listing containing:
        - data_catalogs: List of catalog summaries with catalog_name and type (GLUE, HIVE, LAMBDA) (max 50 per page)
        - next_token: Pagination token for retrieving additional catalogs. If None, this is the last page.
    """
    try:
        client = _get_athena_client(region)
        params: dict[str, Any] = {'MaxResults': 50}
        if next_token.strip():
            params['NextToken'] = next_token
        response = client.list_data_catalogs(**params)
        catalogs = []
        for catalog in response.get('DataCatalogsSummary', []):
            catalogs.append(
                DataCatalogSummary(
                    catalog_name=catalog['CatalogName'],
                    type=DataCatalogType(catalog['Type']),
                )
            )
        return ListDataCatalogsResponse(
            data_catalogs=catalogs,
            next_token=response.get('NextToken'),
        )
    except Exception as e:
        logger.error(f'Error listing data catalogs: {e}')
        error_response = _handle_athena_error(e)
        raise RuntimeError(f'{error_response.error_code}: {error_response.error_message}')


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
