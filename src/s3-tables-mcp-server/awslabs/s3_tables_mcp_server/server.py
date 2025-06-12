#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""AWS S3 Tables MCP Server implementation.

This server provides a Model Context Protocol (MCP) interface for managing AWS S3 Tables,
enabling programmatic access to create, manage, and interact with S3-based table storage.
It supports operations for table buckets, namespaces, and individual S3 tables.
"""

from awslabs.s3_tables_mcp_server.constants import MCP_SERVER_VERSION
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional, Callable
import argparse
import functools

# Import modular components
from . import namespaces
from . import resources
from . import table_buckets
from . import tables
from .models import (
    EncryptionConfiguration,
    TableBucketMaintenanceConfigurationValue,
    TableBucketMaintenanceType,
    TABLE_BUCKET_NAME_PATTERN,
    TableMaintenanceType,
    TableMaintenanceConfigurationValue,
    TABLE_BUCKET_ARN_FIELD,
    NAMESPACE_NAME_FIELD,
    TABLE_NAME_FIELD,
    REGION_NAME_FIELD
)

# Initialize FastMCP app
app = FastMCP(
    name='s3-tables-server',
    instructions="The official MCP Server for interacting with AWS S3 Tables.",
    version=MCP_SERVER_VERSION,
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

@app.resource(
    uri='resource://table-buckets',
    name='ListTableBuckets',
    mime_type='application/json',
    description='Lists all S3 table buckets for your AWS account.'
)
async def list_table_buckets() -> str:
    """List all S3 table buckets for your AWS account.
    
    Permissions:
    You must have the s3tables:ListTableBuckets permission to use this operation.
    """
    return await resources.list_table_buckets_resource()


@app.resource(
    uri='resource://namespaces',
    name='ListNamespaces',
    mime_type='application/json',
    description='Lists all namespaces within all S3 table buckets.'
)
async def list_namespaces() -> str:
    """List all namespaces across all S3 table buckets.
    
    Permissions:
    You must have the s3tables:ListNamespaces permission to use this operation.
    """
    return await resources.list_namespaces_resource()


@app.resource(
    uri='resource://tables',
    name='ListTables',
    mime_type='application/json',
    description='List S3 tables across all table buckets and namespaces.'
)
async def list_tables() -> str:
    """List all S3 tables across all table buckets and namespaces.
    
    Permissions:
    You must have the s3tables:ListTables permission to use this operation.
    """
    return await resources.list_tables_resource()


@app.tool()
@write_operation
async def create_table_bucket(
    name: str = Field(
        ...,
        description='Name of the table bucket to create. Must be 3-63 characters long and contain only lowercase letters, numbers, and hyphens.',
        min_length=3,
        max_length=63,
        pattern=TABLE_BUCKET_NAME_PATTERN
    ),
    encryption_configuration: Optional[EncryptionConfiguration] = Field(
        None,
        description='The encryption configuration to use for the table bucket. This configuration specifies the default encryption settings that will be applied to all tables created in this bucket unless overridden at the table level.'
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Creates a table bucket."""
    return await table_buckets.create_table_bucket(
        name=name,
        encryption_configuration=encryption_configuration,
        region_name=region_name
    )

@app.tool()
@write_operation
async def create_namespace(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Create a new namespace.
    
    Creates a namespace. A namespace is a logical grouping of tables within your table bucket, 
    which you can use to organize tables.
    
    Permissions:
    You must have the s3tables:CreateNamespace permission to use this operation.
    """
    return await namespaces.create_namespace(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        region_name=region_name
    )

@app.tool()
@write_operation
async def create_table(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    format: str = Field(
        "ICEBERG",
        description='The format for the S3 table.',
        pattern=r'ICEBERG'
    ),
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description='The metadata for the S3 table.'
    ),
    encryption_configuration: Optional[EncryptionConfiguration] = Field(
        None,
        description='The encryption configuration to use for the S3 table. This configuration specifies the encryption algorithm and, if using SSE-KMS, the KMS key to use for encrypting the table.'
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Create a new S3 table.
    
    Creates a new S3 table associated with the given namespace in a table bucket.
    The table can be configured with specific format, metadata, and encryption settings.
    
    Permissions:
    You must have the s3tables:CreateTable permission to use this operation.
    If using metadata parameter, you must have the s3tables:PutTableData permission.
    If using encryption_configuration parameter, you must have the s3tables:PutTableEncryption permission.
    """
    from .models import OpenTableFormat, TableMetadata
    
    # Convert string parameter to enum value
    format_enum = OpenTableFormat(format) if format != "ICEBERG" else OpenTableFormat.ICEBERG
    
    # Convert metadata dict to TableMetadata if provided
    table_metadata = TableMetadata.model_validate(metadata) if metadata else None
    
    return await tables.create_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        format=format_enum,
        metadata=table_metadata,
        encryption_configuration=encryption_configuration,
        region_name=region_name
    )

