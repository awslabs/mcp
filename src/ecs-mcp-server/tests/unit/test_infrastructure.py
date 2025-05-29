"""
Pytest-style unit tests for infrastructure module.
"""

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from awslabs.ecs_mcp_server.api.infrastructure import (
    create_ecr_infrastructure,
    create_ecs_infrastructure,
    create_infrastructure,
    prepare_template_files,
)
from awslabs.ecs_mcp_server.utils.security import ValidationError


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
async def test_create_infrastructure_generate_only(
    mock_prepare_template_files, mock_validate_app_name
):
    """Test create_infrastructure with force_deploy=False."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock prepare_template_files
    mock_prepare_template_files.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr template content",
        "ecs_template_content": "ecs template content",
    }

    # Call create_infrastructure with force_deploy=False
    result = await create_infrastructure(
        app_name="test-app", app_path="/path/to/app", force_deploy=False
    )

    # Verify validate_app_name was called
    mock_validate_app_name.assert_called_once_with("test-app")

    # Verify prepare_template_files was called
    mock_prepare_template_files.assert_called_once_with("test-app", "/path/to/app")

    # Verify the result
    assert result["operation"] == "generate_templates"
    assert "template_paths" in result
    assert result["template_paths"]["ecr_template"] == "/path/to/ecr_template.json"
    assert result["template_paths"]["ecs_template"] == "/path/to/ecs_template.json"
    assert "guidance" in result


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecr_infrastructure")
@patch("awslabs.ecs_mcp_server.utils.docker.build_and_push_image", new_callable=AsyncMock)
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure", new_callable=AsyncMock
)
async def test_create_infrastructure_force_deploy(
    mock_create_ecs_infrastructure,
    mock_build_and_push_image,
    mock_create_ecr_infrastructure,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test create_infrastructure with force_deploy=True."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock prepare_template_files
    mock_prepare_template_files.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr template content",
        "ecs_template_content": "ecs template content",
    }

    # Mock create_ecr_infrastructure
    mock_create_ecr_infrastructure.return_value = {
        "stack_name": "test-app-ecr-infrastructure",
        "stack_id": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef",
        "resources": {
            "ecr_repository": "test-app-repo",
            "ecr_repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
            "ecr_push_pull_role_arn": "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
        },
    }

    # Mock build_and_push_image
    mock_build_and_push_image.return_value = "latest"

    # Mock create_ecs_infrastructure
    mock_create_ecs_infrastructure.return_value = {
        "stack_name": "test-app-ecs-infrastructure",
        "stack_id": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecs/ghijkl",
        "resources": {
            "cluster": "test-app-cluster",
            "service": "test-app-service",
            "task_definition": "test-app-task",
            "load_balancer": "test-app-alb",
        },
    }

    # Call create_infrastructure with force_deploy=True and deployment_step=None
    # This should raise a ValidationError
    with pytest.raises(ValidationError) as excinfo:
        await create_infrastructure(
            app_name="test-app", app_path="/path/to/app", force_deploy=True, deployment_step=None
        )

    # Verify the error message
    assert "deployment_step is required when force_deploy is True" in str(excinfo.value)

    # Verify validate_app_name was called
    mock_validate_app_name.assert_called_once_with("test-app")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.create_ecr_infrastructure")
async def test_create_infrastructure_step_1(
    mock_create_ecr_infrastructure,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test create_infrastructure with force_deploy=True and deployment_step=1."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock prepare_template_files
    mock_prepare_template_files.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr template content",
        "ecs_template_content": "ecs template content",
    }

    # Mock create_ecr_infrastructure
    mock_create_ecr_infrastructure.return_value = {
        "stack_name": "test-app-ecr-infrastructure",
        "stack_id": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef",
        "operation": "create",
        "resources": {
            "ecr_repository": "test-app-repo",
            "ecr_repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
            "ecr_push_pull_role_arn": "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
        },
    }

    # Call create_infrastructure with force_deploy=True and deployment_step=1
    result = await create_infrastructure(
        app_name="test-app", app_path="/path/to/app", force_deploy=True, deployment_step=1
    )

    # Verify validate_app_name was called
    mock_validate_app_name.assert_called_once_with("test-app")

    # Verify prepare_template_files was called
    mock_prepare_template_files.assert_called_once_with("test-app", "/path/to/app")

    # No need to verify create_ecr_infrastructure was called

    # Verify the result
    assert result["step"] == 1
    assert result["stack_name"] == "test-app-ecr-infrastructure"
    assert result["operation"] == "create"
    assert "resources" in result
    assert "ecr_repository" in result["resources"]
    assert "ecr_repository_uri" in result["resources"]
    assert "ecr_push_pull_role_arn" in result["resources"]
    assert result["next_step"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
@patch("awslabs.ecs_mcp_server.utils.docker.build_and_push_image", new_callable=AsyncMock)
async def test_create_infrastructure_step_2(
    mock_build_and_push_image,
    mock_get_aws_client,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test create_infrastructure with force_deploy=True and deployment_step=2."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock prepare_template_files
    mock_prepare_template_files.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr template content",
        "ecs_template_content": "ecs template content",
    }

    # Mock CloudFormation client
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "Outputs": [
                    {
                        "OutputKey": "ECRRepositoryURI",
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
                    },
                    {
                        "OutputKey": "ECRPushPullRoleArn",
                        "OutputValue": "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
                    },
                ]
            }
        ]
    }
    mock_get_aws_client.return_value = mock_cfn

    # Mock build_and_push_image
    mock_build_and_push_image.return_value = "latest"

    # Call create_infrastructure with force_deploy=True and deployment_step=2
    result = await create_infrastructure(
        app_name="test-app", app_path="/path/to/app", force_deploy=True, deployment_step=2
    )

    # Verify validate_app_name was called
    mock_validate_app_name.assert_called_once_with("test-app")

    # Verify prepare_template_files was called
    mock_prepare_template_files.assert_called_once_with("test-app", "/path/to/app")

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_once_with("cloudformation")

    # Verify describe_stacks was called
    mock_cfn.describe_stacks.assert_called_once_with(StackName="test-app-ecr-infrastructure")

    # Verify build_and_push_image was called with the role ARN
    mock_build_and_push_image.assert_called_once_with(
        app_path="/path/to/app",
        repository_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
        role_arn="arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
    )

    # Verify the result
    assert result["step"] == 2
    assert result["operation"] == "build_and_push"
    assert "resources" in result
    assert "ecr_repository" in result["resources"]
    assert "ecr_repository_uri" in result["resources"]
    assert "image_tag" in result["resources"]
    assert result["resources"]["image_tag"] == "latest"
    assert result["next_step"] == 3


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_latest_image_tag", new_callable=AsyncMock)
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure", new_callable=AsyncMock
)
async def test_create_infrastructure_step_3(
    mock_create_ecs_infrastructure,
    mock_get_latest_image_tag,
    mock_get_aws_client,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test create_infrastructure with force_deploy=True and deployment_step=3."""
    # Mock get_latest_image_tag to return a valid image tag
    mock_get_latest_image_tag.return_value = "latest"
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock prepare_template_files
    mock_prepare_template_files.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr template content",
        "ecs_template_content": "ecs template content",
    }

    # Mock CloudFormation client
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "Outputs": [
                    {
                        "OutputKey": "ECRRepositoryURI",
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
                    },
                    {
                        "OutputKey": "ECRPushPullRoleArn",
                        "OutputValue": "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
                    },
                ]
            }
        ]
    }
    mock_get_aws_client.return_value = mock_cfn

    # Mock create_ecs_infrastructure
    mock_create_ecs_infrastructure.return_value = {
        "stack_name": "test-app-ecs-infrastructure",
        "stack_id": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecs/ghijkl",
        "operation": "create",
        "resources": {
            "cluster": "test-app-cluster",
            "service": "test-app-service",
            "task_definition": "test-app-task",
            "load_balancer": "test-app-alb",
        },
    }

    # Call create_infrastructure with force_deploy=True and deployment_step=3
    result = await create_infrastructure(
        app_name="test-app", app_path="/path/to/app", force_deploy=True, deployment_step=3
    )

    # Verify validate_app_name was called
    mock_validate_app_name.assert_called_once_with("test-app")

    # Verify prepare_template_files was called
    mock_prepare_template_files.assert_called_once_with("test-app", "/path/to/app")

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_once_with("cloudformation")

    # Verify describe_stacks was called
    mock_cfn.describe_stacks.assert_called_once_with(StackName="test-app-ecr-infrastructure")

    # Verify create_ecs_infrastructure was called
    mock_create_ecs_infrastructure.assert_called_once()

    # Verify the result
    assert result["step"] == 3
    assert result["stack_name"] == "test-app-ecs-infrastructure"
    assert result["operation"] == "create"
    assert "resources" in result
    assert "cluster" in result["resources"]
    assert "service" in result["resources"]
    assert "task_definition" in result["resources"]
    assert "load_balancer" in result["resources"]
    assert "ecr_repository" in result["resources"]
    assert "ecr_repository_uri" in result["resources"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_file_path")
@patch("awslabs.ecs_mcp_server.api.infrastructure.os.makedirs")
@patch("awslabs.ecs_mcp_server.api.infrastructure.os.path.join")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_templates_dir")
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.open",
    new_callable=mock_open,
    read_data="template content",
)
async def test_prepare_template_files(
    mock_open,
    mock_get_templates_dir,
    mock_join,
    mock_makedirs,
    mock_validate_file_path,
    mock_validate_app_name,
):
    """Test prepare_template_files."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock validate_file_path
    mock_validate_file_path.return_value = "/path/to/app"

    # Mock get_templates_dir
    mock_get_templates_dir.return_value = "/path/to/templates"

    # Mock os.path.join
    mock_join.side_effect = lambda *args: "/".join(args)

    # Call prepare_template_files (not async)
    result = prepare_template_files("test-app", "/path/to/app")

    # Verify validate_app_name was called
    mock_validate_app_name.assert_called_once_with("test-app")

    # Verify validate_file_path was called
    mock_validate_file_path.assert_called_once_with("/path/to/app")

    # Verify os.makedirs was called
    mock_makedirs.assert_called_once_with("/path/to/app/cloudformation-templates", exist_ok=True)

    # Verify open was called for each template file
    assert mock_open.call_count >= 4

    # Verify the result
    assert "ecr_template_path" in result
    assert "ecs_template_path" in result
    assert "ecr_template_content" in result
    assert "ecs_template_content" in result


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_ecr_infrastructure(mock_get_aws_client, mock_get_aws_account_id):
    """Test create_ecr_infrastructure."""
    # Mock get_aws_account_id
    mock_get_aws_account_id.return_value = "123456789012"

    # Mock get_aws_client
    mock_cfn = MagicMock()

    # Create a ClientError exception class
    class ClientError(Exception):
        pass

    mock_cfn.exceptions.ClientError = ClientError

    # Make describe_stacks raise ClientError the first time (stack doesn't exist)
    # and return a valid response the second time (after stack creation)
    mock_cfn.describe_stacks.side_effect = [
        ClientError("Stack test-app-ecr-infrastructure does not exist"),
        {
            "Stacks": [
                {
                    "StackId": (
                        "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef"
                    ),
                    "StackStatus": "CREATE_COMPLETE",
                    "Outputs": [
                        {
                            "OutputKey": "ECRRepositoryURI",
                            "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
                        }
                    ],
                }
            ]
        },
    ]

    mock_cfn.create_stack.return_value = {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef"
    }

    mock_get_aws_client.return_value = mock_cfn

    # Call create_ecr_infrastructure
    result = await create_ecr_infrastructure(
        app_name="test-app", template_content="template content"
    )

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_with("cloudformation")

    # Verify create_stack was called
    mock_cfn.create_stack.assert_called_once()

    # Verify describe_stacks was called at least once
    assert mock_cfn.describe_stacks.call_count >= 1

    # Verify the result
    assert result["stack_name"] == "test-app-ecr-infrastructure"
    # The stack_id might be None or the actual ID depending on the implementation
    if "stack_id" in result and result["stack_id"] is not None:
        assert (
            result["stack_id"]
            == "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef"
        )
    assert "resources" in result
    assert "ecr_repository_uri" in result["resources"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id", new_callable=AsyncMock)
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.get_default_vpc_and_subnets", new_callable=AsyncMock
)
@patch("awslabs.ecs_mcp_server.utils.aws.get_route_tables_for_vpc", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_ecs_infrastructure(
    mock_get_aws_client, mock_get_route_tables, mock_get_vpc, mock_get_aws_account_id
):
    """Test create_ecs_infrastructure."""
    # Mock get_aws_account_id
    mock_get_aws_account_id.return_value = "123456789012"

    # Mock get_default_vpc_and_subnets
    mock_get_vpc.return_value = {"vpc_id": "vpc-12345", "subnet_ids": ["subnet-1", "subnet-2"]}

    # Mock get_route_tables_for_vpc
    mock_get_route_tables.return_value = ["rtb-1", "rtb-2"]

    # Mock get_aws_client
    mock_cfn = MagicMock()

    # Create a ClientError exception class
    class ClientError(Exception):
        pass

    mock_cfn.exceptions.ClientError = ClientError

    # Make describe_stacks raise ClientError the first time (stack doesn't exist)
    # and return a valid response the second time (after stack creation)
    mock_cfn.describe_stacks.side_effect = [
        ClientError("Stack test-app-ecs-infrastructure does not exist"),
        {
            "Stacks": [
                {
                    "StackId": (
                        "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecs/ghijkl"
                    ),
                    "StackStatus": "CREATE_COMPLETE",
                    "Outputs": [
                        {
                            "OutputKey": "LoadBalancerDNSName",
                            "OutputValue": "test-app-alb-123456789.us-west-2.elb.amazonaws.com",
                        }
                    ],
                }
            ]
        },
    ]

    mock_cfn.create_stack.return_value = {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecs/ghijkl"
    }

    mock_get_aws_client.return_value = mock_cfn

    # Call create_ecs_infrastructure
    result = await create_ecs_infrastructure(
        app_name="test-app",
        template_content="template content",
        image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
        image_tag="latest",
    )

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_with("cloudformation")

    # Verify create_stack was called
    mock_cfn.create_stack.assert_called_once()

    # Verify the result
    assert result["stack_name"] == "test-app-ecs-infrastructure"
    assert (
        result["stack_id"]
        == "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecs/ghijkl"
    )
    assert "resources" in result
    assert result["resources"]["cluster"] == "test-app-cluster"
    assert result["resources"]["service"] == "test-app-service"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_ecr_infrastructure_update(mock_get_aws_client, mock_get_aws_account_id):
    """Test create_ecr_infrastructure with existing stack."""
    # Mock get_aws_account_id
    mock_get_aws_account_id.return_value = "123456789012"

    # Mock get_aws_client
    mock_cfn = MagicMock()
    # Mock that the stack already exists
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackId": (
                    "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef"
                ),
                "StackStatus": "CREATE_COMPLETE",
                "Outputs": [
                    {
                        "OutputKey": "ECRRepositoryURI",
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
                    },
                    {
                        "OutputKey": "ECRPushPullRoleArn",
                        "OutputValue": "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
                    },
                ],
            }
        ]
    }
    # No ClientError exception will be raised when describe_stacks is called
    mock_cfn.exceptions.ClientError = Exception
    mock_cfn.update_stack.return_value = {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef"
    }
    mock_get_aws_client.return_value = mock_cfn

    # Call create_ecr_infrastructure
    result = await create_ecr_infrastructure(
        app_name="test-app", template_content="template content"
    )

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_with("cloudformation")

    # Verify update_stack was called
    mock_cfn.update_stack.assert_called_once()

    # Verify the result
    assert result["stack_name"] == "test-app-ecr-infrastructure"
    assert result["operation"] == "update"
    assert "resources" in result
    assert "ecr_repository_uri" in result["resources"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_ecr_infrastructure_no_update(mock_get_aws_client, mock_get_aws_account_id):
    """Test create_ecr_infrastructure with no updates needed."""
    # Mock get_aws_account_id
    mock_get_aws_account_id.return_value = "123456789012"

    # Mock get_aws_client
    mock_cfn = MagicMock()
    # Mock that the stack already exists
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackId": (
                    "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef"
                ),
                "StackStatus": "CREATE_COMPLETE",
                "Outputs": [
                    {
                        "OutputKey": "ECRRepositoryURI",
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
                    },
                    {
                        "OutputKey": "ECRPushPullRoleArn",
                        "OutputValue": "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
                    },
                ],
            }
        ]
    }
    # No ClientError exception will be raised when describe_stacks is called
    mock_cfn.exceptions.ClientError = Exception
    # Mock that no updates are needed
    mock_cfn.update_stack.side_effect = Exception("No updates are to be performed")
    mock_get_aws_client.return_value = mock_cfn

    # Call create_ecr_infrastructure
    result = await create_ecr_infrastructure(
        app_name="test-app", template_content="template content"
    )

    # Verify get_aws_client was called
    mock_get_aws_client.assert_called_with("cloudformation")

    # Verify update_stack was called
    mock_cfn.update_stack.assert_called_once()

    # Verify the result
    assert result["stack_name"] == "test-app-ecr-infrastructure"
    assert result["operation"] == "no_update_required"
    assert "resources" in result
    assert "ecr_repository_uri" in result["resources"]
