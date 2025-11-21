"""
Comprehensive unit tests for ECS Express Mode API functionality.

Tests cover api/express.py:
- build_and_push_image_to_ecr
- validate_prerequisites
- delete_express_gateway_service
- delete_ecr_infrastructure
- delete_app

Following DRY principles with parameterized, modular tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from awslabs.ecs_mcp_server.api.express import (
    build_and_push_image_to_ecr,
    delete_app,
    delete_ecr_infrastructure,
    delete_express_gateway_service,
    validate_prerequisites,
    wait_for_service_ready,
)

# ============================================================================
# Fixtures for common test data
# ============================================================================


@pytest.fixture
def mock_ecr_result():
    """Mock ECR infrastructure creation result."""
    return {
        "resources": {
            "ecr_repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-app",
            "ecr_push_pull_role_arn": "arn:aws:iam::123456789012:role/my-app-ecr-role",
        },
        "stack_name": "my-app-ecr-infrastructure",
    }


# ============================================================================
# Tests for build_and_push_image_to_ecr
# ============================================================================


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.express.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.express.create_ecr_infrastructure")
@patch("awslabs.ecs_mcp_server.api.express.build_and_push_image")
async def test_build_and_push_success(
    mock_build_push, mock_create_ecr, mock_prep_templates, mock_validate, mock_ecr_result
):
    """Test successful image build and push to ECR."""
    mock_prep_templates.return_value = {"ecr_template_content": "template"}
    mock_create_ecr.return_value = mock_ecr_result
    mock_build_push.return_value = "v1.0.0"

    result = await build_and_push_image_to_ecr("my-app", "/path/to/app", "v1.0.0")

    assert result["repository_uri"] == mock_ecr_result["resources"]["ecr_repository_uri"]
    assert result["image_tag"] == "v1.0.0"
    assert result["full_image_uri"].endswith(":v1.0.0")
    assert result["stack_name"] == "my-app-ecr-infrastructure"
    mock_validate.assert_called_once_with("my-app")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.validate_app_name")
async def test_build_and_push_invalid_app_name(mock_validate):
    """Test build fails with invalid app name."""
    mock_validate.side_effect = ValueError("Invalid app name")

    with pytest.raises(ValueError, match="Invalid app name"):
        await build_and_push_image_to_ecr("invalid@name", "/path/to/app")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.express.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.express.create_ecr_infrastructure")
async def test_build_and_push_ecr_creation_fails(mock_create_ecr, mock_prep, mock_validate):
    """Test build fails when ECR creation fails."""
    mock_prep.return_value = {"ecr_template_content": "template"}
    mock_create_ecr.side_effect = Exception("ECR creation failed")

    with pytest.raises(Exception, match="ECR creation failed"):
        await build_and_push_image_to_ecr("my-app", "/path/to/app")


# ============================================================================
# Tests for validate_prerequisites
# ============================================================================


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.express.check_iam_role_exists_and_policy")
@patch("awslabs.ecs_mcp_server.api.express.check_ecr_image_exists")
async def test_validate_prerequisites_all_valid(mock_check_image, mock_check_role, mock_account):
    """Test validation succeeds when all prerequisites are met."""
    mock_account.return_value = "123456789012"
    mock_check_role.side_effect = [
        {"status": "valid", "message": "Role valid"},
        {"status": "valid", "message": "Role valid"},
    ]
    mock_check_image.return_value = {"status": "exists", "message": "Image found"}

    result = await validate_prerequisites("123456789012.dkr.ecr.us-west-2.amazonaws.com/app:tag")

    assert result["valid"] is True
    assert len(result["errors"]) == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.express.check_iam_role_exists_and_policy")
@patch("awslabs.ecs_mcp_server.api.express.check_ecr_image_exists")
async def test_validate_prerequisites_execution_role_missing(
    mock_check_image, mock_check_role, mock_account
):
    """Test validation fails when execution role is missing."""
    mock_account.return_value = "123456789012"
    mock_check_role.side_effect = [
        {"status": "not_found", "error": "Role not found"},
        {"status": "valid"},
    ]
    mock_check_image.return_value = {"status": "exists"}

    result = await validate_prerequisites("123456789012.dkr.ecr.us-west-2.amazonaws.com/app:tag")

    assert result["valid"] is False
    assert len(result["errors"]) == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.express.check_iam_role_exists_and_policy")
@patch("awslabs.ecs_mcp_server.api.express.check_ecr_image_exists")
async def test_validate_prerequisites_infra_role_missing(
    mock_check_image, mock_check_role, mock_account
):
    """Test validation fails when infrastructure role is missing."""
    mock_account.return_value = "123456789012"
    mock_check_role.side_effect = [
        {"status": "valid"},
        {"status": "not_found", "error": "Infrastructure role not found"},
    ]
    mock_check_image.return_value = {"status": "exists"}

    result = await validate_prerequisites("123456789012.dkr.ecr.us-west-2.amazonaws.com/app:tag")

    assert result["valid"] is False
    assert len(result["errors"]) == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.express.check_iam_role_exists_and_policy")
@patch("awslabs.ecs_mcp_server.api.express.check_ecr_image_exists")
async def test_validate_prerequisites_image_missing(
    mock_check_image, mock_check_role, mock_account
):
    """Test validation fails when image is missing."""
    mock_account.return_value = "123456789012"
    mock_check_role.side_effect = [{"status": "valid"}, {"status": "valid"}]
    mock_check_image.return_value = {"status": "not_found", "error": "Image not found"}

    result = await validate_prerequisites("123456789012.dkr.ecr.us-west-2.amazonaws.com/app:tag")

    assert result["valid"] is False
    assert len(result["errors"]) == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.express.check_iam_role_exists_and_policy")
@patch("awslabs.ecs_mcp_server.api.express.check_ecr_image_exists")
async def test_validate_prerequisites_missing_error_details(
    mock_check_image, mock_check_role, mock_account
):
    """Test validation with missing error details (fallback messages)."""
    mock_account.return_value = "123456789012"
    mock_check_role.side_effect = [
        {"status": "not_found"},  # No 'error' key
        {"status": "invalid"},  # No 'error' key
    ]
    mock_check_image.return_value = {"status": "not_found"}  # No 'error' key

    result = await validate_prerequisites("123456789012.dkr.ecr.us-west-2.amazonaws.com/app:tag")

    assert result["valid"] is False
    assert len(result["errors"]) == 3


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.express.check_iam_role_exists_and_policy")
@patch("awslabs.ecs_mcp_server.api.express.check_ecr_image_exists")
async def test_validate_prerequisites_with_custom_roles(
    mock_check_image, mock_check_role, mock_account
):
    """Test validation with custom role ARNs."""
    mock_account.return_value = "123456789012"
    mock_check_role.side_effect = [{"status": "valid"}, {"status": "valid"}]
    mock_check_image.return_value = {"status": "exists"}

    result = await validate_prerequisites(
        "123456789012.dkr.ecr.us-west-2.amazonaws.com/app:tag",
        execution_role_arn="arn:aws:iam::123456789012:role/custom-exec",
        infrastructure_role_arn="arn:aws:iam::123456789012:role/custom-infra",
    )

    assert result["valid"] is True
    assert mock_check_role.call_count == 2


# ============================================================================
# Tests for delete_express_gateway_service
# ============================================================================


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_client")
async def test_delete_express_gateway_service_success(mock_get_client):
    """Test successful Express Gateway Service deletion."""
    mock_client = MagicMock()
    mock_client.delete_express_gateway_service.return_value = {"service": {}}
    mock_get_client.return_value = mock_client

    result = await delete_express_gateway_service("arn:aws:ecs:us-west-2:123:service/my-svc")

    assert result["status"] == "deleted"
    assert "successfully" in result["message"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_client")
async def test_delete_express_gateway_service_failure(mock_get_client):
    """Test Express Gateway Service deletion failure."""
    mock_client = MagicMock()
    mock_client.delete_express_gateway_service.side_effect = Exception("Delete failed")
    mock_get_client.return_value = mock_client

    result = await delete_express_gateway_service("arn:aws:ecs:us-west-2:123:service/my-svc")

    assert result["status"] == "failed"
    assert "Delete failed" in result["error"]


# ============================================================================
# Tests for delete_ecr_infrastructure
# ============================================================================


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_client")
async def test_delete_ecr_infrastructure_success(mock_get_client):
    """Test successful ECR infrastructure deletion."""
    mock_client = MagicMock()
    mock_client.describe_stacks.return_value = {"Stacks": [{"StackName": "my-app-ecr"}]}
    mock_waiter = MagicMock()
    mock_client.get_waiter.return_value = mock_waiter
    mock_get_client.return_value = mock_client

    result = await delete_ecr_infrastructure("my-app")

    assert result["status"] == "deleted"
    assert result["stack_name"] == "my-app-ecr-infrastructure"
    mock_client.delete_stack.assert_called_once()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_client")
async def test_delete_ecr_infrastructure_not_found(mock_get_client):
    """Test ECR infrastructure deletion when stack doesn't exist."""
    from botocore.exceptions import ClientError

    mock_client = MagicMock()
    error = ClientError(
        {"Error": {"Code": "ValidationError", "Message": "Stack does not exist"}},
        "DescribeStacks",
    )
    error.__str__ = lambda: "does not exist"
    mock_client.describe_stacks.side_effect = error
    mock_client.exceptions = MagicMock()
    mock_client.exceptions.ClientError = ClientError
    mock_get_client.return_value = mock_client

    result = await delete_ecr_infrastructure("my-app")

    assert result["status"] == "not_found"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_client")
