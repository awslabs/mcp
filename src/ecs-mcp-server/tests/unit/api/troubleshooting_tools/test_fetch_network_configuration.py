"""Tests for the fetch_network_configuration module."""

import sys
import unittest
from unittest import mock
from unittest.mock import MagicMock

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


class TestFetchNetworkConfigurationBase:
    """Base class for network configuration tests."""

    def setup_method(self, method):
        """Clear AWS client cache before each test."""
        from awslabs.ecs_mcp_server.utils.aws import _aws_clients

        _aws_clients.clear()

    def mock_aws_clients(self, mock_clients):
        """Create a mock for boto3.client that returns specified clients."""

        def mock_client_factory(service_name, **kwargs):
            return mock_clients.get(service_name, MagicMock())

        return mock.patch("boto3.client", side_effect=mock_client_factory)


class TestFetchNetworkConfiguration(
    TestFetchNetworkConfigurationBase, unittest.IsolatedAsyncioTestCase
):
    """Tests for fetch_network_configuration."""

    @pytest.mark.anyio
    async def test_fetch_network_configuration_calls_get_network_data(self):
        """Test that fetch_network_configuration calls get_network_data with correct params."""
        # Setup
        vpc_id = "vpc-12345678"
        cluster_name = "test-cluster"

        # Setup mock for get_network_data
        expected_result = {"status": "success", "data": {"vpc_ids": [vpc_id]}}

        # Use mock.patch to patch get_network_data at module level
        with mock.patch.object(
            sys.modules[
                "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"
            ],
            "get_network_data",
        ) as mock_get_network_data:
            mock_get_network_data.return_value = expected_result

            # Call the function (no client parameters)
            result = await fetch_network_configuration(vpc_id, cluster_name)

            # Assertions
            mock_get_network_data.assert_called_once_with(vpc_id, cluster_name)
            self.assertEqual(result, expected_result)

    @pytest.mark.anyio
    async def test_fetch_network_configuration_handles_exceptions(self):
        """Test that fetch_network_configuration handles exceptions properly."""
        with mock.patch.object(
            sys.modules[
                "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"
            ],
            "get_network_data",
        ) as mock_get_network_data:
            mock_get_network_data.side_effect = Exception("Test exception")

            result = await fetch_network_configuration()

            mock_get_network_data.assert_called_once_with(None, None)
            self.assertEqual(result["status"], "error")
            self.assertIn("Internal error", result["error"])
            self.assertIn("Test exception", result["error"])

    def test_handle_aws_api_call_regular_function(self):
        """Test handle_aws_api_call with a regular function."""

        # Setup a regular function that returns a value
        def test_function(arg1, arg2):
            return f"{arg1}-{arg2}"

        # Call handle_aws_api_call with the regular function (now synchronous)
        result = handle_aws_api_call(test_function, None, "value1", "value2")

        # Verify the result
        self.assertEqual(result, "value1-value2")

    def test_handle_aws_api_call_coroutine(self):
        """Test handle_aws_api_call with a regular function (no longer supports coroutines)."""

        # Setup a regular function
        def test_function(arg1, arg2):
            return f"{arg1}-{arg2}"

        # Call handle_aws_api_call with the function (now synchronous)
        result = handle_aws_api_call(test_function, None, "value1", "value2")

        # Verify the result
        self.assertEqual(result, "value1-value2")

    def test_handle_aws_api_call_client_error(self):
        """Test handle_aws_api_call handling of ClientError."""

        # Setup a function that raises ClientError
        def test_function(*args, **kwargs):
            error = ClientError(
                {"Error": {"Code": "TestError", "Message": "Test client error"}}, "operation_name"
            )
            raise error

        # Set up an error_value dict
        error_value = {"result": "error"}

        # Call handle_aws_api_call with the function that raises ClientError (now synchronous)
        result = handle_aws_api_call(test_function, error_value)

        # Verify the result includes the error information
        self.assertEqual(result["result"], "error")
        self.assertIn("error", result)
        self.assertIn("Test client error", result["error"])

    def test_handle_aws_api_call_general_exception(self):
        """Test handle_aws_api_call handling of general exceptions."""

        # Setup a function that raises a general exception
        def test_function(*args, **kwargs):
            raise ValueError("Test general error")

        # Set up an error_value dict
        error_value = {"result": "error"}

        # Call handle_aws_api_call with the function that raises an exception (now synchronous)
        result = handle_aws_api_call(test_function, error_value)

        # Verify the result includes the error information
        self.assertEqual(result["result"], "error")
        self.assertIn("error", result)
        self.assertIn("Test general error", result["error"])

    async def test_get_network_data_happy_path(self):
        """Test the happy path of get_network_data."""
        # Configure mock clients
        mock_ec2 = MagicMock()
        mock_ecs = MagicMock()
        mock_elbv2 = MagicMock()
        mock_cfn = MagicMock()

        # Mock specific responses
        mock_ec2.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-12345678"}]}
        mock_ec2.describe_subnets.return_value = {"Subnets": []}
        mock_ec2.describe_security_groups.return_value = {"SecurityGroups": []}
        mock_ec2.describe_route_tables.return_value = {"RouteTables": []}
        mock_ec2.describe_network_interfaces.return_value = {"NetworkInterfaces": []}
        mock_ec2.describe_nat_gateways.return_value = {"NatGateways": []}
        mock_ec2.describe_internet_gateways.return_value = {"InternetGateways": []}
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
        mock_elbv2.describe_target_groups.return_value = {"TargetGroups": []}
        mock_cfn.list_stacks.return_value = {"StackSummaries": []}

        mock_clients = {
            "ec2": mock_ec2,
            "ecs": mock_ecs,
            "elbv2": mock_elbv2,
            "cloudformation": mock_cfn,
        }

        with self.mock_aws_clients(mock_clients):
            with mock.patch.object(
                sys.modules[
                    "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"
                ],
                "find_clusters",
                return_value=["test-cluster"],
            ):
                # Call the function with specific VPC ID
                result = await get_network_data("vpc-12345678")

                # Verify result structure
                self.assertEqual(result["status"], "success")
                self.assertIn("data", result)
                self.assertIn("timestamp", result["data"])
                self.assertIn("vpc_ids", result["data"])
                self.assertIn("raw_resources", result["data"])
                self.assertIn("analysis_guide", result["data"])

                # Verify VPC ID was used
                self.assertEqual(result["data"]["vpc_ids"], ["vpc-12345678"])

    async def test_get_network_data_no_vpc(self):
        """Test get_network_data when no VPC is found."""
        # Configure mock clients
        mock_ec2 = MagicMock()
        mock_ecs = MagicMock()
        mock_elbv2 = MagicMock()
        mock_cfn = MagicMock()

        # Mock empty responses for VPC discovery
        mock_ecs.list_tasks.return_value = {"taskArns": []}
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
        mock_ec2.describe_vpcs.return_value = {"Vpcs": []}
        mock_cfn.list_stacks.return_value = {"StackSummaries": []}

        mock_clients = {
            "ec2": mock_ec2,
            "ecs": mock_ecs,
            "elbv2": mock_elbv2,
            "cloudformation": mock_cfn,
        }

        with self.mock_aws_clients(mock_clients):
            with mock.patch.object(
                sys.modules[
                    "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"
                ],
                "find_clusters",
                return_value=[],
            ):
                # Call the function with no parameters
                result = await get_network_data()

                # Verify result
                self.assertEqual(result["status"], "warning")
                self.assertIn("No VPCs found", result["message"])

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters(self):
        """Test VPC discovery from ECS clusters."""
        # Configure mock clients
        mock_ecs = MagicMock()
        mock_ec2 = MagicMock()

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

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/cluster/task1"]
        }
        mock_ecs.describe_tasks.return_value = task_response
        mock_ec2.describe_network_interfaces.return_value = eni_response

        mock_clients = {"ecs": mock_ecs, "ec2": mock_ec2}

        with self.mock_aws_clients(mock_clients):
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

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters_no_tasks(self):
        """Test VPC discovery when no tasks are found."""
        mock_ecs = MagicMock()
        mock_ecs.list_tasks.return_value = {"taskArns": []}

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            self.assertEqual(vpc_ids, [])
            mock_ecs.list_tasks.assert_called_once_with(cluster="test-cluster")
            mock_ecs.describe_tasks.assert_not_called()

    @pytest.mark.anyio
    async def test_discover_vpcs_from_loadbalancers(self):
        """Test VPC discovery from load balancers."""
        mock_elbv2 = MagicMock()

        lb_response = {
            "LoadBalancers": [
                {"LoadBalancerName": "test-app-lb", "VpcId": "vpc-12345678"},
                {"LoadBalancerName": "other-lb", "VpcId": "vpc-87654321"},
            ]
        }
        mock_elbv2.describe_load_balancers.return_value = lb_response

        mock_clients = {"elbv2": mock_elbv2}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_loadbalancers()

            self.assertEqual(set(vpc_ids), {"vpc-12345678", "vpc-87654321"})
            mock_elbv2.describe_load_balancers.assert_called_once()

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation(self):
        """Test VPC discovery from CloudFormation stacks."""
        mock_cfn = MagicMock()

        stacks_response = {
            "StackSummaries": [
                {"StackName": "test-app-stack", "StackStatus": "CREATE_COMPLETE"},
                {"StackName": "other-stack", "StackStatus": "CREATE_COMPLETE"},
            ]
        }
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

        mock_cfn.list_stacks.return_value = stacks_response
        mock_cfn.list_stack_resources.side_effect = [resources_response1, resources_response2]

        mock_clients = {"cloudformation": mock_cfn}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_cloudformation()

            self.assertEqual(set(vpc_ids), {"vpc-12345678", "vpc-87654321"})
            mock_cfn.list_stacks.assert_called_once()
            self.assertEqual(mock_cfn.list_stack_resources.call_count, 2)

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation_pagination(self):
        """Test VPC discovery with CloudFormation pagination."""
        mock_cfn = MagicMock()

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

        # Configure mock responses with pagination
        mock_cfn.list_stacks.side_effect = [stacks_response1, stacks_response2]

        # Configure mock responses for stack resources
        mock_cfn.list_stack_resources.side_effect = (
            lambda StackName, **kwargs: resources_response1
            if StackName == "test-app-stack1"
            else resources_response2
        )

        mock_clients = {"cloudformation": mock_cfn}

        with self.mock_aws_clients(mock_clients):
            # Call the function
            vpc_ids = await discover_vpcs_from_cloudformation()

            # Verify the results - should have both VPCs
            self.assertEqual(set(vpc_ids), {"vpc-12345678", "vpc-87654321"})

            # Verify the mocks were called correctly
            self.assertEqual(mock_cfn.list_stacks.call_count, 2)
            self.assertEqual(mock_cfn.list_stack_resources.call_count, 2)

    async def test_get_ec2_resource_with_filters(self):
        """Test EC2 resource retrieval with VPC filtering."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {"Subnets": []}
        mock_ec2.describe_vpcs.return_value = {"Vpcs": []}

        vpc_ids = ["vpc-12345678"]

        # Test describe_subnets with VPC filter
        await get_ec2_resource(mock_ec2, "describe_subnets", vpc_ids)
        mock_ec2.describe_subnets.assert_called_once_with(
            Filters=[{"Name": "vpc-id", "Values": vpc_ids}]
        )

        # Reset mock
        mock_ec2.reset_mock()
        mock_ec2.describe_vpcs.return_value = {"Vpcs": []}

        # Test describe_vpcs with VpcIds parameter
        await get_ec2_resource(mock_ec2, "describe_vpcs", vpc_ids)
        mock_ec2.describe_vpcs.assert_called_once_with(VpcIds=vpc_ids)

    async def test_get_ec2_resource_handles_errors(self):
        """Test EC2 resource retrieval handles errors gracefully."""
        mock_ec2 = MagicMock()

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
        mock_elbv2 = MagicMock()

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
        mock_elbv2 = MagicMock()

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
        result = await get_associated_target_groups(mock_elbv2, ["vpc-12345678"])

        # Verify all target groups are returned
        self.assertEqual(len(result["TargetGroups"]), 2)

        # Verify health was checked for both
        self.assertIn("TargetHealth", result)
        self.assertIn(tg_arn, result["TargetHealth"])
        self.assertIn(other_tg_arn, result["TargetHealth"])

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
        mock_ecs = MagicMock()

        # Setup the expected response
        expected_response = {
            "clusters": [
                {"clusterName": "test-cluster", "status": "ACTIVE", "runningTasksCount": 5}
            ],
            "failures": [],
        }

        # Configure mock responses
        mock_ecs.describe_clusters.return_value = expected_response

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
        mock_ecs = MagicMock()

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
        mock_ecs = MagicMock()

        # Configure mock to raise exception
        mock_ecs.describe_clusters.side_effect = Exception("API error")

        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            get_clusters_info,
        )

        # Call the function
        result = await get_clusters_info(mock_ecs, ["test-cluster"])

        # Verify the results - function returns empty structure on error
        self.assertEqual(result, {"clusters": [], "failures": []})

    @pytest.mark.anyio
    async def test_get_associated_target_groups_empty_response(self):
        """Test get_associated_target_groups with an empty response."""
        # Setup mock ELBv2 client
        mock_elbv2 = MagicMock()

        # Configure describe_target_groups to return empty list
        mock_elbv2.describe_target_groups.return_value = {"TargetGroups": []}

        # Import the function directly
        from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
            get_associated_target_groups,
        )

        # Call the function
        result = await get_associated_target_groups(mock_elbv2, ["vpc-12345678"])

        # Verify results
        self.assertEqual(result["TargetGroups"], [])
        self.assertEqual(result["TargetHealth"], {})

        # Verify describe_target_health was not called (as there are no target groups)
        mock_elbv2.describe_target_health.assert_not_called()

    @pytest.mark.anyio
    async def test_get_associated_target_groups_error_in_health(self):
        """Test get_associated_target_groups with an error when getting target health."""
        mock_elbv2 = MagicMock()

        tg_arn = (
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-tg/1234567890"
        )

        # Configure describe_target_groups to return a target group
        mock_elbv2.describe_target_groups.return_value = {
            "TargetGroups": [
                {
                    "TargetGroupArn": tg_arn,
                    "TargetGroupName": "test-app-tg",
                    "VpcId": "vpc-12345678",
                }
            ]
        }

        # Configure describe_target_health to raise exception
        mock_elbv2.describe_target_health.side_effect = Exception("API error")

        # Call the function
        result = await get_associated_target_groups(mock_elbv2, ["vpc-12345678"])

        # Verify target group was returned
        self.assertEqual(len(result["TargetGroups"]), 1)

        # Based on the actual implementation, the function may add an empty list for target health
        # rather than adding an error key
        self.assertIn(tg_arn, result["TargetHealth"])

    @pytest.mark.anyio
    async def test_get_associated_target_groups_null_target_group(self):
        """Test get_associated_target_groups with a None/null target group in the list."""
        mock_elbv2 = MagicMock()

        # Configure describe_target_groups to return a target group and a None value
        mock_elbv2.describe_target_groups.return_value = {
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

        # Configure describe_target_health to return health info
        mock_elbv2.describe_target_health.return_value = {"TargetHealthDescriptions": []}

        # Call the function
        result = await get_associated_target_groups(mock_elbv2, ["vpc-12345678"])

        # Verify only the valid target group was processed
        self.assertEqual(len(result["TargetGroups"]), 1)

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation_error(self):
        """Test discover_vpcs_from_cloudformation with an API error."""
        mock_cfn = MagicMock()
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}
        mock_cfn.list_stacks.side_effect = ClientError(error_response, "ListStacks")

        mock_clients = {"cloudformation": mock_cfn}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_cloudformation()

            self.assertEqual(vpc_ids, [])
            mock_cfn.list_stacks.assert_called_once()

    @pytest.mark.anyio
    async def test_discover_vpcs_from_loadbalancers_api_error(self):
        """Test discover_vpcs_from_loadbalancers when the API call fails."""
        mock_elbv2 = MagicMock()
        mock_elbv2.describe_load_balancers.side_effect = Exception("API error")

        mock_clients = {"elbv2": mock_elbv2}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_loadbalancers()

            self.assertEqual(vpc_ids, [])
            mock_elbv2.describe_load_balancers.assert_called_once()

    @pytest.mark.anyio
    async def test_discover_vpcs_from_loadbalancers_null_lb(self):
        """Test discover_vpcs_from_loadbalancers with null load balancer entry."""
        mock_elbv2 = MagicMock()

        lb_response = {
            "LoadBalancers": [
                None,  # Test null handling
                {"LoadBalancerName": "test-app-lb", "VpcId": "vpc-12345678"},
            ]
        }
        mock_elbv2.describe_load_balancers.return_value = lb_response

        mock_clients = {"elbv2": mock_elbv2}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_loadbalancers()

            self.assertEqual(vpc_ids, ["vpc-12345678"])
            mock_elbv2.describe_load_balancers.assert_called_once()

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters_null_task(self):
        """Test VPC discovery from clusters with null task in response."""
        mock_ecs = MagicMock()
        mock_ec2 = MagicMock()

        # Mock response for tasks with null task entry
        task_response = {
            "tasks": [
                None,  # Test null handling
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [{"name": "networkInterfaceId", "value": "eni-12345678"}],
                        }
                    ]
                },
            ]
        }
        # Mock response for ENIs with VPC IDs
        eni_response = {"NetworkInterfaces": [{"VpcId": "vpc-12345678"}]}

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/cluster/task1"]
        }
        mock_ecs.describe_tasks.return_value = task_response
        mock_ec2.describe_network_interfaces.return_value = eni_response

        mock_clients = {"ecs": mock_ecs, "ec2": mock_ec2}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            # Verify the results - should ignore null task and process valid ones
            self.assertEqual(vpc_ids, ["vpc-12345678"])

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters_null_attachment(self):
        """Test VPC discovery with null attachment in task."""
        mock_ecs = MagicMock()
        mock_ec2 = MagicMock()

        # Mock response for tasks with null attachment
        task_response = {
            "tasks": [
                {
                    "attachments": [
                        None,  # Test null handling
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [{"name": "networkInterfaceId", "value": "eni-12345678"}],
                        },
                    ]
                }
            ]
        }
        # Mock response for ENIs with VPC IDs
        eni_response = {"NetworkInterfaces": [{"VpcId": "vpc-12345678"}]}

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/cluster/task1"]
        }
        mock_ecs.describe_tasks.return_value = task_response
        mock_ec2.describe_network_interfaces.return_value = eni_response

        mock_clients = {"ecs": mock_ecs, "ec2": mock_ec2}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            # Verify the results - should ignore null attachment and process valid ones
            self.assertEqual(vpc_ids, ["vpc-12345678"])

    @pytest.mark.anyio
    async def test_get_network_data_empty_vpc_and_no_resources(self):
        """Test get_network_data when no VPCs are found."""
        mock_ec2 = MagicMock()
        mock_ecs = MagicMock()
        mock_elbv2 = MagicMock()
        mock_cfn = MagicMock()

        # Configure empty responses
        mock_ecs.list_tasks.return_value = {"taskArns": []}
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
        mock_ec2.describe_vpcs.return_value = {"Vpcs": []}
        mock_cfn.list_stacks.return_value = {"StackSummaries": []}

        mock_clients = {
            "ec2": mock_ec2,
            "ecs": mock_ecs,
            "elbv2": mock_elbv2,
            "cloudformation": mock_cfn,
        }

        with self.mock_aws_clients(mock_clients):
            with mock.patch.object(
                sys.modules[
                    "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"
                ],
                "find_clusters",
                return_value=[],
            ):
                # Call the function (no client parameters)
                result = await get_network_data()

                # Verify result is warning status
                self.assertEqual(result["status"], "warning")
                self.assertIn("No VPCs found", result["message"])

    @pytest.mark.anyio
    async def test_get_ec2_resource_with_null_vpc_ids(self):
        """Test EC2 resource retrieval with null VPC IDs."""
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {"Subnets": []}

        # Test with None vpc_ids
        await get_ec2_resource(mock_ec2, "describe_subnets", None)
        # Verify describe_subnets was called without filters
        mock_ec2.describe_subnets.assert_called_once_with()

    @pytest.mark.anyio
    async def test_get_elb_resources_with_empty_vpc_ids(self):
        """Test ELB resource retrieval with empty VPC IDs list."""
        mock_elbv2 = MagicMock()

        # Configure mock response
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {"LoadBalancerArn": "arn1", "VpcId": "vpc-12345678"},
                {"LoadBalancerArn": "arn2", "VpcId": "vpc-87654321"},
            ]
        }

        # Call function with empty VPC filter
        result = await get_elb_resources(mock_elbv2, "describe_load_balancers", [])

        # Verify result contains all load balancers (no filtering)
        self.assertEqual(len(result["LoadBalancers"]), 2)

    @pytest.mark.anyio
    async def test_get_elb_resources_missing_vpc_id(self):
        """Test ELB resource retrieval with load balancer missing VPC ID."""
        mock_elbv2 = MagicMock()

        # Configure mock response with one load balancer missing VpcId
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {"LoadBalancerArn": "arn1", "VpcId": "vpc-12345678"},
                {"LoadBalancerArn": "arn2"},  # Missing VpcId
            ]
        }

        # Call function with VPC filter
        result = await get_elb_resources(mock_elbv2, "describe_load_balancers", ["vpc-12345678"])

        # Verify result excludes the load balancer without VpcId
        self.assertEqual(len(result["LoadBalancers"]), 1)
        self.assertEqual(result["LoadBalancers"][0]["LoadBalancerArn"], "arn1")

    @pytest.mark.anyio
    async def test_get_elb_resources_null_load_balancer(self):
        """Test ELB resource retrieval with None in LoadBalancers list."""
        mock_elbv2 = MagicMock()

        # Configure mock response with None in LoadBalancers list
        mock_elbv2.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {"LoadBalancerArn": "arn1", "VpcId": "vpc-12345678"},
                None,  # None entry should be handled
            ]
        }

        # Call function with VPC filter
        result = await get_elb_resources(mock_elbv2, "describe_load_balancers", ["vpc-12345678"])

        # Verify result only includes valid load balancer
        self.assertEqual(len(result["LoadBalancers"]), 1)
        self.assertEqual(result["LoadBalancers"][0]["LoadBalancerArn"], "arn1")

    @pytest.mark.anyio
    async def test_get_elb_resources_exception_handling(self):
        """Test ELB resource retrieval handles exceptions gracefully."""
        mock_elbv2 = MagicMock()

        # Configure mock to raise exception
        mock_elbv2.describe_load_balancers.side_effect = Exception("API error")

        # Call function
        result = await get_elb_resources(mock_elbv2, "describe_load_balancers", ["vpc-12345678"])

        # Verify error is returned - the actual implementation returns the full exception string
        self.assertIn("error", result)
        self.assertEqual(result["error"], "API error")

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters_with_null_detail(self):
        """Test VPC discovery from clusters with null detail in attachment."""
        mock_ecs = MagicMock()
        mock_ec2 = MagicMock()

        # Mock response for tasks with null detail
        task_response = {
            "tasks": [
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [
                                None,  # Test null handling
                                {"name": "networkInterfaceId", "value": "eni-12345678"},
                            ],
                        }
                    ]
                }
            ]
        }
        # Mock response for ENIs with VPC IDs
        eni_response = {"NetworkInterfaces": [{"VpcId": "vpc-12345678"}]}

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/cluster/task1"]
        }
        mock_ecs.describe_tasks.return_value = task_response
        mock_ec2.describe_network_interfaces.return_value = eni_response

        mock_clients = {"ecs": mock_ecs, "ec2": mock_ec2}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            # Verify the results - should ignore null detail and process valid ones
            self.assertEqual(vpc_ids, ["vpc-12345678"])

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters_network_interface_not_found(self):
        """Test VPC discovery when networkInterfaceId is not in attachment details."""
        mock_ecs = MagicMock()
        mock_ec2 = MagicMock()

        # Mock response for tasks with missing networkInterfaceId detail
        task_response = {
            "tasks": [
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [{"name": "otherDetail", "value": "some-value"}],
                        }
                    ]
                }
            ]
        }

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/cluster/task1"]
        }
        mock_ecs.describe_tasks.return_value = task_response

        mock_clients = {"ecs": mock_ecs, "ec2": mock_ec2}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            # Verify the results - should be empty since no networkInterfaceId was found
            self.assertEqual(vpc_ids, [])

            # Verify EC2 describe_network_interfaces was not called
            mock_ec2.describe_network_interfaces.assert_not_called()

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters_empty_detail_value(self):
        """Test VPC discovery when networkInterfaceId value is empty."""
        mock_ecs = MagicMock()

        # Mock response for tasks with empty networkInterfaceId value
        task_response = {
            "tasks": [
                {
                    "attachments": [
                        {
                            "type": "ElasticNetworkInterface",
                            "details": [{"name": "networkInterfaceId", "value": ""}],
                        }
                    ]
                }
            ]
        }

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/cluster/task1"]
        }
        mock_ecs.describe_tasks.return_value = task_response

        mock_clients = {"ecs": mock_ecs}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            # Verify the results - should be empty since networkInterfaceId was empty
            self.assertEqual(vpc_ids, [])

    @pytest.mark.anyio
    async def test_discover_vpcs_from_clusters_null_eni(self):
        """Test VPC discovery when ENI response has null entries."""
        mock_ecs = MagicMock()
        mock_ec2 = MagicMock()

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
        # Mock response for ENIs with null entry
        eni_response = {"NetworkInterfaces": [None, {"VpcId": "vpc-12345678"}]}

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {
            "taskArns": ["arn:aws:ecs:us-west-2:123456789012:task/cluster/task1"]
        }
        mock_ecs.describe_tasks.return_value = task_response
        mock_ec2.describe_network_interfaces.return_value = eni_response

        mock_clients = {"ecs": mock_ecs, "ec2": mock_ec2}

        with self.mock_aws_clients(mock_clients):
            vpc_ids = await discover_vpcs_from_clusters(["test-cluster"])

            # Verify the results - should ignore null ENI and process valid ones
            self.assertEqual(vpc_ids, ["vpc-12345678"])

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation_deleted_stack(self):
        """Test VPC discovery from CloudFormation with deleted stacks."""
        mock_cfn = MagicMock()

        # Mock response for stack list with deleted stack
        stacks_response = {
            "StackSummaries": [
                {"StackName": "test-app-stack", "StackStatus": "CREATE_COMPLETE"},
                {
                    "StackName": "test-app-deleted",
                    "StackStatus": "DELETE_COMPLETE",
                },  # Should be filtered out
            ]
        }

        # Mock response for stack resources
        resources_response = {
            "StackResourceSummaries": [
                {"ResourceType": "AWS::EC2::VPC", "PhysicalResourceId": "vpc-12345678"}
            ]
        }

        # Configure mock responses
        mock_cfn.list_stacks.return_value = stacks_response
        mock_cfn.list_stack_resources.return_value = resources_response

        mock_clients = {"cloudformation": mock_cfn}

        with self.mock_aws_clients(mock_clients):
            # Call the function
            vpc_ids = await discover_vpcs_from_cloudformation()

            # Verify the results - only should include VPC from non-deleted stack
            self.assertEqual(vpc_ids, ["vpc-12345678"])

            # Verify list_stack_resources was only called for non-deleted stack
            mock_cfn.list_stack_resources.assert_called_once_with(StackName="test-app-stack")

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation_invalid_stack_resource(self):
        """Test VPC discovery from CloudFormation with invalid resource summary."""
        mock_cfn = MagicMock()

        # Mock response for stack list
        stacks_response = {
            "StackSummaries": [{"StackName": "test-app-stack", "StackStatus": "CREATE_COMPLETE"}]
        }

        # Mock response for stack resources with a None entry and a non-VPC resource
        resources_response = {
            "StackResourceSummaries": [
                None,  # Test null handling
                {
                    "ResourceType": "AWS::S3::Bucket",
                    "PhysicalResourceId": "test-bucket",
                },  # Not a VPC
                {"ResourceType": "AWS::EC2::VPC", "PhysicalResourceId": "vpc-12345678"},
            ]
        }

        # Configure mock responses
        mock_cfn.list_stacks.return_value = stacks_response
        mock_cfn.list_stack_resources.return_value = resources_response

        mock_clients = {"cloudformation": mock_cfn}

        with self.mock_aws_clients(mock_clients):
            # Call the function
            vpc_ids = await discover_vpcs_from_cloudformation()

            # Verify the results - should ignore null resource and non-VPC resource
            self.assertEqual(vpc_ids, ["vpc-12345678"])

    @pytest.mark.anyio
    async def test_discover_vpcs_from_cloudformation_missing_physical_id(self):
        """Test VPC discovery from CloudFormation with missing PhysicalResourceId."""
        mock_cfn = MagicMock()

        # Mock response for stack list
        stacks_response = {
            "StackSummaries": [{"StackName": "test-app-stack", "StackStatus": "CREATE_COMPLETE"}]
        }

        # Mock response for stack resources with missing PhysicalResourceId
        resources_response = {
            "StackResourceSummaries": [
                {"ResourceType": "AWS::EC2::VPC"},  # Missing PhysicalResourceId
                {"ResourceType": "AWS::EC2::VPC", "PhysicalResourceId": "vpc-12345678"},
            ]
        }

        # Configure mock responses
        mock_cfn.list_stacks.return_value = stacks_response
        mock_cfn.list_stack_resources.return_value = resources_response

        mock_clients = {"cloudformation": mock_cfn}

        with self.mock_aws_clients(mock_clients):
            # Call the function
            vpc_ids = await discover_vpcs_from_cloudformation()

            # Verify the results - should ignore resource without PhysicalResourceId
            self.assertEqual(vpc_ids, ["vpc-12345678"])

    @pytest.mark.anyio
    async def test_get_network_data_vpc_discovery_from_tags(self):
        """Test VPC discovery from EC2 VPC tags."""
        mock_ec2 = MagicMock()
        mock_ecs = MagicMock()
        mock_elbv2 = MagicMock()
        mock_cfn = MagicMock()

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {"taskArns": []}
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
        mock_cfn.list_stacks.return_value = {"StackSummaries": []}

        # VPC discovery from tags
        vpc_id = "vpc-12345678"
        mock_ec2.describe_vpcs.return_value = {
            "Vpcs": [
                {
                    "VpcId": vpc_id,
                    "Tags": [{"Key": "Name", "Value": "test-app-vpc"}],
                },
                {
                    "VpcId": "vpc-87654321",
                    "Tags": [{"Key": "Name", "Value": "other-vpc"}],
                },
            ]
        }

        # Standard AWS API mocks
        mock_ec2.describe_subnets.return_value = {"Subnets": []}
        mock_ec2.describe_security_groups.return_value = {"SecurityGroups": []}
        mock_ec2.describe_route_tables.return_value = {"RouteTables": []}
        mock_ec2.describe_network_interfaces.return_value = {"NetworkInterfaces": []}
        mock_ec2.describe_nat_gateways.return_value = {"NatGateways": []}
        mock_ec2.describe_internet_gateways.return_value = {"InternetGateways": []}
        mock_elbv2.describe_target_groups.return_value = {"TargetGroups": []}

        mock_clients = {
            "ec2": mock_ec2,
            "ecs": mock_ecs,
            "elbv2": mock_elbv2,
            "cloudformation": mock_cfn,
        }

        with self.mock_aws_clients(mock_clients):
            with mock.patch.object(
                sys.modules[
                    "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"
                ],
                "find_clusters",
                return_value=[],
            ):
                # Call the function (no client parameters)
                result = await get_network_data()

                # Verify success status
                self.assertEqual(result["status"], "success")

                # Verify both vpc_ids were discovered
                self.assertIn(vpc_id, result["data"]["vpc_ids"])
                self.assertIn("vpc-87654321", result["data"]["vpc_ids"])

    @pytest.mark.anyio
    async def test_get_network_data_null_vpc_in_response(self):
        """Test get_network_data with null VPC in response."""
        mock_ec2 = MagicMock()
        mock_ecs = MagicMock()
        mock_elbv2 = MagicMock()
        mock_cfn = MagicMock()

        # Configure mock responses
        mock_ecs.list_tasks.return_value = {"taskArns": []}
        mock_elbv2.describe_load_balancers.return_value = {"LoadBalancers": []}
        mock_cfn.list_stacks.return_value = {"StackSummaries": []}

        # VPC discovery with null VPC in response
        mock_ec2.describe_vpcs.return_value = {
            "Vpcs": [
                {"VpcId": "vpc-12345678", "Tags": [{"Key": "Name", "Value": "test-app-vpc"}]},
                None,  # Null VPC should be handled
            ]
        }

        # Standard AWS API mocks
        mock_ec2.describe_subnets.return_value = {"Subnets": []}
        mock_ec2.describe_security_groups.return_value = {"SecurityGroups": []}
        mock_ec2.describe_route_tables.return_value = {"RouteTables": []}
        mock_ec2.describe_network_interfaces.return_value = {"NetworkInterfaces": []}
        mock_ec2.describe_nat_gateways.return_value = {"NatGateways": []}
        mock_ec2.describe_internet_gateways.return_value = {"InternetGateways": []}
        mock_elbv2.describe_target_groups.return_value = {"TargetGroups": []}

        mock_clients = {
            "ec2": mock_ec2,
            "ecs": mock_ecs,
            "elbv2": mock_elbv2,
            "cloudformation": mock_cfn,
        }

        with self.mock_aws_clients(mock_clients):
            with mock.patch.object(
                sys.modules[
                    "awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration"
                ],
                "find_clusters",
                return_value=[],
            ):
                # Call the function (no client parameters)
                result = await get_network_data()

                # Verify success status
                self.assertEqual(result["status"], "success")

                # Verify vpc_id was discovered from valid entry
                self.assertEqual(len(result["data"]["vpc_ids"]), 1)
                self.assertEqual(result["data"]["vpc_ids"][0], "vpc-12345678")