@app.tool()
@write_operation
async def delete_table_bucket(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Delete a table bucket.
    
    Deletes a table bucket.
    
    Permissions:
    You must have the s3tables:DeleteTableBucket permission to use this operation.
    """
    return await table_buckets.delete_table_bucket(
        table_bucket_arn=table_bucket_arn,
        region_name=region_name
    )

@app.tool()
@write_operation
async def delete_namespace(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Delete a namespace.
    
    Deletes a namespace.
    
    Permissions:
    You must have the s3tables:DeleteNamespace permission to use this operation.
    """
    return await namespaces.delete_namespace(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        region_name=region_name
    )

@app.tool()
@write_operation
async def delete_table(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    version_token: Optional[str] = Field(
        None,
        description='The version token of the table. Must be 1-2048 characters long.'
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
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
        region_name=region_name
    )

@app.tool()
@write_operation
async def put_table_bucket_encryption(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    encryption_configuration: EncryptionConfiguration = Field(
        ...,
        description='The encryption configuration to apply to the table bucket.'
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Set the encryption configuration for a table bucket.
    
    Permissions:
    You must have the s3tables:PutTableBucketEncryption permission to use this operation.
    
    Note:
    If you choose SSE-KMS encryption you must grant the S3 Tables maintenance principal access to your KMS key.
    For more information, see Permissions requirements for S3 Tables SSE-KMS encryption in the Amazon Simple Storage Service User Guide.
    """
    return await table_buckets.put_table_bucket_encryption(
        table_bucket_arn=table_bucket_arn,
        encryption_configuration=encryption_configuration,
        region_name=region_name
    )

@app.tool()
@write_operation
async def put_table_bucket_maintenance_configuration(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    maintenance_type: TableBucketMaintenanceType = Field(
        ...,
        description='The type of the maintenance configuration.'
    ),
    value: TableBucketMaintenanceConfigurationValue = Field(
        ...,
        description='Defines the values of the maintenance configuration for the table bucket.'
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
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
        region_name=region_name
    )

@app.tool()
@write_operation
async def put_table_bucket_policy(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    resource_policy: str = Field(
        ...,
        description='The JSON that defines the policy.',
        min_length=1,
        max_length=20480
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Create or replace a table bucket policy.
    
    Creates a new maintenance configuration or replaces an existing table bucket policy for a table bucket.
    For more information, see Adding a table bucket policy in the Amazon Simple Storage Service User Guide.
    
    Permissions:
    You must have the s3tables:PutTableBucketPolicy permission to use this operation.
    """
    return await table_buckets.put_table_bucket_policy(
        table_bucket_arn=table_bucket_arn,
        resource_policy=resource_policy,
        region_name=region_name
    )

@app.tool()
@write_operation
async def delete_table_bucket_encryption(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Delete the encryption configuration for a table bucket.
    
    Deletes the encryption configuration for a table bucket.
    
    Permissions:
    You must have the s3tables:DeleteTableBucketEncryption permission to use this operation.
    """
    return await table_buckets.delete_table_bucket_encryption(
        table_bucket_arn=table_bucket_arn,
        region_name=region_name
    )

@app.tool()
@write_operation
async def delete_table_bucket_policy(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Delete a table bucket policy.
    
    Deletes a table bucket policy.
    
    Permissions:
    You must have the s3tables:DeleteTableBucketPolicy permission to use this operation.
    """
    return await table_buckets.delete_table_bucket_policy(
        table_bucket_arn=table_bucket_arn,
        region_name=region_name
    )

@app.tool()
@write_operation
async def delete_table_policy(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Delete a table policy.
    
    Deletes a table policy.
    
    Permissions:
    You must have the s3tables:DeleteTablePolicy permission to use this operation.
    """
    return await tables.delete_table_policy(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        region_name=region_name
    )

@app.tool()
@write_operation
async def get_table_encryption(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get the encryption configuration for an S3 table.
    
    Gets the encryption configuration for an S3 table, including the encryption algorithm
    and KMS key information if SSE-KMS is used.
    
    Permissions:
    You must have the s3tables:GetTableEncryption permission to use this operation.
    """
    return await tables.get_table_encryption(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        region_name=region_name
    )

@app.tool()
@write_operation
async def get_table_maintenance_configuration(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get details about the maintenance configuration of a table.
    
    Gets details about the maintenance configuration of a table. For more information, see S3 Tables maintenance in the Amazon Simple Storage Service User Guide.
    
    Permissions:
    You must have the s3tables:GetTableMaintenanceConfiguration permission to use this operation.
    """
    return await tables.get_table_maintenance_configuration(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        region_name=region_name
    )

@app.tool()
@write_operation
async def get_table_maintenance_job_status(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get the status of a maintenance job for a table.
    
    Gets the status of a maintenance job for a table. For more information, see S3 Tables maintenance in the Amazon Simple Storage Service User Guide.
    
    Permissions:
    You must have the s3tables:GetTableMaintenanceJobStatus permission to use this operation.
    """
    return await tables.get_table_maintenance_job_status(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        region_name=region_name
    )

@app.tool()
@write_operation
async def get_table_metadata_location(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get the location of the S3 table metadata.
    
    Gets the S3 URI location of the table metadata, which contains the schema and other
    table configuration information.
    
    Permissions:
    You must have the s3tables:GetTableMetadataLocation permission to use this operation.
    """
    return await tables.get_table_metadata_location(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        region_name=region_name
    )

@app.tool()
@write_operation
async def get_table_policy(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get details about a table policy.
    
    Gets details about a table policy. For more information, see Viewing a table policy in the Amazon Simple Storage Service User Guide.
    
    Permissions:
    You must have the s3tables:GetTablePolicy permission to use this operation.
    """
    return await tables.get_table_policy(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        region_name=region_name
    )

@app.tool()
@write_operation
async def put_table_maintenance_configuration(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    maintenance_type: TableMaintenanceType = Field(
        ...,
        description='The type of the maintenance configuration. Valid values are icebergCompaction or icebergSnapshotManagement.'
    ),
    value: TableMaintenanceConfigurationValue = Field(
        ...,
        description='Defines the values of the maintenance configuration for the table.'
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
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
        region_name=region_name
    )

@app.tool()
@write_operation
async def rename_table(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    new_name: Optional[str] = TABLE_NAME_FIELD,
    new_namespace_name: Optional[str] = NAMESPACE_NAME_FIELD,
    version_token: Optional[str] = Field(
        None,
        description='The version token of the S3 table. Must be 1-2048 characters long.',
        min_length=1,
        max_length=2048
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Rename an S3 table or move it to a different namespace.
    
    Renames an S3 table or moves it to a different namespace within the same table bucket.
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
        region_name=region_name
    )

@app.tool()
@write_operation
async def update_table_metadata_location(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    metadata_location: str = Field(
        ...,
        description='The new metadata location for the table. Must be 1-2048 characters long.',
        min_length=1,
        max_length=2048
    ),
    version_token: str = Field(
        ...,
        description='The version token of the table. Must be 1-2048 characters long.',
        min_length=1,
        max_length=2048
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Update the metadata location for a table.
    
    Updates the metadata location for a table. The metadata location of a table must be an S3 URI that begins with the table's warehouse location.
    The metadata location for an Apache Iceberg table must end with .metadata.json, or if the metadata file is Gzip-compressed, .metadata.json.gz.
    
    Permissions:
    You must have the s3tables:UpdateTableMetadataLocation permission to use this operation.
    """
    return await tables.update_table_metadata_location(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        metadata_location=metadata_location,
        version_token=version_token,
        region_name=region_name
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

    try:
        app.run()
    except Exception as e:
        print(f'Failed to start server: {str(e)}')

# FastMCP application runner
if __name__ == "__main__":
    main()
