"""
Unit tests for the utils.py module.
"""

from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools.utils import (
    _get_task_definition_by_service,
    _get_task_definition_by_task,
    _get_task_definitions_by_family_prefix,
    _get_task_definitions_by_stack,
    find_clusters,
    find_load_balancers,
    find_services,
    find_task_definitions,
    get_cloudformation_stack_if_exists,
)
from tests.unit.utils.async_test_utils import (
    AsyncIterator,
)


class TestUtilsBase:
    """Base class for utility tests with proper AWS client mocking."""

    def setup_method(self):
        """Clear AWS client cache before each test to ensure isolation."""
        from awslabs.ecs_mcp_server.utils.aws import _aws_clients

        _aws_clients.clear()

    def mock_aws_clients(self, mock_clients):
        """
        Create a context manager that mocks boto3.client with the provided client dictionary.

        Args:
            mock_clients: Dictionary mapping service names to mock clients
                         e.g., {"ecs": mock_ecs, "cloudformation": mock_cfn}
        """

        def mock_client_factory(service_name, **kwargs):
            return mock_clients.get(service_name, mock.MagicMock())

        return mock.patch("boto3.client", side_effect=mock_client_factory)


@pytest.fixture
def mock_aws_clients():
    """Set up all mock AWS clients needed for testing."""
    mock_ecs = mock.MagicMock()
    mock_cfn = mock.MagicMock()
    mock_elbv2 = mock.MagicMock()

    # Return dictionary of clients
    return {"ecs": mock_ecs, "cloudformation": mock_cfn, "elbv2": mock_elbv2}


class TestFindClusters(TestUtilsBase):
    """Test the find_clusters function in utils.py."""

    @pytest.mark.anyio
    async def test_find_clusters_success(self, mock_aws_clients):
        """Test successful retrieval of cluster names."""
        mock_ecs = mock_aws_clients["ecs"]

        # Set up paginator - using Mock not MagicMock because paginate is not async
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator(
            [
                {
                    "clusterArns": [
                        "arn:aws:ecs:us-west-2:123456789012:cluster/cluster-1",
                        "arn:aws:ecs:us-west-2:123456789012:cluster/cluster-2",
                    ]
                }
            ]
        )
        # Replace get_paginator with a regular Mock to avoid returning a coroutine
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_clusters()

        # Assert the function correctly extracted cluster names
        assert len(result) == 2
        assert "cluster-1" in result
        assert "cluster-2" in result
        mock_ecs.get_paginator.assert_called_once_with("list_clusters")

    @pytest.mark.anyio
    async def test_find_clusters_empty_response(self, mock_aws_clients):
        """Test with empty response from list_clusters."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure empty response with paginator
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator([{"clusterArns": []}])
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_clusters()

        # Assert empty result
        assert result == []
        mock_ecs.get_paginator.assert_called_once_with("list_clusters")

    @pytest.mark.anyio
    async def test_find_clusters_missing_key(self, mock_aws_clients):
        """Test with missing 'clusterArns' key in response."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response without clusterArns key
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator([{}])
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_clusters()

        # Assert empty result
        assert result == []
        mock_ecs.get_paginator.assert_called_once_with("list_clusters")

    @pytest.mark.anyio
    async def test_find_clusters_with_invalid_arn(self, mock_aws_clients):
        """Test handling of invalid ARN format."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response with invalid ARN
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator(
            [
                {
                    "clusterArns": [
                        "arn:aws:ecs:us-west-2:123456789012:cluster/valid-cluster",
                        "invalid-arn-format",
                    ]
                }
            ]
        )
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_clusters()

        # Should only include the valid ARN
        assert len(result) == 1
        assert "valid-cluster" in result
        mock_ecs.get_paginator.assert_called_once_with("list_clusters")

    @pytest.mark.anyio
    async def test_find_clusters_with_exception(self, mock_aws_clients):
        """Test exception handling in find_clusters."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure get_paginator to raise an exception
        mock_ecs.get_paginator.side_effect = Exception("Test exception")

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_clusters()

        # Should return empty list on exception
        assert result == []
        mock_ecs.get_paginator.assert_called_once_with("list_clusters")

    @pytest.mark.anyio
    async def test_find_clusters_with_pagination(self, mock_aws_clients):
        """Test pagination handling in find_clusters."""
        mock_ecs = mock_aws_clients["ecs"]

        # Set up paginator mock for multiple pages
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator(
            [
                {"clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/cluster-page1"]},
                {"clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/cluster-page2"]},
            ]
        )
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_clusters()

        # Should include results from all pages
        assert len(result) == 2
        assert "cluster-page1" in result
        assert "cluster-page2" in result
        mock_ecs.get_paginator.assert_called_once_with("list_clusters")


