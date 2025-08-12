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

"""AWS S3 Tables MCP Server implementation.

This server provides a Model Context Protocol (MCP) interface for managing AWS S3 Tables,
enabling programmatic access to create, manage, and interact with S3-based table storage.
It supports operations for table buckets, namespaces, and individual S3 tables.
"""

import argparse
import functools
import json
import os
import platform
import sys
import traceback
from .utils import set_user_agent_mode

# Import modular components
from awslabs.s3_tables_mcp_server import (
    __version__,
    database,
    namespaces,
    resources,
    s3_operations,
    table_buckets,
    tables,
)
from awslabs.s3_tables_mcp_server.constants import (
    NAMESPACE_NAME_FIELD,
    QUERY_FIELD,
    REGION_NAME_FIELD,
    S3_URL_FIELD,
    TABLE_BUCKET_ARN_FIELD,
    TABLE_BUCKET_NAME_PATTERN,
    TABLE_NAME_FIELD,
)
from awslabs.s3_tables_mcp_server.file_processor import (
    import_csv_to_table as import_csv_to_table_func,
)
from awslabs.s3_tables_mcp_server.file_processor import (
    import_parquet_to_table as import_parquet_to_table_func,
)
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated, Any, Callable, Dict, Optional


class S3TablesMCPServer(FastMCP):
    """Extended FastMCP server with write operation control."""

    def __init__(self, *args, **kwargs):
        """Initialize the S3 Tables MCP server with write operation control.

        Args:
            *args: Positional arguments passed to FastMCP
            **kwargs: Keyword arguments passed to FastMCP
        """
        super().__init__(*args, **kwargs)
        self.allow_write: bool = False

        os_name = platform.system().lower()
        if os_name == 'darwin':
            self.log_dir = os.path.expanduser('~/Library/Logs')
        elif os_name == 'windows':
            self.log_dir = os.path.expanduser('~/AppData/Local/Logs')
        else:
            self.log_dir = os.path.expanduser('~/.local/share/s3-tables-mcp-server/logs/')


# Initialize FastMCP app
app = S3TablesMCPServer(
    name='s3-tables-server',
    instructions='A Model Context Protocol (MCP) server that enables programmatic access to AWS S3 Tables. This server provides a comprehensive interface for creating, managing, and interacting with S3-based table storage, supporting operations for table buckets, namespaces, and individual S3 tables. It integrates with Amazon Athena for SQL query execution, allowing both read and write operations on your S3 Tables data.',
)


