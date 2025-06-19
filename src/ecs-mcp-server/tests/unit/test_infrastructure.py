"""
Unit tests for infrastructure module.
"""

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from awslabs.ecs_mcp_server.api.infrastructure import (
    create_ecr_infrastructure,
    create_ecs_infrastructure,
    create_infrastructure,
    get_latest_image_tag,
    prepare_template_files,
)
from awslabs.ecs_mcp_server.utils.security import ValidationError

# ----------------------------------------------------------------------------
# Template File Preparation Tests
# ----------------------------------------------------------------------------


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
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_file_path")
async def test_prepare_template_files_path_not_exists(
    mock_validate_file_path, mock_validate_app_name
):
    """Test prepare_template_files when app_path doesn't exist."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock validate_file_path to raise ValidationError
    mock_validate_file_path.side_effect = ValidationError("Path /non/existent/path does not exist")

    # Use patch to mock os.makedirs and other file operations
    with (
        patch("awslabs.ecs_mcp_server.api.infrastructure.os.makedirs") as mock_makedirs,
        patch("awslabs.ecs_mcp_server.api.infrastructure.os.path.join") as mock_join,
        patch(
            "awslabs.ecs_mcp_server.api.infrastructure.get_templates_dir"
        ) as mock_get_templates_dir,
        patch("builtins.open"),
        patch("awslabs.ecs_mcp_server.api.infrastructure.validate_cloudformation_template"),
    ):
        # Set up mocks for successful path creation
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_get_templates_dir.return_value = "/path/to/templates"

        # Call prepare_template_files
        result = prepare_template_files(app_name="test-app", app_path="/non/existent/path")

        # Verify makedirs was called to create the directory
        mock_makedirs.assert_called_with(
            "/non/existent/path/cloudformation-templates", exist_ok=True
        )

        # Verify the result contains the expected keys
        assert "ecr_template_path" in result
        assert "ecs_template_path" in result
        assert "ecr_template_content" in result
        assert "ecs_template_content" in result


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_file_path")
async def test_prepare_template_files_io_error(mock_validate_file_path, mock_validate_app_name):
    """Test prepare_template_files handling IO errors."""
    # Mock validate_app_name and validate_file_path
    mock_validate_app_name.return_value = True
    mock_validate_file_path.return_value = True

    # Use patch to mock file operations with an IO error
    with (
        patch("awslabs.ecs_mcp_server.api.infrastructure.os.makedirs"),
        patch("awslabs.ecs_mcp_server.api.infrastructure.os.path.join") as mock_join,
        patch(
            "awslabs.ecs_mcp_server.api.infrastructure.get_templates_dir"
        ) as mock_get_templates_dir,
        patch("builtins.open") as mock_open,
    ):
        # Set up mocks
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_get_templates_dir.return_value = "/path/to/templates"
        # Make open raise IOError when reading the source template
        mock_open.side_effect = [IOError("File not found")]

        # Call prepare_template_files - should raise the IOError
        with pytest.raises(IOError) as excinfo:
            prepare_template_files(app_name="test-app", app_path="/path/to/app")

        # Verify the error message
        assert "File not found" in str(excinfo.value)


# ----------------------------------------------------------------------------
# Image Tag Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client_with_role", new_callable=AsyncMock)
async def test_get_latest_image_tag(mock_get_aws_client_with_role):
    """Test get_latest_image_tag with valid response."""
    # Mock ECR client
    mock_ecr = MagicMock()
    mock_ecr.list_images.return_value = {
        "imageIds": [
            {"imageDigest": "sha256:1234", "imageTag": "20230101"},
            {"imageDigest": "sha256:5678", "imageTag": "20230102"},
        ]
    }
    mock_get_aws_client_with_role.return_value = mock_ecr

    # Call get_latest_image_tag
    result = await get_latest_image_tag(
        app_name="test-app", role_arn="arn:aws:iam::123456789012:role/test-role"
    )

    # Verify the result is the latest tag
    assert result == "20230102"

    # Verify get_aws_client_with_role was called with the correct role
    mock_get_aws_client_with_role.assert_called_once_with(
        "ecr", "arn:aws:iam::123456789012:role/test-role"
    )
    # Verify list_images was called with the correct repository name
    mock_ecr.list_images.assert_called_once_with(repositoryName="test-app-repo")


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client_with_role", new_callable=AsyncMock)
async def test_get_latest_image_tag_no_images_error(mock_get_aws_client_with_role):
    """Test get_latest_image_tag with no images in repository."""
    # Mock ECR client with no images
    mock_ecr = MagicMock()
    mock_ecr.list_images.return_value = {"imageIds": []}
    mock_get_aws_client_with_role.return_value = mock_ecr

    # Call get_latest_image_tag - should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        await get_latest_image_tag(
            app_name="test-app", role_arn="arn:aws:iam::123456789012:role/test-role"
        )

    # Verify the error message
    assert "No images found in repository" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client_with_role", new_callable=AsyncMock)
async def test_get_latest_image_tag_no_tagged_images(mock_get_aws_client_with_role):
    """Test get_latest_image_tag with images that don't have tags."""
    # Mock ECR client with images that don't have tags
    mock_ecr = MagicMock()
    mock_ecr.list_images.return_value = {
        "imageIds": [
            {"imageDigest": "sha256:1234"},
            {"imageDigest": "sha256:5678"},
        ]
    }
    mock_get_aws_client_with_role.return_value = mock_ecr

    # Call get_latest_image_tag - should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        await get_latest_image_tag(
            app_name="test-app", role_arn="arn:aws:iam::123456789012:role/test-role"
        )

    # Verify the error message
    assert "No tagged images found in repository" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client_with_role", new_callable=AsyncMock)