async def test_delete_ecr_infrastructure_deletion_fails(mock_get_client):
    """Test ECR infrastructure deletion when delete_stack fails."""
    mock_client = MagicMock()
    mock_client.describe_stacks.return_value = {"Stacks": [{"StackName": "test-stack"}]}
    mock_client.delete_stack.side_effect = Exception("Deletion error")
    mock_get_client.return_value = mock_client

    result = await delete_ecr_infrastructure("my-app")

    assert result["status"] == "failed"
    assert "Deletion error" in result["error"]


# ============================================================================
# Tests for delete_app
# ============================================================================


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.delete_express_gateway_service")
@patch("awslabs.ecs_mcp_server.api.express.delete_ecr_infrastructure")
@patch("awslabs.ecs_mcp_server.api.express.validate_app_name")
async def test_delete_app_complete_success(mock_validate, mock_delete_ecr, mock_delete_svc):
    """Test complete successful app deletion."""
    mock_delete_svc.return_value = {"status": "deleted"}
    mock_delete_ecr.return_value = {
        "status": "deleted",
        "deleted_resources": ["repo", "role"],
    }

    result = await delete_app("arn:aws:ecs:us-west-2:123:service/my-svc", "my-app")

    assert result["service_deletion"]["status"] == "deleted"
    assert result["ecr_deletion"]["status"] == "deleted"
    assert result["summary"]["status"] == "success"
    assert len(result["errors"]) == 0


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.delete_express_gateway_service")
@patch("awslabs.ecs_mcp_server.api.express.delete_ecr_infrastructure")
@patch("awslabs.ecs_mcp_server.api.express.validate_app_name")
async def test_delete_app_service_fails(mock_validate, mock_delete_ecr, mock_delete_svc):
    """Test app deletion when service deletion fails."""
    mock_delete_svc.return_value = {"status": "failed", "error": "Service delete failed"}
    mock_delete_ecr.return_value = {"status": "deleted", "deleted_resources": ["repo"]}

    result = await delete_app("arn:aws:ecs:us-west-2:123:service/my-svc", "my-app")

    assert result["service_deletion"]["status"] == "failed"
    assert result["summary"]["status"] == "partial"
    assert len(result["errors"]) == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.delete_express_gateway_service")
