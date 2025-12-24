"""Tests for the describe_topic module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_topic.describe_topic import describe_topic
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeTopic:
    def test_describe_topic_basic(self):
        mock_client = MagicMock()
        expected_response = {
            'TopicInfo': {
                'TopicName': 'topic-a',
                'TopicArn': 'arn:topic:a',
                'Partitions': 3,
                'Configs': {'retention.ms': '604800000'},
            }
        }
        mock_client.describe_topic.return_value = expected_response

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'topic-a'
        result = describe_topic(cluster_arn, topic_name, mock_client)

        mock_client.describe_topic.assert_called_once_with(ClusterArn=cluster_arn, TopicName=topic_name)
        assert result == expected_response

    def test_describe_topic_error(self):
        mock_client = MagicMock()
        mock_client.describe_topic.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Topic not found'}},
            'DescribeTopic',
        )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'missing-topic'
        with pytest.raises(ClientError) as excinfo:
            describe_topic(cluster_arn, topic_name, mock_client)

        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Topic not found' in str(excinfo.value)
        mock_client.describe_topic.assert_called_once_with(ClusterArn=cluster_arn, TopicName=topic_name)

    def test_describe_topic_missing_client(self):
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        topic_name = 'topic-a'
        with pytest.raises(ValueError) as excinfo:
            describe_topic(cluster_arn, topic_name, None)

        assert 'Client must be provided' in str(excinfo.value)
