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

"""Unit tests for the create_cluster_tool in mutate_cluster register_module."""

import json
import unittest
from awslabs.aws_msk_mcp_server.tools.mutate_cluster.register_module import register_module
from unittest.mock import Mock, patch


class TestMutateClusterCreateClusterTool(unittest.TestCase):
    """Tests for the create_cluster_tool in mutate_cluster register_module."""

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
    def test_create_cluster_tool_with_various_inputs(self, mock_boto3_client):
        """Test the create_cluster_tool function with various inputs."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        # Create a mock client with a mock create_cluster_v2 method
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up the mock return value for create_cluster_v2
        expected_result = {
            'ClusterArn': 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster',
            'ClusterName': 'test-cluster',
            'State': 'CREATING',
        }
        mock_client.create_cluster_v2.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the create_cluster_tool function
        create_cluster_tool = self._extract_tool_function(mock_tool_decorator)
        self.assertIsNotNone(create_cluster_tool, 'Could not find create_cluster_tool function')

        # Common test data
        region = 'us-west-2'
        cluster_name = 'test-cluster'

        # Define test cases
        test_cases = [
            {
                'name': 'valid_json_kwargs',
                'cluster_type': 'PROVISIONED',
                'kwargs': json.dumps(
                    {
                        'broker_node_group_info': {
                            'InstanceType': 'kafka.m5.large',
                            'ClientSubnets': ['subnet-1', 'subnet-2', 'subnet-3'],
                            'SecurityGroups': ['sg-123'],
                            'StorageInfo': {'EbsStorageInfo': {'VolumeSize': 100}},
                        },
                        'kafka_version': '2.8.1',
                        'number_of_broker_nodes': 3,
                    }
                ),
                'expected_params': {
                    'cluster_type': 'Provisioned',
                    'expected_keys': [
                        'BrokerNodeGroupInfo',
                        'KafkaVersion',
                        'NumberOfBrokerNodes',
                    ],
                    'unexpected_keys': ['Serverless'],
                },
            },
            {
                'name': 'dict_kwargs',
                'cluster_type': 'PROVISIONED',
                'kwargs': {  # Direct dictionary instead of JSON string
                    'broker_node_group_info': {
                        'InstanceType': 'kafka.m5.large',
                        'ClientSubnets': ['subnet-1', 'subnet-2', 'subnet-3'],
                        'SecurityGroups': ['sg-123'],
                        'StorageInfo': {'EbsStorageInfo': {'VolumeSize': 100}},
                    },
                    'kafka_version': '2.8.1',
                    'number_of_broker_nodes': 3,
                },
                'expected_params': {
                    'cluster_type': 'Provisioned',
                    'expected_keys': [
                        'BrokerNodeGroupInfo',
                        'KafkaVersion',
                        'NumberOfBrokerNodes',
                    ],
                    'unexpected_keys': ['Serverless'],
                },
            },
            {
                'name': 'empty_kwargs',
                'cluster_type': 'PROVISIONED',
                'kwargs': '',
                'expected_params': {
                    'cluster_type': 'Provisioned',
                    'expected_keys': [],
                    'unexpected_keys': ['Serverless'],
                },
            },
            {
                'name': 'invalid_json_kwargs',
                'cluster_type': 'PROVISIONED',
                'kwargs': '{"this is not valid JSON',
                'expected_params': {
                    'cluster_type': 'Provisioned',
                    'expected_keys': [],
                    'unexpected_keys': ['Serverless'],
                },
            },
            {
                'name': 'none_kwargs',
                'cluster_type': 'PROVISIONED',
                'kwargs': None,
                'expected_params': {
                    'cluster_type': 'Provisioned',
                    'expected_keys': [],
                    'unexpected_keys': ['Serverless'],
                },
            },
            {
                'name': 'serverless_cluster',
                'cluster_type': 'SERVERLESS',
                'kwargs': json.dumps(
                    {
                        'vpc_configs': [
                            {
                                'SubnetIds': ['subnet-1', 'subnet-2', 'subnet-3'],
                                'SecurityGroupIds': ['sg-123'],
                            }
                        ]
                    }
                ),
                'expected_params': {
                    'cluster_type': 'Serverless',
                    'expected_keys': ['VpcConfigs'],
                    'unexpected_keys': ['Provisioned'],
                },
            },
        ]

        # Run each test case
        for test_case in test_cases:
            with self.subTest(test_case['name']):
                # Reset mock for each test case
                mock_client.reset_mock()

                # Call the tool function with the test case inputs
                result = create_cluster_tool(
                    region=region,
                    cluster_name=cluster_name,
                    cluster_type=test_case['cluster_type'],
                    kwargs=test_case['kwargs'],
                )

                # Verify create_cluster_v2 was called
                mock_client.create_cluster_v2.assert_called_once()

                # Check the parameters passed to create_cluster_v2
                call_args = mock_client.create_cluster_v2.call_args[1]
                self.assertEqual(call_args['ClusterName'], cluster_name)

                # Check for expected cluster type and parameters
                expected_cluster_type = test_case['expected_params']['cluster_type']
                self.assertIn(expected_cluster_type, call_args)

                # Check for expected keys in the cluster type parameters
                cluster_params = call_args[expected_cluster_type]
                for key in test_case['expected_params']['expected_keys']:
                    self.assertIn(key, cluster_params)

                # Check that unexpected keys are not present
                for key in test_case['expected_params']['unexpected_keys']:
                    self.assertNotIn(key, call_args)

                # Verify the result
                self.assertEqual(result, expected_result)

        # Verify boto3 client was created correctly (only need to check once)
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], region)
        self.assertIn('config', mock_boto3_client.call_args[1])


if __name__ == '__main__':
    unittest.main()