async def test_get_latest_image_tag_non_numeric_tags(mock_get_aws_client_with_role):
    """Test get_latest_image_tag with non-numeric tags."""
    # Mock ECR client with non-numeric tags
    mock_ecr = MagicMock()
    mock_ecr.list_images.return_value = {
        "imageIds": [
            {"imageDigest": "sha256:1234", "imageTag": "latest"},
            {"imageDigest": "sha256:5678", "imageTag": "stable"},
        ]
    }
    mock_get_aws_client_with_role.return_value = mock_ecr

    # Call get_latest_image_tag - should return the first tag since they can't be sorted numerically
    result = await get_latest_image_tag(
        app_name="test-app", role_arn="arn:aws:iam::123456789012:role/test-role"
    )

    # Verify the result is the first tag
    assert result == "latest"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client_with_role", new_callable=AsyncMock)
async def test_get_latest_image_tag_client_error(mock_get_aws_client_with_role):
    """Test get_latest_image_tag handling AWS client error."""
    # Mock ECR client raising an exception
    mock_ecr = MagicMock()
    mock_ecr.list_images.side_effect = Exception("AWS client error")
    mock_get_aws_client_with_role.return_value = mock_ecr

    # Call get_latest_image_tag - should raise the exception
    with pytest.raises(Exception) as excinfo:
        await get_latest_image_tag(
            app_name="test-app", role_arn="arn:aws:iam::123456789012:role/test-role"
        )

    # Verify the error message
    assert "AWS client error" in str(excinfo.value)


# ----------------------------------------------------------------------------
# ECR Infrastructure Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_ecr_infrastructure_new_stack(mock_get_aws_client, mock_get_account_id):
    """Test create_ecr_infrastructure creating a new stack."""
    # Set up mocks
    mock_get_account_id.return_value = "123456789012"

    mock_cfn = MagicMock()
    mock_cfn.exceptions.ClientError = Exception
    # First describe_stacks should raise to indicate stack doesn't exist
    mock_cfn.describe_stacks.side_effect = [
        Exception("Stack does not exist"),
        {
            "Stacks": [
                {
                    "Outputs": [
                        {
                            "OutputKey": "ECRRepositoryURI",
                            "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
                        },
                        {
                            "OutputKey": "ECRPushPullRoleArn",
                            "OutputValue": "\
                                arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
                        },
                    ]
                }
            ]
        },
    ]
    mock_get_aws_client.return_value = mock_cfn

    # Call the function
    result = await create_ecr_infrastructure(app_name="test-app", template_content="{}")

    # Verify create_stack was called
    mock_cfn.create_stack.assert_called_once()

    # Verify the result
    assert "stack_name" in result
    assert "resources" in result
    assert "ecr_repository_uri" in result["resources"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_ecr_infrastructure_existing_stack(mock_get_aws_client, mock_get_account_id):
    """Test create_ecr_infrastructure updating an existing stack."""
    # Set up mocks
    mock_get_account_id.return_value = "123456789012"

    mock_cfn = MagicMock()
    mock_cfn.exceptions.ClientError = Exception
    # Stack already exists
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackId": (
                    "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef"
                ),
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
    mock_get_aws_client.return_value = mock_cfn

    # Call the function
    result = await create_ecr_infrastructure(app_name="test-app", template_content="{}")

    # Verify update_stack was called
    mock_cfn.update_stack.assert_called_once()

    # Verify the result
    assert "stack_name" in result
    assert result["operation"] == "update"
    assert "resources" in result
    assert "ecr_repository_uri" in result["resources"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_ecr_infrastructure_no_updates(mock_get_aws_client, mock_get_account_id):
    """Test create_ecr_infrastructure with no updates needed."""
    # Set up mocks
    mock_get_account_id.return_value = "123456789012"

    mock_cfn = MagicMock()
    mock_cfn.exceptions.ClientError = Exception
    # Stack already exists
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackId": (
                    "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecr/abcdef"
                ),
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
    # update_stack raises "No updates are to be performed"
    mock_cfn.update_stack.side_effect = Exception("No updates are to be performed")
    mock_get_aws_client.return_value = mock_cfn

    # Call the function
    result = await create_ecr_infrastructure(app_name="test-app", template_content="{}")

    # Verify the result
    assert "stack_name" in result
    assert result["operation"] == "no_update_required"
    assert "resources" in result
    assert "ecr_repository_uri" in result["resources"]


