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

"""Unit tests for the reboot_broker_tool in mutate_cluster register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.mutate_cluster.register_module import register_module
from unittest.mock import Mock, patch


class TestMutateClusterRebootBrokerTool(unittest.TestCase):
    """Tests for the reboot_broker_tool in mutate_cluster register_module."""

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
    def test_reboot_broker_tool_success(self, mock_boto3_client):
        """Test the reboot_broker_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Create a mock client
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up the mock return value for reboot_broker
        expected_result = {
            'ClusterArn': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster',
            'ClusterOperationArn': 'arn:aws:kafka:us-west-2:123456789012:cluster-operation/test-cluster/operation-123',
        }
        mock_client.reboot_broker.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Extract the reboot_broker_tool function
        reboot_broker_index = self._find_tool_index(mock_mcp, 'reboot_broker')
        self.assertIsNotNone(reboot_broker_index, 'Could not find reboot_broker tool registration')

        reboot_broker_tool = self._extract_tool_function(mock_tool_decorator, reboot_broker_index)
        self.assertIsNotNone(reboot_broker_tool, 'Could not find reboot_broker_tool function')

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster'
        broker_ids = ['0', '1', '2']

        # Call the tool function
        result = reboot_broker_tool(region=region, cluster_arn=cluster_arn, broker_ids=broker_ids)

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once_with(
            'kafka',
            region_name=region,
            config=unittest.mock.ANY,  # We don't need to check the exact config
        )

        # Verify reboot_broker was called
        mock_client.reboot_broker.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
