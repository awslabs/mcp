"""
Unit tests for the detect_image_pull_failures module.
"""

import sys
from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures import (
    detect_image_pull_failures,
)
from tests.unit.utils.async_test_utils import create_mock_ecs_client


@pytest.fixture
def mock_aws_client():
    """Create a mock AWS client for testing."""
    mock_ecs = create_mock_ecs_client()

    with mock.patch(
        "awslabs.ecs_mcp_server.api.clients.ecs_client.get_aws_client", return_value=mock_ecs
    ):
        yield mock_ecs


@pytest.fixture
def test_module_setup():
    """Setup the test environment by getting a reference to the module."""
    # Get direct reference to the module
    detect_failures_module = sys.modules[
        "awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures"
    ]

    # Save the original functions
    original_get_td = detect_failures_module._get_task_definitions
    original_validate = detect_failures_module._validate_container_images

    # Return module reference and original functions for later restoration
    yield detect_failures_module, original_get_td, original_validate

    # Restore original functions after test
    detect_failures_module._get_task_definitions = original_get_td
    detect_failures_module._validate_container_images = original_validate


# ----------------------------------------------------------------------------
# Core Functionality Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_detect_image_pull_failures_happy_path(test_module_setup):
    """Test detect_image_pull_failures with all valid images."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock functions
    async def mock_get_td(app_name):
        return [
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "containerDefinitions": [{"name": "container1", "image": "image1"}],
                "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
            }
        ]

    async def mock_validate(task_definitions):
        return [
            {
                "image": "image1",
                "exists": "true",
                "repository_type": "ecr",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "container_name": "container1",
            }
        ]

    # Replace with mocks
    detect_failures_module._get_task_definitions = mock_get_td
    detect_failures_module._validate_container_images = mock_validate

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert len(result["image_issues"]) == 0
    assert "All container images appear to be valid" in result["assessment"]


@pytest.mark.anyio
async def test_detect_image_pull_failures_no_task_definitions(test_module_setup):
    """Test detect_image_pull_failures with no task definitions."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock function that returns empty list
    async def mock_get_td(app_name):
        return []

    # Replace with mock
    detect_failures_module._get_task_definitions = mock_get_td

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert "No task definitions found" in result["assessment"]
    assert "Check if your task definition is named differently" in result["recommendations"][0]


@pytest.mark.anyio
async def test_detect_image_pull_failures_with_invalid_images(test_module_setup):
    """Test detect_image_pull_failures with invalid images."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock functions
    async def mock_get_td(app_name):
        return [
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "containerDefinitions": [
                    {"name": "container1", "image": "valid-image"},
                    {"name": "container2", "image": "invalid-image"},
                ],
                "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
            }
        ]

    async def mock_validate(task_definitions):
        return [
            {
                "image": "valid-image",
                "exists": "true",
                "repository_type": "ecr",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "container_name": "container1",
            },
            {
                "image": "invalid-image",
                "exists": "false",
                "repository_type": "ecr",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "container_name": "container2",
            },
        ]

    # Replace with mocks
    detect_failures_module._get_task_definitions = mock_get_td
    detect_failures_module._validate_container_images = mock_validate

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert len(result["image_issues"]) == 1
    assert "Found 1 container image" in result["assessment"]
    assert len(result["recommendations"]) > 0
    assert "invalid-image" in result["recommendations"][0]


@pytest.mark.anyio
async def test_detect_image_pull_failures_comprehensive(test_module_setup):
    """Test the full workflow of detect_image_pull_failures with multiple issues."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Define mock functions
    async def mock_get_td(app_name):
        return [
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "containerDefinitions": [
                    {"name": "container1", "image": "image1"},
                    {"name": "container2", "image": "image2"},
                ],
            },
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task2:1",
                "containerDefinitions": [{"name": "container3", "image": "image3"}],
            },
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task3:1",
                "containerDefinitions": [{"name": "container4", "image": "image4"}],
            },
        ]

    async def mock_validate(task_definitions):
        return [
            {
                "image": "image1",
                "exists": "true",
                "repository_type": "ecr",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "container_name": "container1",
            },
            {
                "image": "image2",
                "exists": "false",
                "repository_type": "ecr",
                "reason": "Repository not found",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "container_name": "container2",
            },
            {
                "image": "image3",
                "exists": "true",
                "repository_type": "ecr",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task2:1",
                "container_name": "container3",
            },
            {
                "image": "image4",
                "exists": "false",
                "repository_type": "ecr",
                "reason": "Access denied",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task3:1",
                "container_name": "container4",
            },
        ]

    # Replace with mocks
    detect_failures_module._get_task_definitions = mock_get_td
    detect_failures_module._validate_container_images = mock_validate

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert len(result["image_issues"]) == 2
    assert "Found 2 container image(s) that may be causing pull failures" in result["assessment"]
    assert len(result["recommendations"]) >= 2