# ----------------------------------------------------------------------------
# ECS Infrastructure Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_default_vpc_and_subnets")
@patch("awslabs.ecs_mcp_server.utils.aws.get_route_tables_for_vpc")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
async def test_create_ecs_infrastructure_new_stack(
    mock_get_aws_client, mock_get_route_tables, mock_get_vpc, mock_get_account_id
):
    """Test create_ecs_infrastructure creating a new stack."""
    # Set up mocks
    mock_get_account_id.return_value = "123456789012"
    mock_get_vpc.return_value = {"vpc_id": "vpc-12345", "subnet_ids": ["subnet-1", "subnet-2"]}
    mock_get_route_tables.return_value = ["rtb-1", "rtb-2"]

    mock_cfn = MagicMock()
    mock_cfn.exceptions.ClientError = Exception
    # First describe_stacks should raise to indicate stack doesn't exist
    mock_cfn.describe_stacks.side_effect = [
        Exception("Stack does not exist"),
        {
            "Stacks": [
                {
                    "Outputs": [
                        {
                            "OutputKey": "LoadBalancerDNSName",
                            "OutputValue": "test-app-alb-123456789.us-west-2.elb.amazonaws.com",
                        }
                    ]
                }
            ]
        },
    ]
    mock_get_aws_client.return_value = mock_cfn

    # Call the function
    result = await create_ecs_infrastructure(
        app_name="test-app",
        template_content="{}",
        image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
        image_tag="latest",
    )

    # Verify create_stack was called
    mock_cfn.create_stack.assert_called_once()

    # Verify the result
    assert "stack_name" in result
    assert "resources" in result
    assert "cluster" in result["resources"]
    assert "service" in result["resources"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
async def test_create_ecs_infrastructure_existing_stack(mock_get_aws_client, mock_get_account_id):
    """Test create_ecs_infrastructure updating an existing stack."""
    # Set up mocks
    mock_get_account_id.return_value = "123456789012"

    mock_cfn = MagicMock()
    mock_cfn.exceptions.ClientError = Exception
    # Stack already exists
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackId": (
                    "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecs/ghijkl"
                ),
                "Outputs": [
                    {
                        "OutputKey": "LoadBalancerDNSName",
                        "OutputValue": "test-app-alb-123456789.us-west-2.elb.amazonaws.com",
                    }
                ],
            }
        ]
    }
    mock_get_aws_client.return_value = mock_cfn

    # Use patch for get_default_vpc_and_subnets
    with (
        patch(
            "awslabs.ecs_mcp_server.api.infrastructure.get_default_vpc_and_subnets"
        ) as mock_get_vpc,
        patch("awslabs.ecs_mcp_server.utils.aws.get_route_tables_for_vpc") as mock_get_route_tables,
    ):
        mock_get_vpc.return_value = {"vpc_id": "vpc-12345", "subnet_ids": ["subnet-1", "subnet-2"]}
        mock_get_route_tables.return_value = ["rtb-1", "rtb-2"]

        # Call the function
        result = await create_ecs_infrastructure(
            app_name="test-app",
            template_content="{}",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
            image_tag="latest",
        )

        # Verify update_stack was called
        mock_cfn.update_stack.assert_called_once()

        # Verify the result
        assert "stack_name" in result
        assert result["operation"] == "update"
        assert "resources" in result
        assert "cluster" in result["resources"]
        assert "service" in result["resources"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client")
async def test_create_ecs_infrastructure_no_updates(mock_get_aws_client, mock_get_account_id):
    """Test create_ecs_infrastructure with no updates needed."""
    # Set up mocks
    mock_get_account_id.return_value = "123456789012"

    mock_cfn = MagicMock()
    mock_cfn.exceptions.ClientError = Exception
    # Stack already exists
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackId": (
                    "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecs/ghijkl"
                ),
                "Outputs": [
                    {
                        "OutputKey": "LoadBalancerDNSName",
                        "OutputValue": "test-app-alb-123456789.us-west-2.elb.amazonaws.com",
                    }
                ],
            }
        ]
    }
    # update_stack raises "No updates are to be performed"
    mock_cfn.update_stack.side_effect = Exception("No updates are to be performed")
    mock_get_aws_client.return_value = mock_cfn

    # Use patch for get_default_vpc_and_subnets
    with (
        patch(
            "awslabs.ecs_mcp_server.api.infrastructure.get_default_vpc_and_subnets"
        ) as mock_get_vpc,
        patch("awslabs.ecs_mcp_server.utils.aws.get_route_tables_for_vpc") as mock_get_route_tables,
    ):
        mock_get_vpc.return_value = {"vpc_id": "vpc-12345", "subnet_ids": ["subnet-1", "subnet-2"]}
        mock_get_route_tables.return_value = ["rtb-1", "rtb-2"]

        # Call the function
        result = await create_ecs_infrastructure(
            app_name="test-app",
            template_content="{}",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
            image_tag="latest",
        )

        # Verify the result
        assert "stack_name" in result
        assert result["operation"] == "no_update_required"
        assert "resources" in result
        assert "cluster" in result["resources"]
        assert "service" in result["resources"]


