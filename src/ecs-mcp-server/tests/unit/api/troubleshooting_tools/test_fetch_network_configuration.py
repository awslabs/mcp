"""Tests for the fetch_network_configuration module."""

import sys
import unittest
from unittest.mock import AsyncMock, Mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
    discover_vpcs_from_cloudformation,
    discover_vpcs_from_clusters,
    discover_vpcs_from_loadbalancers,
    fetch_network_configuration,
    get_associated_target_groups,
    get_ec2_resource,
    get_elb_resources,
    get_network_data,
    handle_aws_api_call,
)
from tests.unit.utils.async_test_utils import AsyncIterator


class TestFetchNetworkConfiguration(unittest.IsolatedAsyncioTestCase):
    """Tests for fetch_network_configuration."""

    @pytest.mark.anyio
    async def test_fetch_network_configuration_calls_get_network_data(self):
        """Test that fetch_network_configuration calls get_network_data with correct params."""
        # Setup
        app_name = "test-app"
        vpc_id = "vpc-12345678"
        cluster_name = "test-cluster"

        # Create mocks
        mock_ec2 = AsyncMock()
        mock_ecs = AsyncMock()
        mock_elbv2 = AsyncMock()
        mock_cfn = AsyncMock()

        # Setup mock for get_network_data
        expected_result = {"status": "success", "data": {"app_name": app_name}}
        get_network_data_mock = AsyncMock(return_value=expected_result)

        # Need to patch
        # at the module level where fetch_network_configuration accesses get_network_data
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"

        # Extract the original functions to avoid the patching issue
        original_get_network_data = get_network_data

        try:
            module = sys.modules[module_name]
            module.get_network_data = get_network_data_mock

            # Call the function
            result = await fetch_network_configuration(
                app_name,
                vpc_id,
                cluster_name,
                ec2_client=mock_ec2,
                ecs_client=mock_ecs,
                elbv2_client=mock_elbv2,
                cfn_client=mock_cfn,
            )

            # Assertions
            get_network_data_mock.assert_called_once_with(
                app_name, vpc_id, cluster_name, mock_ec2, mock_ecs, mock_elbv2, mock_cfn
            )
            self.assertEqual(result, expected_result)
        finally:
            # Restore original function
            module.get_network_data = original_get_network_data

    @pytest.mark.anyio
    async def test_fetch_network_configuration_handles_exceptions(self):
        """Test that fetch_network_configuration handles exceptions properly."""
        # Setup
        app_name = "test-app"
        get_network_data_mock = AsyncMock(side_effect=Exception("Test exception"))

        # Need to patch at the module level
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"

        # Extract the original functions to avoid the patching issue
        original_get_network_data = get_network_data

        try:
            module = sys.modules[module_name]
            module.get_network_data = get_network_data_mock

            # Call the function
            result = await fetch_network_configuration(app_name)

            # Assertions
            get_network_data_mock.assert_called_once()
            self.assertEqual(result["status"], "error")
            self.assertIn("Internal error", result["error"])
            self.assertIn("Test exception", result["error"])
        finally:
            # Restore original function
            module.get_network_data = original_get_network_data

    @pytest.mark.anyio
    async def test_handle_aws_api_call_regular_function(self):
        """Test handle_aws_api_call with a regular function."""

        # Setup a regular function that returns a value
        def test_function(arg1, arg2):
            return f"{arg1}-{arg2}"

        # Call handle_aws_api_call with the regular function
        result = await handle_aws_api_call(test_function, None, "value1", "value2")

        # Verify the result
        self.assertEqual(result, "value1-value2")

    @pytest.mark.anyio
    async def test_handle_aws_api_call_coroutine(self):
        """Test handle_aws_api_call with a coroutine."""

        # Setup an async function
        async def test_async_function(arg1, arg2):
            return f"{arg1}-{arg2}"

        # Call handle_aws_api_call with the async function
        result = await handle_aws_api_call(test_async_function, None, "value1", "value2")

        # Verify the result
        self.assertEqual(result, "value1-value2")

    @pytest.mark.anyio
    async def test_handle_aws_api_call_client_error(self):
        """Test handle_aws_api_call handling of ClientError."""

        # Setup a function that raises ClientError
        def test_function(*args, **kwargs):
            error = ClientError(
                {"Error": {"Code": "TestError", "Message": "Test client error"}}, "operation_name"
            )
            raise error

        # Set up an error_value dict
        error_value = {"result": "error"}

        # Call handle_aws_api_call with the function that raises ClientError
        result = await handle_aws_api_call(test_function, error_value)

        # Verify the result includes the error information
        self.assertEqual(result["result"], "error")
        self.assertIn("error", result)
        self.assertIn("Test client error", result["error"])

    @pytest.mark.anyio
    async def test_handle_aws_api_call_general_exception(self):
        """Test handle_aws_api_call handling of general exceptions."""

        # Setup a function that raises a general exception
        def test_function(*args, **kwargs):
            raise ValueError("Test general error")

        # Set up an error_value dict
        error_value = {"result": "error"}

        # Call handle_aws_api_call with the function that raises an exception
        result = await handle_aws_api_call(test_function, error_value)

        # Verify the result includes the error information
        self.assertEqual(result["result"], "error")
        self.assertIn("error", result)
        self.assertIn("Test general error", result["error"])

    async def test_get_network_data_happy_path(self):
        """Test the happy path of get_network_data."""
        # Configure mocks for different AWS services
        mock_ec2 = AsyncMock()
        mock_ecs = AsyncMock()
        mock_elbv2 = AsyncMock()
        mock_cfn = AsyncMock()

        # Set up proper pagination for CloudFormation
        mock_paginator = Mock()  # Use regular Mock, not AsyncMock
        mock_paginator.paginate.return_value = AsyncIterator([{"StackSummaries": []}])
        mock_cfn.get_paginator.return_value = mock_paginator

        # Mock specific responses with awaitable results
        mock_ec2.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-12345678"}]}
        mock_ecs.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-west-2:123456789012:cluster/test-cluster"]
        }
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}

        # Call the function with specific VPC ID and inject our mocks
        result = await get_network_data(
            "test-app",
            "vpc-12345678",
            ec2_client=mock_ec2,
            ecs_client=mock_ecs,
            elbv2_client=mock_elbv2,
            cfn_client=mock_cfn,
        )

        # Verify result structure
        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertIn("timestamp", result["data"])
        self.assertIn("app_name", result["data"])
        self.assertIn("vpc_ids", result["data"])
        self.assertIn("raw_resources", result["data"])
        self.assertIn("analysis_guide", result["data"])

        # Verify VPC ID was used
        self.assertEqual(result["data"]["vpc_ids"], ["vpc-12345678"])

    async def test_get_network_data_no_vpc(self):
        """Test get_network_data when no VPC is found."""
        # Configure mocks for different AWS services
        mock_ec2 = AsyncMock()
        mock_ecs = AsyncMock()
        mock_elbv2 = AsyncMock()
        mock_cfn = AsyncMock()

        # Set up proper pagination for CloudFormation
        mock_paginator = Mock()  # Use regular Mock, not AsyncMock
        mock_paginator.paginate.return_value = AsyncIterator([{"StackSummaries": []}])
        mock_cfn.get_paginator.return_value = mock_paginator

        # Mock empty responses for VPC discovery
        mock_ecs.list_clusters.return_value = {"clusterArns": []}
        mock_ecs.list_tasks.return_value = {"taskArns": []}
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
        mock_ec2.describe_vpcs.return_value = {"Vpcs": []}

        # Call the function with our injected mocks
        result = await get_network_data(
            "test-app-no-vpc",
            ec2_client=mock_ec2,
            ecs_client=mock_ecs,
            elbv2_client=mock_elbv2,
            cfn_client=mock_cfn,
        )

        # Verify result
        self.assertEqual(result["status"], "warning")
        self.assertIn("No VPC found", result["message"])

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters(self):
        """Test VPC discovery from ECS clusters."""
        # We need to mock both ECS and EC2 clients and their responses
        mock_ecs = AsyncMock()
        mock_ec2 = AsyncMock()

        # Setup the clients
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"

        # Mock get_aws_client to return our mocks
        original_get_aws_client = sys.modules[module_name].get_aws_client

        # Mock response for tasks with network interfaces
        task_response = {
            "tasks": [
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [{"name": "networkInterfaceId", "value": "eni-12345678"}],
                        }
                    ]
                }
            ]
        }

        # Mock response for ENIs with VPC IDs
        eni_response = {"NetworkInterfaces": [{"VpcId": "vpc-12345678"}]}

        try:
            # Replace get_aws_client with a function that returns our mocks
            async def mock_get_aws_client(service_name):
                if service_name == "ecs":
                    return mock_ecs
                elif service_name == "ec2":
                    return mock_ec2
                return AsyncMock()

            sys.modules[module_name].get_aws_client = mock_get_aws_client

            # Configure mock responses
            mock_ecs.list_tasks = AsyncMock(
                return_value={"taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/cluster/task1"]}
            )
            mock_ecs.describe_tasks = AsyncMock(return_value=task_response)
            mock_ec2.describe_network_interfaces = AsyncMock(return_value=eni_response)

            # Call the function
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            # Verify the results
            self.assertEqual(vpc_ids, ["vpc-12345678"])

            # Verify the mocks were called correctly
            mock_ecs.list_tasks.assert_called_once_with(cluster="test-cluster")
            mock_ecs.describe_tasks.assert_called_once()
            mock_ec2.describe_network_interfaces.assert_called_once_with(
                NetworkInterfaceIds=["eni-12345678"]
            )
        finally:
            # Restore original function
            sys.modules[module_name].get_aws_client = original_get_aws_client

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters_no_tasks(self):
        """Test VPC discovery when no tasks are found."""
        # We need to mock both ECS and EC2 clients and their responses
        mock_ecs = AsyncMock()

        # Setup the clients
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"

        # Mock get_aws_client to return our mocks
        original_get_aws_client = sys.modules[module_name].get_aws_client

        try:
            # Replace get_aws_client with a function that returns our mocks
            async def mock_get_aws_client(service_name):
                if service_name == "ecs":
                    return mock_ecs
                return AsyncMock()

            sys.modules[module_name].get_aws_client = mock_get_aws_client

            # Configure mock responses - no tasks returned
            mock_ecs.list_tasks = AsyncMock(return_value={"taskArns": []})

            # Call the function
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            # Verify the results - should be empty list
            self.assertEqual(vpc_ids, [])

            # Verify the mocks were called correctly
            mock_ecs.list_tasks.assert_called_once_with(cluster="test-cluster")
            mock_ecs.describe_tasks.assert_not_called()
        finally:
            # Restore original function
            sys.modules[module_name].get_aws_client = original_get_aws_client

    @pytest.mark.anyio
    async def test_discover_vpcs_from_loadbalancers(self):
        """Test VPC discovery from load balancers."""
        # Setup mock ELBv2 client
        mock_elbv2 = AsyncMock()

        # Setup the clients
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"

        # Mock get_aws_client to return our mocks
        original_get_aws_client = sys.modules[module_name].get_aws_client

        # Mock response for load balancers with app name in load balancer name
        lb_arns = [
            (
                "arn:aws:elasticloadbalancing:us-west-2:"
                "123456789012:loadbalancer/app/test-app-lb/1234567890"
            ),
            (
                "arn:aws:elasticloadbalancing:us-west-2:"
                "123456789012:loadbalancer/app/other-lb/0987654321"
            ),
        ]
        lb_response = {
            "LoadBalancers": [
                {
                    "LoadBalancerName": "test-app-lb",
                    "LoadBalancerArn": lb_arns[0],
                    "VpcId": "vpc-12345678",
                },
                {
                    "LoadBalancerName": "other-lb",
                    "LoadBalancerArn": lb_arns[1],
                    "VpcId": "vpc-87654321",
                },
            ]
        }

        try:
            # Replace get_aws_client with a function that returns our mocks
            async def mock_get_aws_client(service_name):
                if service_name == "elbv2":
                    return mock_elbv2
                return AsyncMock()

            sys.modules[module_name].get_aws_client = mock_get_aws_client

            # Configure mock responses
            mock_elbv2.describe_load_balancers = AsyncMock(return_value=lb_response)

            # Call the function
            vpc_ids = await discover_vpcs_from_loadbalancers("test-app")

            # Verify the results - should include only the matching load balancer's VPC
            self.assertEqual(vpc_ids, ["vpc-12345678"])

            # Verify the mocks were called correctly
            mock_elbv2.describe_load_balancers.assert_called_once()
        finally:
            # Restore original function
            sys.modules[module_name].get_aws_client = original_get_aws_client

    @pytest.mark.anyio
    async def test_discover_vpcs_from_loadbalancers_with_tags(self):
        """Test VPC discovery from load balancers with name in tags."""
        # Setup mock ELBv2 client
        mock_elbv2 = AsyncMock()

        # Setup the clients
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"

        # Mock get_aws_client to return our mocks
        original_get_aws_client = sys.modules[module_name].get_aws_client

        # Mock response for load balancers
        lb_arn = (
            "arn:aws:elasticloadbalancing:us-west-2:"
            "123456789012:loadbalancer/app/generic-lb/1234567890"
        )
        lb_response = {
            "LoadBalancers": [
                {
                    "LoadBalancerName": "generic-lb",
                    "LoadBalancerArn": lb_arn,
                    "VpcId": "vpc-12345678",
                }
            ]
        }

        # Mock response for tags
        tags_response = {
            "TagDescriptions": [
                {
                    "ResourceArn": lb_arn,
                    "Tags": [{"Key": "Name", "Value": "test-app-environment"}],
                }
            ]
        }

        try:
            # Replace get_aws_client with a function that returns our mocks
            async def mock_get_aws_client(service_name):
                if service_name == "elbv2":
                    return mock_elbv2
                return AsyncMock()

            sys.modules[module_name].get_aws_client = mock_get_aws_client

            # Configure mock responses
            mock_elbv2.describe_load_balancers = AsyncMock(return_value=lb_response)
            mock_elbv2.describe_tags = AsyncMock(return_value=tags_response)

            # Call the function
            vpc_ids = await discover_vpcs_from_loadbalancers("test-app")

            # Verify the results - should include the VPC from the tagged load balancer
            self.assertEqual(vpc_ids, ["vpc-12345678"])

            # Verify the mocks were called correctly
            mock_elbv2.describe_load_balancers.assert_called_once()
            mock_elbv2.describe_tags.assert_called_once()
        finally:
            # Restore original function
            sys.modules[module_name].get_aws_client = original_get_aws_client

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation(self):
        """Test VPC discovery from CloudFormation stacks."""
        # Setup mock CloudFormation client
        mock_cfn = AsyncMock()

        # Setup the clients
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"

        # Mock get_aws_client to return our mocks
        original_get_aws_client = sys.modules[module_name].get_aws_client

        # Mock response for stack list
        stacks_response = {
            "StackSummaries": [{"StackName": "test-app-stack", "StackStatus": "CREATE_COMPLETE"}]
        }

        # Mock response for stack resources
        resources_response = {
            "StackResourceSummaries": [
                {"ResourceType": "AWS::EC2::VPC", "PhysicalResourceId": "vpc-12345678"}
            ]
        }

        try:
            # Replace get_aws_client with a function that returns our mocks
            async def mock_get_aws_client(service_name):
                if service_name == "cloudformation":
                    return mock_cfn
                return AsyncMock()

            sys.modules[module_name].get_aws_client = mock_get_aws_client

            # Configure mock responses
            mock_cfn.list_stacks = AsyncMock(return_value=stacks_response)
            mock_cfn.list_stack_resources = AsyncMock(return_value=resources_response)

            # Call the function
            vpc_ids = await discover_vpcs_from_cloudformation("test-app")

            # Verify the results
            self.assertEqual(vpc_ids, ["vpc-12345678"])

            # Verify the mocks were called correctly
            mock_cfn.list_stacks.assert_called_once()
            mock_cfn.list_stack_resources.assert_called_once_with(StackName="test-app-stack")
        finally:
            # Restore original function
            sys.modules[module_name].get_aws_client = original_get_aws_client

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation_pagination(self):
        """Test VPC discovery with CloudFormation pagination."""
        # Setup mock CloudFormation client
        mock_cfn = AsyncMock()

        # Setup the clients
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"

        # Mock get_aws_client to return our mocks
        original_get_aws_client = sys.modules[module_name].get_aws_client

        # Mock response for first page of stacks
        stacks_response1 = {
            "StackSummaries": [{"StackName": "test-app-stack1", "StackStatus": "CREATE_COMPLETE"}],
            "NextToken": "page2",
        }

        # Mock response for second page of stacks
        stacks_response2 = {
            "StackSummaries": [{"StackName": "test-app-stack2", "StackStatus": "CREATE_COMPLETE"}]
        }

        # Mock responses for stack resources
        resources_response1 = {
            "StackResourceSummaries": [
                {"ResourceType": "AWS::EC2::VPC", "PhysicalResourceId": "vpc-12345678"}
            ]
        }

        resources_response2 = {
            "StackResourceSummaries": [
                {"ResourceType": "AWS::EC2::VPC", "PhysicalResourceId": "vpc-87654321"}
            ]
        }

        try:
            # Replace get_aws_client with a function that returns our mocks
            async def mock_get_aws_client(service_name):
                if service_name == "cloudformation":
                    return mock_cfn
                return AsyncMock()

            sys.modules[module_name].get_aws_client = mock_get_aws_client

            # Configure mock responses with pagination
            mock_cfn.list_stacks = AsyncMock()
            mock_cfn.list_stacks.side_effect = [stacks_response1, stacks_response2]

            # Configure mock responses for stack resources
            mock_cfn.list_stack_resources = AsyncMock()
            mock_cfn.list_stack_resources.side_effect = (
                lambda StackName, **kwargs: resources_response1
                if StackName == "test-app-stack1"
                else resources_response2
            )

            # Call the function
            vpc_ids = await discover_vpcs_from_cloudformation("test-app")

            # Verify the results - should have both VPCs
            self.assertEqual(set(vpc_ids), {"vpc-12345678", "vpc-87654321"})

            # Verify the mocks were called correctly
            self.assertEqual(mock_cfn.list_stacks.call_count, 2)
            self.assertEqual(mock_cfn.list_stack_resources.call_count, 2)
        finally:
            # Restore original function
            sys.modules[module_name].get_aws_client = original_get_aws_client
            self.assertEqual(mock_cfn.list_stack_resources.call_count, 2)

    async def test_get_ec2_resource_with_filters(self):
        """Test EC2 resource retrieval with VPC filtering."""
        mock_ec2 = AsyncMock()

        vpc_ids = ["vpc-12345678"]

        # Test describe_subnets with VPC filter
        await get_ec2_resource(mock_ec2, "describe_subnets", vpc_ids)
        mock_ec2.describe_subnets.assert_called_once_with(
            Filters=[{"Name": "vpc-id", "Values": vpc_ids}]
        )

        # Reset mock
        mock_ec2.reset_mock()

        # Test describe_vpcs with VpcIds parameter
        await get_ec2_resource(mock_ec2, "describe_vpcs", vpc_ids)
        mock_ec2.describe_vpcs.assert_called_once_with(VpcIds=vpc_ids)

    async def test_get_ec2_resource_handles_errors(self):
        """Test EC2 resource retrieval handles errors gracefully."""
        mock_ec2 = AsyncMock()

        # Configure mock to raise exception
        mock_ec2.describe_subnets.side_effect = Exception("API Error")

        # Call function
        result = await get_ec2_resource(mock_ec2, "describe_subnets")

        # Verify error is returned but doesn't raise exception
        self.assertIn("error", result)
        # The error message format was updated in the implementation
        self.assertEqual(result["error"], "API Error")

    async def test_get_elb_resources_with_vpc_filter(self):
        """Test ELB resource retrieval with VPC filtering."""
        mock_elbv2 = AsyncMock()

        # Configure mock response
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {"LoadBalancerArn": "arn1", "VpcId": "vpc-12345678"},
                {"LoadBalancerArn": "arn2", "VpcId": "vpc-87654321"},
            ]
        }

        # Call function with VPC filter
        result = await get_elb_resources(mock_elbv2, "describe_load_balancers", ["vpc-12345678"])

        # Verify result contains only matching VPC
        self.assertEqual(len(result["LoadBalancers"]), 1)
        self.assertEqual(result["LoadBalancers"][0]["VpcId"], "vpc-12345678")

    async def test_get_associated_target_groups(self):
        """Test target group retrieval and health checking."""
        mock_elbv2 = AsyncMock()

        # Configure mock responses
        tg_arn = (
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-app-tg/1234567890"
        )
        other_tg_arn = (
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/other-tg/0987654321"
        )

        mock_elbv2.describe_target_groups.return_value = {
            "TargetGroups": [
                {
                    "TargetGroupArn": tg_arn,
                    "TargetGroupName": "test-app-tg",
                    "VpcId": "vpc-12345678",
                },
                {
                    "TargetGroupArn": other_tg_arn,
                    "TargetGroupName": "other-tg",
                    "VpcId": "vpc-12345678",
                },
            ]
        }

        mock_elbv2.describe_target_health.return_value = {
            "TargetHealthDescriptions": [
                {"Target": {"Id": "i-12345678", "Port": 80}, "TargetHealth": {"State": "healthy"}}
            ]
        }

        # Call function
        result = await get_associated_target_groups(mock_elbv2, "test-app", ["vpc-12345678"])

        # Verify name filtering
        self.assertEqual(len(result["TargetGroups"]), 1)
        self.assertEqual(result["TargetGroups"][0]["TargetGroupName"], "test-app-tg")

        # Verify health was checked
        self.assertIn("TargetHealth", result)
        self.assertIn(tg_arn, result["TargetHealth"])

    def test_generate_analysis_guide(self):
        """Test that analysis guide is generated with the expected structure."""
        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            generate_analysis_guide,
        )

        # Get guide
        guide = generate_analysis_guide()

        # Verify structure
        self.assertIn("common_issues", guide)
        self.assertIn("resource_relationships", guide)

        # Check common_issues
        self.assertTrue(isinstance(guide["common_issues"], list))
        self.assertTrue(len(guide["common_issues"]) > 0)

        # Check resource_relationships
        self.assertTrue(isinstance(guide["resource_relationships"], list))
        self.assertTrue(len(guide["resource_relationships"]) > 0)

        # Check format of first issue
        first_issue = guide["common_issues"][0]
        self.assertIn("issue", first_issue)
        self.assertIn("description", first_issue)
        self.assertIn("checks", first_issue)

    @pytest.mark.anyio
    async def test_get_clusters_info(self):
        """Test the get_clusters_info function."""
        # Setup mock ECS client
        mock_ecs = AsyncMock()

        # Setup the expected response
        expected_response = {
            "clusters": [
                {"clusterName": "test-cluster", "status": "ACTIVE", "runningTasksCount": 5}
            ],
            "failures": [],
        }

        # Configure mock responses
        mock_ecs.describe_clusters = AsyncMock(return_value=expected_response)

        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            get_clusters_info,
        )

        # Call the function
        result = await get_clusters_info(mock_ecs, ["test-cluster"])

        # Verify the results
        self.assertEqual(result, expected_response)

        # Verify the mock was called correctly
        mock_ecs.describe_clusters.assert_called_once_with(clusters=["test-cluster"])

    @pytest.mark.anyio
    async def test_get_clusters_info_empty(self):
        """Test the get_clusters_info function with empty clusters list."""
        # Setup mock ECS client
        mock_ecs = AsyncMock()

        # Call the function with empty clusters list
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            get_clusters_info,
        )

        # Call the function
        result = await get_clusters_info(mock_ecs, [])

        # Verify the results - should be empty dict
        self.assertEqual(result, {})

        # Verify describe_clusters was not called
        mock_ecs.describe_clusters.assert_not_called()

    @pytest.mark.anyio
    async def test_get_clusters_info_error(self):
        """Test the get_clusters_info function with error."""
        # Setup mock ECS client
        mock_ecs = AsyncMock()

        # Configure mock to raise exception
        mock_ecs.describe_clusters = AsyncMock(side_effect=Exception("API error"))

        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            get_clusters_info,
        )

        # Call the function
        result = await get_clusters_info(mock_ecs, ["test-cluster"])

        # Verify the results - the function returns {"clusters": [], "failures": []} on error
        self.assertEqual(result, {"clusters": [], "failures": []})

    @pytest.mark.anyio
    async def test_get_associated_target_groups_empty_response(self):
        """Test get_associated_target_groups with an empty response."""
        # Setup mock ELBv2 client
        mock_elbv2 = AsyncMock()

        # Configure describe_target_groups to return empty list
        mock_elbv2.describe_target_groups = AsyncMock(return_value={"TargetGroups": []})

        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            get_associated_target_groups,
        )

        # Call the function
        result = await get_associated_target_groups(mock_elbv2, "test-app", ["vpc-12345678"])

        # Verify results
        self.assertEqual(result["TargetGroups"], [])
        self.assertEqual(result["TargetHealth"], {})

        # Verify describe_target_health was not called (as there are no target groups)
        mock_elbv2.describe_target_health.assert_not_called()

    @pytest.mark.anyio
    async def test_get_associated_target_groups_error_in_health(self):
        """Test get_associated_target_groups with an error when getting target health."""
        # Setup mock ELBv2 client
        mock_elbv2 = AsyncMock()

        # Configure describe_target_groups to return a target group
        mock_elbv2.describe_target_groups = AsyncMock(
            return_value={
                "TargetGroups": [
                    {
                        "TargetGroupArn": (
                            "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
                            "targetgroup/test-tg/1234567890"
                        ),
                        "TargetGroupName": "test-app-tg",
                        "VpcId": "vpc-12345678",
                    }
                ]
            }
        )

        # Configure describe_target_health to raise exception
        mock_elbv2.describe_target_health = AsyncMock(side_effect=Exception("API error"))

        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            get_associated_target_groups,
        )

        # Call the function
        result = await get_associated_target_groups(mock_elbv2, "test-app", ["vpc-12345678"])

        # Verify target group was returned
        self.assertEqual(len(result["TargetGroups"]), 1)
        tg_arn = (
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-tg/1234567890"
        )

        # Based on the actual implementation, the function may add an empty list for target health
        # rather than adding an error key
        self.assertIn(tg_arn, result["TargetHealth"])

    @pytest.mark.anyio
    async def test_get_associated_target_groups_null_target_group(self):
        """Test get_associated_target_groups with a None/null target group in the list."""
        # Setup mock ELBv2 client
        mock_elbv2 = AsyncMock()

        # Configure describe_target_groups to return a target group and a None value
        mock_elbv2.describe_target_groups = AsyncMock(
            return_value={
                "TargetGroups": [
                    None,  # This tests the None check in the function
                    {
                        "TargetGroupArn": (
                            "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
                            "targetgroup/test-tg/1234567890"
                        ),
                        "TargetGroupName": "test-app-tg",
                        "VpcId": "vpc-12345678",
                    },
                ]
            }
        )

        # Configure describe_target_health to return health info
        mock_elbv2.describe_target_health = AsyncMock(return_value={"TargetHealthDescriptions": []})

        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            get_associated_target_groups,
        )

        # Call the function
        result = await get_associated_target_groups(mock_elbv2, "test-app", ["vpc-12345678"])

        # Verify only the valid target group was processed
        self.assertEqual(len(result["TargetGroups"]), 1)

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation_error(self):
        """Test discover_vpcs_from_cloudformation with an API error."""
        app_name = "test-app"

        # Create a mock CloudFormation client
        mock_cfn = AsyncMock()

        # Set up list_stacks to raise a ClientError
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_cfn.list_stacks.side_effect = ClientError(error_response, "ListStacks")

        # Mock get_aws_client to return our mock_cfn
        module_name = "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"
        original_get_aws_client = sys.modules[module_name].get_aws_client

        try:
            # Replace get_aws_client to return our mock_cfn
            async def mock_get_aws_client(service_name):
                if service_name == "cloudformation":
                    return mock_cfn
                return AsyncMock()

            sys.modules[module_name].get_aws_client = mock_get_aws_client

            # Call discover_vpcs_from_cloudformation
            vpc_ids = await discover_vpcs_from_cloudformation(app_name)

            # Verify list_stacks was called
            mock_cfn.list_stacks.assert_called_once()

            # Verify an empty list is returned when an error occurs
            self.assertEqual(vpc_ids, [])

        finally:
            # Restore original function
            sys.modules[module_name].get_aws_client = original_get_aws_client
