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

# Import modular components
from awslabs.s3_tables_mcp_server import (
    __version__,
    database,
    file_processor,
    namespaces,
    resources,
    s3_operations,
    table_buckets,
    tables,
)
from awslabs.s3_tables_mcp_server.constants import (
    NAMESPACE_NAME_FIELD,
    OUTPUT_LOCATION_FIELD,
    QUERY_FIELD,
    REGION_NAME_FIELD,
    S3_URL_FIELD,
    TABLE_BUCKET_ARN_FIELD,
    TABLE_BUCKET_NAME_PATTERN,
    TABLE_NAME_FIELD,
    WORKGROUP_FIELD,
)
from awslabs.s3_tables_mcp_server.models import (
    TableBucketMaintenanceConfigurationValue,
    TableBucketMaintenanceType,
    TableMaintenanceConfigurationValue,
    TableMaintenanceType,
)
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


# Initialize FastMCP app
app = S3TablesMCPServer(
    name='s3-tables-server',
    instructions='A Model Context Protocol (MCP) server that enables programmatic access to AWS S3 Tables. This server provides a comprehensive interface for creating, managing, and interacting with S3-based table storage, supporting operations for table buckets, namespaces, and individual S3 tables. It integrates with Amazon Athena for SQL query execution, allowing both read and write operations on your S3 Tables data.',
    version=__version__,
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


@app.tool()
async def list_table_buckets() -> str:
    """List all S3 table buckets for your AWS account.

    Permissions:
    You must have the s3tables:ListTableBuckets permission to use this operation.
    """
    return await resources.list_table_buckets_resource()


@app.tool()
async def list_namespaces() -> str:
    """List all namespaces across all S3 table buckets.

    Permissions:
    You must have the s3tables:ListNamespaces permission to use this operation.
    """
    return await resources.list_namespaces_resource()


@app.tool()
async def list_tables() -> str:
    """List all S3 tables across all table buckets and namespaces.

    Permissions:
    You must have the s3tables:ListTables permission to use this operation.
    """
    return await resources.list_tables_resource()


@app.tool()
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
@write_operation
async def delete_table_bucket(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Delete an S3 table bucket.

    Deletes an S3 table bucket.

    Permissions:
    You must have the s3tables:DeleteTableBucket permission to use this operation.
    """
    return await table_buckets.delete_table_bucket(
        table_bucket_arn=table_bucket_arn, region_name=region_name
    )


@app.tool()
@write_operation
async def delete_namespace(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Delete a namespace.

    Deletes a namespace.

    Permissions:
    You must have the s3tables:DeleteNamespace permission to use this operation.
    """
    return await namespaces.delete_namespace(
        table_bucket_arn=table_bucket_arn, namespace=namespace, region_name=region_name
    )


@app.tool()
@write_operation
async def delete_table(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    version_token: Annotated[
        Optional[str],
        Field(None, description='The version token of the table. Must be 1-2048 characters long.'),
    ] = None,
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Delete a table.

    Deletes a table.

    Permissions:
    You must have the s3tables:DeleteTable permission to use this operation.
    """
    return await tables.delete_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        version_token=version_token,
        region_name=region_name,
    )


@app.tool()
@write_operation
async def put_bucket_maintenance_config(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    maintenance_type: Annotated[
        TableBucketMaintenanceType,
        Field(..., description='The type of the maintenance configuration.'),
    ],
    value: Annotated[
        TableBucketMaintenanceConfigurationValue,
        Field(
            ...,
            description='Defines the values of the maintenance configuration for the table bucket.',
        ),
    ],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Create or replace a maintenance configuration for a table bucket.

    Creates a new maintenance configuration or replaces an existing maintenance configuration for a table bucket.
    For more information, see Amazon S3 table bucket maintenance in the Amazon Simple Storage Service User Guide.

    Permissions:
    You must have the s3tables:PutTableBucketMaintenanceConfiguration permission to use this operation.
    """
    return await table_buckets.put_table_bucket_maintenance_configuration(
        table_bucket_arn=table_bucket_arn,
        maintenance_type=maintenance_type,
        value=value,
        region_name=region_name,
    )


@app.tool()
@write_operation
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
@write_operation
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
@write_operation
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
@write_operation
async def put_table_maintenance_config(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    maintenance_type: Annotated[
        TableMaintenanceType,
        Field(
            ...,
            description='The type of the maintenance configuration. Valid values are icebergCompaction or icebergSnapshotManagement.',
        ),
    ],
    value: Annotated[
        TableMaintenanceConfigurationValue,
        Field(
            ..., description='Defines the values of the maintenance configuration for the table.'
        ),
    ],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
):
    """Create or replace a maintenance configuration for a table.

    Creates a new maintenance configuration or replaces an existing maintenance configuration for a table.
    For more information, see S3 Tables maintenance in the Amazon Simple Storage Service User Guide.

    Permissions:
    You must have the s3tables:PutTableMaintenanceConfiguration permission to use this operation.
    """
    return await tables.put_table_maintenance_configuration(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        maintenance_type=maintenance_type,
        value=value,
        region_name=region_name,
    )


@app.tool()
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


@app.tool()
async def query_database(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    query: Annotated[str, QUERY_FIELD],
    output_location: Annotated[Optional[str], OUTPUT_LOCATION_FIELD] = None,
    workgroup: Annotated[str, WORKGROUP_FIELD] = 'primary',
):
    """Execute SQL queries against S3 Tables using Athena.

    This tool provides a secure interface to run read-only SQL queries against your S3 Tables data.
    It leverages Athena for query execution and supports standard SQL operations including SELECT,
    SHOW, DESCRIBE, and Common Table Expressions (CTEs). If a write operation is detected, the tool will return an error.

    The tool automatically handles query execution, result retrieval, and proper formatting of the
    response.

    Examples:
    - SELECT c.customer_id, c.first_name, c.last_name, c.email, t.transaction_id, t.product_name, t.total_amount, t.transaction_date FROM customers c INNER JOIN transactions t ON CONCAT('CUST-', CAST(c.customer_id AS VARCHAR)) = t.customer_id
    - SELECT * FROM customers ORDER BY customer_id LIMIT 10
    - DESCRIBE transactions

    Permissions:
    You must have the necessary Athena permissions to execute queries, including:
    - Access to the specified workgroup
    - GetDataCatalog permission for external catalogs
    - Appropriate IAM permissions for the S3 locations
    """
    try:
        return await database.query_database_resource(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
            output_location=output_location,
            workgroup=workgroup,
        )
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@app.tool()
@write_operation
async def modify_database(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    query: Annotated[str, QUERY_FIELD],
    output_location: Annotated[Optional[str], OUTPUT_LOCATION_FIELD] = None,
    workgroup: Annotated[str, WORKGROUP_FIELD] = 'primary',
):
    """Execute SQL queries against S3 Tables using Athena, including write operations.

    This tool provides a secure interface to run SQL queries against your S3 Tables data,
    including write operations like INSERT, UPDATE, DELETE, etc. It leverages Athena for
    query execution and supports all standard SQL operations.

    The tool automatically handles query execution, result retrieval, and proper formatting of the
    response.

    Examples:
    - INSERT INTO customers (customer_id, first_name, last_name, email) VALUES (1, 'John', 'Doe', 'john.doe@example.com')
    - UPDATE customers SET email = 'john.doe@example.com' WHERE customer_id = 1
    - DELETE FROM customers WHERE customer_id = 1

    Permissions:
    You must have the necessary Athena permissions to execute queries, including:
    - Access to the specified workgroup
    - GetDataCatalog permission for external catalogs
    - Appropriate IAM permissions for the S3 locations
    - Write permissions for the target table
    """
    try:
        return await database.modify_database_resource(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
            query=query,
            output_location=output_location,
            workgroup=workgroup,
        )
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@app.tool()
async def preview_csv_file(
    s3_url: Annotated[str, S3_URL_FIELD],
) -> dict:
    """Preview the structure of a CSV file stored in S3.

    This tool provides a quick preview of a CSV file's structure by reading
    only the headers and first row of data from an S3 location. It's useful for
    understanding the schema and data format without downloading the entire file.
    It can be used before creating an s3 table from a csv file to get the schema and data format.

    Returns error dictionary with status and error message if:
        - URL is not a valid S3 URL
        - File is not a CSV file
        - File cannot be accessed
        - Any other error occurs

    Permissions:
    You must have the s3:GetObject permission for the S3 bucket and key.
    """
    return file_processor.preview_csv_structure(s3_url)


@app.tool()
@write_operation
async def import_csv_to_table(
    table_bucket_arn: Annotated[str, TABLE_BUCKET_ARN_FIELD],
    namespace: Annotated[str, NAMESPACE_NAME_FIELD],
    name: Annotated[str, TABLE_NAME_FIELD],
    s3_url: Annotated[str, S3_URL_FIELD],
    region_name: Annotated[Optional[str], REGION_NAME_FIELD] = None,
) -> dict:
    """Import data from a CSV file into an S3 table.

    This tool reads data from a CSV file stored in S3 and imports it into an existing S3 table.
    The CSV file must have headers that match the table's schema. The tool will validate the CSV structure
    before attempting to import the data.

    To create a table, first use the preview_csv_file tool to get the schema and data format.
    Then use the create_table tool to create the table.

    Returns error dictionary with status and error message if:
        - URL is not a valid S3 URL
        - File is not a CSV file
        - File cannot be accessed
        - Table does not exist
        - CSV headers don't match table schema
        - Any other error occurs

    Permissions:
    You must have:
    - s3:GetObject permission for the CSV file
    - glue:GetCatalog permission to access the Glue catalog
    - glue:GetDatabase and glue:GetDatabases permissions to access database information
    - glue:GetTable and glue:GetTables permissions to access table information
    - glue:CreateTable and glue:UpdateTable permissions to modify table metadata
    """
    return await file_processor.import_csv_to_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        s3_url=s3_url,
        region_name=region_name,
    )


@app.tool()
@write_operation
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
    You must have the s3:GetBucketMetadataTableConfiguration permission to use this operation.
    """
    return await s3_operations.get_bucket_metadata_table_configuration(
        bucket=bucket, region_name=region_name
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

    args = parser.parse_args()

    app.allow_write = args.allow_write

    app.run()


# FastMCP application runner
if __name__ == '__main__':
    print('Starting S3 Tables MCP server...')
    main()