class TestFindServices(TestUtilsBase):
    """Test the find_services function in utils.py."""

    @pytest.mark.anyio
    async def test_find_services_success(self, mock_aws_clients):
        """Test successful retrieval of service names."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure paginator mock for list_services
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator(
            [
                {
                    "serviceArns": [
                        "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/service-1",
                        "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/service-2",
                    ]
                }
            ]
        )
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_services("test-cluster")

        # Assert the function correctly extracted service names
        assert len(result) == 2
        assert "service-1" in result
        assert "service-2" in result
        mock_ecs.get_paginator.assert_called_once_with("list_services")
        paginator.paginate.assert_called_once_with(cluster="test-cluster")

    @pytest.mark.anyio
    async def test_find_services_empty_response(self, mock_aws_clients):
        """Test with empty response from list_services."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure empty response with paginator
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator([{"serviceArns": []}])
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_services("test-cluster")

        # Assert empty result
        assert result == []
        mock_ecs.get_paginator.assert_called_once_with("list_services")
        paginator.paginate.assert_called_once_with(cluster="test-cluster")

    @pytest.mark.anyio
    async def test_find_services_missing_key(self, mock_aws_clients):
        """Test with missing 'serviceArns' key in response."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response without serviceArns key
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator([{}])
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_services("test-cluster")

        # Assert empty result
        assert result == []
        mock_ecs.get_paginator.assert_called_once_with("list_services")
        paginator.paginate.assert_called_once_with(cluster="test-cluster")

    @pytest.mark.anyio
    async def test_find_services_with_invalid_arn(self, mock_aws_clients):
        """Test handling of invalid ARN format."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response with invalid ARN
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator(
            [
                {
                    "serviceArns": [
                        "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/valid-service",
                        "invalid-arn-format",
                    ]
                }
            ]
        )
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_services("test-cluster")

        # Should only include the valid ARN
        assert len(result) == 1
        assert "valid-service" in result
        mock_ecs.get_paginator.assert_called_once_with("list_services")
        paginator.paginate.assert_called_once_with(cluster="test-cluster")

    @pytest.mark.anyio
    async def test_find_services_with_client_error(self, mock_aws_clients):
        """Test ClientError exception handling in find_services."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure get_paginator to raise a ClientError
        error_response = {
            "Error": {"Code": "ClusterNotFoundException", "Message": "Cluster not found"}
        }
        mock_ecs.get_paginator.side_effect = ClientError(error_response, "list_services")

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_services("nonexistent-cluster")

        # Should return empty list on ClientError
        assert result == []
        mock_ecs.get_paginator.assert_called_once_with("list_services")

    @pytest.mark.anyio
    async def test_find_services_with_general_exception(self, mock_aws_clients):
        """Test general exception handling in find_services."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure get_paginator to raise a general exception
        mock_ecs.get_paginator.side_effect = Exception("Test exception")

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_services("test-cluster")

        # Should return empty list on general exception
        assert result == []
        mock_ecs.get_paginator.assert_called_once_with("list_services")

    @pytest.mark.anyio
    async def test_find_services_with_pagination(self, mock_aws_clients):
        """Test pagination handling in find_services."""
        mock_ecs = mock_aws_clients["ecs"]

        # Set up paginator mock for multiple pages
        paginator = mock.Mock()
        paginator.paginate.return_value = AsyncIterator(
            [
                {
                    "serviceArns": [
                        "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/service-page1"
                    ]
                },
                {
                    "serviceArns": [
                        "arn:aws:ecs:us-west-2:123456789012:service/test-cluster/service-page2"
                    ]
                },
            ]
        )
        mock_ecs.get_paginator = mock.Mock(return_value=paginator)

        # Mock boto3.client to return our mock client
        with self.mock_aws_clients({"ecs": mock_ecs}):
            result = await find_services("test-cluster")

        # Should include results from all pages
        assert len(result) == 2
        assert "service-page1" in result
        assert "service-page2" in result
        mock_ecs.get_paginator.assert_called_once_with("list_services")
        paginator.paginate.assert_called_once_with(cluster="test-cluster")


