"""
Unit tests for the get_ecs_troubleshooting_guidance tool.
"""

from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import (
    collect_cluster_details,
    get_ecs_troubleshooting_guidance,
    handle_aws_api_call,
    is_ecr_image,
    parse_ecr_image_uri,
    validate_container_images,
    validate_image,
)
from tests.unit.utils.async_test_utils import (
    AsyncIterator,
    create_sample_cluster_data,
)


class TestGuidanceBase:
    """Base class for guidance tests with proper AWS client mocking."""

    def setup_method(self):
        """Clear AWS client cache before each test to ensure isolation."""
        from awslabs.ecs_mcp_server.utils.aws import _aws_clients

        _aws_clients.clear()

    def mock_aws_clients(self, mock_clients):
        """
        Create a context manager that mocks boto3.client with the provided client dictionary.

        Args:
            mock_clients: Dictionary mapping service names to mock clients
                         e.g., {"ecs": mock_ecs, "ecr": mock_ecr}
        """

        def mock_client_factory(service_name, **kwargs):
            return mock_clients.get(service_name, mock.MagicMock())

        return mock.patch("boto3.client", side_effect=mock_client_factory)


@pytest.fixture
def mock_aws_clients():
    """Set up all mock AWS clients needed for testing."""
    mock_ecs = mock.MagicMock()
    mock_cfn = mock.MagicMock()
    mock_ecr = mock.MagicMock()
    mock_elbv2 = mock.MagicMock()

    return {"ecs": mock_ecs, "cloudformation": mock_cfn, "ecr": mock_ecr, "elbv2": mock_elbv2}


