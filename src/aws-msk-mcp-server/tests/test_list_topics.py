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
from awslabs.aws_msk_mcp_server.tools.read_topic.list_topics import list_topics
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestListTopics:
    def test_list_topics_basic(self):
        mock_client = MagicMock()
        expected_response = {
            'TopicInfoList': [
                {'TopicName': 'topic-a', 'TopicArn': 'arn:topic:a'},
                {'TopicName': 'topic-b', 'TopicArn': 'arn:topic:b'},
            ]
        }
        mock_client.list_topics.return_value = expected_response

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = list_topics(cluster_arn, mock_client)

        mock_client.list_topics.assert_called_once_with(ClusterArn=cluster_arn, MaxResults=10)
        assert result == expected_response
        assert len(result['TopicInfoList']) == 2

    def test_list_topics_error(self):
        mock_client = MagicMock()
        mock_client.list_topics.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Cluster not found'}},
            'ListTopics',
        )

        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            list_topics(cluster_arn, mock_client)

        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)
        mock_client.list_topics.assert_called_once_with(ClusterArn=cluster_arn, MaxResults=10)

    def test_list_topics_missing_client(self):
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            list_topics(cluster_arn, None)

        assert 'Client must be provided' in str(excinfo.value)
