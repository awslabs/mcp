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

"""Tests for the create_replicator module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.replicator.create_replicator import create_replicator
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestCreateReplicator:
    """Tests for the create_replicator module."""

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

    def test_create_replicator_error(self):
        """Test the create_replicator function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.create_replicator.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameters'}},
            'CreateReplicator',
        )

        # Act & Assert
        replicator_name = 'test-replicator'
        source_kafka_cluster_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster/source-cluster/abcdef'
        )
        target_kafka_cluster_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster/target-cluster/abcdef'
        )
        service_execution_role_arn = 'arn:aws:iam::123456789012:role/test-role'

        with pytest.raises(ClientError) as excinfo:
            create_replicator(
                replicator_name,
                source_kafka_cluster_arn,
                target_kafka_cluster_arn,
                service_execution_role_arn,
                mock_client,
            )

        # Verify the error
        assert 'ValidationException' in str(excinfo.value)
        assert 'Invalid parameters' in str(excinfo.value)
        mock_client.create_replicator.assert_called_once()

    def test_create_replicator_missing_client(self):
        """Test the create_replicator function with a missing client."""
        # Act & Assert
        replicator_name = 'test-replicator'
        source_kafka_cluster_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster/source-cluster/abcdef'
        )
        target_kafka_cluster_arn = (
            'arn:aws:kafka:us-east-1:123456789012:cluster/target-cluster/abcdef'
        )
        service_execution_role_arn = 'arn:aws:iam::123456789012:role/test-role'

        with pytest.raises(ValueError) as excinfo:
            create_replicator(
                replicator_name,
                source_kafka_cluster_arn,
                target_kafka_cluster_arn,
                service_execution_role_arn,
                None,
            )

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
