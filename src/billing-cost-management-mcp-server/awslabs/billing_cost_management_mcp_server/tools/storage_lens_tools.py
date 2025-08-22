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

This module provides functionality to create and query Athena tables for S3 Storage Lens data.
See the resources/storage_lens_metrics_reference.md file for detailed metrics information and sample queries.
"""

import asyncio
import json
import os
import re
from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from ..utilities.constants import (
    ATHENA_MAX_RETRIES,
    ATHENA_RETRY_DELAY_SECONDS,
    ENV_STORAGE_LENS_MANIFEST_LOCATION,
    ENV_STORAGE_LENS_OUTPUT_LOCATION,
    STORAGE_LENS_DEFAULT_DATABASE,
    STORAGE_LENS_DEFAULT_TABLE,
)
from datetime import datetime
from enum import Enum
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional, TypedDict
from urllib.parse import urlparse


# FastMCP server instance
storage_lens_server = FastMCP(
    name='storage-lens-tools', instructions='Tools for working with AWS S3 Storage Lens data'
)


# Using constants from centralized constants.py file
# STORAGE_LENS_DEFAULT_DATABASE: Default database name for Storage Lens data
# STORAGE_LENS_DEFAULT_TABLE: Default table name for Storage Lens data
# ATHENA_MAX_RETRIES: Maximum number of retries for Athena query completion
# ATHENA_RETRY_DELAY_SECONDS: Delay between retries in seconds
# ENV_STORAGE_LENS_MANIFEST_LOCATION: Environment variable for S3 URI to manifest file
# ENV_STORAGE_LENS_OUTPUT_LOCATION: Environment variable for S3 location for Athena query results


# Schema format enum
class SchemaFormat(Enum):
    """Storage Lens data format."""

    CSV = 'CSV'
    PARQUET = 'PARQUET'


# Helper classes for typed data
class ColumnDefinition(TypedDict):
    """Column definition for Athena tables."""

    name: str
    type: str


class SchemaInfo(TypedDict):
    """Schema information for Storage Lens data."""

    format: SchemaFormat
    columns: List[ColumnDefinition]
    skip_header: bool


class ManifestFile(TypedDict):
    """Manifest file information."""

    key: str
    last_modified: datetime


class AthenaQueryExecution(TypedDict):
    """Athena query execution information."""

    query_execution_id: str
    status: str


class ManifestHandler:
    """Handler for S3 Storage Lens manifest files."""

    def __init__(self, ctx: Context):
        """Initialize the S3 client.

        Args:
            ctx: MCP context for logging
        """
        self.ctx = ctx
        self.s3_client = create_aws_client('s3')

    async def get_manifest(self, manifest_location: str) -> Dict[str, Any]:
        """Locate and parse the manifest file from S3.

        Args:
            manifest_location: S3 URI to manifest file or folder containing manifest files
                (e.g., 's3://bucket-name/path/to/manifest.json' or 's3://bucket-name/path/to/folder/')

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        try:
            # Parse the S3 URI to get bucket and key
            parsed_uri = urlparse(manifest_location)
            bucket = parsed_uri.netloc
            key = parsed_uri.path.lstrip('/')

            await self.ctx.info(f'Looking for manifest at s3://{bucket}/{key}')

            if key.endswith('manifest.json'):
                return await self._read_manifest_file(bucket, key)
            else:
                return await self._find_latest_manifest(bucket, key)

        except Exception as e:
            await self.ctx.error(f'Failed to get manifest: {str(e)}')
            raise

    async def _read_manifest_file(self, bucket: str, key: str) -> Dict[str, Any]:
        """Read and parse a manifest file from S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key for the manifest file

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            manifest_content = json.loads(response['Body'].read().decode('utf-8'))
            await self.ctx.info(f'Successfully read manifest file at s3://{bucket}/{key}')
            return manifest_content
        except Exception as e:
            await self.ctx.error(f'Failed to read manifest file at s3://{bucket}/{key}: {str(e)}')
            raise Exception(f'Failed to read manifest file at s3://{bucket}/{key}: {str(e)}')

    async def _find_latest_manifest(self, bucket: str, key: str) -> Dict[str, Any]:
        """Find the latest manifest.json file in the specified S3 location.

        Args:
            bucket: S3 bucket name
            key: S3 prefix to search for manifest files

        Returns:
            Dict[str, Any]: Parsed manifest JSON content
        """
        # Ensure key ends with a slash
        if not key.endswith('/'):
            key += '/'

        await self.ctx.info(f'Searching for manifest.json files in s3://{bucket}/{key}')

        try:
            # List objects with the prefix and filter for manifest.json files
            manifest_files = []

            # Use pagination to handle large directories
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix=key):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        if obj['Key'].endswith('manifest.json'):
                            # Use the ManifestFile structure
                            manifest_file = ManifestFile(
                                key=obj['Key'], last_modified=obj['LastModified']
                            )
                            manifest_files.append(manifest_file)

            if not manifest_files:
                raise Exception(f'No manifest.json files found at s3://{bucket}/{key}')

            # Sort by last modified date to get the latest
            latest_manifest = sorted(
                manifest_files, key=lambda x: x['last_modified'], reverse=True
            )[0]

            # Log only the selected latest manifest file
            await self.ctx.info(
                f'Selected latest manifest: s3://{bucket}/{latest_manifest["key"]} '
                f'(Last Modified: {latest_manifest["last_modified"]})'
            )

            # Get the content of the latest manifest file
            return await self._read_manifest_file(bucket, latest_manifest['key'])

        except Exception as e:
            await self.ctx.error(
                f'Failed to locate manifest file in s3://{bucket}/{key}: {str(e)}'
            )
            raise Exception(f'Failed to locate manifest file in s3://{bucket}/{key}: {str(e)}')

    def extract_data_location(self, manifest: Dict[str, Any]) -> str:
        """Extract the S3 location of the data files from the manifest.

        Args:
            manifest: Parsed manifest JSON content

        Returns:
            str: S3 URI to the data files
        """
        report_files = manifest.get('reportFiles', [])

        if not report_files:
            raise Exception('No report files found in manifest')

        # Determine the S3 location of the report files
        sample_file = report_files[0]['key']
        parsed_uri = urlparse(sample_file)

        if not parsed_uri.netloc:
            # If the key is relative, construct the full path
            destination_bucket = manifest.get('destinationBucket', '')
            if destination_bucket.startswith('arn:aws:s3:::'):
                bucket_name = destination_bucket.replace('arn:aws:s3:::', '')
            else:
                bucket_name = destination_bucket

            data_location = f's3://{bucket_name}/{sample_file}'
        else:
            data_location = sample_file

        # Return the directory containing the data files
        return '/'.join(data_location.split('/')[:-1])

    def parse_schema(self, manifest: Dict[str, Any]) -> SchemaInfo:
        """Parse the schema information from the manifest.

        Args:
            manifest: Parsed manifest JSON content

        Returns:
            SchemaInfo: Schema information including format, column definitions, etc.
        """
        report_format = manifest.get('reportFormat', 'CSV')
        report_schema = manifest.get('reportSchema', '')

        if report_format.upper() == 'CSV':
            # For CSV, the schema is a comma-separated list of column names
            columns = report_schema.split(',')
            column_definitions = []

            for column in columns:
                # Default to string type for all columns
                column_definitions.append(ColumnDefinition(name=column.strip(), type='STRING'))

            return SchemaInfo(
                format=SchemaFormat.CSV, columns=column_definitions, skip_header=True
            )
        else:  # Parquet format
            # For Parquet, we need to parse the message schema
            schema_str = report_schema

            # Extract field definitions from the Parquet message schema
            field_pattern = r'required\s+(\w+)\s+(\w+);'
            matches = re.findall(field_pattern, schema_str)

            column_definitions = []
            for match in matches:
                data_type, field_name = match
                # Map Parquet types to Athena types
                if data_type.lower() == 'string':
                    athena_type = 'STRING'
                elif data_type.lower() == 'long':
                    athena_type = 'BIGINT'
                elif data_type.lower() == 'double':
                    athena_type = 'DOUBLE'
                else:
                    athena_type = 'STRING'  # Default to STRING for unknown types

                column_definitions.append(ColumnDefinition(name=field_name, type=athena_type))

            return SchemaInfo(
                format=SchemaFormat.PARQUET, columns=column_definitions, skip_header=False
            )


class AthenaHandler:
    """Handler for Athena operations on S3 Storage Lens data."""

    def __init__(self, ctx: Context):
        """Initialize the Athena client.

        Args:
            ctx: MCP context for logging
        """
        self.ctx = ctx
        # Create Athena client using shared utility function
        self.athena_client = create_aws_client('athena')

    async def create_database(self, database_name: str, output_location: str) -> None:
        """Create an Athena database if it doesn't exist.

        Args:
            database_name: Name of the database to create
            output_location: S3 location for query results
        """
        create_db_query = f'CREATE DATABASE IF NOT EXISTS {database_name}'
        await self.execute_query(create_db_query, 'default', output_location)

    async def create_table_for_csv(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Create an Athena table for CSV data.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results
        """
        column_definitions = []
        for column in schema_info['columns']:
            column_definitions.append(f'`{column["name"]}` {column["type"]}')

        create_table_query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
            {', '.join(column_definitions)}
        )
        ROW FORMAT DELIMITED
        FIELDS TERMINATED BY ','
        STORED AS TEXTFILE
        LOCATION '{data_location}'
        TBLPROPERTIES ('skip.header.line.count'='1')
        """

        await self.execute_query(create_table_query, database_name, output_location)

    async def create_table_for_parquet(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Create an Athena table for Parquet data.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results
        """
        column_definitions = []
        for column in schema_info['columns']:
            column_definitions.append(f'`{column["name"]}` {column["type"]}')

        create_table_query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {database_name}.{table_name} (
            {', '.join(column_definitions)}
        )
        STORED AS PARQUET
        LOCATION '{data_location}'
        """

        await self.execute_query(create_table_query, database_name, output_location)

    async def setup_table(
        self,
        database_name: str,
        table_name: str,
        schema_info: SchemaInfo,
        data_location: str,
        output_location: str,
    ) -> None:
        """Set up an Athena table based on the schema information.

        Args:
            database_name: Name of the database
            table_name: Name of the table to create
            schema_info: Schema information from manifest
            data_location: S3 location of the data files
            output_location: S3 location for query results
        """
        await self.ctx.info(f'Setting up Athena table {database_name}.{table_name}')
        await self.ctx.info(f'Data location: {data_location}')
        await self.ctx.info(f'Schema format: {schema_info["format"]}')
        await self.ctx.info(f'Columns: {[col["name"] for col in schema_info["columns"]]}')

        # Create database if it doesn't exist
        await self.create_database(database_name, output_location)

        # Create table based on format
        if schema_info['format'] == SchemaFormat.CSV:
            await self.ctx.info('Creating table for CSV format')
            await self.create_table_for_csv(
                database_name, table_name, schema_info, data_location, output_location
            )
        else:  # Parquet format
            await self.ctx.info('Creating table for Parquet format')
            await self.create_table_for_parquet(
                database_name, table_name, schema_info, data_location, output_location
            )

    async def execute_query(
        self, query: str, database_name: str, output_location: str
    ) -> AthenaQueryExecution:
        """Execute an Athena query.

        Args:
            query: SQL query to execute
            database_name: Athena database name to use
            output_location: S3 location for Athena query results

        Returns:
            AthenaQueryExecution: Query execution ID and status
        """
        try:
            await self.ctx.info(f'Executing Athena query on database {database_name}:')
            await self.ctx.info(f'Query: {query}')
            await self.ctx.info(f'Output location: {output_location}')

            # Start query execution
            response = self.athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': database_name},
                ResultConfiguration={'OutputLocation': output_location},
            )

            query_execution_id = response['QueryExecutionId']
            await self.ctx.info(f'Query execution ID: {query_execution_id}')

            return AthenaQueryExecution(query_execution_id=query_execution_id, status='STARTED')

        except Exception as e:
            await self.ctx.error(f'Error starting Athena query: {str(e)}')
            # Use shared error handler
            raise Exception(f'Error starting Athena query: {str(e)}')

    async def wait_for_query_completion(
        self, query_execution_id: str, max_retries: int = ATHENA_MAX_RETRIES
    ) -> Dict[str, Any]:
        """Wait for an Athena query to complete.

        Args:
            query_execution_id: Query execution ID
            max_retries: Maximum number of retries

        Returns:
            Dict[str, Any]: Query execution status
        """
        try:
            state = 'RUNNING'  # Initial state assumption
            retries = 0

            await self.ctx.info(f'Waiting for Athena query {query_execution_id} to complete...')

            while (state == 'RUNNING' or state == 'QUEUED') and retries < max_retries:
                response = self.athena_client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                state = response['QueryExecution']['Status']['State']

                await self.ctx.info(f'Query state: {state} (retry {retries}/{max_retries})')

                if state == 'FAILED':
                    reason = response['QueryExecution']['Status'].get(
                        'StateChangeReason', 'Unknown error'
                    )
                    await self.ctx.error(f'Query failed: {reason}')
                    raise Exception(f'Query failed: {reason}')
                elif state == 'SUCCEEDED':
                    await self.ctx.info(f'Query succeeded after {retries} retries')
                    return response['QueryExecution']

                # Wait before checking again
                await asyncio.sleep(ATHENA_RETRY_DELAY_SECONDS)
                retries += 1

            if retries >= max_retries:
                await self.ctx.error(f'Query timed out after {max_retries} retries')
                raise Exception('Query timed out')

            # This should never be reached due to the exception above, but return empty dict for type safety
            return {'status': 'ERROR', 'message': 'Query timed out'}

        except Exception as e:
            # Use shared error handler for consistent error reporting
            await self.ctx.error(f'Error waiting for query completion: {str(e)}')
            raise

    async def get_query_results(self, query_execution_id: str) -> Dict[str, Any]:
        """Get the results of a completed Athena query.

        Args:
            query_execution_id: Query execution ID

        Returns:
            Dict[str, Any]: Query results and metadata
        """
        try:
            # Get query results
            results_response = self.athena_client.get_query_results(
                QueryExecutionId=query_execution_id
            )

            # Process results
            columns = [
                col['Label']
                for col in results_response['ResultSet']['ResultSetMetadata']['ColumnInfo']
            ]
            rows = []

            # Skip header row if it exists
            result_rows = results_response['ResultSet']['Rows']
            start_index = (
                1 if len(result_rows) > 0 and len(columns) == len(result_rows[0]['Data']) else 0
            )

            for row in result_rows[start_index:]:
                values = []
                for item in row['Data']:
                    values.append(item.get('VarCharValue', ''))
                rows.append(dict(zip(columns, values)))

            return {'columns': columns, 'rows': rows}

        except Exception as e:
            # Use shared error handler for consistent error reporting
            await self.ctx.error(f'Error getting query results: {str(e)}')
            raise

    def determine_output_location(
        self, data_location: str, output_location: Optional[str] = None
    ) -> str:
        """Determine the output location for Athena query results.

        Args:
            data_location: S3 location of the data files
            output_location: User-provided output location

        Returns:
            str: S3 location for Athena query results
        """
        if output_location:
            return output_location

        # If output_location is not provided, use the same bucket as the data
        parsed_data_uri = urlparse(data_location)
        bucket = parsed_data_uri.netloc
        return f's3://{bucket}/athena-results/'


class StorageLensQueryTool:
    """Tool for querying S3 Storage Lens metrics using Athena."""

    def __init__(self, ctx: Context):
        """Initialize the manifest and Athena handlers.

        Args:
            ctx: MCP context for logging
        """
        self.ctx = ctx
        self.manifest_handler = ManifestHandler(ctx)
        self.athena_handler = AthenaHandler(ctx)

    async def query_storage_lens(
        self,
        query: str,
        manifest_location: str,
        database_name: str = STORAGE_LENS_DEFAULT_DATABASE,
        table_name: str = STORAGE_LENS_DEFAULT_TABLE,
        output_location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query S3 Storage Lens metrics using Athena.

        Args:
            query: SQL query to execute against Storage Lens data
            manifest_location: S3 URI to manifest file or folder
            database_name: Athena database name (defaults to 'storage_lens_db')
            table_name: Athena table name (defaults to 'storage_lens_metrics')
            output_location: S3 location for query results (optional)

        Returns:
            Dict[str, Any]: Query results and metadata
        """
        try:
            # 1. Locate and parse manifest file
            manifest = await self.manifest_handler.get_manifest(manifest_location)

            # 2. Extract data location and schema information
            data_location = self.manifest_handler.extract_data_location(manifest)
            schema_info = self.manifest_handler.parse_schema(manifest)

            # 3. Determine output location if not provided
            if not output_location:
                output_location = self.athena_handler.determine_output_location(data_location)

            # 4. Setup Athena database and table if needed
            await self.athena_handler.setup_table(
                database_name, table_name, schema_info, data_location, output_location
            )

            # 5. Replace {table} placeholder in query with actual table name
            formatted_query = query
            if '{table}' in query:
                formatted_query = query.replace('{table}', f'{database_name}.{table_name}')
            elif f'{database_name}.{table_name}' not in query:
                # If query doesn't contain the full table name and doesn't have the placeholder
                # then prepend the database and table name to the FROM clause
                if ' from ' in query.lower():
                    formatted_query = query.lower().replace(
                        ' from ', f' FROM {database_name}.{table_name} '
                    )
                else:
                    raise Exception(
                        'Query must either contain {table} placeholder or explicitly reference the table.'
                    )

            # 6. Execute query
            query_result = await self.athena_handler.execute_query(
                formatted_query, database_name, output_location
            )

            # 7. Wait for query to complete
            execution_details = await self.athena_handler.wait_for_query_completion(
                query_result['query_execution_id']
            )

            # 8. Get query results
            results = await self.athena_handler.get_query_results(
                query_result['query_execution_id']
            )

            # 9. Add query statistics and metadata
            stats = execution_details['Statistics']
            formatted_response = {
                'execution_time_ms': stats.get('TotalExecutionTimeInMillis', 0),
                'data_scanned_bytes': stats.get('DataScannedInBytes', 0),
                'engine_execution_time_ms': stats.get('EngineExecutionTimeInMillis', 0),
                'columns': results['columns'],
                'rows': results['rows'],
                'query': formatted_query,
                'manifest_location': manifest_location,
                'data_location': data_location,
            }

            return format_response('success', formatted_response)

        except Exception as e:
            # Use shared error handler for consistent error reporting
            return await handle_aws_error(self.ctx, e, 'query_storage_lens', 'Storage Lens')


