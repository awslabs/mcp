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

"""Tests for the read_topics/__init__.py module."""

from awslabs.aws_msk_mcp_server.tools.read_topics import register_module
from mcp.server.fastmcp import FastMCP
from typing import cast
from unittest.mock import MagicMock, patch


class TestReadTopicsInit:
    """Tests for the read_topics/__init__.py module."""

    def test_register_module(self):
        """Test the register_module function registers all tools."""
        # Arrange
        mock_mcp = MagicMock(spec=FastMCP)

        # Act
        register_module(mock_mcp)

        # Assert
        assert mock_mcp.tool.call_count == 3
        tool_names = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
        assert 'list_topics' in tool_names
        assert 'describe_topic' in tool_names
        assert 'describe_topic_partitions' in tool_names

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.list_topics')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.__version__', '1.0.0')
    def test_list_topics_tool_with_all_params(
        self, mock_config, mock_list_topics, mock_boto3_client
    ):
        """Test the list_topics tool wrapper with all optional parameters."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        list_topics_tool = decorated_functions['list_topics']
        assert list_topics_tool is not None

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        expected_response = {'topics': [{'topicName': 'test-topic'}]}
        mock_list_topics.return_value = expected_response

        # Act
        result = list_topics_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name_filter='test',
            max_results=10,
            next_token='token',
        )

        # Assert
        mock_config.assert_called_once_with(
            user_agent_extra='awslabs/mcp/aws-msk-mcp-server/1.0.0'
        )
        mock_boto3_client.assert_called_once_with(
            'kafka', region_name='us-east-1', config=mock_config_instance
        )
        mock_list_topics.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            mock_kafka_client,
            topic_name_filter='test',
            max_results=10,
            next_token='token',
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.list_topics')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.__version__', '1.0.0')
    def test_list_topics_tool_without_optional_params(
        self, mock_config, mock_list_topics, mock_boto3_client
    ):
        """Test the list_topics tool wrapper without optional parameters."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        list_topics_tool = decorated_functions['list_topics']

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        expected_response = {'topics': []}
        mock_list_topics.return_value = expected_response

        # Act
        result = list_topics_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name_filter=None,
            max_results=None,
            next_token=None,
        )

        # Assert
        mock_list_topics.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            mock_kafka_client,
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.describe_topic')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.__version__', '1.0.0')
    def test_describe_topic_tool(self, mock_config, mock_describe_topic, mock_boto3_client):
        """Test the describe_topic tool wrapper."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        describe_topic_tool = decorated_functions['describe_topic']
        assert describe_topic_tool is not None

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        expected_response = {'TopicName': 'test-topic', 'Status': 'ACTIVE'}
        mock_describe_topic.return_value = expected_response

        # Act
        result = describe_topic_tool(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
        )

        # Assert
        mock_config.assert_called_once_with(
            user_agent_extra='awslabs/mcp/aws-msk-mcp-server/1.0.0'
        )
        mock_boto3_client.assert_called_once_with(
            'kafka', region_name='us-east-1', config=mock_config_instance
        )
        mock_describe_topic.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            'test-topic',
            mock_kafka_client,
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.describe_topic_partitions')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.__version__', '1.0.0')
    def test_describe_topic_partitions_tool_with_params(
        self, mock_config, mock_describe_partitions, mock_boto3_client
    ):
        """Test the describe_topic_partitions tool wrapper with optional params."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        tool_func = decorated_functions['describe_topic_partitions']
        assert tool_func is not None

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        expected_response = {'Partitions': [{'Partition': 0}]}
        mock_describe_partitions.return_value = expected_response

        # Act
        result = tool_func(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            max_results=5,
            next_token='token',
        )

        # Assert
        mock_describe_partitions.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            'test-topic',
            mock_kafka_client,
            max_results=5,
            next_token='token',
        )
        assert result == expected_response

    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.describe_topic_partitions')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.Config')
    @patch('awslabs.aws_msk_mcp_server.tools.read_topics.__version__', '1.0.0')
    def test_describe_topic_partitions_tool_without_optional_params(
        self, mock_config, mock_describe_partitions, mock_boto3_client
    ):
        """Test the describe_topic_partitions tool wrapper without optional params."""
        # Arrange
        decorated_functions = {}

        class MockMCP:
            @staticmethod
            def tool(name=None, **kwargs):
                def decorator(func):
                    decorated_functions[name] = func
                    return func

                return decorator

        register_module(cast(FastMCP, MockMCP()))

        tool_func = decorated_functions['describe_topic_partitions']

        mock_kafka_client = MagicMock()
        mock_boto3_client.return_value = mock_kafka_client

        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance

        expected_response = {'Partitions': []}
        mock_describe_partitions.return_value = expected_response

        # Act
        result = tool_func(
            region='us-east-1',
            cluster_arn='arn:aws:kafka:us-east-1:123:cluster/test/abc',
            topic_name='test-topic',
            max_results=None,
            next_token=None,
        )

        # Assert
        mock_describe_partitions.assert_called_once_with(
            'arn:aws:kafka:us-east-1:123:cluster/test/abc',
            'test-topic',
            mock_kafka_client,
        )
        assert result == expected_response
