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

"""Unit tests for the update_broker_storage_tool in mutate_cluster register_module."""

import json
import unittest
from awslabs.aws_msk_mcp_server.tools.mutate_cluster.register_module import register_module
from unittest.mock import Mock, patch


class TestMutateClusterUpdateBrokerStorageTool(unittest.TestCase):
    """Tests for the update_broker_storage_tool in mutate_cluster register_module."""

    def _extract_tool_function(self, mock_tool_decorator, index=0):
        """Helper method to extract a tool function from the mock decorator."""
        count = 0
        for args, kwargs in mock_tool_decorator.call_args_list:
            if len(args) > 0 and callable(args[0]):
                if count == index:
                    return args[0]
                count += 1
        return None

    @patch('boto3.client')
    def test_update_broker_storage_tool_success(self, mock_boto3_client):
        """Test the update_broker_storage_tool function with successful tag check."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Create a mock client
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up the mock return value for list_tags_for_resource (used by check_mcp_generated_tag)
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'true'}}

        # Set up the mock return value for update_broker_storage
        expected_result = {
            'ClusterArn': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster',
            'ClusterOperationArn': 'arn:aws:kafka:us-west-2:123456789012:cluster-operation/test-cluster/operation-123',
        }
        mock_client.update_broker_storage.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Extract the update_broker_storage_tool function
        # Find the index of the update_broker_storage_tool in the call_args_list
        update_broker_storage_index = None
        for i, (args, kwargs) in enumerate(mock_mcp.tool.call_args_list):
            if kwargs.get('name') == 'update_broker_storage':
                update_broker_storage_index = i
                break

        self.assertIsNotNone(
            update_broker_storage_index, 'Could not find update_broker_storage tool registration'
        )

        # Extract the tool function using the index
        update_broker_storage_tool = self._extract_tool_function(
            mock_tool_decorator, update_broker_storage_index
        )
        self.assertIsNotNone(
            update_broker_storage_tool, 'Could not find update_broker_storage_tool function'
        )

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster'
        current_version = 'K3AEGXETSR30VB'
        target_broker_ebs_volume_info = [
            {
                'KafkaBrokerNodeId': 'ALL',
                'VolumeSizeGB': 1100,
                'ProvisionedThroughput': {'Enabled': True, 'VolumeThroughput': 250},
            }
        ]

        # Call the tool function
        result = update_broker_storage_tool(
            region=region,
            cluster_arn=cluster_arn,
            current_version=current_version,
            target_broker_ebs_volume_info=json.dumps(target_broker_ebs_volume_info),
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once_with(
            'kafka',
            region_name=region,
            config=unittest.mock.ANY,  # We don't need to check the exact config
        )

        # Verify list_tags_for_resource was called correctly (for check_mcp_generated_tag)
        mock_client.list_tags_for_resource.assert_called_once_with(ResourceArn=cluster_arn)

        # Verify update_broker_storage was called correctly
        mock_client.update_broker_storage.assert_called_once()
        call_args = mock_client.update_broker_storage.call_args[1]
        self.assertEqual(call_args['ClusterArn'], cluster_arn)
        self.assertEqual(call_args['CurrentVersion'], current_version)

        # For target_broker_ebs_volume_info, we need to check that it was passed correctly
        # Since the function might be parsing the JSON string or passing it directly,
        # we'll check the key elements instead of doing a direct comparison
        target_info = json.loads(json.dumps(target_broker_ebs_volume_info))
        actual_info = call_args['TargetBrokerEBSVolumeInfo']

        # If actual_info is a string, parse it
        if isinstance(actual_info, str):
            actual_info = json.loads(actual_info)

        # Check the key elements
        self.assertEqual(len(actual_info), len(target_info))
        self.assertEqual(actual_info[0]['KafkaBrokerNodeId'], target_info[0]['KafkaBrokerNodeId'])
        self.assertEqual(actual_info[0]['VolumeSizeGB'], target_info[0]['VolumeSizeGB'])
        self.assertEqual(
            actual_info[0]['ProvisionedThroughput']['Enabled'],
            target_info[0]['ProvisionedThroughput']['Enabled'],
        )
        self.assertEqual(
            actual_info[0]['ProvisionedThroughput']['VolumeThroughput'],
            target_info[0]['ProvisionedThroughput']['VolumeThroughput'],
        )

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_update_broker_storage_tool_tag_check_failure(self, mock_boto3_client):
        """Test the update_broker_storage_tool function with failed tag check."""
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

        # Extract the update_broker_storage_tool function
        # Find the index of the update_broker_storage_tool in the call_args_list
        update_broker_storage_index = None
        for i, (args, kwargs) in enumerate(mock_mcp.tool.call_args_list):
            if kwargs.get('name') == 'update_broker_storage':
                update_broker_storage_index = i
                break

        self.assertIsNotNone(
            update_broker_storage_index, 'Could not find update_broker_storage tool registration'
        )

        # Extract the tool function using the index
        update_broker_storage_tool = self._extract_tool_function(
            mock_tool_decorator, update_broker_storage_index
        )
        self.assertIsNotNone(
            update_broker_storage_tool, 'Could not find update_broker_storage_tool function'
        )

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster'
        current_version = 'K3AEGXETSR30VB'
        target_broker_ebs_volume_info = [
            {
                'KafkaBrokerNodeId': 'ALL',
                'VolumeSizeGB': 1100,
                'ProvisionedThroughput': {'Enabled': True, 'VolumeThroughput': 250},
            }
        ]

        # Call the tool function and expect a ValueError
        with self.assertRaises(ValueError) as context:
            update_broker_storage_tool(
                region=region,
                cluster_arn=cluster_arn,
                current_version=current_version,
                target_broker_ebs_volume_info=json.dumps(target_broker_ebs_volume_info),
            )

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

        # Verify update_broker_storage was NOT called
        mock_client.update_broker_storage.assert_not_called()

    @patch('boto3.client')
    def test_update_broker_storage_tool_with_string_input(self, mock_boto3_client):
        """Test the update_broker_storage_tool function with string input for target_broker_ebs_volume_info."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Create a mock client
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up the mock return value for list_tags_for_resource (used by check_mcp_generated_tag)
        mock_client.list_tags_for_resource.return_value = {'Tags': {'MCP Generated': 'true'}}

        # Set up the mock return value for update_broker_storage
        expected_result = {
            'ClusterArn': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster',
            'ClusterOperationArn': 'arn:aws:kafka:us-west-2:123456789012:cluster-operation/test-cluster/operation-123',
        }
        mock_client.update_broker_storage.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Extract the update_broker_storage_tool function
        # Find the index of the update_broker_storage_tool in the call_args_list
        update_broker_storage_index = None
        for i, (args, kwargs) in enumerate(mock_mcp.tool.call_args_list):
            if kwargs.get('name') == 'update_broker_storage':
                update_broker_storage_index = i
                break

        self.assertIsNotNone(
            update_broker_storage_index, 'Could not find update_broker_storage tool registration'
        )

        # Extract the tool function using the index
        update_broker_storage_tool = self._extract_tool_function(
            mock_tool_decorator, update_broker_storage_index
        )
        self.assertIsNotNone(
            update_broker_storage_tool, 'Could not find update_broker_storage_tool function'
        )

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster'
        current_version = 'K3AEGXETSR30VB'
        target_broker_ebs_volume_info_json = json.dumps(
            [
                {
                    'KafkaBrokerNodeId': 'ALL',
                    'VolumeSizeGB': 1100,
                    'ProvisionedThroughput': {'Enabled': True, 'VolumeThroughput': 250},
                }
            ]
        )

        # Call the tool function with string input
        result = update_broker_storage_tool(
            region=region,
            cluster_arn=cluster_arn,
            current_version=current_version,
            target_broker_ebs_volume_info=target_broker_ebs_volume_info_json,
        )

        # Verify update_broker_storage was called correctly
        mock_client.update_broker_storage.assert_called_once()
        call_args = mock_client.update_broker_storage.call_args[1]
        self.assertEqual(call_args['ClusterArn'], cluster_arn)
        self.assertEqual(call_args['CurrentVersion'], current_version)

        # For target_broker_ebs_volume_info, we need to check that it was passed correctly
        # Since the function might be parsing the JSON string or passing it directly,
        # we'll check the key elements instead of doing a direct comparison
        target_info = json.loads(target_broker_ebs_volume_info_json)
        actual_info = call_args['TargetBrokerEBSVolumeInfo']

        # If actual_info is a string, parse it
        if isinstance(actual_info, str):
            actual_info = json.loads(actual_info)

        # Check the key elements
        self.assertEqual(len(actual_info), len(target_info))
        self.assertEqual(actual_info[0]['KafkaBrokerNodeId'], target_info[0]['KafkaBrokerNodeId'])
        self.assertEqual(actual_info[0]['VolumeSizeGB'], target_info[0]['VolumeSizeGB'])
        self.assertEqual(
            actual_info[0]['ProvisionedThroughput']['Enabled'],
            target_info[0]['ProvisionedThroughput']['Enabled'],
        )
        self.assertEqual(
            actual_info[0]['ProvisionedThroughput']['VolumeThroughput'],
            target_info[0]['ProvisionedThroughput']['VolumeThroughput'],
        )

        # Verify the result
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
