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

"""Table Bucket Management tools for S3 Tables MCP Server."""

from .models import (
    TableBucketMaintenanceConfigurationValue,
    TableBucketMaintenanceType,
)
from .utils import get_s3tables_client, handle_exceptions
from typing import Any, Dict, Optional


@handle_exceptions
async def create_table_bucket(
    name: str,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new S3 Tables bucket."""
    client = get_s3tables_client(region_name)

    # Prepare parameters for create_table_bucket
    params = {'name': name}

    response = client.create_table_bucket(**params)
    return dict(response)


@handle_exceptions
async def delete_table_bucket(
    table_bucket_arn: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Delete a table bucket.

    Permissions:
    You must have the s3tables:DeleteTableBucket permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.delete_table_bucket(tableBucketARN=table_bucket_arn)
    return dict(response)


@handle_exceptions
async def put_table_bucket_maintenance_configuration(
    table_bucket_arn: str,
    maintenance_type: TableBucketMaintenanceType,
    value: TableBucketMaintenanceConfigurationValue,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or replace a maintenance configuration for a table bucket.

    Permissions:
    You must have the s3tables:PutTableBucketMaintenanceConfiguration permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.put_table_bucket_maintenance_configuration(
        tableBucketARN=table_bucket_arn,
        type=maintenance_type.value,
        value=value.model_dump(by_alias=True, exclude_none=True),
    )
    return dict(response)


@handle_exceptions
async def get_table_bucket(
    table_bucket_arn: str, region_name: Optional[str] = None
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
async def get_table_bucket_maintenance_configuration(
    table_bucket_arn: str, region_name: Optional[str] = None
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
    table_bucket_arn: str, region_name: Optional[str] = None
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
async def delete_table_bucket_policy(
    table_bucket_arn: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Delete a table bucket policy.

    Deletes a table bucket policy.

    Permissions:
    You must have the s3tables:DeleteTableBucketPolicy permission to use this operation.
    """
    client = get_s3tables_client(region_name)
    response = client.delete_table_bucket_policy(tableBucketARN=table_bucket_arn)
    return dict(response)
