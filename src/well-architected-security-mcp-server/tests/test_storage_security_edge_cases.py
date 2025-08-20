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

"""Edge case tests for storage_security module to improve coverage."""

from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.well_architected_security_mcp_server.util.storage_security import (
    check_dynamodb_tables,
    check_ebs_volumes,
    check_efs_filesystems,
    check_elasticache_clusters,
    check_rds_instances,
    check_s3_buckets,
    check_storage_encryption,
    find_storage_resources,
)


@pytest.mark.asyncio
async def test_check_s3_buckets_with_kms_encryption(mock_ctx, mock_boto3_session):
    """Test S3 buckets with KMS encryption."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "s3": [
                {"Arn": "arn:aws:s3:us-east-1::bucket/test-bucket-kms"},
            ]
        }
    }

    # Create mock S3 client
    mock_s3_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_s3_client

    # Mock get_bucket_encryption to return KMS encryption
    mock_s3_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms",
                        "KMSMasterKeyID": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                    },
                    "BucketKeyEnabled": False,
                }
            ]
        }
    }

    # Mock get_public_access_block to return blocking configuration
    mock_s3_client.get_public_access_block.return_value = {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }
    }

    # Call the function
    result = await check_s3_buckets("us-east-1", mock_s3_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "s3"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 1
    assert result["resource_details"][0]["compliant"] is True
    assert result["resource_details"][0]["checks"]["using_cmk"] is True


@pytest.mark.asyncio
async def test_check_s3_buckets_fallback_to_list_buckets(mock_ctx, mock_boto3_session):
    """Test S3 buckets when falling back to list_buckets API."""
    # Set up mock storage resources with error
    storage_resources = {"error": "Resource Explorer not configured"}

    # Create mock S3 client
    mock_s3_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_s3_client

    # Mock list_buckets
    mock_s3_client.list_buckets.return_value = {
        "Buckets": [
            {"Name": "test-bucket-1", "CreationDate": "2023-01-01T00:00:00Z"},
            {"Name": "test-bucket-2", "CreationDate": "2023-01-02T00:00:00Z"},
        ]
    }

    # Mock get_bucket_location for region filtering
    mock_s3_client.get_bucket_location.side_effect = [
        {"LocationConstraint": None},  # us-east-1 returns None
        {"LocationConstraint": None},  # us-east-1 returns None
    ]

    # Mock get_bucket_location for both buckets
    mock_s3_client.get_bucket_location.side_effect = [
        {"LocationConstraint": None},  # us-east-1
        {"LocationConstraint": None},  # us-east-1
    ]

    # Mock get_bucket_encryption for both buckets
    mock_s3_client.get_bucket_encryption.side_effect = [
        {
            "ServerSideEncryptionConfiguration": {
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
            }
        },
        ClientError(
            {"Error": {"Code": "ServerSideEncryptionConfigurationNotFoundError"}},
            "GetBucketEncryption",
        ),
    ]

    # Mock get_public_access_block for both buckets
    mock_s3_client.get_public_access_block.side_effect = [
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        },
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": False,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": False,
                "RestrictPublicBuckets": False,
            }
        },
    ]

    # Call the function
    result = await check_s3_buckets("us-east-1", mock_s3_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "s3"
    assert result["resources_checked"] == 2
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 1


@pytest.mark.asyncio
async def test_check_ebs_volumes_fallback_to_describe_volumes(mock_ctx, mock_boto3_session):
    """Test EBS volumes when falling back to describe_volumes API."""
    # Set up mock storage resources with error
    storage_resources = {"error": "Resource Explorer not configured"}

    # Create mock EC2 client
    mock_ec2_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_ec2_client

    # Mock get_paginator for describe_volumes
    mock_paginator = mock.MagicMock()
    mock_ec2_client.get_paginator.return_value = mock_paginator

    # Mock paginate
    mock_page_iterator = mock.MagicMock()
    mock_paginator.paginate.return_value = mock_page_iterator

    # Mock page iteration
    mock_page_iterator.__iter__.return_value = [
        {
            "Volumes": [
                {
                    "VolumeId": "vol-1234567890abcdef0",
                    "Encrypted": True,
                    "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                    "Size": 100,
                    "VolumeType": "gp3",
                    "State": "in-use",
                    "OwnerId": "123456789012",
                }
            ]
        }
    ]

    # Mock describe_volumes for batch processing
    mock_ec2_client.describe_volumes.return_value = {
        "Volumes": [
            {
                "VolumeId": "vol-1234567890abcdef0",
                "Encrypted": True,
                "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                "Size": 100,
                "VolumeType": "gp3",
                "State": "in-use",
                "OwnerId": "123456789012",
            }
        ]
    }

    # Call the function
    result = await check_ebs_volumes("us-east-1", mock_ec2_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "ebs"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0


@pytest.mark.asyncio
async def test_check_rds_instances_fallback_to_describe_db_instances(mock_ctx, mock_boto3_session):
    """Test RDS instances when falling back to describe_db_instances API."""
    # Set up mock storage resources with error
    storage_resources = {"error": "Resource Explorer not configured"}

    # Create mock RDS client
    mock_rds_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_rds_client

    # Mock get_paginator for describe_db_instances
    mock_paginator = mock.MagicMock()
    mock_rds_client.get_paginator.return_value = mock_paginator

    # Mock paginate
    mock_page_iterator = mock.MagicMock()
    mock_paginator.paginate.return_value = mock_page_iterator

    # Mock page iteration
    mock_page_iterator.__iter__.return_value = [
        {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": "test-db-1",
                    "StorageEncrypted": True,
                    "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                    "Engine": "mysql",
                    "DBInstanceStatus": "available",
                    "PubliclyAccessible": False,
                    "DBParameterGroups": [{"DBParameterGroupName": "default.mysql8.0"}],
                }
            ]
        }
    ]

    # Mock describe_db_instances for individual instance check
    mock_rds_client.describe_db_instances.return_value = {
        "DBInstances": [
            {
                "DBInstanceIdentifier": "test-db-1",
                "StorageEncrypted": True,
                "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                "Engine": "mysql",
                "DBInstanceStatus": "available",
                "PubliclyAccessible": False,
                "DBParameterGroups": [{"DBParameterGroupName": "default.mysql8.0"}],
                "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:test-db-1",
            }
        ]
    }

    # Call the function
    result = await check_rds_instances("us-east-1", mock_rds_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "rds"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0


@pytest.mark.asyncio
async def test_check_dynamodb_tables_fallback_to_list_tables(mock_ctx, mock_boto3_session):
    """Test DynamoDB tables when falling back to list_tables API."""
    # Set up mock storage resources with error
    storage_resources = {"error": "Resource Explorer not configured"}

    # Create mock DynamoDB client
    mock_dynamodb_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_dynamodb_client

    # Mock list_tables with pagination
    mock_dynamodb_client.list_tables.side_effect = [
        {"TableNames": ["test-table-1", "test-table-2"], "LastEvaluatedTableName": "test-table-2"},
        {"TableNames": ["test-table-3"]},
    ]

    # Mock describe_table for each table (called twice per table)
    mock_dynamodb_client.describe_table.side_effect = [
        # First table - first call
        {
            "Table": {
                "TableName": "test-table-1",
                "SSEDescription": {"Status": "ENABLED", "SSEType": "KMS"},
                "TableStatus": "ACTIVE",
                "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table-1",
            }
        },
        # First table - second call (SSE check)
        {
            "Table": {
                "TableName": "test-table-1",
                "SSEDescription": {"Status": "ENABLED", "SSEType": "KMS"},
                "TableStatus": "ACTIVE",
            }
        },
        # Second table - first call
        {
            "Table": {
                "TableName": "test-table-2",
                "TableStatus": "ACTIVE",
                "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table-2",
            }
        },
        # Second table - second call (SSE check)
        {
            "Table": {
                "TableName": "test-table-2",
                "TableStatus": "ACTIVE",
            }
        },
        # Third table - first call
        {
            "Table": {
                "TableName": "test-table-3",
                "TableStatus": "ACTIVE",
                "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table-3",
            }
        },
        # Third table - second call (SSE check)
        {
            "Table": {
                "TableName": "test-table-3",
                "TableStatus": "ACTIVE",
            }
        },
    ]

    # Call the function
    result = await check_dynamodb_tables(
        "us-east-1", mock_dynamodb_client, mock_ctx, storage_resources
    )

    # Verify the result
    assert result["service"] == "dynamodb"
    assert result["resources_checked"] == 3
    assert result["compliant_resources"] == 1  # Only the first table with KMS encryption
    assert result["non_compliant_resources"] == 2


@pytest.mark.asyncio
async def test_check_efs_filesystems_fallback_to_describe_file_systems(
    mock_ctx, mock_boto3_session
):
    """Test EFS filesystems when falling back to describe_file_systems API."""
    # Set up mock storage resources with error
    storage_resources = {"error": "Resource Explorer not configured"}

    # Create mock EFS client
    mock_efs_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_efs_client

    # Mock get_paginator for describe_file_systems
    mock_paginator = mock.MagicMock()
    mock_efs_client.get_paginator.return_value = mock_paginator

    # Mock paginate
    mock_page_iterator = mock.MagicMock()
    mock_paginator.paginate.return_value = mock_page_iterator

    # Mock page iteration
    mock_page_iterator.__iter__.return_value = [
        {
            "FileSystems": [
                {
                    "FileSystemId": "fs-1234567890abcdef0",
                    "Encrypted": True,
                    "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                    "LifeCycleState": "available",
                    "PerformanceMode": "generalPurpose",
                }
            ]
        }
    ]

    # Mock describe_file_systems for individual filesystem check
    mock_efs_client.describe_file_systems.return_value = {
        "FileSystems": [
            {
                "FileSystemId": "fs-1234567890abcdef0",
                "Encrypted": True,
                "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                "LifeCycleState": "available",
                "PerformanceMode": "generalPurpose",
                "FileSystemArn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-1234567890abcdef0",
            }
        ]
    }

    # Call the function
    result = await check_efs_filesystems("us-east-1", mock_efs_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "efs"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0


@pytest.mark.asyncio
async def test_check_elasticache_clusters_fallback_to_describe_cache_clusters(
    mock_ctx, mock_boto3_session
):
    """Test ElastiCache clusters when falling back to describe_cache_clusters API."""
    # Set up mock storage resources with error
    storage_resources = {"error": "Resource Explorer not configured"}

    # Create mock ElastiCache client
    mock_elasticache_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_elasticache_client

    # Mock get_paginator for describe_cache_clusters
    mock_paginator = mock.MagicMock()
    mock_elasticache_client.get_paginator.return_value = mock_paginator

    # Mock paginate
    mock_page_iterator = mock.MagicMock()
    mock_paginator.paginate.return_value = mock_page_iterator

    # Mock page iteration
    mock_page_iterator.__iter__.return_value = [
        {
            "CacheClusters": [
                {
                    "CacheClusterId": "test-cluster-1",
                    "AtRestEncryptionEnabled": True,
                    "TransitEncryptionEnabled": True,
                    "AuthTokenEnabled": True,
                    "CacheClusterStatus": "available",
                    "Engine": "redis",
                }
            ]
        }
    ]

    # Mock describe_cache_clusters for individual cluster check
    mock_elasticache_client.describe_cache_clusters.return_value = {
        "CacheClusters": [
            {
                "CacheClusterId": "test-cluster-1",
                "AtRestEncryptionEnabled": True,
                "TransitEncryptionEnabled": True,
                "AuthTokenEnabled": True,
                "CacheClusterStatus": "available",
                "Engine": "redis",
            }
        ]
    }

    # Call the function
    result = await check_elasticache_clusters(
        "us-east-1", mock_elasticache_client, mock_ctx, storage_resources
    )

    # Verify the result
    assert result["service"] == "elasticache"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0


@pytest.mark.asyncio
async def test_find_storage_resources_with_pagination(mock_ctx, mock_boto3_session):
    """Test find_storage_resources with pagination."""
    # Create mock resource explorer client
    mock_resource_explorer_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_resource_explorer_client

    # Mock list_views to return default view
    mock_resource_explorer_client.list_views.return_value = {
        "Views": [
            {
                "ViewArn": "arn:aws:resource-explorer-2:us-east-1:123456789012:view/default-view",
                "Filters": {"FilterString": ""},  # Default view has empty filter
            }
        ]
    }

    # Mock paginator with multiple pages
    mock_paginator = mock.MagicMock()
    mock_resource_explorer_client.get_paginator.return_value = mock_paginator

    # Mock page iterator with multiple pages
    mock_page_iterator = mock.MagicMock()
    mock_paginator.paginate.return_value = mock_page_iterator

    # Mock multiple pages of resources
    mock_page_iterator.__iter__.return_value = [
        {
            "Resources": [
                {"Arn": "arn:aws:s3:::test-bucket-1"},
                {"Arn": "arn:aws:s3:::test-bucket-2"},
            ]
        },
        {
            "Resources": [
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0"},
                {"Arn": "arn:aws:rds:us-east-1:123456789012:db:test-db-1"},
            ]
        },
    ]

    # Call the function
    services = ["s3", "ebs", "rds"]
    result = await find_storage_resources("us-east-1", mock_boto3_session, services, mock_ctx)

    # Verify the result
    assert result["total_resources"] == 4
    assert "resources_by_service" in result
    assert len(result["resources_by_service"]["s3"]) == 2
    assert len(result["resources_by_service"]["ebs"]) == 1
    assert len(result["resources_by_service"]["rds"]) == 1


@pytest.mark.asyncio
async def test_check_storage_encryption_with_botocore_error(mock_ctx, mock_boto3_session):
    """Test check_storage_encryption when BotoCoreError occurs."""
    # Mock find_storage_resources to raise BotoCoreError
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        from botocore.exceptions import BotoCoreError

        mock_find.side_effect = BotoCoreError()

        # Call the function and expect BotoCoreError to be raised
        with pytest.raises(BotoCoreError):
            await check_storage_encryption(
                "us-east-1", ["s3"], mock_boto3_session, mock_ctx, False
            )


@pytest.mark.asyncio
async def test_check_dynamodb_tables_with_sse_error(mock_ctx, mock_boto3_session):
    """Test DynamoDB tables when SSE check fails."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "dynamodb": [
                {"Arn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table-1"},
            ]
        }
    }

    # Create mock DynamoDB client
    mock_dynamodb_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_dynamodb_client

    # Mock describe_table - first call succeeds, second call (SSE check) fails
    mock_dynamodb_client.describe_table.side_effect = [
        {
            "Table": {
                "TableName": "test-table-1",
                "TableStatus": "ACTIVE",
                "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table-1",
            }
        },
        Exception("SSE check failed"),
    ]

    # Call the function
    result = await check_dynamodb_tables(
        "us-east-1", mock_dynamodb_client, mock_ctx, storage_resources
    )

    # Verify the result
    assert result["service"] == "dynamodb"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert "Error checking encryption settings" in result["resource_details"][0]["issues"]
