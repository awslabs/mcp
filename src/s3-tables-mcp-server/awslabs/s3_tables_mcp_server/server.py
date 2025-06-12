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

"""AWS S3 Tables MCP Server implementation."""

from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional

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
    version='0.1.0',
    dependencies=[
        'pydantic',
        'loguru',
    ],
)

@app.resource(
    uri='resource://table-buckets',
    name='ListTableBuckets',
    mime_type='application/json',
    description='Lists all table buckets for your account.'
)
async def list_table_buckets() -> str:
    """List all table buckets for your account.
    
    Permissions:
    You must have the s3tables:ListTableBuckets permission to use this operation.
    """
    return await resources.list_table_buckets_resource()


@app.resource(
    uri='resource://namespaces',
    name='ListNamespaces',
    mime_type='application/json',
    description='Lists all namespaces within all table buckets.'
)
async def list_namespaces() -> str:
    """List all namespaces across all table buckets.
    
    Permissions:
    You must have the s3tables:ListNamespaces permission to use this operation.
    """
    return await resources.list_namespaces_resource()


@app.resource(
    uri='resource://tables',
    name='ListTables',
    mime_type='application/json',
    description='List tables across all table buckets and namespaces.'
)
async def list_tables() -> str:
    """List all tables across all table buckets and namespaces.
    
    Permissions:
    You must have the s3tables:ListTables permission to use this operation.
    """
    return await resources.list_tables_resource()


@app.tool()
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

# Register Table Management Tools
@app.tool()
async def create_table(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    format: str = Field(
        "ICEBERG",
        description='The format for the table.',
        pattern=r'ICEBERG'
    ),
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description='The metadata for the table.'
    ),
    encryption_configuration: Optional[EncryptionConfiguration] = Field(
        None,
        description='The encryption configuration to use for the table. This configuration specifies the encryption algorithm and, if using SSE-KMS, the KMS key to use for encrypting the table.'
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Create a new s3 table.
    
    Creates a new table associated with the given namespace in a table bucket.
    
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
async def get_table_bucket(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get details about a table bucket.
    
    Gets details on a table bucket.
    
    Permissions:
    You must have the s3tables:GetTableBucket permission to use this operation.
    """
    return await table_buckets.get_table_bucket(
        table_bucket_arn=table_bucket_arn,
        region_name=region_name
    )

@app.tool()
async def get_namespace(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get details about a namespace.
    
    Gets details about a namespace.
    
    Permissions:
    You must have the s3tables:GetNamespace permission to use this operation.
    """
    return await namespaces.get_namespace(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        region_name=region_name
    )

@app.tool()
async def get_table(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get details about a table.
    
    Gets details about a table.
    
    Permissions:
    You must have the s3tables:GetTable permission to use this operation.
    """
    return await tables.get_table(
        table_bucket_arn=table_bucket_arn,
        namespace=namespace,
        name=name,
        region_name=region_name
    )

@app.tool()
async def get_table_bucket_encryption(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get the encryption configuration for a table bucket.
    
    Gets the encryption configuration for a table bucket.
    
    Permissions:
    You must have the s3tables:GetTableBucketEncryption permission to use this operation.
    """
    return await table_buckets.get_table_bucket_encryption(
        table_bucket_arn=table_bucket_arn,
        region_name=region_name
    )

@app.tool()
async def get_table_bucket_maintenance_configuration(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get details about a maintenance configuration for a table bucket.
    
    Gets details about a maintenance configuration for a given table bucket.
    
    Permissions:
    You must have the s3tables:GetTableBucketMaintenanceConfiguration permission to use this operation.
    """
    return await table_buckets.get_table_bucket_maintenance_configuration(
        table_bucket_arn=table_bucket_arn,
        region_name=region_name
    )

@app.tool()
async def get_table_bucket_policy(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get details about a table bucket policy.
    
    Gets details about a table bucket policy.
    
    Permissions:
    You must have the s3tables:GetTableBucketPolicy permission to use this operation.
    """
    return await table_buckets.get_table_bucket_policy(
        table_bucket_arn=table_bucket_arn,
        region_name=region_name
    )

@app.tool()
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
async def get_table_encryption(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get the encryption configuration for a table.
    
    Gets the encryption configuration for a table.
    
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
async def get_table_metadata_location(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Get the location of the table metadata.
    
    Gets the location of the table metadata.
    
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
async def rename_table(
    table_bucket_arn: str = TABLE_BUCKET_ARN_FIELD,
    namespace: str = NAMESPACE_NAME_FIELD,
    name: str = TABLE_NAME_FIELD,
    new_name: Optional[str] = TABLE_NAME_FIELD,
    new_namespace_name: Optional[str] = NAMESPACE_NAME_FIELD,
    version_token: Optional[str] = Field(
        None,
        description='The version token of the table. Must be 1-2048 characters long.',
        min_length=1,
        max_length=2048
    ),
    region_name: Optional[str] = REGION_NAME_FIELD
):
    """Rename a table or a namespace.
    
    Renames a table or a namespace. For more information, see S3 Tables in the Amazon Simple Storage Service User Guide.
    
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

# FastMCP application runner
if __name__ == "__main__":
    import asyncio
    print("Starting list_tables test...")
    result = asyncio.run(list_tables())
    print("Result:", result)
    app.run()
