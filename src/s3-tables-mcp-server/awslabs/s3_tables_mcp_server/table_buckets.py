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

"""Table Bucket Management tools for S3 Tables MCP Server."""

from typing import Any, Dict, Optional

from .models import (
    EncryptionConfiguration,
    TableBucketMaintenanceConfigurationValue,
    TableBucketMaintenanceType,
)
from .utils import get_s3tables_client, handle_exceptions


@handle_exceptions
async def create_table_bucket(
    name: str,
    encryption_configuration: Optional[EncryptionConfiguration] = None,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new S3 Tables bucket."""
    client = get_s3tables_client(region_name)
    
    # Prepare parameters for create_table_bucket
    params = {'name': name}
    
    # Add encryption configuration if provided
    if encryption_configuration:
        params['encryptionConfiguration'] = encryption_configuration.model_dump(by_alias=True, exclude_none=True)
    
    response = client.create_table_bucket(**params)
    return dict(response)

@handle_exceptions
async def delete_table_bucket(
    table_bucket_arn: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Delete a table bucket.
    
    Permissions:
    You must have the s3tables:DeleteTableBucket permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.delete_table_bucket(tableBucketARN=table_bucket_arn)
    return dict(response)

@handle_exceptions
async def put_table_bucket_encryption(
    table_bucket_arn: str,
    encryption_configuration: EncryptionConfiguration,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Set the encryption configuration for a table bucket.
    
    Permissions:
    You must have the s3tables:PutTableBucketEncryption permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.put_table_bucket_encryption(
        tableBucketARN=table_bucket_arn,
        encryptionConfiguration=encryption_configuration.model_dump(by_alias=True, exclude_none=True)
    )
    return dict(response)

@handle_exceptions
async def put_table_bucket_maintenance_configuration(
    table_bucket_arn: str,
    maintenance_type: TableBucketMaintenanceType,
    value: TableBucketMaintenanceConfigurationValue,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Create or replace a maintenance configuration for a table bucket.
    
    Permissions:
    You must have the s3tables:PutTableBucketMaintenanceConfiguration permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.put_table_bucket_maintenance_configuration(
        tableBucketARN=table_bucket_arn,
        type=maintenance_type.value,
        value=value.model_dump(by_alias=True, exclude_none=True)
    )
    return dict(response)

@handle_exceptions
async def get_table_bucket(
    table_bucket_arn: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get details about a table bucket.
    
    Gets details on a table bucket.
    
    Permissions:
    You must have the s3tables:GetTableBucket permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table_bucket(tableBucketARN=table_bucket_arn)
    return dict(response)

@handle_exceptions
async def get_table_bucket_encryption(
    table_bucket_arn: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get the encryption configuration for a table bucket.
    
    Gets the encryption configuration for a table bucket.
    
    Permissions:
    You must have the s3tables:GetTableBucketEncryption permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table_bucket_encryption(tableBucketARN=table_bucket_arn)
    return dict(response)

@handle_exceptions
async def get_table_bucket_maintenance_configuration(
    table_bucket_arn: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get details about a maintenance configuration for a table bucket.
    
    Gets details about a maintenance configuration for a given table bucket.
    
    Permissions:
    You must have the s3tables:GetTableBucketMaintenanceConfiguration permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table_bucket_maintenance_configuration(tableBucketARN=table_bucket_arn)
    return dict(response)

@handle_exceptions
async def get_table_bucket_policy(
    table_bucket_arn: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get details about a table bucket policy.
    
    Gets details about a table bucket policy.
    
    Permissions:
    You must have the s3tables:GetTableBucketPolicy permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.get_table_bucket_policy(tableBucketARN=table_bucket_arn)
    return dict(response)

@handle_exceptions
async def delete_table_bucket_encryption(
    table_bucket_arn: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Delete the encryption configuration for a table bucket.
    
    Deletes the encryption configuration for a table bucket.
    
    Permissions:
    You must have the s3tables:DeleteTableBucketEncryption permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.delete_table_bucket_encryption(tableBucketARN=table_bucket_arn)
    return dict(response)

@handle_exceptions
async def delete_table_bucket_policy(
    table_bucket_arn: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Delete a table bucket policy.
    
    Deletes a table bucket policy.
    
    Permissions:
    You must have the s3tables:DeleteTableBucketPolicy permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.delete_table_bucket_policy(tableBucketARN=table_bucket_arn)
    return dict(response)