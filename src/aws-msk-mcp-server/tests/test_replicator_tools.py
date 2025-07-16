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

"""Tests for the replicator tools module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.replicator import (
    create_replicator,
    describe_replicator,
    list_replicators,
    register_module,
)
from unittest.mock import MagicMock


class TestReplicatorTools:
    """Tests for the replicator tools module."""

    def test_register_module(self):
        """Test the register_module function."""
        # Arrange
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock()

        # Act
        register_module(mock_mcp)

        # Assert
        assert mock_mcp.tool.call_count == 3
        # Verify tool registrations
        tool_calls = mock_mcp.tool.call_args_list
        assert tool_calls[0][1]['name'] == 'describe_replicator'
        assert tool_calls[1][1]['name'] == 'create_replicator'
        assert tool_calls[2][1]['name'] == 'list_replicators'


class TestDescribeReplicator:
    """Tests for the describe_replicator function."""

    def test_describe_replicator_basic(self):
        """Test the describe_replicator function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ReplicatorInfo': {
                'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef',
                'ReplicatorName': 'test-replicator',
                'KafkaClusters': [
                    {
                        'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/source-cluster/abcdef',
                        'Role': 'SOURCE',
                    },
                    {
                        'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/target-cluster/abcdef',
                        'Role': 'TARGET',
                    },
                ],
                'ReplicationInfoList': [
                    {
                        'TopicName': 'test-topic',
                        'TopicNamePrefix': 'test-',
                        'TargetCompressionType': 'NONE',
                    }
                ],
                'ServiceExecutionRoleArn': 'arn:aws:iam::123456789012:role/test-role',
                'ReplicatorState': 'ACTIVE',
                'CreationTime': '2025-06-20T10:00:00.000Z',
                'CurrentVersion': '1',
            }
        }
        mock_client.describe_replicator.return_value = expected_response

        # Act
        replicator_arn = 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef'
        result = describe_replicator(replicator_arn, mock_client)

        # Assert
        mock_client.describe_replicator.assert_called_once_with(ReplicatorArn=replicator_arn)
        assert result == expected_response

    def test_describe_replicator_missing_client(self):
        """Test the describe_replicator function with a missing client."""
        # Act & Assert
        replicator_arn = 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef'
        with pytest.raises(ValueError) as excinfo:
            describe_replicator(replicator_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)


class TestCreateReplicator:
    """Tests for the create_replicator function."""

    def test_create_replicator_basic(self):
        """Test the create_replicator function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef',
            'ReplicatorName': 'test-replicator',
            'ReplicatorState': 'CREATING',
            'CreationTime': '2025-06-20T10:00:00.000Z',
        }
        mock_client.create_replicator.return_value = expected_response

        # Act
        replicator_name = 'test-replicator'
        source_kafka_cluster_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster/source-cluster/abcdef'
        )
        target_kafka_cluster_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster/target-cluster/abcdef'
        )
        service_execution_role_arn = 'arn:aws:iam::123456789012:role/test-role'

        result = create_replicator(
            replicator_name,
            source_kafka_cluster_arn,
            target_kafka_cluster_arn,
            service_execution_role_arn,
            mock_client,
        )

        # Assert
        mock_client.create_replicator.assert_called_once()
        call_args = mock_client.create_replicator.call_args[1]
        assert call_args['ReplicatorName'] == replicator_name
        assert call_args['SourceKafkaClusterArn'] == source_kafka_cluster_arn
        assert call_args['TargetKafkaClusterArn'] == target_kafka_cluster_arn
        assert call_args['ServiceExecutionRoleArn'] == service_execution_role_arn
        assert result == expected_response

    def test_create_replicator_with_optional_params(self):
        """Test the create_replicator function with optional parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef',
            'ReplicatorName': 'test-replicator',
            'ReplicatorState': 'CREATING',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'Tags': {'Environment': 'Test', 'Owner': 'Team'},
        }
        mock_client.create_replicator.return_value = expected_response

        # Act
        replicator_name = 'test-replicator'
        source_kafka_cluster_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster/source-cluster/abcdef'
        )
        target_kafka_cluster_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster/target-cluster/abcdef'
        )
        service_execution_role_arn = 'arn:aws:iam::123456789012:role/test-role'

        kafka_clusters = {
            'SourceKafkaCluster': {
                'AmazonMskCluster': {'MskClusterArn': source_kafka_cluster_arn}
            },
            'TargetKafkaCluster': {
                'AmazonMskCluster': {'MskClusterArn': target_kafka_cluster_arn}
            },
        }

        replication_info_list = [{'TopicName': 'test-topic', 'TargetCompressionType': 'NONE'}]

        tags = {'Environment': 'Test', 'Owner': 'Team'}

        result = create_replicator(
            replicator_name,
            source_kafka_cluster_arn,
            target_kafka_cluster_arn,
            service_execution_role_arn,
            mock_client,
            kafka_clusters,
            replication_info_list,
            tags,
        )

        # Assert
        mock_client.create_replicator.assert_called_once()
        call_args = mock_client.create_replicator.call_args[1]
        assert call_args['ReplicatorName'] == replicator_name
        assert call_args['SourceKafkaClusterArn'] == source_kafka_cluster_arn
        assert call_args['TargetKafkaClusterArn'] == target_kafka_cluster_arn
        assert call_args['ServiceExecutionRoleArn'] == service_execution_role_arn
        assert call_args['KafkaClusters'] == kafka_clusters
        assert call_args['ReplicationInfoList'] == replication_info_list
        assert call_args['Tags'] == tags
        assert result == expected_response


class TestListReplicators:
    """Tests for the list_replicators function."""

    def test_list_replicators_basic(self):
        """Test the list_replicators function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ReplicatorInfoList': [
                {
                    'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator-1/abcdef',
                    'ReplicatorName': 'test-replicator-1',
                    'ReplicatorState': 'ACTIVE',
                    'CreationTime': '2025-06-20T10:00:00.000Z',
                },
                {
                    'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator-2/abcdef',
                    'ReplicatorName': 'test-replicator-2',
                    'ReplicatorState': 'CREATING',
                    'CreationTime': '2025-06-20T11:00:00.000Z',
                },
            ]
        }
        mock_client.list_replicators.return_value = expected_response

        # Act
        result = list_replicators(mock_client)

        # Assert
        mock_client.list_replicators.assert_called_once_with()
        assert result == expected_response

    def test_list_replicators_with_pagination(self):
        """Test the list_replicators function with pagination parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ReplicatorInfoList': [
                {
                    'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator-3/abcdef',
                    'ReplicatorName': 'test-replicator-3',
                    'ReplicatorState': 'ACTIVE',
                    'CreationTime': '2025-06-20T12:00:00.000Z',
                }
            ],
            'NextToken': 'next-token-value',
        }
        mock_client.list_replicators.return_value = expected_response

        # Act
        max_results = 10
        next_token = 'token-value'
        result = list_replicators(mock_client, max_results, next_token)

        # Assert
        mock_client.list_replicators.assert_called_once_with(
            MaxResults=max_results, NextToken=next_token
        )
        assert result == expected_response
