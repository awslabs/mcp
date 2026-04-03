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

"""Comprehensive tests for the storage_security module to achieve 90%+ coverage."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.util.storage_security import (
    check_storage_encryption,
)


@pytest.mark.asyncio
async def test_check_storage_encryption_multiple_services(mock_ctx, mock_boto3_session):
    """Test checking storage encryption with multiple services."""
    # Mock find_storage_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 6,
            "resources_by_service": {
                "s3": [
                    {"Arn": "arn:aws:s3:::test-bucket-1"},
                    {"Arn": "arn:aws:s3:::test-bucket-2"},
                ],
                "ebs": [
                    {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0"},
                    {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-0987654321fedcba0"},
                ],
                "rds": [
                    {"Arn": "arn:aws:rds:us-east-1:123456789012:db:test-db-1"},
                ],
                "dynamodb": [
                    {"Arn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table-1"},
                ],
            },
        }

        # Mock all service check functions
        with (
            mock.patch(
                "awslabs.well_architected_security_mcp_server.util.storage_security.check_s3_buckets"
            ) as mock_check_s3,
            mock.patch(
                "awslabs.well_architected_security_mcp_server.util.storage_security.check_ebs_volumes"
            ) as mock_check_ebs,
            mock.patch(
                "awslabs.well_architected_security_mcp_server.util.storage_security.check_rds_instances"
            ) as mock_check_rds,
            mock.patch(
                "awslabs.well_architected_security_mcp_server.util.storage_security.check_dynamodb_tables"
            ) as mock_check_dynamodb,
        ):
            # Set up mock returns
            mock_check_s3.return_value = {
                "service": "s3",
                "resources_checked": 2,
                "compliant_resources": 1,
                "non_compliant_resources": 1,
                "resource_details": [
                    {"name": "test-bucket-1", "compliant": True},
                    {"name": "test-bucket-2", "compliant": False},
                ],
            }

            mock_check_ebs.return_value = {
                "service": "ebs",
                "resources_checked": 2,
                "compliant_resources": 2,
                "non_compliant_resources": 0,
                "resource_details": [
                    {"name": "vol-1234567890abcdef0", "compliant": True},
                    {"name": "vol-0987654321fedcba0", "compliant": True},
                ],
            }

            mock_check_rds.return_value = {
                "service": "rds",
                "resources_checked": 1,
                "compliant_resources": 0,
                "non_compliant_resources": 1,
                "resource_details": [
                    {"name": "test-db-1", "compliant": False},
                ],
            }

            mock_check_dynamodb.return_value = {
                "service": "dynamodb",
                "resources_checked": 1,
                "compliant_resources": 1,
                "non_compliant_resources": 0,
                "resource_details": [
                    {"name": "test-table-1", "compliant": True},
                ],
            }

            # Call the function
            result = await check_storage_encryption(
                "us-east-1", ["s3", "ebs", "rds", "dynamodb"], mock_boto3_session, mock_ctx, False
            )

            # Verify the result
            assert result["region"] == "us-east-1"
            assert result["services_checked"] == ["s3", "ebs", "rds", "dynamodb"]
            assert result["resources_checked"] == 6
            assert result["compliant_resources"] == 4
            assert result["non_compliant_resources"] == 2
            assert len(result["compliance_by_service"]) == 4
            assert len(result["resource_details"]) == 6
            assert len(result["recommendations"]) > 0

            # Verify all service check functions were called
            mock_check_s3.assert_called_once()
            mock_check_ebs.assert_called_once()
            mock_check_rds.assert_called_once()
            mock_check_dynamodb.assert_called_once()


@pytest.mark.asyncio
async def test_check_storage_encryption_with_efs_and_elasticache(mock_ctx, mock_boto3_session):
    """Test checking storage encryption with EFS and ElastiCache services."""
    # Mock find_storage_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 2,
            "resources_by_service": {
                "efs": [
                    {
                        "Arn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-1234567890abcdef0"
                    },
                ],
                "elasticache": [
                    {"Arn": "arn:aws:elasticache:us-east-1:123456789012:cluster:test-cluster-1"},
                ],
            },
        }

        # Mock EFS and ElastiCache check functions
        with (
            mock.patch(
                "awslabs.well_architected_security_mcp_server.util.storage_security.check_efs_filesystems"
            ) as mock_check_efs,
            mock.patch(
                "awslabs.well_architected_security_mcp_server.util.storage_security.check_elasticache_clusters"
            ) as mock_check_elasticache,
        ):
            # Set up mock returns
            mock_check_efs.return_value = {
                "service": "efs",
                "resources_checked": 1,
                "compliant_resources": 1,
                "non_compliant_resources": 0,
                "resource_details": [
                    {"name": "fs-1234567890abcdef0", "compliant": True},
                ],
            }

            mock_check_elasticache.return_value = {
                "service": "elasticache",
                "resources_checked": 1,
                "compliant_resources": 0,
                "non_compliant_resources": 1,
                "resource_details": [
                    {"name": "test-cluster-1", "compliant": False},
                ],
            }

            # Call the function
            result = await check_storage_encryption(
                "us-east-1", ["efs", "elasticache"], mock_boto3_session, mock_ctx, False
            )

            # Verify the result
            assert result["region"] == "us-east-1"
            assert result["services_checked"] == ["efs", "elasticache"]
            assert result["resources_checked"] == 2
            assert result["compliant_resources"] == 1
            assert result["non_compliant_resources"] == 1
            assert len(result["compliance_by_service"]) == 2
            assert len(result["resource_details"]) == 2

            # Verify service check functions were called
            mock_check_efs.assert_called_once()
            mock_check_elasticache.assert_called_once()


@pytest.mark.asyncio
async def test_check_storage_encryption_unsupported_service(mock_ctx, mock_boto3_session):
    """Test checking storage encryption with unsupported service."""
    # Mock find_storage_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 1,
            "resources_by_service": {
                "unsupported": [
                    {"Arn": "arn:aws:unsupported:us-east-1:123456789012:resource/test-resource"},
                ],
            },
        }

        # Call the function with unsupported service
        result = await check_storage_encryption(
            "us-east-1", ["unsupported"], mock_boto3_session, mock_ctx, False
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services_checked"] == ["unsupported"]
        assert result["resources_checked"] == 0
        assert result["compliant_resources"] == 0
        assert result["non_compliant_resources"] == 0
        assert len(result["compliance_by_service"]) == 0
        assert len(result["resource_details"]) == 0


@pytest.mark.asyncio
async def test_check_storage_encryption_find_resources_error(mock_ctx, mock_boto3_session):
    """Test checking storage encryption when find_storage_resources returns error."""
    # Mock find_storage_resources to return error
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "error": "Resource Explorer not configured",
            "total_resources": 0,
        }

        # Call the function
        result = await check_storage_encryption(
            "us-east-1", ["s3"], mock_boto3_session, mock_ctx, False
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services_checked"] == ["s3"]
        assert result["resources_checked"] == 0
        assert result["compliant_resources"] == 0
        assert result["non_compliant_resources"] == 0
        assert len(result["compliance_by_service"]) == 1  # S3 service is still checked
        assert len(result["resource_details"]) == 0


@pytest.mark.asyncio
async def test_check_storage_encryption_service_check_error(mock_ctx, mock_boto3_session):
    """Test checking storage encryption when service check function returns error."""
    # Mock find_storage_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 1,
            "resources_by_service": {
                "s3": [
                    {"Arn": "arn:aws:s3:::test-bucket-1"},
                ],
            },
        }

        # Mock check_s3_buckets to return error
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.storage_security.check_s3_buckets"
        ) as mock_check_s3:
            mock_check_s3.return_value = {
                "service": "s3",
                "error": "API Error",
                "resources_checked": 0,
                "compliant_resources": 0,
                "non_compliant_resources": 0,
                "resource_details": [],
            }

            # Call the function
            result = await check_storage_encryption(
                "us-east-1", ["s3"], mock_boto3_session, mock_ctx, False
            )

            # Verify the result
            assert result["region"] == "us-east-1"
            assert result["services_checked"] == ["s3"]
            assert result["resources_checked"] == 0
            assert result["compliant_resources"] == 0
            assert result["non_compliant_resources"] == 0
            assert "s3" in result["compliance_by_service"]
            assert len(result["resource_details"]) == 0


@pytest.mark.asyncio
async def test_check_storage_encryption_empty_services(mock_ctx, mock_boto3_session):
    """Test checking storage encryption with empty services list."""
    # Mock find_storage_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 0,
            "resources_by_service": {},
        }

        # Call the function with empty services
        result = await check_storage_encryption(
            "us-east-1", [], mock_boto3_session, mock_ctx, False
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services_checked"] == []
        assert result["resources_checked"] == 0
        assert result["compliant_resources"] == 0
        assert result["non_compliant_resources"] == 0
        assert len(result["compliance_by_service"]) == 0
        assert len(result["resource_details"]) == 0
        assert len(result["recommendations"]) > 0  # Should still have general recommendations


@pytest.mark.asyncio
async def test_check_storage_encryption_no_resources_found(mock_ctx, mock_boto3_session):
    """Test checking storage encryption when no resources are found."""
    # Mock find_storage_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 0,
            "resources_by_service": {
                "s3": [],
                "ebs": [],
            },
        }

        # Call the function
        result = await check_storage_encryption(
            "us-east-1", ["s3", "ebs"], mock_boto3_session, mock_ctx, False
        )

        # Verify the result
        assert result["region"] == "us-east-1"
        assert result["services_checked"] == ["s3", "ebs"]
        assert result["resources_checked"] == 0
        assert result["compliant_resources"] == 0
        assert result["non_compliant_resources"] == 0
        assert len(result["compliance_by_service"]) == 2  # Both services are still checked
        assert len(result["resource_details"]) == 0
        assert len(result["recommendations"]) > 0  # Should still have general recommendations