@patch("awslabs.ecs_mcp_server.api.express.delete_ecr_infrastructure")
@patch("awslabs.ecs_mcp_server.api.express.validate_app_name")
async def test_delete_app_ecr_fails(mock_validate, mock_delete_ecr, mock_delete_svc):
    """Test app deletion when ECR deletion fails."""
    mock_delete_svc.return_value = {"status": "deleted"}
    mock_delete_ecr.return_value = {"status": "failed", "error": "ECR delete failed"}

    result = await delete_app("arn:aws:ecs:us-west-2:123:service/my-svc", "my-app")

    assert result["ecr_deletion"]["status"] == "failed"
    assert result["summary"]["status"] == "partial"
    assert len(result["errors"]) == 1


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.delete_express_gateway_service")
@patch("awslabs.ecs_mcp_server.api.express.delete_ecr_infrastructure")
@patch("awslabs.ecs_mcp_server.api.express.validate_app_name")
async def test_delete_app_both_fail(mock_validate, mock_delete_ecr, mock_delete_svc):
    """Test app deletion when both deletions fail."""
    mock_delete_svc.return_value = {"status": "failed", "error": "Service failed"}
    mock_delete_ecr.return_value = {"status": "failed", "error": "ECR failed"}

    result = await delete_app("arn:aws:ecs:us-west-2:123:service/my-svc", "my-app")

    assert result["summary"]["status"] == "failed"
    assert len(result["errors"]) == 2


