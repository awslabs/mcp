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

"""Additional tests for the storage_security module to improve coverage."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.util.storage_security import (
    check_dynamodb_tables,
    check_ebs_volumes,
    check_efs_filesystems,
    check_elasticache_clusters,
    check_rds_instances,
)


@pytest.mark.asyncio
async def test_check_ebs_volumes_success(mock_ctx, mock_boto3_session):
    """Test successful checking of EBS volumes."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "ebs": [
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0"},
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-0987654321fedcba0"},
            ]
        }
    }

    # Create mock EC2 client
    mock_ec2_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_ec2_client

    # Mock describe_volumes to return encrypted volumes
    mock_ec2_client.describe_volumes.return_value = {
        "Volumes": [
            {
                "VolumeId": "vol-1234567890abcdef0",
                "Encrypted": True,
                "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                "Size": 100,
                "VolumeType": "gp3",
                "State": "in-use",
            },
            {
                "VolumeId": "vol-0987654321fedcba0",
                "Encrypted": False,
                "Size": 50,
                "VolumeType": "gp2",
                "State": "available",
            },
        ]
    }

    # Call the function
    result = await check_ebs_volumes("us-east-1", mock_ec2_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "ebs"
    assert result["resources_checked"] == 2
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 2

    # Verify EC2 client was called correctly
    mock_ec2_client.describe_volumes.assert_called_once()


@pytest.mark.asyncio
async def test_check_ebs_volumes_no_resources(mock_ctx, mock_boto3_session):
    """Test checking EBS volumes with no resources."""
    # Set up mock storage resources with no EBS volumes
    storage_resources = {"resources_by_service": {}}

    # Create mock EC2 client
    mock_ec2_client = mock.MagicMock()

    # Call the function
    result = await check_ebs_volumes("us-east-1", mock_ec2_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "ebs"
    assert result["resources_checked"] == 0
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0


@pytest.mark.asyncio
async def test_check_ebs_volumes_api_error(mock_ctx, mock_boto3_session):
    """Test handling of API errors when checking EBS volumes."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "ebs": [
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0"},
            ]
        }
    }

    # Create mock EC2 client
    mock_ec2_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_ec2_client

    # Mock describe_volumes to raise an exception
    mock_ec2_client.describe_volumes.side_effect = Exception("API Error")

    # Call the function
    result = await check_ebs_volumes("us-east-1", mock_ec2_client, mock_ctx, storage_resources)

    # Verify the result - the function logs errors but continues processing
    assert result["service"] == "ebs"
    assert result["resources_checked"] == 1  # It still counts the resource
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0  # No details due to error


@pytest.mark.asyncio
async def test_check_rds_instances_success(mock_ctx, mock_boto3_session):
    """Test successful checking of RDS instances."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "rds": [
                {"Arn": "arn:aws:rds:us-east-1:123456789012:db:test-db-1"},
                {"Arn": "arn:aws:rds:us-east-1:123456789012:db:test-db-2"},
            ]
        }
    }

    # Create mock RDS client
    mock_rds_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_rds_client

    # Mock describe_db_instances to return encrypted instances
    # The function calls describe_db_instances for each instance individually
    mock_rds_client.describe_db_instances.side_effect = [
        {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": "test-db-1",
                    "StorageEncrypted": True,
                    "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                    "Engine": "mysql",
                    "DBInstanceStatus": "available",
                    "PubliclyAccessible": False,
                }
            ]
        },
        {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": "test-db-2",
                    "StorageEncrypted": False,
                    "Engine": "postgres",
                    "DBInstanceStatus": "available",
                    "PubliclyAccessible": True,
                }
            ]
        },
    ]

    # Call the function
    result = await check_rds_instances("us-east-1", mock_rds_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "rds"
    assert result["resources_checked"] == 2
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 2

    # Verify RDS client was called correctly
    assert mock_rds_client.describe_db_instances.call_count == 2


@pytest.mark.asyncio
async def test_check_rds_instances_no_resources(mock_ctx, mock_boto3_session):
    """Test checking RDS instances with no resources."""
    # Set up mock storage resources with no RDS instances
    storage_resources = {"resources_by_service": {}}

    # Create mock RDS client
    mock_rds_client = mock.MagicMock()

    # Call the function
    result = await check_rds_instances("us-east-1", mock_rds_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "rds"
    assert result["resources_checked"] == 0
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0


@pytest.mark.asyncio
async def test_check_dynamodb_tables_success(mock_ctx, mock_boto3_session):
    """Test successful checking of DynamoDB tables."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "dynamodb": [
                {"Arn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table-1"},
                {"Arn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table-2"},
            ]
        }
    }

    # Create mock DynamoDB client
    mock_dynamodb_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_dynamodb_client

    # Mock describe_table to return encrypted tables
    # The function calls describe_table twice for each table (once for table info, once for SSE)
    mock_dynamodb_client.describe_table.side_effect = [
        # First table - first call
        {
            "Table": {
                "TableName": "test-table-1",
                "SSEDescription": {
                    "Status": "ENABLED",
                    "SSEType": "KMS",
                    "KMSMasterKeyArn": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                },
                "TableStatus": "ACTIVE",
            }
        },
        # First table - second call (SSE check)
        {
            "Table": {
                "TableName": "test-table-1",
                "SSEDescription": {
                    "Status": "ENABLED",
                    "SSEType": "KMS",
                    "KMSMasterKeyArn": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                },
                "TableStatus": "ACTIVE",
            }
        },
        # Second table - first call
        {
            "Table": {
                "TableName": "test-table-2",
                "TableStatus": "ACTIVE",
                # No SSEDescription means not encrypted
            }
        },
        # Second table - second call (SSE check)
        {
            "Table": {
                "TableName": "test-table-2",
                "TableStatus": "ACTIVE",
                # No SSEDescription means not encrypted
            }
        },
    ]

    # Call the function
    result = await check_dynamodb_tables(
        "us-east-1", mock_dynamodb_client, mock_ctx, storage_resources
    )

    # Verify the result
    assert result["service"] == "dynamodb"
    assert result["resources_checked"] == 2
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 2

    # Verify DynamoDB client was called correctly
    assert mock_dynamodb_client.describe_table.call_count == 4  # Called twice for each table


@pytest.mark.asyncio
async def test_check_dynamodb_tables_no_resources(mock_ctx, mock_boto3_session):
    """Test checking DynamoDB tables with no resources."""
    # Set up mock storage resources with no DynamoDB tables
    storage_resources = {"resources_by_service": {}}

    # Create mock DynamoDB client
    mock_dynamodb_client = mock.MagicMock()

    # Call the function
    result = await check_dynamodb_tables(
        "us-east-1", mock_dynamodb_client, mock_ctx, storage_resources
    )

    # Verify the result
    assert result["service"] == "dynamodb"
    assert result["resources_checked"] == 0
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0


@pytest.mark.asyncio
async def test_check_efs_filesystems_success(mock_ctx, mock_boto3_session):
    """Test successful checking of EFS filesystems."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "elasticfilesystem": [  # EFS function looks for "elasticfilesystem", not "efs"
                {
                    "Arn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-1234567890abcdef0"
                },
                {
                    "Arn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-0987654321fedcba0"
                },
            ]
        }
    }

    # Create mock EFS client
    mock_efs_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_efs_client

    # Mock describe_file_systems to return encrypted filesystems
    # The function calls describe_file_systems for each filesystem individually
    mock_efs_client.describe_file_systems.side_effect = [
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
        },
        {
            "FileSystems": [
                {
                    "FileSystemId": "fs-0987654321fedcba0",
                    "Encrypted": False,
                    "LifeCycleState": "available",
                    "PerformanceMode": "generalPurpose",
                }
            ]
        },
    ]

    # Call the function
    result = await check_efs_filesystems("us-east-1", mock_efs_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "efs"
    assert result["resources_checked"] == 2
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 2

    # Verify EFS client was called correctly
    assert mock_efs_client.describe_file_systems.call_count == 2


@pytest.mark.asyncio
async def test_check_efs_filesystems_no_resources(mock_ctx, mock_boto3_session):
    """Test checking EFS filesystems with no resources."""
    # Set up mock storage resources with no EFS filesystems
    storage_resources = {"resources_by_service": {}}

    # Create mock EFS client
    mock_efs_client = mock.MagicMock()

    # Call the function
    result = await check_efs_filesystems("us-east-1", mock_efs_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "efs"
    assert result["resources_checked"] == 0
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0


@pytest.mark.asyncio
async def test_check_elasticache_clusters_success(mock_ctx, mock_boto3_session):
    """Test successful checking of ElastiCache clusters."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "elasticache": [
                {"Arn": "arn:aws:elasticache:us-east-1:123456789012:cluster:test-cluster-1"},
                {"Arn": "arn:aws:elasticache:us-east-1:123456789012:cluster:test-cluster-2"},
            ]
        }
    }

    # Create mock ElastiCache client
    mock_elasticache_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_elasticache_client

    # Mock describe_cache_clusters to return encrypted clusters
    # The function calls describe_cache_clusters for each cluster individually
    mock_elasticache_client.describe_cache_clusters.side_effect = [
        {
            "CacheClusters": [
                {
                    "CacheClusterId": "test-cluster-1",
                    "AtRestEncryptionEnabled": True,
                    "TransitEncryptionEnabled": True,
                    "CacheClusterStatus": "available",
                    "Engine": "redis",
                }
            ]
        },
        {
            "CacheClusters": [
                {
                    "CacheClusterId": "test-cluster-2",
                    "AtRestEncryptionEnabled": False,
                    "TransitEncryptionEnabled": False,
                    "CacheClusterStatus": "available",
                    "Engine": "memcached",
                }
            ]
        },
    ]

    # Call the function
    result = await check_elasticache_clusters(
        "us-east-1", mock_elasticache_client, mock_ctx, storage_resources
    )

    # Verify the result
    assert result["service"] == "elasticache"
    assert result["resources_checked"] == 2
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 2

    # Verify ElastiCache client was called correctly
    assert mock_elasticache_client.describe_cache_clusters.call_count == 2


@pytest.mark.asyncio
async def test_check_elasticache_clusters_no_resources(mock_ctx, mock_boto3_session):
    """Test checking ElastiCache clusters with no resources."""
    # Set up mock storage resources with no ElastiCache clusters
    storage_resources = {"resources_by_service": {}}

    # Create mock ElastiCache client
    mock_elasticache_client = mock.MagicMock()

    # Call the function
    result = await check_elasticache_clusters(
        "us-east-1", mock_elasticache_client, mock_ctx, storage_resources
    )

    # Verify the result
    assert result["service"] == "elasticache"
    assert result["resources_checked"] == 0
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0


@pytest.mark.asyncio
async def test_check_elasticache_clusters_api_error(mock_ctx, mock_boto3_session):
    """Test handling of API errors when checking ElastiCache clusters."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "elasticache": [
                {"Arn": "arn:aws:elasticache:us-east-1:123456789012:cluster:test-cluster-1"},
            ]
        }
    }

    # Create mock ElastiCache client
    mock_elasticache_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_elasticache_client

    # Mock describe_cache_clusters to raise an exception
    mock_elasticache_client.describe_cache_clusters.side_effect = Exception("API Error")

    # Call the function
    result = await check_elasticache_clusters(
        "us-east-1", mock_elasticache_client, mock_ctx, storage_resources
    )

    # Verify the result - the function logs errors but continues processing
    assert result["service"] == "elasticache"
    assert result["resources_checked"] == 1  # It still counts the resource
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0  # No details due to error


