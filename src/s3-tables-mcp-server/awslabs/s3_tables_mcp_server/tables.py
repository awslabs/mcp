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

"""Table Management tools for S3 Tables MCP Server."""

from .models import (
    OpenTableFormat,
    TableMaintenanceConfigurationValue,
    TableMaintenanceType,
    TableMetadata,
)
from .utils import get_s3tables_client, handle_exceptions
from typing import Any, Dict, Optional


@handle_exceptions
async def create_table(
    table_bucket_arn: str,
    namespace: str,
    name: str,
    format: OpenTableFormat = OpenTableFormat.ICEBERG,
    metadata: Optional[TableMetadata] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new table associated with the given namespace in a table bucket.

    Permissions:
    You must have the s3tables:CreateTable permission to use this operation.
    If using metadata parameter, you must have the s3tables:PutTableData permission.
    """
    client = get_s3tables_client(region_name)

    # Prepare parameters for create_table
    params: Dict[str, Any] = {
        'tableBucketARN': table_bucket_arn,
        'namespace': namespace,
        'name': name,
        'format': format.value,
    }

    # Add metadata if provided
    if metadata:
        params['metadata'] = metadata.model_dump(by_alias=True, exclude_none=True)

    response = client.create_table(**params)
    return dict(response)


@handle_exceptions
async def delete_table(
    table_bucket_arn: str,
    namespace: str,
    name: str,
    version_token: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a table.

    Permissions:
    You must have the s3tables:DeleteTable permission to use this operation.
    """
    client = get_s3tables_client(region_name)

    # Prepare parameters for delete_table
    params: Dict[str, Any] = {
        'tableBucketARN': table_bucket_arn,
        'namespace': namespace,
        'name': name,
    }

    # Add version token if provided
    if version_token:
        params['versionToken'] = version_token

    response = client.delete_table(**params)
    return dict(response)


@handle_exceptions
async def get_table(
    table_bucket_arn: str, namespace: str, name: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get details about a table.

    Gets details about a table.

    Permissions:
    You must have the s3tables:GetTable permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table(tableBucketARN=table_bucket_arn, namespace=namespace, name=name)
    return dict(response)


@handle_exceptions
async def delete_table_policy(
    table_bucket_arn: str, namespace: str, name: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Delete a table policy.

    Deletes a table policy.

    Permissions:
    You must have the s3tables:DeleteTablePolicy permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.delete_table_policy(
        tableBucketARN=table_bucket_arn, namespace=namespace, name=name
    )
    return dict(response)


@handle_exceptions
async def get_table_maintenance_configuration(
    table_bucket_arn: str, namespace: str, name: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get details about the maintenance configuration of a table.

    Gets details about the maintenance configuration of a table. For more information, see S3 Tables maintenance in the Amazon Simple Storage Service User Guide.

    Permissions:
    You must have the s3tables:GetTableMaintenanceConfiguration permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table_maintenance_configuration(
        tableBucketARN=table_bucket_arn, namespace=namespace, name=name
    )
    return dict(response)


@handle_exceptions
async def get_table_maintenance_job_status(
    table_bucket_arn: str, namespace: str, name: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get the status of a maintenance job for a table.

    Gets the status of a maintenance job for a table. For more information, see S3 Tables maintenance in the Amazon Simple Storage Service User Guide.

    Permissions:
    You must have the s3tables:GetTableMaintenanceJobStatus permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table_maintenance_job_status(
        tableBucketARN=table_bucket_arn, namespace=namespace, name=name
    )
    return dict(response)


@handle_exceptions
async def get_table_metadata_location(
    table_bucket_arn: str, namespace: str, name: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get the location of the table metadata.

    Gets the location of the table metadata.

    Permissions:
    You must have the s3tables:GetTableMetadataLocation permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table_metadata_location(
        tableBucketARN=table_bucket_arn, namespace=namespace, name=name
    )
    return dict(response)


@handle_exceptions
async def get_table_policy(
    table_bucket_arn: str, namespace: str, name: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get details about a table policy.

    Gets details about a table policy. For more information, see Viewing a table policy in the Amazon Simple Storage Service User Guide.

    Permissions:
    You must have the s3tables:GetTablePolicy permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table_policy(
        tableBucketARN=table_bucket_arn, namespace=namespace, name=name
    )
    return dict(response)


@handle_exceptions
async def put_table_maintenance_configuration(
    table_bucket_arn: str,
    namespace: str,
    name: str,
    maintenance_type: TableMaintenanceType,
    value: TableMaintenanceConfigurationValue,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or replace a maintenance configuration for a table.

    Creates a new maintenance configuration or replaces an existing maintenance configuration for a table.
    For more information, see S3 Tables maintenance in the Amazon Simple Storage Service User Guide.

    Permissions:
    You must have the s3tables:PutTableMaintenanceConfiguration permission to use this operation.
    """
    client = get_s3tables_client(region_name)

    # Prepare parameters for put_table_maintenance_configuration
    params: Dict[str, Any] = {
        'tableBucketARN': table_bucket_arn,
        'namespace': namespace,
        'name': name,
        'type': maintenance_type.value,
        'value': value.model_dump(by_alias=True, exclude_none=True),
    }

    response = client.put_table_maintenance_configuration(**params)
    return dict(response)


@handle_exceptions
async def rename_table(
    table_bucket_arn: str,
    namespace: str,
    name: str,
    new_name: Optional[str] = None,
    new_namespace_name: Optional[str] = None,
    version_token: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Rename a table or a namespace.

    Renames a table or a namespace. For more information, see S3 Tables in the Amazon Simple Storage Service User Guide.

    Args:
        table_bucket_arn: The Amazon Resource Name (ARN) of the table bucket.
        namespace: The namespace associated with the table.
        name: The current name of the table.
        new_name: Optional new name for the table.
        new_namespace_name: Optional new name for the namespace.
        version_token: Optional version token of the table.
        region_name: Optional AWS region name.

    Returns:
        Dict containing the response from the rename operation.

    Permissions:
    You must have the s3tables:RenameTable permission to use this operation.
    """
    client = get_s3tables_client(region_name)

    # Prepare parameters for rename_table
    params: Dict[str, Any] = {
        'tableBucketARN': table_bucket_arn,
        'namespace': namespace,
        'name': name,
    }

    # Add optional parameters if provided
    if new_name:
        params['newName'] = new_name
    if new_namespace_name:
        params['newNamespaceName'] = new_namespace_name
    if version_token:
        params['versionToken'] = version_token

    response = client.rename_table(**params)
    return dict(response)


@handle_exceptions
async def update_table_metadata_location(
    table_bucket_arn: str,
    namespace: str,
    name: str,
    metadata_location: str,
    version_token: str,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Update the metadata location for a table.

    Updates the metadata location for a table. The metadata location of a table must be an S3 URI that begins with the table's warehouse location.
    The metadata location for an Apache Iceberg table must end with .metadata.json, or if the metadata file is Gzip-compressed, .metadata.json.gz.

    Permissions:
    You must have the s3tables:UpdateTableMetadataLocation permission to use this operation.
    """
    client = get_s3tables_client(region_name)

    # Prepare parameters for update_table_metadata_location
    params: Dict[str, Any] = {
        'tableBucketARN': table_bucket_arn,
        'namespace': namespace,
        'name': name,
        'metadataLocation': metadata_location,
        'versionToken': version_token,
    }

    response = client.update_table_metadata_location(**params)
    return dict(response)