def write_operation(func: Callable) -> Callable:
    """Decorator to check if write operations are allowed.

    Args:
        func: The function to decorate

    Returns:
        The decorated function

    Raises:
        ValueError: If write operations are not allowed
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not app.allow_write:
            raise ValueError('Operation not permitted: Server is configured in read-only mode')
        return await func(*args, **kwargs)

    return wrapper


def log_tool_call_with_response(func):
    """Decorator to log tool call, response, and errors, using the function name automatically. Skips logging during tests if MCP_SERVER_DISABLE_LOGGING is set."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Disable logging during tests
        if os.environ.get('PYTEST_CURRENT_TEST') or os.environ.get('MCP_SERVER_DISABLE_LOGGING'):
            return await func(*args, **kwargs)
        tool_name = func.__name__
        # Log the call
        try:
            os.makedirs(app.log_dir, exist_ok=True)
            log_file = os.path.join(app.log_dir, 'mcp-server-awslabs.s3-tables-mcp-server.log')
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'tool': tool_name,
                'event': 'call',
                'args': args,
                'kwargs': kwargs,
                'mcp_version': __version__,
            }
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry, default=str) + '\n')
        except Exception as e:
            print(
                f"ERROR: Failed to create or write to log file in directory '{app.log_dir}': {e}",
                file=sys.stderr,
            )
            sys.exit(1)
        # Execute the function and log response or error
        try:
            response = await func(*args, **kwargs)
            try:
                log_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'tool': tool_name,
                    'event': 'response',
                    'response': response,
                    'mcp_version': __version__,
                }
                with open(log_file, 'a') as f:
                    f.write(json.dumps(log_entry, default=str) + '\n')
            except Exception as e:
                print(
                    f"ERROR: Failed to log response in directory '{app.log_dir}': {e}",
                    file=sys.stderr,
                )
            return response
        except Exception as e:
            tb = traceback.format_exc()
            try:
                log_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'tool': tool_name,
                    'event': 'error',
                    'error': str(e),
                    'traceback': tb,
                    'mcp_version': __version__,
                }
                with open(log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as log_e:
                print(
                    f"ERROR: Failed to log error in directory '{app.log_dir}': {log_e}",
                    file=sys.stderr,
                )
            raise

    return wrapper


def log_tool_call(tool_name, *args, **kwargs):
    """Log a tool call with its arguments and metadata to the server log file.

    Args:
        tool_name (str): The name of the tool being called.
        *args: Positional arguments passed to the tool.
        **kwargs: Keyword arguments passed to the tool.
    """
    try:
        os.makedirs(app.log_dir, exist_ok=True)
        log_file = os.path.join(app.log_dir, 'mcp-server-awslabs.s3-tables-mcp-server.log')
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tool': tool_name,
            'args': args,
            'kwargs': kwargs,
            'mcp_version': __version__,
        }
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(
            f"ERROR: Failed to create or write to log file in directory '{app.log_dir}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)


@app.tool()
@log_tool_call_with_response
async def list_table_buckets(
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
) -> str:
    """List all S3 table buckets for your AWS account.

    Permissions:
    You must have the s3tables:ListTableBuckets permission to use this operation.
    """
    return await resources.list_table_buckets_resource(region_name=region_name)


@app.tool()
@log_tool_call_with_response
async def list_namespaces(region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None) -> str:
    """List all namespaces across all S3 table buckets.

    Permissions:
    You must have the s3tables:ListNamespaces permission to use this operation.
    """
    return await resources.list_namespaces_resource(region_name=region_name)


@app.tool()
@log_tool_call_with_response
async def list_tables(region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None) -> str:
    """List all S3 tables across all table buckets and namespaces.

    Permissions:
    You must have the s3tables:ListTables permission to use this operation.
    """
    return await resources.list_tables_resource(region_name=region_name)


@app.tool()
@log_tool_call_with_response
@write_operation
async def create_table_bucket(
    name: Annotated[
        str,
        Field(
            ...,
            description='Name of the table bucket to create. Must be 3-63 characters long and contain only lowercase letters, numbers, and hyphens.',
            min_length=3,
            max_length=63,
            pattern=TABLE_BUCKET_NAME_PATTERN,
        ),
    ],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Creates an S3 table bucket.

    Permissions:
    You must have the s3tables:CreateTableBucket permission to use this operation.
    """
    return await table_buckets.create_table_bucket(name=name, region_name=region_name)


@app.tool()
@log_tool_call_with_response
@write_operation
async def create_namespace(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Create a new namespace in an S3 table bucket.

    Creates a namespace. A namespace is a logical grouping of tables within your S3 table bucket,
    which you can use to organize S3 tables.

    Permissions:
    You must have the s3tables:CreateNamespace permission to use this operation.
    """
    return await namespaces.create_namespace(
        table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region_name
    )


@app.tool()
@log_tool_call_with_response
@write_operation
async def create_table(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    format: Annotated[
        str, Field('ICEBERG', description='The format for the S3 table.', pattern=r'ICEBERG')
    ] = 'ICEBERG',
    metadata: Annotated[
        Optional[Dict[str, Any]], Field(None, description='The metadata for the S3 table.')
    ] = None,
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Create a new S3 table in an S3 table bucket.

    Creates a new S3 table associated with the given S3 namespace in an S3 table bucket.
    The S3 table can be configured with specific format and metadata settings. Metadata contains the schema of the table. Use double type for decimals.
    Do not use the metadata parameter if the schema is unclear.

    Example of S3 table metadata:
    {
        "metadata": {
            "iceberg": {
                "schema": {
                    "type": "struct",
                    "fields": [{
                            "id": 1,
                            "name": "customer_id",
                            "type": "long",
                            "required": true
                        },
                        {
                            "id": 2,
                            "name": "customer_name",
                            "type": "string",
                            "required": true
                        },
                        {
                            "id": 3,
                            "name": "customer_balance",
                            "type": "double",
                            "required": false
                        }
                    ]
                },
                "partition-spec": [
                    {
                        "source-id": 1,
                        "field-id": 1000,
                        "transform": "month",
                        "name": "sale_date_month"
                    }
                ],
                "table-properties": {
                    "description": "Customer information table with customer_id for joining with transactions"
                }
            }
        }
    }

    Permissions:
    You must have the s3tables:CreateTable permission to use this operation.
    If using metadata parameter, you must have the s3tables:PutTableData permission.
    """
    from awslabs.s3_tables_mcp_server.models import OpenTableFormat, TableMetadata

    # Convert string parameter to enum value
    format_enum = OpenTableFormat(format) if format != 'ICEBERG' else OpenTableFormat.ICEBERG

    # Convert metadata dict to TableMetadata if provided
    table_metadata = TableMetadata.model_validate(metadata) if metadata else None

    return await tables.create_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        format=format_enum,
        metadata=table_metadata,
        region_name=region_name,
    )


@app.tool()
@log_tool_call_with_response
async def get_table_maintenance_config(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Get details about the maintenance configuration of a table.

    Gets details about the maintenance configuration of a table. For more information, see S3 Tables maintenance in the Amazon Simple Storage Service User Guide.

    Permissions:
    You must have the s3tables:GetTableMaintenanceConfiguration permission to use this operation.
    """
    return await tables.get_table_maintenance_configuration(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region_name
    )


@app.tool()
@log_tool_call_with_response
async def get_maintenance_job_status(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Get the status of a maintenance job for a table.

    Gets the status of a maintenance job for a table. For more information, see S3 Tables maintenance in the Amazon Simple Storage Service User Guide.

    Permissions:
    You must have the s3tables:GetTableMaintenanceJobStatus permission to use this operation.
    """
    return await tables.get_table_maintenance_job_status(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region_name
    )


@app.tool()
@log_tool_call_with_response
async def get_table_metadata_location(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Get the location of the S3 table metadata.

    Gets the S3 URI location of the table metadata, which contains the schema and other
    table configuration information.

    Permissions:
    You must have the s3tables:GetTableMetadataLocation permission to use this operation.
    """
    return await tables.get_table_metadata_location(
        table_bucket_arn=table_bucket_arn, namespace=namespace, name=name, region_name=region_name
    )


@app.tool()
@log_tool_call_with_response
@write_operation
async def rename_table(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    new_name: Annotated[Optional[str], TABLE_NAME_FIELD] = None,
    new_namespace_name: Annotated[Optional[str], NAMESPACE_NAME_FIELD] = None,
    version_token: Annotated[
        Optional[str],
        Field(
            None,
            description='The version token of the S3 table. Must be 1-2048 characters long.',
            min_length=1,
            max_length=2048,
        ),
    ] = None,
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Rename an S3 table or move it to a different S3 namespace.

    Renames an S3 table or moves it to a different S3 namespace within the same S3 table bucket.
    This operation maintains the table's data and configuration while updating its location.

    Permissions:
    You must have the s3tables:RenameTable permission to use this operation.
    """
    return await tables.rename_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        new_name=new_name,
        new_namespace_name=new_namespace_name,
        version_token=version_token,
        region_name=region_name,
    )


@app.tool()
@log_tool_call_with_response
@write_operation
async def update_table_metadata_location(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    metadata_location: Annotated[
        str,
        Field(
            ...,
            description='The new metadata location for the S3 table. Must be 1-2048 characters long.',
            min_length=1,
            max_length=2048,
        ),
    ],
    version_token: Annotated[
        str,
        Field(
            ...,
            description='The version token of the S3 table. Must be 1-2048 characters long.',
            min_length=1,
            max_length=2048,
        ),
    ],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Update the metadata location for an S3 table.

    Updates the metadata location for an S3 table. The metadata location of an S3 table must be an S3 URI that begins with the S3 table's warehouse location.
    The metadata location for an Apache Iceberg S3 table must end with .metadata.json, or if the metadata file is Gzip-compressed, .metadata.json.gz.

    Permissions:
    You must have the s3tables:UpdateTableMetadataLocation permission to use this operation.
    """
    return await tables.update_table_metadata_location(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        metadata_location=metadata_location,
        version_token=version_token,
        region_name=region_name,
    )


def _default_uri_for_region(region: str) -> str:
    return f'https://s3tables.{region}.amazonaws.com/iceberg'


@app.tool()
@log_tool_call_with_response
async def query_database(
    warehouse: Annotated[str, Field(..., description='Warehouse string for Iceberg catalog')],
    region: Annotated[
        str, Field(..., description='AWS region for S3Tables/Iceberg REST endpoint')
    ],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    query: Annotated[str, QUERY_FIELD],
    uri: Annotated[str, Field(..., description='REST URI for Iceberg catalog')],
    catalog_name: Annotated[
        str, Field('s3tablescatalog', description='Catalog name')
    ] = 's3tablescatalog',
    rest_signing_name: Annotated[
        str, Field('s3tables', description='REST signing name')
    ] = 's3tables',
    rest_sigv4_enabled: Annotated[str, Field('true', description='Enable SigV4 signing')] = 'true',
):
    """Execute SQL queries against S3 Tables using PyIceberg/Daft.

    This tool provides a secure interface to run read-only SQL queries against your S3 Tables data using the PyIceberg and Daft engine.
    Use a correct region for warehouse, region, and uri.

    Example input values:
        warehouse: 'arn:aws:s3tables:<Region>:<accountID>:bucket/<bucketname>'
        region: 'us-west-2'
        namespace: 'retail_data'
        query: 'SELECT * FROM customers LIMIT 10'
        uri: 'https://s3tables.us-west-2.amazonaws.com/iceberg'
        catalog_name: 's3tablescatalog'
        rest_signing_name: 's3tables'
        rest_sigv4_enabled: 'true'
    """
    if uri is None:
        uri = _default_uri_for_region(region)
    return await database.query_database_resource(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        query=query,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )


@app.tool()
@log_tool_call_with_response
@write_operation
async def import_csv_to_table(
    warehouse: Annotated[str, Field(..., description='Warehouse string for Iceberg catalog')],
    region: Annotated[
        str, Field(..., description='AWS region for S3Tables/Iceberg REST endpoint')
    ],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    table_name: Annotated[str, TABLE_NAME_FIELD],
    s3_url: Annotated[str, S3_URL_FIELD],
    uri: Annotated[str, Field(..., description='REST URI for Iceberg catalog')],
    catalog_name: Annotated[
        str, Field('s3tablescatalog', description='Catalog name')
    ] = 's3tablescatalog',
    rest_signing_name: Annotated[
        str, Field('s3tables', description='REST signing name')
    ] = 's3tables',
    rest_sigv4_enabled: Annotated[str, Field('true', description='Enable SigV4 signing')] = 'true',
    preserve_case: Annotated[
        bool, Field(..., description='Preserve case of column names')
    ] = False,
) -> dict:
    """Import data from a CSV file into an S3 table.

    This tool reads data from a CSV file stored in S3 and imports it into an S3 table.
    If the table doesn't exist, it will be created with a schema inferred from the CSV file.
    If the table exists, the CSV file schema must be compatible with the table's schema.
    The tool will validate the schema before attempting to import the data.
    If preserve_case is True, the column names will not be converted to snake_case. Otherwise, the column names will be converted to snake_case.

    Returns error dictionary with status and error message if:
        - URL is not a valid S3 URL
        - File is not a CSV file
        - File cannot be accessed
        - Table does not exist
        - CSV headers don't match table schema
        - Any other error occurs

    Example input values:
        warehouse: 'arn:aws:s3tables:<Region>:<accountID>:bucket/<bucketname>'
        region: 'us-west-2'
        namespace: 'retail_data'
        table_name: 'customers'
        s3_url: 's3://bucket-name/path/to/file.csv'
        uri: 'https://s3tables.us-west-2.amazonaws.com/iceberg'
        catalog_name: 's3tablescatalog'
        rest_signing_name: 's3tables'
        rest_sigv4_enabled: 'true'
        preserve_case: False

    Permissions:
    You must have:
    - s3:GetObject permission for the CSV file
    - s3tables:GetTable and s3tables:GetTables permissions to access table information
    - s3tables:PutTableData permission to write to the table
    """
    if uri is None:
        uri = _default_uri_for_region(region)
    return await import_csv_to_table_func(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
        preserve_case=preserve_case,
    )


@app.tool()
@log_tool_call_with_response
@write_operation
async def import_parquet_to_table(
    warehouse: Annotated[str, Field(..., description='Warehouse string for Iceberg catalog')],
    region: Annotated[
        str, Field(..., description='AWS region for S3Tables/Iceberg REST endpoint')
    ],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    table_name: Annotated[str, TABLE_NAME_FIELD],
    s3_url: Annotated[str, S3_URL_FIELD],
    uri: Annotated[str, Field(..., description='REST URI for Iceberg catalog')],
    catalog_name: Annotated[
        str, Field('s3tablescatalog', description='Catalog name')
    ] = 's3tablescatalog',
    rest_signing_name: Annotated[
        str, Field('s3tables', description='REST signing name')
    ] = 's3tables',
    rest_sigv4_enabled: Annotated[str, Field('true', description='Enable SigV4 signing')] = 'true',
    preserve_case: Annotated[
        bool, Field(..., description='Preserve case of column names')
    ] = False,
) -> dict:
    """Import data from a Parquet file into an S3 table.

    This tool reads data from a Parquet file stored in S3 and imports it into an S3 table.
    If the table doesn't exist, it will be created with a schema inferred from the Parquet file.
    If the table exists, the Parquet file schema must be compatible with the table's schema.
    The tool will validate the schema before attempting to import the data.
    If preserve_case is True, the column names will not be converted to snake_case. Otherwise, the column names will be converted to snake_case.

    Returns error dictionary with status and error message if:
        - URL is not a valid S3 URL
        - File is not a Parquet file
        - File cannot be accessed
        - Parquet schema is incompatible with existing table schema
        - Any other error occurs

    Returns success dictionary with:
        - status: 'success'
        - message: Success message with row count
        - rows_processed: Number of rows imported
        - file_processed: Name of the processed file
        - table_created: True if a new table was created

    Example input values:
        warehouse: 'arn:aws:s3tables:<Region>:<accountID>:bucket/<bucketname>'
        region: 'us-west-2'
        namespace: 'retail_data'
        table_name: 'customers'
        s3_url: 's3://bucket-name/path/to/file.parquet'
        uri: 'https://s3tables.us-west-2.amazonaws.com/iceberg'
        catalog_name: 's3tablescatalog'
        rest_signing_name: 's3tables'
        rest_sigv4_enabled: 'true'
        preserve_case: False

    Permissions:
    You must have:
    - s3:GetObject permission for the Parquet file
    - s3tables:GetTable and s3tables:GetTables permissions to access table information
    - s3tables:PutTableData permission to write to the table
    - s3tables:CreateTable permission (if table doesn't exist)
    """
    if uri is None:
        uri = _default_uri_for_region(region)
    return await import_parquet_to_table_func(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        s3_url=s3_url,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
        preserve_case=preserve_case,
    )


@app.tool()
@log_tool_call_with_response
async def get_bucket_metadata_config(
    bucket: Annotated[
        str,
        Field(
            ...,
            description='The name of the S3 bucket to get metadata table configuration for.',
            min_length=1,
        ),
    ],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
) -> dict:
    """Get the metadata table configuration for a regular general purpose S3 bucket.

    Retrieves the metadata table configuration for a regular general purpose bucket in s3. This configuration
    determines how metadata is stored and managed for the bucket.
    The response includes:
    - S3 Table Bucket ARN
    - S3 Table ARN
    - S3 Table Name
    - S3 Table Namespace

    Description:
    Amazon S3 Metadata accelerates data discovery by automatically capturing metadata for the objects in your general purpose buckets and storing it in read-only, fully managed Apache Iceberg tables that you can query. These read-only tables are called metadata tables. As objects are added to, updated, and removed from your general purpose buckets, S3 Metadata automatically refreshes the corresponding metadata tables to reflect the latest changes.
    By default, S3 Metadata provides three types of metadata:
    - System-defined metadata, such as an object's creation time and storage class
    - Custom metadata, such as tags and user-defined metadata that was included during object upload
    - Event metadata, such as when an object is updated or deleted, and the AWS account that made the request

    Metadata table schema:
    - bucket: String
    - key: String
    - sequence_number: String
    - record_type: String
    - record_timestamp: Timestamp (no time zone)
    - version_id: String
    - is_delete_marker: Boolean
    - size: Long
    - last_modified_date: Timestamp (no time zone)
    - e_tag: String
    - storage_class: String
    - is_multipart: Boolean
    - encryption_status: String
    - is_bucket_key_enabled: Boolean
    - kms_key_arn: String
    - checksum_algorithm: String
    - object_tags: Map<String, String>
    - user_metadata: Map<String, String>
    - requester: String
    - source_ip_address: String
    - request_id: String

    Permissions:
    You must have the s3:GetBucketMetadataConfiguration permission to use this operation.
    """
    return await s3_operations.get_bucket_metadata_table_configuration(
        bucket=bucket, region_name=region_name
    )


@app.tool()
@log_tool_call_with_response
@write_operation
async def append_rows_to_table(
    warehouse: Annotated[str, Field(..., description='Warehouse string for Iceberg catalog')],
    region: Annotated[
        str, Field(..., description='AWS region for S3Tables/Iceberg REST endpoint')
    ],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    table_name: Annotated[str, TABLE_NAME_FIELD],
    rows: Annotated[list[dict], Field(..., description='List of rows to append, each as a dict')],
    uri: Annotated[str, Field(..., description='REST URI for Iceberg catalog')],
    catalog_name: Annotated[
        str, Field('s3tablescatalog', description='Catalog name')
    ] = 's3tablescatalog',
    rest_signing_name: Annotated[
        str, Field('s3tables', description='REST signing name')
    ] = 's3tables',
    rest_sigv4_enabled: Annotated[str, Field('true', description='Enable SigV4 signing')] = 'true',
) -> dict:
    """Append rows to an Iceberg table using PyIceberg/Daft.

    This tool appends data rows to an existing Iceberg table using the PyIceberg engine.
    The rows parameter must be a list of dictionaries, each representing a row.
    Check the schema of the table before appending rows.

    Example input values:
        warehouse: 'arn:aws:s3tables:<Region>:<accountID>:bucket/<bucketname>'
        region: 'us-west-2'
        namespace: 'retail_data'
        table_name: 'customers'
        rows: [{"customer_id": 1, "customer_name": "Alice"}, ...]
        uri: 'https://s3tables.us-west-2.amazonaws.com/iceberg'
        catalog_name: 's3tablescatalog'
        rest_signing_name: 's3tables'
        rest_sigv4_enabled: 'true'
    """
    if uri is None:
        uri = _default_uri_for_region(region)
    return await database.append_rows_to_table_resource(
        warehouse=warehouse,
        region=region,
        namespace=namespace,
        table_name=table_name,
        rows=rows,
        uri=uri,
        catalog_name=catalog_name,
        rest_signing_name=rest_signing_name,
        rest_sigv4_enabled=rest_sigv4_enabled,
    )


def main():
    """Run the MCP server with CLI argument support.

    This function initializes and runs the AWS S3 Tables MCP server, which provides
    programmatic access to manage S3 tables through the Model Context Protocol.
    """
    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for S3 Tables'
    )
    parser.add_argument(
        '--allow-write',
        action='store_true',
        help='Allow write operations. By default, the server runs in read-only mode.',
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default=None,
        help='Directory to write logs to. Defaults to /var/logs on Linux and ~/Library/Logs on MacOS.',
    )

    args = parser.parse_args()

    app.allow_write = args.allow_write
    set_user_agent_mode(args.allow_write)

    # Determine log directory
    if args.log_dir:
        app.log_dir = os.path.expanduser(args.log_dir)

    # Log program startup details
    log_tool_call(
        'server_start',
        argv=sys.argv,
        parsed_args=vars(args),
        mcp_version=__version__,
        python_version=sys.version,
        platform=platform.platform(),
    )

    app.run()


# FastMCP application runner
if __name__ == '__main__':
    print('Starting S3 Tables MCP server...')
    main()
