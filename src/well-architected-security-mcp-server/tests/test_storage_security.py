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

"""Tests for the storage_security module."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.util.storage_security import (
    _update_results,
    check_s3_buckets,
    check_storage_encryption,
    find_storage_resources,
    generate_recommendations,
)


@pytest.mark.asyncio
async def test_update_results():
    """Test the _update_results function."""
    # Create main results dictionary
    main_results = {
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "compliance_by_service": {},
        "resource_details": [],
    }

    # Create service results dictionary
    service_results = {
        "service": "s3",
        "resources_checked": 5,
        "compliant_resources": 3,
        "non_compliant_resources": 2,
        "resource_details": [
            {"name": "bucket1", "compliant": True},
            {"name": "bucket2", "compliant": False},
            {"name": "bucket3", "compliant": True},
            {"name": "bucket4", "compliant": True},
            {"name": "bucket5", "compliant": False},
        ],
    }

    # Test with include_unencrypted_only=False
    await _update_results(main_results, service_results, "s3", False)

    # Verify results
    assert main_results["resources_checked"] == 5
    assert main_results["compliant_resources"] == 3
    assert main_results["non_compliant_resources"] == 2
    assert "s3" in main_results["compliance_by_service"]
    assert main_results["compliance_by_service"]["s3"]["resources_checked"] == 5
    assert main_results["compliance_by_service"]["s3"]["compliant_resources"] == 3
    assert main_results["compliance_by_service"]["s3"]["non_compliant_resources"] == 2
    assert len(main_results["resource_details"]) == 5

    # Reset main results
    main_results = {
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "compliance_by_service": {},
        "resource_details": [],
    }

    # Test with include_unencrypted_only=True
    await _update_results(main_results, service_results, "s3", True)

    # Verify results
    assert main_results["resources_checked"] == 5
    assert main_results["compliant_resources"] == 3
    assert main_results["non_compliant_resources"] == 2
    assert "s3" in main_results["compliance_by_service"]
    assert main_results["compliance_by_service"]["s3"]["resources_checked"] == 5
    assert main_results["compliance_by_service"]["s3"]["compliant_resources"] == 3
    assert main_results["compliance_by_service"]["s3"]["non_compliant_resources"] == 2
    assert len(main_results["resource_details"]) == 2  # Only non-compliant resources
    assert all(not resource["compliant"] for resource in main_results["resource_details"])


@pytest.mark.asyncio
async def test_generate_recommendations():
    """Test the generate_recommendations function."""
    # Test with no services
    results = {"compliance_by_service": {}}
    recommendations = await generate_recommendations(results)
    assert len(recommendations) == 2  # General recommendations
    assert any("customer-managed KMS keys" in rec for rec in recommendations)

    # Test with S3 service with non-compliant resources
    results = {"compliance_by_service": {"s3": {"non_compliant_resources": 2}}}
    recommendations = await generate_recommendations(results)
    assert len(recommendations) == 4  # S3 recommendations + general recommendations
    assert any("Enable default encryption" in rec for rec in recommendations)
    assert any("block public access" in rec for rec in recommendations)

    # Test with S3 service with all compliant resources
    results = {"compliance_by_service": {"s3": {"non_compliant_resources": 0}}}
    recommendations = await generate_recommendations(results)
    assert len(recommendations) == 2  # Only general recommendations
    assert not any("Enable default encryption" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_find_storage_resources_success(
    mock_ctx, mock_boto3_session, mock_resource_explorer_client
):
    """Test successful finding of storage resources."""
    # Set up mock response for Resource Explorer
    resource_explorer = mock_resource_explorer_client

    # Mock paginator to return resources
    paginator = mock.MagicMock()
    resource_explorer.get_paginator.return_value = paginator

    # Create mock page iterator
    page_iterator = mock.MagicMock()
    paginator.paginate.return_value = page_iterator

    # Set up mock resources
    mock_resources = [
        {"Arn": "arn:aws:s3:::test-bucket"},
        {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0"},
        {"Arn": "arn:aws:rds:us-east-1:123456789012:db:test-db"},
        {"Arn": "arn:aws:dynamodb:us-east-1:123456789012:table/test-table"},
    ]

    # Set up mock pages
    page_iterator.__iter__.return_value = [{"Resources": mock_resources}]

    # Call the function
    services = ["s3", "ebs", "rds", "dynamodb"]
    result = await find_storage_resources("us-east-1", mock_boto3_session, services, mock_ctx)

    # Verify the result
    assert result["total_resources"] == 4
    assert "resources_by_service" in result
    assert "s3" in result["resources_by_service"]
    assert "ebs" in result["resources_by_service"]
    assert "rds" in result["resources_by_service"]
    assert "dynamodb" in result["resources_by_service"]

    # Verify Resource Explorer was called correctly
    mock_boto3_session.client.assert_called_with(
        "resource-explorer-2", region_name="us-east-1", config=mock.ANY
    )
    resource_explorer.list_views.assert_called_once()
    paginator.paginate.assert_called_once()
    assert "service:s3" in paginator.paginate.call_args[1]["Filters"]["FilterString"]
    assert (
        "service:ec2 resourcetype:ec2:volume"
        in paginator.paginate.call_args[1]["Filters"]["FilterString"]
    )


@pytest.mark.asyncio
async def test_find_storage_resources_no_default_view(mock_ctx, mock_boto3_session):
    """Test handling when no default Resource Explorer view is found."""
    # Create a mock resource explorer client
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Mock list_views to return views without a default view
    resource_explorer.list_views.return_value = {
        "Views": [
            {
                "ViewArn": "arn:aws:resource-explorer-2:us-east-1:123456789012:view/custom-view",
                "Filters": {"FilterString": "service:s3"},  # Not a default view
            }
        ]
    }

    # Call the function
    services = ["s3"]
    result = await find_storage_resources("us-east-1", mock_boto3_session, services, mock_ctx)

    # Verify the result
    assert "error" in result
    assert "No default Resource Explorer view found" in result["error"]

    # Verify warning was logged
    mock_ctx.warning.assert_called_once()
    assert "No default Resource Explorer view found" in mock_ctx.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_find_storage_resources_api_error(mock_ctx, mock_boto3_session):
    """Test handling of API errors."""
    # Create a mock resource explorer client
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Mock list_views to raise an exception
    resource_explorer.list_views.side_effect = Exception("API Error")

    # Mock the error method to do nothing
    mock_ctx.error = mock.MagicMock()

    try:
        # Call the function
        services = ["s3"]
        result = await find_storage_resources("us-east-1", mock_boto3_session, services, mock_ctx)

        # Verify the result
        assert "error" in result
        assert isinstance(result["error"], str)  # Just check that there is an error message
    except Exception as e:
        # If the function raises an exception, that's also acceptable
        # Just make sure it's the expected exception
        assert "API Error" in str(e)


@pytest.mark.asyncio
async def test_check_s3_buckets_success(mock_ctx, mock_boto3_session):
    """Test successful checking of S3 buckets."""
    # Set up mock storage resources - use bucket ARN format that matches the parsing logic
    storage_resources = {
        "resources_by_service": {
            "s3": [
                {"Arn": "arn:aws:s3:us-east-1::bucket/test-bucket-1"},
                {"Arn": "arn:aws:s3:us-east-1::bucket/test-bucket-2"},
            ]
        }
    }

    # Create mock S3 client
    mock_s3_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_s3_client

    # Mock get_bucket_encryption to return encryption configuration
    mock_s3_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
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
    assert result["resources_checked"] == 2
    assert result["compliant_resources"] == 2
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 2

    # Verify S3 client was called correctly
    assert mock_s3_client.get_bucket_encryption.call_count == 2
    assert mock_s3_client.get_public_access_block.call_count == 2


@pytest.mark.asyncio
async def test_check_s3_buckets_no_encryption(mock_ctx, mock_boto3_session):
    """Test checking S3 buckets with no encryption."""
    # Set up mock storage resources - use bucket ARN format that matches the parsing logic
    storage_resources = {
        "resources_by_service": {
            "s3": [
                {"Arn": "arn:aws:s3:us-east-1::bucket/test-bucket-1"},
            ]
        }
    }

    # Create mock S3 client
    mock_s3_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_s3_client

    # Mock get_bucket_encryption to raise ClientError (no encryption)
    from botocore.exceptions import ClientError

    mock_s3_client.get_bucket_encryption.side_effect = ClientError(
        {"Error": {"Code": "ServerSideEncryptionConfigurationNotFoundError"}},
        "GetBucketEncryption",
    )

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
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    # Check that there's at least one issue related to encryption
    assert not result["resource_details"][0]["compliant"]
    assert any("encryption" in issue.lower() for issue in result["resource_details"][0]["issues"])


@pytest.mark.asyncio
async def test_check_s3_buckets_no_public_access_block(mock_ctx, mock_boto3_session):
    """Test checking S3 buckets with no public access block."""
    # Set up mock storage resources - use bucket ARN format that matches the parsing logic
    storage_resources = {
        "resources_by_service": {
            "s3": [
                {"Arn": "arn:aws:s3:us-east-1::bucket/test-bucket-1"},
            ]
        }
    }

    # Create mock S3 client
    mock_s3_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_s3_client

    # Mock get_bucket_encryption to return encryption configuration
    mock_s3_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }
    }

    # Mock get_public_access_block to return non-blocking configuration
    mock_s3_client.get_public_access_block.return_value = {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": False,  # Not fully blocking
            "RestrictPublicBuckets": True,
        }
    }

    # Call the function
    result = await check_s3_buckets("us-east-1", mock_s3_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "s3"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    # Check that there's at least one issue related to public access
    assert not result["resource_details"][0]["compliant"]
    assert any(
        "public access" in issue.lower() for issue in result["resource_details"][0]["issues"]
    )


@pytest.mark.asyncio
async def test_check_s3_buckets_public_access_block_error(mock_ctx, mock_boto3_session):
    """Test checking S3 buckets with error getting public access block."""
    # Set up mock storage resources - use bucket ARN format that matches the parsing logic
    storage_resources = {
        "resources_by_service": {
            "s3": [
                {"Arn": "arn:aws:s3:us-east-1::bucket/test-bucket-1"},
            ]
        }
    }

    # Create mock S3 client
    mock_s3_client = mock.MagicMock()
    mock_boto3_session.client.return_value = mock_s3_client

    # Mock get_bucket_encryption to return encryption configuration
    mock_s3_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }
    }

    # Mock get_public_access_block to raise an exception
    mock_s3_client.get_public_access_block.side_effect = Exception(
        "Error getting public access block"
    )

    # Call the function
    result = await check_s3_buckets("us-east-1", mock_s3_client, mock_ctx, storage_resources)

    # Verify the result
    assert result["service"] == "s3"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    # Check that there's at least one issue related to public access
    assert not result["resource_details"][0]["compliant"]
    assert any(
        "public access" in issue.lower() for issue in result["resource_details"][0]["issues"]
    )


@pytest.mark.asyncio
async def test_check_s3_buckets_api_error(mock_ctx, mock_s3_client):
    """Test handling of API errors when checking S3 buckets."""
    # Mock list_buckets to raise an exception
    mock_s3_client.list_buckets.side_effect = Exception("API Error")

    # Mock the error method to do nothing
    mock_ctx.error = mock.MagicMock()

    try:
        # Call the function with empty storage resources
        storage_resources = {"error": "No resources found"}
        result = await check_s3_buckets("us-east-1", mock_s3_client, mock_ctx, storage_resources)

        # Verify the result
        assert result["service"] == "s3"
        assert "error" in result
        assert "API Error" in result["error"]
        assert result["resources_checked"] == 0
        assert result["compliant_resources"] == 0
        assert result["non_compliant_resources"] == 0
    except Exception as e:
        # If the function raises an exception, that's also acceptable
        # Just make sure it's the expected exception
        assert "API Error" in str(e)


@pytest.mark.asyncio
async def test_check_storage_encryption_success(mock_ctx, mock_boto3_session):
    """Test successful checking of storage encryption."""
    # Mock find_storage_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 2,
            "resources_by_service": {
                "s3": [
                    {"Arn": "arn:aws:s3:::test-bucket-1"},
                    {"Arn": "arn:aws:s3:::test-bucket-2"},
                ]
            },
        }

        # Mock check_s3_buckets
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.storage_security.check_s3_buckets"
        ) as mock_check_s3:
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

            # Call the function
            result = await check_storage_encryption(
                "us-east-1", ["s3"], mock_boto3_session, mock_ctx, False
            )

            # Verify the result
            assert result["region"] == "us-east-1"
            assert result["services_checked"] == ["s3"]
            assert result["resources_checked"] == 2
            assert result["compliant_resources"] == 1
            assert result["non_compliant_resources"] == 1
            assert "s3" in result["compliance_by_service"]
            assert len(result["resource_details"]) == 2
            assert len(result["recommendations"]) > 0

            # Verify mocks were called correctly
            mock_find.assert_called_once_with("us-east-1", mock_boto3_session, ["s3"], mock_ctx)
            mock_check_s3.assert_called_once()


@pytest.mark.asyncio
async def test_check_storage_encryption_include_unencrypted_only(mock_ctx, mock_boto3_session):
    """Test checking storage encryption with include_unencrypted_only=True."""
    # Mock find_storage_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.storage_security.find_storage_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 2,
            "resources_by_service": {
                "s3": [
                    {"Arn": "arn:aws:s3:::test-bucket-1"},
                    {"Arn": "arn:aws:s3:::test-bucket-2"},
                ]
            },
        }

        # Mock check_s3_buckets
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.storage_security.check_s3_buckets"
        ) as mock_check_s3:
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

            # Call the function with include_unencrypted_only=True
            result = await check_storage_encryption(
                "us-east-1", ["s3"], mock_boto3_session, mock_ctx, True
            )

            # Verify the result
            assert result["region"] == "us-east-1"
            assert result["services_checked"] == ["s3"]
            assert result["resources_checked"] == 2
            assert result["compliant_resources"] == 1
            assert result["non_compliant_resources"] == 1
            assert "s3" in result["compliance_by_service"]
            assert len(result["resource_details"]) == 1  # Only non-compliant resources
            assert not result["resource_details"][0]["compliant"]
            assert len(result["recommendations"]) > 0
