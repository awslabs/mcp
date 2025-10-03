"""
Unit tests for Blue/Green deployment functionality in infrastructure.
"""

import inspect
import json
import os
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic.fields import FieldInfo

from awslabs.ecs_mcp_server.api.infrastructure import (
    create_ecs_infrastructure,
    create_infrastructure,
)
from awslabs.ecs_mcp_server.modules.infrastructure import register_module
from awslabs.ecs_mcp_server.utils.templates import get_templates_dir


@pytest.fixture
def aws_env():
    """AWS environment test data."""
    return {
        "account_id": "123456789012",
        "vpc_info": {"vpc_id": "vpc-12345", "subnet_ids": ["subnet-1", "subnet-2"]},
        "route_tables": ["rtb-1", "rtb-2"],
        "ecr_outputs": [
            {
                "OutputKey": "ECRRepositoryURI",
                "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app-repo",
            },
            {
                "OutputKey": "ECRPushPullRoleArn",
                "OutputValue": "arn:aws:iam::123456789012:role/test-app-ecr-pushpull-role",
            },
        ],
    }


def get_cfn_param(parameters: List[Dict], key: str) -> str:
    """Extract CloudFormation parameter value."""
    param = next((p for p in parameters if p["ParameterKey"] == key), None)
    return param["ParameterValue"] if param else None


@pytest.fixture
def ecs_mocks(aws_env):
    """Setup ECS infrastructure mocks."""
    with (
        patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_account_id") as mock_account,
        patch("awslabs.ecs_mcp_server.api.infrastructure.get_default_vpc_and_subnets") as mock_vpc,
        patch("awslabs.ecs_mcp_server.utils.aws.get_route_tables_for_vpc") as mock_routes,
        patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client") as mock_client,
    ):
        mock_account.return_value = aws_env["account_id"]
        mock_vpc.return_value = aws_env["vpc_info"]
        mock_routes.return_value = aws_env["route_tables"]

        mock_cfn = MagicMock()
        mock_cfn.exceptions.ClientError = Exception
        mock_cfn.describe_stacks.side_effect = [Exception("Stack does not exist")]
        mock_client.return_value = mock_cfn

        yield mock_cfn


def get_bg_template():
    """Load actual B/G CloudFormation template."""
    templates_dir = get_templates_dir()
    template_path = os.path.join(templates_dir, "ecs_infrastructure.json")

    with open(template_path, "r") as f:
        return json.load(f)


@pytest.mark.anyio
async def test_bake_time_default(ecs_mocks):
    """Test bake_time_minutes defaults to 5 minutes."""
    await create_ecs_infrastructure(
        app_name="test-app",
        template_content="{}",
        image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
        image_tag="latest",
    )

    ecs_mocks.create_stack.assert_called_once()
    parameters = ecs_mocks.create_stack.call_args[1]["Parameters"]
    assert get_cfn_param(parameters, "BakeTimeMinutes") == "5"


@pytest.mark.anyio
async def test_bake_time_custom(ecs_mocks):
    """Test custom bake_time_minutes passes through correctly."""
    custom_bake_time = 15
    await create_ecs_infrastructure(
        app_name="test-app",
        template_content="{}",
        image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app",
        image_tag="latest",
        bake_time_minutes=custom_bake_time,
    )

    ecs_mocks.create_stack.assert_called_once()
    parameters = ecs_mocks.create_stack.call_args[1]["Parameters"]
    assert get_cfn_param(parameters, "BakeTimeMinutes") == str(custom_bake_time)


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_latest_image_tag", new_callable=AsyncMock)
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure", new_callable=AsyncMock
)
async def test_bake_time_propagation(
    mock_create_ecs, mock_get_tag, mock_client, mock_prepare, mock_validate
):
    """Test bake_time_minutes propagates through create_infrastructure."""
    mock_validate.return_value = True
    mock_prepare.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr content",
        "ecs_template_content": "ecs content",
    }

    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "Outputs": [
                    {
                        "OutputKey": "ECRRepositoryURI",
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo",
                    },
                    {
                        "OutputKey": "ECRPushPullRoleArn",
                        "OutputValue": "arn:aws:iam::123456789012:role/role",
                    },
                ]
            }
        ]
    }
    mock_client.return_value = mock_cfn
    mock_get_tag.return_value = "20230101"
    mock_create_ecs.return_value = {
        "stack_name": "test-app-ecs-infrastructure",
        "operation": "create",
    }

    custom_bake_time = 20
    await create_infrastructure(
        app_name="test-app",
        app_path="/path/to/app",
        force_deploy=True,
        deployment_step=3,
        bake_time_minutes=custom_bake_time,
    )

    mock_create_ecs.assert_called_once()
    assert mock_create_ecs.call_args[1]["bake_time_minutes"] == custom_bake_time


