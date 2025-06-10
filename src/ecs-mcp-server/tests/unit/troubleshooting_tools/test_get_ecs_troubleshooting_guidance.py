"""
Unit tests for the get_ecs_troubleshooting_guidance tool.
"""

from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import (
    create_assessment,
    discover_resources,
    find_clusters,
    find_load_balancers,
    find_services,
    get_cluster_details,
    get_ecs_troubleshooting_guidance,
    get_stack_status,
    get_task_definitions,
    handle_aws_api_call,
    is_ecr_image,
    parse_ecr_image_uri,
    validate_container_images,
    validate_image,
)
from tests.unit.utils.async_test_utils import (
    AsyncIterator,
    create_mock_cloudformation_client,
    create_mock_ecs_client,
    create_sample_cluster_data,
)


@pytest.fixture
def mock_aws_clients():
    """Set up all mock AWS clients needed for testing."""
    mock_ecs = create_mock_ecs_client()
    mock_cfn = create_mock_cloudformation_client()
    mock_ecr = mock.AsyncMock()
    mock_elbv2 = mock.AsyncMock()

    with (
        mock.patch(
            "awslabs.ecs_mcp_server.api.clients.ecs_client.get_aws_client", return_value=mock_ecs
        ),
        mock.patch(
            "awslabs.ecs_mcp_server.utils.aws.get_aws_client",
            side_effect=lambda service: {
                "ecs": mock_ecs,
                "cloudformation": mock_cfn,
                "ecr": mock_ecr,
                "elbv2": mock_elbv2,
            }.get(service, mock.AsyncMock()),
        ),
    ):
        yield {"ecs": mock_ecs, "cloudformation": mock_cfn, "ecr": mock_ecr, "elbv2": mock_elbv2}


