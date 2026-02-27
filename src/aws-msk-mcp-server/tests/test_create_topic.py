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

"""Tests for the create_topic module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_topics.create_topic import create_topic
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestCreateTopic:
    """Tests for the create_topic module."""

    def test_create_topic_success(self):
        """Test the create_topic function with successful response."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'new-topic'
        partition_count = 3
        replication_factor = 2
        expected_response = {
            'TopicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/new-topic',
            'TopicName': 'new-topic',
            'Status': 'CREATING',
        }
        mock_client.create_topic.return_value = expected_response

        # Act
        result = create_topic(
            cluster_arn, topic_name, partition_count, replication_factor, mock_client
        )

        # Assert
        mock_client.create_topic.assert_called_once_with(
            ClusterArn=cluster_arn,
            TopicName=topic_name,
            PartitionCount=partition_count,
            ReplicationFactor=replication_factor,
        )
        assert result == expected_response
        assert result['TopicName'] == 'new-topic'
        assert result['Status'] == 'CREATING'

    def test_create_topic_with_configs(self):
        """Test the create_topic function with custom configurations."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'configured-topic'
        partition_count = 5
        replication_factor = 3
        configs = 'eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0='
        expected_response = {
            'TopicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/configured-topic',
            'TopicName': 'configured-topic',
            'Status': 'CREATING',
        }
        mock_client.create_topic.return_value = expected_response

        # Act
        result = create_topic(
            cluster_arn, topic_name, partition_count, replication_factor, mock_client, configs
        )

        # Assert
        mock_client.create_topic.assert_called_once_with(
            ClusterArn=cluster_arn,
            TopicName=topic_name,
            PartitionCount=partition_count,
            ReplicationFactor=replication_factor,
            Configs=configs,
        )
        assert result == expected_response

    def test_create_topic_already_exists(self):
        """Test the create_topic function when topic already exists."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'existing-topic'
        partition_count = 3
        replication_factor = 2
        mock_client.create_topic.side_effect = ClientError(
            {'Error': {'Code': 'ConflictException', 'Message': 'Topic already exists'}},
            'CreateTopic',
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            create_topic(cluster_arn, topic_name, partition_count, replication_factor, mock_client)

        # Verify the error
        assert 'ConflictException' in str(excinfo.value)

    def test_create_topic_missing_client(self):
        """Test the create_topic function with missing client."""
        # Arrange
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'new-topic'
        partition_count = 3
        replication_factor = 2

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            create_topic(cluster_arn, topic_name, partition_count, replication_factor, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
