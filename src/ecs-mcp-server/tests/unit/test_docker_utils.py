"""
Pytest-style unit tests for docker utils module.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.utils.aws import get_aws_account_id
from awslabs.ecs_mcp_server.utils.docker import (
    build_and_push_image,
    get_ecr_login_password,
)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
async def test_build_and_push_image_success(
    mock_get_ecr_login_password, mock_get_aws_account_id, mock_exists, mock_run
):
    """Test build_and_push_image with successful build and push."""
    # Mock os.path.exists
    mock_exists.return_value = True

    # Mock get_aws_account_id
    mock_get_aws_account_id.return_value = "123456789012"

    # Mock get_ecr_login_password
    mock_get_ecr_login_password.return_value = "password"

    # Mock subprocess.run with different return values for different commands
    mock_run.side_effect = [
        MagicMock(returncode=0),  # docker login
        MagicMock(returncode=0),  # docker buildx build
        MagicMock(returncode=0),  # docker push
        MagicMock(
            returncode=0, stdout='{"imageIds": [{"imageTag": "latest"}]}'
        ),  # aws ecr list-images
    ]

    # Call build_and_push_image
    tag = await build_and_push_image(
        app_path="/path/to/app",
        repository_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
        tag="latest",
        role_arn="arn:aws:iam::123456789012:role/test-ecr-push-pull-role",
    )

    # Verify os.path.exists was called
    mock_exists.assert_called_once_with("/path/to/app/Dockerfile")

    # Verify subprocess.run was called multiple times
    assert mock_run.call_count == 4

    # Verify the result
    assert tag == "latest"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
async def test_build_and_push_image_dockerfile_not_found(
    mock_get_aws_account_id, mock_exists, mock_run
):
    """Test build_and_push_image with Dockerfile not found."""
    # Mock os.path.exists
    mock_exists.return_value = False

    # Mock get_aws_account_id
    mock_get_aws_account_id.return_value = "123456789012"

    # Call build_and_push_image and expect an exception
    with pytest.raises(FileNotFoundError) as excinfo:
        await build_and_push_image(
            app_path="/path/to/app",
            repository_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
            tag="latest",
            role_arn="arn:aws:iam::123456789012:role/test-ecr-push-pull-role",
        )

    # Verify the error message
    assert "Dockerfile not found" in str(excinfo.value)

    # Verify subprocess.run was not called
    mock_run.assert_not_called()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
async def test_build_and_push_image_build_error(
    mock_get_ecr_login_password, mock_get_aws_account_id, mock_exists, mock_run
):
    """Test build_and_push_image with build error."""
    # Mock os.path.exists
    mock_exists.return_value = True

    # Mock get_aws_account_id
    mock_get_aws_account_id.return_value = "123456789012"

    # Mock get_ecr_login_password
    mock_get_ecr_login_password.return_value = "password"

    # Mock subprocess.run for each command
    mock_run.side_effect = [
        MagicMock(returncode=0),  # docker login
        MagicMock(returncode=1, stderr="Error: failed to build image"),  # docker buildx build
        MagicMock(
            returncode=1, stderr="Error: failed to build image"
        ),  # regular docker build (fallback)
    ]

    # Call build_and_push_image and expect an exception
    with pytest.raises(RuntimeError) as excinfo:
        await build_and_push_image(
            app_path="/path/to/app",
            repository_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
            tag="latest",
            role_arn="arn:aws:iam::123456789012:role/test-ecr-push-pull-role",
        )

    # Verify the error message
    assert "Failed to build Docker image" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
async def test_build_and_push_image_push_error(
    mock_get_ecr_login_password, mock_get_aws_account_id, mock_exists, mock_run
):
    """Test build_and_push_image with push error."""
    # Mock os.path.exists
    mock_exists.return_value = True

    # Mock get_aws_account_id
    mock_get_aws_account_id.return_value = "123456789012"

    # Mock get_ecr_login_password
    mock_get_ecr_login_password.return_value = "password"

    # Mock subprocess.run for each command
    mock_run.side_effect = [
        MagicMock(returncode=0),  # docker login
        MagicMock(returncode=0),  # docker buildx build
        MagicMock(returncode=1, stderr="Error: failed to push image"),  # docker push
    ]

    # Call build_and_push_image and expect an exception
    with pytest.raises(RuntimeError) as excinfo:
        await build_and_push_image(
            app_path="/path/to/app",
            repository_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
            tag="latest",
            role_arn="arn:aws:iam::123456789012:role/test-ecr-push-pull-role",
        )

    # Verify the error message
    assert "Failed to push Docker image" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client_with_role")
async def test_get_ecr_login_password_success(mock_get_aws_client_with_role):
    """Test get_ecr_login_password with successful login."""
    # Mock get_aws_client_with_role
    mock_ecr = MagicMock()
    mock_ecr.get_authorization_token.return_value = {
        "authorizationData": [
            {
                "authorizationToken": "QVdTOmV4YW1wbGVwYXNzd29yZA==",
                # Base64 encoded "AWS:examplepassword"
                "proxyEndpoint": "https://123456789012.dkr.ecr.us-west-2.amazonaws.com",
            }
        ]
    }
    mock_get_aws_client_with_role.return_value = mock_ecr

    # Call get_ecr_login_password
    result = await get_ecr_login_password("arn:aws:iam::123456789012:role/test-ecr-push-pull-role")

    # Verify get_aws_client_with_role was called
    mock_get_aws_client_with_role.assert_called_once_with(
        "ecr", "arn:aws:iam::123456789012:role/test-ecr-push-pull-role"
    )

    # Verify get_authorization_token was called
    mock_ecr.get_authorization_token.assert_called_once()

    # Verify the result
    assert result == "examplepassword"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client_with_role")
async def test_get_ecr_login_password_error(mock_get_aws_client_with_role):
    """Test get_ecr_login_password with error."""
    # Mock get_aws_client_with_role
    mock_ecr = MagicMock()
    mock_ecr.get_authorization_token.side_effect = Exception("Error getting authorization token")
    mock_get_aws_client_with_role.return_value = mock_ecr

    # Call get_ecr_login_password
    with pytest.raises(Exception) as excinfo:
        await get_ecr_login_password("arn:aws:iam::123456789012:role/test-ecr-push-pull-role")

    # Verify the error message
    assert "Error getting" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_get_aws_account_id(mock_get_aws_client):
    """Test get_aws_account_id."""
    # Mock get_aws_client
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
    mock_get_aws_client.return_value = mock_sts

    # Call get_aws_account_id
    result = await get_aws_account_id()

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_once_with("sts")

    # Verify get_caller_identity was called
    mock_sts.get_caller_identity.assert_called_once()

    # Verify the result
    assert result == "123456789012"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client")
async def test_get_aws_account_id_error(mock_get_aws_client):
    """Test get_aws_account_id with error."""
    # Mock get_aws_client
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.side_effect = Exception("Error getting caller identity")
    mock_get_aws_client.return_value = mock_sts

    # Call get_aws_account_id
    with pytest.raises(Exception) as excinfo:
        await get_aws_account_id()

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_once_with("sts")

    # Verify get_caller_identity was called
    mock_sts.get_caller_identity.assert_called_once()

    # Verify the error message
    assert "Error getting caller identity" in str(excinfo.value)
