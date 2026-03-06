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

"""Tests for the describe_topic module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_topics.describe_topic import describe_topic
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeTopic:
    """Tests for the describe_topic module."""

    def test_describe_topic_success(self):
        """Test the describe_topic function with successful response."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        expected_response = {
            'TopicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic',
            'TopicName': 'test-topic',
            'PartitionCount': 3,
            'ReplicationFactor': 2,
            'Status': 'ACTIVE',
            'Configs': 'eyJjbGVhbnVwLnBvbGljeSI6ICJkZWxldGUifQ==',  # pragma: allowlist secret - base64 test data, not actual secret
        }
        mock_client.describe_topic.return_value = expected_response

        # Act
        result = describe_topic(cluster_arn, topic_name, mock_client)

        # Assert
        mock_client.describe_topic.assert_called_once_with(
            ClusterArn=cluster_arn, TopicName=topic_name
        )
        assert result == expected_response
        assert result['TopicName'] == 'test-topic'
        assert result['PartitionCount'] == 3
        assert result['Status'] == 'ACTIVE'

    def test_describe_topic_not_found(self):
        """Test the describe_topic function when topic is not found."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'nonexistent-topic'
        mock_client.describe_topic.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Topic not found'}},
            'DescribeTopic',
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            describe_topic(cluster_arn, topic_name, mock_client)

        # Verify the error
        assert 'NotFoundException' in str(excinfo.value)
        assert 'Topic not found' in str(excinfo.value)

    def test_describe_topic_missing_client(self):
        """Test the describe_topic function with a missing client."""
        # Arrange
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            describe_topic(cluster_arn, topic_name, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
