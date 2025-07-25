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

"""Unit tests for the read_cluster register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.read_cluster.register_module import register_module
from unittest.mock import Mock, call, patch


class TestReadClusterRegisterModule(unittest.TestCase):
    """Tests for the read_cluster register_module."""

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
            call(name='describe_cluster_operation'),
            call(name='get_cluster_info'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))

    @patch('boto3.client')
    def test_describe_cluster_operation_tool(self, mock_boto3_client):
        """Test the describe_cluster_operation_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.describe_cluster_operation_v2.return_value = {
            'ClusterOperationInfo': {'Status': 'Success'}
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function
        result = tool_func(region='us-west-2', cluster_operation_arn='test-arn')

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify describe_cluster_operation_v2 was called correctly
        mock_client.describe_cluster_operation_v2.assert_called_once_with(
            ClusterOperationArn='test-arn'
        )

        # Verify the result
        self.assertEqual(result, {'ClusterOperationInfo': {'Status': 'Success'}})

    @patch('boto3.client')
    def test_get_cluster_info_all(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='all'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return values for the boto3 client methods
        mock_client.describe_cluster_v2.return_value = {'ClusterInfo': {'Status': 'Active'}}
        mock_client.get_bootstrap_brokers.return_value = {
            'BootstrapBrokerString': 'broker1,broker2'
        }
        mock_client.list_nodes.return_value = {'NodeInfoList': [{'BrokerId': 1}]}
        mock_client.get_compatible_kafka_versions.return_value = {
            'CompatibleKafkaVersions': ['2.8.1']
        }
        mock_client.get_cluster_policy.return_value = {'Policy': 'policy-json'}
        mock_client.list_cluster_operations_v2.return_value = {
            'ClusterOperationInfoList': [{'OperationId': 1}]
        }
        mock_client.list_client_vpc_connections.return_value = {
            'VpcConnectionInfoList': [{'VpcId': 'vpc-123'}]
        }
        mock_client.list_scram_secrets.return_value = {'SecretArnList': ['secret-arn']}

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='all'
        result = tool_func(region='us-west-2', cluster_arn='test-cluster-arn', info_type='all')

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify the result structure
        self.assertIn('metadata', result)
        self.assertIn('brokers', result)
        self.assertIn('nodes', result)
        self.assertIn('compatible_versions', result)
        self.assertIn('policy', result)
        self.assertIn('operations', result)
        self.assertIn('client_vpc_connections', result)
        self.assertIn('scram_secrets', result)

    @patch('boto3.client')
    def test_get_cluster_info_all_with_errors(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='all' when some calls fail."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return values and exceptions
        mock_client.describe_cluster_v2.side_effect = Exception('Metadata error')
        mock_client.get_bootstrap_brokers.side_effect = Exception('Brokers error')
        mock_client.list_nodes.side_effect = Exception('Nodes error')
        mock_client.get_compatible_kafka_versions.side_effect = Exception('Versions error')
        mock_client.get_cluster_policy.side_effect = Exception('Policy error')
        mock_client.list_cluster_operations_v2.side_effect = Exception('Operations error')
        mock_client.list_client_vpc_connections.side_effect = Exception('VPC connections error')
        mock_client.list_scram_secrets.side_effect = Exception('SCRAM secrets error')

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='all'
        result = tool_func(region='us-west-2', cluster_arn='test-cluster-arn', info_type='all')

        # Verify the result structure contains error messages
        self.assertEqual(result['metadata'], {'error': 'Metadata error'})
        self.assertEqual(result['brokers'], {'error': 'Brokers error'})
        self.assertEqual(result['nodes'], {'error': 'Nodes error'})
        self.assertEqual(result['compatible_versions'], {'error': 'Versions error'})
        self.assertEqual(result['policy'], {'error': 'Policy error'})
        self.assertEqual(result['operations'], {'error': 'Operations error'})
        self.assertEqual(result['client_vpc_connections'], {'error': 'VPC connections error'})
        self.assertEqual(result['scram_secrets'], {'error': 'SCRAM secrets error'})

    @patch('boto3.client')
    def test_get_cluster_info_metadata(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='metadata'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.describe_cluster_v2.return_value = {'ClusterInfo': {'Status': 'Active'}}

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='metadata'
        result = tool_func(
            region='us-west-2', cluster_arn='test-cluster-arn', info_type='metadata'
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify describe_cluster_v2 was called correctly
        mock_client.describe_cluster_v2.assert_called_once_with(ClusterArn='test-cluster-arn')

        # Verify the result
        self.assertEqual(result, {'ClusterInfo': {'Status': 'Active'}})

    @patch('boto3.client')
    def test_get_cluster_info_brokers(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='brokers'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.get_bootstrap_brokers.return_value = {
            'BootstrapBrokerString': 'broker1,broker2'
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='brokers'
        result = tool_func(region='us-west-2', cluster_arn='test-cluster-arn', info_type='brokers')

        # Verify get_bootstrap_brokers was called correctly
        mock_client.get_bootstrap_brokers.assert_called_once_with(ClusterArn='test-cluster-arn')

        # Verify the result
        self.assertEqual(result, {'BootstrapBrokerString': 'broker1,broker2'})

    @patch('boto3.client')
    def test_get_cluster_info_nodes(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='nodes'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_nodes.return_value = {'NodeInfoList': [{'BrokerId': 1}]}

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='nodes'
        result = tool_func(region='us-west-2', cluster_arn='test-cluster-arn', info_type='nodes')

        # Verify list_nodes was called correctly
        mock_client.list_nodes.assert_called_once_with(
            ClusterArn='test-cluster-arn', MaxResults=10
        )

        # Verify the result
        self.assertEqual(result, {'NodeInfoList': [{'BrokerId': 1}]})

    @patch('boto3.client')
    def test_get_cluster_info_compatible_versions(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='compatible_versions'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.get_compatible_kafka_versions.return_value = {
            'CompatibleKafkaVersions': ['2.8.1']
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='compatible_versions'
        result = tool_func(
            region='us-west-2', cluster_arn='test-cluster-arn', info_type='compatible_versions'
        )

        # Verify get_compatible_kafka_versions was called correctly
        mock_client.get_compatible_kafka_versions.assert_called_once_with(
            ClusterArn='test-cluster-arn'
        )

        # Verify the result
        self.assertEqual(result, {'CompatibleKafkaVersions': ['2.8.1']})

    @patch('boto3.client')
    def test_get_cluster_info_policy(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='policy'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.get_cluster_policy.return_value = {'Policy': 'policy-json'}

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='policy'
        result = tool_func(region='us-west-2', cluster_arn='test-cluster-arn', info_type='policy')

        # Verify get_cluster_policy was called correctly
        mock_client.get_cluster_policy.assert_called_once_with(ClusterArn='test-cluster-arn')

        # Verify the result
        self.assertEqual(result, {'Policy': 'policy-json'})

    @patch('boto3.client')
    def test_get_cluster_info_operations(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='operations'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_cluster_operations_v2.return_value = {
            'ClusterOperationInfoList': [{'OperationId': 1}]
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='operations' and kwargs
        result = tool_func(
            region='us-west-2',
            cluster_arn='test-cluster-arn',
            info_type='operations',
            kwargs={'max_results': 5, 'next_token': 'token'},
        )

        # Verify list_cluster_operations_v2 was called correctly with kwargs
        mock_client.list_cluster_operations_v2.assert_called_once_with(
            ClusterArn='test-cluster-arn', MaxResults=5, NextToken='token'
        )

        # Verify the result
        self.assertEqual(result, {'ClusterOperationInfoList': [{'OperationId': 1}]})

    @patch('boto3.client')
    def test_get_cluster_info_client_vpc_connections(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='client_vpc_connections'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_client_vpc_connections.return_value = {
            'VpcConnectionInfoList': [{'VpcId': 'vpc-123'}]
        }

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='client_vpc_connections' and kwargs
        result = tool_func(
            region='us-west-2',
            cluster_arn='test-cluster-arn',
            info_type='client_vpc_connections',
            kwargs={'max_results': 5, 'next_token': 'token'},
        )

        # Verify list_client_vpc_connections was called correctly with kwargs
        mock_client.list_client_vpc_connections.assert_called_once_with(
            ClusterArn='test-cluster-arn', MaxResults=5, NextToken='token'
        )

        # Verify the result
        self.assertEqual(result, {'VpcConnectionInfoList': [{'VpcId': 'vpc-123'}]})

    @patch('boto3.client')
    def test_get_cluster_info_scram_secrets(self, mock_boto3_client):
        """Test the get_cluster_info function with info_type='scram_secrets'."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client
        mock_client.list_scram_secrets.return_value = {'SecretArnList': ['secret-arn']}

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with info_type='scram_secrets' and kwargs
        result = tool_func(
            region='us-west-2',
            cluster_arn='test-cluster-arn',
            info_type='scram_secrets',
            kwargs={'max_results': 5, 'next_token': 'token'},
        )

        # Verify list_scram_secrets was called correctly with kwargs
        mock_client.list_scram_secrets.assert_called_once_with(
            ClusterArn='test-cluster-arn', MaxResults=5, NextToken='token'
        )

        # Verify the result
        self.assertEqual(result, {'SecretArnList': ['secret-arn']})

    @patch('boto3.client')
    def test_get_cluster_info_invalid_type(self, mock_boto3_client):
        """Test the get_cluster_info function with an invalid info_type."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Register the module
        register_module(mock_mcp)

        # Get the tool function
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Call the tool function with an invalid info_type
        with self.assertRaises(ValueError) as context:
            tool_func(region='us-west-2', cluster_arn='test-cluster-arn', info_type='invalid')

        # Verify the error message
        self.assertIn('Unsupported info_type', str(context.exception))


if __name__ == '__main__':
    unittest.main()