@storage_lens_server.tool(
    name='storage-lens',
    description="""Query S3 Storage Lens metrics data using Athena SQL.

IMPORTANT USAGE GUIDELINES:
- Before using this tool, provide a 1-3 sentence explanation starting with "EXPLANATION:"
- Use standard SQL syntax for Athena queries
- Use {table} as a placeholder for the Storage Lens metrics table name
- Perform aggregations (GROUP BY) when analyzing data across multiple dimensions

This tool allows you to analyze S3 Storage Lens metrics data using SQL queries.
Storage Lens provides metrics about your S3 storage, including:

- Storage metrics: Total bytes, object counts by storage class
- Cost optimization metrics: Transition opportunities, incomplete multipart uploads
- Data protection metrics: Replication, versioning, encryption status
- Activity metrics: Upload, download, and request metrics

STORAGE LENS EXPORT SCHEMA:
The Storage Lens export data has the following standard columns:
- version_number: The version of the S3 Storage Lens metrics being used
- configuration_id: The configuration_id of your S3 Storage Lens configuration
- report_date: The date that the metrics were tracked
- aws_account_number: Your AWS account number
- aws_region: The AWS Region for which the metrics are being tracked
- storage_class: The storage class (STANDARD, STANDARD_IA, GLACIER, etc.)
- record_type: The type of artifact being reported (ACCOUNT, BUCKET, PREFIX, STORAGE_LENS_GROUP_BUCKET, STORAGE_LENS_GROUP_ACCOUNT)
- record_value: The value of the record_type artifact (account ID, bucket name, prefix, or Storage Lens group ARN)
- bucket_name: The name of the bucket (when record_type is BUCKET or PREFIX)
- metric_name: The name of the metric (e.g., 'StorageBytes', 'ObjectCount', 'EncryptedStorageBytes')
- metric_value: The numeric value of the metric

IMPORTANT: Metrics are stored in rows, not columns. Each row represents one metric value for a specific combination of dimensions.

Environment variables:
- STORAGE_LENS_MANIFEST_LOCATION: S3 URI to manifest file or folder (required)
- STORAGE_LENS_OUTPUT_LOCATION: S3 location for Athena query results (optional)

Example queries:
1. Top 10 buckets by storage size:
   SELECT
       bucket_name,
       SUM(CAST(metric_value AS BIGINT)) as total_size
   FROM {table}
   WHERE metric_name = 'StorageBytes'
   GROUP BY bucket_name
   ORDER BY total_size DESC
   LIMIT 10

2. Storage distribution by storage class:
   SELECT
       storage_class,
       SUM(CAST(metric_value AS BIGINT)) as total_size
   FROM {table}
   WHERE metric_name = 'StorageBytes'
   GROUP BY storage_class
   ORDER BY total_size DESC

3. Buckets with incomplete multipart uploads:
   SELECT
       bucket_name,
       SUM(CAST(metric_value AS BIGINT)) as incomplete_bytes
   FROM {table}
   WHERE metric_name = 'IncompleteMultipartUploadStorageBytes'
     AND CAST(metric_value AS BIGINT) > 0
   GROUP BY bucket_name
   ORDER BY incomplete_bytes DESC

4. Storage Distribution by Region and Storage Class:
   SELECT
       aws_region,
       storage_class,
       SUM(CAST(metric_value AS BIGINT)) as total_bytes
   FROM {table}
   WHERE metric_name = 'StorageBytes'
   GROUP BY aws_region, storage_class
   ORDER BY total_bytes DESC

5. Object Lifecycle Management Opportunities:
   SELECT
       aws_region,
       storage_class,
       SUM(CASE WHEN metric_name = 'NonCurrentVersionStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as noncurrent_bytes,
       SUM(CASE WHEN metric_name = 'StorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as total_bytes
   FROM {table}
   WHERE metric_name IN ('NonCurrentVersionStorageBytes', 'StorageBytes')
   GROUP BY aws_region, storage_class
   HAVING SUM(CASE WHEN metric_name = 'NonCurrentVersionStorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) > 0
   ORDER BY noncurrent_bytes DESC

6. Lifecycle Rule Analysis:
   SELECT
       bucket_name,
       SUM(CASE WHEN metric_name = 'TotalLifecycleRuleCount' THEN CAST(metric_value AS INTEGER) ELSE 0 END) as lifecycle_rule_count,
       SUM(CASE WHEN metric_name = 'StorageBytes' THEN CAST(metric_value AS BIGINT) ELSE 0 END) as total_bytes
   FROM {table}
   WHERE metric_name IN ('TotalLifecycleRuleCount', 'StorageBytes')
   GROUP BY bucket_name
   ORDER BY lifecycle_rule_count ASC, total_bytes DESC""",
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
        db_name = database_name or STORAGE_LENS_DEFAULT_DATABASE
        tbl_name = table_name or STORAGE_LENS_DEFAULT_TABLE

        # Create the query tool
        query_tool = StorageLensQueryTool(ctx)

        # Execute the query
        result = await query_tool.query_storage_lens(
            query=query,
            manifest_location=manifest_loc,
            database_name=db_name,
            table_name=tbl_name,
            output_location=output_loc,
        )

        return result

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'storage_lens_run_query', 'Athena')
