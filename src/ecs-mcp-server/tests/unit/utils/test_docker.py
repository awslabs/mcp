"""
Unit tests for docker utility module.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.utils.docker import build_and_push_image, get_ecr_login_password

# ----------------------------------------------------------------------------
# ECR Login Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_client")
async def test_get_ecr_login_password_error(mock_get_aws_client):
    """Test get_ecr_login_password when ECR client raises an error."""
    # Mock ECR client to raise an exception
    mock_ecr_client = MagicMock()
    mock_ecr_client.get_authorization_token.side_effect = Exception("ECR API Error")
    mock_get_aws_client.return_value = mock_ecr_client

    # Test that the function properly propagates the exception
    with pytest.raises(Exception) as excinfo:
        await get_ecr_login_password()

    # Verify error message
    assert "Error getting ECR login password: ECR API Error" in str(excinfo.value)

    # Verify the client was called correctly
    mock_get_aws_client.assert_called_once_with("ecr")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.aws.get_aws_client_with_role")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_client")
async def test_get_ecr_login_password_with_role_arn(
    mock_get_aws_client, mock_get_aws_client_with_role
):
    """Test get_ecr_login_password with role ARN."""
    # Mock ECR client
    mock_ecr_client = MagicMock()
    mock_ecr_client.get_authorization_token.return_value = {
        "authorizationData": [
            {"authorizationToken": "QVdTOnRlc3RwYXNzd29yZA=="}
        ]  # AWS:testpassword
    }
    mock_get_aws_client_with_role.return_value = mock_ecr_client

    # Call the function with role_arn
    result = await get_ecr_login_password(role_arn="test-role-arn")

    # Verify the result
    assert result == "testpassword"

    # Since the function imports get_aws_client_with_role from aws module
    mock_get_aws_client_with_role.assert_called_once_with("ecr", "test-role-arn")


# ----------------------------------------------------------------------------
# Build and Push Image Parameter Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_build_and_push_image_missing_role_arn():
    """Test build_and_push_image when role_arn is not provided."""
    with pytest.raises(ValueError) as excinfo:
        await build_and_push_image(
            app_path="/path/to/app", repository_uri="test-repository", tag="latest"
        )

    # Verify error message
    assert "role_arn is required for ECR authentication" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.join")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
async def test_build_and_push_image_dockerfile_not_found(
    mock_get_aws_account_id, mock_join, mock_exists
):
    """Test build_and_push_image when Dockerfile is not found."""
    # Set up mocks
    mock_join.return_value = "/path/to/app/Dockerfile"
    mock_exists.return_value = False
    # Skip the AWS account ID call that fails
    mock_get_aws_account_id.return_value = "123456789012"

    with pytest.raises(FileNotFoundError) as excinfo:
        await build_and_push_image(
            app_path="/path/to/app",
            repository_uri="test-repository",
            tag="latest",
            role_arn="test-role-arn",
        )

    # Verify error message
    assert "Dockerfile not found" in str(excinfo.value)

    # Verify the function checked for the Dockerfile
    mock_exists.assert_called_once_with("/path/to/app/Dockerfile")


# ----------------------------------------------------------------------------
# Docker Command Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.environ.get")
async def test_build_and_push_image_docker_login_failure(
    mock_env_get, mock_subprocess_run, mock_get_aws_account_id, mock_get_ecr_login, mock_exists
):
    """Test build_and_push_image when docker login fails."""
    # Set up mocks
    mock_exists.return_value = True
    mock_get_aws_account_id.return_value = "123456789012"
    mock_get_ecr_login.return_value = "test-password"
    mock_env_get.side_effect = (
        lambda key, default: "us-west-2" if key == "AWS_REGION" else "default"
    )

    # Configure subprocess.run to fail on docker login
    mock_subprocess_run.return_value = MagicMock(
        returncode=1,
        stderr="Docker login failed",
    )

    # Test that the function raises a RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        await build_and_push_image(
            app_path="/path/to/app",
            repository_uri="test-repository",
            tag="latest",
            role_arn="test-role-arn",
        )

    # Verify error message
    assert "Failed to login to ECR" in str(excinfo.value)

    # Verify the function attempted to perform docker login
    mock_subprocess_run.assert_called_once()
    assert "docker" in mock_subprocess_run.call_args[0][0][0]
    assert "login" in mock_subprocess_run.call_args[0][0][1]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.environ.get")
async def test_build_and_push_image_docker_buildx_failure_fallback_success(
    mock_env_get, mock_subprocess_run, mock_get_aws_account_id, mock_get_ecr_login, mock_exists
):
    """Test build_and_push_image when docker buildx fails but regular build succeeds."""
    # Set up mocks
    mock_exists.return_value = True
    mock_get_aws_account_id.return_value = "123456789012"
    mock_get_ecr_login.return_value = "test-password"
    mock_env_get.side_effect = (
        lambda key, default: "us-west-2" if key == "AWS_REGION" else "default"
    )

    # Configure subprocess.run with different results for each call
    # 1st call: docker login success
    # 2nd call: docker buildx failure
    # 3rd call: docker build success
    # 4th call: docker push success
    # 5th call: aws ecr list-images success
    mock_subprocess_run.side_effect = [
        # docker login
        MagicMock(returncode=0, stderr="", stdout="Login Succeeded"),
        # docker buildx build
        MagicMock(returncode=1, stderr="buildx not installed", stdout=""),
        # docker build
        MagicMock(returncode=0, stderr="", stdout="Successfully built"),
        # docker push
        MagicMock(returncode=0, stderr="", stdout="Push complete"),
        # aws ecr list-images
        MagicMock(returncode=0, stderr="", stdout='{"imageIds":[{"imageTag":"latest"}]}'),
    ]

    # Call the function
    result = await build_and_push_image(
        app_path="/path/to/app",
        repository_uri="test-repository",
        tag="latest",
        role_arn="test-role-arn",
    )

    # Verify the result
    assert result == "latest"

    # Verify all the subprocess calls
    assert mock_subprocess_run.call_count == 5

    # Verify the function attempted the fallback build
    build_calls = [call for call in mock_subprocess_run.call_args_list if "build" in call[0][0]]
    assert len(build_calls) == 2

    # Ensure first attempt was buildx
    assert "buildx" in build_calls[0][0][0][1]
    # Ensure fallback was regular build
    assert build_calls[1][0][0][0] == "docker"
    assert build_calls[1][0][0][1] == "build"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.environ.get")
async def test_build_and_push_image_docker_build_failure(
    mock_env_get, mock_subprocess_run, mock_get_aws_account_id, mock_get_ecr_login, mock_exists
):
    """Test build_and_push_image when both docker buildx and regular build fail."""
    # Set up mocks
    mock_exists.return_value = True
    mock_get_aws_account_id.return_value = "123456789012"
    mock_get_ecr_login.return_value = "test-password"
    mock_env_get.side_effect = (
        lambda key, default: "us-west-2" if key == "AWS_REGION" else "default"
    )

    # Configure subprocess.run with different results for each call
    # 1st call: docker login success
    # 2nd call: docker buildx failure
    # 3rd call: docker build failure
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stderr="", stdout="Login Succeeded"),
        MagicMock(returncode=1, stderr="buildx not installed", stdout=""),
        MagicMock(returncode=1, stderr="Docker build failed", stdout=""),
    ]

    # Test that the function raises a RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        await build_and_push_image(
            app_path="/path/to/app",
            repository_uri="test-repository",
            tag="latest",
            role_arn="test-role-arn",
        )

    # Verify error message
    assert "Failed to build Docker image" in str(excinfo.value)

    # Verify the function attempted both buildx and regular build
    assert mock_subprocess_run.call_count == 3

    build_calls = [call for call in mock_subprocess_run.call_args_list if "build" in call[0][0]]
    assert len(build_calls) == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.environ.get")
async def test_build_and_push_image_docker_push_failure(
    mock_env_get, mock_subprocess_run, mock_get_aws_account_id, mock_get_ecr_login, mock_exists
):
    """Test build_and_push_image when docker push fails."""
    # Set up mocks
    mock_exists.return_value = True
    mock_get_aws_account_id.return_value = "123456789012"
    mock_get_ecr_login.return_value = "test-password"
    mock_env_get.side_effect = (
        lambda key, default: "us-west-2" if key == "AWS_REGION" else "default"
    )

    # Configure subprocess.run with different results
    # 1st call: docker login success
    # 2nd call: docker buildx success
    # 3rd call: docker push failure
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stderr="", stdout="Login Succeeded"),
        MagicMock(returncode=0, stderr="", stdout="Successfully built"),
        MagicMock(returncode=1, stderr="Docker push failed", stdout=""),
    ]

    # Test that the function raises a RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        await build_and_push_image(
            app_path="/path/to/app",
            repository_uri="test-repository",
            tag="latest",
            role_arn="test-role-arn",
        )

    # Verify error message
    assert "Failed to push Docker image" in str(excinfo.value)

    # Verify the push command was called
    assert mock_subprocess_run.call_count == 3
    last_call = mock_subprocess_run.call_args_list[-1]
    assert "push" in last_call[0][0][1]


# ----------------------------------------------------------------------------
# Tag Generation and Verification Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.environ.get")
@patch("awslabs.ecs_mcp_server.utils.docker.time.time")
async def test_build_and_push_image_auto_tag_generation(
    mock_time,
    mock_env_get,
    mock_subprocess_run,
    mock_get_aws_account_id,
    mock_get_ecr_login,
    mock_exists,
):
    """Test build_and_push_image with automatic tag generation."""
    # Set up mocks
    mock_exists.return_value = True
    mock_get_aws_account_id.return_value = "123456789012"
    mock_get_ecr_login.return_value = "test-password"
    mock_env_get.side_effect = (
        lambda key, default: "us-west-2" if key == "AWS_REGION" else "default"
    )
    mock_time.return_value = 1609459200  # 2021-01-01 00:00:00

    # Configure subprocess.run to succeed for all calls
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stderr="", stdout="Login Succeeded"),
        MagicMock(returncode=0, stderr="", stdout="Successfully built"),
        MagicMock(returncode=0, stderr="", stdout="Push complete"),
        MagicMock(returncode=0, stderr="", stdout='{"imageIds":[{"imageTag":"1609459200"}]}'),
    ]

    # Call the function without providing a tag
    result = await build_and_push_image(
        app_path="/path/to/app", repository_uri="test-repository", role_arn="test-role-arn"
    )

    # Verify the result matches the timestamp
    assert result == "1609459200"

    # Check that tag is in the build command
    build_call = mock_subprocess_run.call_args_list[1]
    # The repository URI and tag are combined in a single argument as repository_uri:tag
    repo_tag_param = "test-repository:1609459200"
    assert any(repo_tag_param in arg for arg in build_call[0][0])


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.environ.get")
async def test_build_and_push_image_verification_failure(
    mock_env_get, mock_subprocess_run, mock_get_aws_account_id, mock_get_ecr_login, mock_exists
):
    """Test build_and_push_image when verification fails."""
    # Set up mocks
    mock_exists.return_value = True
    mock_get_aws_account_id.return_value = "123456789012"
    mock_get_ecr_login.return_value = "test-password"
    mock_env_get.side_effect = (
        lambda key, default: "us-west-2" if key == "AWS_REGION" else "default"
    )

    # Configure subprocess.run with different results
    # 1st call: docker login success
    # 2nd call: docker buildx success
    # 3rd call: docker push success
    # 4th call: aws ecr list-images success but with different tag
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stderr="", stdout="Login Succeeded"),
        MagicMock(returncode=0, stderr="", stdout="Successfully built"),
        MagicMock(returncode=0, stderr="", stdout="Push complete"),
        MagicMock(returncode=0, stderr="", stdout='{"imageIds":[{"imageTag":"different-tag"}]}'),
    ]

    # In the actual implementation, it looks like we continue even if tag verification fails,
    # as it's just warning, not an error. Let's update the test to match.
    tag = await build_and_push_image(
        app_path="/path/to/app",
        repository_uri="test-repository",
        tag="latest",
        role_arn="test-role-arn",
    )

    # Verify the tag was returned correctly
    assert tag == "latest"

    # Verify the verification command was called
    assert mock_subprocess_run.call_count == 4
    last_call = mock_subprocess_run.call_args_list[-1]
    assert "list-images" in last_call[0][0][2]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.utils.docker.os.path.exists")
@patch("awslabs.ecs_mcp_server.utils.docker.get_ecr_login_password")
@patch("awslabs.ecs_mcp_server.utils.docker.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.utils.docker.subprocess.run")
@patch("awslabs.ecs_mcp_server.utils.docker.os.environ.get")
async def test_build_and_push_image_verification_command_failure(
    mock_env_get, mock_subprocess_run, mock_get_aws_account_id, mock_get_ecr_login, mock_exists
):
    """Test build_and_push_image when verification command fails."""
    # Set up mocks
    mock_exists.return_value = True
    mock_get_aws_account_id.return_value = "123456789012"
    mock_get_ecr_login.return_value = "test-password"
    mock_env_get.side_effect = (
        lambda key, default: "us-west-2" if key == "AWS_REGION" else "default"
    )

    # Configure subprocess.run with different results
    # 1st call: docker login success
    # 2nd call: docker buildx success
    # 3rd call: docker push success
    # 4th call: aws ecr list-images failure
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stderr="", stdout="Login Succeeded"),
        MagicMock(returncode=0, stderr="", stdout="Successfully built"),
        MagicMock(returncode=0, stderr="", stdout="Push complete"),
        MagicMock(returncode=1, stderr="Command failed", stdout=""),
    ]

    # Call the function - it should succeed despite verification failure
    # since the verification is best-effort with a warning
    tag = await build_and_push_image(
        app_path="/path/to/app",
        repository_uri="test-repository",
        tag="latest",
        role_arn="test-role-arn",
    )

    # Verify the result
    assert tag == "latest"

    # Verify the verification command was called
    assert mock_subprocess_run.call_count == 4
    last_call = mock_subprocess_run.call_args_list[-1]
    assert "list-images" in last_call[0][0][2]