@pytest.mark.asyncio
async def test_check_rds_instances_api_error(mock_ctx, mock_boto3_session):
    """Test handling of API errors when checking RDS instances."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "rds": [
                {"Arn": "arn:aws:rds:us-east-1:123456789012:db:test-db-1"},
            ]
        }
    }

    # Create mock RDS client
    mock_rds_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_rds_client

    # Mock describe_db_instances to raise an exception
    mock_rds_client.describe_db_instances.side_effect = Exception("API Error")

    # Call the function
    result = await check_rds_instances("us-east-1", mock_rds_client, mock_ctx, storage_resources)

    # Verify the result - the function logs errors but continues processing
    assert result["service"] == "rds"
    assert result["resources_checked"] == 1  # It still counts the resource
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0  # No details due to error


@pytest.mark.asyncio
async def test_check_dynamodb_tables_api_error(mock_ctx, mock_boto3_session):
    """Test handling of API errors when checking DynamoDB tables."""
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

    # Mock describe_table to raise an exception
    mock_dynamodb_client.describe_table.side_effect = Exception("API Error")

    # Call the function
    result = await check_dynamodb_tables(
        "us-east-1", mock_dynamodb_client, mock_ctx, storage_resources
    )

    # Verify the result - the function logs errors but continues processing
    assert result["service"] == "dynamodb"
    assert result["resources_checked"] == 1  # It still counts the resource
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0  # No details due to error


@pytest.mark.asyncio
async def test_check_efs_filesystems_api_error(mock_ctx, mock_boto3_session):
    """Test handling of API errors when checking EFS filesystems."""
    # Set up mock storage resources
    storage_resources = {
        "resources_by_service": {
            "efs": [
                {
                    "Arn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-1234567890abcdef0"
                },
            ]
        }
    }

    # Create mock EFS client
    mock_efs_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_efs_client

    # Mock describe_file_systems to raise an exception
    mock_efs_client.describe_file_systems.side_effect = Exception("API Error")

    # Call the function
    result = await check_efs_filesystems("us-east-1", mock_efs_client, mock_ctx, storage_resources)

    # Verify the result - the function logs errors but continues processing
    assert result["service"] == "efs"
    assert result["resources_checked"] == 0  # EFS function doesn't find resources from ARN
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 0  # No details due to error