class TestFindLoadBalancers(TestUtilsBase):
    """Test the find_load_balancers function in utils.py."""

    @pytest.mark.anyio
    async def test_find_load_balancers_success(self, mock_aws_clients):
        """Test successful retrieval of load balancers."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Mock service response
        mock_ecs.describe_services.return_value = {
            "services": [
                {
                    "loadBalancers": [
                        {
                            "targetGroupArn": (
                                "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/tg-1"
                            )
                        }
                    ]
                }
            ]
        }

        # Mock target group response
        mock_elbv2.describe_target_groups.return_value = {
            "TargetGroups": [
                {
                    "LoadBalancerArns": [
                        "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/lb-1"
                    ]
                }
            ]
        }

        # Mock load balancer response
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {
                    "LoadBalancerArn": (
                        "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/lb-1"
                    ),
                    "DNSName": "lb-1.us-west-2.elb.amazonaws.com",
                }
            ]
        }

        # Mock boto3.client to return appropriate clients
        def mock_client_factory(service_name, **kwargs):
            if service_name == "ecs":
                return mock_ecs
            elif service_name == "elbv2":
                return mock_elbv2

        with self.mock_aws_clients({"ecs": mock_ecs, "elbv2": mock_elbv2}):
            result = await find_load_balancers("test-cluster", "test-service")

        # Assert expected result
        assert len(result) == 1
        assert "DNSName" in result[0]
        assert result[0]["DNSName"] == "lb-1.us-west-2.elb.amazonaws.com"
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["test-service"]
        )
        mock_elbv2.describe_target_groups.assert_called_once_with(
            TargetGroupArns=["arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/tg-1"]
        )
        mock_elbv2.describe_load_balancers.assert_called_once()

    @pytest.mark.anyio
    async def test_find_load_balancers_service_not_found(self, mock_aws_clients):
        """Test when service is not found."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Mock empty service response
        mock_ecs.describe_services.return_value = {"services": []}

        # Mock boto3.client to return our mock clients
        with self.mock_aws_clients({"ecs": mock_ecs, "elbv2": mock_elbv2}):
            result = await find_load_balancers("test-cluster", "nonexistent-service")

        # Assert empty result
        assert result == []
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["nonexistent-service"]
        )
        mock_elbv2.describe_target_groups.assert_not_called()

    @pytest.mark.anyio
    async def test_find_load_balancers_no_load_balancers(self, mock_aws_clients):
        """Test when service has no load balancers."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Mock service response with no load balancers
        mock_ecs.describe_services.return_value = {"services": [{"loadBalancers": []}]}

        # Mock boto3.client to return appropriate clients
        def mock_client_factory(service_name, **kwargs):
            if service_name == "ecs":
                return mock_ecs
            elif service_name == "elbv2":
                return mock_elbv2

        with self.mock_aws_clients({"ecs": mock_ecs, "elbv2": mock_elbv2}):
            result = await find_load_balancers("test-cluster", "test-service")

        # Assert empty result
        assert result == []
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["test-service"]
        )
        mock_elbv2.describe_target_groups.assert_not_called()

    @pytest.mark.anyio
    async def test_find_load_balancers_no_target_groups(self, mock_aws_clients):
        """Test when load balancers have no target groups."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Mock service response with load balancers but no target group ARNs
        mock_ecs.describe_services.return_value = {
            "services": [
                {
                    "loadBalancers": [{}]  # No targetGroupArn key
                }
            ]
        }

        # Mock boto3.client to return appropriate clients
        def mock_client_factory(service_name, **kwargs):
            if service_name == "ecs":
                return mock_ecs
            elif service_name == "elbv2":
                return mock_elbv2

        with self.mock_aws_clients({"ecs": mock_ecs, "elbv2": mock_elbv2}):
            result = await find_load_balancers("test-cluster", "test-service")

        # Assert empty result
        assert result == []
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["test-service"]
        )
        mock_elbv2.describe_target_groups.assert_not_called()

    @pytest.mark.anyio
    async def test_find_load_balancers_target_group_not_found(self, mock_aws_clients):
        """Test when target group is not found."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Mock service response
        mock_ecs.describe_services.return_value = {
            "services": [
                {
                    "loadBalancers": [
                        {
                            "targetGroupArn": (
                                "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/tg-1"
                            )
                        }
                    ]
                }
            ]
        }

        # Mock empty target group response
        mock_elbv2.describe_target_groups.return_value = {"TargetGroups": []}

        # Mock boto3.client to return appropriate clients
        def mock_client_factory(service_name, **kwargs):
            if service_name == "ecs":
                return mock_ecs
            elif service_name == "elbv2":
                return mock_elbv2

        with mock.patch("boto3.client", side_effect=mock_client_factory):
            result = await find_load_balancers("test-cluster", "test-service")

        # Assert empty result
        assert result == []
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["test-service"]
        )
        mock_elbv2.describe_target_groups.assert_called_once_with(
            TargetGroupArns=["arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/tg-1"]
        )

    @pytest.mark.anyio
    async def test_find_load_balancers_with_client_error(self, mock_aws_clients):
        """Test ClientError exception handling."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Mock client error
        error_response = {
            "Error": {"Code": "ClusterNotFoundException", "Message": "Cluster not found"}
        }
        mock_ecs.describe_services.side_effect = ClientError(error_response, "DescribeServices")

        # Mock boto3.client to return our mock clients
        with self.mock_aws_clients({"ecs": mock_ecs, "elbv2": mock_elbv2}):
            result = await find_load_balancers("nonexistent-cluster", "test-service")

        # Assert empty result
        assert result == []
        mock_ecs.describe_services.assert_called_once_with(
            cluster="nonexistent-cluster", services=["test-service"]
        )

    @pytest.mark.anyio
    async def test_find_load_balancers_with_general_exception(self, mock_aws_clients):
        """Test general exception handling."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_elbv2 = mock_aws_clients["elbv2"]

        # Mock general exception
        mock_ecs.describe_services.side_effect = Exception("Test exception")

        # Mock boto3.client to return appropriate clients
        def mock_client_factory(service_name, **kwargs):
            if service_name == "ecs":
                return mock_ecs
            elif service_name == "elbv2":
                return mock_elbv2

        with self.mock_aws_clients({"ecs": mock_ecs, "elbv2": mock_elbv2}):
            result = await find_load_balancers("test-cluster", "test-service")

        # Assert empty result
        assert result == []
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["test-service"]
        )


class TestFindTaskDefinitions(TestUtilsBase):
    """Test the find_task_definitions function in utils.py."""

    @pytest.mark.anyio
    async def test_find_task_definitions_by_service(self, mock_aws_clients):
        """Test finding task definitions by service name."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock the helper function to verify it's called
        with mock.patch(
            "awslabs.ecs_mcp_server.api.troubleshooting_tools.utils._get_task_definition_by_service",
            return_value=[
                {
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    )
                }
            ],
        ) as mock_helper:
            # Mock boto3.client and call the function
            with self.mock_aws_clients({"ecs": mock_ecs}):
                result = await find_task_definitions(
                    cluster_name="test-cluster", service_name="test-service"
                )

            # Verify the helper was called with correct args
            mock_helper.assert_called_once_with("test-cluster", "test-service", mock_ecs)

            # Verify result
            assert len(result) == 1
            assert (
                result[0]["taskDefinitionArn"]
                == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
            )

    @pytest.mark.anyio
    async def test_find_task_definitions_by_task(self, mock_aws_clients):
        """Test finding task definitions by task ID."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock the helper function
        with mock.patch(
            "awslabs.ecs_mcp_server.api.troubleshooting_tools.utils._get_task_definition_by_task",
            return_value=[
                {
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    )
                }
            ],
        ) as mock_helper:
            # Mock boto3.client and call the function
            with self.mock_aws_clients({"ecs": mock_ecs}):
                result = await find_task_definitions(
                    cluster_name="test-cluster", task_id="task-123"
                )

            # Verify the helper was called with correct args
            mock_helper.assert_called_once_with("task-123", "test-cluster", mock_ecs)

            # Verify result
            assert len(result) == 1
            assert (
                result[0]["taskDefinitionArn"]
                == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
            )

    @pytest.mark.anyio
    async def test_find_task_definitions_by_stack(self, mock_aws_clients):
        """Test finding task definitions by stack name."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock the helper function
        with mock.patch(
            "awslabs.ecs_mcp_server.api.troubleshooting_tools.utils._get_task_definitions_by_stack",
            return_value=[
                {
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    )
                }
            ],
        ) as mock_helper:
            # Mock boto3.client and call the function
            with self.mock_aws_clients({"ecs": mock_ecs}):
                result = await find_task_definitions(stack_name="test-stack")

            # Verify the helper was called with correct args
            mock_helper.assert_called_once_with("test-stack", mock_ecs)

            # Verify result
            assert len(result) == 1
            assert (
                result[0]["taskDefinitionArn"]
                == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
            )

    @pytest.mark.anyio
    async def test_find_task_definitions_by_family_prefix(self, mock_aws_clients):
        """Test finding task definitions by family prefix."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock the helper function
        with mock.patch(
            "awslabs.ecs_mcp_server.api.troubleshooting_tools.utils._get_task_definitions_by_family_prefix",
            return_value=[
                {
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    )
                }
            ],
        ) as mock_helper:
            # Mock boto3.client and call the function
            with self.mock_aws_clients({"ecs": mock_ecs}):
                result = await find_task_definitions(family_prefix="test-app")

            # Verify the helper was called with correct args
            mock_helper.assert_called_once_with("test-app", mock_ecs)

            # Verify result
            assert len(result) == 1
            assert (
                result[0]["taskDefinitionArn"]
                == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
            )

    @pytest.mark.anyio
    async def test_find_task_definitions_missing_required_params(self, mock_aws_clients):
        """Test with missing required parameters."""

        # Call the function without any of the required parameters
        result = await find_task_definitions()

        # Should return empty list when missing required params
        assert result == []

    @pytest.mark.anyio
    async def test_find_task_definitions_with_exception(self, mock_aws_clients):
        """Test exception handling in find_task_definitions."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock the helper function to raise an exception
        with mock.patch(
            "awslabs.ecs_mcp_server.api.troubleshooting_tools.utils._get_task_definition_by_service",
            side_effect=Exception("Test exception"),
        ):
            # Mock boto3.client and call the function
            with self.mock_aws_clients({"ecs": mock_ecs}):
                result = await find_task_definitions(
                    cluster_name="test-cluster", service_name="test-service"
                )

            # Should return empty list on exception
            assert result == []


