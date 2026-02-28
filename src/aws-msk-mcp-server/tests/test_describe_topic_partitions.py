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

"""Tests for the describe_topic_partitions module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_topics.describe_topic_partitions import (
    describe_topic_partitions,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeTopicPartitions:
    """Tests for the describe_topic_partitions module."""

    def test_describe_topic_partitions_success(self):
        """Test the describe_topic_partitions function with successful response."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        expected_response = {
            'Partitions': [
                {'Partition': 0, 'Leader': 1, 'Replicas': [1, 2], 'Isr': [1, 2]},
                {'Partition': 1, 'Leader': 2, 'Replicas': [2, 3], 'Isr': [2, 3]},
                {'Partition': 2, 'Leader': 3, 'Replicas': [3, 1], 'Isr': [3, 1]},
            ]
        }
        mock_client.describe_topic_partitions.return_value = expected_response

        # Act
        result = describe_topic_partitions(cluster_arn, topic_name, mock_client)

        # Assert
        mock_client.describe_topic_partitions.assert_called_once_with(
            ClusterArn=cluster_arn, TopicName=topic_name
        )
        assert result == expected_response
        assert len(result['Partitions']) == 3
        assert result['Partitions'][0]['Partition'] == 0
        assert result['Partitions'][0]['Leader'] == 1

    def test_describe_topic_partitions_with_pagination(self):
        """Test the describe_topic_partitions function with pagination."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        max_results = 2
        next_token = 'token-value'
        expected_response = {
            'Partitions': [
                {'Partition': 0, 'Leader': 1, 'Replicas': [1, 2], 'Isr': [1, 2]},
                {'Partition': 1, 'Leader': 2, 'Replicas': [2, 3], 'Isr': [2, 3]},
            ],
            'NextToken': 'next-token-value',
        }
        mock_client.describe_topic_partitions.return_value = expected_response

        # Act
        result = describe_topic_partitions(
            cluster_arn, topic_name, mock_client, max_results=max_results, next_token=next_token
        )

        # Assert
        mock_client.describe_topic_partitions.assert_called_once_with(
            ClusterArn=cluster_arn,
            TopicName=topic_name,
            MaxResults=max_results,
            NextToken=next_token,
        )
        assert result == expected_response
        assert 'NextToken' in result

    def test_describe_topic_partitions_error(self):
        """Test the describe_topic_partitions function when API call fails."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        mock_client.describe_topic_partitions.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Topic not found'}},
            'DescribeTopicPartitions',
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            describe_topic_partitions(cluster_arn, topic_name, mock_client)

        # Verify the error
        assert 'NotFoundException' in str(excinfo.value)

    def test_describe_topic_partitions_missing_client(self):
        """Test the describe_topic_partitions function with missing client."""
        # Arrange
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            describe_topic_partitions(cluster_arn, topic_name, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