@pytest.mark.anyio
@patch("awslabs.ecs_mcp_server.api.infrastructure.validate_app_name")
@patch("awslabs.ecs_mcp_server.api.infrastructure.prepare_template_files")
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_aws_client", new_callable=AsyncMock)
@patch("awslabs.ecs_mcp_server.api.infrastructure.get_latest_image_tag", new_callable=AsyncMock)
@patch(
    "awslabs.ecs_mcp_server.api.infrastructure.create_ecs_infrastructure", new_callable=AsyncMock
)
async def test_no_bake_time_provided(
    mock_create_ecs, mock_get_tag, mock_client, mock_prepare, mock_validate
):
    """Test create_infrastructure when no bake_time_minutes provided."""
    mock_validate.return_value = True
    mock_prepare.return_value = {
        "ecr_template_path": "/path/to/ecr_template.json",
        "ecs_template_path": "/path/to/ecs_template.json",
        "ecr_template_content": "ecr content",
        "ecs_template_content": "ecs content",
    }

    mock_cfn = MagicMock()
    mock_cfn.describe_stacks.return_value = {
        "Stacks": [
            {
                "Outputs": [
                    {
                        "OutputKey": "ECRRepositoryURI",
                        "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo",
                    },
                    {
                        "OutputKey": "ECRPushPullRoleArn",
                        "OutputValue": "arn:aws:iam::123456789012:role/role",
                    },
                ]
            }
        ]
    }
    mock_client.return_value = mock_cfn
    mock_get_tag.return_value = "20230101"
    mock_create_ecs.return_value = {
        "stack_name": "test-app-ecs-infrastructure",
        "operation": "create",
    }

    await create_infrastructure(
        app_name="test-app",
        app_path="/path/to/app",
        force_deploy=True,
        deployment_step=3,
    )

    mock_create_ecs.assert_called_once()
    assert mock_create_ecs.call_args[1]["bake_time_minutes"] is None


