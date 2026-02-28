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

"""Tests for the delete_topic module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_topics.delete_topic import delete_topic
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDeleteTopic:
    """Tests for the delete_topic module."""

    def test_delete_topic_success(self):
        """Test the delete_topic function with successful deletion."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        confirm_delete = 'DELETE'
        expected_response = {
            'TopicArn': 'arn:aws:kafka:us-east-1:123456789012:topic/test-cluster/abcdef/test-topic',
            'TopicName': 'test-topic',
            'Status': 'DELETING',
        }
        mock_client.delete_topic.return_value = expected_response

        # Act
        result = delete_topic(cluster_arn, topic_name, mock_client, confirm_delete)

        # Assert
        mock_client.delete_topic.assert_called_once_with(
            ClusterArn=cluster_arn, TopicName=topic_name
        )
        assert result == expected_response
        assert result['Status'] == 'DELETING'

    def test_delete_topic_without_confirmation(self):
        """Test the delete_topic function without confirmation."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        confirm_delete = None

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            delete_topic(cluster_arn, topic_name, mock_client, confirm_delete)

        # Verify the error
        assert 'Safety confirmation required' in str(excinfo.value)
        assert 'DELETE' in str(excinfo.value)
        mock_client.delete_topic.assert_not_called()

    def test_delete_topic_wrong_confirmation(self):
        """Test the delete_topic function with wrong confirmation string."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        confirm_delete = 'delete'  # lowercase, not accepted

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            delete_topic(cluster_arn, topic_name, mock_client, confirm_delete)

        # Verify the error
        assert 'Safety confirmation required' in str(excinfo.value)
        mock_client.delete_topic.assert_not_called()

    def test_delete_topic_system_topic_consumer(self):
        """Test the delete_topic function rejects system topics with __consumer prefix."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = '__consumer_offsets'
        confirm_delete = 'DELETE'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            delete_topic(cluster_arn, topic_name, mock_client, confirm_delete)

        # Verify the error
        assert 'Cannot delete topic' in str(excinfo.value)
        assert 'system prefixes' in str(excinfo.value)
        mock_client.delete_topic.assert_not_called()

    def test_delete_topic_system_topic_amazon(self):
        """Test the delete_topic function rejects system topics with __amazon prefix."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = '__amazon_msk_canary'
        confirm_delete = 'DELETE'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            delete_topic(cluster_arn, topic_name, mock_client, confirm_delete)

        # Verify the error
        assert 'Cannot delete topic' in str(excinfo.value)
        assert 'protected from deletion' in str(excinfo.value)
        mock_client.delete_topic.assert_not_called()

    def test_delete_topic_allows_regular_underscore_topics(self):
        """Test the delete_topic function allows topics with single underscore."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = '_regular_topic'
        confirm_delete = 'DELETE'

        # Act - should NOT raise, regular underscore topics are allowed
        confirm_delete = 'DELETE'
        expected_response = {'TopicArn': 'arn:test', 'Status': 'DELETING'}
        mock_client.delete_topic.return_value = expected_response

        result = delete_topic(cluster_arn, topic_name, mock_client, confirm_delete)

        # Assert - should succeed
        mock_client.delete_topic.assert_called_once()
        assert result == expected_response

    def test_delete_topic_not_found(self):
        """Test the delete_topic function when topic doesn't exist."""
        # Arrange
        mock_client = MagicMock()
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'nonexistent-topic'
        confirm_delete = 'DELETE'
        mock_client.delete_topic.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'Topic not found'}}, 'DeleteTopic'
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            delete_topic(cluster_arn, topic_name, mock_client, confirm_delete)

        # Verify the error
        assert 'NotFoundException' in str(excinfo.value)

    def test_delete_topic_missing_client(self):
        """Test the delete_topic function with missing client."""
        # Arrange
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'test-topic'
        confirm_delete = 'DELETE'

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            delete_topic(cluster_arn, topic_name, None, confirm_delete)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