# ============================================================================
# Tests for wait_for_service_ready
# ============================================================================


@pytest.mark.anyio
@pytest.mark.parametrize(
    "task_responses,expected_status,expected_in_message",
    [
        # Success on first attempt
        (
            [
                {
                    "list": {"taskArns": ["arn:aws:ecs:us-west-2:123:task/abc"]},
                    "describe": {
                        "tasks": [
                            {
                                "taskArn": "arn:aws:ecs:us-west-2:123:task/abc",
                                "lastStatus": "RUNNING",
                            }
                        ]
                    },
                }
            ],
            "success",
            "1 running",
        ),
        # Success after retry (no tasks -> running)
        (
            [
                {"list": {"taskArns": []}, "describe": None},
                {
                    "list": {"taskArns": ["arn:aws:ecs:us-west-2:123:task/abc"]},
                    "describe": {
                        "tasks": [
                            {
                                "taskArn": "arn:aws:ecs:us-west-2:123:task/abc",
                                "lastStatus": "RUNNING",
                            }
                        ]
                    },
                },
            ],
            "success",
            "running",
        ),
        # Multiple running tasks
        (
            [
                {
                    "list": {
                        "taskArns": [
                            "arn:aws:ecs:us-west-2:123:task/abc",
                            "arn:aws:ecs:us-west-2:123:task/def",
                        ]
                    },
                    "describe": {
                        "tasks": [
                            {
                                "taskArn": "arn:aws:ecs:us-west-2:123:task/abc",
                                "lastStatus": "RUNNING",
                            },
                            {
                                "taskArn": "arn:aws:ecs:us-west-2:123:task/def",
                                "lastStatus": "RUNNING",
                            },
                        ]
                    },
                }
            ],
            "success",
            "2 running",
        ),
    ],
)
@patch("awslabs.ecs_mcp_server.api.express.asyncio.sleep")
@patch("awslabs.ecs_mcp_server.api.express.get_aws_client")
async def test_wait_for_service_ready_success_scenarios(
    mock_get_client, mock_sleep, task_responses, expected_status, expected_in_message
):
    """Test various success scenarios for wait_for_service_ready."""
    mock_client = MagicMock()

    list_responses = [r["list"] for r in task_responses]
    describe_responses = [r["describe"] for r in task_responses if r["describe"]]

    mock_client.list_tasks.side_effect = list_responses
    mock_client.describe_tasks.side_effect = describe_responses
    mock_get_client.return_value = mock_client

    result = await wait_for_service_ready("my-cluster", "my-service")

    assert result["status"] == expected_status
    assert expected_in_message in result["message"].lower()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.asyncio.sleep", return_value=None)
@patch("awslabs.ecs_mcp_server.api.express.get_aws_client")
async def test_wait_for_service_ready_timeout(mock_get_client, mock_sleep):
    """Test timeout scenario when service doesn't become ready."""
    mock_client = MagicMock()
    mock_client.list_tasks.return_value = {"taskArns": []}
    mock_get_client.return_value = mock_client

    result = await wait_for_service_ready("my-cluster", "my-service", timeout_seconds=1)

    assert result["status"] == "timeout"
    assert "timeout" in result["message"].lower()


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.express.get_aws_client")
async def test_wait_for_service_ready_error(mock_get_client):
    """Test error handling when ECS client creation fails."""
    mock_get_client.side_effect = Exception("Failed to create ECS client")

    result = await wait_for_service_ready("my-cluster", "my-service")

    assert result["status"] == "failed"
    assert "error" in result["message"].lower()