# ----------------------------------------------------------------------------
# Create Infrastructure Tests
# ----------------------------------------------------------------------------


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
async def test_create_infrastructure_no_force_deploy(
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
async def test_create_infrastructure_missing_deployment_step(mock_validate_app_name):
    """Test create_infrastructure with force_deploy=True but missing deployment_step."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Call create_infrastructure with force_deploy=True but no deployment_step
    with pytest.raises(ValidationError) as excinfo:
        await create_infrastructure(
            app_name="test-app", app_path="/path/to/app", force_deploy=True, deployment_step=None
        )

    # Verify the error message
    assert "deployment_step is required when force_deploy is True" in str(excinfo.value)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_cloudformation_template")
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.create_ecr_infrastructure", new_callable=AsyncMock
)
async def test_create_infrastructure_force_deploy_step1(
    mock_create_ecr,
    mock_validate_template,
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
    mock_create_ecr.return_value = {
        "operation": "create",
        "resources": {
            "ecr_repository": "test-app-repo",
            "ecr_repository_uri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
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

    # Verify create_ecr_infrastructure was called
    mock_create_ecr.assert_called_once_with(
        app_name="test-app", template_content="ecr template content"
    )

    # Verify the result
    assert result["step"] == 1
    assert result["stack_name"] == "test-app-ecr-infrastructure"
    assert result["operation"] == "create"
    assert "resources" in result
    assert result["resources"]["ecr_repository"] == "test-app-repo"
    assert result["next_step"] == 2


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_infrastructure_force_deploy_step2(
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
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
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
    with patch(
        "awslabs.ecs_mcp_server.utils.docker.build_and_push_image", new_callable=AsyncMock
    ) as mock_build_and_push:
        mock_build_and_push.return_value = "20230101"

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

        # Verify build_and_push_image was called
        mock_build_and_push.assert_called_once_with(
            app_path="/path/to/app",
            repository_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            role_arn="arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
        )

        # Verify the result
        assert result["step"] == 2
        assert result["operation"] == "build_and_push"
        assert "resources" in result
        assert result["resources"]["ecr_repository"] == "test-app-repo"
        assert result["resources"]["image_tag"] == "20230101"
        assert result["next_step"] == 3


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_infrastructure_step2_error_retrieving_ecr_info(
    mock_get_aws_client,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test with force_deploy=True and deployment_step=2 with error retrieving ECR info."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock prepare_template_files
    mock_prepare_template_files.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr template content",
        "ecs_template_content": "ecs template content",
    }

    # Mock CloudFormation client with error
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.side_effect = Exception("Stack does not exist")
    mock_get_aws_client.return_value = mock_cfn

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

    # Verify the result
    assert result["step"] == 2
    assert result["operation"] == "error"
    assert "message" in result
    assert "Failed to retrieve ECR infrastructure information" in result["message"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_infrastructure_step2_build_error(
    mock_get_aws_client,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test create_infrastructure with force_deploy=True and deployment_step=2 with build error."""
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
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
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

    # Mock build_and_push_image with error
    with patch(
        "awslabs.ecs_mcp_server.utils.docker.build_and_push_image", new_callable=AsyncMock
    ) as mock_build_and_push:
        mock_build_and_push.side_effect = Exception("Docker build failed")

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

        # Verify build_and_push_image was called
        mock_build_and_push.assert_called_once_with(
            app_path="/path/to/app",
            repository_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            role_arn="arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
        )

        # Verify the result
        assert result["step"] == 2
        assert result["operation"] == "error"
        assert "message" in result
        assert "Docker image build failed: Docker build failed" in result["message"]


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_latest_image_tag", new_callable=AsyncMock)
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure", new_callable=AsyncMock
)
async def test_create_infrastructure_force_deploy_step3(
    mock_create_ecs,
    mock_get_latest_image_tag,
    mock_get_aws_client,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test create_infrastructure with force_deploy=True and deployment_step=3."""
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
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
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

    # Mock get_latest_image_tag
    mock_get_latest_image_tag.return_value = "20230101"

    # Mock create_ecs_infrastructure
    mock_create_ecs.return_value = {
        "stack_name": "test-app-ecs-infrastructure",
        "stack_id": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app-ecs/abcdef",
        "operation": "create",
        "vpc_id": "vpc-12345",
        "subnet_ids": ["subnet-1", "subnet-2"],
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

    # Verify get_latest_image_tag was called
    mock_get_latest_image_tag.assert_called_once_with(
        "test-app", "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role"
    )

    # Verify create_ecs_infrastructure was called with the correct parameters
    # Note: The health_check_path parameter defaults to "/" in the implementation
    mock_create_ecs.assert_called_once()
    call_args = mock_create_ecs.call_args[1]
    assert call_args["app_name"] == "test-app"
    assert call_args["image_uri"] == "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo"
    assert call_args["image_tag"] == "20230101"
    assert call_args["template_content"] == "ecs template content"

    # Verify the result
    assert result["step"] == 3
    assert result["stack_name"] == "test-app-ecs-infrastructure"
    assert result["operation"] == "create"
    assert "resources" in result
    assert result["resources"]["cluster"] == "test-app-cluster"
    assert result["resources"]["ecr_repository"] == "test-app-repo"
    assert result["image_tag"] == "20230101"


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_latest_image_tag", new_callable=AsyncMock)
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure", new_callable=AsyncMock
)
async def test_create_infrastructure_step3_error(
    mock_create_ecs,
    mock_get_latest_image_tag,
    mock_get_aws_client,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test create_infrastructure with force_deploy=True and deployment_step=3 with error."""
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
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
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

    # Mock get_latest_image_tag
    mock_get_latest_image_tag.return_value = "20230101"

    # Mock create_ecs_infrastructure with error
    mock_create_ecs.side_effect = Exception("ECS infrastructure creation failed")

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

    # Verify get_latest_image_tag was called
    mock_get_latest_image_tag.assert_called_once_with(
        "test-app", "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role"
    )

    # Verify create_ecs_infrastructure was called
    mock_create_ecs.assert_called_once()

    # Verify the result
    assert result["step"] == 3
    assert result["operation"] == "error"
    assert "message" in result
    assert (
        "ECS infrastructure creation failed: ECS infrastructure creation failed"
        in result["message"]
    )


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
async def test_create_infrastructure_invalid_deployment_step(
    mock_get_aws_client,
    mock_prepare_template_files,
    mock_validate_app_name,
):
    """Test create_infrastructure with force_deploy=True and invalid deployment_step."""
    # Mock validate_app_name
    mock_validate_app_name.return_value = True

    # Mock prepare_template_files
    mock_prepare_template_files.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr template content",
        "ecs_template_content": "ecs template content",
    }

    # Mock CloudFormation client with error
    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.side_effect = Exception("Stack does not exist")
    mock_get_aws_client.return_value = mock_cfn

    # Call create_infrastructure with force_deploy=True and invalid deployment_step
    result = await create_infrastructure(
        app_name="test-app", app_path="/path/to/app", force_deploy=True, deployment_step=99
    )

    # Verify the result
    assert result["operation"] == "error"
    assert "message" in result
    assert "Failed to retrieve ECR infrastructure information" in result["message"]