# ----------------------------------------------------------------------------
# Edge Case Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_detect_image_pull_failures_with_missing_execution_role(test_module_setup):
    """Test detect_image_pull_failures with missing execution role."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock functions
    async def mock_get_td(app_name):
        return [
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "containerDefinitions": [
                    {
                        "name": "container1",
                        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:latest",
                    }
                ],
                # No executionRoleArn
            }
        ]

    async def mock_validate(task_definitions):
        return [
            {
                "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:latest",
                "exists": "true",
                "repository_type": "ecr",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "container_name": "container1",
            }
        ]

    # Replace with mocks
    detect_failures_module._get_task_definitions = mock_get_td
    detect_failures_module._validate_container_images = mock_validate

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert len(result["image_issues"]) == 0
    assert "All container images appear to be valid" in result["assessment"]
    assert any("executionRole" in rec for rec in result["recommendations"])


@pytest.mark.anyio
async def test_detect_image_pull_failures_external_image(test_module_setup):
    """Test detect_image_pull_failures with external images."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock functions
    async def mock_get_td(app_name):
        return [
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "containerDefinitions": [{"name": "container1", "image": "nginx:latest"}],
                "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
            }
        ]

    async def mock_validate(task_definitions):
        return [
            {
                "image": "nginx:latest",
                "exists": "unknown",
                "repository_type": "external",
                "task_definition": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "container_name": "container1",
            }
        ]

    # Replace with mocks
    detect_failures_module._get_task_definitions = mock_get_td
    detect_failures_module._validate_container_images = mock_validate

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert len(result["image_issues"]) == 1
    assert "found" in result["assessment"].lower()
    assert any("External image" in rec for rec in result["recommendations"])


# ----------------------------------------------------------------------------
# Error Handling Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
async def test_detect_image_pull_failures_task_definitions_error(test_module_setup):
    """Test detect_image_pull_failures with error from get_task_definitions."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock function that raises an exception
    async def mock_get_td(app_name):
        raise Exception("Failed to get task definitions")

    # Replace with mock
    detect_failures_module._get_task_definitions = mock_get_td

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "error"
    assert "Failed to get task definitions" in result["error"]
    assert "Error checking for image pull failures" in result["assessment"]


@pytest.mark.anyio
async def test_detect_image_pull_failures_validate_images_error(test_module_setup):
    """Test detect_image_pull_failures with error from validate_container_images."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock functions
    async def mock_get_td(app_name):
        return [
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "containerDefinitions": [{"name": "container1", "image": "image1"}],
            }
        ]

    async def mock_validate(task_definitions):
        raise Exception("Failed to validate images")

    # Replace with mocks
    detect_failures_module._get_task_definitions = mock_get_td
    detect_failures_module._validate_container_images = mock_validate

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "error"
    assert "Failed to validate images" in result["error"]
    assert "Error validating container images" in result["assessment"]


@pytest.mark.anyio
async def test_detect_image_pull_failures_client_error(test_module_setup):
    """Test detect_image_pull_failures with AWS ClientError."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock functions
    async def mock_get_td(app_name):
        return [
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/task1:1",
                "containerDefinitions": [{"name": "container1", "image": "image1"}],
            }
        ]

    async def mock_validate(task_definitions):
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "User not authorized to access ECR"}},
            "DescribeImages",
        )

    # Replace with mocks
    detect_failures_module._get_task_definitions = mock_get_td
    detect_failures_module._validate_container_images = mock_validate

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "error"
    assert "User not authorized to access ECR" in result["error"]
    assert "Error validating container images" in result["assessment"]


@pytest.mark.anyio
async def test_detect_image_pull_failures_general_exception(test_module_setup):
    """Test detect_image_pull_failures with general exception handling."""
    # Unpack the module reference and original functions
    detect_failures_module, _, _ = test_module_setup

    # Create mock function that returns something not iterable (will cause an exception)
    async def mock_get_td(app_name):
        return 123  # This will cause an exception in the function when it tries to iterate

    # Replace with mock
    detect_failures_module._get_task_definitions = mock_get_td

    # Call the function
    result = await detect_image_pull_failures("test-app")

    # Verify the result
    assert result["status"] == "error"
    assert "error" in result
    assert len(result["image_issues"]) == 0