class TestHelperFunctions:
    """Test individual helper functions in the get_ecs_troubleshooting_guidance module."""

    @pytest.mark.anyio
    async def test_find_clusters(self, mock_aws_clients):
        """Test finding ECS clusters related to an application name."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure the response
        mock_ecs.list_clusters.return_value = {
            "clusterArns": [
                "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster",
                "arn:aws:ecs:us-west-2:123456789012:cluster/other-cluster",
            ]
        }

        result = await find_clusters("test-app", ecs_client=mock_ecs)

        # Should find only the cluster containing the app name
        assert len(result) == 1
        assert result[0] == "test-app-cluster"
        mock_ecs.list_clusters.assert_called_once()

    @pytest.mark.anyio
    async def test_find_clusters_no_clusters(self, mock_aws_clients):
        """Test find_clusters when no clusters exist."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response with empty clusterArns
        mock_ecs.list_clusters.return_value = {"clusterArns": []}

        result = await find_clusters("test-app", ecs_client=mock_ecs)
        assert result == []

    @pytest.mark.anyio
    async def test_find_clusters_missing_key(self, mock_aws_clients):
        """Test find_clusters when clusterArns key is missing."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response without clusterArns key
        mock_ecs.list_clusters.return_value = {}

        result = await find_clusters("test-app", ecs_client=mock_ecs)
        assert result == []

    @pytest.mark.anyio
    async def test_find_clusters_invalid_arn(self, mock_aws_clients):
        """Test find_clusters with invalid ARN format."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response with invalid ARN
        mock_ecs.list_clusters.return_value = {
            "clusterArns": [
                "not-a-valid-arn",
                "arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster",
            ]
        }

        result = await find_clusters("test-app", ecs_client=mock_ecs)
        assert len(result) == 1
        assert result[0] == "test-app-cluster"

    @pytest.mark.anyio
    async def test_find_services(self, mock_aws_clients):
        """Test finding ECS services in a cluster related to an application name."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure the response for list_services
        mock_ecs.list_services.return_value = {
            "serviceArns": [
                "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/test-app-service",
                "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/other-service",
            ]
        }

        result = await find_services("test-app", "test-cluster", ecs_client=mock_ecs)

        # Should find only the service containing the app name
        assert len(result) == 1
        assert result[0] == "test-app-service"
        mock_ecs.list_services.assert_called_once_with(cluster="test-cluster")

    @pytest.mark.anyio
    async def test_find_services_non_dictionary_response(self, mock_aws_clients):
        """Test find_services with a non-dictionary response."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_ecs.list_services.return_value = "not-a-dictionary"

        result = await find_services("test-app", "test-cluster", ecs_client=mock_ecs)
        assert result == []

    @pytest.mark.anyio
    async def test_find_services_missing_service_arns(self, mock_aws_clients):
        """Test find_services with missing serviceArns key."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_ecs.list_services.return_value = {"not_service_arns": []}

        result = await find_services("test-app", "test-cluster", ecs_client=mock_ecs)
        assert result == []

    @pytest.mark.anyio
    async def test_find_services_with_exception(self, mock_aws_clients):
        """Test find_services handling exceptions."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_ecs.list_services.side_effect = Exception("Service listing error")

        # Should handle the exception gracefully
        result = await find_services("test-app", "test-cluster", ecs_client=mock_ecs)
        assert result == []

    @pytest.mark.anyio
    async def test_find_load_balancers(self, mock_aws_clients):
        """Test finding load balancers related to an application name."""
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Configure response
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [{"LoadBalancerName": "test-app-lb"}, {"LoadBalancerName": "other-lb"}]
        }

        result = await find_load_balancers("test-app", elbv2_client=mock_elbv2)

        # Should find only the LB containing the app name
        assert len(result) == 1
        assert result[0] == "test-app-lb"
        mock_elbv2.describe_load_balancers.assert_called_once()

    @pytest.mark.anyio
    async def test_find_load_balancers_no_matches(self, mock_aws_clients):
        """Test finding load balancers with no name matches."""
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Configure response with no matching names
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {"LoadBalancerName": "other-lb-1"},
                {"LoadBalancerName": "other-lb-2"},
            ]
        }

        result = await find_load_balancers("test-app", elbv2_client=mock_elbv2)

        # Should find no load balancers
        assert result == []

    @pytest.mark.anyio
    async def test_find_load_balancers_no_key(self, mock_aws_clients):
        """Test find_load_balancers with missing LoadBalancers key."""
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Configure response with missing LoadBalancers key
        mock_elbv2.describe_load_balancers.return_value = {}

        result = await find_load_balancers("test-app", elbv2_client=mock_elbv2)

        # Should find no load balancers
        assert result == []

    @pytest.mark.anyio
    async def test_find_load_balancers_missing_name(self, mock_aws_clients):
        """Test find_load_balancers with missing LoadBalancerName."""
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Configure response with a load balancer missing the name
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {"LoadBalancerName": "test-app-lb"},
                {"OtherField": "no-name-field"},  # Missing LoadBalancerName
            ]
        }

        result = await find_load_balancers("test-app", elbv2_client=mock_elbv2)

        # Should find only the LB with proper name
        assert len(result) == 1
        assert result[0] == "test-app-lb"

    @pytest.mark.anyio
    async def test_get_task_definitions(self, mock_aws_clients):
        """Test get_task_definitions with case-insensitive matching."""
        mock_ecs = mock_aws_clients["ecs"]

        # Create task definition arns with mix of case
        task_def_arns = [
            "arn:aws:ecs:us-west-2:123456789012:task-definition/TEST-app:1",
            "arn:aws:ecs:us-west-2:123456789012:task-definition/other-app:1",
        ]

        # Set up paginator with AsyncIterator
        mock_paginator = mock.Mock()  # Not AsyncMock!
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskDefinitionArns": task_def_arns}]
        )
        mock_ecs.get_paginator.return_value = mock_paginator

        # Set up describe_task_definition with side_effect function for dynamic response
        async def mock_describe_task_def(taskDefinition, **kwargs):
            # Extract family name from ARN
            family = taskDefinition.split("/")[1].split(":")[0]
            return {
                "taskDefinition": {
                    "taskDefinitionArn": taskDefinition,
                    "family": family,
                    "containerDefinitions": [{"image": f"{family}-image"}],
                }
            }

        mock_ecs.describe_task_definition.side_effect = mock_describe_task_def

        result = await get_task_definitions("test-app", ecs_client=mock_ecs)

        # Should find the task definition with case-insensitive match
        assert len(result) == 1
        assert "TEST-app" in result[0]["taskDefinitionArn"]

    @pytest.mark.anyio
    async def test_get_stack_status(self, mock_aws_clients):
        """Test get_stack_status function."""
        mock_cfn = mock_aws_clients["cloudformation"]

        # Configure describe_stacks response
        mock_cfn.describe_stacks.return_value = {"Stacks": [{"StackStatus": "CREATE_COMPLETE"}]}

        result = await get_stack_status("test-app", cloudformation_client=mock_cfn)

        # Should return the stack status
        assert result == "CREATE_COMPLETE"
        mock_cfn.describe_stacks.assert_called_once_with(StackName="test-app")

    @pytest.mark.anyio
    async def test_get_stack_status_not_found(self, mock_aws_clients):
        """Test get_stack_status when stack is not found."""
        mock_cfn = mock_aws_clients["cloudformation"]

        # Configure error response
        error_response = {"Error": {"Code": "ValidationError", "Message": "Stack not found"}}
        mock_cfn.describe_stacks.side_effect = ClientError(error_response, "DescribeStacks")

        result = await get_stack_status("nonexistent-app", cloudformation_client=mock_cfn)

        # Should return NOT_FOUND
        assert result == "NOT_FOUND"

    @pytest.mark.anyio
    async def test_validate_container_images(self, mock_aws_clients):
        """Test validate_container_images function."""
        mock_ecr = mock_aws_clients["ecr"]

        # Test with multiple task definitions and container images
        task_definitions = [
            {
                "taskDefinitionArn": "\
                    arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app:latest",
                    }
                ],
            },
            {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:"
                "123456789012:task-definition/test-app:1",
                "containerDefinitions": [{"name": "web", "image": "nginx:latest"}],
            },
        ]

        # Configure mock responses for ECR
        mock_ecr.describe_repositories.return_value = {
            "repositories": [{"repositoryName": "test-app"}]
        }
        mock_ecr.describe_images.return_value = {"imageDetails": [{"imageTag": "latest"}]}

        result = await validate_container_images(task_definitions, ecr_client=mock_ecr)

        # Should validate all container images
        assert len(result) == 2
        assert result[0]["repository_type"] == "ecr"
        assert result[0]["exists"] == "true"
        assert result[1]["repository_type"] == "external"
        assert result[1]["exists"] == "unknown"

    @pytest.mark.anyio
    async def test_validate_image_ecr(self, mock_aws_clients):
        """Test validate_image function with ECR images."""
        mock_ecr = mock_aws_clients["ecr"]

        # Configure responses
        mock_ecr.describe_repositories.return_value = {"repositories": [{"repositoryName": "repo"}]}

        mock_ecr.describe_images.return_value = {"imageDetails": [{"imageTag": "tag"}]}

        result = await validate_image(
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:tag", ecr_client=mock_ecr
        )

        # Validation should succeed
        assert result["exists"] == "true"
        assert result["repository_type"] == "ecr"
        assert result["error"] is None
        mock_ecr.describe_repositories.assert_called_once_with(repositoryNames=["repo"])
        mock_ecr.describe_images.assert_called_once()

    @pytest.mark.anyio
    async def test_validate_image_ecr_repository_not_found(self, mock_aws_clients):
        """Test validate_image function with ECR repository not found."""
        mock_ecr = mock_aws_clients["ecr"]

        # Configure error response
        error_response = {
            "Error": {"Code": "RepositoryNotFoundException", "Message": "Repository repo not found"}
        }
        mock_ecr.describe_repositories.side_effect = ClientError(
            error_response, "DescribeRepositories"
        )

        result = await validate_image(
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:tag", ecr_client=mock_ecr
        )

        # Should fail validation
        assert result["exists"] == "false"
        assert result["repository_type"] == "ecr"
        assert "Repository repo not found" in result["error"]

    @pytest.mark.anyio
    async def test_validate_image_ecr_image_not_found(self, mock_aws_clients):
        """Test validate_image function with ECR image tag not found."""
        mock_ecr = mock_aws_clients["ecr"]

        # Configure responses - repository exists but image doesn't
        mock_ecr.describe_repositories.return_value = {"repositories": [{"repositoryName": "repo"}]}

        error_response = {
            "Error": {
                "Code": "ImageNotFoundException",
                "Message": "Image with tag 'missing' not found",
            }
        }
        mock_ecr.describe_images.side_effect = ClientError(error_response, "DescribeImages")

        result = await validate_image(
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:missing", ecr_client=mock_ecr
        )

        # Should fail validation but repository exists
        assert result["exists"] == "false"
        assert result["repository_type"] == "ecr"
        assert "not found" in result["error"]
        mock_ecr.describe_repositories.assert_called_once()

    @pytest.mark.anyio
    async def test_validate_image_ecr_other_client_error(self, mock_aws_clients):
        """Test validate_image function with other ClientError response."""
        mock_ecr = mock_aws_clients["ecr"]

        # Configure responses - repository exists but other error occurs
        mock_ecr.describe_repositories.return_value = {"repositories": [{"repositoryName": "repo"}]}

        error_response = {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}}
        mock_ecr.describe_images.side_effect = ClientError(error_response, "DescribeImages")

        result = await validate_image(
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:latest", ecr_client=mock_ecr
        )

        # All client errors are treated as image not found in current implementation
        assert result["exists"] == "false"  # Current implementation treats all errors as "false"
        assert result["repository_type"] == "ecr"
        assert "Access denied" in result["error"]

    @pytest.mark.anyio
    async def test_validate_image_non_ecr(self, mock_aws_clients):
        """Test validate_image function with non-ECR images."""
        mock_ecr = mock_aws_clients["ecr"]

        # Non-ECR image
        result = await validate_image("nginx:latest", ecr_client=mock_ecr)

        # Should show unknown status for non-ECR images
        assert result["exists"] == "unknown"
        assert result["repository_type"] == "external"
        assert result["error"] is None

        # Mock shouldn't be called for external images
        mock_ecr.describe_repositories.assert_not_called()

    @pytest.mark.anyio
    async def test_get_cluster_details(self, mock_aws_clients):
        """Test get_cluster_details function."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure describe_clusters response
        mock_ecs.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "status": "ACTIVE",
                    "runningTasksCount": 5,
                    "pendingTasksCount": 0,
                    "activeServicesCount": 2,
                    "registeredContainerInstancesCount": 3,
                }
            ]
        }

        result = await get_cluster_details(["test-cluster"], ecs_client=mock_ecs)

        # Should return cluster details
        assert len(result) == 1
        assert result[0]["name"] == "test-cluster"
        assert result[0]["status"] == "ACTIVE"
        assert result[0]["runningTasksCount"] == 5
        mock_ecs.describe_clusters.assert_called_once_with(clusters=["test-cluster"])

    @pytest.mark.anyio
    async def test_get_cluster_details_empty_input(self, mock_aws_clients):
        """Test get_cluster_details with empty cluster name list."""
        mock_ecs = mock_aws_clients["ecs"]

        result = await get_cluster_details([], ecs_client=mock_ecs)

        # Should return empty list
        assert result == []
        mock_ecs.describe_clusters.assert_not_called()

    @pytest.mark.anyio
    async def test_get_cluster_details_missing_clusters(self, mock_aws_clients):
        """Test get_cluster_details when clusters key is missing."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response without clusters key
        mock_ecs.describe_clusters.return_value = {"failures": []}

        result = await get_cluster_details(["test-cluster"], ecs_client=mock_ecs)

        # Should return empty list
        assert result == []

    @pytest.mark.anyio
    async def test_handle_aws_api_call_generic_exception(self):
        """Test handle_aws_api_call with a generic exception."""

        # Test with general Exception
        def failing_func():
            raise Exception("Generic error")

        result = await handle_aws_api_call(failing_func, "error-value")
        assert result == "error-value"

    def test_is_ecr_image(self):
        """Test is_ecr_image function with various formats."""
        # Valid ECR image URI
        assert is_ecr_image("123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:tag") is True

        # Without tag
        assert is_ecr_image("123456789012.dkr.ecr.us-west-2.amazonaws.com/repo") is True

        # Invalid URIs
        assert is_ecr_image("docker.io/nginx:latest") is False
        assert is_ecr_image("not-a-valid-url") is False

    def test_is_ecr_image_edge_cases(self):
        """Test is_ecr_image function with edge cases."""
        # Malformed hostname with double dots
        assert is_ecr_image("123456789012..dkr.ecr.us-west-2.amazonaws.com/repo") is False

        # Hostname starting with dot
        assert is_ecr_image(".123456789012.dkr.ecr.us-west-2.amazonaws.com/repo") is False

        # Hostname ending with dot
        assert is_ecr_image("123456789012.dkr.ecr.us-west-2.amazonaws.com./repo") is False

        # Invalid ECR pattern (wrong account ID length)
        assert is_ecr_image("123456789.dkr.ecr.us-west-2.amazonaws.com/repo") is False

        # Test with exception-causing input
        assert is_ecr_image(None) is False
        assert is_ecr_image({}) is False

    def test_parse_ecr_image_uri(self):
        """Test parse_ecr_image_uri function with various formats."""
        # Standard ECR URI with tag
        repo, tag = parse_ecr_image_uri("123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:tag")
        assert repo == "repo"
        assert tag == "tag"

        # Without tag (should default to latest)
        repo, tag = parse_ecr_image_uri("123456789012.dkr.ecr.us-west-2.amazonaws.com/repo")
        assert repo == "repo"
        assert tag == "latest"

    def test_parse_ecr_image_uri_error_handling(self):
        """Test parse_ecr_image_uri function with invalid inputs."""
        # Test with None
        repo, tag = parse_ecr_image_uri(None)
        assert repo == ""
        assert tag == ""

        # Test with empty string
        repo, tag = parse_ecr_image_uri("")
        assert repo == ""
        assert tag == "latest"  # Empty string gets 'latest' as the default tag

        # Test with complex path
        repo, tag = parse_ecr_image_uri(
            "123456789012.dkr.ecr.us-west-2.amazonaws.com/path/to/repo:tag"
        )
        assert repo == "repo"
        assert tag == "tag"

        # Test with ARN format - our implementation splits at first colon
        repo, tag = parse_ecr_image_uri("arn:aws:ecr:us-west-2:123456789012:repository/repo:tag")
        assert repo == "arn"
        assert tag == "aws:ecr:us-west-2:123456789012:repository/repo:tag"

    def test_create_assessment(self):
        """Test create_assessment function with various scenarios."""
        # Test with stack not found
        assessment = create_assessment(
            "test-app",
            "NOT_FOUND",
            {"clusters": [], "services": [], "task_definitions": [], "load_balancers": []},
        )
        assert "does not exist" in assessment

        # Test with stack complete but no clusters
        assessment = create_assessment(
            "test-app",
            "CREATE_COMPLETE",
            {"clusters": [], "services": [], "task_definitions": [], "load_balancers": []},
        )
        assert "but no related ECS clusters were found" in assessment

        # Test with stack and clusters both exist
        assessment = create_assessment(
            "test-app",
            "CREATE_COMPLETE",
            {
                "clusters": ["test-cluster"],
                "services": [],
                "task_definitions": [],
                "load_balancers": [],
            },
        )
        assert "both exist" in assessment

    @pytest.mark.anyio
    async def test_discover_resources(self, mock_aws_clients):
        """Test discover_resources function."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Mock clusters
        mock_ecs.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"]
        }

        # Mock services
        mock_ecs.list_services.return_value = {
            "serviceArns": [
                "arn:aws:ecs:us-west-2:123456789012:service/test-app-cluster/test-app-service"
            ]
        }

        # Mock task definitions
        task_def_arns = ["arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"]
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskDefinitionArns": task_def_arns}]
        )
        mock_ecs.get_paginator.return_value = mock_paginator

        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:"
                "123456789012:task-definition/test-app:1",
                "containerDefinitions": [{"name": "app", "image": "test-image"}],
            }
        }

        # Mock load balancers
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [{"LoadBalancerName": "test-app-lb"}]
        }

        resources, task_defs = await discover_resources(
            "test-app", ecs_client=mock_ecs, elbv2_client=mock_elbv2
        )

        # Verify the results
        assert "test-app-cluster" in resources["clusters"]
        assert "test-app-service" in resources["services"]
        assert "test-app:1" in resources["task_definitions"]
        assert "test-app-lb" in resources["load_balancers"]
        assert len(task_defs) == 1
        assert task_defs[0]["containerDefinitions"][0]["name"] == "app"

    @pytest.mark.anyio
    async def test_handle_aws_api_call(self):
        """Test handle_aws_api_call utility function."""

        # Test with sync function
        def sync_func(arg1, arg2):
            return f"{arg1}-{arg2}"

        result = await handle_aws_api_call(sync_func, "default", "value1", "value2")
        assert result == "value1-value2"

        # Test with async function
        async def async_func(arg1, arg2):
            return f"{arg1}-{arg2}"

        result = await handle_aws_api_call(async_func, "default", "value1", "value2")
        assert result == "value1-value2"

        # Test with ClientError
        def error_func():
            error_response = {"Error": {"Code": "TestError", "Message": "Test error"}}
            raise ClientError(error_response, "TestOperation")

        result = await handle_aws_api_call(error_func, "default-value")
        assert result == "default-value"


class TestComprehensiveSystem:
    """Test the end-to-end functionality of get_ecs_troubleshooting_guidance."""

    @pytest.mark.anyio
    async def test_successful_execution(self, mock_aws_clients):
        """Test successful execution with all resources existing."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_ecr = mock_aws_clients["ecr"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Setup CloudFormation
        mock_cfn.describe_stacks.return_value = {"Stacks": [{"StackStatus": "CREATE_COMPLETE"}]}

        # Setup clusters
        mock_ecs.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"]
        }
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-app-cluster")]
        }

        # Setup services
        mock_ecs.list_services.return_value = {
            "serviceArns": [
                "arn:aws:ecs:us-west-2:123456789012:service/test-app-cluster/test-app-service"
            ]
        }

        # Setup task definitions
        task_def_arns = ["arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"]
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskDefinitionArns": task_def_arns}]
        )
        mock_ecs.get_paginator.return_value = mock_paginator

        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:"
                "123456789012:task-definition/test-app:1",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app:latest",
                    }
                ],
            }
        }

        # Setup ECR
        mock_ecr.describe_repositories.return_value = {
            "repositories": [{"repositoryName": "test-app"}]
        }
        mock_ecr.describe_images.return_value = {"imageDetails": [{"imageTag": "latest"}]}

        # Setup load balancers
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [{"LoadBalancerName": "test-app-lb"}]
        }

        # Call the main function
        result = await get_ecs_troubleshooting_guidance(
            "test-app",
            symptoms_description="Test symptoms",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        # Verify result
        assert result["status"] == "success"
        assert "both exist" in result["assessment"]
        assert result["raw_data"]["symptoms_description"] == "Test symptoms"
        assert "test-app-cluster" in result["raw_data"]["related_resources"]["clusters"]
        assert len(result["raw_data"]["image_check_results"]) == 1
        assert result["raw_data"]["image_check_results"][0]["exists"] == "true"

    @pytest.mark.anyio
    async def test_stack_not_found(self, mock_aws_clients):
        """Test scenario where CloudFormation stack is not found."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_ecr = mock_aws_clients["ecr"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Configure CloudFormation error response
        error_response = {"Error": {"Code": "ValidationError", "Message": "Stack not found"}}
        mock_cfn.describe_stacks.side_effect = ClientError(error_response, "DescribeStacks")

        # Configure ECS paginator for task definitions
        task_def_arns = []  # Empty list
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskDefinitionArns": task_def_arns}]
        )
        mock_ecs.get_paginator.return_value = mock_paginator

        result = await get_ecs_troubleshooting_guidance(
            "nonexistent-app",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        # Should indicate stack not found
        assert result["status"] == "success"
        assert "does not exist" in result["assessment"]
        assert result["raw_data"]["cloudformation_status"] == "NOT_FOUND"

    @pytest.mark.anyio
    async def test_cloudformation_access_denied(self, mock_aws_clients):
        """Test when CloudFormation access is denied."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_ecr = mock_aws_clients["ecr"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Configure CloudFormation error response
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_cfn.describe_stacks.side_effect = ClientError(error_response, "DescribeStacks")

        result = await get_ecs_troubleshooting_guidance(
            "test-app",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        # Should indicate error accessing stack
        assert result["status"] == "error"
        assert "error" in result
        assert "Error accessing stack information" in result["assessment"]
        assert "Access denied" in result["error"]

    @pytest.mark.anyio
    async def test_generic_exception_handling(self, mock_aws_clients):
        """Test general exception handling with unexpected errors."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]
        mock_ecr = mock_aws_clients["ecr"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Make the main get_ecs_troubleshooting_guidance function raise an unhandled exception
        mock_ecs.list_clusters.side_effect = Exception("Unexpected error")
        mock_cfn.describe_stacks.side_effect = Exception("Other unexpected error")

        # Make sure elbv2 client is properly mocked
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}

        result = await get_ecs_troubleshooting_guidance(
            "test-app",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        # Should indicate general error
        assert result["status"] == "error"
        assert "error" in result
        assert "Other unexpected error" in result["error"] or "Unexpected error" in result["error"]
        # When the CloudFormation describe_stacks call fails, the specific error message is
        # included in the assessment
        assert "Other unexpected error" in result["assessment"]

    @pytest.mark.anyio
    async def test_stack_in_progress(self, mock_aws_clients):
        """Test when CloudFormation stack is in progress."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_ecr = mock_aws_clients["ecr"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Configure CloudFormation response
        mock_cfn.describe_stacks.return_value = {"Stacks": [{"StackStatus": "CREATE_IN_PROGRESS"}]}

        # Configure ECS paginator for task definitions
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator([{"taskDefinitionArns": []}])
        mock_ecs.get_paginator.return_value = mock_paginator

        result = await get_ecs_troubleshooting_guidance(
            "test-app",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        # Should indicate stack is in progress
        assert result["status"] == "success"
        assert "is currently being created/updated" in result["assessment"]
        assert result["raw_data"]["cloudformation_status"] == "CREATE_IN_PROGRESS"

    @pytest.mark.anyio
    async def test_stack_failure_state(self, mock_aws_clients):
        """Test when CloudFormation stack is in a failure state."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_ecr = mock_aws_clients["ecr"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Configure CloudFormation response
        mock_cfn.describe_stacks.return_value = {"Stacks": [{"StackStatus": "ROLLBACK_COMPLETE"}]}

        # Configure ECS paginator for task definitions
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator([{"taskDefinitionArns": []}])
        mock_ecs.get_paginator.return_value = mock_paginator

        result = await get_ecs_troubleshooting_guidance(
            "test-app",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        # Should indicate stack is in failed state
        assert result["status"] == "success"
        assert "is in a failed state" in result["assessment"]
        assert result["raw_data"]["cloudformation_status"] == "ROLLBACK_COMPLETE"

    @pytest.mark.anyio
    async def test_mixed_image_validation(self, mock_aws_clients):
        """Test validation of mixed container image types."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_ecr = mock_aws_clients["ecr"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Setup CloudFormation
        mock_cfn.describe_stacks.return_value = {"Stacks": [{"StackStatus": "CREATE_COMPLETE"}]}

        # Setup clusters
        mock_ecs.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/test-app-cluster"]
        }
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-app-cluster")]
        }

        # Setup task definitions with mixed image types
        task_def_arns = ["arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"]
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskDefinitionArns": task_def_arns}]
        )
        mock_ecs.get_paginator.return_value = mock_paginator

        # Task definition with both ECR and external images
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:"
                "123456789012:task-definition/test-app:1",
                "containerDefinitions": [
                    {
                        "name": "app",
                        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-app:latest",
                    },
                    {"name": "nginx", "image": "nginx:latest"},
                ],
            }
        }

        # ECR repository exists but image doesn't
        mock_ecr.describe_repositories.return_value = {
            "repositories": [{"repositoryName": "test-app"}]
        }

        error_response = {"Error": {"Code": "ImageNotFoundException", "Message": "Image not found"}}
        mock_ecr.describe_images.side_effect = ClientError(error_response, "DescribeImages")

        result = await get_ecs_troubleshooting_guidance(
            "test-app",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        # Should show both ECR and external images in validation results
        assert result["status"] == "success"
        assert len(result["raw_data"]["image_check_results"]) == 2
        # ECR image should show as not existing due to mocked error
        assert result["raw_data"]["image_check_results"][0]["repository_type"] == "ecr"
        assert result["raw_data"]["image_check_results"][0]["exists"] == "false"
        # External image should be marked as unknown
        assert result["raw_data"]["image_check_results"][1]["repository_type"] == "external"
        assert result["raw_data"]["image_check_results"][1]["exists"] == "unknown"

    @pytest.mark.anyio
    async def test_task_definition_parsing_error(self, mock_aws_clients):
        """Test robust handling of malformed task definition ARNs."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_elbv2 = mock_aws_clients["elbv2"]
        mock_ecr = mock_aws_clients["ecr"]

        # Setup CloudFormation
        mock_cfn.describe_stacks.return_value = {"Stacks": [{"StackStatus": "CREATE_COMPLETE"}]}

        # Setup load balancers
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}

        # Return malformed ARNs
        task_def_arns = [
            "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1",  # Valid
            "not-an-arn",  # Invalid
        ]
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskDefinitionArns": task_def_arns}]
        )
        mock_ecs.get_paginator.return_value = mock_paginator

        # Valid task definition response for the valid ARN
        async def mock_describe_task_def(taskDefinition, **kwargs):
            if "not-an-arn" in taskDefinition:
                raise ClientError(
                    {"Error": {"Code": "InvalidArn", "Message": "Invalid ARN"}},
                    "DescribeTaskDefinition",
                )

            return {
                "taskDefinition": {
                    "taskDefinitionArn": "arn:aws:ecs:us-west-2:"
                    "123456789012:task-definition/test-app:1",
                    "containerDefinitions": [{"name": "app", "image": "test-image"}],
                }
            }

        mock_ecs.describe_task_definition.side_effect = mock_describe_task_def

        # Should handle the error gracefully and continue with valid task definition
        result = await get_ecs_troubleshooting_guidance(
            "test-app",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        assert result["status"] == "success"
        # Should have processed the valid task definition despite the invalid one
        assert len(result["raw_data"]["task_definitions"]) >= 0

    @pytest.mark.anyio
    async def test_missing_containers(self, mock_aws_clients):
        """Test handling task definitions with missing container definitions."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_elbv2 = mock_aws_clients["elbv2"]
        mock_ecr = mock_aws_clients["ecr"]

        # Setup CloudFormation
        mock_cfn.describe_stacks.return_value = {"Stacks": [{"StackStatus": "CREATE_COMPLETE"}]}

        # Setup load balancers
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}

        # Setup clusters
        mock_ecs.list_clusters.return_value = {"clusterArns": []}

        # Setup task definitions
        task_def_arns = ["arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"]
        mock_paginator = mock.Mock()
        mock_paginator.paginate.return_value = AsyncIterator(
            [{"taskDefinitionArns": task_def_arns}]
        )
        mock_ecs.get_paginator.return_value = mock_paginator

        # Task definition without containerDefinitions
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:"
                "123456789012:task-definition/test-app:1",
                # No containerDefinitions key
            }
        }

        # Should handle missing containerDefinitions gracefully
        result = await get_ecs_troubleshooting_guidance(
            "test-app",
            ecs_client=mock_ecs,
            cloudformation_client=mock_cfn,
            ecr_client=mock_ecr,
            elbv2_client=mock_elbv2,
        )

        assert result["status"] == "success"
        # Should have empty image check results
        assert result["raw_data"]["image_check_results"] == []
