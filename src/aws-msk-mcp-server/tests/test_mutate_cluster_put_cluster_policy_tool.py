# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the put_cluster_policy_tool in mutate_cluster register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.mutate_cluster.register_module import register_module
from unittest.mock import Mock, patch


class TestMutateClusterPutClusterPolicyTool(unittest.TestCase):
    """Tests for the put_cluster_policy_tool in mutate_cluster register_module."""

    def _extract_tool_function(self, mock_tool_decorator, index=0):
        """Helper method to extract a tool function from the mock decorator."""
        count = 0
        for args, kwargs in mock_tool_decorator.call_args_list:
            if len(args) > 0 and callable(args[0]):
                if count == index:
                    return args[0]
                count += 1
        return None

    def _find_tool_index(self, mock_mcp, tool_name):
        """Helper method to find the index of a tool in the call_args_list."""
        for i, (args, kwargs) in enumerate(mock_mcp.tool.call_args_list):
            if kwargs.get('name') == tool_name:
                return i
        return None

    @patch('boto3.client')
    def test_put_cluster_policy_tool_success(self, mock_boto3_client):
        """Test the put_cluster_policy_tool function with successful tag check."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Create a mock client
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up the mock return value for list_tags_for_resource (used by check_mcp_generated_tag)
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'true'}}

        # Set up the mock return value for put_cluster_policy
        expected_result = {'CurrentVersion': 'K3AEGXETSR30VB'}
        mock_client.put_cluster_policy.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Extract the put_cluster_policy_tool function
        put_cluster_policy_index = self._find_tool_index(mock_mcp, 'put_cluster_policy')
        self.assertIsNotNone(
            put_cluster_policy_index, 'Could not find put_cluster_policy tool registration'
        )

        put_cluster_policy_tool = self._extract_tool_function(
            mock_tool_decorator, put_cluster_policy_index
        )
        self.assertIsNotNone(
            put_cluster_policy_tool, 'Could not find put_cluster_policy_tool function'
        )

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster'
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'AWS': 'arn:aws:iam::123456789012:role/ExampleRole'},
                    'Action': ['kafka:GetBootstrapBrokers', 'kafka:DescribeCluster'],
                    'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/example-cluster/*',
                }
            ],
        }

        # Call the tool function
        result = put_cluster_policy_tool(region=region, cluster_arn=cluster_arn, policy=policy)

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once_with(
            'kafka',
            region_name=region,
            config=unittest.mock.ANY,  # We don't need to check the exact config
        )

        # Verify list_tags_for_resource was called correctly (for check_mcp_generated_tag)
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)

        # Verify put_cluster_policy was called correctly
        mock_client.put_cluster_policy.assert_called_once_with(
            ClusterArn=cluster_arn, Policy=policy
        )

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_put_cluster_policy_tool_tag_check_failure(self, mock_boto3_client):
        """Test the put_cluster_policy_tool function with failed tag check."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Create a mock client
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up the mock return value for list_tags_for_resource (used by check_mcp_generated_tag)
        # Missing the "MCP Generated" tag
        mock_client.list_tags_for_resource.return_value = {'Tags': {'SomeOtherTag': 'value'}}

        # Register the module
        register_module(mock_mcp)

        # Extract the put_cluster_policy_tool function
        put_cluster_policy_index = self._find_tool_index(mock_mcp, 'put_cluster_policy')
        self.assertIsNotNone(
            put_cluster_policy_index, 'Could not find put_cluster_policy tool registration'
        )

        put_cluster_policy_tool = self._extract_tool_function(
            mock_tool_decorator, put_cluster_policy_index
        )
        self.assertIsNotNone(
            put_cluster_policy_tool, 'Could not find put_cluster_policy_tool function'
        )

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster'
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {'AWS': 'arn:aws:iam::123456789012:role/ExampleRole'},
                    'Action': ['kafka:GetBootstrapBrokers', 'kafka:DescribeCluster'],
                    'Resource': 'arn:aws:kafka:us-east-1:123456789012:cluster/example-cluster/*',
                }
            ],
        }

        # Call the tool function and expect a ValueError
        with self.assertRaises(ValueError) as context:
            put_cluster_policy_tool(region=region, cluster_arn=cluster_arn, policy=policy)

        # Verify the error message
        self.assertIn("does not have the 'MCP Generated' tag", str(context.exception))

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once_with(
            'kafka',
            region_name=region,
            config=unittest.mock.ANY,  # We don't need to check the exact config
        )

        # Verify list_tags_for_resource was called correctly (for check_mcp_generated_tag)
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)

        # Verify put_cluster_policy was NOT called
        mock_client.put_cluster_policy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