@pytest.mark.anyio
async def test_mcp_tool_bake_time_parameter():
    """Test MCP tool passes bake_time_minutes parameter correctly."""
    with patch(
        "awslabs.ecs_mcp_server.modules.infrastructure.create_infrastructure",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = {"operation": "generate_templates"}

        mock_mcp = MagicMock()
        registered_func = None

        def capture_tool(name=None):
            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_mcp.tool = capture_tool
        mock_mcp.prompt = MagicMock()

        register_module(mock_mcp)
        assert registered_func is not None

        custom_bake_time = 12
        result = await registered_func(
            app_name="test-app",
            app_path="/path/to/app",
            force_deploy=False,
            bake_time_minutes=custom_bake_time,
        )

        assert result["operation"] == "generate_templates"
        mock_create.assert_called_once()
        assert mock_create.call_args[1]["bake_time_minutes"] == custom_bake_time


@pytest.mark.anyio
async def test_mcp_tool_optional_bake_time():
    """Test MCP tool accepts optional bake_time_minutes parameter."""
    mock_mcp = MagicMock()
    registered_func = None

    def capture_tool(name=None):
        def decorator(func):
            nonlocal registered_func
            registered_func = func
            return func

        return decorator

    mock_mcp.tool = capture_tool
    mock_mcp.prompt = MagicMock()

    register_module(mock_mcp)

    sig = inspect.signature(registered_func)
    bake_param = sig.parameters.get("bake_time_minutes")

    assert bake_param is not None
    assert isinstance(bake_param.default, FieldInfo)
    assert bake_param.default.default is None


@pytest.mark.anyio
async def test_bg_template_components():
    """Test CloudFormation template contains all B/G components."""
    template = get_bg_template()
    resources = template["Resources"]

    # Verify dual target groups
    assert "ALBTargetGroup" in resources
    assert "ALBAltTargetGroup" in resources
    assert resources["ALBTargetGroup"]["Type"] == "AWS::ElasticLoadBalancingV2::TargetGroup"
    assert resources["ALBAltTargetGroup"]["Type"] == "AWS::ElasticLoadBalancingV2::TargetGroup"

    # Verify listener rules
    assert "ALBListenerAltRule" in resources
    assert "ALBListenerProdRule" in resources
    assert resources["ALBListenerAltRule"]["Type"] == "AWS::ElasticLoadBalancingV2::ListenerRule"
    assert resources["ALBListenerProdRule"]["Type"] == "AWS::ElasticLoadBalancingV2::ListenerRule"

    # Verify ECS Infrastructure Role
    assert "ECSInfrastructureRoleForLoadBalancers" in resources
    assert resources["ECSInfrastructureRoleForLoadBalancers"]["Type"] == "AWS::IAM::Role"

    # Verify ECS Service B/G configuration
    ecs_service = resources["ECSService"]
    deployment_config = ecs_service["Properties"]["DeploymentConfiguration"]
    assert deployment_config["Strategy"] == "BLUE_GREEN"
    assert "BakeTimeInMinutes" in deployment_config
    assert "DeploymentCircuitBreaker" in deployment_config

    # Verify advanced load balancer configuration
    lb_config = ecs_service["Properties"]["LoadBalancers"][0]["AdvancedConfiguration"]
    assert "AlternateTargetGroupArn" in lb_config
    assert "ProductionListenerRule" in lb_config
    assert "TestListenerRule" in lb_config


@pytest.mark.anyio
async def test_bg_listener_rules():
    """Test B/G listener rules configuration."""
    template = get_bg_template()
    resources = template["Resources"]

    # Test listener rules
    alt_rule = resources["ALBListenerAltRule"]
    prod_rule = resources["ALBListenerProdRule"]

    assert alt_rule["Properties"]["Priority"] == 2
    assert alt_rule["Properties"]["Actions"][0]["TargetGroupArn"]["Ref"] == "ALBAltTargetGroup"

    assert prod_rule["Properties"]["Priority"] == 1
    assert prod_rule["Properties"]["Actions"][0]["TargetGroupArn"]["Ref"] == "ALBTargetGroup"


@pytest.mark.anyio
async def test_deployment_controller_configuration():
    """Test ECS Service has DeploymentController set to ECS."""
    template = get_bg_template()
    ecs_service = template["Resources"]["ECSService"]

    assert "DeploymentController" in ecs_service["Properties"]
    assert ecs_service["Properties"]["DeploymentController"]["Type"] == "ECS"


@pytest.mark.anyio
async def test_iam_policy_arn_correctness():
    """Test ECS Infrastructure Role uses correct IAM policy ARN."""
    template = get_bg_template()
    resources = template["Resources"]

    # Get the ECS Infrastructure Role
    infrastructure_role = resources["ECSInfrastructureRoleForLoadBalancers"]
    managed_policies = infrastructure_role["Properties"]["ManagedPolicyArns"]

    # Verify correct IAM policy ARN (without /service-role/ path)
    expected_arn = "arn:aws:iam::aws:policy/AmazonECSInfrastructureRolePolicyForLoadBalancers"
    assert expected_arn in managed_policies

    # Verify incorrect ARN is not present
    incorrect_arn = (
        "arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRolePolicyForLoadBalancers"
    )
    assert incorrect_arn not in managed_policies


@pytest.mark.anyio
async def test_no_conflicting_role_property():
    """Test ECS Service does not have conflicting top-level Role property."""
    template = get_bg_template()
    ecs_service = template["Resources"]["ECSService"]

    # Verify no top-level Role property exists (conflicts with B/G AdvancedConfiguration.RoleArn)
    assert "Role" not in ecs_service["Properties"]

    # Verify RoleArn is properly configured in AdvancedConfiguration
    lb_config = ecs_service["Properties"]["LoadBalancers"][0]["AdvancedConfiguration"]
    assert "RoleArn" in lb_config
    assert "Fn::GetAtt" in lb_config["RoleArn"]
    assert lb_config["RoleArn"]["Fn::GetAtt"][0] == "ECSInfrastructureRoleForLoadBalancers"


@pytest.mark.anyio
async def test_bake_time_property_correctness():
    """Test DeploymentConfiguration uses correct BakeTimeInMinutes property for native ECS B/G."""
    template = get_bg_template()
    ecs_service = template["Resources"]["ECSService"]
    deployment_config = ecs_service["Properties"]["DeploymentConfiguration"]

    # Verify correct property name for native ECS B/G
    assert "BakeTimeInMinutes" in deployment_config
    assert deployment_config["BakeTimeInMinutes"]["Ref"] == "BakeTimeMinutes"

    # Verify incorrect property name is not present
    assert "BakeTimeMinutes" not in deployment_config


@pytest.mark.anyio
async def test_bg_parameter_definition():
    """Test CloudFormation parameter for BakeTimeMinutes is properly defined."""
    template = get_bg_template()
    parameters = template["Parameters"]

    # Verify BakeTimeMinutes parameter exists
    assert "BakeTimeMinutes" in parameters
    param = parameters["BakeTimeMinutes"]

    # Verify parameter properties
    assert param["Type"] == "Number"
    assert param["Default"] == 5
    assert "Description" in param
    # Check description indicates B/G deployment context
    desc_lower = param["Description"].lower()
    assert "green deployment" in desc_lower or "blue/green" in desc_lower or "bake" in desc_lower


@pytest.mark.anyio
async def test_advanced_configuration_completeness():
    """Test LoadBalancer AdvancedConfiguration has all required B/G properties."""
    template = get_bg_template()
    ecs_service = template["Resources"]["ECSService"]
    lb_config = ecs_service["Properties"]["LoadBalancers"][0]["AdvancedConfiguration"]

    # Verify all required B/G properties are present
    required_properties = [
        "AlternateTargetGroupArn",
        "ProductionListenerRule",
        "TestListenerRule",
        "RoleArn",
    ]

    for prop in required_properties:
        assert prop in lb_config, f"Missing required property: {prop}"

    # Verify references are correct
    assert lb_config["AlternateTargetGroupArn"]["Ref"] == "ALBAltTargetGroup"
    assert lb_config["ProductionListenerRule"]["Ref"] == "ALBListenerProdRule"
    assert lb_config["TestListenerRule"]["Ref"] == "ALBListenerAltRule"
