"""
Unit tests for the status.py module that handles deployment status checks.
"""

import datetime
import unittest
from unittest import mock

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api import status


class TestDeploymentStatus(unittest.TestCase):
    """Unit tests for the status.py module."""

    @mock.patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
    @mock.patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_deployment_status_success(
        self, mock_get_aws_client, mock_get_alb_url, mock_find_cloudformation_stack
    ):
        """Test successful deployment status retrieval."""
        # Setup mock responses
        mock_find_cloudformation_stack.return_value = (
            "test-app-ecs-infrastructure",
            {"status": "CREATE_COMPLETE", "outputs": {}, "recent_events": []},
        )
        mock_get_alb_url.return_value = "http://test-app-123.us-west-2.elb.amazonaws.com"

        mock_ecs_client = mock.MagicMock()
        mock_ecs_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-app-service",
                    "status": "ACTIVE",
                    "deployments": [
                        {
                            "status": "PRIMARY",
                            "rolloutState": "COMPLETED",
                            "runningCount": 2,
                            "desiredCount": 2,
                        }
                    ],
                    "runningCount": 2,
                    "desiredCount": 2,
                    "pendingCount": 0,
                }
            ]
        }
        mock_ecs_client.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/test-cluster/abcdef"]
        }
        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/test-cluster/abcdef",
                    "lastStatus": "RUNNING",
                    "healthStatus": "HEALTHY",
                    "startedAt": datetime.datetime.now(),
                }
            ]
        }

        mock_get_aws_client.return_value = mock_ecs_client

        # Call the function
        result = await status.get_deployment_status("test-app")

        # Verify the result
        assert result["status"] == "COMPLETE"
        assert result["app_name"] == "test-app"
        assert result["alb_url"] == "http://test-app-123.us-west-2.elb.amazonaws.com"
        assert result["service_status"] == "ACTIVE"
        assert result["deployment_status"] == "COMPLETED"
        assert result["running_count"] == 2
        assert result["desired_count"] == 2
        assert "custom_domain_guidance" in result

        # Verify the function calls
        mock_find_cloudformation_stack.assert_called_once_with("test-app", None)
        mock_get_alb_url.assert_called_once_with("test-app", "test-app-ecs-infrastructure")
        mock_get_aws_client.assert_called_once_with("ecs")

    @mock.patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
    @mock.patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_deployment_status_stack_not_found(
        self, mock_get_aws_client, mock_get_alb_url, mock_find_cloudformation_stack
    ):
        """Test when CloudFormation stack is not found."""
        # Setup mock responses
        mock_find_cloudformation_stack.return_value = (
            None,
            {"status": "NOT_FOUND", "details": "No stack found with any naming pattern"},
        )

        # Call the function
        result = await status.get_deployment_status("test-app")

        # Verify the result
        assert result["status"] == "INFRASTRUCTURE_UNAVAILABLE"
        assert result["app_name"] == "test-app"
        assert result["alb_url"] is None

        # Verify the function calls
        mock_find_cloudformation_stack.assert_called_once_with("test-app", None)
        mock_get_alb_url.assert_not_called()
        mock_get_aws_client.assert_not_called()

    @mock.patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
    @mock.patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_deployment_status_service_not_found(
        self, mock_get_aws_client, mock_get_alb_url, mock_find_cloudformation_stack
    ):
        """Test when ECS service is not found."""
        # Setup mock responses
        mock_find_cloudformation_stack.return_value = (
            "test-app-ecs",
            {"status": "CREATE_COMPLETE", "outputs": {}, "recent_events": []},
        )
        mock_get_alb_url.return_value = "http://test-app-123.us-west-2.elb.amazonaws.com"

        mock_ecs_client = mock.MagicMock()
        mock_ecs_client.describe_services.return_value = {
            "services": [],
            "failures": [
                {
                    "arn": "arn:aws:ecs:us-west-2:123456789012:service/test-app/test-app-service",
                    "reason": "MISSING",
                }
            ],
        }
        mock_get_aws_client.return_value = mock_ecs_client

        # Call the function
        result = await status.get_deployment_status("test-app")

        # Verify the result
        assert result["status"] == "NOT_FOUND"
        assert result["app_name"] == "test-app"
        assert result["alb_url"] is None

        # Verify the function calls
        mock_find_cloudformation_stack.assert_called_once_with("test-app", None)
        mock_get_alb_url.assert_called_once_with("test-app", "test-app-ecs")
        mock_get_aws_client.assert_called_once_with("ecs")

    @mock.patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
    @mock.patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_deployment_status_with_custom_params(
        self, mock_get_aws_client, mock_get_alb_url, mock_find_cloudformation_stack
    ):
        """Test deployment status retrieval with custom parameters."""
        # Setup mock responses
        mock_find_cloudformation_stack.return_value = (
            "custom-stack",
            {"status": "CREATE_COMPLETE", "outputs": {}, "recent_events": []},
        )
        mock_get_alb_url.return_value = "http://custom-alb.us-west-2.elb.amazonaws.com"

        mock_ecs_client = mock.MagicMock()
        mock_ecs_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "custom-service",
                    "status": "ACTIVE",
                    "deployments": [
                        {
                            "status": "PRIMARY",
                            "rolloutState": "COMPLETED",
                            "runningCount": 1,
                            "desiredCount": 1,
                        }
                    ],
                    "runningCount": 1,
                    "desiredCount": 1,
                    "pendingCount": 0,
                }
            ]
        }
        mock_ecs_client.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/custom-cluster/abcdef"]
        }
        mock_ecs_client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/custom-cluster/abcdef",
                    "lastStatus": "RUNNING",
                    "healthStatus": "HEALTHY",
                    "startedAt": datetime.datetime.now(),
                }
            ]
        }

        mock_get_aws_client.return_value = mock_ecs_client

        # Call the function with custom parameters
        result = await status.get_deployment_status(
            "test-app",
            cluster_name="custom-cluster",
            stack_name="custom-stack",
            service_name="custom-service",
        )

        # Verify the result
        assert result["status"] == "COMPLETE"
        assert result["app_name"] == "test-app"
        assert result["cluster"] == "custom-cluster"
        assert result["alb_url"] == "http://custom-alb.us-west-2.elb.amazonaws.com"
        assert result["service_status"] == "ACTIVE"

        # Verify the function calls
        mock_find_cloudformation_stack.assert_called_once_with("test-app", "custom-stack")
        mock_get_alb_url.assert_called_once_with("test-app", "custom-stack")
        mock_get_aws_client.assert_called_once_with("ecs")
        mock_ecs_client.describe_services.assert_called_once_with(
            cluster="custom-cluster", services=["custom-service"]
        )

    @mock.patch("awslabs.ecs_mcp_server.api.status._find_cloudformation_stack")
    @mock.patch("awslabs.ecs_mcp_server.api.status._get_alb_url")
    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_deployment_status_exception_handling(
        self, mock_get_aws_client, mock_get_alb_url, mock_find_cloudformation_stack
    ):
        """Test exception handling in deployment status retrieval."""
        # Setup mock responses
        mock_find_cloudformation_stack.return_value = (
            "test-app-ecs",
            {"status": "CREATE_COMPLETE", "outputs": {}, "recent_events": []},
        )
        mock_get_alb_url.return_value = "http://test-app-123.us-west-2.elb.amazonaws.com"

        # Simulate an exception in describe_services
        mock_ecs_client = mock.MagicMock()
        mock_ecs_client.describe_services.side_effect = ClientError(
            {"Error": {"Code": "ClusterNotFoundException", "Message": "Cluster not found"}},
            "DescribeServices",
        )
        mock_get_aws_client.return_value = mock_ecs_client

        # Call the function
        result = await status.get_deployment_status("test-app")

        # Verify the result
        assert result["status"] == "ERROR"
        assert result["app_name"] == "test-app"
        assert result["alb_url"] == "http://test-app-123.us-west-2.elb.amazonaws.com"
        assert "ClusterNotFoundException" in result["message"]

        # Verify the function calls
        mock_find_cloudformation_stack.assert_called_once_with("test-app", None)
        mock_get_alb_url.assert_called_once_with("test-app", "test-app-ecs")
        mock_get_aws_client.assert_called_once_with("ecs")

    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_cfn_stack_status_success(self, mock_get_aws_client):
        """Test successful CloudFormation stack status retrieval."""
        # Setup mock response
        mock_cfn_client = mock.MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackName": "test-stack",
                    "StackStatus": "CREATE_COMPLETE",
                    "CreationTime": datetime.datetime.now(),
                    "LastUpdatedTime": datetime.datetime.now(),
                    "Outputs": [
                        {"OutputKey": "OutputKey1", "OutputValue": "OutputValue1"},
                        {"OutputKey": "OutputKey2", "OutputValue": "OutputValue2"},
                    ],
                }
            ]
        }
        mock_cfn_client.describe_stack_events.return_value = {
            "StackEvents": [
                {
                    "StackId": (
                        "arn:aws:cloudformation:us-west-2:123456789012:stack/test-stack/abcdef"
                    ),
                    "EventId": "event1",
                    "StackName": "test-stack",
                    "LogicalResourceId": "resource1",
                    "ResourceType": "AWS::ECS::Service",
                    "Timestamp": datetime.datetime.now(),
                    "ResourceStatus": "CREATE_COMPLETE",
                    "ResourceStatusReason": "Resource creation complete",
                },
                {
                    "StackId": (
                        "arn:aws:cloudformation:us-west-2:123456789012:stack/test-stack/abcdef"
                    ),
                    "EventId": "event2",
                    "StackName": "test-stack",
                    "LogicalResourceId": "resource2",
                    "ResourceType": "AWS::EC2::SecurityGroup",
                    "Timestamp": datetime.datetime.now() - datetime.timedelta(minutes=1),
                    "ResourceStatus": "CREATE_COMPLETE",
                },
            ]
        }

        mock_get_aws_client.return_value = mock_cfn_client

        # Call the function
        result = await status._get_cfn_stack_status("test-stack")

        # Verify the result
        assert result["status"] == "CREATE_COMPLETE"
        assert "creation_time" in result
        assert "last_updated_time" in result
        assert len(result["outputs"]) == 2
        assert result["outputs"]["OutputKey1"] == "OutputValue1"
        assert len(result["recent_events"]) == 2
        assert result["recent_events"][0]["resource_type"] == "AWS::ECS::Service"
        assert result["recent_events"][0]["status"] == "CREATE_COMPLETE"
        assert result["recent_events"][0]["reason"] == "Resource creation complete"

        # Verify the function calls
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cfn_client.describe_stacks.assert_called_once_with(StackName="test-stack")
        mock_cfn_client.describe_stack_events.assert_called_once_with(StackName="test-stack")

    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_cfn_stack_status_not_found(self, mock_get_aws_client):
        """Test CloudFormation stack status retrieval when stack is not found."""
        # Setup mock response
        mock_cfn_client = mock.MagicMock()
        mock_cfn_client.describe_stacks.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ValidationError",
                    "Message": "Stack with id test-stack does not exist",
                }
            },
            "DescribeStacks",
        )

        mock_get_aws_client.return_value = mock_cfn_client

        # Call the function
        result = await status._get_cfn_stack_status("test-stack")

        # Verify the result
        assert result["status"] == "NOT_FOUND"
        assert "details" in result
        assert "test-stack not found" in result["details"]

        # Verify the function calls
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cfn_client.describe_stacks.assert_called_once_with(StackName="test-stack")

    @mock.patch("awslabs.ecs_mcp_server.api.status._get_cfn_stack_status")
    async def test_find_cloudformation_stack_with_explicit_stack_name(
        self, mock_get_cfn_stack_status
    ):
        """Test finding a CloudFormation stack with an explicitly provided name."""
        # Setup mock response
        mock_get_cfn_stack_status.return_value = {
            "status": "CREATE_COMPLETE",
            "outputs": {},
            "recent_events": [],
        }

        # Call the function with explicit stack name
        stack_name, stack_status = await status._find_cloudformation_stack(
            "test-app", "explicit-stack"
        )

        # Verify the result
        assert stack_name == "explicit-stack"
        assert stack_status["status"] == "CREATE_COMPLETE"

        # Verify the function calls
        mock_get_cfn_stack_status.assert_called_once_with("explicit-stack")

    @mock.patch("awslabs.ecs_mcp_server.api.status._get_cfn_stack_status")
    async def test_find_cloudformation_stack_with_patterns(self, mock_get_cfn_stack_status):
        """Test finding a CloudFormation stack using patterns."""
        # Setup mock responses for different stack name patterns
        mock_get_cfn_stack_status.side_effect = [
            {
                "status": "NOT_FOUND",
                "details": "Stack test-app-ecs-infrastructure not found",
            },  # First pattern fails
            {
                "status": "CREATE_COMPLETE",
                "outputs": {},
                "recent_events": [],
            },  # Second pattern succeeds
        ]

        # Call the function without explicit stack name
        stack_name, stack_status = await status._find_cloudformation_stack("test-app")

        # Verify the result
        assert stack_name == "test-app-ecs"  # Should find the second pattern
        assert stack_status["status"] == "CREATE_COMPLETE"

        # Verify the function calls
        assert mock_get_cfn_stack_status.call_count == 2
        mock_get_cfn_stack_status.assert_has_calls(
            [mock.call("test-app-ecs-infrastructure"), mock.call("test-app-ecs")]
        )

    @mock.patch("awslabs.ecs_mcp_server.api.status._get_cfn_stack_status")
    async def test_find_cloudformation_stack_not_found(self, mock_get_cfn_stack_status):
        """Test when no CloudFormation stack is found."""
        # Setup mock responses for all patterns to fail
        mock_get_cfn_stack_status.side_effect = [
            {"status": "NOT_FOUND", "details": "Stack test-app-ecs-infrastructure not found"},
            {"status": "NOT_FOUND", "details": "Stack test-app-ecs not found"},
        ]

        # Call the function
        stack_name, stack_status = await status._find_cloudformation_stack("test-app")

        # Verify the result
        assert stack_name is None
        assert stack_status["status"] == "NOT_FOUND"
        assert "No stack found with any naming pattern" in stack_status["details"]

        # Verify the function calls
        assert mock_get_cfn_stack_status.call_count == 2
        mock_get_cfn_stack_status.assert_has_calls(
            [mock.call("test-app-ecs-infrastructure"), mock.call("test-app-ecs")]
        )

    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_alb_url_with_known_stack(self, mock_get_aws_client):
        """Test ALB URL retrieval with a known stack name."""
        # Setup mock response
        mock_cfn_client = mock.MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Outputs": [
                        {
                            "OutputKey": "LoadBalancerDNS",
                            "OutputValue": "test-alb-123.us-west-2.elb.amazonaws.com",
                        }
                    ]
                }
            ]
        }
        mock_get_aws_client.return_value = mock_cfn_client

        # Call the function with known stack name
        result = await status._get_alb_url("test-app", "known-stack")

        # Verify the result
        assert result == "http://test-alb-123.us-west-2.elb.amazonaws.com"

        # Verify the function calls
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cfn_client.describe_stacks.assert_called_once_with(StackName="known-stack")

    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_alb_url_with_http_prefix(self, mock_get_aws_client):
        """Test ALB URL retrieval when URL already has http:// prefix."""
        # Setup mock response
        mock_cfn_client = mock.MagicMock()
        mock_cfn_client.describe_stacks.return_value = {
            "Stacks": [
                {
                    "Outputs": [
                        {
                            "OutputKey": "LoadBalancerUrl",
                            "OutputValue": "http://test-alb-123.us-west-2.elb.amazonaws.com",
                        }
                    ]
                }
            ]
        }
        mock_get_aws_client.return_value = mock_cfn_client

        # Call the function
        result = await status._get_alb_url("test-app", "test-stack")

        # Verify the result - should not add another http:// prefix
        assert result == "http://test-alb-123.us-west-2.elb.amazonaws.com"

        # Verify the function calls
        mock_get_aws_client.assert_called_once_with("cloudformation")
        mock_cfn_client.describe_stacks.assert_called_once_with(StackName="test-stack")

    @mock.patch("awslabs.ecs_mcp_server.api.status.get_aws_client")
    async def test_get_alb_url_not_found(self, mock_get_aws_client):
        """Test ALB URL retrieval when no ALB URL is found in any stack."""
        # Setup mock responses for different stack name patterns
        mock_cfn_client = mock.MagicMock()
        mock_cfn_client.describe_stacks.side_effect = [
            # First stack doesn't have LoadBalancer outputs
            {"Stacks": [{"Outputs": [{"OutputKey": "OtherOutput", "OutputValue": "value"}]}]},
            # Second stack call raises an exception
            ClientError(
                {
                    "Error": {
                        "Code": "ValidationError",
                        "Message": "Stack with id test-app-ecs does not exist",
                    }
                },
                "DescribeStacks",
            ),
        ]
        mock_get_aws_client.return_value = mock_cfn_client

        # Call the function without known stack name
        result = await status._get_alb_url("test-app")

        # Verify the result
        assert result is None

        # Verify the function calls
        mock_get_aws_client.assert_called_once_with("cloudformation")
        assert mock_cfn_client.describe_stacks.call_count == 2
        mock_cfn_client.describe_stacks.assert_has_calls(
            [
                mock.call(StackName="test-app-ecs-infrastructure"),
                mock.call(StackName="test-app-ecs"),
            ]
        )

    def test_get_stack_names_to_try(self):
        """Test stack name generation function."""
        # Test with no provided stack name
        stack_names = status._get_stack_names_to_try("test-app")
        assert len(stack_names) == 2
        assert "test-app-ecs-infrastructure" == stack_names[0]
        assert "test-app-ecs" == stack_names[1]

        # Test with provided stack name
        stack_names = status._get_stack_names_to_try("test-app", "custom-stack")
        assert len(stack_names) == 3
        assert "custom-stack" == stack_names[0]
        assert "test-app-ecs-infrastructure" == stack_names[1]
        assert "test-app-ecs" == stack_names[2]

        # Test duplicate avoidance (if provided stack name matches a pattern)
        stack_names = status._get_stack_names_to_try("test-app", "test-app-ecs")
        assert len(stack_names) == 2
        assert "test-app-ecs" == stack_names[0]
        assert "test-app-ecs-infrastructure" == stack_names[1]

    def test_generate_custom_domain_guidance(self):
        """Test custom domain guidance generation."""
        # Call the function
        result = status._generate_custom_domain_guidance(
            "test-app", "http://test-alb-123.us-west-2.elb.amazonaws.com"
        )

        # Verify the result contains all required sections
        assert "custom_domain" in result
        assert "https_setup" in result
        assert "cloudformation_update" in result
        assert "next_steps" in result

        # Verify the custom domain section
        custom_domain = result["custom_domain"]
        assert "title" in custom_domain
        assert "description" in custom_domain
        assert "steps" in custom_domain
        assert "route53_commands" in custom_domain
        assert len(custom_domain["steps"]) >= 3

        # Verify the HTTPS setup section
        https_setup = result["https_setup"]
        assert "title" in https_setup
        assert "description" in https_setup
        assert "steps" in https_setup
        assert "acm_commands" in https_setup
        assert len(https_setup["steps"]) >= 3

        # Verify the CloudFormation update section
        cf_update = result["cloudformation_update"]
        assert "title" in cf_update
        assert "description" in cf_update
        assert "steps" in cf_update
        assert "commands" in cf_update

        # Verify the ALB hostname is correctly extracted
        alb_hostname = "test-alb-123.us-west-2.elb.amazonaws.com"
        route53_commands = "\n".join(custom_domain["route53_commands"])
        assert alb_hostname in route53_commands
        assert "test-app" in route53_commands


if __name__ == "__main__":
    unittest.main()
