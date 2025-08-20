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

"""AWS S3 Storage Lens tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

import os
from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


storage_lens_server = FastMCP(
    name='storage-lens-tools', instructions='Tools for working with AWS S3 Storage Lens data'
)

# Environment variable names
ENV_STORAGE_LENS_MANIFEST_LOCATION = 'STORAGE_LENS_MANIFEST_LOCATION'
ENV_STORAGE_LENS_OUTPUT_LOCATION = 'STORAGE_LENS_OUTPUT_LOCATION'

# Default database and table names
DEFAULT_DATABASE = 'storage_lens_db'
DEFAULT_TABLE = 'storage_lens_metrics'


@storage_lens_server.tool(
    name='storage-lens-run-query',
    description="""Query S3 Storage Lens metrics data using Athena SQL.

IMPORTANT USAGE GUIDELINES:
- Use standard SQL syntax for Athena queries
- Use {table} as a placeholder for the Storage Lens metrics table name
- Perform aggregations (GROUP BY) when analyzing data across multiple dimensions

This tool allows you to analyze S3 Storage Lens metrics data using SQL queries.
Storage Lens provides metrics about your S3 storage, including:

- Storage metrics: Total bytes, object counts by storage class
- Cost optimization metrics: Transition opportunities, incomplete multipart uploads
- Data protection metrics: Replication, versioning, encryption status
- Activity metrics: Upload, download, and request metrics

Common columns in the Storage Lens metrics table include:
- bucket_name: Name of the S3 bucket
- storage_class: S3 storage class (Standard, IA, Glacier, etc.)
- region: AWS region of the bucket
- storage_bytes: Total storage in bytes
- object_count: Number of objects
- average_object_size: Average size of objects in bytes
- incomplete_multipart_upload_bytes: Bytes in incomplete multipart uploads
- transition_lifecycle_rule_count: Number of lifecycle transition rules

Environment variables:
- STORAGE_LENS_MANIFEST_LOCATION: S3 URI to manifest file or folder (required)
- STORAGE_LENS_OUTPUT_LOCATION: S3 location for Athena query results (optional)

Example queries:
1. Top 10 buckets by storage size:
   SELECT bucket_name, SUM(storage_bytes) as total_size FROM {table} GROUP BY bucket_name ORDER BY total_size DESC LIMIT 10

2. Storage by storage class:
   SELECT storage_class, SUM(storage_bytes) as total_size FROM {table} GROUP BY storage_class ORDER BY total_size DESC

3. Buckets with incomplete multipart uploads:
   SELECT bucket_name, SUM(incomplete_multipart_upload_bytes) as incomplete_bytes FROM {table} WHERE incomplete_multipart_upload_bytes > 0 GROUP BY bucket_name ORDER BY incomplete_bytes DESC""",
)
async def storage_lens_run_query(
    ctx: Context,
    query: str,
    manifest_location: Optional[str] = None,
    output_location: Optional[str] = None,
    database_name: Optional[str] = None,
    table_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Query S3 Storage Lens metrics data using Athena SQL.

    Args:
        ctx: The MCP context
        query: SQL query to execute against the data (use {table} as a placeholder for the table name)
        manifest_location: S3 URI to manifest file or folder (overrides environment variable)
        output_location: S3 location for Athena query results (overrides environment variable)
        database_name: Athena database name (defaults to 'storage_lens_db')
        table_name: Athena table name (defaults to 'storage_lens_metrics')

    Returns:
        Dict containing the query results and metadata
    """
    try:
        # Log the request
        await ctx.info(f'Running Storage Lens query: {query}')

        # Get manifest location from args or environment variable
        manifest_loc = manifest_location or os.environ.get(ENV_STORAGE_LENS_MANIFEST_LOCATION, '')
        if not manifest_loc:
            return format_response(
                'error',
                {},
                f"Missing manifest location. Provide 'manifest_location' parameter or set {ENV_STORAGE_LENS_MANIFEST_LOCATION} environment variable.",
            )

        # Get output location from args or environment variable (optional)
        output_loc = output_location or os.environ.get(ENV_STORAGE_LENS_OUTPUT_LOCATION, '')

        # Use default or provided database and table names
        db_name = database_name or DEFAULT_DATABASE
        tbl_name = table_name or DEFAULT_TABLE

        # Ensure the query has the {table} placeholder
        formatted_query = query
        if '{table}' in query:
            formatted_query = query.replace('{table}', f'{db_name}.{tbl_name}')
        elif f'{db_name}.{tbl_name}' not in query:
            # If query doesn't contain the full table name and doesn't have the placeholder
            # then prepend the database and table name to the FROM clause
            if ' from ' in query.lower():
                formatted_query = query.lower().replace(' from ', f' FROM {db_name}.{tbl_name} ')
            else:
                return format_response(
                    'error',
                    {},
                    'Query must either contain {table} placeholder or explicitly reference the table.',
                )

        # Execute the query using Athena
        result = await execute_athena_query(
            ctx, formatted_query, manifest_loc, output_loc, db_name, tbl_name
        )

        return result

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'storage_lens_run_query', 'Athena')


