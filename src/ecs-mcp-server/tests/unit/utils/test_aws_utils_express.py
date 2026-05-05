"""
Unit tests for Express Mode AWS utility functions.

Tests cover utils/aws.py:
- check_iam_role_exists
- check_ecr_image_exists

Following DRY principles with parameterized, modular tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.utils.aws import (
    check_ecr_image_exists,
    check_iam_role_exists_and_policy,
)

# ============================================================================
# Fixtures for common test data
# ============================================================================


@pytest.fixture
def mock_iam_role_response():
    """Mock IAM role response with valid trust policy."""
    return {
        "Role": {
            "RoleName": "ecsTaskExecutionRole",
            "Arn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ]
            },
        }
    }


@pytest.fixture
def mock_ecr_image_response():
    """Mock ECR describe_images response."""
    return {
        "imageDetails": [
            {
                "imageDigest": "sha256:abc123",
                "imageTags": ["latest"],
                "imagePushedAt": "2024-01-01T00:00:00Z",
            }
        ]
    }


# ============================================================================
# Tests for check_iam_role_exists
# ============================================================================


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_iam_role_exists_valid(mock_get_client, mock_iam_role_response):
    """Test IAM role check succeeds for valid role."""
    mock_client = MagicMock()
    mock_client.get_role.return_value = mock_iam_role_response
    mock_get_client.return_value = mock_client

    details = await check_iam_role_exists_and_policy(
        "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
        "ecs-tasks.amazonaws.com",
        "Task Execution Role",
    )

    assert details["status"] == "valid"
    assert details["name"] == "ecsTaskExecutionRole"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_iam_role_exists_not_found(mock_get_client):
    """Test IAM role check fails when role doesn't exist."""
    from botocore.exceptions import ClientError

    # Create NoSuchEntityException as a proper exception
    class NoSuchEntityException(ClientError):
        pass

    mock_client = MagicMock()
    mock_client.exceptions = MagicMock()
    mock_client.exceptions.NoSuchEntityException = NoSuchEntityException

    error = NoSuchEntityException(
        {"Error": {"Code": "NoSuchEntity", "Message": "Role not found"}}, "GetRole"
    )
    mock_client.get_role.side_effect = error
    mock_get_client.return_value = mock_client

    details = await check_iam_role_exists_and_policy(
        "arn:aws:iam::123456789012:role/nonexistent", "ecs-tasks.amazonaws.com", "Test Role"
    )

    assert details["status"] == "not_found"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_iam_role_invalid_trust_policy(mock_get_client):
    """Test IAM role check fails with invalid trust policy."""
    mock_client = MagicMock()
    mock_client.get_role.return_value = {
        "Role": {
            "RoleName": "wrongRole",
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ]
            },
        }
    }
    mock_get_client.return_value = mock_client

    details = await check_iam_role_exists_and_policy(
        "arn:aws:iam::123456789012:role/wrongRole", "ecs-tasks.amazonaws.com", "Test Role"
    )

    assert details["status"] == "invalid_trust_policy"
    assert "does not allow" in details["error"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_iam_role_service_list(mock_get_client):
    """Test IAM role check with service principal as list."""
    mock_client = MagicMock()
    mock_client.get_role.return_value = {
        "Role": {
            "RoleName": "testRole",
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": ["ecs-tasks.amazonaws.com", "ecs.amazonaws.com"]},
                        "Action": "sts:AssumeRole",
                    }
                ]
            },
        }
    }
    mock_get_client.return_value = mock_client

    details = await check_iam_role_exists_and_policy(
        "arn:aws:iam::123456789012:role/testRole", "ecs-tasks.amazonaws.com", "Test Role"
    )

    assert details["status"] == "valid"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_iam_role_generic_exception(mock_get_client):
    """Test IAM role check handles generic exceptions."""
    mock_client = MagicMock()
    mock_client.get_role.side_effect = RuntimeError("Unexpected error")
    mock_get_client.return_value = mock_client

    details = await check_iam_role_exists_and_policy(
        "arn:aws:iam::123456789012:role/testRole", "ecs-tasks.amazonaws.com", "Test Role"
    )

    assert details["status"] == "error"
    assert "Error validating Test Role" in details["error"]


# ============================================================================
# Tests for check_ecr_image_exists
# ============================================================================


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_ecr_image_exists_valid(mock_get_client, mock_ecr_image_response):
    """Test ECR image check succeeds for existing image."""
    mock_client = MagicMock()
    mock_client.describe_images.return_value = mock_ecr_image_response
    mock_get_client.return_value = mock_client

    details = await check_ecr_image_exists(
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:latest"
    )

    assert details["status"] == "exists"
    assert details["repository"] == "my-app"
    assert details["tag"] == "latest"


@pytest.mark.anyio
async def test_check_ecr_image_invalid_format_no_tag():
    """Test ECR image check fails without tag."""
    details = await check_ecr_image_exists("123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app")

    assert details["status"] == "invalid_format"
    assert "must include a tag" in details["error"]


@pytest.mark.anyio
async def test_check_ecr_image_invalid_format_no_repo():
    """Test ECR image check fails without repository name."""
    details = await check_ecr_image_exists("invalid-uri:tag")

    assert details["status"] == "invalid_format"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_ecr_image_not_found(mock_get_client):
    """Test ECR image check fails when image doesn't exist."""
    mock_client = MagicMock()
    mock_client.describe_images.return_value = {"imageDetails": []}
    mock_get_client.return_value = mock_client

    details = await check_ecr_image_exists(
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:missing"
    )

    assert details["status"] == "not_found"
    assert details["tag"] == "missing"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_ecr_image_repository_not_found(mock_get_client):
    """Test ECR image check fails when repository doesn't exist."""
    from botocore.exceptions import ClientError

    # Create RepositoryNotFoundException as a proper exception
    class RepositoryNotFoundException(ClientError):
        pass

    mock_client = MagicMock()
    mock_client.exceptions = MagicMock()
    mock_client.exceptions.RepositoryNotFoundException = RepositoryNotFoundException

    error = RepositoryNotFoundException(
        {"Error": {"Code": "RepositoryNotFoundException", "Message": "Repository not found"}},
        "DescribeImages",
    )
    mock_client.describe_images.side_effect = error
    mock_get_client.return_value = mock_client

    details = await check_ecr_image_exists(
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/missing-repo:tag"
    )

    assert details["status"] == "repository_not_found"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_check_ecr_image_generic_exception(mock_get_client):
    """Test ECR image check handles generic exceptions."""
    mock_client = MagicMock()
    mock_client.describe_images.side_effect = RuntimeError("Unexpected error")
    mock_get_client.return_value = mock_client

    details = await check_ecr_image_exists(
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app:tag"
    )

    assert details["status"] == "error"
    assert "Error validating image in ECR" in details["error"]
