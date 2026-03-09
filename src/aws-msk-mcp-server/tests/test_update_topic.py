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

"""Tests for the update_topic module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_topics.update_topic import update_topic
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestUpdateTopic:
    """Tests for the update_topic module."""

    def test_update_topic_configs_only(self):
        """Test the update_topic function with only config updates."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        configs = 'eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0='
        expected_response = {
            'TopicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic',
            'TopicName': 'test-topic',
            'Status': 'UPDATING',
        }
        mock_client.update_topic.return_value = expected_response

        # Act
        result = update_topic(cluster_arn, topic_name, mock_client, configs=configs)

        # Assert
        mock_client.update_topic.assert_called_once_with(
            ClusterArn=cluster_arn, TopicName=topic_name, Configs=configs
        )
        assert result == expected_response
        assert result['Status'] == 'UPDATING'

    def test_update_topic_partition_count_only(self):
        """Test the update_topic function with only partition count update."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        partition_count = 10
        expected_response = {
            'TopicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic',
            'TopicName': 'test-topic',
            'Status': 'UPDATING',
        }
        mock_client.update_topic.return_value = expected_response

        # Act
        result = update_topic(
            cluster_arn, topic_name, mock_client, partition_count=partition_count
        )

        # Assert
        mock_client.update_topic.assert_called_once_with(
            ClusterArn=cluster_arn, TopicName=topic_name, PartitionCount=partition_count
        )
        assert result == expected_response

    def test_update_topic_both_params(self):
        """Test the update_topic function with both configs and partition count."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        configs = 'eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0='
        partition_count = 10
        expected_response = {
            'TopicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic',
            'TopicName': 'test-topic',
            'Status': 'UPDATING',
        }
        mock_client.update_topic.return_value = expected_response

        # Act
        result = update_topic(
            cluster_arn, topic_name, mock_client, configs=configs, partition_count=partition_count
        )

        # Assert
        mock_client.update_topic.assert_called_once_with(
            ClusterArn=cluster_arn,
            TopicName=topic_name,
            Configs=configs,
            PartitionCount=partition_count,
        )
        assert result == expected_response

    def test_update_topic_not_found(self):
        """Test the update_topic function when topic is not found."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'nonexistent-topic'
        configs = 'eyJjbGVhbnVwLnBvbGljeSI6ICJjb21wYWN0In0='
        mock_client.update_topic.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Topic not found'}}, 'UpdateTopic'
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            update_topic(cluster_arn, topic_name, mock_client, configs=configs)

        # Verify the error
        assert 'NotFoundException' in str(excinfo.value)

    def test_update_topic_missing_client(self):
        """Test the update_topic function with missing client."""
        # Arrange
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            update_topic(cluster_arn, topic_name, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