async def execute_athena_query(
    ctx, query, manifest_location, output_location, database_name, table_name
):
    """Execute a query using Athena on Storage Lens data."""
    try:
        # Initialize Athena client using shared utility
        athena_client = create_aws_client('athena')

        # Create database and table if they don't exist
        await create_or_update_table(
            ctx, athena_client, manifest_location, database_name, table_name
        )

        # Set up the output location
        athena_output = output_location
        if not athena_output:
            # Use a default location if not provided
            if manifest_location.endswith('/'):
                athena_output = f'{manifest_location}query-results/'
            else:
                athena_output = f'{manifest_location}/query-results/'

        # Start the query execution
        start_response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database_name},
            ResultConfiguration={'OutputLocation': athena_output},
        )

        # Get the query execution ID
        query_execution_id = start_response['QueryExecutionId']

        # Wait for the query to complete
        await ctx.info(f'Query execution ID: {query_execution_id}')
        await ctx.info('Waiting for query to complete...')

        # Poll for query completion
        result = await poll_query_status(ctx, athena_client, query_execution_id)

        return result

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'execute_athena_query', 'Athena')


async def create_or_update_table(ctx, athena_client, manifest_location, database_name, table_name):
    """Create or update the Athena table for Storage Lens data."""
    try:
        # Create the database if it doesn't exist
        create_db_query = f'CREATE DATABASE IF NOT EXISTS {database_name}'
        response = athena_client.start_query_execution(
            QueryString=create_db_query,
            ResultConfiguration={
                'OutputLocation': f's3://{manifest_location.split("/")[2]}/athena-temp/'
            },
        )

        # Wait for the database creation to complete
        query_execution_id = response['QueryExecutionId']
        await wait_for_query_completion(ctx, athena_client, query_execution_id)

        # Create or update the table
        create_table_query = generate_create_table_query(
            manifest_location, database_name, table_name
        )
        response = athena_client.start_query_execution(
            QueryString=create_table_query,
            QueryExecutionContext={'Database': database_name},
            ResultConfiguration={
                'OutputLocation': f's3://{manifest_location.split("/")[2]}/athena-temp/'
            },
        )

        # Wait for the table creation to complete
        query_execution_id = response['QueryExecutionId']
        await wait_for_query_completion(ctx, athena_client, query_execution_id)

        await ctx.info(f'Created or updated table {database_name}.{table_name}')

    except Exception as e:
        await ctx.error(f'Error creating or updating table: {str(e)}')
        raise


def generate_create_table_query(manifest_location, database_name, table_name):
    """Generate the CREATE TABLE query for Storage Lens data."""
    # Extract the S3 bucket and prefix from the manifest location
    bucket_name = manifest_location.split('/')[2]
    prefix_parts = manifest_location.split('/')[3:]
    prefix = '/'.join(prefix_parts)

    # Ensure prefix ends with a trailing slash
    if not prefix.endswith('/'):
        prefix = prefix + '/'

    query = f"""
    CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
        region string,
        bucket_name string,
        storage_class string,
        record_timestamp timestamp,
        storage_bytes bigint,
        object_count bigint,
        average_object_size double,
        incomplete_multipart_upload_bytes bigint,
        incomplete_multipart_upload_count bigint,
        delete_marker_count bigint,
        noncurrent_version_count bigint,
        noncurrent_version_bytes bigint,
        transition_lifecycle_rule_count bigint,
        expiration_lifecycle_rule_count bigint,
        intelligent_tiering_fa_bytes bigint,
        intelligent_tiering_ia_bytes bigint,
        intelligent_tiering_aa_bytes bigint
    )
    ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
    WITH SERDEPROPERTIES (
        'serialization.format' = '1'
    )
    STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
    OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
    LOCATION 's3://{bucket_name}/{prefix}data/'
    TBLPROPERTIES ('has_encrypted_data'='false')
    """

    return query


async def wait_for_query_completion(ctx, athena_client, query_execution_id):
    """Wait for an Athena query to complete."""
    max_retries = 30
    for _ in range(max_retries):
        # Get the query execution status
        response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)

        status = response['QueryExecution']['Status']['State']

        if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            return status

        # Wait before checking again
        await ctx.info(f'Query status: {status}, waiting...')

    return 'TIMEOUT'


async def poll_query_status(ctx, athena_client, query_execution_id):
    """Poll for query status and return results when complete."""
    try:
        # Wait for the query to complete
        status = await wait_for_query_completion(ctx, athena_client, query_execution_id)

        # Get the query execution details
        response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)

        execution_details = response['QueryExecution']
        status_info = execution_details['Status']

        if status == 'SUCCEEDED':
            # Get the query results
            results_response = athena_client.get_query_results(
                QueryExecutionId=query_execution_id,
                MaxResults=100,
            )

            # Process the results
            column_info = results_response['ResultSet']['ResultSetMetadata']['ColumnInfo']
            columns = [col['Name'] for col in column_info]

            rows = []
            for row_data in results_response['ResultSet']['Rows'][1:]:
                row = {}
                for i, value in enumerate(row_data['Data']):
                    if 'VarCharValue' in value:
                        row[columns[i]] = value['VarCharValue']
                    else:
                        row[columns[i]] = None
                rows.append(row)

            # Create the formatted response
            formatted_response = {
                'query_execution_id': query_execution_id,
                'execution_time': status_info.get('CompletionDateTime', 0)
                - status_info.get('SubmissionDateTime', 0),
                'data_scanned_bytes': execution_details.get('Statistics', {}).get(
                    'DataScannedInBytes', 0
                ),
                'columns': columns,
                'result_count': len(rows),
                'results': rows,
                'has_more': 'NextToken' in results_response,
                's3_result_location': execution_details['ResultConfiguration']['OutputLocation'],
            }

            return format_response('success', formatted_response)
        else:
            # Query failed or was cancelled
            error_message = status_info.get('StateChangeReason', 'Unknown error')
            return format_response(
                'error', {'query_execution_id': query_execution_id, 'state': status}, error_message
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'poll_query_status', 'Athena')
