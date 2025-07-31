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

"""Unit tests for the replicator register_module."""

import unittest
from awslabs.aws_msk_mcp_server.tools.replicator.register_module import register_module
from unittest.mock import Mock, call, patch


class TestReplicatorRegisterModule(unittest.TestCase):
    """Tests for the replicator register_module."""

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
            call(name='describe_replicator'),
            call(name='create_replicator'),
            call(name='list_replicators'),
        ]
        mock_mcp.tool.assert_has_calls(expected_tool_calls, any_order=True)
        self.assertEqual(mock_mcp.tool.call_count, len(expected_tool_calls))

    @patch('boto3.client')
    def test_describe_replicator_tool(self, mock_boto3_client):
        """Test the describe_replicator_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return value
        expected_result = {
            'ReplicatorInfo': {
                'ReplicatorArn': 'arn:aws:kafka:us-west-2:123456789012:replicator/test-replicator',
                'ReplicatorName': 'test-replicator',
                'ReplicatorState': 'RUNNING',
            }
        }
        mock_client.describe_replicator.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (first registered tool)
        tool_func = mock_tool_decorator.call_args_list[0][0][0]

        # Call the tool function
        replicator_arn = 'arn:aws:kafka:us-west-2:123456789012:replicator/test-replicator'
        result = tool_func(region='us-west-2', replicator_arn=replicator_arn)

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify describe_replicator was called
        mock_client.describe_replicator.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_create_replicator_tool(self, mock_boto3_client):
        """Test the create_replicator_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return value
        expected_result = {
            'ReplicatorArn': 'arn:aws:kafka:us-west-2:123456789012:replicator/test-replicator',
            'ReplicatorName': 'test-replicator',
            'ReplicatorState': 'CREATING',
        }
        mock_client.create_replicator.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (second registered tool)
        tool_func = mock_tool_decorator.call_args_list[1][0][0]

        # Test data
        replicator_name = 'test-replicator'
        source_kafka_cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/source-cluster'
        target_kafka_cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/target-cluster'
        service_execution_role_arn = 'arn:aws:iam::123456789012:role/MSKReplicatorRole'

        # Optional parameters
        kafka_clusters = {
            'KafkaClusters': [
                {
                    'AmazonMskCluster': {'MskClusterArn': source_kafka_cluster_arn},
                    'VpcConfig': {
                        'SecurityGroupIds': ['sg-12345'],
                        'SubnetIds': ['subnet-12345', 'subnet-67890'],
                    },
                },
                {
                    'AmazonMskCluster': {'MskClusterArn': target_kafka_cluster_arn},
                    'VpcConfig': {
                        'SecurityGroupIds': ['sg-67890'],
                        'SubnetIds': ['subnet-abcde', 'subnet-fghij'],
                    },
                },
            ]
        }

        replication_info_list = [
            {
                'SourceKafkaClusterArn': source_kafka_cluster_arn,
                'TargetKafkaClusterArn': target_kafka_cluster_arn,
                'TopicReplication': {
                    'CopyAccessControlListsForTopics': True,
                    'CopyTopicConfigurations': True,
                    'DetectAndCopyNewTopics': True,
                    'TopicsToExclude': ['exclude-topic'],
                },
            }
        ]

        tags = {'Environment': 'Test', 'Owner': 'TestTeam'}

        # Call the tool function
        result = tool_func(
            region='us-west-2',
            replicator_name=replicator_name,
            source_kafka_cluster_arn=source_kafka_cluster_arn,
            target_kafka_cluster_arn=target_kafka_cluster_arn,
            service_execution_role_arn=service_execution_role_arn,
            kafka_clusters=kafka_clusters,
            replication_info_list=replication_info_list,
            tags=tags,
        )

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify create_replicator was called
        mock_client.create_replicator.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('boto3.client')
    def test_list_replicators_tool(self, mock_boto3_client):
        """Test the list_replicators_tool function."""
        # Setup
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # Set up mock return value
        expected_result = {
            'ReplicatorInfoList': [
                {
                    'ReplicatorArn': 'arn:aws:kafka:us-west-2:123456789012:replicator/replicator-1',
                    'ReplicatorName': 'replicator-1',
                    'ReplicatorState': 'RUNNING',
                },
                {
                    'ReplicatorArn': 'arn:aws:kafka:us-west-2:123456789012:replicator/replicator-2',
                    'ReplicatorName': 'replicator-2',
                    'ReplicatorState': 'CREATING',
                },
            ],
            'NextToken': 'AAAABBBCCC',
        }
        mock_client.list_replicators.return_value = expected_result

        # Register the module
        register_module(mock_mcp)

        # Get the tool function (third registered tool)
        tool_func = mock_tool_decorator.call_args_list[2][0][0]

        # Call the tool function with optional parameters
        result = tool_func(region='us-west-2', max_results=10, next_token='token')

        # Verify boto3 client was created correctly
        mock_boto3_client.assert_called_once()
        self.assertEqual(mock_boto3_client.call_args[0][0], 'kafka')
        self.assertEqual(mock_boto3_client.call_args[1]['region_name'], 'us-west-2')
        self.assertIn('config', mock_boto3_client.call_args[1])

        # Verify list_replicators was called
        mock_client.list_replicators.assert_called_once()

        # Verify the result
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