class TestHelperFunctions(TestGuidanceBase):
    """Test individual helper functions in the get_ecs_troubleshooting_guidance module."""

    @pytest.mark.anyio
    async def test_handle_aws_api_call_client_error(self):
        """Test handle_aws_api_call with ClientError."""
        from botocore.exceptions import ClientError

        def failing_func():
            error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
            raise ClientError(error_response, "TestOperation")

        result = await handle_aws_api_call(failing_func, "error-value")
        assert result == "error-value"

    @pytest.mark.anyio
    async def test_handle_aws_api_call_with_coroutine(self):
        """Test handle_aws_api_call with a coroutine function."""

        async def async_func():
            return "success"

        result = await handle_aws_api_call(async_func, "error-value")
        assert result == "success"

    def test_is_ecr_image_with_exception(self):
        """Test is_ecr_image function with exception-causing input."""
        # Test with invalid input that causes exception in urlparse
        assert is_ecr_image("://invalid-url") is False

    def test_parse_ecr_image_uri_with_exception(self):
        """Test parse_ecr_image_uri with exception-causing input."""
        # Test with input that causes exception - use a type that will cause split() to fail
        repo, tag = parse_ecr_image_uri(None)
        assert repo == ""
        assert tag == ""

    @pytest.mark.anyio
    async def test_validate_image_general_exception_in_repo_check(self, mock_aws_clients):
        """Test validate_image with general exception during repository check."""
        mock_ecr = mock_aws_clients["ecr"]

        # Configure general exception during repository check
        mock_ecr.describe_repositories.side_effect = Exception("General repository error")

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_image("123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:tag")

        assert result["exists"] == "false"
        assert result["repository_type"] == "ecr"
        assert "General repository error" in result["error"]

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

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_container_images(task_definitions)

        # Should validate all container images
        assert len(result) == 2
        assert result[0]["repository_type"] == "ecr"
        assert result[0]["exists"] == "true"
        assert result[1]["repository_type"] == "external"
        assert result[1]["exists"] == "unknown"

    @pytest.mark.anyio
    async def test_validate_container_images_no_containers(self, mock_aws_clients):
        """Test validate_container_images with task definitions having no container definitions."""
        mock_ecr = mock_aws_clients["ecr"]

        # Test with task definition that has no containerDefinitions key
        task_definitions = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                ),
                # No containerDefinitions key
            }
        ]

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_container_images(task_definitions)

        # Should return empty list
        assert result == []
        mock_ecr.describe_repositories.assert_not_called()

    @pytest.mark.anyio
    async def test_validate_container_images_missing_image(self, mock_aws_clients):
        """Test validate_container_images with containers missing image field."""
        mock_ecr = mock_aws_clients["ecr"]

        # Test with container definition that has no image field
        task_definitions = [
            {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                ),
                "containerDefinitions": [
                    {"name": "app"}  # No image field
                ],
            }
        ]

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_container_images(task_definitions)

        # Should return result with empty image string
        assert len(result) == 1
        assert result[0]["image"] == ""
        mock_ecr.describe_repositories.assert_not_called()

    @pytest.mark.anyio
    async def test_validate_image_ecr(self, mock_aws_clients):
        """Test validate_image function with ECR images."""
        mock_ecr = mock_aws_clients["ecr"]

        # Configure responses
        mock_ecr.describe_repositories.return_value = {"repositories": [{"repositoryName": "repo"}]}

        mock_ecr.describe_images.return_value = {"imageDetails": [{"imageTag": "tag"}]}

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_image("123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:tag")

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

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_image("123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:tag")

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

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_image(
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:missing"
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

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_image(
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:latest"
            )

        # All client errors are treated as image not found in current implementation
        assert result["exists"] == "false"  # Current implementation treats all errors as "false"
        assert result["repository_type"] == "ecr"
        assert "Access denied" in result["error"]

    @pytest.mark.anyio
    async def test_validate_image_ecr_general_exception(self, mock_aws_clients):
        """Test validate_image function with general exception during validation."""
        mock_ecr = mock_aws_clients["ecr"]

        # Configure responses - repository exists but general error occurs
        mock_ecr.describe_repositories.return_value = {"repositories": [{"repositoryName": "repo"}]}

        # Set up a general exception
        mock_ecr.describe_images.side_effect = Exception("General error")

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_image(
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo:latest"
            )

        # Should fail validation with general error
        assert result["exists"] == "false"
        assert result["repository_type"] == "ecr"
        assert "General error" in result["error"]

    @pytest.mark.anyio
    async def test_validate_image_non_ecr(self, mock_aws_clients):
        """Test validate_image function with non-ECR images."""
        mock_ecr = mock_aws_clients["ecr"]

        # Non-ECR image
        with self.mock_aws_clients({"ecr": mock_ecr}):
            result = await validate_image("nginx:latest")

        # Should show unknown status for non-ECR images
        assert result["exists"] == "unknown"
        assert result["repository_type"] == "external"
        assert result["error"] is None

        # Mock shouldn't be called for external images
        mock_ecr.describe_repositories.assert_not_called()

    @pytest.mark.anyio
    async def test_collect_cluster_details(self, mock_aws_clients):
        """Test collect_cluster_details function."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure describe_clusters response
        mock_ecs.describe_clusters.return_value = {
            "clusters": [
                {
                    "clusterName": "test-cluster",
                    "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster",
                    "status": "ACTIVE",
                    "runningTasksCount": 5,
                    "pendingTasksCount": 0,
                    "activeServicesCount": 2,
                    "registeredContainerInstancesCount": 3,
                }
            ]
        }

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            cluster_details, cluster_arn = await collect_cluster_details("test-cluster", mock_ecs)

        # Should return cluster details and ARN
        assert len(cluster_details) == 1
        assert cluster_details[0]["name"] == "test-cluster"
        assert cluster_details[0]["status"] == "ACTIVE"
        assert cluster_details[0]["runningTasksCount"] == 5
        assert cluster_arn == "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster"
        mock_ecs.describe_clusters.assert_called_once_with(clusters=["test-cluster"])

    @pytest.mark.anyio
    async def test_collect_cluster_details_error(self, mock_aws_clients):
        """Test collect_cluster_details with error handling."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure error response
        mock_ecs.describe_clusters.side_effect = Exception("Cluster access error")

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            cluster_details, cluster_arn = await collect_cluster_details("test-cluster", mock_ecs)

        # Should return empty results
        assert cluster_details == []
        assert cluster_arn is None

    @pytest.mark.anyio
    async def test_collect_cluster_details_missing_clusters(self, mock_aws_clients):
        """Test collect_cluster_details when clusters key is missing."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response without clusters key
        mock_ecs.describe_clusters.return_value = {"failures": []}

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            cluster_details, cluster_arn = await collect_cluster_details("test-cluster", mock_ecs)

        # Should return empty results
        assert cluster_details == []
        assert cluster_arn is None

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


class TestComprehensiveSystem(TestGuidanceBase):
    """Test the end-to-end functionality of get_ecs_troubleshooting_guidance."""

    @pytest.mark.anyio
    async def test_successful_execution(self, mock_aws_clients):
        """Test successful execution with cluster and service."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_ecr = mock_aws_clients["ecr"]

        # Setup clusters
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Setup services
        mock_ecs.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-service",
                    "status": "ACTIVE",
                    "taskDefinition": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-service:1"
                    ),
                }
            ]
        }

        # Setup task definitions
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-service:1"
                ),
                "containerDefinitions": [
                    {
                        "name": "app",
                        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-service:latest",
                    }
                ],
            }
        }

        # Setup ECR
        mock_ecr.describe_repositories.return_value = {
            "repositories": [{"repositoryName": "test-service"}]
        }
        mock_ecr.describe_images.return_value = {"imageDetails": [{"imageTag": "latest"}]}

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs, "ecr": mock_ecr}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
                service_name="test-service",
                symptoms_description="Test symptoms",
            )

        # Verify result
        assert result["status"] == "success"
        assert "Analyzed ECS cluster 'test-cluster'" in result["assessment"]
        assert "and service 'test-service'" in result["assessment"]
        assert result["raw_data"]["symptoms_description"] == "Test symptoms"
        assert len(result["raw_data"]["cluster_details"]) == 1
        assert result["raw_data"]["cluster_details"][0]["name"] == "test-cluster"
        assert len(result["raw_data"]["service_details"]) == 1
        assert result["raw_data"]["service_details"][0]["name"] == "test-service"
        assert len(result["raw_data"]["image_check_results"]) == 1
        assert result["raw_data"]["image_check_results"][0]["exists"] == "true"

    @pytest.mark.anyio
    async def test_cluster_only(self, mock_aws_clients):
        """Test execution with only cluster name provided."""
        mock_ecs = mock_aws_clients["ecs"]

        # Setup clusters
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
            )

        # Verify result
        assert result["status"] == "success"
        assert "Analyzed ECS cluster 'test-cluster'" in result["assessment"]
        assert len(result["raw_data"]["cluster_details"]) == 1
        assert result["raw_data"]["cluster_details"][0]["name"] == "test-cluster"
        assert "service_name" not in result["raw_data"]
        assert len(result["raw_data"]["task_definitions"]) == 0

    @pytest.mark.anyio
    async def test_service_not_found(self, mock_aws_clients):
        """Test when service is not found."""
        mock_ecs = mock_aws_clients["ecs"]

        # Setup clusters
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Setup empty services response
        mock_ecs.describe_services.return_value = {
            "services": [],
            "failures": [{"reason": "MISSING"}],
        }

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
                service_name="nonexistent-service",
            )

        # Verify result
        assert result["status"] == "success"
        assert "Analyzed ECS cluster 'test-cluster'" in result["assessment"]
        assert "and service 'nonexistent-service'" in result["assessment"]
        assert len(result["raw_data"]["task_definitions"]) == 0

    @pytest.mark.anyio
    async def test_generic_exception_handling(self, mock_aws_clients):
        """Test general exception handling with unexpected errors."""
        mock_ecs = mock_aws_clients["ecs"]

        # Make the describe_clusters function raise an unhandled exception
        mock_ecs.describe_clusters.side_effect = Exception("Unexpected error")

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
            )

        # Should indicate general error
        assert result["status"] == "error"
        assert "error" in result
        assert "Cluster 'test-cluster' not found" in result["error"]
        assert "Error analyzing deployment" in result["assessment"]

    @pytest.mark.anyio
    async def test_service_with_task_definition(self, mock_aws_clients):
        """Test service with task definition."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_ecr = mock_aws_clients["ecr"]

        # Setup clusters
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Setup services with task definition
        mock_ecs.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-service",
                    "status": "ACTIVE",
                    "taskDefinition": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-service:1"
                    ),
                }
            ]
        }

        # Setup task definition
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-service:1"
                ),
                "containerDefinitions": [
                    {
                        "name": "app",
                        "image": "nginx:latest",  # Using a non-ECR image
                    }
                ],
            }
        }

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs, "ecr": mock_ecr}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
                service_name="test-service",
            )

        # Verify result
        assert result["status"] == "success"
        assert "1 task definition" in result["assessment"]
        assert len(result["raw_data"]["task_definitions"]) == 1
        assert len(result["raw_data"]["image_check_results"]) == 1
        assert result["raw_data"]["image_check_results"][0]["repository_type"] == "external"

    @pytest.mark.anyio
    async def test_service_with_task_definition_error(self, mock_aws_clients):
        """Test service with task definition error."""
        mock_ecs = mock_aws_clients["ecs"]

        # Setup clusters
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Setup services with task definition
        mock_ecs.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-service",
                    "status": "ACTIVE",
                    "taskDefinition": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-service:1"
                    ),
                }
            ]
        }

        # Setup task definition error
        mock_ecs.describe_task_definition.side_effect = Exception("Task definition error")

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
                service_name="test-service",
            )

        # Verify result
        assert result["status"] == "success"
        assert "Analyzed ECS cluster 'test-cluster'" in result["assessment"]
        assert "and service 'test-service'" in result["assessment"]
        assert len(result["raw_data"]["task_definitions"]) == 0

    @pytest.mark.anyio
    async def test_mixed_image_validation(self, mock_aws_clients):
        """Test validation of mixed container image types."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_ecr = mock_aws_clients["ecr"]

        # Setup clusters
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Setup services with task definition
        mock_ecs.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-service",
                    "status": "ACTIVE",
                    "taskDefinition": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-service:1"
                    ),
                }
            ]
        }

        # Task definition with both ECR and external images
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-service:1"
                ),
                "containerDefinitions": [
                    {
                        "name": "app",
                        "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-service:latest",
                    },
                    {"name": "nginx", "image": "nginx:latest"},
                ],
            }
        }

        # ECR repository exists but image doesn't
        mock_ecr.describe_repositories.return_value = {
            "repositories": [{"repositoryName": "test-service"}]
        }

        error_response = {"Error": {"Code": "ImageNotFoundException", "Message": "Image not found"}}
        mock_ecr.describe_images.side_effect = ClientError(error_response, "DescribeImages")

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs, "ecr": mock_ecr}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
                service_name="test-service",
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

        # Setup clusters
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Setup services with invalid task definition ARN
        mock_ecs.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "test-service",
                    "status": "ACTIVE",
                    "taskDefinition": "not-an-arn",  # Invalid ARN
                }
            ]
        }

        # Mock describe_task_definition to raise error for invalid ARN
        mock_ecs.describe_task_definition.side_effect = ClientError(
            {"Error": {"Code": "InvalidArn", "Message": "Invalid ARN"}},
            "DescribeTaskDefinition",
        )

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
                service_name="test-service",
            )

        # Should handle the error gracefully
        assert result["status"] == "success"
        assert "Analyzed ECS cluster 'test-cluster'" in result["assessment"]
        assert len(result["raw_data"]["task_definitions"]) == 0

    @pytest.mark.anyio
    async def test_missing_containers(self, mock_aws_clients):
        """Test handling task definitions with missing container definitions."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]
        mock_elbv2 = mock_aws_clients["elbv2"]
        mock_ecr = mock_aws_clients["ecr"]

        # Setup clusters - need to set up describe_clusters for the refactored code
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Setup CloudFormation
        mock_cfn.describe_stacks.return_value = {"Stacks": [{"StackStatus": "CREATE_COMPLETE"}]}

        # Setup load balancers
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}

        # Setup service discovery
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

        # Mock boto3.client and call the main function
        with self.mock_aws_clients(
            {"ecs": mock_ecs, "cloudformation": mock_cfn, "ecr": mock_ecr, "elbv2": mock_elbv2}
        ):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
            )

        assert result["status"] == "success"
        # Should have empty image check results
        assert result["raw_data"]["image_check_results"] == []

    @pytest.mark.anyio
    async def test_symptoms_description(self, mock_aws_clients):
        """Test that symptoms description is included in the result."""
        mock_ecs = mock_aws_clients["ecs"]

        # Setup clusters
        mock_ecs.describe_clusters.return_value = {
            "clusters": [create_sample_cluster_data("test-cluster")]
        }

        # Call with custom symptoms description
        symptoms = "My ECS service isn't accessible through the ALB"

        # Mock boto3.client and call the main function
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await get_ecs_troubleshooting_guidance(
                cluster_name="test-cluster",
                symptoms_description=symptoms,
            )

        # Verify symptoms description is included in result
        assert result["status"] == "success"
        assert result["raw_data"]["symptoms_description"] == symptoms