class TestGetTaskDefinitionByService(TestUtilsBase):
    """Test the _get_task_definition_by_service helper function."""

    @pytest.mark.anyio
    async def test_get_task_definition_by_service_success(self, mock_aws_clients):
        """Test successful retrieval of task definition by service."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock service response
        mock_ecs.describe_services.return_value = {
            "services": [
                {"taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"}
            ]
        }

        # Mock task definition response
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                ),
                "family": "test-app",
                "revision": 1,
            }
        }

        # Call the function
        result = await _get_task_definition_by_service("test-cluster", "test-service", mock_ecs)

        # Assert expected result
        assert len(result) == 1
        assert (
            result[0]["taskDefinitionArn"]
            == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )
        assert result[0]["family"] == "test-app"
        assert result[0]["revision"] == 1

        # Verify correct API calls
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["test-service"]
        )
        mock_ecs.describe_task_definition.assert_called_once_with(
            taskDefinition="arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )

    @pytest.mark.anyio
    async def test_get_task_definition_by_service_not_found(self, mock_aws_clients):
        """Test when service is not found."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock empty service response
        mock_ecs.describe_services.return_value = {"services": []}

        # Call the function
        result = await _get_task_definition_by_service(
            "test-cluster", "nonexistent-service", mock_ecs
        )

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["nonexistent-service"]
        )
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definition_by_service_no_task_definition(self, mock_aws_clients):
        """Test when service doesn't have task definition."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock service response without taskDefinition
        mock_ecs.describe_services.return_value = {
            "services": [{}]  # No taskDefinition key
        }

        # Call the function
        result = await _get_task_definition_by_service("test-cluster", "test-service", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["test-service"]
        )
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definition_by_service_client_error(self, mock_aws_clients):
        """Test ClientError handling."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock client error
        error_response = {
            "Error": {"Code": "ClusterNotFoundException", "Message": "Cluster not found"}
        }
        mock_ecs.describe_services.side_effect = ClientError(error_response, "DescribeServices")

        # Call the function
        result = await _get_task_definition_by_service(
            "nonexistent-cluster", "test-service", mock_ecs
        )

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.describe_services.assert_called_once_with(
            cluster="nonexistent-cluster", services=["test-service"]
        )
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definition_by_service_general_exception(self, mock_aws_clients):
        """Test general exception handling."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock general exception
        mock_ecs.describe_services.side_effect = Exception("Test exception")

        # Call the function
        result = await _get_task_definition_by_service("test-cluster", "test-service", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.describe_services.assert_called_once_with(
            cluster="test-cluster", services=["test-service"]
        )
        mock_ecs.describe_task_definition.assert_not_called()


class TestGetTaskDefinitionByTask(TestUtilsBase):
    """Test the _get_task_definition_by_task helper function."""

    @pytest.mark.anyio
    async def test_get_task_definition_by_task_success(self, mock_aws_clients):
        """Test successful retrieval of task definition by task ID."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock task response
        mock_ecs.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    )
                }
            ]
        }

        # Mock task definition response
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                ),
                "family": "test-app",
                "revision": 1,
            }
        }

        # Call the function
        result = await _get_task_definition_by_task("task-123", "test-cluster", mock_ecs)

        # Assert expected result
        assert len(result) == 1
        assert (
            result[0]["taskDefinitionArn"]
            == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )
        assert result[0]["family"] == "test-app"
        assert result[0]["revision"] == 1

        # Verify correct API calls
        mock_ecs.describe_tasks.assert_called_once_with(cluster="test-cluster", tasks=["task-123"])
        mock_ecs.describe_task_definition.assert_called_once_with(
            taskDefinition="arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )

    @pytest.mark.anyio
    async def test_get_task_definition_by_task_not_found(self, mock_aws_clients):
        """Test when task is not found."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock empty task response
        mock_ecs.describe_tasks.return_value = {"tasks": []}

        # Call the function
        result = await _get_task_definition_by_task("nonexistent-task", "test-cluster", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.describe_tasks.assert_called_once_with(
            cluster="test-cluster", tasks=["nonexistent-task"]
        )
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definition_by_task_no_arn(self, mock_aws_clients):
        """Test when task doesn't have task definition ARN."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock task response without taskDefinitionArn
        mock_ecs.describe_tasks.return_value = {
            "tasks": [{}]  # No taskDefinitionArn key
        }

        # Call the function
        result = await _get_task_definition_by_task("task-123", "test-cluster", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.describe_tasks.assert_called_once_with(cluster="test-cluster", tasks=["task-123"])
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definition_by_task_client_error(self, mock_aws_clients):
        """Test ClientError handling."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock client error
        error_response = {
            "Error": {"Code": "ClusterNotFoundException", "Message": "Cluster not found"}
        }
        mock_ecs.describe_tasks.side_effect = ClientError(error_response, "DescribeTasks")

        # Call the function
        result = await _get_task_definition_by_task("task-123", "nonexistent-cluster", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.describe_tasks.assert_called_once_with(
            cluster="nonexistent-cluster", tasks=["task-123"]
        )
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definition_by_task_general_exception(self, mock_aws_clients):
        """Test general exception handling."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock general exception
        mock_ecs.describe_tasks.side_effect = Exception("Test exception")

        # Call the function
        result = await _get_task_definition_by_task("task-123", "test-cluster", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.describe_tasks.assert_called_once_with(cluster="test-cluster", tasks=["task-123"])
        mock_ecs.describe_task_definition.assert_not_called()


class TestGetTaskDefinitionsByStack(TestUtilsBase):
    """Test the _get_task_definitions_by_stack helper function."""

    @pytest.mark.anyio
    async def test_get_task_definitions_by_stack_success(self, mock_aws_clients):
        """Test successful retrieval of task definitions by stack name."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Fix the CloudFormation mock properly
        mock_cfn.list_stack_resources = mock.MagicMock(
            return_value={
                "StackResourceSummaries": [
                    {
                        "ResourceType": "AWS::ECS::TaskDefinition",
                        "PhysicalResourceId": (
                            "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                        ),
                    },
                    {
                        "ResourceType": "AWS::ECS::Cluster",
                        "PhysicalResourceId": (
                            "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster"
                        ),
                    },
                ]
            }
        )

        # Mock task definition response
        mock_ecs.describe_task_definition.return_value = {
            "taskDefinition": {
                "taskDefinitionArn": (
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                ),
                "family": "test-app",
                "revision": 1,
            }
        }

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs, "cloudformation": mock_cfn}):
            result = await _get_task_definitions_by_stack("test-stack", mock_ecs)

        # Assert expected result
        assert len(result) == 1
        assert (
            result[0]["taskDefinitionArn"]
            == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )
        assert result[0]["family"] == "test-app"
        assert result[0]["revision"] == 1

        # Verify correct API calls
        mock_cfn.list_stack_resources.assert_called_once_with(StackName="test-stack")
        mock_ecs.describe_task_definition.assert_called_once_with(
            taskDefinition="arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )

    @pytest.mark.anyio
    async def test_get_task_definitions_by_stack_no_task_definitions(self, mock_aws_clients):
        """Test when no task definitions are found in the stack resources."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Configure CloudFormation mock with no task definitions
        mock_cfn.list_stack_resources.return_value = {
            "StackResourceSummaries": [
                {
                    "ResourceType": "AWS::ECS::Cluster",
                    "PhysicalResourceId": "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster",
                },
                {"ResourceType": "AWS::EC2::SecurityGroup", "PhysicalResourceId": "sg-12345"},
            ]
        }

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs, "cloudformation": mock_cfn}):
            result = await _get_task_definitions_by_stack("test-stack", mock_ecs)

        # Assert expected result
        assert len(result) == 0

        # Verify correct API calls
        mock_cfn.list_stack_resources.assert_called_once_with(StackName="test-stack")
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definitions_by_stack_empty_stack(self, mock_aws_clients):
        """Test when the stack has no resources."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Mock empty stack resources
        mock_cfn.list_stack_resources = mock.MagicMock(return_value={"StackResourceSummaries": []})

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs, "cloudformation": mock_cfn}):
            result = await _get_task_definitions_by_stack("test-stack", mock_ecs)

        # Assert expected result
        assert len(result) == 0

        # Verify correct API calls
        mock_cfn.list_stack_resources.assert_called_once_with(StackName="test-stack")
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definitions_by_stack_cloudformation_error(self, mock_aws_clients):
        """Test when CloudFormation client raises a ClientError."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Mock ClientError for list_stack_resources
        error_response = {"Error": {"Code": "ValidationError", "Message": "Stack does not exist"}}
        mock_cfn.list_stack_resources = mock.MagicMock(
            side_effect=ClientError(error_response, "ListStackResources")
        )

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs, "cloudformation": mock_cfn}):
            result = await _get_task_definitions_by_stack("test-stack", mock_ecs)

        # Assert expected result
        assert len(result) == 0

        # Verify correct API calls
        mock_cfn.list_stack_resources.assert_called_once_with(StackName="test-stack")
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definitions_by_stack_ecs_error(self, mock_aws_clients):
        """Test when ECS client raises a ClientError during task definition retrieval."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Mock stack resources with task definition
        mock_cfn.list_stack_resources = mock.MagicMock(
            return_value={
                "StackResourceSummaries": [
                    {
                        "ResourceType": "AWS::ECS::TaskDefinition",
                        "PhysicalResourceId": (
                            "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                        ),
                    }
                ]
            }
        )

        # Mock ClientError for describe_task_definition
        error_response = {
            "Error": {"Code": "ClientException", "Message": "Task definition not found"}
        }
        mock_ecs.describe_task_definition = mock.MagicMock(
            side_effect=ClientError(error_response, "DescribeTaskDefinition")
        )

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs, "cloudformation": mock_cfn}):
            result = await _get_task_definitions_by_stack("test-stack", mock_ecs)

        # Assert expected result
        assert len(result) == 0

        # Verify correct API calls
        mock_cfn.list_stack_resources.assert_called_once_with(StackName="test-stack")
        mock_ecs.describe_task_definition.assert_called_once_with(
            taskDefinition="arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )

    @pytest.mark.anyio
    async def test_get_task_definitions_by_stack_general_exception(self, mock_aws_clients):
        """Test when a general exception occurs."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Mock general exception
        mock_cfn.list_stack_resources = mock.MagicMock(side_effect=Exception("Unexpected error"))

        # Mock boto3.client and call the function
        with self.mock_aws_clients({"ecs": mock_ecs, "cloudformation": mock_cfn}):
            result = await _get_task_definitions_by_stack("test-stack", mock_ecs)

        # Assert expected result
        assert len(result) == 0

        # Verify correct API calls
        mock_cfn.list_stack_resources.assert_called_once_with(StackName="test-stack")
        mock_ecs.describe_task_definition.assert_not_called()


