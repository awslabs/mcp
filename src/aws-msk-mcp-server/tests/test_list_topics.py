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

"""Tests for the list_topics module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_topics.list_topics import list_topics
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListTopics:
    """Tests for the list_topics module."""

    def test_list_topics_basic(self):
        """Test the list_topics function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        expected_response = {
            'topics': [
                {
                    'topicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic-1',
                    'topicName': 'test-topic-1',
                    'partitionCount': 3,
                    'replicationFactor': 2,
                    'outOfSyncReplicaCount': 0,
                },
                {
                    'topicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic-2',
                    'topicName': 'test-topic-2',
                    'partitionCount': 5,
                    'replicationFactor': 3,
                    'outOfSyncReplicaCount': 0,
                },
            ]
        }
        mock_client.list_topics.return_value = expected_response

        # Act
        result = list_topics(cluster_arn, mock_client)

        # Assert
        mock_client.list_topics.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'topics' in result
        assert len(result['topics']) == 2
        assert result['topics'][0]['topicName'] == 'test-topic-1'
        assert result['topics'][1]['topicName'] == 'test-topic-2'

    def test_list_topics_with_filter(self):
        """Test the list_topics function with topic name filter."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_filter = 'test'
        expected_response = {
            'topics': [
                {
                    'topicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic-1',
                    'topicName': 'test-topic-1',
                    'partitionCount': 3,
                    'replicationFactor': 2,
                    'outOfSyncReplicaCount': 0,
                }
            ]
        }
        mock_client.list_topics.return_value = expected_response

        # Act
        result = list_topics(cluster_arn, mock_client, topic_name_filter=topic_filter)

        # Assert
        mock_client.list_topics.assert_called_once_with(
            ClusterArn=cluster_arn, TopicNameFilter=topic_filter
        )
        assert result == expected_response
        assert len(result['topics']) == 1

    def test_list_topics_with_pagination(self):
        """Test the list_topics function with pagination parameters."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        max_results = 10
        next_token = 'next-token-value'
        expected_response = {
            'topics': [
                {
                    'topicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic-1',
                    'topicName': 'test-topic-1',
                    'partitionCount': 3,
                    'replicationFactor': 2,
                    'outOfSyncReplicaCount': 0,
                }
            ],
            'nextToken': 'another-token',
        }
        mock_client.list_topics.return_value = expected_response

        # Act
        result = list_topics(
            cluster_arn, mock_client, max_results=max_results, next_token=next_token
        )

        # Assert
        mock_client.list_topics.assert_called_once_with(
            ClusterArn=cluster_arn, MaxResults=max_results, NextToken=next_token
        )
        assert result == expected_response
        assert 'nextToken' in result

    def test_list_topics_empty_response(self):
        """Test the list_topics function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        expected_response = {'topics': []}
        mock_client.list_topics.return_value = expected_response

        # Act
        result = list_topics(cluster_arn, mock_client)

        # Assert
        mock_client.list_topics.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'topics' in result
        assert len(result['topics']) == 0

    def test_list_topics_error(self):
        """Test the list_topics function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        mock_client.list_topics.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Cluster not found'}}, 'ListTopics'
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            list_topics(cluster_arn, mock_client)

        # Verify the error
        assert 'NotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)
        mock_client.list_topics.assert_called_once_with(ClusterArn=cluster_arn)

    def test_list_topics_missing_client(self):
        """Test the list_topics function with a missing client."""
        # Arrange
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            list_topics(cluster_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
