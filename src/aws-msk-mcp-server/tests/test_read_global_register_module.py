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

"""Unit tests for the read_global register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.read_global.register_module import register_module
from unittest.mock import Mock, call, patch


class TestReadGlobalRegisterModule(unittest.TestCase):
    """Tests for the read_global register_module."""

    def test_register_module(self):
        """Test that register_module registers the expected tools."""
        # Setup
        mock_mcp = Mock()
        mock_tool = Mock()
        mock_mcp.tool.return_value = mock_tool

        # Call the function
        register_module(mock_mcp)

        # Verify the correct tools were registered
        expected_tool_calls = [
            call(name='get_global_info'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))

    @patch('boto3.client')
    def test_get_global_info_all(self, mock_boto3_client):
        """Test the get_global_info function with info_type='all'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return values for the boto3 client methods
        mock_client.list_clusters_v2.return_value = {
            'ClusterInfoList': [{'ClusterName': 'test-cluster'}]
        }
        mock_client.list_configurations.return_value = {
            'ConfigurationInfoList': [{'Name': 'test-config'}]
        }
        mock_client.list_vpc_connections.return_value = {
            'VpcConnectionInfoList': [{'VpcId': 'vpc-123'}]
        }
        mock_client.list_kafka_versions.return_value = {'KafkaVersions': [{'Version': '2.8.1'}]}

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with info_type='all'
        result = tool_func(region='us-west-2', info_type='all', kwargs={})

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify the result structure
        self.assertIn('clusters', result)
        self.assertIn('configurations', result)
        self.assertIn('vpc_connections', result)
        self.assertIn('kafka_versions', result)

        # Verify the individual API calls were made
        mock_client.list_clusters_v2.assert_called_once()
        mock_client.list_configurations.assert_called_once()
        mock_client.list_vpc_connections.assert_called_once()
        mock_client.list_kafka_versions.assert_called_once()

    @patch('boto3.client')
    def test_get_global_info_clusters(self, mock_boto3_client):
        """Test the get_global_info function with info_type='clusters'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_clusters_v2.return_value = {
            'ClusterInfoList': [{'ClusterName': 'test-cluster'}]
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with info_type='clusters' and kwargs
        result = tool_func(
            region='us-west-2',
            info_type='clusters',
            kwargs={
                'cluster_name_filter': 'test',
                'cluster_type_filter': 'PROVISIONED',
                'max_results': 5,
                'next_token': 'token',
            },
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_clusters_v2 was called correctly with kwargs
        mock_client.list_clusters_v2.assert_called_once()

        # Verify the result
        self.assertEqual(result, {'ClusterInfoList': [{'ClusterName': 'test-cluster'}]})

    @patch('boto3.client')
    def test_get_global_info_configurations(self, mock_boto3_client):
        """Test the get_global_info function with info_type='configurations'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_configurations.return_value = {
            'ConfigurationInfoList': [{'Name': 'test-config'}]
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with info_type='configurations' and kwargs
        result = tool_func(
            region='us-west-2',
            info_type='configurations',
            kwargs={'max_results': 5, 'next_token': 'token'},
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_configurations was called correctly with kwargs
        mock_client.list_configurations.assert_called_once()

        # Verify the result
        self.assertEqual(result, {'ConfigurationInfoList': [{'Name': 'test-config'}]})

    @patch('boto3.client')
    def test_get_global_info_vpc_connections(self, mock_boto3_client):
        """Test the get_global_info function with info_type='vpc_connections'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_vpc_connections.return_value = {
            'VpcConnectionInfoList': [{'VpcId': 'vpc-123'}]
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with info_type='vpc_connections' and kwargs
        result = tool_func(
            region='us-west-2',
            info_type='vpc_connections',
            kwargs={'max_results': 5, 'next_token': 'token'},
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_vpc_connections was called correctly with kwargs
        mock_client.list_vpc_connections.assert_called_once()

        # Verify the result
        self.assertEqual(result, {'VpcConnectionInfoList': [{'VpcId': 'vpc-123'}]})

    @patch('boto3.client')
    def test_get_global_info_kafka_versions(self, mock_boto3_client):
        """Test the get_global_info function with info_type='kafka_versions'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_kafka_versions.return_value = {'KafkaVersions': [{'Version': '2.8.1'}]}

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with info_type='kafka_versions'
        result = tool_func(region='us-west-2', info_type='kafka_versions', kwargs={})

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_kafka_versions was called correctly
        mock_client.list_kafka_versions.assert_called_once()

        # Verify the result
        self.assertEqual(result, {'KafkaVersions': [{'Version': '2.8.1'}]})

    @patch('boto3.client')
    def test_get_global_info_invalid_type(self, mock_boto3_client):
        """Test the get_global_info function with an invalid info_type."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function with an invalid info_type
        with self.assertRaises(ValueError) as context:
            tool_func(region='us-west-2', info_type='invalid', kwargs={})

        # Verify the error message
        self.assertIn('Unsupported info_type', str(context.exception))


if __name__ == '__main__':
    unittest.main()