class TestGetTaskDefinitionsByFamilyPrefix(TestUtilsBase):
    """Test the _get_task_definitions_by_family_prefix helper function."""

    @pytest.mark.anyio
    async def test_get_task_definitions_by_family_prefix_success(self, mock_aws_clients):
        """Test successful retrieval of task definitions by family prefix."""
        mock_ecs = mock_aws_clients["ecs"]

        # Step 1: Mock list_task_definition_families response
        mock_ecs.list_task_definition_families.return_value = {
            "families": ["test-app", "test-app-2"]
        }

        # Step 2: Mock list_task_definitions responses for each family
        mock_ecs.list_task_definitions.side_effect = [
            {
                "taskDefinitionArns": [
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                ]
            },
            {
                "taskDefinitionArns": [
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app-2:1"
                ]
            },
        ]

        # Step 3: Mock describe_task_definition responses
        mock_ecs.describe_task_definition.side_effect = [
            {
                "taskDefinition": {
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                    ),
                    "family": "test-app",
                    "revision": 1,
                }
            },
            {
                "taskDefinition": {
                    "taskDefinitionArn": (
                        "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app-2:1"
                    ),
                    "family": "test-app-2",
                    "revision": 1,
                }
            },
        ]

        # Call the function
        result = await _get_task_definitions_by_family_prefix("test-app", mock_ecs)

        # Assert expected result
        assert len(result) == 2
        assert (
            result[0]["taskDefinitionArn"]
            == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )
        assert result[0]["family"] == "test-app"
        assert result[0]["revision"] == 1
        assert (
            result[1]["taskDefinitionArn"]
            == "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app-2:1"
        )
        assert result[1]["family"] == "test-app-2"
        assert result[1]["revision"] == 1

        # Verify correct API calls
        mock_ecs.list_task_definition_families.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE"
        )
        assert mock_ecs.list_task_definitions.call_count == 2
        mock_ecs.list_task_definitions.assert_any_call(
            familyPrefix="test-app", status="ACTIVE", sort="DESC", maxResults=1
        )
        mock_ecs.list_task_definitions.assert_any_call(
            familyPrefix="test-app-2", status="ACTIVE", sort="DESC", maxResults=1
        )
        assert mock_ecs.describe_task_definition.call_count == 2
        mock_ecs.describe_task_definition.assert_any_call(
            taskDefinition="arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )
        mock_ecs.describe_task_definition.assert_any_call(
            taskDefinition="arn:aws:ecs:us-west-2:123456789012:task-definition/test-app-2:1"
        )

    @pytest.mark.anyio
    async def test_get_task_definitions_by_family_prefix_empty_families(self, mock_aws_clients):
        """Test with empty families response."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure empty families response
        mock_ecs.list_task_definition_families = mock.MagicMock(return_value={"families": []})

        # Call the function
        result = await _get_task_definitions_by_family_prefix("nonexistent-prefix", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify correct API calls
        mock_ecs.list_task_definition_families.assert_called_once_with(
            familyPrefix="nonexistent-prefix", status="ACTIVE"
        )
        mock_ecs.list_task_definitions.assert_not_called()
        mock_ecs.describe_task_definition.assert_not_called()


class TestDetectCloudFormationStack(TestUtilsBase):
    """Test the detect_cloudformation_stack function in utils.py."""

    @pytest.mark.anyio
    async def test_detect_cloudformation_stack_success(self, mock_aws_clients):
        """Test successful CloudFormation stack detection."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Mock tags response
        mock_ecs.list_tags_for_resource.return_value = {
            "tags": [
                {"key": "aws:cloudformation:stack-name", "value": "test-stack"},
                {
                    "key": "aws:cloudformation:stack-id",
                    "value": "arn:aws:cloudformation:us-west-2:123456789012:stack/test-stack/12345",
                },
            ]
        }

        # Mock CloudFormation stack details
        mock_cfn.describe_stacks.return_value = {
            "Stacks": [
                {
                    "StackName": "test-stack",
                    "StackStatus": "CREATE_COMPLETE",
                    "CreationTime": "2023-01-01T00:00:00Z",
                    "LastUpdatedTime": "2023-01-01T01:00:00Z",
                }
            ]
        }

        # Mock boto3.client to return appropriate clients
        def mock_client_factory(service_name, **kwargs):
            if service_name == "ecs":
                return mock_ecs
            elif service_name == "cloudformation":
                return mock_cfn

        with self.mock_aws_clients({"ecs": mock_ecs, "cloudformation": mock_cfn}):
            result = await get_cloudformation_stack_if_exists(
                "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster"
            )

        # Verify CloudFormation stack is detected
        assert result is not None
        assert result["stack_name"] == "test-stack"
        assert result["stack_status"] == "CREATE_COMPLETE"
        assert "stack_id" in result
        assert "creation_time" in result

    @pytest.mark.anyio
    async def test_detect_cloudformation_stack_no_tags(self, mock_aws_clients):
        """Test when resource has no CloudFormation tags."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock empty tags response
        mock_ecs.list_tags_for_resource.return_value = {"tags": []}

        result = await get_cloudformation_stack_if_exists(
            "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster",
        )

        # Should return None when no CloudFormation tags found
        assert result is None

    @pytest.mark.anyio
    async def test_detect_cloudformation_stack_no_stack_name_tag(self, mock_aws_clients):
        """Test when resource has tags but no stack name tag."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock tags response without stack name
        mock_ecs.list_tags_for_resource.return_value = {
            "tags": [
                {"key": "Environment", "value": "production"},
                {"key": "Team", "value": "backend"},
            ]
        }

        result = await get_cloudformation_stack_if_exists(
            "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster",
        )

        # Should return None when no stack name tag found
        assert result is None

    @pytest.mark.anyio
    async def test_detect_cloudformation_stack_cfn_error(self, mock_aws_clients):
        """Test CloudFormation error during stack description."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Mock tags response
        mock_ecs.list_tags_for_resource.return_value = {
            "tags": [{"key": "aws:cloudformation:stack-name", "value": "test-stack"}]
        }

        # Mock CloudFormation error
        error_response = {"Error": {"Code": "ValidationError", "Message": "Stack not found"}}
        mock_cfn.describe_stacks.side_effect = ClientError(error_response, "DescribeStacks")

        # Mock boto3.client to return appropriate clients
        with self.mock_aws_clients({"ecs": mock_ecs, "cloudformation": mock_cfn}):
            result = await get_cloudformation_stack_if_exists(
                "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster"
            )

        # Should return error information
        assert result is not None
        assert result["stack_name"] == "test-stack"
        assert result["stack_status"] == "UNKNOWN"
        assert "error" in result

    @pytest.mark.anyio
    async def test_detect_cloudformation_stack_tags_error(self, mock_aws_clients):
        """Test error during tag listing."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock exception in tag listing
        mock_ecs.list_tags_for_resource.side_effect = Exception("Tag listing error")

        result = await get_cloudformation_stack_if_exists(
            "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster",
        )

        # Should return None when tag listing fails
        assert result is None

    @pytest.mark.anyio
    async def test_detect_cloudformation_stack_empty_stacks(self, mock_aws_clients):
        """Test when CloudFormation returns empty stacks."""
        mock_ecs = mock_aws_clients["ecs"]
        mock_cfn = mock_aws_clients["cloudformation"]

        # Mock tags response
        mock_ecs.list_tags_for_resource.return_value = {
            "tags": [{"key": "aws:cloudformation:stack-name", "value": "test-stack"}]
        }

        # Mock empty CloudFormation response
        mock_cfn.describe_stacks.return_value = {"Stacks": []}

        result = await get_cloudformation_stack_if_exists(
            "arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster",
        )

        # Should return None when no stacks found
        assert result is None

    @pytest.mark.anyio
    async def test_get_task_definitions_by_family_prefix_missing_key(self, mock_aws_clients):
        """Test with missing 'families' key in response."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure response without families key
        mock_ecs.list_task_definition_families = mock.MagicMock(return_value={})

        # Call the function
        result = await _get_task_definitions_by_family_prefix("test-app", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify correct API calls
        mock_ecs.list_task_definition_families.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE"
        )
        mock_ecs.list_task_definitions.assert_not_called()
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definitions_by_family_prefix_no_task_definitions(
        self, mock_aws_clients
    ):
        """Test when no task definitions are found for a family."""
        mock_ecs = mock_aws_clients["ecs"]

        # Step 1: Mock families response
        mock_ecs.list_task_definition_families = mock.MagicMock(
            return_value={"families": ["test-app"]}
        )

        # Step 2: Mock empty task definitions response
        mock_ecs.list_task_definitions.return_value = {"taskDefinitionArns": []}

        # Call the function
        result = await _get_task_definitions_by_family_prefix("test-app", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify correct API calls
        mock_ecs.list_task_definition_families.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE"
        )
        mock_ecs.list_task_definitions.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE", sort="DESC", maxResults=1
        )
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definitions_by_family_prefix_client_error_list_families(
        self, mock_aws_clients
    ):
        """Test ClientError when listing families."""
        mock_ecs = mock_aws_clients["ecs"]

        # Mock ClientError for list_task_definition_families
        error_response = {"Error": {"Code": "ClientException", "Message": "Error listing families"}}
        mock_ecs.list_task_definition_families = mock.MagicMock(
            side_effect=ClientError(error_response, "ListTaskDefinitionFamilies")
        )

        # Call the function
        result = await _get_task_definitions_by_family_prefix("test-app", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.list_task_definition_families.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE"
        )
        mock_ecs.list_task_definitions.assert_not_called()
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definitions_by_family_prefix_client_error_list_task_definitions(
        self, mock_aws_clients
    ):
        """Test ClientError when listing task definitions."""
        mock_ecs = mock_aws_clients["ecs"]

        # Step 1: Mock families response
        mock_ecs.list_task_definition_families = mock.MagicMock(
            return_value={"families": ["test-app"]}
        )

        # Step 2: Mock ClientError for list_task_definitions
        error_response = {
            "Error": {"Code": "ClientException", "Message": "Error listing task definitions"}
        }
        mock_ecs.list_task_definitions = mock.MagicMock(
            side_effect=ClientError(error_response, "ListTaskDefinitions")
        )

        # Call the function
        result = await _get_task_definitions_by_family_prefix("test-app", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.list_task_definition_families.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE"
        )
        mock_ecs.list_task_definitions.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE", sort="DESC", maxResults=1
        )
        mock_ecs.describe_task_definition.assert_not_called()

    @pytest.mark.anyio
    async def test_get_task_definitions_by_family_prefix_client_error_describe_task_definition(
        self, mock_aws_clients
    ):
        """Test ClientError when describing task definition."""
        mock_ecs = mock_aws_clients["ecs"]

        # Step 1: Mock families response
        mock_ecs.list_task_definition_families = mock.MagicMock(
            return_value={"families": ["test-app"]}
        )

        # Step 2: Mock list_task_definitions response
        mock_ecs.list_task_definitions = mock.MagicMock(
            return_value={
                "taskDefinitionArns": [
                    "arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
                ]
            }
        )

        # Step 3: Mock ClientError for describe_task_definition
        error_response = {
            "Error": {"Code": "ClientException", "Message": "Task definition not found"}
        }
        mock_ecs.describe_task_definition = mock.MagicMock(
            side_effect=ClientError(error_response, "DescribeTaskDefinition")
        )

        # Call the function
        result = await _get_task_definitions_by_family_prefix("test-app", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.list_task_definition_families.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE"
        )
        mock_ecs.list_task_definitions.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE", sort="DESC", maxResults=1
        )
        mock_ecs.describe_task_definition.assert_called_once_with(
            taskDefinition="arn:aws:ecs:us-west-2:123456789012:task-definition/test-app:1"
        )

    @pytest.mark.anyio
    async def test_get_task_definitions_by_family_prefix_general_exception(self, mock_aws_clients):
        """Test general exception handling."""
        mock_ecs = mock_aws_clients["ecs"]

        # Configure general exception
        mock_ecs.list_task_definition_families = mock.MagicMock(
            side_effect=Exception("Test exception")
        )

        # Call the function
        result = await _get_task_definitions_by_family_prefix("test-app", mock_ecs)

        # Assert empty result
        assert result == []

        # Verify API calls
        mock_ecs.list_task_definition_families.assert_called_once_with(
            familyPrefix="test-app", status="ACTIVE"
        )
        mock_ecs.list_task_definitions.assert_not_called()
        mock_ecs.describe_task_definition.assert_not_called()
